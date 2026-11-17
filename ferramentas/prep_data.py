"""Normaliza a extração do Hub XP (JSON com eb/cp/lf/tp) num conjunto de registros para o portal."""
import json, re, sys
from datetime import datetime

def brn(s):
    s = s.replace("R$", "").strip()
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0

def rate_num(t):
    m = re.search(r"(-?\s?[\d.,]+)\s*%", t.replace("+ ", "+").replace("- ", "-"))
    if not m: return None
    v = m.group(1).replace(" ", "")
    return float(v.replace(".", "").replace(",", ".")) if "," in v else float(v)

def indexador(t):
    u = t.upper()
    if "IPC-A" in u: return "IPCA"
    if "IGP" in u: return "IGPM"
    if "DOLAR" in u or "PTAX" in u: return "USD"
    if "LFT" in u or "SELIC" in u: return "SELIC"
    if re.search(r"CDI\s*[+-]", u): return "CDI+"
    if "CDI" in u: return "CDI"
    return "PRE"

def bucket(venc, hoje):
    y = (venc - hoje).days / 365.25
    if y < 0.75: return 0
    n = round(y)
    return 8 if n > 7 else n           # 0=6m, 1..7 anos, 8=>7 anos

def rating_class(r):
    b = re.sub(r"\(.*?\)", "", r).replace("br", "").replace(".", "").strip()
    m = re.match(r"(AAA|AA|A|BBB|BB|B|CCC|CC|C|D)", b)
    if not m: return "Sem rating"
    c = m.group(1)
    return c if c in ("AAA", "AA", "A", "BBB") else "BB ou menor"

def short_rating(r):
    return re.sub(r"\s*\(.*?\)", "", r).strip() or "-"

def emissor_de(a):
    base = a.rsplit(" - ", 1)[0]
    return re.sub(r"\s*-\s*JURO MENSAL", "", base).strip()

def fmt_like(template, v):
    """Escreve v no lugar do número de uma taxa como 'CDI + 0,40%' ou '90,5% CDI'."""
    if v is None or not template: return template
    txt = f"{v:.2f}".rstrip("0").rstrip(".") if abs(v * 100 - round(v * 100)) < 1e-9 else f"{v:.2f}"
    m = re.search(r"\d+,\d+|\d+", template)
    dec = len(m.group(0).split(",")[1]) if m and "," in m.group(0) else 0
    txt = f"{v:.{max(dec, 2) if dec else 2}f}"
    if not dec or "CDI" in template and "+" not in template and "-" not in template:
        txt = f"{v:.2f}".rstrip("0").rstrip(".")
    txt = txt.replace(".", ",")
    if re.search(r"CDI\s*[+-]", template):
        return f"CDI + {txt}%" if v >= 0 else f"CDI -{txt.lstrip('-')}%"
    return re.sub(r"-?\d+(?:,\d+)?(?=\s*%)", txt, template, count=1)

def add_media(r):
    for a, b, out_s, out_n in (("r0", "r1", "r2", "n2"), ("g0", "g1", "g2", "m2")):
        n0 = r["n0"] if a == "r0" else r["m0"]; n1 = r["n1"] if a == "r0" else r["m1"]
        if n0 is None or n1 is None:
            r[out_s], r[out_n] = r[a], n0
        else:
            avg = round((n0 + n1) / 2, 4)
            r[out_n] = avg; r[out_s] = fmt_like(r[a], avg)
    return r

# Gross Up calculado no padrão da XP para isentos sem Gross Up na extração.
# Calibrado em 16/11/2026 contra os isentos de Emissão Bancária (LCA/LCI/LCD), que têm o Gross Up da própria XP:
# pré com desvio máx. 0,01 p.p.; IPCA+ 0,01 p.p.; % CDI 0,08 p.p.
CDI_PROJ, IPCA_PROJ = 0.1528, 0.0736

def _ir(d): return .225 if d <= 180 else .20 if d <= 360 else .175 if d <= 720 else .15

def _g_pre(n, t, a):
    N = (1 + n) ** t - 1
    return (1 + N / (1 - a)) ** (1 / t) - 1

def gross_calc(ix, v, venc, hoje):
    if v is None: return None
    d = max((venc - hoje).days, 1); t = d / 365; a = _ir(d)
    if ix == "PRE":
        return _g_pre(v / 100, t, a) * 100
    if ix == "CDI":
        dd = (1 + CDI_PROJ) ** (1 / 252) - 1; n = 252 * t
        N = (1 + v / 100 * dd) ** n - 1
        return ((1 + N / (1 - a)) ** (1 / n) - 1) / dd * 100
    if ix in ("IPCA", "CDI+"):
        base = IPCA_PROJ if ix == "IPCA" else CDI_PROJ
        nom = (1 + base) * (1 + v / 100) - 1
        return ((1 + _g_pre(nom, t, a)) / (1 + base) - 1) * 100
    return None

def build(src, data_str):
    raw = json.load(open(src, encoding="utf-8"))
    hoje = datetime.strptime(data_str, "%d/%m/%Y")
    recs, seen = [], set()
    for l in raw.get("eb", "").splitlines():
        if l in seen: continue
        seen.add(l)
        a, v, liq, tmin, tmax, gmin, gmax, pu, q, rat, risco = l.split("~")[:11]
        venc = datetime.strptime(v, "%d/%m/%Y"); tipo = a.split()[0]
        recs.append(dict(c="EB", a=a, e=emissor_de(a), t=tipo, v=v, vd=venc.strftime("%Y%m%d"), b=bucket(venc, hoje),
                         l=1 if liq.strip().lower().startswith("di") else 0, i=indexador(tmin),
                         r0=tmin, r1=tmax, n0=rate_num(tmin), n1=rate_num(tmax), g0=gmin, g1=gmax, m0=rate_num(gmin), m1=rate_num(gmax),
                         pu=brn(pu), am=brn(pu) * brn(q), rt=short_rating(rat), rc=rating_class(rat),
                         rk=int(risco) if risco.isdigit() else None, x=1 if tipo in ("LCA", "LCI", "LCD") else 0, p="Geral"))
    for key, cat in (("cp", "CP"), ("lf", "LF")):
        useen = set()
        for l in raw.get(key, "").splitlines():
            f = l.split("~")
            nome, icons = (f[0].split("#", 1) + [""])[:2]
            v, tmin, tmax, pu, q, rat, risco, tipo = f[1], f[3], f[4], f[5], f[6], f[7], f[8], f[9]
            k = (nome, v, tmin, pu)
            if k in useen: continue
            useen.add(k)
            ix = indexador(tmin)
            if ix in ("USD",): continue
            venc = datetime.strptime(v, "%d/%m/%Y")
            publico = "Profissional" if "investor-professional" in icons else ("Qualificado" if "investor-qualified" in icons else "Geral")
            isento = "encouraged-badge" in icons or tipo in ("CRI", "CRA", "LIG")
            n0, n1 = rate_num(tmin), rate_num(tmax)
            g0 = g1 = ""; m0 = m1 = None; gc = 0
            gs0 = f[10].strip() if len(f) > 11 else ""
            gs1 = f[11].strip() if len(f) > 11 else ""
            if gs0 and gs1 and rate_num(gs0) is not None:      # Gross Up lido da tela da XP
                g0, g1, m0, m1 = gs0, gs1, rate_num(gs0), rate_num(gs1)
            elif isento and ix in ("PRE", "CDI", "IPCA", "CDI+"):   # sem a coluna: calcula no padrão da XP
                m0, m1 = gross_calc(ix, n0, venc, hoje), gross_calc(ix, n1, venc, hoje)
                if m0 is not None and m1 is not None:
                    m0, m1 = round(m0, 4), round(m1, 4); g0, g1 = fmt_like(tmin, m0), fmt_like(tmax, m1); gc = 1
            recs.append(dict(c=cat, a=nome, e=emissor_de(nome), t=tipo or nome.split()[0], v=v, vd=venc.strftime("%Y%m%d"), b=bucket(venc, hoje),
                             l=0, i=ix, r0=tmin, r1=tmax, n0=n0, n1=n1, g0=g0, g1=g1, m0=m0, m1=m1, gc=gc,
                             pu=brn(pu), am=brn(pu) * brn(q), rt=short_rating(rat), rc=rating_class(rat),
                             rk=int(risco) if risco.isdigit() else None, x=1 if isento else 0, p=publico,
                             du=(float(f[12].replace(',', '.')) if len(f) > 12 and f[12].strip().replace(',', '.').replace('.', '', 1).isdigit() else None)))
    for l in raw.get("tp", "").splitlines():
        a, v, tmin, tmax, pu, q, risco = l.split("~")[:7]
        venc = datetime.strptime(v, "%d/%m/%Y")
        recs.append(dict(c="TP", a=a, e="Tesouro Nacional", t=a.split()[0], v=v, vd=venc.strftime("%Y%m%d"), b=bucket(venc, hoje), l=0,
                         i=indexador(tmin), r0=tmin, r1=tmax, n0=rate_num(tmin), n1=rate_num(tmax), g0="", g1="", m0=None, m1=None,
                         pu=brn(pu), am=brn(pu) * brn(q), rt="Soberano", rc="Soberano", rk=int(risco) if risco.isdigit() else None, x=0, p="Geral"))
    return [add_media(r) for r in recs]

if __name__ == "__main__":
    recs = build(sys.argv[1], sys.argv[2])
    from collections import Counter
    print(len(recs), Counter(r["c"] for r in recs), Counter((r["c"], r["i"]) for r in recs))
    print(Counter(r["rc"] for r in recs)); print(Counter(r["t"] for r in recs))
    bad = [r for r in recs if r["n0"] is None]; print("sem taxa:", len(bad), [b["r0"] for b in bad[:5]])

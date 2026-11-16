"""Gera portal/index.html a partir da extração do Hub XP.
Uso: python3 build_portal.py <extracao.json> <dd/mm/aaaa> <hh:mm>"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prep_data import build

src, date, time = sys.argv[1], sys.argv[2], sys.argv[3]
recs = build(src, date)
for r in recs:  # arredonda para enxugar o JSON
    r["pu"] = round(r["pu"], 2); r["am"] = round(r["am"], 2)
payload = json.dumps({"date": date, "time": time.replace(":", "h"), "recs": recs}, ensure_ascii=False, separators=(",", ":"))
payload = payload.replace("</", "<\\/")
here = os.path.dirname(os.path.abspath(__file__))
import base64
FD = os.path.join(here, "fonts")
fonts = {k: base64.b64encode(open(os.path.join(FD, f), "rb").read()).decode() for k, f in
         (("RC-B.ttf", "RobotoCondensed-Bold-sub.ttf"), ("PT.ttf", "PT_Sans-Narrow-Web-Regular-sub.ttf"), ("PT-B.ttf", "PT_Sans-Narrow-Web-Bold-sub.ttf"))}
html = open(os.path.join(here, "template.html"), encoding="utf-8").read().replace("__DATA__", payload).replace("__FONTS__", json.dumps(fonts))
out = os.path.join(here, "..", "index.html")
open(out, "w", encoding="utf-8").write(html)
print(out, len(recs), f"{len(html)/1024:.0f} KB")

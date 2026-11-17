// Funções coladas no Hub XP (aba Renda Fixa) com a ferramenta de JavaScript do Claude in Chrome.
// 1) Cole este arquivo inteiro uma vez. 2) Em cada aba, ajuste as colunas (ver RUNBOOK) e rode __coletar('chave').
// 3) Rode __empacotar() e depois __quadro(0), __quadro(1)... tirando um zoom (PNG) de cada quadro.
window.__T = c => c.innerText.trim().replace(/\s+/g, ' ');
window.__grabAll = () => {
  const all = [...document.querySelectorAll('soma-table-row')];
  const h = [...all[0].querySelectorAll('soma-table-cell')].map(__T);
  return all.slice(1).map(r => [...r.querySelectorAll('soma-table-cell')].map((c, i) => {
    if (h[i] === 'Risco') { const b = [...c.querySelectorAll('*')].find(e => e.tagName == 'SOMA-BADGE'); return b ? (b.getAttribute('label') || b.getAttribute('value') || b.textContent.trim()) : ''; }
    if (i === 0) return __T(c) + '#' + [...c.querySelectorAll('soma-icon')].map(e => e.getAttribute('icon')).join('+');
    return __T(c);
  }));
};
window.__header = () => [...document.querySelectorAll('soma-table-row')][0].querySelectorAll('soma-table-cell').length && [...[...document.querySelectorAll('soma-table-row')][0].querySelectorAll('soma-table-cell')].map(__T);
// Coleta a página atual e avança. Chame repetidas vezes (uma chamada por página, com ~2 s entre elas) até aparecer "FIM".
window.__D = window.__D || {};
window.__coletar = (chave) => {
  const p = document.querySelector('soma-pagination');
  const rows = __grabAll();
  window.__D[chave] = window.__D[chave] || { hdr: __header(), rows: [] };
  const seen = new Set(window.__D[chave].rows.map(r => r.join('~')));
  let novos = 0; rows.forEach(r => { const k = r.join('~'); if (!seen.has(k)) { window.__D[chave].rows.push(r); seen.add(k); novos++; } });
  if (!p) return chave + ': ' + window.__D[chave].rows.length + ' linhas FIM';
  const pg = +p.getAttribute('page'), tot = Math.ceil(+p.getAttribute('total') / +p.getAttribute('itemsperpage'));
  if (pg >= tot) return chave + ': página ' + pg + '/' + tot + ', ' + window.__D[chave].rows.length + ' linhas FIM';
  p.shadowRoot.querySelectorAll('button')[2].click();
  return chave + ': página ' + pg + '/' + tot + ' (+' + novos + '), total ' + window.__D[chave].rows.length;
};
// Converte cada aba para o formato de linhas usado por ferramentas/prep_data.py
window.__fmt = {
  // Emissão Bancária: ativo~venc~liquidez~tmin~tmax~gmin~gmax~pu~qtd~rating~risco
  eb: d => { const H = d.hdr, ix = n => H.findIndex(x => x.startsWith(n)); return d.rows.map(r => [r[0].split('#')[0], r[ix('Vencimento')], r[ix('Liquidez')], r[ix('Taxa Mín')], r[ix('Taxa Máx')], r[ix('Gross Up: Taxa Mín')], r[ix('Gross Up: Taxa Máx')], r[ix('P.U')], r[ix('Qtd. min')], r[ix('Rating')], r[ix('Risco')]].join('~')).join('\n'); },
  // Crédito Privado / LF: ativo#icones~venc~ir~tmin~tmax~pu~qtd~rating~risco~tipo~gmin~gmax
  cp: d => { const H = d.hdr, ix = n => H.findIndex(x => x.startsWith(n)); return d.rows.map(r => [r[0], r[ix('Vencimento')], '', r[ix('Taxa Mín')], r[ix('Taxa Máx')], r[ix('P.U')], r[ix('Qtd. min')], r[ix('Rating')], r[ix('Risco')], r[ix('Tipo de produto')], ix('Gross Up: Taxa Mín') >= 0 ? r[ix('Gross Up: Taxa Mín')] : '', ix('Gross Up: Taxa Máx') >= 0 ? r[ix('Gross Up: Taxa Máx')] : '', ix('Duration') >= 0 ? r[ix('Duration')] : ''].join('~')).join('\n'); },
  // Títulos Públicos: ativo~venc~tmin~tmax~pu~qtd~risco
  tp: d => { const H = d.hdr, ix = n => H.findIndex(x => x.startsWith(n)); return d.rows.map(r => [r[0].split('#')[0], r[ix('Vencimento')], r[ix('Taxa Mín')], r[ix('Taxa Máx')], r[ix('P.U')], r[ix('Qtd. min')], r[ix('Risco')]].join('~')).join('\n'); }
};
window.__empacotar = async () => {
  const D = window.__D, out = {};
  if (D.eb) out.eb = __fmt.eb(D.eb);
  if (D.cp) out.cp = __fmt.cp(D.cp);
  if (D.lf) out.lf = __fmt.cp(D.lf);
  if (D.tp) out.tp = __fmt.tp(D.tp);
  const txt = JSON.stringify(out);
  const cs = new Blob([txt]).stream().pipeThrough(new CompressionStream('gzip'));
  window.__GZ = new Uint8Array(await new Response(cs).arrayBuffer());
  return Object.entries(out).map(([k, v]) => k + '=' + v.split('\n').length).join(' ') + ' | gzip ' + window.__GZ.length + ' bytes, quadros=' + Math.ceil(window.__GZ.length / Math.floor(320 * 179 / 8));
};
// Desenha o quadro N (preto e branco) no canto da tela, para ser lido com um zoom PNG e decode_frames.py
window.__quadro = (frame) => {
  const C = 320, R = 180, S = 4, B = 8, bytesPer = Math.floor(C * (R - 1) / 8), data = window.__GZ;
  if (frame < 0) { document.getElementById('__cx')?.remove(); return 'removido'; }
  const chunk = data.slice(frame * bytesPer, frame * bytesPer + bytesPer);
  let cv = document.getElementById('__cx'); if (!cv) { cv = document.createElement('canvas'); cv.id = '__cx'; document.body.appendChild(cv); }
  cv.width = C * S + 2 * B; cv.height = R * S + 2 * B;
  cv.style.cssText = `position:fixed;left:20px;top:20px;z-index:2147483647;width:${cv.width}px;height:${cv.height}px;image-rendering:pixelated`;
  const g = cv.getContext('2d'); g.fillStyle = '#ff0000'; g.fillRect(0, 0, cv.width, cv.height); g.fillStyle = '#ffffff'; g.fillRect(B, B, C * S, R * S); g.fillStyle = '#000000';
  const bits = []; [frame, data.length, chunk.length].forEach(v => { for (let i = 31; i >= 0; i--) bits.push((v >>> i) & 1); });
  bits.forEach((b, i) => { if (b) g.fillRect(B + i * S, B, S, S); });
  for (let i = 0; i < chunk.length; i++) { const byte = chunk[i]; for (let k = 0; k < 8; k++) if ((byte >> (7 - k)) & 1) { const idx = i * 8 + k, r = 1 + Math.floor(idx / C), c = idx % C; g.fillRect(B + c * S, B + r * S, S, S); } }
  return 'quadro ' + frame + ': ' + chunk.length + ' de ' + data.length + ' bytes';
};
'funções carregadas';

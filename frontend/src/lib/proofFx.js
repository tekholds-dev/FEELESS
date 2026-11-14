// 🎆 PROOF FX — the live stage behind a running proof (owner 2026-11-11: "the chat fades into live activity animations and live vitals,
// ~100 different effect types per proof"). Redone 2026-11-14 (owner: "serious professional looks" — no pulsing circles, no star dots, no
// fast flashing; keep the matrix numbers + the chat blocks, organised): one canvas, three layers drawn every frame —
//   BACKGROUND (5) × FOREGROUND (5) × PALETTE (4) = 100 looks per proof, picked from the run's id (the same run always looks the same),
//   and a proof-specific REAL-DATA VIEW on top that rotates every ROTATE s through whichever views the run can fill right now.
// `energy` (0..1) spikes on a new step / spend tick and fades: it only brightens an edge or a frame a little, never flashes.
// Pure 2D canvas, no blur filters, no DOM per particle. The caller stops the loop off-screen / hidden / under fx-lite.

// each palette: [accent, second, warn] — muted, high-contrast on Obsidian; up / down on charts are always UP / DN
export const PALETTES = {
  pow: [['#f5a524', '#ffd27a', '#f0596a'], ['#19e68c', '#f5a524', '#f0596a'], ['#ffb547', '#8fa3ff', '#f0596a'], ['#e9c46a', '#5fd3b5', '#f0596a']],
  pop: [['#3ee7ff', '#9b8cff', '#f0596a'], ['#19e68c', '#3ee7ff', '#f0596a'], ['#7cc4ff', '#ffd27a', '#f0596a'], ['#5fd3b5', '#b9a6ff', '#f0596a']],
  pob: [['#ff8a4c', '#ffd27a', '#3ee7ff'], ['#f5a524', '#19e68c', '#7cc4ff'], ['#ff6b8b', '#ffd27a', '#5fd3b5'], ['#e9c46a', '#8fa3ff', '#ff8a4c']],
  poc: [['#ff5fa8', '#b9a6ff', '#3ee7ff'], ['#c08cff', '#ffd27a', '#ff5fa8'], ['#ff7a9c', '#7cc4ff', '#ffd27a'], ['#e48cff', '#5fd3b5', '#ff7a9c']],
  poe: [['#19e68c', '#ffd27a', '#f0596a'], ['#5fd3b5', '#7cc4ff', '#f0596a'], ['#9be15d', '#e9c46a', '#f0596a'], ['#2fd1a8', '#b9a6ff', '#f0596a']],
  pos: [['#7cc4ff', '#b9a6ff', '#19e68c'], ['#3ee7ff', '#ffd27a', '#ff5fa8'], ['#8fa3ff', '#5fd3b5', '#ffb547'], ['#a5b4fc', '#19e68c', '#f5a524']],
  work: [['#9b8cff', '#3ee7ff', '#ff5fa8'], ['#b9a6ff', '#19e68c', '#ffb547'], ['#8fa3ff', '#ffd27a', '#ff5fa8'], ['#c08cff', '#5fd3b5', '#3ee7ff']],
};
const UP = '#2fd18b'; const DN = '#f0596a'; const INK = '#ecebf3'; const MUTED = '#9d99b3'; const PANEL = '#0b0a13';
const MONO = '"JetBrains Mono", monospace'; const SANS = 'Sora, sans-serif';

// a small seeded random, so one run id = one look
export function seeded(seed) {
  let h = 2166136261;
  for (const ch of String(seed || 'feeless')) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  return () => { h += 0x6D2B79F5; let t = h; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const a = (hex, al) => `${hex}${Math.round(Math.max(0, Math.min(1, al)) * 255).toString(16).padStart(2, '0')}`;

// ── drawing helpers ───────────────────────────────────────────────────────────────────────────────────────────────
function box(c, x, y, w, h, r = 6) { c.beginPath(); if (c.roundRect) c.roundRect(x, y, w, h, r); else c.rect(x, y, w, h); }
function panel(c, x, y, w, h, edge = '#ffffff', al = 0.82) { box(c, x, y, w, h, 6); c.fillStyle = a(PANEL, al); c.fill(); c.strokeStyle = a(edge, 0.12); c.lineWidth = 1; c.stroke(); }
function txt(c, s, x, y, { size = 11, font = MONO, weight = 500, color = INK, align = 'left', max = 0 } = {}) {
  c.font = `${weight} ${size}px ${font}`; c.fillStyle = color; c.textAlign = align; let t = String(s ?? '');
  if (max > 0 && c.measureText(t).width > max) { while (t.length > 1 && c.measureText(`${t}…`).width > max) t = t.slice(0, -1); t = `${t}…`; }
  c.fillText(t, x, y); c.textAlign = 'left'; return c.measureText(t).width;
}
function tag(c, s, x, y, bg, fg = '#0b0a13') {   // a filled price tag on the right axis, TradingView-style
  c.font = `600 10px ${MONO}`; const tw = c.measureText(s).width + 10; box(c, x, y - 8, tw, 16, 3); c.fillStyle = bg; c.fill();
  c.fillStyle = fg; c.fillText(s, x + 5, y + 4); return tw;
}
const fmtPx = v => (v >= 1 ? v.toFixed(4) : v >= 0.001 ? v.toFixed(6) : v.toPrecision(3));
const usd = v => `$${Number(v || 0) < 1 ? Number(v || 0).toFixed(4) : Number(v || 0).toFixed(2)}`;
const pct = v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}%`;
const hostOf = s => { const m = String(s || '').match(/(?:https?:\/\/)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:[/:?#]|\s|$)/i); const host = m ? m[1].replace(/^www\./, '').toLowerCase() : ''; return /\.(html?|jsx?|tsx?|css|json|md|py|txt|png|jpe?g|svg|gif|webp|mp4)$/.test(host) ? '' : host; };

// ── BACKGROUNDS (shared, slow, quiet) ─────────────────────────────────────────────────────────────────────────────
const BG = [
  function matrix(c, s) {   // dim data columns falling — the owner's keeper
    const { w, h, t, p } = s; c.font = `10px ${MONO}`;
    for (let i = 0; i < 40; i++) { const x = (i / 40) * w; const sp = 16 + s.r[i] * 34; const y0 = ((t * sp + s.r[i + 40] * h) % (h + 120)) - 120;
      for (let k = 0; k < 8; k++) { c.fillStyle = a(p[1], 0.04 + (k / 8) * 0.14); c.fillText(((i * 7 + k * 3 + Math.floor(t * 0.8)) % 16).toString(16), x, y0 + k * 13); } }
  },
  function blueprint(c, s) {   // an engineer's grid, minor + major lines, drifting very slowly
    const { w, h, t, p } = s; const off = (t * 3) % 96; c.lineWidth = 1;
    for (let x = -off; x < w + 24; x += 24) { const major = Math.round((x + off) / 24) % 4 === 0; c.strokeStyle = a(p[0], major ? 0.09 : 0.035); c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke(); }
    for (let y = 0; y < h; y += 24) { c.strokeStyle = a(p[0], (y / 24) % 4 === 0 ? 0.09 : 0.035); c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
  },
  function floor(c, s) {   // a perspective floor, moving at a walk
    const { w, h, t, p } = s; const hz = h * 0.5; c.strokeStyle = a(p[0], 0.14); c.lineWidth = 1;
    for (let i = -12; i <= 12; i++) { c.beginPath(); c.moveTo(w / 2 + i * 14, hz); c.lineTo(w / 2 + i * w / 8, h); c.stroke(); }
    for (let k = 0; k < 12; k++) { const z = ((k + (t * 0.18) % 1) / 12); const y = hz + (h - hz) * z * z; c.globalAlpha = z * 0.9; c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
    c.globalAlpha = 1;
  },
  function aurora(c, s) {   // slow curtain bands (gradients only, no blur)
    const { w, h, t, p } = s;
    for (let b = 0; b < 3; b++) { const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, a(p[b % 3], 0)); g.addColorStop(0.5, a(p[b % 3], 0.08)); g.addColorStop(1, a(p[b % 3], 0));
      c.fillStyle = g; c.beginPath(); c.moveTo(0, h);
      for (let x = 0; x <= w; x += 24) c.lineTo(x, h * (0.35 + 0.12 * Math.sin(x / 160 + t * 0.15 + b * 2) + 0.05 * Math.sin(x / 53 - t * 0.25)));
      c.lineTo(w, h); c.fill(); }
  },
  function contour(c, s) {   // topographic lines, barely moving
    const { w, h, t, p } = s; c.lineWidth = 1;
    for (let k = 0; k < 9; k++) { c.strokeStyle = a(k % 3 ? p[0] : p[1], 0.06 + (k % 3 === 0 ? 0.04 : 0)); c.beginPath();
      for (let x = 0; x <= w; x += 12) { const y = h * (k + 0.5) / 9 + 10 * Math.sin(x / 170 + k * 0.9 + t * 0.07) + 6 * Math.sin(x / 61 - k + t * 0.05); x ? c.lineTo(x, y) : c.moveTo(x, y); }
      c.stroke(); }
  },
];

// ── VIEWS — REAL DATA ONLY (owner 2026-11-11: "all these live animations need to be true live data no bs") ──────────────────────
// Every view draws from `s.data`, built by ProofLive from the run itself: the coin's real candles / the watcher's price line, the coins on
// its shortlist, the paper position's return, the game it watches, both minds' own words, the steps their windows took, the sites they
// opened, and the cost and step counts sampled every poll. A view whose data is missing is never shown (ready), so nothing is invented.
function price(c, s) {   // the coin's real candles (or the watcher's price line) with entry / take / stop tagged on a right-hand price axis
  const { w, h, data } = s; const cs = data.candles || []; const line = data.line || []; const AX = 74; const T = 10; const B = 8; const cw = w - AX - 8;
  const vals = cs.length ? cs.flatMap(k => [k.h, k.l]) : line; const lv = [data.entry, data.tp, data.sl].filter(v => v > 0);
  const lo = Math.min(...vals, ...lv); const hi = Math.max(...vals, ...lv); const span = hi - lo || hi * 0.01 || 1;
  const y = v => T + (1 - (v - lo) / span) * (h - T - B);
  if (h >= 90) { c.strokeStyle = a('#ffffff', 0.06); c.lineWidth = 1; for (let k = 0; k <= 3; k++) { const v = lo + span * k / 3; c.beginPath(); c.moveTo(8, y(v)); c.lineTo(cw + 8, y(v)); c.stroke(); txt(c, fmtPx(v), cw + 14, y(v) + 3, { size: 9, color: MUTED }); } }
  c.strokeStyle = a('#ffffff', 0.12); c.beginPath(); c.moveTo(cw + 10, T - 4); c.lineTo(cw + 10, h - B + 2); c.stroke();
  if (cs.length) { const n = cs.length; const bw = cw / n;
    cs.forEach((k, i) => { const col = k.c >= k.o ? UP : DN; const x = 8 + i * bw; c.strokeStyle = c.fillStyle = col;
      c.beginPath(); c.moveTo(x + bw / 2, y(k.h)); c.lineTo(x + bw / 2, y(k.l)); c.stroke();
      c.fillRect(x + bw * 0.18, y(Math.max(k.o, k.c)), Math.max(1, bw * 0.64), Math.max(1.5, Math.abs(y(k.o) - y(k.c)))); });
  } else { c.lineWidth = 1.6; c.strokeStyle = s.p[0]; c.beginPath(); line.forEach((v, i) => { const x = 8 + (i / Math.max(1, line.length - 1)) * cw; i ? c.lineTo(x, y(v)) : c.moveTo(x, y(v)); }); c.stroke(); c.lineWidth = 1; }
  [[data.tp, 'TAKE', UP], [data.entry, 'ENTRY', '#c9c6d8'], [data.sl, 'STOP', DN]].forEach(([v, l, col]) => { if (!(v > 0)) return;
    c.strokeStyle = a(col, 0.55); c.setLineDash([4, 4]); c.beginPath(); c.moveTo(8, y(v)); c.lineTo(cw + 10, y(v)); c.stroke(); c.setLineDash([]);
    tag(c, l, 10, y(v), a(PANEL, 0.92), col); tag(c, fmtPx(v), cw + 12, y(v), a(col, 0.9)); });
  const last = cs.length ? cs[cs.length - 1].c : line[line.length - 1];
  if (last > 0) { const ly = y(last); c.strokeStyle = a(s.p[0], 0.8); c.beginPath(); c.moveTo(8, ly); c.lineTo(cw + 10, ly); c.stroke();
    tag(c, fmtPx(last), cw + 12, ly, s.p[0]); if (data.entry > 0) txt(c, pct((last / data.entry - 1) * 100), cw + 6, ly - 12, { size: 10, weight: 700, color: last >= data.entry ? UP : DN, align: 'right' }); }
}
price.ready = d => (d.candles || []).length > 2 || (d.line || []).length > 2;

function coins(c, s) {   // the real shortlist, ranked: each coin's change as a bar from zero, the picked one marked
  const { w, h, p, data } = s; const list = [...data.coins].sort((x, y) => (!!y.picked - !!x.picked) || ((y.chg ?? -1e9) - (x.chg ?? -1e9)));
  const head = h >= 70 ? 18 : 0; const rh = Math.max(16, Math.min(24, (h - head - 6) / Math.max(1, list.length))); const n = Math.max(1, Math.floor((h - head - 4) / rh));
  if (head) { txt(c, `SHORTLIST · ${list.length} COIN${list.length === 1 ? '' : 'S'}`, 10, 13, { size: 9, weight: 600, color: MUTED }); txt(c, '24H CHANGE', w - 10, 13, { size: 9, weight: 600, color: MUTED, align: 'right' }); }
  const mx = Math.max(5, ...list.map(k => Math.abs(k.chg || 0))); const x0 = Math.max(120, w * 0.42); const half = (w - x0 - 70) / 2; const zero = x0 + half;
  c.strokeStyle = a('#ffffff', 0.14); c.beginPath(); c.moveTo(zero, head); c.lineTo(zero, head + n * rh); c.stroke();
  list.slice(0, n).forEach((k, i) => { const yy = head + i * rh; const mid = yy + rh / 2;
    if (k.picked) { box(c, 4, yy + 1, w - 8, rh - 2, 4); c.fillStyle = a(p[0], 0.12); c.fill(); c.strokeStyle = a(p[0], 0.6); c.stroke(); }
    txt(c, `$${k.sym}`, 12, mid + 4, { size: 11, weight: k.picked ? 700 : 500, color: k.picked ? INK : '#c9c6d8', max: x0 - 70 });
    if (k.picked) tag(c, 'PICK', x0 - 50, mid, p[0]);
    if (k.chg != null) { const bw = (Math.abs(k.chg) / mx) * half; c.fillStyle = a(k.chg >= 0 ? UP : DN, 0.75); c.fillRect(k.chg >= 0 ? zero : zero - bw, mid - 4, bw, 8);
      txt(c, pct(k.chg), w - 10, mid + 4, { size: 10, weight: 600, color: k.chg >= 0 ? UP : DN, align: 'right' }); } });
}
coins.ready = d => (d.coins || []).length > 0;

function talk(c, s) {   // both minds' own words as an ordered transcript: A on the left lane, B on the right, newest at the bottom
  const { w, h, p, data } = s; const cw = Math.min(w * 0.66, 460); const ch = 36; const gap = 9; const n = Math.max(1, Math.floor((h - 6) / (ch + gap)));
  const lines = data.talk.slice(-n);
  lines.forEach((m, i) => { const k = lines.length - 1 - i; const yy = h - 4 - (k + 1) * ch - k * gap; const col = p[m.mind % 2 ? 1 : 0]; const x = m.mind ? w - cw - 10 : 10;
    c.globalAlpha = k === 0 ? 1 : Math.max(0.45, 0.85 - k * 0.15);
    panel(c, x, yy, cw, ch, col, 0.86); c.fillStyle = col; c.fillRect(x, yy + 4, 2.5, ch - 8);
    txt(c, `MIND ${m.mind ? 'B' : 'A'}`, x + 12, yy + 13, { size: 8.5, weight: 700, color: col });
    txt(c, String(m.text || '').replace(/\s+/g, ' '), x + 12, yy + 27, { size: 11.5, font: SANS, weight: 400, color: INK, max: cw - 24 }); });
  c.globalAlpha = 1;
}
talk.ready = d => (d.talk || []).length > 0;

function steps(c, s) {   // the real steps its windows took, as a log table: # · mind · action · detail; the newest row is marked
  const { w, h, p, e, data } = s; const all = data.steps; const head = 18; const rh = 17; const n = Math.max(1, Math.floor((h - head - 4) / rh)); const rows = all.slice(-n); const first = all.length - rows.length;
  const X = [10, 44, 84, 170];
  ['#', 'MIND', 'ACTION', 'DETAIL'].forEach((l, i) => txt(c, l, X[i], 12, { size: 8.5, weight: 700, color: MUTED }));
  txt(c, `${all.length} step${all.length === 1 ? '' : 's'}`, w - 10, 12, { size: 9, weight: 600, color: MUTED, align: 'right' });
  c.strokeStyle = a('#ffffff', 0.1); c.beginPath(); c.moveTo(6, head - 2); c.lineTo(w - 6, head - 2); c.stroke();
  rows.forEach((r, i) => { const yy = head + i * rh; const last = i === rows.length - 1; const col = r.mind ? p[1] : p[0];
    if (last) { c.fillStyle = a(p[0], 0.1 + e * 0.08); c.fillRect(6, yy, w - 12, rh); c.fillStyle = p[0]; c.fillRect(6, yy, 2, rh); }
    else if (i % 2) { c.fillStyle = a('#ffffff', 0.025); c.fillRect(6, yy, w - 12, rh); }
    const [act, ...rest] = String(r.text || '').split(' · ');
    txt(c, String(first + i + 1).padStart(2, '0'), X[0], yy + 12, { size: 10, color: MUTED });
    txt(c, r.mind != null ? 'AB'[r.mind] || '·' : '·', X[1] + 8, yy + 12, { size: 10, weight: 700, color: col });
    txt(c, act.toUpperCase(), X[2], yy + 12, { size: 9.5, weight: 600, color: last ? INK : '#c9c6d8', max: X[3] - X[2] - 8 });
    txt(c, rest.join(' · '), X[3], yy + 12, { size: 10.5, color: last ? INK : '#b3afc6', max: w - X[3] - 12 }); });
}
steps.ready = d => (d.steps || []).length > 0;

function meter(c, s) {   // what this run has cost and done: three plain numbers, then spend over the run on a labelled axis
  const { w, h, p, data } = s; const ser = data.series; const n = ser.length; const last = ser[n - 1]; const per = last.steps ? last.spent / last.steps : 0;
  const kw = Math.min(170, w * 0.34); const kpis = [['SPENT SO FAR', usd(last.spent), p[0]], ['STEPS TAKEN', String(last.steps), INK], ['COST PER STEP', last.steps ? usd(per) : '—', INK]];
  const kh = Math.min(34, (h - 8) / 3);
  kpis.forEach(([l, v, col], i) => { const yy = 4 + i * kh; txt(c, l, 10, yy + 10, { size: 8.5, weight: 700, color: MUTED }); if (kh >= 26) txt(c, v, 10, yy + 25, { size: 14, weight: 700, color: col }); else txt(c, v, kw - 8, yy + 10, { size: 11, weight: 700, color: col, align: 'right' }); });
  const x0 = kw + 40; const x1 = w - 12; const y0 = 10; const y1 = h - 16; if (x1 - x0 < 60 || y1 - y0 < 30) return;
  const maxU = Math.max(...ser.map(x => x.spent), 1e-6); const maxS = Math.max(...ser.map(x => x.steps), 1); const X = i => x0 + (i / Math.max(1, n - 1)) * (x1 - x0); const Y = v => y1 - (v / maxU) * (y1 - y0);
  c.strokeStyle = a('#ffffff', 0.08); [0, 0.5, 1].forEach(f => { c.beginPath(); c.moveTo(x0, Y(maxU * f)); c.lineTo(x1, Y(maxU * f)); c.stroke(); });
  txt(c, usd(maxU), x0 - 6, y0 + 4, { size: 9, color: MUTED, align: 'right' }); txt(c, '$0', x0 - 6, y1 + 3, { size: 9, color: MUTED, align: 'right' });
  txt(c, 'run start', x0, h - 3, { size: 8.5, color: MUTED }); txt(c, 'now', x1, h - 3, { size: 8.5, color: MUTED, align: 'right' });
  ser.forEach((x, i) => { if (i && x.steps > ser[i - 1].steps) { c.fillStyle = a(p[1], 0.5); c.fillRect(X(i) - 1, y1 - 6 * Math.min(1, (x.steps - ser[i - 1].steps) / Math.max(1, maxS / 6)) - 2, 2, 6); } });
  c.beginPath(); c.moveTo(X(0), y1); ser.forEach((x, i) => c.lineTo(X(i), Y(x.spent))); c.lineTo(X(n - 1), y1); c.closePath();
  const g = c.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, a(p[0], 0.28)); g.addColorStop(1, a(p[0], 0)); c.fillStyle = g; c.fill();
  c.strokeStyle = p[0]; c.lineWidth = 1.8; c.beginPath(); ser.forEach((x, i) => (i ? c.lineTo(X(i), Y(x.spent)) : c.moveTo(X(i), Y(x.spent)))); c.stroke(); c.lineWidth = 1;
  c.fillStyle = p[0]; c.beginPath(); c.arc(X(n - 1), Y(last.spent), 3, 0, 7); c.fill();
}
meter.ready = d => (d.series || []).length > 1;

function roe(c, s) {   // PoP: the paper position's real return on margin over this run, against break-even, with its high and low
  const { w, h, p, data } = s; const v = data.roe; const last = v[v.length - 1]; const pos = data.pos || {};
  const head = 30; const lo = Math.min(0, ...v); const hi = Math.max(0, ...v); const span = hi - lo || 1; const x0 = 10; const x1 = w - 60;
  const y = x => head + 18 + (1 - (x - lo) / span) * (h - head - 36); const X = i => x0 + (i / Math.max(1, v.length - 1)) * (x1 - x0); const z = y(0);
  txt(c, 'PAPER POSITION · RETURN ON MARGIN', 10, 12, { size: 8.5, weight: 700, color: MUTED });
  txt(c, [pos.market, pos.side && String(pos.side).toUpperCase(), pos.lev && `${pos.lev}×`].filter(Boolean).join(' · ') || `${v.length} readings this run`, 10, 25, { size: 11, weight: 600, color: INK, max: w - 130 });
  txt(c, pct(last), w - 10, 26, { size: 20, weight: 700, color: last >= 0 ? UP : DN, align: 'right' });
  c.strokeStyle = a('#ffffff', 0.35); c.setLineDash([4, 4]); c.beginPath(); c.moveTo(x0, z); c.lineTo(x1, z); c.stroke(); c.setLineDash([]);
  txt(c, 'break-even', x1 + 4, z + 3, { size: 8.5, color: MUTED });
  [[UP, 0, z], [DN, z, h]].forEach(([col, top, bot]) => { c.save(); c.beginPath(); c.rect(0, top, w, bot - top); c.clip();
    c.beginPath(); c.moveTo(X(0), z); v.forEach((x, i) => c.lineTo(X(i), y(x))); c.lineTo(X(v.length - 1), z); c.closePath(); c.fillStyle = a(col, 0.16); c.fill();
    c.strokeStyle = col; c.lineWidth = 1.8; c.beginPath(); v.forEach((x, i) => (i ? c.lineTo(X(i), y(x)) : c.moveTo(X(i), y(x)))); c.stroke(); c.lineWidth = 1; c.restore(); });
  const iH = v.indexOf(Math.max(...v)); const iL = v.indexOf(Math.min(...v));
  if (h >= 90) { if (v[iH] > 0) txt(c, `high ${pct(v[iH])}`, Math.min(X(iH), x1 - 30), y(v[iH]) - 6, { size: 9, color: UP, align: 'center' }); if (v[iL] < 0) txt(c, `low ${pct(v[iL])}`, Math.min(X(iL), x1 - 30), y(v[iL]) + 13, { size: 9, color: DN, align: 'center' }); }
  c.fillStyle = last >= 0 ? UP : DN; c.beginPath(); c.arc(X(v.length - 1), y(last), 3, 0, 7); c.fill();
}
roe.ready = d => (d.roe || []).length > 1;

function score(c, s) {   // PoB: the real game score it is watching, and its pick
  const { w, h, p, data } = s; const g = data.game; const bw = Math.min(150, w * 0.3); const bh = Math.min(64, h - 34); const top = 8;
  [[g.home || 'HOME', g.hs, w / 2 - bw - 40, p[0]], [g.away || 'AWAY', g.as, w / 2 + 40, p[1]]].forEach(([name, n, x, col]) => {
    panel(c, x, top, bw, bh, col, 0.86); c.fillStyle = col; c.fillRect(x, top, bw, 2);
    txt(c, String(name).toUpperCase(), x + bw / 2, top + 16, { size: 10, weight: 700, color: MUTED, align: 'center', max: bw - 12 });
    txt(c, n == null ? '–' : String(n), x + bw / 2, top + bh - 10, { size: Math.min(30, bh * 0.5), weight: 700, color: INK, align: 'center' }); });
  if (g.clock) txt(c, g.clock, w / 2, top + bh / 2 + 4, { size: 11, weight: 600, color: INK, align: 'center' });
  if (g.pick && h >= bh + 30) { const label = `ITS PICK · ${String(g.pick).toUpperCase()}`; c.font = `700 10px ${MONO}`; const tw = c.measureText(label).width + 20;
    box(c, w / 2 - tw / 2, top + bh + 8, tw, 18, 9); c.fillStyle = a(p[0], 0.16); c.fill(); c.strokeStyle = a(p[0], 0.6); c.stroke(); txt(c, label, w / 2, top + bh + 21, { size: 10, weight: 700, color: p[0], align: 'center' }); }
}
score.ready = d => !!(d.game && (d.game.hs != null || d.game.home));

function sources(c, s) {   // PoC / PoE / PoS: every site both minds really opened, how often, and where each one is right now
  const { w, h, p, data } = s; const rows = siteRows(data); const head = 18; const rh = 18; const n = Math.max(1, Math.floor((h - head - 4) / rh));
  txt(c, `WHERE IT READ · ${rows.length} SITE${rows.length === 1 ? '' : 'S'}`, 10, 12, { size: 8.5, weight: 700, color: MUTED }); txt(c, 'VISITS', w - 10, 12, { size: 8.5, weight: 700, color: MUTED, align: 'right' });
  c.strokeStyle = a('#ffffff', 0.1); c.beginPath(); c.moveTo(6, head - 2); c.lineTo(w - 6, head - 2); c.stroke();
  const mx = Math.max(...rows.map(r => r.n), 1); const bx = Math.max(150, w * 0.45); const bwMax = w - bx - 50;
  rows.slice(0, n).forEach((r, i) => { const yy = head + i * rh; const mid = yy + rh / 2;
    txt(c, r.host, 12, mid + 4, { size: 11, weight: r.now.length ? 700 : 500, color: r.now.length ? INK : '#c9c6d8', max: bx - 70 });
    r.now.forEach((m, j) => tag(c, `NOW ${'AB'[m]}`, bx - 104 + j * 50, mid, m ? p[1] : p[0]));
    c.fillStyle = a('#ffffff', 0.06); c.fillRect(bx, mid - 3, bwMax, 6); c.fillStyle = a(p[0], 0.8); c.fillRect(bx, mid - 3, (r.n / mx) * bwMax, 6);
    txt(c, String(r.n), w - 10, mid + 4, { size: 10, weight: 600, color: INK, align: 'right' }); });
}
function siteRows(d) {
  const by = new Map(); const add = (host, mind, now) => { if (!host) return; const r = by.get(host) || { host, n: 0, now: [] }; if (now) { if (!r.now.includes(mind)) r.now.push(mind); } else r.n += 1; by.set(host, r); };
  (d.steps || []).forEach(x => add(hostOf(x.text), x.mind, false)); (d.pages || []).forEach(x => add(hostOf(x.host), x.mind, true));
  return [...by.values()].sort((x, y) => (y.now.length - x.now.length) || (y.n - x.n));
}
sources.ready = d => siteRows(d).length > 0;

const STAGES = [['RESEARCH', /search|open|read|visit|browse|scroll|look|go|navigate|click/i], ['WRITE', /type|write|edit|draft|fill|compose/i], ['BUILD', /build|create|save|file|deploy|upload|make|generate|render/i], ['CHECK', /check|test|verify|review|screenshot|grade|judge/i]];
const stageOf = text => { const act = String(text || '').split(' · ')[0]; const i = STAGES.findIndex(([, re]) => re.test(act)); return i < 0 ? 0 : i; };
function pipeline(c, s) {   // PoS: the build as a pipeline — research → write → build → check — each stage's real step count, the live one lit
  const { w, h, p, e, data } = s; const counts = STAGES.map(() => 0); data.steps.forEach(x => { counts[stageOf(x.text)] += 1; });
  const at = stageOf(data.steps[data.steps.length - 1].text); const nw = Math.min(140, (w - 40) / 4 - 14); const gap = (w - 20 - nw * 4) / 3; const nh = Math.min(52, h - 30); const top = 6;
  STAGES.forEach(([l], i) => { const x = 10 + i * (nw + gap); const done = counts[i] > 0 && i < at; const live = i === at; const col = live ? p[0] : done ? p[1] : '#5d5975';
    if (i) { c.strokeStyle = a(i <= at ? p[1] : '#ffffff', i <= at ? 0.6 : 0.12); c.lineWidth = 2; c.beginPath(); c.moveTo(x - gap, top + nh / 2); c.lineTo(x, top + nh / 2); c.stroke(); c.lineWidth = 1; }
    panel(c, x, top, nw, nh, col, 0.88); if (live) { c.strokeStyle = a(p[0], 0.7 + e * 0.3); c.lineWidth = 1.5; box(c, x, top, nw, nh, 6); c.stroke(); c.lineWidth = 1; }
    txt(c, l, x + 10, top + 15, { size: 9, weight: 700, color: col });
    txt(c, String(counts[i]), x + 10, top + nh - 10, { size: Math.min(18, nh * 0.36), weight: 700, color: counts[i] ? INK : '#5d5975' });
    txt(c, live ? 'NOW' : done ? 'DONE' : '', x + nw - 10, top + nh - 10, { size: 8.5, weight: 700, color: col, align: 'right' }); });
  if (h >= nh + 30) { const last = data.steps[data.steps.length - 1]; txt(c, `${'AB'[last.mind] || '·'}  ${last.text}`, 10, top + nh + 20, { size: 10.5, color: '#c9c6d8', max: w - 20 }); }
}
pipeline.ready = d => (d.steps || []).length > 0;

function ledger(c, s) {   // PoE: this run's own books — every spend tick as a ledger line (time · steps · cost · running total)
  const { w, h, p, data } = s; const ser = data.series; const lines = [];
  ser.forEach((x, i) => { if (i && x.spent !== ser[i - 1].spent) lines.push({ at: x.at, steps: x.steps, d: x.spent - ser[i - 1].spent, bal: x.spent }); });
  const head = 18; const rh = 17; const foot = 20; const n = Math.max(1, Math.floor((h - head - foot - 2) / rh)); const rows = lines.slice(-n);
  const X = [10, Math.max(80, w * 0.24), Math.max(150, w * 0.5), w - 10];
  ['TIME', 'STEPS', 'COST', 'RUNNING TOTAL'].forEach((l, i) => txt(c, l, X[i], 12, { size: 8.5, weight: 700, color: MUTED, align: i === 3 ? 'right' : 'left' }));
  c.strokeStyle = a('#ffffff', 0.1); c.beginPath(); c.moveTo(6, head - 2); c.lineTo(w - 6, head - 2); c.stroke();
  const tm = at => { if (!at) return '—'; const d = new Date(at); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`; };
  rows.forEach((r, i) => { const yy = head + i * rh + 12; if (i % 2) { c.fillStyle = a('#ffffff', 0.025); c.fillRect(6, yy - 12, w - 12, rh); }
    txt(c, tm(r.at), X[0], yy, { size: 10, color: '#c9c6d8' }); txt(c, String(r.steps), X[1], yy, { size: 10, color: '#c9c6d8' });
    txt(c, `−${usd(r.d)}`, X[2], yy, { size: 10, weight: 600, color: DN }); txt(c, usd(r.bal), X[3], yy, { size: 10, weight: 600, color: INK, align: 'right' }); });
  const fy = Math.min(h - 6, head + rows.length * rh + foot - 4); c.strokeStyle = a(p[0], 0.5); c.beginPath(); c.moveTo(6, fy - 14); c.lineTo(w - 6, fy - 14); c.stroke();
  txt(c, `RUN TOTAL · ${lines.length} charge${lines.length === 1 ? '' : 's'}`, X[0], fy, { size: 9, weight: 700, color: MUTED }); txt(c, usd(ser[ser.length - 1].spent), X[3], fy, { size: 11, weight: 700, color: p[0], align: 'right' });
}
ledger.ready = d => (d.series || []).filter((x, i, l) => i && x.spent !== l[i - 1].spent).length > 0;

function draft(c, s) {   // PoC: the newest real words it wrote, laid out as the working draft (author, word count, wrapped lines)
  const { w, h, p, data } = s; const pick = [...data.talk].reverse().find(m => String(m.text || '').trim().length >= 20) || data.talk[data.talk.length - 1];
  const body = String(pick.text || '').replace(/\s+/g, ' ').trim(); const words = body ? body.split(' ').length : 0;
  const pw = Math.min(w - 20, 560); const x = (w - pw) / 2; panel(c, x, 4, pw, h - 8, p[0], 0.9); c.fillStyle = p[0]; c.fillRect(x, 4, pw, 2);
  txt(c, `WORKING DRAFT · MIND ${pick.mind ? 'B' : 'A'}`, x + 12, 20, { size: 8.5, weight: 700, color: p[0] }); txt(c, `${words} word${words === 1 ? '' : 's'}`, x + pw - 12, 20, { size: 9, weight: 600, color: MUTED, align: 'right' });
  c.font = `400 12px ${SANS}`; const lines = []; let cur = '';
  body.split(' ').forEach(word => { const t = cur ? `${cur} ${word}` : word; if (c.measureText(t).width > pw - 24 && cur) { lines.push(cur); cur = word; } else cur = t; }); if (cur) lines.push(cur);
  const n = Math.max(1, Math.floor((h - 40) / 17)); const shown = lines.slice(0, n); if (lines.length > n) shown[n - 1] = `${shown[n - 1].replace(/\s+\S*$/, '')} …`;
  shown.forEach((l, i) => txt(c, l, x + 12, 40 + i * 17, { size: 12, font: SANS, weight: 400, color: INK }));
}
draft.ready = d => (d.talk || []).some(m => String(m.text || '').trim().length > 0);

// which real-data views each proof tries, in order (only the ones whose data exists are shown)
export const SCENES = {
  pow: [price, coins, talk, steps, meter],
  pop: [roe, price, talk, steps, meter],
  pob: [score, talk, steps, meter],
  poc: [draft, sources, talk, steps, meter],
  poe: [ledger, sources, talk, steps, meter],
  pos: [pipeline, steps, sources, talk, meter],
  work: [steps, talk, meter],
};

// ── FOREGROUNDS (shared, quiet: frame the view, never flash) ──────────────────────────────────────────────────────────
function vignette(c, w, h) { const g = c.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.max(w, h) * 0.75); g.addColorStop(0, '#00000000'); g.addColorStop(1, '#0000008c'); c.fillStyle = g; c.fillRect(0, 0, w, h); }
const FG = [
  function clean(c, s) { vignette(c, s.w, s.h); },
  function scan(c, s) {   // one soft scanline every 9 s
    const { w, h, t, p } = s; const y = ((t / 9) % 1) * h; const g = c.createLinearGradient(0, y - 30, 0, y); g.addColorStop(0, a(p[1], 0)); g.addColorStop(1, a(p[1], 0.07)); c.fillStyle = g; c.fillRect(0, y - 30, w, 30); vignette(c, w, h);
  },
  function frame(c, s) {   // HUD corner brackets + a tick ruler along the top
    const { w, h, p, e } = s; const L = 14; c.strokeStyle = a(p[0], 0.45 + e * 0.25); c.lineWidth = 1.5;
    [[6, 6, 1, 1], [w - 6, 6, -1, 1], [6, h - 6, 1, -1], [w - 6, h - 6, -1, -1]].forEach(([x, y, dx, dy]) => { c.beginPath(); c.moveTo(x, y + dy * L); c.lineTo(x, y); c.lineTo(x + dx * L, y); c.stroke(); });
    c.lineWidth = 1; c.strokeStyle = a('#ffffff', 0.1); for (let x = 30; x < w - 30; x += 12) { c.beginPath(); c.moveTo(x, 2); c.lineTo(x, x % 60 < 12 ? 7 : 4); c.stroke(); }
  },
  function sweep(c, s) {   // a slow diagonal light sweep every 14 s
    const { w, h, t, p } = s; const k = (t / 14) % 1; const x = -w * 0.4 + k * w * 1.8; const g = c.createLinearGradient(x - 120, 0, x + 120, h * 0.4);
    g.addColorStop(0, a(p[1], 0)); g.addColorStop(0.5, a(p[1], 0.05)); g.addColorStop(1, a(p[1], 0)); c.fillStyle = g; c.fillRect(0, 0, w, h); vignette(c, w, h);
  },
  function edge(c, s) {   // an accent rule along the bottom edge that warms a little on each new step
    const { w, h, p, e } = s; const g = c.createLinearGradient(0, 0, w, 0); g.addColorStop(0, a(p[0], 0)); g.addColorStop(0.5, a(p[0], 0.45 + e * 0.35)); g.addColorStop(1, a(p[0], 0));
    c.fillStyle = g; c.fillRect(0, h - 2, w, 2); c.fillRect(0, 0, w, 1); vignette(c, w, h);
  },
];

// the look of a run: background × foreground × palette picked from its id (100 per proof); its view is whichever real-data views the run
// can fill right now, rotating every ROTATE seconds.
export const LOOKS_PER_PROOF = BG.length * FG.length * PALETTES.pow.length;
export const ROTATE = 18;
export function pickLook(kind, seed) {
  const r = seeded(`${kind}:${seed}`);
  return { bg: Math.floor(r() * BG.length), scene: Math.floor(r() * 5), fg: Math.floor(r() * FG.length), pal: Math.floor(r() * PALETTES.pow.length) };
}
export const readyScenes = (kind, data) => (SCENES[kind] || SCENES.work).filter(f => f.ready(data || {}));
export function sceneName(kind, look, t, data) { const list = readyScenes(kind, data); return list.length ? list[(look.scene + Math.floor(t / ROTATE)) % list.length].name : ''; }

export function drawFrame(ctx, { w, h, t, kind, look, energy = 0, rnd, data = {}, band = null }) {
  const k = SCENES[kind] ? kind : 'work'; const p = PALETTES[k][look.pal % PALETTES[k].length];
  const s = { w, h, t, p, e: energy, r: rnd, data };
  if (!(w > 4 && h > 4)) return { scene: '', bg: '', fg: '' };   // a 0px canvas (hidden / still opening) makes x % w = NaN and the gradients throw
  ctx.clearRect(0, 0, w, h);
  BG[look.bg % BG.length](ctx, s);
  const list = readyScenes(k, data); let name = '';
  // 🐞 2026-11-14: the view draws only in the open band between the step row and the vitals (its labels used to land under the vitals and
  // the chat line); backgrounds + foregrounds still fill the whole stage
  const [y0, y1] = band && band[1] - band[0] >= 60 ? band : [0, h];
  ctx.save(); if (y0 > 0 || y1 < h) { ctx.translate(0, y0); ctx.beginPath(); ctx.rect(0, 0, w, y1 - y0); ctx.clip(); s.h = y1 - y0; }
  if (list.length) { const step = Math.floor(t / ROTATE); const into = (t % ROTATE) / ROTATE; const cur = list[(look.scene + step) % list.length];
    if (into < 0.04 && step > 0 && list.length > 1) { ctx.globalAlpha = 1 - into / 0.04; list[(look.scene + step - 1) % list.length](ctx, s); ctx.globalAlpha = into / 0.04; }
    cur(ctx, s); ctx.globalAlpha = 1; name = cur.name; }
  ctx.restore(); s.h = h;
  FG[look.fg % FG.length](ctx, s);
  return { scene: name, bg: BG[look.bg % BG.length].name, fg: FG[look.fg % FG.length].name };
}

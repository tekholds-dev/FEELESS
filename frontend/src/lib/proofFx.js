// 🎆 PROOF FX — the live stage behind a running proof (owner 2026-11-11: "the chat fades into live activity animations and live vitals,
// ~100 different effect types per proof"). One canvas, three layers drawn every frame: a BACKGROUND (5) × a proof-specific SCENE (5) ×
// a FOREGROUND (4) = 100 looks per proof, picked from the run's id so the same run always looks the same, and the scene rotates every
// ~22 s so a long run keeps changing. `energy` (0..1) comes from the live vitals: a new step or a spend tick spikes it and the scene reacts.
// Pure 2D canvas, no blur filters, no DOM per particle. The caller stops the loop off-screen / hidden / under fx-lite.

export const PALETTES = {
  pow: [['#ff9f2e', '#ffd166', '#ff5c7a'], ['#ffb347', '#3cf0c5', '#ff7a1a']],
  pop: [['#3ee7ff', '#9b6bff', '#ff5c7a'], ['#3cf0c5', '#3ee7ff', '#ff3fa4']],
  pob: [['#ff6b3d', '#ffd166', '#3cf0c5'], ['#ff3fa4', '#ffb347', '#3ee7ff']],
  poc: [['#ff3fa4', '#b48cff', '#3ee7ff'], ['#ff5c7a', '#ffd166', '#b48cff']],
  poe: [['#3cf0c5', '#ffd166', '#9b6bff'], ['#7dffb2', '#3ee7ff', '#ffd166']],
  pos: [['#3ee7ff', '#b48cff', '#3cf0c5'], ['#9b6bff', '#3ee7ff', '#ff3fa4']],
  work: [['#9b6bff', '#3ee7ff', '#ff3fa4'], ['#b48cff', '#3cf0c5', '#ff3fa4']],
};

// a small seeded random, so one run id = one look
export function seeded(seed) {
  let h = 2166136261;
  for (const ch of String(seed || 'feeless')) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  return () => { h += 0x6D2B79F5; let t = h; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const a = (hex, al) => `${hex}${Math.round(Math.max(0, Math.min(1, al)) * 255).toString(16).padStart(2, '0')}`;

// ── BACKGROUNDS (shared) ────────────────────────────────────────────────────────────────────────────────────────────
const BG = [
  function stars(c, s) {   // drifting starfield, parallax in 3 depths
    const { w, h, t, p } = s;
    for (let i = 0; i < 90; i++) { const d = (i % 3) + 1; const x = ((s.r[i] * w) - t * 6 * d) % w; const y = s.r[i + 90] * h;
      c.fillStyle = a(i % 7 ? '#ffffff' : p[1], 0.18 * d); c.fillRect(x < 0 ? x + w : x, y, d * 0.8, d * 0.8); }
  },
  function floor(c, s) {   // perspective grid floor racing toward you
    const { w, h, t, p } = s; const hz = h * 0.55; c.strokeStyle = a(p[0], 0.22); c.lineWidth = 1;
    for (let i = -12; i <= 12; i++) { c.beginPath(); c.moveTo(w / 2 + i * 14, hz); c.lineTo(w / 2 + i * w / 8, h); c.stroke(); }
    for (let k = 0; k < 12; k++) { const z = ((k + (t * 0.8) % 1) / 12); const y = hz + (h - hz) * z * z; c.globalAlpha = z; c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
    c.globalAlpha = 1;
  },
  function aurora(c, s) {   // slow curtain bands (gradients only, no blur)
    const { w, h, t, p } = s;
    for (let b = 0; b < 3; b++) { const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, a(p[b % 3], 0)); g.addColorStop(0.5, a(p[b % 3], 0.12)); g.addColorStop(1, a(p[b % 3], 0));
      c.fillStyle = g; c.beginPath(); c.moveTo(0, h);
      for (let x = 0; x <= w; x += 24) c.lineTo(x, h * (0.35 + 0.12 * Math.sin(x / 140 + t * 0.4 + b * 2) + 0.06 * Math.sin(x / 47 - t * 0.7)));
      c.lineTo(w, h); c.fill(); }
  },
  function hex(c, s) {   // hex lattice with a travelling pulse
    const { w, h, t, p } = s; const R = 18; const dx = R * 1.73; c.lineWidth = 1;
    for (let y = 0, row = 0; y < h + R; y += R * 1.5, row++) for (let x = (row % 2) * dx / 2; x < w + dx; x += dx) {
      const d = Math.hypot(x - w / 2, y - h / 2); const pulse = Math.max(0, 1 - Math.abs(((d / 260) - t * 0.25) % 1 - 0.5) * 6);
      c.strokeStyle = a(p[0], 0.06 + pulse * 0.3); c.beginPath();
      for (let k = 0; k < 6; k++) { const an = Math.PI / 3 * k + Math.PI / 6; c[k ? 'lineTo' : 'moveTo'](x + R * 0.9 * Math.cos(an), y + R * 0.9 * Math.sin(an)); }
      c.closePath(); c.stroke(); }
  },
  function columns(c, s) {   // dim data columns falling
    const { w, h, t, p } = s; c.font = '10px "JetBrains Mono", monospace';
    for (let i = 0; i < 40; i++) { const x = (i / 40) * w; const sp = 20 + s.r[i] * 50; const y0 = ((t * sp + s.r[i + 40] * h) % (h + 120)) - 120;
      for (let k = 0; k < 8; k++) { c.fillStyle = a(p[1], 0.05 + (k / 8) * 0.16); c.fillText(((i * 7 + k * 3 + Math.floor(t * 2)) % 16).toString(16), x, y0 + k * 13); } }
  },
];

// ── SCENES — REAL DATA ONLY (owner 2026-11-11: "all these live animations need to be true live data no bs") ─────────────────
// Every scene draws from `s.data`, built by ProofLive from the run itself: the coin's real candles / the watcher's price line, the
// coins on its shortlist, both minds' own words, the steps their windows took, and the cost and step counts sampled every poll.
// A scene whose data is missing is never shown (READY), so nothing on screen is invented. Positions and motion are layout; every
// number, word and shape that means something comes from the run.
const fmtPx = v => (v >= 1 ? v.toFixed(4) : v >= 0.001 ? v.toFixed(6) : v.toPrecision(3));
function price(c, s) {   // the coin's real candles (or the watcher's real price line), its entry / take-profit / stop drawn on it
  const { w, h, t, p, e, data } = s; const cs = data.candles || []; const line = data.line || [];
  const vals = cs.length ? cs.flatMap(k => [k.h, k.l]) : line; const lv = [data.entry, data.tp, data.sl].filter(v => v > 0);
  const lo = Math.min(...vals, ...lv); const hi = Math.max(...vals, ...lv); const span = hi - lo || hi * 0.01 || 1;
  const y = v => h * 0.9 - ((v - lo) / span) * h * 0.78;
  if (cs.length) { const n = cs.length; const bw = w / n;
    cs.forEach((k, i) => { const up = k.c >= k.o; c.strokeStyle = c.fillStyle = up ? p[0] : p[2]; c.globalAlpha = 0.45 + 0.55 * (i / n);
      c.beginPath(); c.moveTo(i * bw + bw / 2, y(k.h)); c.lineTo(i * bw + bw / 2, y(k.l)); c.stroke(); c.fillRect(i * bw + bw * 0.2, y(Math.max(k.o, k.c)), bw * 0.6, Math.max(1.5, Math.abs(y(k.o) - y(k.c)))); });
    c.globalAlpha = 1;
  } else { c.lineWidth = 2; c.strokeStyle = p[1]; c.beginPath(); line.forEach((v, i) => { const x = (i / Math.max(1, line.length - 1)) * w; i ? c.lineTo(x, y(v)) : c.moveTo(x, y(v)); }); c.stroke(); c.lineWidth = 1; }
  [[data.entry, 'ENTRY', '#ffffff'], [data.tp, 'TAKE', p[0]], [data.sl, 'STOP', p[2]]].forEach(([v, l, col]) => { if (!(v > 0)) return;
    c.strokeStyle = a(col, 0.7); c.setLineDash([5, 5]); c.beginPath(); c.moveTo(0, y(v)); c.lineTo(w, y(v)); c.stroke(); c.setLineDash([]);
    c.fillStyle = col; c.font = '10px "JetBrains Mono", monospace'; c.fillText(`${l} ${fmtPx(v)}`, 6, y(v) - 4); });
  const last = cs.length ? cs[cs.length - 1].c : line[line.length - 1];
  if (last > 0) { const ly = y(last); c.fillStyle = a(p[1], 0.25 + e * 0.5); c.beginPath(); c.arc(w - 6, ly, 6 + e * 6 + Math.sin(t * 4) * 1.5, 0, 7); c.fill();
    c.fillStyle = '#fff'; c.font = 'bold 11px "JetBrains Mono", monospace'; c.textAlign = 'right'; c.fillText(fmtPx(last), w - 16, ly - 8); c.textAlign = 'start'; }
}
price.ready = d => (d.candles || []).length > 2 || (d.line || []).length > 2;

function coins(c, s) {   // the real shortlist on a radar: each blip is one coin it is weighing, the picked one burns brightest
  const { w, h, t, p, e, data } = s; const list = data.coins; const cx = w / 2; const cy = h / 2; const R = Math.min(w, h) * 0.42; const an = t * 1.2;
  c.strokeStyle = a(p[0], 0.22); for (let k = 1; k <= 3; k++) { c.beginPath(); c.arc(cx, cy, R * k / 3, 0, 7); c.stroke(); }
  if (c.createConicGradient) { const g = c.createConicGradient(an, cx, cy); g.addColorStop(0, a(p[0], 0.4)); g.addColorStop(0.1, a(p[0], 0)); g.addColorStop(1, a(p[0], 0)); c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R, 0, 7); c.fill(); }
  c.font = '11px "Chakra Petch", sans-serif';
  list.forEach((k, i) => { const ba = (i / list.length) * 6.28 + 0.4; const br = R * (k.picked ? 0.35 : 0.62 + (i % 2) * 0.2); const since = ((an - ba) % 6.28 + 6.28) % 6.28; const glow = Math.max(0, 1 - since / 2.2);
    const x = cx + br * Math.cos(ba); const yy = cy + br * Math.sin(ba);
    c.fillStyle = a(k.picked ? p[1] : k.chg < 0 ? p[2] : p[0], 0.35 + glow * 0.65); c.beginPath(); c.arc(x, yy, (k.picked ? 6 : 4) + glow * 3 + (k.picked ? e * 4 : 0), 0, 7); c.fill();
    c.fillStyle = a('#ffffff', 0.55 + glow * 0.45); c.fillText(`$${k.sym}${k.chg != null ? ` ${k.chg >= 0 ? '+' : ''}${Math.round(k.chg)}%` : ''}`, x + 9, yy + 4); });
}
coins.ready = d => (d.coins || []).length > 0;

function talk(c, s) {   // both minds' own words, newest rising from the bottom, each in its mind's colour
  const { w, h, t, p, data } = s; const lines = data.talk.slice(-7); c.font = '12.5px Sora, sans-serif';
  const drift = (t * 6) % 22;
  lines.forEach((m, i) => { const k = lines.length - 1 - i; const y = h - 18 - k * 34 - drift * (k === 0 ? 0 : 0.2); const col = p[m.mind % 3];
    const txt = String(m.text || '').replace(/\s+/g, ' '); const max = Math.floor((w - 70) / 7); const shown = txt.length > max ? `${txt.slice(0, max - 1)}…` : txt;
    c.globalAlpha = Math.max(0.15, 1 - k * 0.14); c.fillStyle = a(col, 0.18); c.fillRect(m.mind ? w * 0.18 : 8, y - 15, Math.min(w * 0.8, c.measureText(shown).width + 54), 24);
    c.fillStyle = col; c.font = 'bold 10px "JetBrains Mono", monospace'; c.fillText(m.mind ? 'B' : 'A', (m.mind ? w * 0.18 : 8) + 8, y + 1);
    c.fillStyle = '#ffffff'; c.font = '12.5px Sora, sans-serif'; c.fillText(shown, (m.mind ? w * 0.18 : 8) + 26, y + 1); });
  c.globalAlpha = 1;
}
talk.ready = d => (d.talk || []).length > 0;

function steps(c, s) {   // the real steps its windows took, as a scanning log; the newest step is lit
  const { w, h, t, p, e, data } = s; const rh = Math.max(15, (h - 30) / 10); const rows = data.steps.slice(-Math.max(1, Math.min(10, Math.floor((h - 8) / rh)))); c.font = '11px "JetBrains Mono", monospace';
  const by = ((t * 0.3) % 1) * h;
  rows.forEach((r, i) => { const y = 16 + i * rh; const last = i === rows.length - 1; const read = y < by || last;
    c.fillStyle = a(last ? p[1] : '#ffffff', last ? 0.95 : read ? 0.6 : 0.3); const txt = `${r.mind != null ? 'AB'[r.mind] || '·' : '·'}  ${String(r.text || '').replace(/\s+/g, ' ')}`;
    c.fillText(txt.length > (w - 20) / 6.6 ? `${txt.slice(0, Math.floor((w - 20) / 6.6) - 1)}…` : txt, 12, y);
    if (last) { c.fillStyle = a(p[1], 0.18 + e * 0.4); c.fillRect(4, y - 12, w - 8, 17); } });
  const g = c.createLinearGradient(0, by - 26, 0, by); g.addColorStop(0, a(p[0], 0)); g.addColorStop(1, a(p[0], 0.22)); c.fillStyle = g; c.fillRect(0, by - 26, w, 26);
}
steps.ready = d => (d.steps || []).length > 0;

function meter(c, s) {   // what this run has really cost and done, sampled every poll: spend (area) and steps (bars)
  const { w, h, p, e, data } = s; const ser = data.series; const n = ser.length; const maxU = Math.max(...ser.map(x => x.spent), 1e-6); const maxS = Math.max(...ser.map(x => x.steps), 1);
  const bw = w / Math.max(n, 2);
  ser.forEach((x, i) => { const bh = (x.steps / maxS) * h * 0.35; c.fillStyle = a(p[0], 0.25 + (i / n) * 0.5); c.fillRect(i * bw + 1, h - bh, Math.max(1, bw - 2), bh); });
  c.beginPath(); c.moveTo(0, h); ser.forEach((x, i) => c.lineTo(i * bw + bw / 2, h * 0.92 - (x.spent / maxU) * h * 0.7)); c.lineTo(w, h); c.closePath();
  const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, a(p[1], 0.45)); g.addColorStop(1, a(p[1], 0)); c.fillStyle = g; c.fill();
  c.strokeStyle = p[1]; c.lineWidth = 2; c.beginPath(); ser.forEach((x, i) => { const yy = h * 0.92 - (x.spent / maxU) * h * 0.7; i ? c.lineTo(i * bw + bw / 2, yy) : c.moveTo(bw / 2, yy); }); c.stroke(); c.lineWidth = 1;
  const last = ser[n - 1]; c.fillStyle = '#fff'; c.font = 'bold 12px "JetBrains Mono", monospace'; c.textAlign = 'right';
  c.fillText(`$${last.spent.toFixed(4)} · ${last.steps} steps`, w - 10, 20); c.textAlign = 'start';
  c.fillStyle = a(p[1], 0.3 + e * 0.6); c.beginPath(); c.arc(w - bw / 2, h * 0.92 - (last.spent / maxU) * h * 0.7, 4 + e * 5, 0, 7); c.fill();
}
meter.ready = d => (d.series || []).length > 1;

function roe(c, s) {   // PoP: the paper position's real return over this run, against zero
  const { w, h, p, e, data } = s; const v = data.roe; const lo = Math.min(0, ...v); const hi = Math.max(0, ...v); const span = hi - lo || 1;
  const y = x => h * 0.88 - ((x - lo) / span) * h * 0.72; const z = y(0);
  c.strokeStyle = a('#ffffff', 0.3); c.setLineDash([4, 4]); c.beginPath(); c.moveTo(0, z); c.lineTo(w, z); c.stroke(); c.setLineDash([]);
  c.lineWidth = 2.5; c.strokeStyle = v[v.length - 1] >= 0 ? p[0] : p[2]; c.beginPath(); v.forEach((x, i) => { const xx = (i / Math.max(1, v.length - 1)) * w; i ? c.lineTo(xx, y(x)) : c.moveTo(xx, y(x)); }); c.stroke(); c.lineWidth = 1;
  const last = v[v.length - 1]; c.fillStyle = '#fff'; c.font = `bold ${Math.round(h * 0.16)}px "JetBrains Mono", monospace`; c.textAlign = 'center';
  c.globalAlpha = 0.9; c.fillText(`${last >= 0 ? '+' : ''}${last.toFixed(1)}%`, w / 2, h * 0.3 + e * 4); c.globalAlpha = 1; c.textAlign = 'start';
}
roe.ready = d => (d.roe || []).length > 1;

function score(c, s) {   // PoB: the real game score it is watching, and its pick
  const { w, h, p, e, data } = s; const g = data.game; c.textAlign = 'center';
  c.font = '600 13px "Chakra Petch", sans-serif'; c.fillStyle = a('#ffffff', 0.7); c.fillText(g.home || 'HOME', w * 0.28, h * 0.22); c.fillText(g.away || 'AWAY', w * 0.72, h * 0.22);
  c.font = `bold ${Math.round(h * 0.3)}px "JetBrains Mono", monospace`;
  [[g.hs, w * 0.28, p[0]], [g.as, w * 0.72, p[2]]].forEach(([n, x, col]) => { c.fillStyle = a(col, 0.16); c.fillRect(x - w * 0.15, h * 0.3, w * 0.3, h * 0.4); c.fillStyle = col; c.fillText(n == null ? '–' : String(n), x, h * 0.6); });
  if (g.clock) { c.font = '12px "JetBrains Mono", monospace'; c.fillStyle = '#fff'; c.fillText(g.clock, w / 2, h * 0.52); }
  if (g.pick) { c.font = '600 12px Sora, sans-serif'; c.fillStyle = a(p[1], 0.85 + e * 0.15); c.fillText(`its pick: ${g.pick}`, w / 2, h * 0.85); }
  c.textAlign = 'start';
}
score.ready = d => !!(d.game && (d.game.hs != null || d.game.home));

// which real-data scenes each proof tries, in order (only the ones whose data exists are shown)
export const SCENES = {
  pow: [price, coins, talk, steps, meter],
  pop: [roe, price, talk, steps, meter],
  pob: [score, talk, steps, meter],
  poc: [talk, steps, meter],
  poe: [talk, steps, meter],
  pos: [steps, talk, meter],
  work: [steps, talk, meter],
};

// ── FOREGROUNDS (shared) ──────────────────────────────────────────────────────────────────────────────────────────
const FG = [
  function sparks(c, s) {   // bursts on each new step
    const { w, h, t, p, e } = s; if (e < 0.05) return;
    for (let i = 0; i < 26; i++) { const an = s.r[i] * 6.28; const r = (1 - e) * 140 * (0.4 + s.r[i + 26]); c.fillStyle = a(p[i % 3], e); c.fillRect(w / 2 + r * Math.cos(an + t * 0.1), h / 2 + r * Math.sin(an + t * 0.1), 2.5, 2.5); }
  },
  function scan(c, s) {   // horizontal scanline sweep
    const { w, h, t, p } = s; const y = ((t * 0.2) % 1) * h; const g = c.createLinearGradient(0, y - 40, 0, y); g.addColorStop(0, a(p[1], 0)); g.addColorStop(1, a(p[1], 0.18)); c.fillStyle = g; c.fillRect(0, y - 40, w, 40);
  },
  function bokeh(c, s) {   // soft drifting lights (drawn as radial fills, never a blur filter)
    const { w, h, t, p } = s;
    for (let i = 0; i < 8; i++) { const x = (s.r[i] * w + t * 8 * (i % 2 ? 1 : -1)) % w; const y = s.r[i + 8] * h + Math.sin(t * 0.5 + i) * 12; const R = 18 + s.r[i + 16] * 26;
      const g = c.createRadialGradient(x, y, 0, x, y, R); g.addColorStop(0, a(p[i % 3], 0.16)); g.addColorStop(1, a(p[i % 3], 0)); c.fillStyle = g; c.beginPath(); c.arc(x < 0 ? x + w : x, y, R, 0, 7); c.fill(); }
  },
  function pulses(c, s) {   // ring pulses out of the centre
    const { w, h, t, p, e } = s;
    for (let k = 0; k < 3; k++) { const ph = (t * 0.35 + k / 3) % 1; c.strokeStyle = a(p[0], (1 - ph) * (0.25 + e * 0.5)); c.lineWidth = 2; c.beginPath(); c.arc(w / 2, h / 2, ph * Math.max(w, h) * 0.55, 0, 7); c.stroke(); }
    c.lineWidth = 1;
  },
];

// the look of a run: background × foreground × palette picked from its id (40 per proof); its scenes are whichever real-data views
// the run can fill right now, rotating every ROTATE seconds.
export const LOOKS_PER_PROOF = BG.length * FG.length * 2;
export const ROTATE = 18;
export function pickLook(kind, seed) {
  const r = seeded(`${kind}:${seed}`);
  return { bg: Math.floor(r() * BG.length), scene: Math.floor(r() * 5), fg: Math.floor(r() * FG.length), pal: Math.floor(r() * 2) };
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
  // 🐞 2026-11-14: the data scene draws only in the open band between the step row and the vitals (its ENTRY / price labels used to land
  // under the vitals and the chat line); backgrounds + foregrounds still fill the whole stage
  const [y0, y1] = band && band[1] - band[0] >= 60 ? band : [0, h];
  ctx.save(); if (y0 > 0 || y1 < h) { ctx.translate(0, y0); ctx.beginPath(); ctx.rect(0, 0, w, y1 - y0); ctx.clip(); s.h = y1 - y0; }
  if (list.length) { const step = Math.floor(t / ROTATE); const into = (t % ROTATE) / ROTATE; const cur = list[(look.scene + step) % list.length];
    if (into < 0.06 && step > 0 && list.length > 1) { ctx.globalAlpha = 1 - into / 0.06; list[(look.scene + step - 1) % list.length](ctx, s); ctx.globalAlpha = into / 0.06; }
    cur(ctx, s); ctx.globalAlpha = 1; name = cur.name; }
  ctx.restore(); s.h = h;
  FG[look.fg % FG.length](ctx, s);
  return { scene: name, bg: BG[look.bg % BG.length].name, fg: FG[look.fg % FG.length].name };
}

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

// ── SCENES (per proof) ─────────────────────────────────────────────────────────────────────────────────────────────
function candles(c, s) {   // live candles streaming left, the last one breathing
  const { w, h, t, p, e } = s; const n = 34; const bw = w / n; let v = 0.5;
  for (let i = 0; i < n + 1; i++) { const k = Math.floor(t * 1.4) + i; const r1 = Math.sin(k * 12.9898) * 43758.5453 % 1; const r2 = Math.sin(k * 78.233) * 12543.21 % 1;
    const o = v; v = Math.max(0.15, Math.min(0.85, v + (r1 - 0.48) * 0.12 * (1 + e))); const hi = Math.max(o, v) + Math.abs(r2) * 0.06; const lo = Math.min(o, v) - Math.abs(r1) * 0.06;
    const x = i * bw - ((t * 1.4) % 1) * bw; const up = v >= o; c.strokeStyle = c.fillStyle = up ? p[0] : p[2];
    c.globalAlpha = 0.35 + 0.6 * (i / n); c.beginPath(); c.moveTo(x + bw / 2, h * (1 - hi)); c.lineTo(x + bw / 2, h * (1 - lo)); c.stroke();
    c.fillRect(x + bw * 0.2, h * (1 - Math.max(o, v)), bw * 0.6, Math.max(2, h * Math.abs(v - o))); }
  c.globalAlpha = 1;
}
function radar(c, s) {   // radar sweep with blips that flare on energy
  const { w, h, t, p, e } = s; const cx = w / 2; const cy = h / 2; const R = Math.min(w, h) * 0.42; const an = t * 1.6;
  c.strokeStyle = a(p[0], 0.25); for (let k = 1; k <= 4; k++) { c.beginPath(); c.arc(cx, cy, R * k / 4, 0, 7); c.stroke(); }
  const g = c.createConicGradient ? c.createConicGradient(an, cx, cy) : null;
  if (g) { g.addColorStop(0, a(p[0], 0.45)); g.addColorStop(0.12, a(p[0], 0)); g.addColorStop(1, a(p[0], 0)); c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R, 0, 7); c.fill(); }
  for (let i = 0; i < 14; i++) { const ba = s.r[i] * 6.28; const br = R * (0.2 + s.r[i + 14] * 0.8); const since = ((an - ba) % 6.28 + 6.28) % 6.28; const glow = Math.max(0, 1 - since / 2.5);
    c.fillStyle = a(i % 4 ? p[1] : p[2], 0.15 + glow * 0.85); c.beginPath(); c.arc(cx + br * Math.cos(ba), cy + br * Math.sin(ba), 2 + glow * 3 + e * 3, 0, 7); c.fill(); }
}
function orbit(c, s) {   // coins orbiting the one being researched
  const { w, h, t, p, e } = s; const cx = w / 2; const cy = h / 2;
  c.fillStyle = a(p[1], 0.9); c.beginPath(); c.arc(cx, cy, 10 + e * 6, 0, 7); c.fill();
  for (let r = 0; r < 3; r++) { const R = 46 + r * 38; c.strokeStyle = a(p[0], 0.18); c.beginPath(); c.ellipse(cx, cy, R * 1.6, R * 0.6, -0.25, 0, 7); c.stroke();
    for (let k = 0; k < 3 + r; k++) { const an = t * (0.6 - r * 0.15) + k * 6.28 / (3 + r); const x = cx + R * 1.6 * Math.cos(an) * Math.cos(-0.25) - R * 0.6 * Math.sin(an) * Math.sin(-0.25);
      const y = cy + R * 1.6 * Math.cos(an) * Math.sin(-0.25) + R * 0.6 * Math.sin(an) * Math.cos(-0.25); c.fillStyle = a(k % 2 ? p[0] : p[2], 0.85); c.beginPath(); c.arc(x, y, 4 + (Math.sin(an) + 1) * 2, 0, 7); c.fill(); } }
}
function depth(c, s) {   // order-book mountains (bids / asks) breathing
  const { w, h, t, p, e } = s; const mid = w / 2;
  [[p[0], -1], [p[2], 1]].forEach(([col, dir]) => { c.fillStyle = a(col, 0.28); c.strokeStyle = a(col, 0.9); c.beginPath(); c.moveTo(mid, h);
    let y = h * 0.92; for (let x = 0; x <= mid; x += 8) { y -= (0.6 + Math.sin(x / 30 + t * 2 * dir) * 0.5 + e) * 1.4; c.lineTo(mid + dir * x, Math.max(h * 0.15, y)); }
    c.lineTo(mid + dir * mid, h); c.closePath(); c.fill(); c.stroke(); });
  c.fillStyle = a(p[1], 0.8); c.fillRect(mid - 1, h * 0.1, 2, h * 0.9);
}
function scanner(c, s) {   // a page being read: lines of text with a scanning beam
  const { w, h, t, p, e } = s; const by = ((t * 0.35) % 1) * h;
  for (let y = 18; y < h; y += 14) { const len = (0.3 + (Math.sin(y * 3.1) + 1) * 0.3) * w * 0.8; const read = y < by;
    c.fillStyle = a(read ? p[1] : '#ffffff', read ? 0.35 : 0.08); c.fillRect(w * 0.1, y, len, 4); }
  const g = c.createLinearGradient(0, by - 30, 0, by + 4); g.addColorStop(0, a(p[0], 0)); g.addColorStop(1, a(p[0], 0.35 + e * 0.4)); c.fillStyle = g; c.fillRect(0, by - 30, w, 34);
}
function book(c, s) {   // live order book rows flashing
  const { w, h, t, p } = s; const rows = 14; const rh = h / rows;
  for (let i = 0; i < rows; i++) { const ask = i < rows / 2; const v = 0.2 + Math.abs(Math.sin(i * 1.7 + Math.floor(t * 3) * 0.6)) * 0.75;
    c.fillStyle = a(ask ? p[2] : p[0], 0.22); c.fillRect(ask ? w - w * 0.45 * v : 0, i * rh + 2, w * 0.45 * v, rh - 4);
    c.fillStyle = a('#ffffff', 0.35); c.font = '10px "JetBrains Mono", monospace'; c.fillText((84.8 + (rows / 2 - i) * 0.03).toFixed(2), w / 2 - 18, i * rh + rh * 0.68); }
}
function ribbon(c, s) {   // price ribbon with liquidation sparks
  const { w, h, t, p, e } = s; c.lineWidth = 2;
  for (let band = 0; band < 3; band++) { c.strokeStyle = a(p[band], 0.7 - band * 0.2); c.beginPath();
    for (let x = 0; x <= w; x += 6) { const y = h * (0.5 + 0.2 * Math.sin(x / 90 + t * 0.9 + band * 0.4) + 0.06 * Math.sin(x / 23 - t * 2) * (1 + e)); x ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke(); }
  for (let i = 0; i < 6; i++) { const ph = (t * 0.5 + s.r[i]) % 1; c.fillStyle = a(p[2], 1 - ph); c.beginPath(); c.arc(s.r[i + 6] * w, h * (0.3 + s.r[i + 12] * 0.4) - ph * 30, 2 + ph * 4, 0, 7); c.fill(); }
}
function heat(c, s) {   // funding heatmap cells
  const { w, h, t, p } = s; const cols = 18; const rows = 9; const cw = w / cols; const ch = h / rows;
  for (let x = 0; x < cols; x++) for (let y = 0; y < rows; y++) { const v = (Math.sin(x * 0.7 + t) + Math.cos(y * 0.9 - t * 0.6) + 2) / 4;
    c.fillStyle = a(v > 0.5 ? p[0] : p[2], Math.abs(v - 0.5) * 1.1); c.fillRect(x * cw + 1, y * ch + 1, cw - 2, ch - 2); }
}
function tug(c, s) {   // long vs short tug of war meter
  const { w, h, t, p, e } = s; const k = 0.5 + 0.18 * Math.sin(t * 0.7) + 0.08 * Math.sin(t * 2.3) * (1 + e);
  c.fillStyle = a(p[0], 0.5); c.fillRect(w * 0.1, h * 0.45, w * 0.8 * k, h * 0.1); c.fillStyle = a(p[2], 0.5); c.fillRect(w * 0.1 + w * 0.8 * k, h * 0.45, w * 0.8 * (1 - k), h * 0.1);
  c.fillStyle = '#fff'; c.fillRect(w * 0.1 + w * 0.8 * k - 1, h * 0.38, 3, h * 0.24);
  for (let i = 0; i < 20; i++) { const side = i % 2; const ph = (t * 0.8 + s.r[i]) % 1; c.fillStyle = a(side ? p[2] : p[0], 1 - ph);
    c.fillRect(side ? w * 0.9 - ph * w * 0.3 : w * 0.1 + ph * w * 0.3, h * (0.3 + s.r[i + 20] * 0.4), 3, 3); }
}
function field(c, s) {   // a pitch with ball arcs
  const { w, h, t, p, e } = s; c.strokeStyle = a(p[2], 0.35); c.lineWidth = 1.5; c.strokeRect(w * 0.08, h * 0.15, w * 0.84, h * 0.7);
  c.beginPath(); c.moveTo(w / 2, h * 0.15); c.lineTo(w / 2, h * 0.85); c.stroke(); c.beginPath(); c.arc(w / 2, h / 2, h * 0.12, 0, 7); c.stroke();
  for (let i = 0; i < 4; i++) { const ph = (t * 0.45 + i / 4) % 1; const x0 = w * (0.15 + s.r[i] * 0.3); const x1 = w * (0.55 + s.r[i + 4] * 0.3);
    const x = x0 + (x1 - x0) * ph; const y = h * 0.7 - Math.sin(ph * Math.PI) * h * (0.35 + e * 0.1); c.fillStyle = a(p[1], 1 - ph * 0.6); c.beginPath(); c.arc(x, y, 3.5, 0, 7); c.fill(); }
}
function flip(c, s) {   // scoreboard digits flipping
  const { w, h, t, p } = s; c.font = `bold ${Math.round(h * 0.28)}px "JetBrains Mono", monospace`; c.textAlign = 'center';
  const a1 = Math.floor(t / 3) % 40; const b1 = Math.floor(t / 4.3) % 40;
  [[a1, w * 0.3, p[0]], [b1, w * 0.7, p[2]]].forEach(([n, x, col]) => { c.fillStyle = a(col, 0.18); c.fillRect(x - w * 0.14, h * 0.28, w * 0.28, h * 0.44); c.fillStyle = col; c.fillText(String(n).padStart(2, '0'), x, h * 0.6); });
  c.fillStyle = a('#ffffff', 0.5); c.fillText(':', w / 2, h * 0.58); c.textAlign = 'start';
}
function prob(c, s) {   // the win chance curve redrawing
  const { w, h, t, p, e } = s; c.lineWidth = 2.5; c.strokeStyle = p[1]; c.beginPath();
  for (let x = 0; x <= w; x += 5) { const y = h * (0.5 - 0.3 * Math.tanh((x / w - 0.5) * 4 + Math.sin(t * 0.6) * 1.5) + 0.03 * Math.sin(x / 15 + t * 3) * (1 + e)); x ? c.lineTo(x, y) : c.moveTo(x, y); }
  c.stroke(); c.fillStyle = a(p[0], 0.08); c.lineTo(w, h); c.lineTo(0, h); c.fill();
}
function crowd(c, s) {   // the crowd doing the wave
  const { w, h, t, p } = s;
  for (let r = 0; r < 6; r++) for (let x = 0; x < w; x += 10) { const lift = Math.max(0, Math.sin(x / 40 - t * 3 + r * 0.6)) * 8; c.fillStyle = a(r % 2 ? p[0] : p[1], 0.25 + lift / 20);
    c.beginPath(); c.arc(x + (r % 2) * 5, h * 0.4 + r * 14 - lift, 3, 0, 7); c.fill(); }
}
function clock(c, s) {   // game clock ring counting down
  const { w, h, t, p, e } = s; const cx = w / 2; const cy = h / 2; const R = Math.min(w, h) * 0.32; const k = 1 - ((t / 40) % 1);
  c.lineWidth = 8; c.strokeStyle = a(p[0], 0.15); c.beginPath(); c.arc(cx, cy, R, 0, 7); c.stroke();
  c.strokeStyle = p[1]; c.beginPath(); c.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + 6.283 * k); c.stroke();
  c.fillStyle = a(p[2], 0.6 + e * 0.4); c.beginPath(); c.arc(cx + R * Math.cos(-Math.PI / 2 + 6.283 * k), cy + R * Math.sin(-Math.PI / 2 + 6.283 * k), 6, 0, 7); c.fill(); c.lineWidth = 1;
}
function glyphs(c, s) {   // words raining into a draft
  const { w, h, t, p } = s; const words = ['hook', 'viral', 'thread', 'POV', 'reels', 'clip', 'trend', 'post', 'caption', 'loop', 'drop', 'reply'];
  c.font = '13px Sora, sans-serif';
  for (let i = 0; i < 26; i++) { const ph = (t * (0.08 + s.r[i] * 0.1) + s.r[i + 26]) % 1; c.fillStyle = a(p[i % 3], 0.9 - ph * 0.8); c.fillText(words[i % words.length], s.r[i + 52] * (w - 60), ph * h); }
}
function wave(c, s) {   // audio waveform bars
  const { w, h, t, p, e } = s; const n = 48; const bw = w / n;
  for (let i = 0; i < n; i++) { const v = Math.abs(Math.sin(i * 0.4 + t * 4) * Math.sin(i * 0.13 - t * 1.3)) * (0.6 + e * 0.4); c.fillStyle = a(p[i % 2], 0.7);
    c.fillRect(i * bw + 1, h / 2 - v * h * 0.4, bw - 2, v * h * 0.8); }
}
function splash(c, s) {   // ink bursts
  const { w, h, t, p } = s;
  for (let b = 0; b < 4; b++) { const ph = (t * 0.3 + b / 4) % 1; const cx = s.r[b] * w; const cy = s.r[b + 4] * h;
    for (let k = 0; k < 14; k++) { const an = k / 14 * 6.28 + b; const r = ph * 70; c.fillStyle = a(p[b % 3], (1 - ph) * 0.8); c.beginPath(); c.arc(cx + r * Math.cos(an), cy + r * Math.sin(an), 3 * (1 - ph) + 1, 0, 7); c.fill(); } }
}
function ticker(c, s) {   // trending tape scrolling
  const { w, h, t, p } = s; const items = ['#1 TRENDING', '+412% views', 'HOOK 0:02', 'SAVE RATE 9%', 'CTR 6.1%', 'SHARES ↑', 'WATCH 71%'];
  c.font = 'bold 14px "Chakra Petch", sans-serif';
  for (let r = 0; r < 4; r++) { let x = -((t * (40 + r * 18)) % 900); const y = h * (0.2 + r * 0.2);
    for (let k = 0; x < w; k++) { const txt = items[(k + r) % items.length]; c.fillStyle = a(p[(k + r) % 3], 0.75); c.fillText(txt, x, y); x += c.measureText(txt).width + 40; } }
}
function typing(c, s) {   // a draft typing itself
  const { w, h, t, p } = s; const lines = 9; const at = (t * 0.9) % lines;
  for (let i = 0; i < lines; i++) { const len = i < Math.floor(at) ? 1 : i === Math.floor(at) ? at % 1 : 0; const full = (0.4 + ((i * 37) % 50) / 100) * w * 0.8;
    c.fillStyle = a('#ffffff', 0.5); c.fillRect(w * 0.1, h * 0.15 + i * h * 0.08, full * len, 5);
    if (i === Math.floor(at)) { c.fillStyle = p[0]; c.fillRect(w * 0.1 + full * len + 3, h * 0.15 + i * h * 0.08 - 4, 2, 13); } }
}
function stacks(c, s) {   // coin stacks rising (savings)
  const { w, h, t, p, e } = s;
  for (let i = 0; i < 7; i++) { const n = Math.floor(4 + (Math.sin(t * 0.5 + i) + 1) * 4 + e * 3); const x = w * (0.15 + i * 0.11);
    for (let k = 0; k < n; k++) { c.fillStyle = a(k % 2 ? p[1] : p[0], 0.75); c.beginPath(); c.ellipse(x, h * 0.85 - k * 7, 16, 5, 0, 0, 7); c.fill(); } }
}
function ring(c, s) {   // goal ring filling
  const { w, h, t, p, e } = s; const cx = w / 2; const cy = h / 2; const R = Math.min(w, h) * 0.3; const k = 0.4 + 0.35 * ((Math.sin(t * 0.3) + 1) / 2);
  c.lineWidth = 12; c.strokeStyle = a(p[0], 0.15); c.beginPath(); c.arc(cx, cy, R, 0, 7); c.stroke();
  c.strokeStyle = p[0]; c.beginPath(); c.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + 6.283 * k); c.stroke();
  c.lineWidth = 1; c.fillStyle = '#fff'; c.font = `bold ${Math.round(R * 0.45)}px "JetBrains Mono", monospace`; c.textAlign = 'center'; c.fillText(`${Math.round(k * 100)}%`, cx, cy + R * 0.15); c.textAlign = 'start';
  for (let i = 0; i < 10; i++) { const ph = (t * 0.6 + s.r[i]) % 1; c.fillStyle = a(p[1], (1 - ph) * (0.5 + e)); c.fillRect(cx + (s.r[i + 10] - 0.5) * R * 2, cy + R + 20 - ph * R * 2.4, 3, 3); }
}
function pipes(c, s) {   // money flowing through pipes into buckets
  const { w, h, t, p } = s; c.lineWidth = 6;
  for (let i = 0; i < 3; i++) { const y = h * (0.3 + i * 0.2); c.strokeStyle = a(p[i], 0.2); c.beginPath(); c.moveTo(0, y); c.bezierCurveTo(w * 0.4, y, w * 0.6, h * 0.85, w * (0.3 + i * 0.2), h * 0.9); c.stroke();
    for (let k = 0; k < 5; k++) { const ph = (t * 0.4 + k / 5 + i * 0.1) % 1; const x = (1 - ph) ** 3 * 0 + 3 * (1 - ph) ** 2 * ph * w * 0.4 + 3 * (1 - ph) * ph * ph * w * 0.6 + ph ** 3 * w * (0.3 + i * 0.2);
      const yy = (1 - ph) ** 3 * y + 3 * (1 - ph) ** 2 * ph * y + 3 * (1 - ph) * ph * ph * h * 0.85 + ph ** 3 * h * 0.9; c.fillStyle = p[i]; c.beginPath(); c.arc(x, yy, 4, 0, 7); c.fill(); } }
  c.lineWidth = 1;
}
function calendar(c, s) {   // the month ticking bills off
  const { w, h, t, p } = s; const cw = w / 7.5; const ch = h / 6; const today = Math.floor(t / 1.2) % 30;
  for (let d = 0; d < 30; d++) { const x = w * 0.04 + (d % 7) * cw; const y = h * 0.1 + Math.floor(d / 7) * ch; const done = d < today;
    c.strokeStyle = a(p[0], 0.3); c.strokeRect(x, y, cw - 6, ch - 6); if (done) { c.fillStyle = a(d % 9 === 0 ? p[1] : p[0], d % 9 === 0 ? 0.6 : 0.18); c.fillRect(x + 1, y + 1, cw - 8, ch - 8); }
    if (d === today) { c.strokeStyle = p[2]; c.lineWidth = 2; c.strokeRect(x, y, cw - 6, ch - 6); c.lineWidth = 1; } }
}
function bills(c, s) {   // bill cards sliding to PAID
  const { w, h, t, p } = s;
  for (let i = 0; i < 4; i++) { const ph = (t * 0.25 + i / 4) % 1; const x = w * 0.1 + ph * w * 0.6; const y = h * (0.15 + i * 0.19);
    c.fillStyle = a('#ffffff', 0.08); c.fillRect(x, y, w * 0.28, h * 0.14); c.fillStyle = ph > 0.7 ? p[0] : a('#ffffff', 0.5); c.font = 'bold 11px "JetBrains Mono", monospace';
    c.fillText(ph > 0.7 ? 'PAID ✓' : ['RENT', 'POWER', 'PHONE', 'CARD'][i], x + 10, y + h * 0.085); }
}
function blocks(c, s) {   // wireframe blocks assembling a page
  const { w, h, t, p } = s; const cells = [[0.08, 0.1, 0.84, 0.12], [0.08, 0.26, 0.5, 0.3], [0.62, 0.26, 0.3, 0.3], [0.08, 0.6, 0.26, 0.28], [0.37, 0.6, 0.26, 0.28], [0.66, 0.6, 0.26, 0.28]];
  const at = (t * 0.5) % (cells.length + 2);
  cells.forEach(([x, y, cw, ch], i) => { const k = Math.max(0, Math.min(1, at - i)); c.strokeStyle = a(p[i % 3], 0.3 + k * 0.6); c.strokeRect(x * w, y * h, cw * w * Math.max(0.05, k), ch * h);
    if (k >= 1) { c.fillStyle = a(p[i % 3], 0.1); c.fillRect(x * w, y * h, cw * w, ch * h); } });
}
function code(c, s) {   // code lines scrolling, syntax-colored
  const { w, h, t, p } = s; c.font = '11px "JetBrains Mono", monospace'; const off = (t * 22) % 16;
  for (let i = -1; i < h / 16 + 1; i++) { const n = i + Math.floor(t * 22 / 16); const ind = (n * 7) % 4; let x = 14 + ind * 14;
    for (let k = 0; k < 3 + (n % 4); k++) { const len = 18 + ((n * 13 + k * 29) % 60); c.fillStyle = a(p[(n + k) % 3], 0.55); c.fillRect(x, i * 16 - off + 8, len, 5); x += len + 8; } }
}
function graph(c, s) {   // a node graph wiring itself
  const { w, h, t, p, e } = s; const N = 16; const pts = [];
  for (let i = 0; i < N; i++) pts.push([w * (0.1 + s.r[i] * 0.8) + Math.sin(t * 0.5 + i) * 8, h * (0.1 + s.r[i + N] * 0.8) + Math.cos(t * 0.4 + i) * 8]);
  for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) { const d = Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]); if (d < 130) { c.strokeStyle = a(p[0], (1 - d / 130) * 0.5); c.beginPath(); c.moveTo(...pts[i]); c.lineTo(...pts[j]); c.stroke(); } }
  pts.forEach((q, i) => { c.fillStyle = a(p[i % 3], 0.9); c.beginPath(); c.arc(q[0], q[1], 3 + (i % 4 === Math.floor(t) % 4 ? e * 4 : 0), 0, 7); c.fill(); });
}
function pixels(c, s) {   // a picture building pixel by pixel
  const { w, h, t, p } = s; const sz = 12; const cols = Math.ceil(w / sz); const rows = Math.ceil(h / sz); const at = ((t * 60) % (cols * rows * 1.2));
  for (let i = 0; i < Math.min(at, cols * rows); i++) { const x = (i * 7919) % cols; const y = Math.floor(((i * 7919) / cols)) % rows;
    c.fillStyle = a(p[(x + y) % 3], 0.12 + ((x * y) % 7) / 20); c.fillRect(x * sz, y * sz, sz - 1, sz - 1); }
}
function rulers(c, s) {   // blueprint rulers and measuring
  const { w, h, t, p } = s; c.strokeStyle = a(p[0], 0.3);
  for (let x = 0; x < w; x += 10) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, x % 50 ? 6 : 14); c.stroke(); }
  for (let y = 0; y < h; y += 10) { c.beginPath(); c.moveTo(0, y); c.lineTo(y % 50 ? 6 : 14, y); c.stroke(); }
  const mx = w * (0.3 + 0.4 * ((Math.sin(t * 0.7) + 1) / 2)); c.strokeStyle = p[1]; c.setLineDash([4, 4]); c.beginPath(); c.moveTo(mx, 0); c.lineTo(mx, h); c.stroke(); c.setLineDash([]);
  c.fillStyle = p[1]; c.font = '10px "JetBrains Mono", monospace'; c.fillText(`${Math.round(mx)}px`, mx + 4, 26);
}
function tabs(c, s) {   // browser tabs opening and reading
  const { w, h, t, p } = s; const n = 4;
  for (let i = 0; i < n; i++) { const on = Math.floor(t / 2.5) % n === i; const x = w * 0.06 + i * w * 0.22; c.fillStyle = a(on ? p[0] : '#ffffff', on ? 0.4 : 0.08); c.fillRect(x, h * 0.12, w * 0.2, h * 0.08); }
  scanner(c, { ...s, h: h * 0.75 });
}

export const SCENES = {
  pow: [candles, radar, orbit, depth, scanner],
  pop: [book, ribbon, heat, tug, depth],
  pob: [field, flip, prob, crowd, clock],
  poc: [glyphs, wave, splash, ticker, typing],
  poe: [stacks, ring, pipes, calendar, bills],
  pos: [blocks, code, graph, pixels, rulers],
  work: [graph, tabs, scanner, orbit, code],
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

export const LOOKS_PER_PROOF = BG.length * 5 * FG.length;   // 5 × 5 × 4 = 100

// The look for a run: [bg, scene, fg, palette] indices from its id. The scene steps on every ROTATE seconds.
export const ROTATE = 22;
export function pickLook(kind, seed) {
  const r = seeded(`${kind}:${seed}`);
  return { bg: Math.floor(r() * BG.length), scene: Math.floor(r() * 5), fg: Math.floor(r() * FG.length), pal: Math.floor(r() * 2) };
}

// draw one frame. `prev` (optional) is the scene fading out during a rotation.
export function drawFrame(ctx, { w, h, t, kind, look, energy = 0, rnd }) {
  const k = SCENES[kind] ? kind : 'work'; const p = PALETTES[k][look.pal % PALETTES[k].length];
  const s = { w, h, t, p, e: energy, r: rnd };
  if (!(w > 4 && h > 4)) return { scene: '', bg: '', fg: '' };   // a 0px canvas (hidden / still opening) makes x % w = NaN and the gradients throw
  ctx.clearRect(0, 0, w, h);
  BG[look.bg % BG.length](ctx, s);
  const step = Math.floor(t / ROTATE); const into = (t % ROTATE) / ROTATE; const list = SCENES[k];
  const cur = list[(look.scene + step) % list.length];
  if (into < 0.06 && step > 0) { ctx.globalAlpha = 1 - into / 0.06; list[(look.scene + step - 1) % list.length](ctx, s); ctx.globalAlpha = into / 0.06; }
  cur(ctx, s); ctx.globalAlpha = 1;
  FG[look.fg % FG.length](ctx, s);
  return { scene: cur.name, bg: BG[look.bg % BG.length].name, fg: FG[look.fg % FG.length].name };
}
export const sceneName = (kind, look, t) => { const list = SCENES[SCENES[kind] ? kind : 'work']; return list[(look.scene + Math.floor(t / ROTATE)) % list.length].name; };

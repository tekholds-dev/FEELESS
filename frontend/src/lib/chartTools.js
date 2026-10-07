import { useEffect, useState } from 'react';

// 🧰 CHART TOOLS: auto-drawn trench levels that stay on EVERY chart (PriceChart). One click each, one choice for the whole site
// (localStorage `feeless.chartTools`). All maths are pure and read only the candles on screen: [time, open, high, low, close, vol].
//   🪜 FVG   — fair value gaps still open (a 3-candle jump nobody traded through): price likes to come back and fill them
//   🧲 Magnet — resting liquidity: equal highs / equal lows nobody has taken yet (price gets pulled to them)
//   🔫 Gun line — the trigger: the last swing high still overhead; a close above it = fired (then it is support)
//   🦠 Germ  — where the biggest run on screen was born (its base candle); losing it = the move is dead
//   ⚡ Meta edge — all four at once + one read: score, where it stands, the plan in one line
export const CHART_TOOLS = [['fvg', '🪜', 'FVG', 'Fair value gaps still open — price likes to come back and fill them'],
  ['magnet', '🧲', 'Magnets', 'Equal highs / lows nobody has taken yet — resting liquidity that pulls price'],
  ['gun', '🔫', 'Gun line', 'The trigger: last swing high overhead. A close above = fired'],
  ['germ', '🦠', 'Germ', 'Where the biggest run on screen was born. Losing it = the move is dead'],
  ['edge', '⚡', 'Meta edge', 'All four at once + one read: score, where it stands, the plan']];
const KEY = 'feeless.chartTools';
const IDS = CHART_TOOLS.map(t => t[0]);
const subs = new Set();
let cur = null;
export const getChartTools = () => { if (cur) return cur; try { const v = JSON.parse(window.localStorage.getItem(KEY) || '[]'); cur = Array.isArray(v) ? v.filter(x => IDS.includes(x)) : []; } catch { cur = []; } return cur; };
export const toggleChartTool = id => { if (!IDS.includes(id)) return; const v = getChartTools(); cur = v.includes(id) ? v.filter(x => x !== id) : [...v, id];
  try { window.localStorage.setItem(KEY, JSON.stringify(cur)); } catch { /* private window: lasts for this visit */ } subs.forEach(f => f(cur)); };
export function useChartTools() { const [v, setV] = useState(getChartTools); useEffect(() => { subs.add(setV); setV(getChartTools()); return () => { subs.delete(setV); }; }, []); return v; }

const T = 0, O = 1, H = 2, L = 3, C = 4;
const WINDOW = 120;
const win = cs => (cs || []).filter(c => c && c[H] > 0 && c[L] > 0).slice(-WINDOW);

// swing points: a high (low) no candle within k bars on either side beats
export function swings(cs, k = 2) {
  const hi = []; const lo = [];
  for (let i = k; i < cs.length - k; i++) {
    let isH = true; let isL = true;
    for (let j = i - k; j <= i + k; j++) { if (j === i) continue; if (cs[j][H] >= cs[i][H]) isH = false; if (cs[j][L] <= cs[i][L]) isL = false; }
    if (isH) hi.push({ i, time: cs[i][T], price: cs[i][H] }); if (isL) lo.push({ i, time: cs[i][T], price: cs[i][L] });
  }
  return { hi, lo };
}

// 🪜 open fair value gaps, newest first (≤ max). A later candle trading into a gap shrinks it; through it = filled = gone.
export function fvgs(candles, { minPct = 0.4, max = 3 } = {}) {
  const cs = win(candles); const out = [];
  for (let i = 2; i < cs.length; i++) {
    const a = cs[i - 2]; const b = cs[i]; let g = null;
    if (b[L] > a[H]) g = { dir: 'up', bot: a[H], top: b[L] }; else if (b[H] < a[L]) g = { dir: 'down', bot: b[H], top: a[L] };
    if (!g || (g.top - g.bot) / g.bot * 100 < minPct) continue;
    for (let j = i + 1; j < cs.length && g.top > g.bot; j++) { if (g.dir === 'up') g.top = Math.min(g.top, Math.max(cs[j][L], g.bot)); else g.bot = Math.max(g.bot, Math.min(cs[j][H], g.top)); }
    if ((g.top - g.bot) / g.bot * 100 >= minPct / 2) out.push({ ...g, mid: (g.top + g.bot) / 2, time: cs[i - 1][T] });
  }
  return out.reverse().slice(0, max);
}

// 🧲 resting liquidity: swing highs above / swing lows below the last close that no later candle has taken, clustered within
// `tol`% (2+ touches = equal highs / lows = a strong magnet). Nearest two each side.
export function magnets(candles, { tol = 0.8 } = {}) {
  const cs = win(candles); if (cs.length < 8) return [];
  const last = cs[cs.length - 1][C]; const { hi, lo } = swings(cs);
  const live = (pts, side) => pts.filter(p => { for (let j = p.i + 1; j < cs.length; j++) { if (side === 'above' ? cs[j][H] > p.price : cs[j][L] < p.price) return false; } return side === 'above' ? p.price > last : p.price < last; });
  const cluster = (pts, side) => { const s = [...pts].sort((a, b) => a.price - b.price); const g = [];
    s.forEach(p => { const c = g[g.length - 1]; if (c && (p.price - c.price) / c.price * 100 <= tol) { c.hits += 1; c.price = side === 'above' ? Math.max(c.price, p.price) : Math.min(c.price, p.price); } else g.push({ price: p.price, hits: 1 }); });
    return g.map(x => ({ ...x, side, distPct: (x.price / last - 1) * 100 })).sort((a, b) => Math.abs(a.distPct) - Math.abs(b.distPct)).slice(0, 2); };
  return [...cluster(live(hi, 'above'), 'above'), ...cluster(live(lo, 'below'), 'below')];
}

// 🔫 the trigger: the nearest swing high still above the last close. None overhead → the last one it broke = fired (support now).
export function gunLine(candles) {
  const cs = win(candles); if (cs.length < 8) return null;
  const last = cs[cs.length - 1][C]; const { hi } = swings(cs); if (!hi.length) return null;
  const over = hi.filter(p => p.price > last).sort((a, b) => b.i - a.i)[0];
  if (over) return { price: over.price, fired: false, distPct: (over.price / last - 1) * 100 };
  const under = hi.sort((a, b) => b.i - a.i)[0];
  return { price: under.price, fired: true, distPct: (under.price / last - 1) * 100 };
}

// 🦠 where the biggest run on screen was born: the base candle of the largest low → high move inside `span` bars (≥ minRun %).
export function germ(candles, { span = 12, minRun = 15 } = {}) {
  const cs = win(candles); let best = null;
  for (let i = 0; i < cs.length - 1; i++) for (let j = i + 1; j <= Math.min(cs.length - 1, i + span); j++) { const run = (cs[j][H] / cs[i][L] - 1) * 100; if (!best || run > best.runPct) best = { i, runPct: run }; }
  if (!best || best.runPct < minRun) return null;
  const c = cs[best.i]; const last = cs[cs.length - 1][C];
  return { bot: c[L], top: Math.max(c[O], c[C]), time: c[T], runPct: best.runPct, lost: last < c[L] };
}

// ⚡ one read from everything above. A reading of the candles on screen — never a forecast.
export function edgeRead(candles) {
  const cs = win(candles); if (cs.length < 12) return null;
  const last = cs[cs.length - 1][C]; const hi = Math.max(...cs.map(c => c[H])); const lo = Math.min(...cs.map(c => c[L]));
  const pos = hi > lo ? (last - lo) / (hi - lo) : 0.5; const pull = (1 - last / hi) * 100;
  const sw = swings(cs); const h2 = sw.hi.slice(-2); const l2 = sw.lo.slice(-2);
  const up = h2.length === 2 && l2.length === 2 && h2[1].price > h2[0].price && l2[1].price > l2[0].price;
  const down = h2.length === 2 && l2.length === 2 && h2[1].price < h2[0].price && l2[1].price < l2[0].price;
  const gaps = fvgs(cs); const gun = gunLine(cs); const gm = germ(cs); const mags = magnets(cs);
  const inGap = gaps.find(g => g.dir === 'up' && last >= g.bot && last <= g.top * 1.005);
  const gapBelow = gaps.filter(g => g.dir === 'up' && g.top < last).sort((a, b) => b.top - a.top)[0];
  let score = 50; const why = [];
  if (up) { score += 15; why.push('trend up (higher highs + higher lows)'); } else if (down) { score -= 20; why.push('trend down (lower highs + lower lows)'); } else why.push('ranging');
  if (gm?.lost) { score -= 22; why.push('lost its germ — the run is dead until it is back above'); }
  if (inGap) { score += 12; why.push('sitting inside an open gap (the dip zone)'); }
  if (pull < 5) { score -= 10; why.push(`at its highs (${pull.toFixed(0)}% under the top) — wait for the dip`); } else if (pull <= 18 && !down) { score += 13; why.push(`${pull.toFixed(0)}% off its high — a dip, not a top`); } else if (pull > 40) { score -= 8; why.push(`${pull.toFixed(0)}% off its high`); }
  if (gun?.fired) { score += 8; why.push('gun line fired — it is support now'); } else if (gun && gun.distPct < 4) why.push(`gun line ${gun.distPct.toFixed(1)}% overhead — a close above fires it`);
  if (pos < 0.34 && !up) { score -= 8; why.push('bottom of its range'); }
  score = Math.max(0, Math.min(100, Math.round(score)));
  const verdict = score >= 68 ? 'edge' : score >= 45 ? 'wait' : 'none';
  const plan = verdict === 'edge' ? (gm ? 'Dead under the germ.' : 'Dead under the last swing low.') + (gun && !gun.fired ? ' Fires above the gun line.' : '')
    : verdict === 'wait' ? (pull < 5 && gapBelow ? 'Wait for the dip into the gap below.' : gun && !gun.fired ? 'Wait for a close above the gun line.' : 'Wait for a higher low.')
      : 'No setup on this chart right now.';
  return { score, verdict, why, plan, pos, pull, up, down, gaps, gun, germ: gm, magnets: mags };
}

// everything the picked tools need, in one pass (`edge` switches all four on)
export function toolRead(candles, on) {
  const s = new Set(on || []); if (!s.size) return null; const all = s.has('edge'); const cs = win(candles); if (cs.length < 8) return null;
  return { fvg: all || s.has('fvg') ? fvgs(cs) : [], magnets: all || s.has('magnet') ? magnets(cs) : [], gun: all || s.has('gun') ? gunLine(cs) : null,
    germ: all || s.has('germ') ? germ(cs) : null, edge: all ? edgeRead(cs) : null };
}

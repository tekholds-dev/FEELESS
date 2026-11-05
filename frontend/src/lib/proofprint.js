// 🧬 PROOFPRINT MATH (owner's design, 2026-11-04): a real fingerprint drawn from real proofs. Every finished proof is one segment of a ridge, coloured by how it really did; a ridge fills every 12 proofs and the print grows outward from the middle.
export const SHAPES = [['whorl', 'Whorl'], ['left', 'Left loop'], ['right', 'Right loop'], ['arch', 'Arch'], ['double', 'Double loop']];
export const INKS = [['proof', 'Results'], ['blue', 'Collective blue'], ['gold', 'Gold']];
const NAMES = { pow: ['Trades', 'PoW'], pop: ['Perps', 'PoP'], pob: ['Bids', 'PoB'], poc: ['Content', 'PoC'] };
const RAMP = { proof: ['#79e8aa', '#f2c46b', '#f17d89'], blue: ['#9fe0ff', '#4fb8ff', '#2d67d8'], gold: ['#ffe9ad', '#ffc24d', '#b8741a'] };
export const band = v => (v >= 80 ? 'STRONG' : v >= 55 ? 'MEDIUM' : 'WEAK');
export const inkOf = (v, ink = 'proof') => { const r = RAMP[ink] || RAMP.proof; return v >= 80 ? r[0] : v >= 55 ? r[1] : r[2]; };
export function geom(shape, j, t) {
  const rx = 20 + j * 8.2; const ry = 24 + j * 10.3; let x = 240 + Math.cos(t) * rx; let y = 255 + Math.sin(t) * ry;
  const n = 1 + 0.02 * Math.sin(t * 3 + j * 0.24) + 0.009 * Math.cos(t * 7 + j * 0.4); x = 240 + (x - 240) * n; y = 255 + (y - 255) * n;
  if (shape === 'left') x -= 24 * Math.exp(-(((y - 255) / 115) ** 2));
  if (shape === 'right') x += 24 * Math.exp(-(((y - 255) / 115) ** 2));
  if (shape === 'arch') y = 255 + Math.sin(t) * ry * 0.73 + Math.max(0, Math.sin(t)) * j * 1.1;
  if (shape === 'double') { x += 13 * Math.sin(t * 2 + j * 0.2); y += 7 * Math.sin(t * 3); }
  return [x, y];
}
export function part(shape, j, a, b, steps = 28) { let d = ''; for (let k = 0; k <= steps; k += 1) { const [x, y] = geom(shape, j, a + ((b - a) * k) / steps); d += `${k ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)} `; } return d; }
/** A proof's real result as 0 to 100. +50% or better is 100, flat is 50. A right call 85, a wrong one 25. No result: no score. */
export function scoreOf(row) {
  const v = row?.value; if (v == null || !Number.isFinite(Number(v))) return null;
  if (row.kind === 'pow' || row.kind === 'pop') return Math.max(0, Math.min(100, Math.round(50 + Number(v))));
  return Number(v) > 0 ? 85 : Number(v) < 0 ? 25 : 50;
}
export const pickTwo = shots => { const out = []; const seen = new Set(); [...(shots || [])].reverse().forEach(s => { if (out.length < 2 && !seen.has(s.site)) { out.push(s); seen.add(s.site); } }); return out; };
const MAX_RINGS = 9; const PER_RING = 12;
export function printOf(rows) {
  const by = {}; [...(rows || [])].sort((a, b) => (a.at || 0) - (b.at || 0)).forEach(r => { const score = scoreOf(r); if (score != null && NAMES[r.kind]) (by[r.kind] = by[r.kind] || []).push({ ...r, score }); });
  const rings = []; Object.entries(by).forEach(([kind, list]) => { for (let i = 0; i < list.length; i += PER_RING) { const cps = list.slice(i, i + PER_RING); rings.push({ id: `${kind}-${i}`, kind, name: NAMES[kind][0], code: NAMES[kind][1], firstAt: cps[0].at || 0, checkpoints: cps }); } });
  rings.sort((a, b) => a.firstAt - b.firstAt);
  return { rings: rings.slice(-MAX_RINGS), total: Object.values(by).reduce((n, l) => n + l.length, 0), kinds: Object.keys(by) };
}
/** The print the Collective gives: only proofs really sent to it, one ridge per agent or per kind. */
export function collectivePrint(feed, split = 'agent') {
  const by = {}; (feed || []).filter(p => p.sent?.sig && p.pct != null).forEach(p => { const k = split === 'agent' ? p.agent || 'Agent' : p.kind || 'PoW'; (by[k] = by[k] || []).push({ ...p, id: p.id, at: p.sent.at || p.at || 0, score: Math.max(0, Math.min(100, Math.round(50 + Number(p.pct)))), name: p.label, sub: `${p.agent || ''} sent ${Number(p.sent.sol || 0).toFixed(4)} SOL`, shown: `+${Number(p.pct).toFixed(1)}%`, shots: [] }); });
  const rings = Object.entries(by).slice(0, MAX_RINGS).map(([k, cps]) => ({ id: k, kind: 'sent', name: k, code: 'SENT', firstAt: 0, checkpoints: cps.slice(0, PER_RING) }));
  return { rings, total: rings.reduce((n, r) => n + r.checkpoints.length, 0) };
}

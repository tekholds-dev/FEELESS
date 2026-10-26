// 🛰 THE INTAKE BAND, read (pure — HQ › Agents cockpit, under the chart, over the live decisions). Owner, 2026-10-13: "show everything the
// RPC brings in and what gets picked … quick dope animation, clickable, with a splash of meta vitals I can have the agents act on".
// Every coin the kernel reads is a dot: ACROSS = live market cap on a log scale ($1K … $1M, the owner's band shaded), UP = how far the
// agents took it (IN → CONTENDING → READY → PICKED). Nothing here decides anything — it is the kernel's own state, drawn.
import { capX, capOf } from './cockpitControls';

export const LANES = [['in', 'IN', 'every coin the intake brought in'], ['contending', 'CONTENDING', 'passes the wall — ranked, not ready'],
  ['ready', 'READY', 'the kernel would seat it now'], ['picked', 'PICKED', 'a seat is buying / holding it']];
const LANE_OF = { DISCOVERED: 'in', TRACKING: 'in', CONTENDING: 'contending', READY: 'ready', ORDER_PENDING: 'picked', HELD: 'picked', EXIT_PENDING: 'picked' };
export const MAX_DOTS = 140;

/** cands (kernel candidates) + held mints → dots {mint, sym, x 0–1, lane 0–3, stage, inside, rank, c}; picked + ready first, newest coins after. */
// 🦠 how far a coin sits above its germ floor (%), from whichever lens the agents wrote (1m first, then 5m) — null when no floor is on file
export function germOf(c) {
  const x = c || {}; const v = [x.germDist, x.chart?.germDist, x.ch?.germDist, x.thesis?.germDist, x.germ?.dist, x.germ5Dist, x.chart?.germ5Dist].find(n => n != null && Number.isFinite(Number(n)));
  return v == null ? null : Number(v);
}
export const AT_GERM = [-3, 10];   // within 3% under … 10% over the floor = the purple bubble (the agents' buy zone)
export function intakeDots(cands, held = [], band = {}) {
  const hs = new Set(held || []);
  const mn = Number(band?.min) || 0; const mx = Number(band?.max) || 3e5;
  const rows = (cands || []).map(c => {
    const stage = hs.has(c.mint) ? 'picked' : LANE_OF[c.status] || 'in';
    const cap = capOf(c);
    const g = germOf(c);
    return { mint: c.mint, sym: c.symbol, x: capX(cap), cap, lane: LANES.findIndex(([k]) => k === stage), stage, inside: cap > mn && cap < mx, rank: Number(c.rank) || 0, germ: g, atGerm: g != null && g >= AT_GERM[0] && g <= AT_GERM[1], c };
  }).filter(d => d.mint && d.x != null);
  const order = { picked: 0, ready: 1, contending: 2, in: 3 };
  return rows.sort((a, b) => order[a.stage] - order[b.stage] || b.rank - a.rank).slice(0, MAX_DOTS);
}

/** How many coins sit in each lane (+ in the owner's band). */
export function laneCounts(dots) {
  const out = Object.fromEntries(LANES.map(([k]) => [k, 0]));
  (dots || []).forEach(d => { out[d.stage] += 1; });
  return { ...out, inside: (dots || []).filter(d => d.inside).length, total: (dots || []).length };
}

/** The splash card's vitals for one coin: short facts, bad ones flagged. */
export function splashFacts(c) {
  const x = c || {}; const cap = capOf(x); const f = [];
  const k$ = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
  if (cap > 0) f.push(['MC', k$(cap), '']);
  if (x.ageMin != null) f.push(['AGE', x.ageMin >= 60 ? `${(x.ageMin / 60).toFixed(1)}h` : `${Math.round(x.ageMin)}m`, x.ageMin < 15 ? 'is-warn' : '']);
  if (x.move5m != null) f.push(['5M', `${x.move5m > 0 ? '+' : ''}${Number(x.move5m).toFixed(1)}%`, x.move5m <= -8 ? 'is-bad' : x.move5m > 15 ? 'is-warn' : x.move5m > 0 ? 'is-good' : '']);
  if (x.buyShare != null) f.push(['BUYERS', `${Math.round(x.buyShare)}%`, x.buyShare < 50 ? 'is-bad' : x.buyShare >= 60 ? 'is-good' : '']);
  if (x.liq != null) f.push(['POOL', k$(Number(x.liq)), Number(x.liq) < 8000 ? 'is-bad' : '']);
  if (x.vol5m != null) f.push(['5M VOL', k$(Number(x.vol5m)), '']);
  return f;
}

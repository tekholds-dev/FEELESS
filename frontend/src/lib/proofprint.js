// 🧬 PROOFPRINT MATH (owner 2026-11-04): a real fingerprint drawn from real proofs. The print itself is the agent's identity: 30 patterns and 30 inks picked by a keyed seed from the server, then every curve, core, tilt and ridge break bent by that same seed. Nobody chooses one and no two match.
// Every finished proof is one segment of a ridge, bright when it did well, dim when it did badly. A ridge fills every 12 proofs and the print grows outward.
const FAMILIES = ['Whorl', 'Spiral', 'Left Loop', 'Right Loop', 'Tented Arch', 'Double Loop'];
const VARIANTS = ['Prime', 'Drift', 'Ember', 'Tide', 'Forge'];
const NAMES = { pow: ['Trades', 'PoW'], pop: ['Perps', 'PoP'], pob: ['Bids', 'PoB'], poc: ['Content', 'PoC'], pos: ['Code', 'PoStatic'], poe: ['Books', 'PoEco'] };
const PER_RING = 12; const MAX_RINGS = 9;
export const PATTERNS = FAMILIES.flatMap(f => VARIANTS.map(v => `${f} ${v}`));
const hashStr = s => { let h = 2166136261; const t = String(s || 'feeless'); for (let i = 0; i < t.length; i += 1) { h ^= t.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
const rngOf = seed => { let a = hashStr(seed); return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
const memo = new Map();
export function identityOf(seed) {
  const key = String(seed || 'feeless'); if (memo.has(key)) return memo.get(key);
  const r = rngOf(key); const pattern = Math.floor(r() * 30); const family = Math.floor(pattern / 5); const variant = pattern % 5; const inkN = Math.floor(r() * 30); const hue = inkN * 12 + 6; const hue2 = (hue + 24 + r() * 28) % 360; const vary = [0.55, 0.85, 1.15, 1.4, 1.75][variant];
  const id = { key, code: `FP-${hashStr(`${key}a`).toString(16).toUpperCase().padStart(8, '0').slice(0, 4)}-${hashStr(`${key}b`).toString(16).toUpperCase().padStart(8, '0').slice(0, 4)}`, pattern, patternName: PATTERNS[pattern], family, inkN: inkN + 1, hue, hue2,
    sx: 0.9 + r() * 0.2, sy: 0.92 + r() * 0.16, cx: (r() - 0.5) * 26, cy: (r() - 0.5) * 22, tilt: (r() - 0.5) * 0.3, a3: (0.012 + r() * 0.02) * vary, a5: (0.005 + r() * 0.012) * vary, a7: (0.002 + r() * 0.008) * vary, b3: 0.1 + r() * 0.4, b5: 0.1 + r() * 0.5, p3: r() * 6.28, p5: r() * 6.28, p7: r() * 6.28, pull: 16 + r() * 22, twist: 8 + r() * 10, tent: 16 + r() * 22,
    gaps: Array.from({ length: 18 }, () => (r() < 0.62 ? [r() * 6.28, 0.05 + r() * 0.14] : null)) };
  memo.set(key, id); return id;
}
// 🧬 Each kind of proof draws its own way: its own pattern family and ink. The seed makes each agent's and each folder's print its own.
export const KIND_PRINT = { pow: { family: 0, ink: '#3ee58a' }, pop: { family: 4, ink: '#ff5dbb' }, pob: { family: 3, ink: '#ffb454' }, poc: { family: 1, ink: '#c58bff' }, pos: { family: 5, ink: '#57c7ff' }, poe: { family: 2, ink: '#f2c14e' } };
export const kindOfFolder = fid => { const f = String(fid || '').toLowerCase(); return f.startsWith('ps') ? 'pos' : f.startsWith('pob') ? 'pob' : f.startsWith('poc') || f.startsWith('pc') ? 'poc' : f.startsWith('pop') ? 'pop' : f.startsWith('pe') || f.startsWith('poe') ? 'poe' : 'pow'; };
export function kindIdentity(seed, kind, fid = '') { const k = KIND_PRINT[kind] ? kind : 'pow'; return { ...identityOf(`${seed}:${k}${fid ? `:${fid}` : ''}`), family: KIND_PRINT[k].family, kind: k, ink: KIND_PRINT[k].ink }; }
export const ringRy = (j, id) => (24 + j * 10.3) * (id?.sy || 1);
export function geom(id, j, t) {
  const rx = (20 + j * 8.2) * id.sx; const ry = (24 + j * 10.3) * id.sy; const turn = id.family === 1 ? (t / 6.2832) * 9 : 0; let x = Math.cos(t) * (rx + turn); let y = Math.sin(t) * (ry + turn);
  const n = 1 + id.a3 * Math.sin(t * 3 + j * id.b3 + id.p3) + id.a5 * Math.cos(t * 5 + j * id.b5 + id.p5) + id.a7 * Math.sin(t * 7 + id.p7); x *= n; y *= n;
  if (id.family === 2) x -= id.pull * Math.exp(-((y / 115) ** 2)) * (1 + j * 0.02);
  if (id.family === 3) x += id.pull * Math.exp(-((y / 115) ** 2)) * (1 + j * 0.02);
  if (id.family === 4) { y = y * 0.76 + Math.max(0, Math.sin(t)) * j * 1.1; y -= id.tent * Math.exp(-((x / 34) ** 2)) * (Math.sin(t) < 0 ? 1 : 0.2); }
  if (id.family === 5) { x += id.twist * Math.sin(t * 2 + j * 0.2); y += (id.twist * 0.55) * Math.sin(t * 3); }
  const c = Math.cos(id.tilt); const s = Math.sin(id.tilt);
  return [240 + id.cx + x * c - y * s, 255 + id.cy + x * s + y * c];
}
export function part(id, j, a, b, steps = 28) { let d = ''; for (let k = 0; k <= steps; k += 1) { const [x, y] = geom(id, j, a + ((b - a) * k) / steps); d += `${k ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)} `; } return d; }
/** A background ridge with its natural breaks: the breaks are part of what makes the print its own. */
export function ridge(id, j, steps = 60) { const g = id.gaps[j % id.gaps.length]; if (!g) return part(id, j, 0, 6.2832, steps); const s = g[0]; return part(id, j, s + g[1], s + 6.2832 - g[1], steps); }
export const band = v => (v >= 80 ? 'STRONG' : v >= 55 ? 'MEDIUM' : 'WEAK');
// The ridges' colour is the agent's own ink. Each proof on them is its result: green strong, yellow medium, red weak.
export const inkOf = v => (v >= 80 ? '#4dea8f' : v >= 55 ? '#f5cf52' : '#f2697a');
export const weightOf = score => 0.55 + (Math.abs(score - 50) / 50) * 1.05;   // a bigger result takes more of the line

export const fitBox = (n, id) => { const h = ringRy(n, id) + 34; const w = (h * 480) / 540; return `${(240 + id.cx - w).toFixed(1)} ${(255 + id.cy - h).toFixed(1)} ${(w * 2).toFixed(1)} ${(h * 2).toFixed(1)}`; };
export const faintCount = (rings, grow = 6) => Math.max(grow, Math.min(18, rings * 2 + 4));
const TWO = Math.PI * 2;
/** Where each proof sits on its ridge: the line grows from its start by each result's size, and fills the ring once it holds 12 average proofs. */
export function spans(cps) { const each = cps.map(c => weightOf(c.score)); const scale = Math.min(TWO / (PER_RING * 1.1), TWO / Math.max(1e-9, each.reduce((a, b) => a + b, 0))); let at = 0; return each.map(w => { const from = at; at += w * scale; return [from, at]; }); }
export function ringPoint(id, i, cps, k) { const [a, b] = spans(cps)[k] || [0, 0]; return geom(id, i * 2 + 2, (a + b) / 2); }
export const segment = (id, i, a, b) => part(id, i * 2 + 2, a, b, Math.max(6, Math.round((b - a) * 16)));
/** A proof's real result as 0 to 100. +50% or better is 100, flat is 50. A right call 85, a wrong one 25. No result: no score. */
export function scoreOf(row) {
  const v = row?.value; if (v == null || !Number.isFinite(Number(v))) return null;
  if (row.kind === 'pow' || row.kind === 'pop') return Math.max(0, Math.min(100, Math.round(50 + Number(v))));
  return Number(v) > 0 ? 85 : Number(v) < 0 ? 25 : 50;
}
export const pickTwo = shots => { const out = []; const seen = new Set(); [...(shots || [])].reverse().forEach(s => { if (out.length < 2 && !seen.has(s.site)) { out.push(s); seen.add(s.site); } }); return out; };
export function printOf(rows) {
  const by = {}; [...(rows || [])].sort((a, b) => (a.at || 0) - (b.at || 0)).forEach(r => { const score = scoreOf(r); if (score != null && NAMES[r.kind]) (by[r.kind] = by[r.kind] || []).push({ ...r, score }); });
  const rings = []; Object.entries(by).forEach(([kind, list]) => { for (let i = 0; i < list.length; i += PER_RING) { const cps = list.slice(i, i + PER_RING); rings.push({ id: `${kind}-${i}`, kind, name: NAMES[kind][0], code: NAMES[kind][1], firstAt: cps[0].at || 0, checkpoints: cps }); } });
  rings.sort((a, b) => a.firstAt - b.firstAt);
  return { rings: rings.slice(-MAX_RINGS), total: Object.values(by).reduce((n, l) => n + l.length, 0), kinds: Object.keys(by) };
}
/** {proof id: its exact line on the agent's print}. A folder draws this same line, so its print and the desktop's are one thing. */
export function linesOf(print) { const m = {}; (print?.rings || []).forEach((r, i) => { const sp = spans(r.checkpoints); r.checkpoints.forEach((c, k) => { m[c.id] = { i, a: sp[k][0], b: sp[k][1], score: c.score }; }); }); return m; }
export function statsOf(rows) {
  const scored = (rows || []).map(r => ({ ...r, score: scoreOf(r) })).filter(r => r.score != null).sort((a, b) => (a.at || 0) - (b.at || 0)); let run = 0; let best = 0; let now = 0;
  scored.forEach(r => { if (r.score >= 55) { run += 1; best = Math.max(best, run); } else run = 0; }); for (let i = scored.length - 1; i >= 0 && scored[i].score >= 55; i -= 1) now += 1;
  const n = b => scored.filter(r => band(r.score) === b).length;
  return { total: scored.length, strong: n('STRONG'), medium: n('MEDIUM'), weak: n('WEAK'), bestRun: best, run: now, avg: scored.length ? Math.round(scored.reduce((a, r) => a + r.score, 0) / scored.length) : 0, top: [...scored].sort((a, b) => b.score - a.score)[0] || null, big: scored.filter(r => r.kind === 'pow' && Number(r.value) >= 50).length };
}
/** The print the Collective gives: only proofs really sent to it, one ridge per agent or per kind. */
export function collectivePrint(feed, split = 'agent') {
  const by = {}; (feed || []).filter(p => p.sent?.sig && p.pct != null).forEach(p => { const k = split === 'agent' ? p.agent || 'Agent' : p.kind || 'PoW'; (by[k] = by[k] || []).push({ ...p, id: p.id, at: p.sent.at || p.at || 0, score: Math.max(0, Math.min(100, Math.round(50 + Number(p.pct)))), name: p.label, sub: `${p.agent || ''} sent ${Number(p.sent.sol || 0).toFixed(4)} SOL`, shown: `+${Number(p.pct).toFixed(1)}%`, shots: [] }); });
  const rings = Object.entries(by).slice(0, MAX_RINGS).map(([k, cps]) => ({ id: k, kind: 'sent', name: k, code: 'SENT', firstAt: 0, checkpoints: cps.slice(0, PER_RING) }));
  return { rings, total: rings.reduce((n, r) => n + r.checkpoints.length, 0) };
}
/** 🌊 THE EXAMPLE: the same rules as collective_pool.py, day by day, for members who stay, one row per plan. No new people join: this shows it needs none. */
export function growthExample(rules, { members = 500, sendWeek = 10, tradeDay = 50, plan = 'month', strength = 50, days = 360, outsideDay = 0 } = {}) {
  const plans = rules.plans || []; const p = plans.find(x => x.plan === plan) || plans[1] || { backPct: 85, days: 30, weightX: 2, roomX: 2 }; const fee = (tradeDay < rules.txnSmallUsd ? rules.txnSmallPct : tradeDay < rules.txnBigUsd ? rules.txnMidPct : rules.txnBigPct) / 100; const skim = rules.skimPct / 100; const potPct = rules.potPct / 100; const payDay = (rules.potPayDayPct || 5) / 100;
  const ptsWeek = Math.min(rules.ptsMaxSend ?? 60, (rules.ptsBase ?? 5) + sendWeek * (rules.ptsPerUsd ?? 2)) * (0.5 + strength / 100); const fade = 0.5 ** (1 / (rules.boostFadeDays || 60)); let pts = 0; let you = { lock: [], sent: 0, own: 0, fee: 0, room: 0, vault: 0 }; let net = { pot: 0, keep: 0, lock: 0 }; let feesIn = 0; const rows = []; let even = null;
  for (let d = 0; d <= days; d += 1) {
    const dayFees = members * tradeDay * fee; feesIn += dayFees; net.pot += dayFees * potPct + outsideDay * ((rules.sitePct ?? 20) / 100); net.keep += dayFees * (1 - potPct); pts *= fade;
    const boost = rules.boostMode === 'rank' ? 0 : Math.min(1, pts / 100) * (0.5 + strength / 200);
    if (d && d % 7 === 0) { pts += ptsWeek; const lockIt = sendWeek * (1 - skim); net.keep += members * sendWeek * skim; you.sent += sendWeek; you.room += sendWeek * (p.roomX ?? p.weightX); if (plan === 'vault') { you.vault += lockIt; net.keep += members * lockIt; } else { const back = lockIt * Math.min(100, p.backPct + (rules.boostBackPts || 0) * boost) / 100; you.lock.push({ left: lockIt, back, each: lockIt / p.days, days: p.days }); net.lock += members * lockIt; net.keep += members * (lockIt - back); net.lock -= members * (lockIt - back); } }
    const pay = net.pot * payDay; const mine = Math.min(you.room, pay / Math.max(1, members)); net.pot -= mine * members; you.fee += mine; you.room = Math.max(0, you.room - mine) * 0.5 ** (1 / 30);
    you.lock.forEach(l => { if (l.left <= 0) return; const out = Math.min(l.left, l.each); const got = out * (l.back / (l.each * l.days)); l.left -= out; you.own += got; net.lock -= members * got; });
    const coming = you.lock.reduce((a, l) => a + l.left * (l.back / (l.each * l.days)), 0); const back = you.own + you.fee; if (even == null && you.sent > 0 && back >= you.sent) even = d;
    if (d % 10 === 0) rows.push({ d, feesPaid: tradeDay * fee * d, sent: you.sent, own: you.own, fee: you.fee, back, coming, keep: net.keep, pot: net.pot, lock: net.lock, feesIn, points: pts, boost });
  }
  return { rows, even };
}

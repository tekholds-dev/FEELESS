// 🎛 THE COCKPIT'S META CONTROLS + 💹 THE LIVE TRADE HUD, read (pure — HQ › Agents cockpit). Every option comes from the server's own
// `policy.controls` (the cfg validator's lists); nothing here invents a value. Owner, 2026-10-12: "update controls to be meta, the live pnl
// tracker and agt tab way more meta".

// the controls, grouped the way a trader thinks about them; a key the server does not send is simply not drawn
export const CTRL_GROUPS = [
  ['universe', '🎯 UNIVERSE', 'Which coins a NEW seat may buy — held winners keep running past the band', ['agentMcMin', 'agentMcMax', 'agentMinAgeH']],
  ['exits', '💰 EXITS', 'How a seat leaves: your line, or the agents\' own read', ['agentTp', 'agentSl', 'agentTrail', 'agentMaxHold']],
  ['seats', '🪑 SEATS & ENTRY', 'How big a seat is, how fast an empty one fills, when a seat is given up', ['agentSizePct', 'agentSeatTarget', 'agentEntry', 'agentSwitch']],
];

const k$ = v => (v >= 1e6 ? `$${+(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${+(v / 1e3).toFixed(1)}K` : `$${v}`);
const hm = m => (m >= 60 ? `${+(m / 60).toFixed(1)}h` : `${m}m`);

// one option as the short word on its segment button
export function optWord(key, v) {
  const n = Number(v);
  switch (key) {
    case 'agentTp': return n ? `+${n}%` : 'AGENTS';
    case 'agentSl': return n ? `−${n}%` : 'AGENTS';
    case 'agentMaxHold': return n ? hm(n) : 'AGENTS';
    case 'agentSizePct': return n ? `${n}%` : 'AGENTS';
    case 'agentSeatTarget': return n ? `${n}s` : 'AUTO';
    case 'agentMinAgeH': return n ? hm(Math.round(n * 60)) : 'ANY';
    case 'agentMcMin': return n ? k$(n) : 'NONE';
    case 'agentMcMax': return k$(n);
    case 'agentEntry': return v === 'go' ? 'GO ONLY' : 'AGENTS';
    case 'agentTrail': case 'agentSwitch': return v === 'agents' || v === 'auto' ? 'AGENTS' : String(v).toUpperCase();
    default: return String(v);
  }
}

// who decides a control right now → its tone class
export const whoTone = w => (w === 'CREATOR OVERRIDE' ? 'is-you' : w === 'YOUR BAND' ? 'is-band' : 'is-agents');
export const WHO_WORD = { 'CREATOR OVERRIDE': 'YOURS', 'YOUR BAND': 'YOUR BAND', 'AGENTS CHOOSE': 'AGENTS' };

// 🎯 the MC band on a log track ($1K … $1M) + where this pass's candidates sit (each dot = a real coin the kernel read)
const LO = Math.log10(1e3); const HI = Math.log10(1e6);
export const capX = v => (Number(v) > 0 ? Math.max(0, Math.min(1, (Math.log10(Number(v)) - LO) / (HI - LO))) : null);
export const capOf = c => (Number(c?.cap) > 0 ? Number(c.cap) : Number(c?.price) > 0 && Number(c?.supply) > 0 ? Number(c.price) * Number(c.supply) : null);
export function bandTrack(min, max, cands) {
  const mn = Number(min) || 0; const mx = Number(max) || 3e5;
  const dots = (cands || []).map(c => ({ c, cap: capOf(c) })).filter(x => x.cap > 0).slice(0, 40)
    .map(({ c, cap }) => ({ x: capX(cap), inside: cap > mn && cap < mx, ready: c.status === 'READY', sym: c.symbol, cap }));
  return { lo: mn > 0 ? capX(mn) : 0, hi: capX(mx) ?? 1, dots, inside: dots.filter(d => d.inside).length, ready: dots.filter(d => d.inside && d.ready).length };
}

// 🫀 the model's vitals as meters: rug reads INVERTED (high = bad); the others high = good. Unknown = not drawn.
export const VITAL_ROWS = [['rug', 'RUG RISK', true], ['narrative', 'NARRATIVE', false], ['crowd', 'CROWD', false], ['momentum', 'MOMENTUM', false]];
export const TIMING_TONE = { EARLY: 'is-good', 'ON TIME': 'is-good', LATE: 'is-warn', CHASE: 'is-bad', DEAD: 'is-bad' };
export function vitalRows(a) {
  const v = a?.vitals || {};
  return VITAL_ROWS.filter(([k]) => Number.isFinite(Number(v[k])) && v[k] !== null && v[k] !== undefined).map(([k, label, inv]) => {
    const n = Math.max(0, Math.min(100, Number(v[k]))); const good = inv ? n <= 30 : n >= 60; const bad = inv ? n >= 60 : n <= 30;
    return { k, label, v: n, fill: n / 100, tone: good ? 'is-good' : bad ? 'is-bad' : 'is-warn' };
  });
}
export const hasVitals = a => !!(a && ((a.vitals && Object.keys(a.vitals).length) || a.timing || (a.flags || []).length));

// the newest model answer about one coin (any desk) — for the queue's AI column and a seat
export function aiOf(notes, mint) {
  const n = (notes || {})[mint]; if (!n) return null;
  const best = Object.entries(n).map(([role, x]) => ({ role, ...x })).filter(x => x.advice).sort((a, b) => (b.at || 0) - (a.at || 0))[0];
  return best || null;
}

// 💹 the live trade on one bar: stop … take, with now, the peak it reached, the worst it saw, and the trail line once armed.
// Every number is the position's own (Reaper's record) or the live price; the bar widens so now / peak are always on it.
export function tradeBar(pos, px) {
  const e = Number(pos?.entry); const p = Number(px) || Number(pos?.px); const sl = Number(pos?.stop); const tp = Number(pos?.take);
  if (!(e > 0) || !(p > 0)) return null;
  const pct = (p / e - 1) * 100; const peak = Math.max(pct, Number.isFinite(Number(pos?.mfe ?? pos?.peak)) ? Number(pos?.mfe ?? pos?.peak) : pct);
  const low = Math.min(pct, Number.isFinite(Number(pos?.mae)) ? Number(pos.mae) : pct);
  const trail = Number.isFinite(Number(pos?.trailAt)) && pos?.trailAt != null ? Number(pos.trailAt) : null;
  const arm = Number.isFinite(Number(pos?.armAt)) && pos?.armAt != null ? Number(pos.armAt) : null;
  const lo = Math.min(sl ? -Math.abs(sl) : -30, low - 2); const hi = Math.max(tp > 0 ? tp : 50, peak + 2);
  const at = v => Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  return { pct, lo, hi, at: at(pct), zero: at(0), peak, peakAt: at(peak), low, lowAt: at(low), trail, trailAt: trail == null ? null : at(trail), arm, armAt: arm == null ? null : at(arm),
    stopAt: sl ? at(-Math.abs(sl)) : null, takeAt: tp > 0 ? at(tp) : null, hasStop: !!sl, hasTake: tp > 0, stop: sl ? -Math.abs(sl) : null, take: tp > 0 ? tp : null,
    toTake: tp > 0 ? tp - pct : null, toStop: sl ? pct + Math.abs(sl) : null, giveBack: Math.max(0, peak - pct) };
}

// a real tick's direction since the last one (for the flash) — 0 when unchanged / unknown
export const tickDir = (prev, next) => (Number(prev) > 0 && Number(next) > 0 && prev !== next ? (next > prev ? 1 : -1) : 0);

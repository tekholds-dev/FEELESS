// 🎛 THE COCKPIT'S META CONTROLS + 💹 THE LIVE TRADE HUD, read (pure — HQ › Agents cockpit). Every option comes from the server's own
// `policy.controls` (the cfg validator's lists); nothing here invents a value. Owner, 2026-10-12: "update controls to be meta, the live pnl
// tracker and agt tab way more meta".

// the controls, grouped the way a trader thinks about them; a key the server does not send is simply not drawn
export const CTRL_GROUPS = [
  ['universe', '🎯 UNIVERSE', 'Which coins a NEW seat may buy — held winners keep running past the band', ['agentMcMin', 'agentMcMax', 'agentMinAgeH']],
  ['exits', '💰 EXITS', 'How a seat leaves: your line, or the agents\' own read', ['agentTp', 'agentSl', 'agentTrail', 'agentMaxHold']],
  ['seats', '🪑 SEATS & ENTRY', 'How big a seat is, how fast an empty one fills, when a seat is given up', ['agentSizePct', 'agentSeatTarget', 'agentEntry', 'agentSwitch']],
  ['gate', '🛂 BUY GATE', 'What the keeper accepts on an agent buy — most empty seats are a coin refused right here', ['agentGapPct', 'agentBackPct', 'agentPoolMin']],
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
    case 'agentEntry': return v === 'go' ? 'GO ONLY' : v === 'armed' ? 'ARMED' : 'AGENTS';
    case 'agentGapPct': return n ? `≤ ${n}%` : '2.5%';
    case 'agentBackPct': return n ? `≤ ${n}%` : '3.5%';
    case 'agentPoolMin': return n ? k$(n) : '$8K';
    case 'agentTrail': case 'agentSwitch': return v === 'agents' || v === 'auto' ? 'AGENTS' : String(v).toUpperCase();
    default: return String(v);
  }
}

// 🛂 the keeper's own refusals of agent buys (seat pre-check + final gate), counted by the limit that refused them — which knob is closing the seat
export const GATE_WORDS = [['gap', 'price gap', /above market/i], ['back', 'sell-back', /sells back|sell it back/i], ['pool', 'thin pool', /pool too thin/i],
  ['route', 'no route / busy', /route|jupiter|429/i]];
export function gateCounts(refused) {
  const out = { total: 0 }; GATE_WORDS.forEach(([k]) => { out[k] = 0; });
  (refused || []).forEach(r => { const w = String(r?.why || ''); const hit = GATE_WORDS.find(([, , re]) => re.test(w)); out.total += 1; out[hit ? hit[0] : 'other'] = (out[hit ? hit[0] : 'other'] || 0) + 1; });
  return out;
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

// 🧠 the model's vital intel (summary · risk flags · narrative · creator context · conflict resolution · confidence delta): unknown = not drawn
export const INTEL_ROWS = [['narrative', '📖', 'NARRATIVE'], ['creator_context', '👤', 'CREATOR'], ['conflict_resolution', '⚖', 'CONFLICT']];
export const hasIntel = a => !!(a && (a.summary || (a.risk_flags || []).length || INTEL_ROWS.some(([k]) => a[k]) || (a.scout && Object.keys(a.scout).length)));
// 🔎 the text scout as chips (what only the model reads): original or a copycat · callers' thesis real or a swarm · site matches · real tech 0–100
export function scoutChips(sc) {
  const s = sc || {}; const out = [];
  if (s.original === true) out.push(['orig', '🧬 ORIGINAL', 'is-good']); else if (s.original === false) out.push(['orig', '📋 COPYCAT', 'is-bad']);
  if (s.thesis === 'real') out.push(['thesis', '🗣 REAL THESIS', 'is-good']); else if (s.thesis === 'swarm') out.push(['thesis', '🗣 SWARM LINE', 'is-bad']);
  if (s.site === 'match') out.push(['site', '🌐 SITE MATCHES', 'is-good']); else if (s.site === 'mismatch') out.push(['site', '🌐 SITE MISMATCH', 'is-bad']);
  if (Number.isFinite(s.tech)) out.push(['tech', `⚙ TECH ${s.tech}`, s.tech >= 60 ? 'is-good' : s.tech <= 20 ? 'is-meme' : 'is-hold']);
  return out;
}
// 🧪 the rule lab's row in words: unseen (the newest 40% of real trades) result of the coins it matches vs the rest
export function labLine(r) {
  const t = r?.test || {}; const f = v => (v == null ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
  return t.n ? `unseen ${t.n}: ${f(t.avg)} vs ${f(t.rest)}` : r?.lossHits ? `${r.lossHits} recent real losses fit it` : 'waiting for trades';
}
export const intelRows = a => INTEL_ROWS.filter(([k]) => a?.[k]).map(([k, icon, label]) => ({ k, icon, label, text: a[k] }));

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

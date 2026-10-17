// 🎛 THE AGENTS COCKPIT, as plain data (HQ › Agents, the first thing on the tab). Every field below is read from the ONE agent hub
// snapshot (+ its live deltas + the shared live-price poller): the real card's seats, Reaper's rulings, the kernel's decisions, the
// kernel's decision TAPE (a line exists only because something real changed) and the owner's review list. Nothing here computes a
// trade, a confidence or a forecast — an unknown number stays null and the page prints "—" / UNAVAILABLE.
//
// 📊 MARKET CAP IS THE CHART LANGUAGE: a coin's MC = live price × the supply the kernel resolved (backend trench_kernel/supply.py:
// token supply → a launchpad's fixed 1B → live cap ÷ price). No supply → the chart says MARKET CAP UNAVAILABLE, never a raw price chart.
import { mcapOf, isLaunchpadMint } from './mcap';
import { rowState, VERD, devilOf } from './agentRead';

const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
// the $ a seat is up / down: its value now minus what that value was at entry (value ÷ (1 + %)). Unknown either side = unknown.
export const pnlUsdOf = (usd, pct) => (usd == null || pct == null || pct <= -100 ? null : usd - usd / (1 + pct / 100));

// MC from a price: the kernel's supply first, then the live record's own cap, then a launchpad's fixed supply (mcapOf). null = unknown.
export function mcFrom(price, supply, liveMc, mint) {
  const p = num(price); const s = num(supply);
  if (p > 0 && s > 0) return p * s;
  const m = mcapOf(p, liveMc, mint);
  return m > 0 ? m : null;
}
// the supply implied by what is known (price × supply = MC): the kernel's own, else live cap ÷ live price, else a launchpad's 1B
export function supplyFrom(price, supply, liveMc, mint) {
  const s = num(supply); if (s > 0) return s;
  const p = num(price); const m = mcFrom(p, null, liveMc, mint);
  return p > 0 && m > 0 ? m / p : null;
}

// ── the decision tape ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
export const TAPE_AGENT = { tally: ['📊', 'Tally'], sherlock: ['🔍', 'Sherlock'], weather: ['🌦', 'Weather'], trigger: ['⏱', 'Trigger'], devil: ['⚖', 'Devil'], warden: ['🛡', 'Warden'],
  courier: ['📮', 'Courier'], reaper: ['☠', 'Reaper'], archivist: ['🗄', 'Archivist'], judge: ['👨‍⚖️', 'Judge'], kernel: ['⚙', 'Kernel'], owner: ['👤', 'You'] };
// one tone per line, from its own words: green = a real step forward (READY, ENTER, a fill, a take), red = a block / loss / exit, gold = a warning
export function tapeTone(r) {
  const a = String(r?.action || '').toUpperCase(); const pc = num(r?.result?.pct);
  if (/HARD VETO|VETO|FAILED|REFUSED|DROPPED|EXIT|COLLAPS/.test(a) || (pc != null && pc < 0 && /FILED|REVIEW/.test(a))) return 'is-bad';
  if (/WARNING|PROBATION|BACK TO/.test(a)) return 'is-warn';
  if (/READY|ENTER|FILLED|TAKE|HELD|SIZE|CLEARED|ARM|SURGE|CANDIDATE|PROTECT/.test(a) || (pc != null && pc > 0)) return 'is-good';
  return '';
}
// newest first, optionally one coin / one agent
export const tapeOf = (rows, { mint = null, agent = null, n = 40 } = {}) => [...(rows || [])].filter(r => (!mint || r.mint === mint) && (!agent || r.agent === agent)).sort((a, b) => (b.id || 0) - (a.id || 0)).slice(0, n);
// 🧹 consecutive lines from the SAME agent with the SAME action fold into one ("⏱ Trigger · WAIT ×5 · $SI $SCASH …") — built from the owner-approved
// build item "Collapse repeated WAIT labels" (b4). The newest line of the run stays the row; `n` + `syms` say what it covers.
export function groupTape(rows) {
  const out = [];
  for (const r of rows || []) {
    const last = out[out.length - 1];
    if (last && last.agent === r.agent && last.action === r.action) { last.n += 1; if (r.symbol && !last.syms.includes(r.symbol)) last.syms.push(r.symbol); continue; }
    out.push({ ...r, n: 1, syms: r.symbol ? [r.symbol] : [] });
  }
  return out;
}
// 🩸 where the real losses come from (b2/b3/b6) + the Judge's real record (b1): the Judge's own reviews of confirmed exits, the capital desk's leaks
export function lossMap(court, capital) {
  const c = court || {}; const w = Number(c.wins) || 0; const l = Number(c.losses) || 0;
  const causes = (c.lossPatterns || []).map(x => ({ cause: String(x.cause || '?').replace(/_/g, ' '), n: Number(x.n) || 0, desk: x.desk || '?' })).sort((a, b) => b.n - a.n);
  const top = Math.max(1, ...causes.map(x => x.n));
  return { w, l, pct: w + l ? Math.round((w / (w + l)) * 100) : null, causes: causes.map(x => ({ ...x, fill: x.n / top })),
    leaks: (capital?.leaks || []).map(x => ({ rule: x.rule, n: x.n, avg: x.avgPct })), last: c.lastLoss ? { sym: c.lastLoss.sym, pct: c.lastLoss.pct, lesson: c.lastLoss.lesson || c.lastLoss.change } : null };
}
// 📏 agents with no real decision on record yet (b-unmeasured) · desks whose real record is identical (they are credited per TEAM decision)
export function measureRead(agents, ds) {
  const st = ds || {}; const keys = (agents || []).map(a => a.key);
  const un = keys.filter(k => !(Number(st[k]?.decisions) > 0));
  const sig = k => (st[k] && !st[k].own?.n ? `${st[k].decisions}|${st[k].accuracy}` : null); const same = {};   // a desk with its OWN vote record no longer "shares one record"
  keys.forEach(k => { const g = sig(k); if (g) same[g] = (same[g] || 0) + 1; });
  return { unmeasured: un, sameN: Math.max(0, ...Object.values(same)) };
}

// the newest tape line for each coin (a seat card's "last action")
// 🗳 one desk's record as the card shows it: its OWN vote on real money first, else the team record it shares, else its own job's measure
export function recWord(st) {
  if (!st) return 'no real record yet';
  const o = st.own;
  if (o?.n) return `🗳 ${o.rightPct ?? '—'}% own · ${o.n} votes${o.lone ? ` · ${o.loneRight}/${o.lone} lone` : ''}`;
  if (st.kind === 'landed') return `📮 ${st.accuracy ?? '—'}% landed · ${st.decisions ?? 0} sends`;
  if (st.kind === 'intact') return `🗄 ${st.decisions ?? 0} filed · ${st.accuracy === 100 ? 'chain intact' : st.accuracy === 0 ? 'REWRITTEN' : '—'}`;
  return `${st.accuracy ?? '—'}% · ${st.winResp ?? 0}W ${st.lossResp ?? 0}L`;
}
// 🗳 the go / doubt split of one desk's own votes: typical real % when it said GO vs when it doubted (the gap is what its vote is worth)
export function voteSplit(st) {
  const o = st?.own; if (!o?.n) return null;
  return { go: o.go?.med ?? null, goN: o.go?.n || 0, doubt: o.doubt?.med ?? null, doubtN: o.doubt?.n || 0,
    edge: o.go?.med != null && o.doubt?.med != null ? +(o.go.med - o.doubt.med).toFixed(1) : null };
}

export function lastByMint(rows) {
  const out = {}; (rows || []).forEach(r => { if (r.mint && (!out[r.mint] || (r.id || 0) > (out[r.mint].id || 0))) out[r.mint] = r; }); return out;
}

// ── the seats ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// Reaper's ruling → the badge (PROTECT / HOLD / EXIT / TAKE …); a seat the keeper is still buying = ORDER PENDING
// ONE card per seat of the real card: who holds it, its live % since entry, entry / now in MARKET CAP, the $ in the seat, how long it
// has been held, Reaper's ruling + rule, and the coin's newest real tape line. An open seat says how many READY coins could take it.
export function seatCards(d, livePx) {
  const o = d?.office || {}; const seats = d?.card?.seats || []; const pos = Object.fromEntries((o.positions || []).filter(p => p.mint).map(p => [p.mint, p]));
  const board = Object.fromEntries((o.seatBoard || []).filter(b => b.mint).map(b => [b.mint, b])); const cand = Object.fromEntries(((o.kernel || {}).candidates || []).map(c => [c.mint, c]));
  const last = lastByMint(o.tape); const ready = ((o.kernel || {}).candidates || []).filter(c => c.status === 'READY').length;
  const rows = seats.length ? seats : (o.positions || []).map(p => ({ symbol: p.symbol, mint: p.mint, pair: p.pair, kind: p.owner === 'agents' ? 'agent' : 'engine' }));
  const firstOpen = rows.findIndex(x => !x.mint || x.kind === 'open');   // the notes about READY coins that did not get a seat are shown once, on the first OPEN seat
  return rows.map((x, i) => {
    const open = !x.mint || x.kind === 'open';
    if (open) {   // the server's own reason this seat is open (OFFICE NOT LIVE · NO VALID ENTRY · BUDGET …) — never a promise that it fills
      const sv = (o.seat?.seats || []).find(z => z.seat === i + 1) || (o.seatBoard || []).find(z => z.seat === i + 1 && z.empty) || null;
      return { seat: i + 1, open: true, badge: sv?.code || 'OPEN', why: sv?.reason || sv?.why || o.seat?.reason || `${ready} READY candidate${ready === 1 ? '' : 's'} on the desk this pass`,
        refused: i === firstOpen ? (o.seat?.refused || []).slice(0, 3) : [], tapeWait: i === firstOpen ? (o.flowWait?.rows || []).slice(0, 3) : [] };   // why READY coins did not become positions (the keeper's own words) — once, on the first open seat
    }
    const p = pos[x.mint] || {}; const b = board[x.mint] || {}; const c = cand[x.mint] || {};
    const lp = livePx && x.pair ? livePx.get?.(x.pair) : null;
    const px = num(lp?.price) || num(p.px) || num(c.price);
    const supply = supplyFrom(num(p.px) || num(c.price) || px, p.supply ?? c.supply, lp?.mc, x.mint);
    const entry = num(p.entry);
    const pctSrv = num(p.pct ?? x.pct ?? b.pct);
    // 💹 LIVE: a seat's P&L moves with the shared live price (every 3s) against its own entry — the server's figure only between reads
    const pct = entry > 0 && num(lp?.price) > 0 ? (num(lp.price) / entry - 1) * 100 : pctSrv;
    const buying = !!(x.buying || b.buying) && p.exec !== 'confirmed';
    const badge = buying ? 'ORDER PENDING' : (p.decision || b.result || (x.action ? String(x.action).toUpperCase() : 'HOLD'));
    const ageH = num(p.launch?.ageH); const usd0 = num(p.usd); const usd = usd0 != null && num(p.px) > 0 && num(lp?.price) > 0 ? usd0 * num(lp.price) / num(p.px) : usd0;
    return { seat: i + 1, open: false, symbol: x.symbol, mint: x.mint, pair: x.pair || p.pair, kind: x.kind || 'agent', tag: x.tag || null, buying, badge,
      pct, entry, px, supply, entryMc: num(p.entryMc) || (entry > 0 && supply > 0 ? entry * supply : null), mc: px > 0 && supply > 0 ? px * supply : num(p.mc),
      usd, pnlUsd: pnlUsdOf(usd, pct), heldMin: num(p.heldMin ?? b.heldMin), rule: p.rule || b.rule || null, why: p.evidence || b.why || x.why || null,
      take: num(p.take ?? x.take), stop: num(p.stop), peak: num(p.mfe ?? p.peak), trailAt: num(p.trailAt), armAt: num(p.armAt), last: last[x.mint] || null, ageMin: ageH != null ? ageH * 60 : num(c.ageMin),
      nextReview: num(p.nextReview), realized: num(p.realizedUsd), path: Array.isArray(p.path) ? p.path.map(num).filter(v => v != null) : [],
      flow: p.flow?.state ? p.flow : null, drain: p.drain || null, liqPct: num(p.liqPct), rotate: !!b.switch, reaper: p.decision || p.state || b.result || null, action: p.action || x.action || null, state: null,
      mine: x.kind === 'yours' || x.kind === 'suggested' || p.owner === 'you', would: x.would || null, agentsWould: p.would || null, study: Array.isArray(p.study) ? p.study : [] };
  });
}

// the coin the cockpit centres on: the owner's pick when it still exists, else the most pressed held seat, else the best READY coin,
// else the best candidate, else the first owner review row
const URGENT = ['EXIT', 'EXIT INVALIDATED', 'TAKE PROFIT', 'PROTECT', 'HOLD 5 MORE', 'HOLD', 'ORDER PENDING'];
export function focusMint(d, pick) {
  const o = d?.office || {}; const cands = (o.kernel || {}).candidates || []; const seats = seatCards(d).filter(s => !s.open);
  const known = new Set([...seats.map(s => s.mint), ...cands.map(c => c.mint), ...(o.ownerReview || []).map(r => r.mint)]);
  if (pick && known.has(pick)) return pick;
  const hot = [...seats].sort((a, b) => URGENT.indexOf(a.badge) - URGENT.indexOf(b.badge))[0];
  if (hot) return hot.mint;
  const ready = cands.filter(c => c.status === 'READY').sort((a, b) => (b.rank || 0) - (a.rank || 0))[0];
  return ready?.mint || cands[0]?.mint || (o.ownerReview || [])[0]?.mint || null;
}

// ── the chart ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
const MARK = {   // a tape line → a chart marker (only real events; a line with no time is never drawn)
  trigger: r => (r.action === 'ENTER' ? { shape: 'circle', color: '#45e486', position: 'belowBar', text: '⏱ ENTER' } : null),
  kernel: r => (r.action === 'READY' ? { shape: 'circle', color: '#15d16a', position: 'belowBar', text: 'READY' } : null),
  devil: r => (r.action === 'HARD VETO' ? { shape: 'square', color: '#ff8fa3', position: 'aboveBar', text: '⚖ VETO' } : null),
  reaper: r => (/EXIT|TAKE|PROTECT/.test(r.action) ? { shape: 'arrowDown', color: /EXIT/.test(r.action) ? '#ff8fa3' : '#9fe3ff', position: 'aboveBar', text: `☠ ${r.action}` } : null),
  warden: r => (r.action === 'VETO' ? { shape: 'square', color: '#f5c542', position: 'aboveBar', text: '🛡 VETO' } : null),
};
// the coin's REAL fills (the keeper's ledger, confirmed) sit at their exact fill price; decisions sit on the candle they happened in
export function chartMarkers(rows, fills) {
  const out = [];
  (fills || []).forEach(f => { const t = num(f.at); const px = num(f.px); if (!t) return;
    const buy = f.side === 'buy'; out.push({ time: Math.floor(t), position: px ? (buy ? 'atPriceBottom' : 'atPriceTop') : (buy ? 'belowBar' : 'aboveBar'), price: px || undefined, shape: buy ? 'arrowUp' : 'arrowDown', color: buy ? '#15d16a' : '#fa708c', text: `${buy ? 'BUY' : 'SELL'}${f.usd != null ? ` $${Number(f.usd).toFixed(2)}` : ''}` }); });
  (rows || []).forEach(r => { const fn = MARK[r.agent]; const m = fn && fn(r); const t = num(r.at); if (m && t) out.push({ time: Math.floor(t), ...m }); });
  return out.sort((a, b) => a.time - b.time);
}
// the coin on the chart: pair + MC + the agents' levels (entry / take / stop for a position; nothing invented for a candidate)
export function chartModel(d, mint, livePx) {
  if (!mint) return null;
  const o = d?.office || {}; const p = (o.positions || []).find(x => x.mint === mint); const c = ((o.kernel || {}).candidates || []).find(x => x.mint === mint);
  const s = (d?.card?.seats || []).find(x => x.mint === mint); const rv = (o.ownerReview || []).find(x => x.mint === mint);
  const pair = p?.pair || c?.pair || s?.pair || rv?.pair || null; const symbol = p?.symbol || c?.symbol || s?.symbol || rv?.symbol || null;
  const lp = livePx && pair ? livePx.get?.(pair) : null;
  const price = num(lp?.price) || num(p?.px) || num(c?.price) || num(rv?.price);
  const supply = supplyFrom(price, p?.supply ?? c?.supply ?? rv?.supply, lp?.mc, mint);
  const mc = price > 0 && supply > 0 ? price * supply : null;
  const e = num(p?.entry); const lines = [];
  if (e > 0) {
    lines.push({ px: e, title: 'entry', color: '#15d16a' });
    if (num(p.take)) lines.push({ px: e * (1 + p.take / 100), title: `take +${p.take}%`, color: '#9fe3ff' });
    if (num(p.stop)) lines.push({ px: e * (1 + p.stop / 100), title: `stop ${p.stop}%`, color: '#ff8fa3' });
    if (num(p.trailAt)) lines.push({ px: e * (1 + p.trailAt / 100), title: `trail +${p.trailAt}%`, color: '#e8c46a' });   // 🏔 the live trailing exit Reaper is holding to
    if (num(p.peak) > 0) lines.push({ px: e * (1 + p.peak / 100), title: `peak +${(+p.peak).toFixed(1)}%`, color: '#45e486' });
    if (num(p.thesis?.invalidation) && !['yours', 'model'].includes(p.takeSource)) lines.push({ px: p.thesis.invalidation, title: 'invalid', color: '#ff8fa3' });   // Reaper never sells your / the models' trade on the thesis — don't draw it there
  }
  const own = num(p?.supply ?? c?.supply ?? rv?.supply) > 0;
  const supplySrc = p?.supplySrc || c?.supplySrc || rv?.supplySrc || (!supply ? null : own ? 'kernel' : num(lp?.mc) > 0 ? 'live cap ÷ price' : isLaunchpadMint(mint) ? 'launchpad' : null);
  return { mint, pair, symbol, price, supply, supplySrc, mc, lines, held: !!p,
    markers: chartMarkers(tapeOf(o.tape, { mint, n: 120 }), p?.fills) };
}

export const supplyWord = s => (!(s > 0) ? 'UNKNOWN' : s >= 1e9 ? `${(s / 1e9).toLocaleString('en-US', { maximumFractionDigits: 2 })}B` : `${(s / 1e6).toLocaleString('en-US', { maximumFractionDigits: 1 })}M`);

// ── the decision panel ───────────────────────────────────────────────────────────────────────────────────────────────────────────
// what the kernel (a candidate) or Reaper (a position) has decided about one coin, with the evidence behind it — no invented confidence
export function decisionOf(d, mint) {
  if (!mint) return null;
  const o = d?.office || {}; const p = (o.positions || []).find(x => x.mint === mint); const c = ((o.kernel || {}).candidates || []).find(x => x.mint === mint);
  const rv = (o.ownerReview || []).find(x => x.mint === mint);
  const out = { mint, symbol: p?.symbol || c?.symbol || rv?.symbol || null, owner: rv?.mode || c?.owner || null };
  if (p) {
    out.kind = 'position'; out.verdict = p.decision || p.state || 'HOLD'; out.rule = p.rule || null; out.obeying = p.obeying || null;
    out.reasons = [p.evidence, ...(Array.isArray(p.why) ? p.why : [])].filter(Boolean).map(String).slice(0, 6);
    out.facts = [['since entry', p.pct], ['peak', p.peak], ['take line', p.take], ['stop', p.stop], ['held', p.heldMin], ['next review', p.nextReview]];
    out.chart = { structure: p.structure || null, quality: p.quality || p.data?.state || null, run: p.run || null, phase: p.phase || null };
  }
  if (c) {
    const dv = devilOf(c);
    if (!p) { out.kind = 'candidate'; out.verdict = VERD[rowState(c)]; out.state = rowState(c); out.reasons = [c.why].filter(Boolean); }
    out.kernel = { status: c.status, rank: c.rank, trigger: c.trigger, narrative: c.narrative, devil: dv, size: c.size, sizeWhy: c.sizeWhy, courier: c.courier, unknown: c.unknown || [] };
    out.market = { liq: num(c.liq), vol5m: num(c.vol5m), move5m: num(c.move5m), buyShare: num(c.buyShare), ageMin: num(c.ageMin), fresh: c.fresh || null };
  }
  if (!p && !c && rv) { out.kind = 'review'; out.verdict = rv.state; out.reasons = [rv.why].filter(Boolean); out.review = rv; }
  if (!p && !c && !rv) return null;
  return out;
}

// ── the review queue ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
// the trench desk's age buckets (the kernel's freshness ladder) — a candidate with no known age is in none of them
export const AGE_BUCKETS = [['all', 'All', 0, Infinity], ['0-5', '0–5m', 0, 5], ['5-15', '5–15m', 5, 15], ['15-60', '15–60m', 15, 60], ['60-180', '1–3h', 60, 180], ['180-360', '3–6h', 180, 360]];
export function inBucket(c, k) {
  const b = AGE_BUCKETS.find(x => x[0] === k); if (!b || k === 'all') return true;
  const m = num(c?.ageMin); return m != null && m >= b[2] && m < b[3];
}
export const bucketCounts = cands => Object.fromEntries(AGE_BUCKETS.map(([k]) => [k, (cands || []).filter(c => inBucket(c, k)).length]));
// the queue the owner reads: the coins the kernel is weighing (not the ones already on the card), newest first
export function reviewQueue(cands, k = 'all') {
  return (cands || []).filter(c => !['HELD', 'EXIT_PENDING'].includes(c.status) && inBucket(c, k))
    .sort((a, b) => (num(a.ageMin) ?? 1e9) - (num(b.ageMin) ?? 1e9) || (b.rank || 0) - (a.rank || 0));
}

// ── the seat's state, in the cockpit's words ─────────────────────────────────────────────────────────────────────────────────────
// OPEN (nothing can take it) · HUNTING (open, READY coins on the desk) · ARMED (the buy is in flight) · HELD · PROTECT (Reaper's trail /
// protect) · ROTATE (a challenger beats it by the switch margin this pass) · EXITING (Reaper ruled EXIT / TAKE — the sell is on its way)
export const STATE_CLS = { HUNTING: 'is-hunt', ARMED: 'is-pend', HELD: 'is-hold', PROTECT: 'is-good', ROTATE: 'is-rot', EXITING: 'is-bad', OPEN: 'is-open' };
export function seatState(s, readyN = 0) {
  if (!s || s.open) return readyN > 0 ? 'HUNTING' : 'OPEN';
  if (s.buying) return 'ARMED';
  const r = String(s.reaper || s.badge || '').toUpperCase();
  if (/EXIT|TAKE/.test(r)) return 'EXITING';
  if (/PROTECT/.test(r)) return 'PROTECT';
  if (s.rotate) return 'ROTATE';
  return 'HELD';
}

// ── the mission ribbon (every number is the real card's own; unknown = "—") ──────────────────────────────────────────────────────
export function missionTiles(d, seats) {
  const o = d?.office || {}; const m = o.mission || {}; const ops = o.ops || {}; const ss = o.seatSummary || {}; const x = o.execution || {}; const cy = o.cycle || {};
  const v = num(m.value); const pin = num(m.putIn); const net = v != null && pin != null ? v - pin : null;
  const held = (seats || []).filter(z => !z.open).length; const all = (seats || []).length || num(ss.target);
  const be = num(m.toBreakeven); const la = m.lastAction;
  return [
    { k: 'putin', label: 'PUT IN', val: pin, fmt: 'usd' },
    { k: 'equity', label: 'CURRENT EQUITY', val: v, fmt: 'usd', live: true, meter: v != null && pin ? v / pin : null, meterCls: v != null && pin && v >= pin ? 'is-good' : 'is-bad' },
    { k: 'net', label: 'NET P&L', val: net, fmt: 'usd', live: true, sub: net != null && pin ? `${((net / pin) * 100).toFixed(1)}% of put in` : null, cls: net == null ? '' : net >= 0 ? 'm-pos' : 'm-neg' },
    { k: 'phase', label: 'PHASE', text: m.phase || '—', sub: m.phase === 'RECOVERY' ? '1 of 2 · to breakeven' : m.phase === 'GROWTH' ? '2 of 2 · to 2× put-in' : m.phase === 'GRADUATED' ? '2× reached' : null, cls: m.phase === 'RECOVERY' ? 'is-warn' : m.phase ? 'm-pos' : '' },
    { k: 'be', label: 'BREAKEVEN', val: num(m.breakevenTarget ?? m.putIn), fmt: 'usd', meter: v != null && num(m.breakevenTarget ?? m.putIn) ? v / num(m.breakevenTarget ?? m.putIn) : null, meterCls: be != null && be >= 0 ? 'is-good' : 'is-bad', sub: be == null ? null : be >= 0 ? '✓ reached' : `−$${Math.abs(be).toFixed(2)}${m.needX ? ` · needs ${m.needX}×` : ''}`, subCls: be != null && be < 0 ? 'm-neg' : 'm-pos' },
    m.lives != null ? { k: 'lives', label: 'TEAM LIVES', text: `${m.lives} / ${m.livesOf ?? 9}`, meter: m.lives / (m.livesOf ?? 9), meterCls: m.lives <= 3 ? 'is-bad' : 'is-good', sub: num(m.nextDutyIn) != null ? `next duty ${Math.max(0, Math.round(m.nextDutyIn / 60))}m` : null }
      : (gs => ({ k: 'lives', label: 'TEAM', text: gs.length ? `${gs.filter(g => g.status === 'ACTIVE').length} / ${gs.length} ACTIVE` : '—', meter: gs.length ? gs.filter(g => g.status === 'ACTIVE').length / gs.length : null, meterCls: gs.some(g => g.status === 'PROBATION') ? 'is-warn' : 'is-good',   // the ten-agent lifecycle replaced the 9 lives
        sub: gs.some(g => g.status === 'PROBATION') ? `probation: ${gs.filter(g => g.status === 'PROBATION').map(g => g.role).join(', ')}` : gs.length ? 'judged on real exits' : null,
        cls: gs.some(g => g.status === 'PROBATION') ? 'is-warn' : gs.length ? 'm-pos' : '' }))(o.generations || []),
    { k: 'occ', label: 'OCCUPANCY', text: all ? `${held} / ${all}` : '—', meter: all ? held / all : null, meterCls: all && held < all ? 'is-warn' : 'is-good', sub: ss.bench != null ? `bench ${ss.bench} · ready ${ss.benchReady ?? 0}` : null, cls: all && held < all ? 'is-warn' : '' },
    { k: 'cycle', label: 'CYCLE', text: cy.every ? `${Math.round(cy.every)}s` : '—', meter: num(cy.nextIn) != null && cy.every ? 1 - Math.min(1, cy.nextIn / cy.every) : null, sub: num(cy.nextIn) != null ? `next in ${Math.round(cy.nextIn)}s · ${cy.read ?? 0} read` : null },
    { k: 'last', label: 'LAST REAL ACTION', text: la ? `${String(la.move || '').toUpperCase()} $${la.sym}` : '—', sub: la?.at ? `${Math.max(0, Math.round((Date.now() / 1000 - la.at) / 60))}m ago · ${la.result?.state || 'sent'}` : 'none since the service started', tip: la?.why },
    { k: 'cash', label: 'CASH', val: num(ops.cash ?? ss.cash), fmt: 'usd', sub: 'free card cash' },
    { k: 'keeper', label: 'KEEPER', text: ops.keeper ? String(ops.keeper).toUpperCase() : '—', sub: ops.office ? `office ${String(ops.office).toLowerCase()}` : null, cls: /1 active/i.test(ops.keeper || '') ? 'm-pos' : ops.keeper ? 'is-warn' : '' },
    { k: 'exec', label: 'EXECUTION', text: x.health || ops.execution || '—', meter: x.sends ? (x.fills ?? 0) / x.sends : null, meterCls: x.sends && (x.fills ?? 0) / x.sends < 0.7 ? 'is-warn' : 'is-good', sub: x.sends != null ? `${x.fills ?? 0} of ${x.sends} sends filled / h` : null, cls: (x.health || ops.execution) === 'HEALTHY' ? 'm-pos' : (x.health || ops.execution) === 'BAD' ? 'm-neg' : (x.health || ops.execution) ? 'is-warn' : '', tip: [...(x.why || []), execWords(x.metrics)].filter(Boolean).join(' · ') },
  ];
}

// the Courier's last-hour numbers in words (from the ledger — backend fuse_wallet.exec_metrics); null when none came
export function execWords(m) {
  if (!m) return null;
  const p = [`${m.fills}/${m.sends} filled`, m.expired ? `${m.expired} expired` : null, m.quoteAgeMed != null ? `quote ${m.quoteAgeMed}s old at send` : null,
    m.landMed != null ? `lands in ${m.landMed}s` : null, m.slipMed != null ? `${m.slipMed > 0 ? '+' : ''}${m.slipMed}% vs mid` : null,
    m.staleRefresh ? `${m.staleRefresh} stale quotes refreshed` : null, m.dupesDropped ? `${m.dupesDropped} duplicate requests dropped` : null, m.retries ? `${m.retries} retries` : null];
  return p.filter(Boolean).join(' · ');
}

// ── chart markers: ONE letter per real event (T Trigger · D Devil · W Warden · B buy filled · R Reaper · X exit) ──────────────────
const LETTER = {
  trigger: r => (/ENTER/.test(r.action) ? ['T', '#45e486', 'belowBar', 'circle'] : null),
  devil: r => (/HARD VETO/.test(r.action) ? ['D', '#ff5577', 'aboveBar', 'square'] : /WARNING/.test(r.action) ? ['D', '#f5c451', 'aboveBar', 'square'] : null),
  warden: r => (/^SIZE|VETO/.test(r.action) ? ['W', /VETO/.test(r.action) ? '#ff8fa3' : '#6c9bff', 'aboveBar', 'square'] : null),
  courier: r => (/FILLED|CONFIRMED/.test(r.action) ? (/SELL/.test(r.action) ? ['X', '#fa708c', 'aboveBar', 'arrowDown'] : /BUY/.test(r.action) ? ['B', '#15d16a', 'belowBar', 'arrowUp'] : null) : null),
  reaper: r => (/EXIT/.test(r.action) ? ['X', '#ff5577', 'aboveBar', 'arrowDown'] : /PROTECT|TAKE|HOLD/.test(r.action) ? ['R', '#9fe3ff', 'aboveBar', 'circle'] : null),
};
// → [{time, position, shape, color, text (the letter), price?, id, agent, action, why, mc, at}] — a line with no time is never drawn
export function letterMarkers(rows, fills) {
  const out = []; const hasCourier = (rows || []).some(r => r.agent === 'courier');
  (rows || []).forEach(r => { const f = LETTER[r.agent]; const m = f && f(r); const t = num(r.at); if (!m || !t) return;
    const px = num(r.px); const at = m[0] === 'B' || m[0] === 'X';
    out.push({ time: Math.floor(t), position: px && at ? (m[0] === 'B' ? 'atPriceBottom' : 'atPriceTop') : m[2], ...(px && at ? { price: px } : {}), shape: m[3], color: m[1], text: m[0],
      id: r.id, agent: r.agent, action: r.action, why: r.why, mc: num(r.mc), at: t }); });
  if (!hasCourier) (fills || []).forEach(f => { const t = num(f.at); const px = num(f.px); if (!t) return; const buy = f.side === 'buy';
    out.push({ time: Math.floor(t), position: px ? (buy ? 'atPriceBottom' : 'atPriceTop') : (buy ? 'belowBar' : 'aboveBar'), ...(px ? { price: px } : {}), shape: buy ? 'arrowUp' : 'arrowDown',
      color: buy ? '#15d16a' : '#fa708c', text: buy ? 'B' : 'X', id: `f${t}`, agent: 'courier', action: buy ? 'FILLED BUY' : 'FILLED SELL', why: f.usd != null ? `$${Number(f.usd).toFixed(2)} on the ledger` : 'on the ledger', mc: null, at: t }); });
  return out.sort((a, b) => a.time - b.time);
}

// ── freshness words (the INPUTS tab) ──────────────────────────────────────────────────────────────────────────────────────────────
export function freshWord(sec, { pending = false, partial = false } = {}) {
  if (sec == null) return pending ? 'PENDING' : 'UNAVAILABLE';
  if (partial) return 'PARTIAL';
  return sec <= 15 ? 'LIVE' : sec <= 120 ? 'FRESH' : sec <= 600 ? 'PARTIAL' : 'STALE';
}
const age = (t, now) => (num(t) ? Math.max(0, Math.round(now - num(t))) : null);
// one row per input the agents read: [label, word, seconds | null, what it is]
export function inputsOf({ c, pos, live, mc, nowMs = Date.now() }) {
  const now = nowMs / 1000; const t = c?.times || {}; const un = new Set(c?.unknown || []);
  const px = live?.at ? Math.max(0, Math.round((nowMs - live.at) / 1000)) : age(t.price, now) ?? c?.ages?.price ?? null;
  const candle = pos?.data?.ageSec != null ? Math.round(pos.data.ageSec) : age(t.candle, now) ?? c?.ages?.candle ?? null;
  const liq = age(t.market, now) ?? c?.ages?.market ?? null;
  const hold = age(t.holders, now) ?? c?.ages?.holders ?? null; const wal = age(t.wallets, now) ?? c?.ages?.wallets ?? null; const res = age(t.research, now) ?? c?.ages?.research ?? null;
  const sought = !!c;
  return [
    ['price', freshWord(px, { pending: sought }), px, 'live price (shared 3s poller, else the kernel)'],
    ['candles', freshWord(candle, { pending: sought }), candle, pos?.data?.label || 'the candles service (1-minute rows)'],
    ['market cap', mc ? freshWord(px, { pending: sought }) : 'UNAVAILABLE', mc ? px : null, mc ? 'price × the resolved supply' : 'no supply known — never charted as price'],
    ['liquidity', freshWord(liq, { pending: sought }), liq, 'pool depth from the launch board'],
    ['holders', freshWord(hold, { pending: sought && un.has('holders'), partial: hold != null && un.has('holders') }), hold, 'holder scan (top-10, insiders, bundles)'],
    ['early wallets', freshWord(wal, { pending: sought && (un.has('early wallets') || un.has('wallets')), partial: wal != null && un.has('early wallets') }), wal, "the launch's first buyers"],
    ['social / research', freshWord(res, { pending: sought && un.has('research') }), res, 'site / X from the coin record'],
    (() => { const am = c?.ageMin != null ? Number(c.ageMin) : pos?.launch?.ageH != null ? Number(pos.launch.ageH) * 60 : null; const pad = pos?.launch?.pad;
      return ['launch metadata', am != null || pad ? 'FRESH' : sought || pos ? 'PENDING' : 'UNAVAILABLE', null, am != null ? `launched ${Math.round(am)}m ago${pad ? ` · ${pad}` : ''}` : pad ? `${pad} · launch time not known yet` : 'launch time not known yet']; })(),
  ];
}

// ── the trace: each desk's answer for ONE coin (the kernel's own trace when the office built one, else each role's newest tape line) ─
export const CHAIN = ['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge'];
export function traceOf(o, mint) {
  if (!mint) return null;
  const q = (o?.queue || []).find(x => x.mint === mint)?.trace || (o?.currentCase?.mint === mint ? o?.currentCase?.trace : null);
  const fromKernel = q?.lines ? Object.fromEntries(q.lines.map(l => [l[0], { word: l[1], why: l[2], src: 'kernel trace' }])) : {};
  const lastBy = {}; (o?.tape || []).filter(r => r.mint === mint).forEach(r => { if (!lastBy[r.agent] || r.id > lastBy[r.agent].id) lastBy[r.agent] = r; });
  const lines = CHAIN.map(a => { const k = fromKernel[a]; const t = lastBy[a];
    return { agent: a, word: k?.word || t?.action || null, why: k?.why || t?.why || null, at: t?.at || null, id: t?.id ?? null, src: k ? k.src : t ? 'tape' : null }; });
  return { mint, lines, final: q?.final || null, why: q?.why || null };
}

// ── real-event pulses: the agents whose newest tape id moved since the last look (the first look pulses nothing) ──────────────
export function maxIdByAgent(rows) { const m = {}; (rows || []).forEach(r => { if (r.agent && (m[r.agent] == null || r.id > m[r.agent])) m[r.agent] = r.id; }); return m; }
export function newEvents(prev, rows) {
  if (!prev) return {};
  const cur = maxIdByAgent(rows); const out = {};
  Object.entries(cur).forEach(([a, id]) => { if (prev[a] == null || id > prev[a]) out[a] = id; });
  return out;
}

// ── the review queue's status word ───────────────────────────────────────────────────────────────────────────────────────────────
export function queueStatus(c) {
  if (!c) return 'TRACKING';
  if (c.owner === 'arm') return 'ARMED';
  if (c.status === 'ORDER_PENDING') return 'PENDING';
  if (c.status === 'READY') return 'READY';
  if (c.status === 'CONTENDING') return (c.unknown || []).length ? 'ANALYZING' : 'CONTENDING';
  return num(c.ageMin) != null && c.ageMin < 5 ? 'NEW' : 'TRACKING';
}
export const queueMc = c => mcFrom(c?.price, c?.supply, c?.cap, c?.mint);

// 🌊 the buy / sell vital of a seat's last 90s of real swaps (flow.vital on the server): one word + the green share of the bar
export const FLOW_WORD = { BUYERS: 'BUYERS LEAD', SELLERS: 'SELLERS LEAD', PEAK: 'PEAK', BALANCED: 'BALANCED', THIN: 'THIN TAPE' };
export function flowBar(f) {
  if (!f?.state) return null;
  const pct = Number.isFinite(Number(f.buyPct)) ? Math.max(0, Math.min(100, Number(f.buyPct))) : null;
  return { state: f.state, word: f.state === 'BUYERS' && f.hot ? 'CROWD BUYING' : FLOW_WORD[f.state] || f.state, buy: pct == null ? 0.5 : pct / 100, known: pct != null,
    tone: f.state === 'BUYERS' ? 'is-up' : f.state === 'SELLERS' ? 'is-dn' : f.state === 'PEAK' ? 'is-warn' : 'is-flat',
    line: `${f.buyers ?? 0} buyers · ${f.sellers ?? 0} sellers`, why: f.why || '' };
}

// 💹 every held seat together, live: $ at work, open P&L in $ and % of what is at work, and the seat doing best. null = nothing held.
export function openPnl(seats) {
  const held = (seats || []).filter(s => !s.open && !s.buying && num(s.usd) > 0 && num(s.pct) != null);
  if (!held.length) return null;
  const usd = held.reduce((a, s) => a + num(s.usd), 0); const pnl = held.reduce((a, s) => a + (num(s.pnlUsd) || 0), 0); const cost = usd - pnl;
  const best = held.reduce((a, s) => (a == null || num(s.pct) > num(a.pct) ? s : a), null);
  return { n: held.length, usd, pnl, pct: cost > 0 ? pnl / cost * 100 : null, best: best ? { symbol: best.symbol, pct: num(best.pct), mint: best.mint } : null };
}


// 💵 THE MONEY STRIP (owner, 2026-10-15: "is it making or losing money, what is it holding, why — at a glance"). Pure; every number from the
// payload: the card's value + put in (mission), today's REAL result = closed trades on the trade tape whose last sell landed since local
// midnight (+ the open seats' live P&L apart), the held seats with their live %, the night shift / night guard state (`nightGuard`).
export function moneyOf(d, seats, nowMs = Date.now()) {
  const o = d?.office || {}; const m = o.mission || {}; const v = num(m.value); const pin = num(m.putIn);
  const mid = new Date(nowMs); mid.setHours(0, 0, 0, 0); const since = mid.getTime() / 1000;
  const rows = o.tradeTape?.rows || [];
  const closed = rows.filter(r => !r.open && r.result && (r.sells || []).length && Math.max(...r.sells.map(s => num(s.at) || 0)) >= since);
  const usd = closed.reduce((a, r) => a + (num(r.result.usd) || 0), 0); const won = closed.filter(r => num(r.result.pct) > 0).length;
  const oldest = rows.length ? Math.min(...rows.map(r => num(r.at) || Infinity)) : null;
  const held = (seats || []).filter(s => !s.open);
  const openUsd = held.reduce((a, s) => a + (num(s.pnlUsd) || 0), 0);
  const ng = o.nightGuard || null;
  const night = !ng ? { state: 'day', word: '☀ DAY', tip: 'your own settings (the night shift runs 00:00–09:00)' }
    : ng.paused ? { state: 'paused', word: `🛡 GUARD PAUSED${ng.leftMin != null ? ` · ${ng.leftMin}m` : ''}`, tip: `night guard paused real buys: ${ng.why || 'a line was crossed'} — exits keep running` }
      : ng.night ? { state: 'night', word: '🌙 NIGHT SHIFT', tip: `seats ≤ 15% of the card, chart must say ENTER NOW · guard trips at ${ng.lines?.draw ?? '—'}% down / ${ng.lines?.streak ?? '—'} losses / one rug${ng.drawPct != null ? ` · now ${ng.drawPct}% down` : ''}` }
        : { state: 'day', word: '☀ DAY', tip: `your own settings · the night guard tripped ${ng.trips || 0}× so far` };
  const cy = o.cycle || {}; const passAge = cy.at ? Math.max(0, nowMs / 1000 - cy.at) : null; const every = num(cy.every) || 18;
  return { value: v, putIn: pin, netPct: v != null && pin ? (v / pin - 1) * 100 : null,
    today: { usd: closed.length ? usd : null, n: closed.length, won, partial: oldest != null && oldest > since },
    open: held.map(s => ({ seat: s.seat, sym: s.symbol, mint: s.mint, pct: num(s.pct), usd: num(s.pnlUsd), tags: exitTags(s) })), openUsd: held.length ? openUsd : null,
    seats: (seats || []).length, night, late: passAge != null && passAge > every * 3, passAge };
}

// 🛫 💰 🔁 the new exit rules, as chips wherever Reaper's word is shown: runway (a green coin is not banked in its first minutes), half
// banked (R6h scale-out, action 'trim'), comeback (a coin sold green bought back when it ran past our exit). From Reaper's own words only.
export function exitTags(s) {
  const t = [s?.why, s?.rule, s?.reaper, s?.tag, s?.evidence, s?.decision].filter(Boolean).join(' '); const out = [];
  if (/runway/i.test(t)) out.push({ k: 'runway', ic: '🛫', word: 'RUNWAY', tip: 'a green coin is not banked in its first 6 min — the trail still sells it if it gives the gain back' });
  if (/\bR6h\b|half banked/i.test(t) || s?.action === 'trim') out.push({ k: 'half', ic: '💰', word: 'BANKED', tip: `R6h scale-out: most of the coin sold at the take line, the rest rides the trail${/(\d+)% sold/.test(t) ? ` (${t.match(/(\d+)% sold/)[1]}% sold)` : ''}` });
  if (/comeback/i.test(t)) out.push({ k: 'comeback', ic: '🔁', word: 'COMEBACK', tip: 'sold green, ran past our exit, bought back inside the sit-out' });
  return out;
}

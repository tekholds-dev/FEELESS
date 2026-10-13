import { createContext, createElement, useContext, useEffect, useMemo, useSyncExternalStore } from 'react';
import { apiUrl } from './api';
import { useLivePrices } from './livePrices';
import { livePairs, liveOverlay } from './agentLive';
import { devilOf, rowState } from './agentRead';

// 🛰 THE ONE AGENT HUB STORE. Every HQ surface (the Agents tab, the office board, the 3D room, the agents' screens, the seat
// board, the My-cards agent alert, the swap-in agents list) reads THIS store — nobody else fetches agent state.
//
//   INITIAL SNAPSHOT   GET /admin/agents, once
//   LIVE DELTAS        GET /admin/agents/stream (Server-Sent Events over fetch — the HQ session rides in headers): candidate_update ·
//                      hunter_update · position_update · agent_update · lifecycle_update · execution_update · metric_update · mint_update
//                      · decision (one tape line) · owner_update (the owner's review list) · snapshot. `applyDelta` folds one into the snapshot; nothing is rebuilt for a tiny change.
//   FALLBACK           no stream (a test, a proxy that buffers, an old backend): the snapshot is re-read every SNAPSHOT_MS. With the
//                      stream live it is re-read only every SNAPSHOT_LIVE_MS, for the parts that are not delta-streamed (the practice
//                      desk's board and feed), and at once when the server says `resync`.
//
// FRESHNESS STAYS EXPLICIT (`freshness`): the live market price, the kernel's last decision, Sherlock's evidence, the holder scan and
// execution each carry their own age — a price tick never makes a decision or a scan look newer than it is.
export const SNAPSHOT_MS = 20000;
export const SNAPSHOT_LIVE_MS = 60000;
const SESSION_KEY = 'feeless:cc-session';
export const TAPE_KEEP = 120;   // decision-tape lines kept on the page (the snapshot carries 40; the stream adds each as it happens)
const HARD = 'HARD_VETO';

// ── pure: fold one delta into the snapshot ───────────────────────────────────────────────────────────────────────────────────────
const upsert = (list, key, id, data) => { const xs = (list || []).filter(x => x[key] !== id); return data == null ? xs : [...xs, data]; };
const held = c => (['HELD', 'EXIT_PENDING'].includes(c.status) ? 1 : 0);
const kOfCandidate = c => ({ status: c.status, rank: c.rank, why: c.why, trigger: c.trigger, narrative: c.narrative, devil: c.devil || [], hard: (c.devil || []).some(o => o[1] === HARD),
  size: c.size, unknown: c.unknown || [], courier: c.courier });
export function applyDelta(raw, ev) {
  if (!raw || !ev || !ev.kind) return raw;
  const o = raw.office || {}; const k = o.kernel || {}; const { key, data } = ev;
  switch (ev.kind) {
    case 'candidate_update': {
      const prev = (k.candidates || []).find(c => c.mint === key);
      const cands = upsert(k.candidates, 'mint', key, data && { ...prev, ...data }).sort((a, b) => held(b) - held(a) || (b.rank || 0) - (a.rank || 0));
      const table = raw.table && raw.table.some(x => x.mint === key) ? raw.table.map(x => (x.mint === key && data ? { ...x, k: kOfCandidate(data) } : x)) : raw.table;
      return { ...raw, table, office: { ...o, kernel: { ...k, candidates: cands } } };
    }
    case 'hunter_update': return { ...raw, office: { ...o, kernel: { ...k, lanes: data || [] } } };
    case 'position_update': {
      const prev = (o.positions || []).find(p => p.mint === key);
      return { ...raw, office: { ...o, positions: upsert(o.positions, 'mint', key, data && { ...prev, ...data }) } };   // (a position's candles stay the snapshot's)
    }
    case 'agent_update': return { ...raw, office: { ...o, agents: (o.agents || []).map(a => (a.key === key ? { ...a, ...data } : a)) } };
    case 'lifecycle_update': return { ...raw, office: { ...o, generations: data || [] } };
    case 'execution_update': { const d = data || {};
      return { ...raw, office: { ...o, execution: { ...(o.execution || {}), ...(d.courier || {}) }, ready: d.ready ?? o.ready, seat: d.seat ?? o.seat, ops: d.ops ?? o.ops, seatBoard: d.seatBoard ?? o.seatBoard,
        seatSummary: d.seatSummary ?? o.seatSummary, wake: d.wake ?? o.wake, armed: d.armed ?? o.armed, mission: { ...(o.mission || {}), lastAction: d.lastAction ?? (o.mission || {}).lastAction } } }; }
    case 'metric_update': { const d = data || {};
      return { ...raw, office: { ...o, kernel: { ...k, metrics: d.kernel || k.metrics }, enrich: d.enrich || o.enrich, rpcStats: d.rpc || o.rpcStats, stream: d.stream || o.stream } }; }
    case 'mint_update': { if (!data) return raw;
      const cands = (k.candidates || []).map(c => (c.mint === key ? { ...c, price: data.price, times: { ...(c.times || {}), price: data.priceAt }, ...(data.status ? { status: data.status } : {}), ...(data.reaper ? { reaper: data.reaper } : {}) } : c));
      return { ...raw, office: { ...o, kernel: { ...k, candidates: cands }, livePx: { ...(o.livePx || {}), [key]: { price: data.price, at: data.priceAt } } } }; }
    case 'snapshot': return { ...raw, office: { ...o, passAt: data?.at ?? o.passAt } };
    case 'decision': {   // 📜 one REAL kernel decision line (the tape): appended once by its id, newest kept, bounded
      if (!data || data.id == null || (o.tape || []).some(r => r.id === data.id)) return raw;
      return { ...raw, office: { ...o, tape: [...(o.tape || []), data].sort((a, b) => a.id - b.id).slice(-TAPE_KEEP) } };
    }
    case 'ai_update': return data && typeof data === 'object' ? { ...raw, office: { ...o, ai: data } } : raw;   // 🧠 the AI router's provider rows + advice (advisory only)
    case 'owner_update': return { ...raw, office: { ...o, ownerReview: Array.isArray(data) ? data : o.ownerReview } };   // 👤 the owner's review list
    default: return raw;
  }
}

// ── pure: SSE frames out of a text buffer → [events, the unfinished rest] ────────────────────────────────────────────────────────
export function parseSse(buf) {
  const out = []; const parts = String(buf).split('\n\n'); const rest = parts.pop();
  parts.forEach(f => { let kind = 'message'; let id = null; const data = [];
    f.split('\n').forEach(l => { if (l.startsWith('event:')) kind = l.slice(6).trim(); else if (l.startsWith('id:')) id = Number(l.slice(3).trim()); else if (l.startsWith('data:')) data.push(l.slice(5).trim()); });
    if (!data.length) return;   // a beat / a comment
    try { const j = JSON.parse(data.join('\n')); out.push(['hello', 'resync', 'bye'].includes(kind) ? { kind, seq: id, data: j } : { kind, seq: id, ...j }); } catch (e) { /* a torn frame: the next one carries on */ }
  });
  return [out, rest];
}

// ── pure: selectors (the ONLY way a surface reads a decision) ────────────────────────────────────────────────────────────────────
export function selectors(d, now = Date.now() / 1000) {
  const o = d?.office || {}; const k = o.kernel || {};
  const cands = k.candidates || []; const byMint = new Map(cands.map(c => [c.mint, c]));
  const gens = o.generations || [];
  return {
    getAgent: role => ({ ...(o.agents || []).find(a => a.key === role), generation: gens.find(g => g.role === role) || null }),
    getAgents: () => (o.agents || []).map(a => ({ ...a, generation: gens.find(g => g.role === a.key) || null })),
    getGenerations: () => gens,
    getGeneration: role => gens.find(g => g.role === role) || null,
    getMint: mint => byMint.get(mint) || null,
    getCandidate: mint => byMint.get(mint) || null,
    getCandidates: status => (status ? cands.filter(c => c.status === status) : cands),
    getDecision: mint => { const c = byMint.get(mint); return c ? { state: rowState(c), status: c.status, rank: c.rank, why: c.why, devil: devilOf(c) } : null; },
    getDevil: x => devilOf(typeof x === 'string' ? byMint.get(x) : x),
    getSeat: id => (o.seatBoard || []).find(s => s.seat === id) || null,
    getHunter: id => (k.lanes || []).find(l => l.lane === id) || null,
    getHunters: () => k.lanes || [],
    getPosition: mint => (o.positions || []).find(p => p.mint === mint) || null,
    getPositions: () => o.positions || [],
    getBench: () => o.bench || [],
    getTape: mint => (o.tape || []).filter(r => !mint || r.mint === mint),
    getOwnerReview: () => o.ownerReview || [],
    getCounts: () => ({ ...(k.metrics?.byStatus || {}), ready: cands.filter(c => c.status === 'READY').length, contending: cands.filter(c => c.status === 'CONTENDING').length,
      probation: gens.filter(g => g.status === 'PROBATION').map(g => g.role) }),
    getMetrics: () => ({ kernel: k.metrics || null, rpc: o.rpcStats || null, enrich: o.enrich || null, stream: o.stream || null, execution: k.metrics?.execution || null }),
    snapshotAge: () => (o.at ? Math.max(0, Math.round(now - o.at)) : null),
  };
}

// freshness of one coin, each input on its own clock: the live market price · the kernel's decision · Sherlock's research · the holder scan
const ageOf = (t, now) => (t ? Math.max(0, Math.round(now - t)) : null);
export function freshness(c, livePx, nowMs = Date.now()) {
  const now = nowMs / 1000; const t = c?.times || null;
  const mkt = livePx?.at ? Math.max(0, Math.round((nowMs - livePx.at) / 1000)) : t?.price ? ageOf(t.price, now) : c?.ages?.price ?? null;
  return { market: mkt, decision: c?.decidedAt ? ageOf(c.decidedAt, now) : c?.decidedAgo ?? null, research: t ? ageOf(t.research, now) : c?.ages?.research ?? null,
    holders: t ? ageOf(t.holders, now) : c?.ages?.holders ?? null, scan: c?.scan || null };
}

// ── the store (ONE per page; reference-counted: it polls / streams only while something is mounted on it) ────────────────────────
const S = { raw: null, err: null, call: null, refs: 0, subs: new Set(), poll: null, abort: null, seq: 0, live: false, every: SNAPSHOT_MS, loading: null, snap: { raw: null, err: null, live: false } };
const emit = () => { S.snap = { raw: S.raw, err: S.err, live: S.live }; S.subs.forEach(f => f()); };
const session = () => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address && s.sig ? s : null; } catch (e) { return null; } };

// 🧠 THE AI STORE (owner's lag-fix spec, 2026-10-13: "patch only the affected agent card when AI returns — do not re-render the whole
// Agents tab"): the model's answers live in their OWN tiny store. An `ai_update` re-renders only the components that show AI (`useAi`)
// — the seats, chart, tape, matrix and queue never re-render for it. The snapshot's own copy (`office.ai`) is only a first-paint fallback.
const AI = { v: null, subs: new Set() };
export const aiSet = v => { if (v && typeof v === 'object' && v !== AI.v) { AI.v = v; AI.subs.forEach(f => f()); } };
const aiSub = f => { AI.subs.add(f); return () => AI.subs.delete(f); };
const aiGet = () => AI.v;
export function useAi(fallback = null) { const v = useSyncExternalStore(aiSub, aiGet, aiGet); return v || fallback || null; }

export function hubLoad() {
  if (!S.call) return Promise.resolve(null);
  if (S.loading) return S.loading;
  S.loading = S.call('/admin/agents').then(r => { S.raw = r; S.err = null; aiSet(r?.office?.ai); emit(); return r; }).catch(e => { S.err = e; emit(); return null; }).finally(() => { S.loading = null; });
  return S.loading;
}
// a one-off reader (the swap-in picker's 🤖 list): the hub's current snapshot when it is running, else ONE request — never a second poller
export const hubSnapshot = call => (S.raw ? Promise.resolve(S.raw) : call ? call('/admin/agents') : Promise.resolve(null));
export const hubApply = ev => { if (ev?.kind === 'ai_update') { aiSet(ev.data); return; } const next = applyDelta(S.raw, ev); if (next !== S.raw) { S.raw = next; emit(); } };
// ⚡ STREAM deltas are folded in at once but PAINTED together: a kernel pass sends a burst (one delta per candidate that changed) and each
// used to re-render the whole Agents tab — dozens of full renders inside a second, every pass. Now ≤ one paint per EMIT_MS.
export const EMIT_MS = 400;   // 150 → 400 (2026-10-13): a busy pass still meant ~6 whole-tab renders a second; live prices and P&L ride their own poller, the owner's taps are instant (hubApply)
let emitTimer = null;
// 💤 A BACKGROUND TAB COLLECTS, IT DOES NOT PAINT (2026-10-13: the server counted 3 live copies of the Agents tab, each re-rendering on
// every delta while out of sight): deltas keep folding into the snapshot, the page paints ONCE when it is shown again.
const hidden = () => typeof document !== 'undefined' && document.hidden;
const emitSoon = () => {
  if (hidden()) { S.dirty = true; return; }
  if (process.env.NODE_ENV === 'test') { emit(); return; }
  if (!emitTimer) emitTimer = setTimeout(() => { emitTimer = null; emit(); }, EMIT_MS);
};
const onVisible = () => { if (!hidden() && S.dirty) { S.dirty = false; emit(); } };
export const streamApply = ev => { if (ev?.kind === 'ai_update') { aiSet(ev.data); return; } const next = applyDelta(S.raw, ev); if (next !== S.raw) { S.raw = next; emitSoon(); } };   // AI never repaints the tab

async function runStream() {
  const s = session();
  if (!s || typeof fetch !== 'function' || typeof TextDecoder === 'undefined' || S.abort) return;
  const ac = new AbortController(); S.abort = ac;
  try {
    const res = await fetch(apiUrl(`/api/reputation/admin/agents/stream?since=${S.seq || 0}`), { signal: ac.signal, headers: { 'x-admin-address': s.address, 'x-admin-ts': String(s.ts), 'x-admin-sig': s.sig, Accept: 'text/event-stream' } });
    if (!res.ok || !res.body || !res.body.getReader) throw new Error(`stream ${res.status}`);
    const rd = res.body.getReader(); const dec = new TextDecoder(); let buf = '';
    for (;;) {
      const { done, value } = await rd.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      const [evs, rest] = parseSse(buf); buf = rest;
      evs.forEach(e => {
        if (e.kind === 'hello') { S.live = true; S.seq = e.data?.seq ?? S.seq; if (e.data?.resync || !S.raw) hubLoad(); emit(); }
        else if (e.kind === 'resync') { S.seq = e.data?.seq ?? S.seq; hubLoad(); }
        else if (e.kind !== 'bye') { if (e.seq) S.seq = e.seq; streamApply(e); }
      });
    }
  } catch (e) { /* no stream (offline, a buffering proxy, signed out): the snapshot poll carries on */ }
  if (S.abort === ac) S.abort = null;
  if (S.live) { S.live = false; emit(); }
  if (S.refs > 0) setTimeout(() => { if (S.refs > 0 && !S.abort) runStream(); }, 4000);
}

function start() {
  if (S.poll) return;
  if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisible);
  hubLoad();
  let last = Date.now();
  S.poll = setInterval(() => { const due = S.live ? SNAPSHOT_LIVE_MS : S.every; if (Date.now() - last >= due - 50) { last = Date.now(); if (!(typeof document !== 'undefined' && document.hidden)) hubLoad(); } }, 1000);
  runStream();
}
function stop() { if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisible); if (emitTimer) { clearTimeout(emitTimer); emitTimer = null; } if (S.poll) { clearInterval(S.poll); S.poll = null; } if (S.abort) { try { S.abort.abort(); } catch (e) { /* closed */ } S.abort = null; } S.live = false; }
export function hubReset() { stop(); AI.v = null; AI.subs.clear(); Object.assign(S, { raw: null, err: null, call: null, refs: 0, seq: 0, live: false, loading: null, every: SNAPSHOT_MS, dirty: false }); S.subs.clear(); S.snap = { raw: null, err: null, live: false }; }   // tests

const subscribe = f => { S.subs.add(f); return () => S.subs.delete(f); };
const getSnap = () => S.snap;

export function useAgentHub(call, every = SNAPSHOT_MS) {
  useEffect(() => { if (!call) return undefined;
    if (S.call !== call) { if (S.call && S.refs === 0) { S.raw = null; S.seq = 0; } S.call = call; }
    S.every = every; S.refs += 1; start();
    return () => { S.refs -= 1; if (S.refs <= 0) { S.refs = 0; stop(); } }; }, [call, every]);
  const snap = useSyncExternalStore(subscribe, getSnap, getSnap);
  const raw = snap.raw;
  const livePx = useLivePrices(livePairs(raw));
  const d = useMemo(() => liveOverlay(raw, livePx), [raw, livePx]);
  const sel = useMemo(() => selectors(d), [d]);
  return { d, raw, livePx, sel, load: hubLoad, err: snap.err, live: snap.live };
}

// the store for a subtree (the 3D room, the agents' screens, the office board read the hub from here — never from a fetch of their own)
const Ctx = createContext(null);
export const AgentHubProvider = ({ value, children }) => createElement(Ctx.Provider, { value }, children);
export const useHub = () => useContext(Ctx);
// a surface that may also be rendered alone (a test, a pop-out): its own `o` prop wins, else the hub's office
export const useOffice = o => { const hub = useContext(Ctx); return o || hub?.d?.office || null; };

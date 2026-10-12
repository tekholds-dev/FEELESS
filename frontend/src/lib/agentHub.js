import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLivePrices } from './livePrices';
import { livePairs, liveOverlay } from './agentLive';

// 🛰 THE ONE AGENT HUB STORE (owner's agent-kernel spec, 2026-10-12): the Agents tab reads ONE snapshot of GET /admin/agents (the
// kernel + the office) and overlays the SHARED live-price poller on it. Components never transform agent decisions themselves — they ask the
// selectors below. Freshness is kept apart on purpose: LIVE MARKET DATA (the price poller, seconds) is not the LAST AGENT DECISION (the
// kernel's decidedAgo per coin) and not Sherlock's evidence (research age) — the UI says which is which.
export const SNAPSHOT_MS = 20000;

export function selectors(d, now = Date.now() / 1000) {
  const o = d?.office || {}; const k = o.kernel || {};
  const byMint = new Map((k.candidates || []).map(c => [c.mint, c]));
  return {
    getAgent: role => ({ ...(o.agents || []).find(a => a.key === role), generation: (o.generations || []).find(g => g.role === role) || null }),
    getMint: mint => byMint.get(mint) || null,
    getCandidate: mint => byMint.get(mint) || null,
    getSeat: id => (o.seatBoard || []).find(s => s.seat === id) || null,
    getHunter: id => (k.lanes || []).find(l => l.lane === id) || null,
    getHunters: () => k.lanes || [],
    getPosition: mint => (o.positions || []).find(p => p.mint === mint) || null,
    getBench: () => o.bench || [],
    getMetrics: () => ({ kernel: k.metrics || null, rpc: o.rpcStats || null }),
    snapshotAge: () => (o.at ? Math.max(0, Math.round(now - o.at)) : null),
  };
}

// freshness of one coin, separately: the live market price (the poller), the last agent decision, the evidence
export function freshness(c, livePx, nowMs = Date.now()) {
  const mkt = livePx?.at ? Math.max(0, Math.round((nowMs - livePx.at) / 1000)) : c?.ages?.price ?? null;
  return { market: mkt, decision: c?.decidedAgo ?? null, research: c?.ages?.research ?? null, holders: c?.ages?.holders ?? null };
}

export function useAgentHub(call, every = SNAPSHOT_MS) {
  const [raw, setRaw] = useState(null); const [err, setErr] = useState(null);
  const load = useCallback(() => call('/admin/agents').then(r => { setRaw(r); setErr(null); }).catch(e => setErr(e)), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, every); return () => clearInterval(t); }, [load, every]);
  const livePx = useLivePrices(livePairs(raw));
  const d = useMemo(() => liveOverlay(raw, livePx), [raw, livePx]);
  const sel = useMemo(() => selectors(d), [d]);
  return { d, raw, livePx, sel, load, err };
}

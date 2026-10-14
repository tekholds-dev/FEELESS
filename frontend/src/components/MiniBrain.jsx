// 🧠 The creator's Brain in the mini cat: the same chat as HQ › Agents, on any page. CREATOR WALLET ONLY (`useIsCreator` — the server's
// yes / no) and only with the HQ session the creator already signed (lib/hqCall — it never asks for a signature from here).
import React, { lazy, Suspense, useMemo } from 'react';
import { hqCallFor, readHqSession } from '../lib/hqCall';

const AiChat = lazy(() => import('./command/AiChat').then(m => ({ default: m.AiChat })));

export function MiniBrain({ address }) {
  const call = useMemo(() => hqCallFor(address), [address]);
  if (!address) return null;
  if (!readHqSession(address)) return <div className="cch-gate" data-testid="mini-brain-gate"><b>🧠 BRAIN</b><span>Open HQ once (the ⚡ HQ button) and sign in — the Brain then works from here on every page.</span></div>;
  return <div className="mini-brain" data-testid="mini-brain"><Suspense fallback={<div className="cch-gate"><span>waking the brain…</span></div>}><AiChat call={call} variant="mini" /></Suspense></div>;
}

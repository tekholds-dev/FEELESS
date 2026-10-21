// 🪟 Nexa's chat on the FeeCat page — CREATOR WALLET ONLY (the server's yes / no) and only with the HQ session already signed (lib/hqCall).
// The Brain chat locked to her model: she answers from her own FeeCat desk (record, last read, tunes, notebook).
import React, { lazy, Suspense, useMemo } from 'react';
import { hqCallFor, readHqSession } from '../lib/hqCall';
import { useIsCreator } from './HqPop';

const AiChat = lazy(() => import('./command/AiChat').then(m => ({ default: m.AiChat })));

export function useNexaTab() { return useIsCreator(); }

export function NexaChatTab({ address }) {
  const call = useMemo(() => hqCallFor(address), [address]);
  if (!address) return null;
  if (!readHqSession(address)) return <div className="cch-gate" data-testid="nexa-tab-gate"><b>🪟 NEXA</b><span>Open HQ once (the ⚡ HQ button) and sign in — Nexa then answers here.</span></div>;
  return <section className="paper-panel nexa-tab" data-testid="nexa-tab"><Suspense fallback={<div className="cch-gate"><span>waking Nexa…</span></div>}>
    <AiChat call={call} variant="full" lockProvider="win" title="🪟 NEXA · FeeCat's model" /></Suspense></section>;
}

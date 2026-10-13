import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { useAgentHub, streamApply, hubReset } from './agentHub';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./livePrices', () => ({ useLivePrices: () => new Map() }));

const SNAP = { office: { kernel: { candidates: [{ mint: 'M', symbol: 'A', status: 'READY', rank: 150 }] }, tape: [] } };
const setHidden = v => Object.defineProperty(document, 'hidden', { configurable: true, get: () => v });

test('💤 a background tab folds the stream in but paints only once it is shown again', async () => {
  let renders = 0; let last = null;
  const call = jest.fn(async () => SNAP);
  function Probe() { const h = useAgentHub(call); renders += 1; last = h.d; return null; }
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<Probe />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(last?.office?.kernel?.candidates?.[0]?.rank).toBe(150);
  const before = renders;
  setHidden(true);
  await act(async () => { for (let i = 0; i < 5; i += 1) streamApply({ kind: 'candidate_update', key: 'M', data: { mint: 'M', symbol: 'A', status: 'READY', rank: 151 + i } }); });
  expect(renders).toBe(before);                                                 // out of sight: nothing re-rendered
  setHidden(false);
  await act(async () => { document.dispatchEvent(new Event('visibilitychange')); });
  expect(renders).toBe(before + 1); expect(last.office.kernel.candidates[0].rank).toBe(155);   // ONE paint, with every delta folded in
  await act(async () => { root.unmount(); });
  hubReset(); setHidden(false);
});

test('🧠 an AI answer repaints only what shows AI — the Agents tab itself does not re-render', async () => {
  const { useAi } = require('./agentHub');
  let tab = 0; let card = 0; let seen = null;
  const call = jest.fn(async () => SNAP);
  function Tab() { useAgentHub(call); tab += 1; return <Card />; }
  const Card = React.memo(function Card() { const ai = useAi(); card += 1; seen = ai; return null; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<Tab />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const [t0, c0] = [tab, card];
  await act(async () => { streamApply({ kind: 'ai_update', key: 'ai', data: { notes: { M: { sherlock: { advice: { stance: 'FAVOR', narrative: 'cat meta' } } } }, metrics: { queue: 1 } } }); });
  expect(tab).toBe(t0); expect(card).toBe(c0 + 1); expect(seen.notes.M.sherlock.advice.narrative).toBe('cat meta');
  await act(async () => { root.unmount(); });
  hubReset();
});

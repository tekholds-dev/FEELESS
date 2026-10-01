import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { useCoinEdge, fetchEdgeIntel } from './coinEdge';
import { usePumpPulse } from './pumpPulse';
import { useVerified } from './verifyBatch';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const A = 'Aaaa1111111111111111111111111111111111111111', B = 'Bbbb1111111111111111111111111111111111111111';
function Probe({ m }) { const e = useCoinEdge(m); const p = usePumpPulse(m); const v = useVerified(m); return <i data-m={m}>{e?.signals?.length || 0}|{p?.m5Change ?? '-'}|{v?.level || '-'}</i>; }

test('every hook for every coin on screen shares ONE batched edge request', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ edge: { [A]: { pulse: { m5Change: 3 }, verify: { level: 'verified' }, signals: [{ kind: 'bond' }] }, [B]: { pulse: null, verify: null, signals: [] } } }) }));
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<><Probe m={A} /><Probe m={B} /><Probe m={A} /></>); });
  await act(async () => { await new Promise(r => setTimeout(r, 300)); });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(String(global.fetch.mock.calls[0][0])).toMatch(/edge\?mints=(Aaaa.*,Bbbb|Bbbb.*,Aaaa)/);
  expect(el.querySelector(`[data-m="${A}"]`).textContent).toBe('1|3|verified');
  expect(el.querySelector(`[data-m="${B}"]`).textContent).toBe('0|-|-');
});

test('forensics for the tape ask the edge with intel=1, once per minute', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ edge: { [A]: { intel: { creator: 'C', sniperWallets: ['S'] } } } }) }));
  const i1 = await fetchEdgeIntel(A); const i2 = await fetchEdgeIntel(A);
  expect(i1.creator).toBe('C'); expect(i2).toBe(i1); expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(String(global.fetch.mock.calls[0][0])).toContain('intel=1');
});

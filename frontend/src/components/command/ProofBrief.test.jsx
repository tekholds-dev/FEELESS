import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProofBrief } from './ProofDoors';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('📰 the proofs brief: today\'s best proof type with its reason, one bar per type, a tap opens that proof; nothing when the route is missing', async () => {
  const b = { best: 'pob', at: 1794360000, rows: [{ kind: 'pob', filed24: 1, filed7: 14, reviews: 1, avgScore: 46, passPct: 0, right: 6, wrong: 3, rightPct: 67, heat: 62 }, { kind: 'pos', filed24: 1, filed7: 62, reviews: 12, avgScore: 19, passPct: 0, right: 20, wrong: 15, rightPct: 57, heat: 51 }],
    kits: { moved24: [{ kit: 'three', pkg: 'three', v: '0.181.0', prev: '0.180.0' }], tracked: 9 } };
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => b }));
  const picked = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<ProofBrief onPick={k => picked.push(k)} />)); await act(async () => { await Promise.resolve(); });
  const q = s => el.querySelector(`[data-testid="${s}"]`);
  expect(q('proof-brief-best').textContent).toBe('Work in PoB today 14 filed this week, review average 46/100, 67% graded right.');
  expect(q('proof-brief-pos').textContent).toContain('62 wk');
  expect(q('proof-brief').textContent).toContain('three 0.180.0 → 0.181.0');
  await act(async () => q('proof-brief-pos').click()); expect(picked).toEqual(['pos']);
  global.fetch = jest.fn(async () => ({ ok: false, json: async () => ({}) }));
  await act(async () => root.render(<ProofBrief key="2" />)); await act(async () => { await Promise.resolve(); });
  expect(q('proof-brief')).toBeNull();
  await act(async () => root.unmount());
});

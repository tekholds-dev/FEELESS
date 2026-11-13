import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProofBrief } from './ProofDoors';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🃏 the type row: six lit cards carry today\'s numbers, the busiest is HOT, a tap opens that type; with no brief they still switch types', async () => {
  const b = { best: 'pob', at: 1794360000, rows: [{ kind: 'pob', filed24: 1, filed7: 14, reviews: 1, avgScore: 46, passPct: 0, right: 6, wrong: 3, rightPct: 67, heat: 62 }, { kind: 'pos', filed24: 1, filed7: 62, reviews: 12, avgScore: 19, passPct: 0, right: 20, wrong: 15, rightPct: 57, heat: 51 }] };
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => b }));
  const picked = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<ProofBrief k="pos" onPick={k => picked.push(k)} />)); await act(async () => { await Promise.resolve(); });
  const q = s => el.querySelector(`[data-testid="${s}"]`);
  expect(el.querySelectorAll('.pdr-type')).toHaveLength(6); expect(q('pdr-pos').getAttribute('aria-selected')).toBe('true');
  expect(q('proof-brief-pos').textContent).toBe('62 this wk · 57% right'); expect(q('pdr-pob').textContent).toContain('HOT');
  await act(async () => q('pdr-pob').click()); expect(picked).toEqual(['pob']);
  global.fetch = jest.fn(async () => ({ ok: false, json: async () => ({}) }));
  await act(async () => root.render(<ProofBrief key="2" k="pow" />)); await act(async () => { await Promise.resolve(); });
  expect(el.querySelectorAll('.pdr-type')).toHaveLength(6); expect(q('proof-brief-pow').textContent).toBe('Proof of Work');
  await act(async () => root.unmount());
});

test('🖥 the type row and its judge meters are ONE child, so the showcase stage keeps its row (2026-11-13 regression: the meter took the stage slot)', async () => {
  const b = { rows: [], judges: [{ judge: 'collective', rightPct: 71, n: 99, beats: false, failAllPct: 72, say: 'x' }] };
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => b }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<ProofBrief k="pos" />)); await act(async () => { await Promise.resolve(); });
  expect(el.children).toHaveLength(1); expect(el.firstElementChild.className).toBe('pdr-brief');
  expect(el.firstElementChild.querySelector('[data-testid="proof-brief"]')).not.toBeNull(); expect(el.firstElementChild.querySelector('[data-testid="judge-meters"]')).not.toBeNull();
  await act(async () => root.unmount());
});

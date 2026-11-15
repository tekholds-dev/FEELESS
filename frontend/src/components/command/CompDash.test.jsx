import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { compDash, CompDash } from './CompDash';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const sc = (right, n, kinds) => ({ n, right, acc: Math.round((right / n) * 10000) / 10000, kinds });
const C2 = {
  base: { name: 'Qwen3.5-9B' },
  exam: { n: 28, done: 1794685004, examinees: [
    { id: 'baseline', name: 'Always "won"', kind: 'baseline', score: sc(15, 28, { PoB: { n: 11, right: 7 }, PoW: { n: 8, right: 2 } }) },
    { id: 'comp_mem', name: 'COMP v2 + memory', kind: 'local', score: sc(19, 28, { PoB: { n: 11, right: 8 }, PoW: { n: 8, right: 7 } }) },
    { id: 'ossy', name: 'OSSY', kind: 'own', score: sc(14, 28, { PoB: { n: 11, right: 5 }, PoW: { n: 8, right: 4 } }) },
    { id: 'claude', name: 'Claude', kind: 'flagship' },
  ] },
  run: { iters: 200, curve: { train: [[10, 1.4], [20, 0.4]], val: [[1, 3.6], [20, 0.3]] } },
  race: [{ at: 1, scores: { comp_mem: 0.6, baseline: 0.5 } }, { at: 2, scores: { comp_mem: 0.6786, baseline: 0.5357 } }],
  dataset: { train: 99, valid: 15, test: 28 }, market: { won: 250, lost: 554, flat: 1597, open: 36, nextSettle: 0 },
};

test('the deck ranks every entered mind, measures COMP against guessing and the judges, and lists who has not raced', () => {
  const v = compDash(C2, { rows: 900, goals: { rows: 5000 } });
  expect(v.ranked.map(r => r.id)).toEqual(['comp_mem', 'baseline', 'ossy']);
  expect(v.hero).toEqual({ name: 'COMP + memory', acc: 67.9, overGuess: 14.3, overJudges: 17.9 });
  expect(v.missing).toEqual(['Claude']);
  expect(v.heat[0].cells.find(c => c.k === 'PoW')).toMatchObject({ right: 7, n: 8 });
  expect(v.learn.map(r => r.i)).toEqual([1, 10, 20]);
  expect(v.race[1].comp_mem).toBe(67.9);
  expect(v.fuel).toMatchObject({ rows: 900, goal: 5000, train: 99, test: 28 });
});

test('no exam yet still renders a deck that says so', async () => {
  expect(compDash({}, null)).toMatchObject({ ready: false, hero: null, ranked: [] });
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<CompDash call={() => Promise.resolve({})} lab={null} onWorkshop={() => {}} />); });
  expect(el.textContent).toContain('COMP has not sat an exam yet.');
  expect(el.querySelector('[data-testid="cpd-workshop"]')).not.toBeNull();
});

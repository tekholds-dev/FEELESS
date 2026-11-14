import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AttnExplained, attnRead, attnSay, datasetRead, examVerdict } from './CompExplain';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const attn = { tokens: ['liq', ' ', 'age', ' ', 'buy'], heads: [
  [[1, 0, 0, 0, 0], [.5, .5, 0, 0, 0], [.3, .3, .4, 0, 0], [.2, .2, .3, .3, 0], [.6, .05, .2, .05, .1]],
  [[1, 0, 0, 0, 0], [.5, .5, 0, 0, 0], [.3, .3, .4, 0, 0], [.2, .2, .3, .3, 0], [.6, .1, .2, 0, .1]]] };

test('where it looks: the heads blended, the strongest word vs the weakest real word, said plainly', () => {
  const r = attnRead(attn);
  expect(r.tokens[r.top]).toBe('liq'); expect(r.tokens[r.low]).toBe('age'); expect(r.ratio).toBeCloseTo(3);
  expect(attnSay(r)).toBe('Guessing what comes after “buy”, it leaned on “liq” most: 3× more than “age”.');
  expect(r.w[0]).toBe(1); expect(r.heads).toHaveLength(2);
  expect(attnRead({ tokens: ['a'], heads: [[[1]]] })).toBeNull(); expect(attnRead(null)).toBeNull();
});

test('split heads shows one lit strip per head; blended by default', () => {
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<AttnExplained peek={{ step: 9, attn }} />));
  expect(host.querySelector('[data-testid=cex-heads]')).toBeNull();
  act(() => { host.querySelector('[data-testid=cex-split]').click(); });
  expect(host.querySelectorAll('[data-testid=cex-heads] li')).toHaveLength(2);
  act(() => root.unmount()); host.remove();
});

test('the dataset and the exam, each in one line', () => {
  const d = { rows: 130, pairs: 61, duels: 1, goals: { rows: 1000, pairs: 200 }, kinds: [{ kind: 'PoB', rows: 71, won: 40, lost: 31, flat: 0, open: 2 }, { kind: 'PoW', rows: 59, won: 30, lost: 29, flat: 0, open: 1 }] };
  const r = datasetRead(d);
  expect(r.say).toBe('130 rows to learn from. Closest to a fine-tune: PoB at 7% of 1,000. 61 right-vs-wrong pairs, 31% of the 200 that make preference training worth it.');
  expect(r.rows.map(x => x.kind)).toEqual(['PoB', 'PoW', '⚔ Duels']);
  const exam = { examinees: [{ id: 'comp', kind: 'local', name: 'COMP v2', score: { acc: 0.62 } }, { id: 'baseline', kind: 'baseline', name: 'Majority', score: { acc: 0.55 } },
    { id: 'claude', kind: 'flagship', name: 'Claude', score: { acc: 0.7 } }, { id: 'gpt', kind: 'flagship', name: 'GPT', blocked: 'no key' }] };
  expect(examVerdict(exam)).toBe('COMP v2 got 62% right: 7 points above always-guess-the-majority (55%), 8 points behind Claude (70%).');
  expect(examVerdict({ examinees: [] })).toBe('');
});

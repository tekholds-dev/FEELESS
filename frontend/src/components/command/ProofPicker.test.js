import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ProofPicker, { filterFiles, pickerKinds } from './ProofPicker';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const D = {
  powFolders: [{ id: 'w1', n: 1, topic: 'Old PoW', at: 100 }, { id: 'w2', n: 2, topic: 'New PoW', at: 300 }],
  pobFolders: [{ id: 'b1', n: 4, topic: 'Will SOL flip ETH', at: 200 }],
  psFolders: [{ id: 's1', n: 1, name: 'Landing page', at: 50 }],
};
const W = { w1: { score: 210, top: 300, rank: 'A' }, b1: { score: 40, top: 300, rank: 'D' } };
const key = (el, k) => act(() => { el.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true })); });

test('every proof type is a slice; its proofs come newest first with their pot score, unscored ones say so', () => {
  const ks = pickerKinds(D, W);
  expect(ks.map(k => k.kind)).toEqual(['PoW', 'PoP', 'PoB', 'PoC', 'PoStatic', 'PoEco']);
  expect(ks.map(k => k.win)).toEqual(['pow', 'pop', 'bids', 'poc', 'postatic', 'poe']);   // the desk window each one opens in
  const pow = ks[0].files; expect(pow.map(f => f.id)).toEqual(['w2', 'w1']);
  expect(pow[1]).toMatchObject({ score: 210, rank: 'A', top: 300 }); expect(pow[0]).toMatchObject({ score: null, rank: null });
  expect(ks[1].files).toEqual([]);
  const ps = pickerKinds({ psFolders: [{ id: 'a', n: 61, topic: 'Game', at: 3 }, { id: 'b', n: 61, topic: 'Shop', at: 2 }, { id: 'c', n: 61, topic: 'PoStatic ad', at: 4 }, { id: 'e', n: 7, topic: 'Ad  PoEco', at: 5 }] }, {})[4].files;
  expect(ps.map(f => [f.id, f.n])).toEqual([['a', null], ['b', null]]);   // ad builds left out; a number two proofs share is not shown
  expect(filterFiles(pow, 'new').map(f => f.id)).toEqual(['w2']); expect(filterFiles(pow, '#1').map(f => f.id)).toEqual(['w1']); expect(filterFiles(pow, 'rank a').map(f => f.id)).toEqual(['w1']);
});

test('keyboard: arrows turn the wheel and walk the cards, Enter opens that proof in its window, Esc closes', () => {
  const picks = []; let closed = 0;
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<ProofPicker d={D} weights={W} onPick={p => picks.push(p)} onClose={() => { closed += 1; }} />));
  const q = host.querySelector('[data-testid=ppk-q]'); expect(document.activeElement).toBe(q);
  expect(host.querySelector('[data-testid=ppk-slice-PoW]').getAttribute('aria-selected')).toBe('true');
  key(q, 'ArrowDown'); key(q, 'Enter');
  expect(picks.pop()).toEqual({ win: 'pow', kind: 'PoW', id: 'w1' });
  key(q, 'ArrowRight'); key(q, 'ArrowRight');   // PoW → PoP → PoB
  expect(host.querySelector('[data-testid=ppk-slice-PoB]').getAttribute('aria-selected')).toBe('true');
  key(q, 'Enter'); expect(picks.pop()).toEqual({ win: 'bids', kind: 'PoB', id: 'b1' });
  key(q, 'ArrowLeft'); expect(host.querySelector('[data-testid=ppk-none]')).not.toBeNull();   // PoP: nothing filed, it says so
  key(q, 'Escape'); expect(closed).toBe(1);
  act(() => root.unmount()); host.remove();
});

test('touch: tap a slice, tap a card', () => {
  const picks = []; const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<ProofPicker d={D} weights={W} onPick={p => picks.push(p)} onClose={() => {}} />));
  act(() => { host.querySelector('[data-testid=ppk-slice-PoStatic]').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  const cards = host.querySelectorAll('[data-testid=ppk-card]'); expect(cards.length).toBe(1);
  act(() => { cards[0].dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(picks).toEqual([{ win: 'postatic', kind: 'PoStatic', id: 's1' }]);
  act(() => root.unmount()); host.remove();
});

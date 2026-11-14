import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CollectiveIdeas, formOf, collectivePick } from './CollectiveIdeas';

const P = [{ id: 1, agent: 'Happy', kind: 'PoB', stamp: { state: 'proved' } }, { id: 2, agent: 'Happy', kind: 'PoB', stamp: { state: 'proved' } },
  { id: 3, agent: 'Fee', kind: 'PoW', stamp: { state: 'not' } }, { id: 4, agent: 'Fee', kind: 'PoW', stamp: { state: 'proved' } },
  { id: 5, agent: 'Fee', kind: 'PoW', label: '$BONK', stamp: { state: 'open' }, at: 9 }, { id: 6, agent: 'Happy', kind: 'PoB', label: 'Lakers', stamp: { state: 'open' }, at: 1 }];

test('form ranks by record, each agent backs the best but its own, and the pick comes from the best record', () => {
  const f = formOf(P);
  expect(f.map(a => [a.agent, a.proved, a.settled])).toEqual([['Happy', 2, 2], ['Fee', 1, 2]]);
  expect(f[0].backers).toEqual(['Fee']); expect(f[1].backers).toEqual(['Happy']);
  expect(collectivePick(P, f).label).toBe('Lakers');
});

test('it shows form, the pick and a settled rival with the loser', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CollectiveIdeas d={{ proofs: P, rivals: [{ ticker: 'T', title: 'Lakers win', yes: 'Happy', no: 'Fee', result: 'yes', winner: 'Happy', loser: 'Fee' }] }} />); });
  expect(el.querySelector('[data-testid="cix-form"]').textContent).toContain('2/2 proved');
  expect(el.querySelector('[data-testid="cix-pick"]').textContent).toContain('Lakers');
  expect(el.querySelector('[data-testid="cix-rivals"]').textContent).toContain('Fee lost');
});

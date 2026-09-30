import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const { MetaCard } = require('./MetaCard');
const { CardStudio } = require('./CardStudio');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const setVal = (el, v) => { const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
const CARDS = [
  { key: 'badge:custom-og', kind: 'badge', title: 'OG', subtitle: 'FEELESS badge', glyph: '⭐', lore: 'Here first.', design: 'holo', rarity: 'epic', accent: '#16d67f', accent2: '#f5c451', art: '', holders: 3, earns: [{ pool: 'OG pool', pct: 30 }], earnedEach: 0.2 },
  { key: 'season:s1', kind: 'season', title: 'Diamond Winter', subtitle: 'Season 1 card', glyph: '🏅', lore: '', design: 'obsidian', rarity: 'legendary', holders: 9, earns: [{ pool: 'Season reserve', pct: 10, tierWeighted: true }], earnedEach: 0 },
];

test('card shows art side and money side', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<MetaCard card={{ ...CARDS[0], earnedMine: 0.05 }} size="lg" interactive />); });
  expect(el.textContent).toContain('OG');
  expect(el.textContent).toContain('30% of pot');
  expect(el.textContent).toContain('0.200 SOL');
  expect(el.textContent).toContain('This wallet earned');
  act(() => root.unmount());
});

test('studio: pick a card, edit it live, save it', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: CARDS }) }));
  const POOLS = [{ id: 'p1', name: 'OG pool', wallet: 'Pool1111111111111111111111111111111111111111', pct: 50, mode: 'pct', weights: { 'badge:custom-og': 30 }, fixed: {} }];
  const call = jest.fn(async (path, o) => (path === '/admin/badge-pools' && !o ? { pools: POOLS } : path === '/admin/badge-pools' ? { ok: true } : { ...CARDS[0], ...JSON.parse(o.body) }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<CardStudio call={call} />); });
  expect(el.querySelectorAll('.mc-pick')).toHaveLength(2);
  await act(async () => { el.querySelector('.mc-pick').click(); });
  const title = el.querySelector('.cs-form input');
  await act(async () => { setVal(title, 'Original Gangster'); });
  await act(async () => { [...el.querySelectorAll('.cs-form .m-seg button')].find(b => b.textContent === 'Glitch').click(); });
  expect(el.querySelector('.cs-preview .mc').className).toContain('d-glitch');
  expect(el.querySelector('.cs-preview').textContent).toContain('Original Gangster');
  await act(async () => { el.querySelector('[data-testid="card-save"]').click(); });
  const put = call.mock.calls.find(c => c[0].startsWith('/admin/cards/'));
  expect(put[0]).toBe('/admin/cards/badge:custom-og');
  expect(JSON.parse(put[1].body)).toMatchObject({ title: 'Original Gangster', design: 'glitch' });
  // rewards are edited on the card: % of the OG pool's pot + SOL each
  const pct = el.querySelector('[data-testid="card-rewards"] input');
  expect(pct.value).toBe('30');
  await act(async () => { setVal(pct, '45'); });
  await act(async () => { [...el.querySelectorAll('[data-testid="card-rewards"] button')].find(b => b.textContent === 'Save rewards').click(); });
  const post = call.mock.calls.find(c => c[0] === '/admin/badge-pools' && c[1]?.method === 'POST');
  expect(JSON.parse(post[1].body)).toMatchObject({ id: 'p1', mode: 'pct', weights: { 'badge:custom-og': 45 } });
  if (process.env.DUMP_PANEL) require('fs').writeFileSync('/tmp/claude-0/panels.html', el.innerHTML);
  act(() => root.unmount());
});

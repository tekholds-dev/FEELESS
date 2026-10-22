import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { FamilyDeck, DECK } from './FamilyDeck';

const q = id => document.querySelector(`[data-testid="${id}"]`);
beforeEach(() => { sessionStorage.clear(); global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200, headers: { get: () => null }, json: () => Promise.resolve({ coins: [], open: 0, green: 0, by: {} }), text: () => Promise.resolve('') })); });

test('🧰 the Family Deck runs ten real tools under the block — one at a time, remembered, Books + Members for your own family', async () => {
  expect(DECK).toHaveLength(10);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const tools = jest.fn(() => <div data-testid="seats-table">seats</div>);
  await act(async () => { root.render(<FamilyDeck mine={{ id: 1, book: [{ symbol: 'AAA', who: 'don', usd: 4.2, ret: 0.3 }] }} tools={tools} />); });
  expect(q('family-deck').querySelectorAll('[role="tab"]')).toHaveLength(10);
  expect(q('deck-trades').getAttribute('aria-selected')).toBe('true');
  await act(async () => { q('deck-books').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 50)); });
  expect(q('family-books').textContent).toContain('AAA');
  expect(sessionStorage.getItem('feeless.fam.deck')).toContain('books');
  await act(async () => { q('deck-members').click(); });
  expect(q('seats-table')).not.toBeNull(); expect(tools).toHaveBeenCalledWith('table');
  await act(async () => { root.render(<FamilyDeck mine={null} />); });
  expect(q('family-deck').textContent).toContain('seats show here');
  act(() => root.unmount());
});

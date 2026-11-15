import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { RealShelf } from './RealShelf';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); await act(async () => { createRoot(el).render(node); }); return el; };
const CARDS = [{ id: 'iphone-duo', name: 'iPhone Duo', line: 'Apple · Sept 2026', cat: 'phones', brief: 'A new colourway', remix: true, model: { id: 'm1', name: 'Samsung Galaxy Z Flip 3' } },
  { id: 'ps2', name: 'PlayStation 2', line: 'Sony', cat: 'gaming', brief: 'A 2026 shell', remix: false, model: { id: 'm2', name: 'Sony PlayStation 2' } }];

// Owner 2026-11-15: real products show first; the iPhone Duo is there; one tap adds its model and hands the agent the brief.
test('real products first, filter by kind, one tap takes the card', async () => {
  const took = [];
  const el = await mount(<RealShelf cards={CARDS} cats={[['phones', 'Phones'], ['gaming', 'Gaming']]} onTake={c => took.push(c.id)} />);
  expect(el.querySelector('[data-testid="rws-iphone-duo"]').textContent).toContain('from Samsung Galaxy Z Flip 3');   // says what it starts from
  await act(async () => { el.querySelector('[data-testid="rws-cat-gaming"]').click(); });
  expect(el.querySelector('[data-testid="rws-iphone-duo"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="rws-ps2"]').click(); });
  expect(took).toEqual(['ps2']);
  expect((await mount(<RealShelf cards={[]} />)).innerHTML).toBe('');
});

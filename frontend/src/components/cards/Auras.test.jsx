import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MetaCard, CARD_AURAS, AuraPicker } from './MetaCard';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };

test('15 auras, each renders its own live layer outside the card', async () => {
  expect(CARD_AURAS).toHaveLength(15);
  for (const [id, , , n] of CARD_AURAS) {
    const el = await mount(<MetaCard card={{ key: id, title: 'T', rarity: 'rare', aura: id }} />);
    const layer = el.querySelector(`[data-testid="aura-${id}"]`);
    expect(layer).not.toBeNull(); expect(layer.querySelectorAll('i')).toHaveLength(n);
    expect(layer.nextSibling.className).toContain('mc-idle');            // behind/around, not inside the card face
  }
  const none = await mount(<MetaCard card={{ key: 'x', title: 'T', aura: 'bogus' }} />);
  expect(none.querySelector('.mca')).toBeNull();
});

test('aura picker: none + 15, clicking sets the id', async () => {
  const on = jest.fn();
  const el = await mount(<AuraPicker value="fire" onChange={on} />);
  expect(el.querySelectorAll('button')).toHaveLength(16);
  expect(el.querySelector('[data-testid="aura-pick-fire"]').className).toBe('active');
  await act(async () => { el.querySelector('[data-testid="aura-pick-toxic"]').click(); });
  expect(on).toHaveBeenCalledWith('toxic');
});

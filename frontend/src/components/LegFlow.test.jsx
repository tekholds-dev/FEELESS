import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
jest.mock('../lib/coinEdge', () => ({ useCoinEdge: mint => ({ bs: { '5m': mint === 'BRK' ? { buyUsd: 100, sellUsd: 900 } : { buyUsd: 800, sellUsd: 200 } } }) }));
const { LegFlow } = require('./FuseCard');

test('under each coin: green = bought, red = sold, in proportion — sellers winning shows a sliver of green — plus a lean line', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><LegFlow l={{ mint: 'BRK', symbol: 'Break' }} m5={-6} /><LegFlow l={{ mint: 'QI', symbol: 'QI' }} m5={4} /></>); });
  const brk = el.querySelector('[data-testid="legflow-Break"]');
  expect(brk.querySelector('.fcl-b').style.transform).toBe('scaleX(0.1)');
  expect(brk.querySelector('.fcl-s').style.transform).toBe('scaleX(0.9)');
  expect(brk.querySelector('.fcl-lean').getAttribute('class')).toMatch(/is-down/);
  expect(el.querySelector('[data-testid="legflow-QI"] .fcl-lean').getAttribute('class')).toMatch(/is-up/);
});

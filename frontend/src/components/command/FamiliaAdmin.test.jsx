import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FamiliaAdmin, hitPayout } from './FamiliaAdmin';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RULES = { blockMp: 2400, feeTier: 2.5, turfMax: 12, moveMp: 1500, fuseMinMp: 2000, familiesPerWallet: 2, createUsd: 25, createFeeUsd: 5, hitRate: 0.000025, hitCapUsd: 0.1, hitMinUsd: 1 };
const D = { rules: RULES, live: [], range: {}, blockPrice: { fee: 6000, harbor: 2400 },
  economy: { families: 3, members: 9, bankMp: 12000, topBankMp: 8000, houseMp: 7158, raidsLive: 1, raids24h: 4, cities: [{ key: 'fee', name: 'FEE CITY', plots: 24, held: 2 }, { key: 'harbor', name: 'Pump Harbor', plots: 32, held: 3 }] } };

test('the paid-hit math matches the server and the owner\'s anchors', () => {
  expect(hitPayout(5, 100, 1000, 0.000025, 0.1)).toBeCloseTo(0.000177, 6);                // $5 on a 10x bigger family
  expect(hitPayout(4000, 4000, 4000, 0.000025, 0.1)).toBe(0.1);                             // equal $4K families: the cap
  expect(hitPayout(5, 1000, 100, 0.000025, 0.1)).toBeLessThan(hitPayout(5, 100, 1000, 0.000025, 0.1));
});

test('the control center shows the economy, prices Fee City and saves the rules', async () => {
  const call = jest.fn((p, o) => Promise.resolve(o ? { ...D, rules: { ...RULES, ...JSON.parse(o.body) } } : D));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FamiliaAdmin call={call} />); });
  expect(el.textContent).toContain('7,158'); expect(el.textContent).toContain('6,000 MP');
  expect(el.querySelector('[data-testid="fad-pay"]').textContent).toBe('$0.000177');
  expect(el.textContent).toContain('$20.00');                                                // $25 start → $20 into the family wallet
  const inp = el.querySelector('[data-testid="fad-fuseMinMp"]');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, '2500'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="fad-save"]').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/familia/rules', expect.objectContaining({ method: 'POST' }));
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).fuseMinMp).toBe('2500');
});

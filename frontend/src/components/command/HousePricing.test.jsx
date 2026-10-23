import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { HousePricing, houseExamples, HOUSE_DEFAULT } from './FuseAdminSettings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

test('🏠 house fees: live examples, and save posts all four to HQ › Core', async () => {
  const x = houseExamples(HOUSE_DEFAULT);
  expect(x.creatorOn100).toBe(50); expect(x.roundTrip).toBeCloseTo(0.0199); expect(x.mpPerFeecat).toBe(100);
  expect(houseExamples({ fuseCreatorMaxBps: 99999 }).creatorOn100).toBe(100);
  const call = jest.fn(() => Promise.resolve({ house: { ...HOUSE_DEFAULT, feecatFeePct: 0.5 }, feecatSynced: true }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<HousePricing call={call} initial={{ fuseCreatorMaxBps: 2500 }} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('house-examples').textContent).toContain('$25.00'); expect(q('house-examples').textContent).toContain('100 MP');
  await act(async () => { q('house-save').click(); });
  const [path, opts] = call.mock.calls[0];
  expect(path).toBe('/admin/fees/house'); expect(JSON.parse(opts.body)).toEqual({ fuseCreatorMaxBps: 2500, feecatFeePct: 1, redeemMp: 1000000, redeemFeecat: 10000 });
  expect(q('house-feecat').value).toBe('0.5');
  await act(async () => { root.unmount(); });
});

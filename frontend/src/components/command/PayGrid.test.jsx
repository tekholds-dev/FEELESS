import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PayGrid } from './PayGrid';
import { PAY_OPTIONS, fit } from '../../lib/payOptions';

test('the pay grid ranks for what you pick, filters, and compares up to three', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { createRoot(el).render(<PayGrid />); });
  const order = () => [...el.querySelectorAll('.pg-card')].map(c => c.dataset.testid.replace('pg-card-', ''));
  expect(order().length).toBe(PAY_OPTIONS.length);
  expect(['crossmint', 'stripe', 'reap', 'bvnk']).toContain(order()[0]);   // testing: a sandbox and an API rank first
  await act(async () => { q('pg-lens-small').click(); }); const top = PAY_OPTIONS.find(r => r.k === order()[0]); expect(top.us === 'yes' || top.us === 'partly').toBe(true);   // small customers: works in the US first
  await act(async () => { q('pg-f-sandbox').click(); }); expect(order().every(k => PAY_OPTIONS.find(r => r.k === k).test === 'sandbox')).toBe(true);
  await act(async () => { q('pg-f-sandbox').click(); q('pg-type-ramp').click(); }); expect(order().every(k => PAY_OPTIONS.find(r => r.k === k).type === 'ramp')).toBe(true);
  for (const k of ['coinbase', 'moonpay', 'transak', 'ramp']) await act(async () => { q(`pg-cmp-${k}`).click(); });
  expect(q('pg-compare').querySelectorAll('thead th').length).toBe(4);   // 3 picked + the label column: a 4th pick drops the oldest
  expect(q('pg-compare').textContent).not.toContain('Coinbase Onramp');
});

test('every row has a source, a check word where sources disagree, and an unknown never scores top marks', () => {
  for (const r of PAY_OPTIONS) { expect(r.src.length).toBeGreaterThan(0); expect(r.url).toMatch(/^https:\/\//); if (r.us === 'check') expect(r.usWord).toBeTruthy(); }
  const unknown = { us: 'check', kyc: 'id', test: 'check', api: false, fee: 'Not published', type: 'person' };
  expect(Math.max(fit(unknown, 'test'), fit(unknown, 'small'), fit(unknown, 'wide'))).toBeLessThan(5);
});

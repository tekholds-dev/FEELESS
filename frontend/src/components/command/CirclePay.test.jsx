import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const { CirclePay, payPhrase } = require('./CirclePay');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('Circle payout needs the exact typed phrase, then posts it once', async () => {
  const rows = [{ address: 'A', sol: 0.2 }, { address: 'B', sol: 0.1 }];
  expect(payPhrase(rows)).toBe('PAY 0.3');
  const call = jest.fn(async () => ({ paidSol: 0.3, wallets: 2, failed: [] }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<CirclePay call={call} circle={{ name: 'Reserve', balances: [{ symbol: 'SOL', amount: '1' }] }} rows={rows} path="/admin/reserve/s1/pay-circle" />); });
  await act(async () => { el.querySelector('[data-testid="circle-pay"]').click(); });
  const send = () => [...el.querySelectorAll('button')].find(b => b.textContent.startsWith('Send'));
  expect(send().disabled).toBe(true);
  const input = el.querySelector('[data-testid="circle-pay-input"]');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { setter.call(input, 'PAY 0.3'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(send().disabled).toBe(false);
  await act(async () => { send().click(); });
  expect(call).toHaveBeenCalledWith('/admin/reserve/s1/pay-circle', expect.objectContaining({ body: JSON.stringify({ confirm: 'PAY 0.3' }) }));
  act(() => root.unmount());
});

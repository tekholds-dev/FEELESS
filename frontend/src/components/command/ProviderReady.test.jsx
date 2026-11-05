import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ProviderReady } from './ProviderReady';

test('🔑 shows how many are ready; a click opens that key, and only its name is ever shown', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const call = jest.fn(async () => ({ ready: 1, total: 2, rows: [{ name: 'DFlow', unlocks: 'Kalshi', ready: false, missing: ['DFLOW_API_KEY'], where: 'dflow.net' }, { name: 'Groq', unlocks: 'Backup', ready: true, missing: [], where: 'x' }] }));
  await act(async () => { root.render(<ProviderReady call={call} />); });
  expect(call).toHaveBeenCalledWith('/admin/providers'); expect(el.textContent).toContain('1/2'); expect(el.textContent).toContain('set does not mean funded'); expect(el.textContent).not.toContain('DFLOW_API_KEY');
  await act(async () => { el.querySelector('[data-testid="pvr-DFlow"]').click(); });
  expect(el.textContent).toContain('DFLOW_API_KEY'); expect(el.querySelector('[data-testid="pvr-save-DFlow"]').disabled).toBe(true);
  const box = el.querySelector('[data-testid="pvr-input-DFLOW_API_KEY"]'); expect(box.type).toBe('password');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(box, 'k1'); box.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="pvr-save-DFlow"]').click(); });
  expect(call).toHaveBeenCalledWith('/admin/provider-key', { method: 'POST', body: JSON.stringify({ name: 'DFLOW_API_KEY', value: 'k1' }) });
  await act(async () => { root.unmount(); }); el.remove();
});

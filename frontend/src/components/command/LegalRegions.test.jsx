import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LegalRegions } from './LegalRegions';
jest.mock('react-router-dom', () => ({ Link: ({ to, children, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const F = { site: 'The whole site', swap: 'Swaps', perps: 'Perps' };
const cfg = { version: '2026-11-13', minAge: 18, everywhere: ['CU', 'IR', 'KP', 'SY'], requireAccept: true, features: { site: { blocked: [], ageGate: true }, swap: { blocked: [], ageGate: true }, perps: { blocked: ['GB'], ageGate: true } } };
const view = c => ({ version: '2026-11-13', cfg: c, features: F, sanctioned: ['CU', 'IR', 'KP', 'SY'], accepted: 3, stale: 1, byCountry: [['US', 2], ['DE', 1]], requests: [{ wallet: 'AAAAbbbbccccdddd', kind: 'delete', at: Date.now() / 1000 - 120, counts: { chat: 3, profile: 1 } }] });

test('⚖ HQ Legal & regions: counts + by-country bars + the log; the sanctioned four are locked; closing a country per feature saves the whole cfg', async () => {
  const sent = [];
  const call = jest.fn(async (path, opts) => { if (opts?.method === 'POST') { const b = JSON.parse(opts.body); sent.push(b); return view(b.cfg); } return view(cfg); });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<LegalRegions call={call} />)); await act(async () => { await Promise.resolve(); });
  const q = s => el.querySelector(`[data-testid="${s}"]`);
  expect(q('lgr-accepted').textContent).toBe('3');
  expect(q('lgr-by-country').querySelectorAll('li')).toHaveLength(2);
  expect(q('lgr-log').textContent).toContain('DELETE'); expect(q('lgr-log').textContent).toContain('4 rows');
  expect(q('lgr-every-x-IR')).toBeNull();   // locked: no remove button
  expect(q('lgr-save').disabled).toBe(true);
  const sel = q('lgr-swap-add'); const set = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
  await act(async () => { set.call(sel, 'FR'); sel.dispatchEvent(new Event('change', { bubbles: true })); });
  await act(async () => q('lgr-perps-x-GB').click());
  await act(async () => q('lgr-age-swap').click());
  expect(q('lgr-save').disabled).toBe(false);
  await act(async () => q('lgr-save').click()); await act(async () => { await Promise.resolve(); });
  expect(sent[0].cfg.features.swap).toEqual({ blocked: ['FR'], ageGate: false });
  expect(sent[0].cfg.features.perps.blocked).toEqual([]);
  expect(q('lgr-save').disabled).toBe(true);
  await act(async () => root.unmount());
});

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { perpPlan, quoteMatches } from './RealPerps';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: () => {}, success: () => {} } }));
const mockProvider = { publicKey: { toString: () => 'ME' }, signTransaction: async tx => tx };
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'ME' }, provider: mockProvider }) }));
jest.mock('@solana/web3.js', () => ({ VersionedTransaction: { deserialize: () => ({ message: { staticAccountKeys: [{ toBase58: () => 'ME' }] }, serialize: () => new Uint8Array([1, 2, 3]) }) } }));
const { RealPerps } = require('./RealPerps');

test('📉 the preview math + the quote must match the ticket', () => {
  const p = perpPlan(100, 10, 10, 'long', 0.06);
  expect(p.size).toBe(100); expect(p.per1).toBe(1); expect(p.fee).toBeCloseTo(0.06); expect(p.liq).toBeCloseTo(90.06); expect(p.liqPct).toBeCloseTo(9.94);
  expect(perpPlan(100, 10, 10, 'short').liq).toBeCloseTo(109.94);
  expect(quoteMatches({ side: 'short', positionSizeUsd: '1250' }, 'short', 1250)).toBe(true);
  expect(quoteMatches({ side: 'long', positionSizeUsd: '1250' }, 'short', 1250)).toBe(false);
  expect(quoteMatches({ side: 'short', positionSizeUsd: '600' }, 'short', 1250)).toBe(false);
});

test('📉 the dash: pick SHORT BTC $25 × 50 → Jupiter\'s quote → sign + open → live position → close', async () => {
  const posts = [];
  const POS = { pubkey: 'P1', asset: 'BTC', side: 'short', lev: 50, size: 1250, collateral: 25, entry: 81300, mark: 81000, liq: 82800, pnl: 4.61, pnlPct: 18.4, fees: 0.75 };
  let positions = [];
  global.fetch = jest.fn((u, o) => {
    if (o?.method === 'POST') { const b = JSON.parse(o.body); posts.push([String(u), b]);
      if (String(u).endsWith('/execute')) { positions = [POS]; return Promise.resolve({ ok: true, json: () => Promise.resolve({ txid: 'TXID12345678', action: b.action }) }); }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ transaction: 'AAAA', action: b.act === 'close' ? 'decrease-position' : 'increase-position',
        quote: { side: 'short', positionSizeUsd: '1250', entryPriceUsd: '81300', liquidationPriceUsd: '82810', openFeeUsd: '0.75' } }) }); }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ pools: { BTC: { openFeePercent: 0.06 } }, positions, min: 10, maxLev: 100 }) });
  });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<RealPerps coin="SOL" marks={{ SOL: 103.5, ETH: 3810, BTC: 81300 }} />); }); await act(async () => { await Promise.resolve(); });
  expect(q('real-perps').textContent).toContain('Long or short SOL'); expect(el.querySelectorAll('a[href^="http"]')).toHaveLength(0);
  await act(async () => { q('rp-a-BTC').click(); q('rp-short').click(); q('rp-u-25').click(); q('rp-l-50').click(); });
  expect(q('real-perps').className).toContain('is-short'); expect(q('rp-go').textContent).toContain('REVIEW SHORT BTC');
  await act(async () => { q('rp-go').click(); });
  expect(posts[0][1]).toEqual({ address: 'ME', asset: 'BTC', side: 'short', usd: 25, lev: 50 });
  expect(q('rp-quote').textContent).toContain('$82,810'); expect(q('rp-go').textContent).toContain('SIGN + OPEN SHORT BTC 50×');
  await act(async () => { q('rp-go').click(); }); await act(async () => { await Promise.resolve(); });
  expect(posts[1][0]).toContain('/perps-real/execute'); expect(posts[1][1]).toMatchObject({ address: 'ME', action: 'increase-position' });
  expect(q('rp-pos-0').textContent).toContain('BTC 50×'); expect(q('rp-pos-0').textContent).toContain('+$4.61');
  await act(async () => { q('rp-close-0').click(); });
  expect(posts[2][1]).toEqual({ act: 'close', address: 'ME', positionPubkey: 'P1' }); expect(posts[3][1].action).toBe('decrease-position');
  act(() => root.unmount()); el.remove();
});

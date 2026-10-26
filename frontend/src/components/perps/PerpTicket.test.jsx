import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: () => {}, success: () => {} } }));
jest.mock('@solana/web3.js', () => ({ VersionedTransaction: { deserialize: () => ({ message: { staticAccountKeys: [{ toBase58: () => 'ME' }] }, serialize: () => new Uint8Array([1, 2, 3]) }) } }));
const { PerpTicket, payWith, levToF, fToLev, MAX_LEV } = require('./PerpTicket');
const { PerpPositions } = require('./PerpPositions');
const provider = { signTransaction: async tx => tx };
const wallet = { chain: 'solana', address: 'ME' };

function mockFetch(posts) {
  global.fetch = jest.fn((u, o) => { if (!o) return Promise.resolve({ ok: true, json: () => Promise.resolve({ amount: String(u).includes('EPjF') ? 500 : 2 }) });
    const b = JSON.parse(o.body); posts.push([String(u), b]);
    if (String(u).endsWith('/execute')) return Promise.resolve({ ok: true, json: () => Promise.resolve({ txid: 'TXID12345678' }) });
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ transaction: 'AAAA', action: b.act === 'close' ? 'decrease-position' : String(b.act || '').startsWith('tpsl') ? 'create-tpsl' : 'increase-position',
      quote: { side: b.side, positionSizeUsd: String((b.usd || 0) * (b.lev || 0)), entryPriceUsd: '102.6', liquidationPriceUsd: '98.5', openFeeUsd: '0.15' },
      tpsl: [{ kind: 'tp', pnl: 5.1, pnlPct: 51 }, { kind: 'sl', pnl: -2.4, pnlPct: -24 }] }) }); });
}

test('🎟 TP / SL before the trade ride the open: review → Jupiter quote (+ the P&L at each trigger) → sign → executed', async () => {
  const posts = []; mockFetch(posts);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  let t = { side: 'long', usd: 10, lev: 25, tp: null, sl: null }; let opened = 0;
  const render = () => root.render(<PerpTicket asset="SOL" mark={102.6} pool={{ openFeePercent: 0.06, longBorrowRatePercent: 0.0016 }} t={t} set={x => { t = { ...t, ...x }; render(); }} addr="ME" wallet={wallet} provider={provider} onOpened={() => { opened += 1; }} />);
  await act(async () => { render(); });
  await act(async () => { q('pt-tp-2').click(); q('pt-sl-1').click(); });
  expect(t.tp).toBeCloseTo(104.652, 2); expect(t.sl).toBeCloseTo(101.574, 2);
  expect(q('pt-tpsl').textContent).toContain('+$5.00'); expect(q('pt-tpsl').textContent).toContain('R : R');
  await act(async () => { q('pt-go').click(); });
  expect(posts[0][1]).toMatchObject({ address: 'ME', asset: 'SOL', side: 'long', usd: 10, lev: 25, mark: 102.6 }); expect(posts[0][1].tp).toBeCloseTo(104.652, 2);
  expect(q('pt-quote').textContent).toContain('$98.50'); expect(q('pt-tpsl').textContent).toContain('+$5.10');   // Jupiter's own P&L at the TP
  await act(async () => { q('pt-go').click(); }); await act(async () => { await Promise.resolve(); });
  expect(posts[1][0]).toContain('/perps-real/execute'); expect(posts[1][1]).toMatchObject({ address: 'ME', action: 'increase-position' }); expect(opened).toBe(1);
  await act(async () => { t = { ...t, tp: 100 }; render(); });                                       // a long's TP under the price can never be sent
  expect(q('pt-go').disabled).toBe(true); expect(q('pt-tpsl').textContent).toContain('must be above the price');
  act(() => root.unmount()); el.remove();
});

test('📋 positions: live P&L on the true price, close 50 %, move + cancel a TP — each a Jupiter transaction the wallet signs', async () => {
  const posts = []; mockFetch(posts);
  const P = { pubkey: 'P1', asset: 'SOL', side: 'long', lev: 10, size: 100, collateral: 10, entry: 100, mark: 100, liq: 90.6, tpsl: [{ id: 'R1', kind: 'tp', price: 110 }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<PerpPositions positions={[P]} marks={{ SOL: 102 }} addr="ME" wallet={wallet} provider={provider} />); });
  expect(q('pp-0').textContent).toContain('% ROE'); expect(q('pp-0').textContent).toContain('TP');
  await act(async () => { q('pp-close-0-50').click(); }); await act(async () => { await Promise.resolve(); });
  expect(posts[0][1]).toEqual({ address: 'ME', act: 'close', positionPubkey: 'P1', pct: 50, size: 100 }); expect(posts[1][1].action).toBe('decrease-position');
  await act(async () => { el.querySelector('.pp-x').click(); }); await act(async () => { await Promise.resolve(); });
  expect(posts[2][1]).toEqual({ address: 'ME', act: 'tpsl-cancel', positionRequestPubkey: 'R1' });
  act(() => root.unmount()); el.remove();
});

test('💳 pay with: USDC when it covers the collateral, else SOL (0.01 kept for fees), else none · 🎚 the slider reaches Jupiter\'s 250×', () => {
  expect(payWith(25, { usdc: 30, sol: 0 }, 100).best).toBe('USDC');
  expect(payWith(25, { usdc: 3, sol: 1 }, 100).best).toBe('SOL');
  expect(payWith(25, { usdc: 3, sol: 0.2 }, 100).best).toBe(null);   // (0.2 − 0.01) × $100 = $19 < $25
  expect(MAX_LEV).toBe(250); expect(fToLev(1)).toBe(250); expect(fToLev(0)).toBe(1.1);
  expect(fToLev(levToF(10))).toBe(10); expect(levToF(25)).toBeGreaterThan(0.5);   // log scale: 25× sits past the middle
});

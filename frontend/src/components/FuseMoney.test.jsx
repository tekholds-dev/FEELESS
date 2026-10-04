import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MoneyMath, RoundBell, CardShowcase, CardCosts, TrailSummary, CoinTable } from './FuseMoney';
import { FuseWallet } from './command/FuseWallet';
import { FuseFees } from './command/FuseFees';
import { primeRow } from './ArenaPrime';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = (ms = 0) => act(async () => { await new Promise(r => setTimeout(r, ms)); });
const mount = async el => { const host = document.createElement('div'); document.body.appendChild(host); await act(async () => { createRoot(host).render(el); }); return host; };

test('money math reads PUT IN → IN CARD + PAID OUT = NOW, profit apart from fees', async () => {
  const h = await mount(<MoneyMath putIn={100} held={714.35} paidOut={25} fees={1.2} compounded={300} />);
  const t = h.textContent;
  expect(t).toContain('$100.00'); expect(t).toContain('$714.35'); expect(t).toContain('$25.00'); expect(t).toContain('$739.35');
  expect(t).toContain('+$639.35'); expect(t).toContain('fees $1.20 paid apart');
  expect(t).toContain('♻ $300.00 of take-profits rolled back in');
});

test('tier card rows count only what was PAID OUT as taken (never the gross take-profits)', () => {
  const r = primeRow({ id: 'p', label: 'Gold', startUsd: 100, valueUsd: 739.35, takenUsd: 404.73, walletUsd: 25, cash: 0, pnlPct: 639.35, legs: [] });
  expect(r.realizedUsd).toBe(25);
});

test('round bell shows a 10…1 countdown in the last 10 seconds', async () => {
  const h = await mount(<RoundBell at={Date.now() / 1000 + 7.5} label="ROUND 3" />);
  const b = h.querySelector('[data-testid="round-bell"]');
  expect(b.className).toContain('is-bell'); expect(b.textContent).toContain('8'); expect(b.textContent).toContain('🔔 ROUND 3');
  const h2 = await mount(<RoundBell at={Date.now() / 1000 + 600} />);
  expect(h2.querySelector('.rbell').className).not.toContain('is-bell'); expect(h2.textContent).toMatch(/(10:00|9:59)/);
});

test('3-card showcase puts one card in front and brings a tapped card forward', async () => {
  const cards = [0, 1, 2].map(i => ({ key: `k${i}`, name: `Card ${i}`, pct: i, badge: 'x', sub: 'y' }));
  const opened = [];
  const h = await mount(<CardShowcase cards={cards} onOpen={c => opened.push(c.key)} />);
  expect(h.querySelector('[data-testid="sc3-0"]').className).toContain('p-0');
  act(() => h.querySelector('[data-testid="sc3-2"]').click());
  expect(h.querySelector('[data-testid="sc3-2"]').className).toContain('p-0');
  act(() => h.querySelector('[data-testid="sc3-2"]').click());
  expect(opened).toEqual(['k2']);
});

test('card costs: a receipt before buying, HQ pays no FEELESS fee, auto-fees toggles', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ bundle: { maxPct: 5, swapUsd: 0.1 }, plan: { buyUsd: 0.3, perCoinUsd: 0.1, swapUsd: 0.2, roundsUsd: 0.25, packs: 1, per5Usd: 0.25, swapsUsd: 2, totalUsd: 2.55, pct: 8.5, rounds: 10, free: 5 } }) }));
  const set = [];
  const h = await mount(<CardCosts coins={3} amount={30} autoFees onAutoFees={v => set.push(v)} />); await tick(300);
  expect(h.textContent).toContain('$0.30'); expect(h.textContent).toContain('$2.55'); expect(h.textContent).toContain('8.5%');
  act(() => h.querySelector('[data-testid="auto-fees"]').click()); expect(set).toEqual([false]);
  const s = await mount(<CardCosts coins={3} amount={30} staff />); await tick(300);
  expect(s.textContent).toContain('$0 FEELESS fee');
});

test('trail summary + coin table say what did good, what stays, entry → now', async () => {
  const h = await mount(<><TrailSummary events={[{ kind: 'tp', symbol: 'WIF', usd: 12 }, { kind: 'sl', symbol: 'RUG', usd: 4 }]} legs={[{ symbol: 'SOL', usd: 50 }]} />
    <CoinTable legs={[{ pairAddress: 'p', symbol: 'SOL', entryPx: 150, nowPx: 165, inUsd: 50, nowUsd: 55, pct: 10 }]} /></>);
  const t = h.textContent;
  expect(t).toContain('$WIF'); expect(t).toContain('$12.00 taken'); expect(t).toContain('$RUG'); expect(t).toContain('$50.00 held');
  expect(t).toContain('$150 → $165'); expect(t).toContain('+10.0%');
});

test('HQ Fuse wallet: locked until signing is enabled, tiers, dry run, audit trail', async () => {
  const calls = [];
  const call = jest.fn(async (url, o) => { calls.push([url, o?.body]);
    if (url === '/admin/fuse-wallet/preview') return { orders: [{ side: 'buy', symbol: 'WIF', usd: 10, impactPct: 0.4, route: ['Raydium'] }], networkUsdEst: 0.02, note: 'same coins',
      card: { paperUsd: 104, paperPct: 4, rounds: 3, phase: 'degen', coins: [{ symbol: 'SOL', role: 'anchor', pairAddress: 'p1', weightPct: 50, usd: 10, pricePct: 1.2 }, { symbol: 'WIF', role: 'runner', pairAddress: 'p2', weightPct: 50, usd: 10, pricePct: -3 }] } };
    return { cfg: { walletId: 'w1', address: 'ADDR1234', armed: false, paused: false, maxCardUsd: 100, reserveSol: 0.03 }, signer: false, wallets: [{ id: 'w1', address: 'ADDR1234', name: 'Fuse', blockchain: 'SOL' }],
      balances: { sol: 2, tokens: { LIVE: 25, EMPTY: 0 } }, solUsd: 150, freeSol: 1.97, missing: [], books: {}, tiers: { safe: '💎 Prime Diamond' }, calibration: { impactMult: 1, n: 0 }, totals: { swaps: 0 },
      ledger: [{ at: 1, card: 'safe', side: 'topup', usd: 20, status: 'done' }] }; });
  const h = await mount(<FuseWallet call={call} />); await tick();
  expect(h.querySelector('[data-testid="fw-lock"]')).toBeTruthy();
  expect(h.querySelector('[data-testid="fw-armed"]').disabled).toBe(true);
  expect(h.querySelector('[data-testid="fw-topup-safe"]').disabled).toBe(true);
  expect(h.textContent).toContain('$300.00');   // 2 SOL × $150
  expect(h.textContent).toContain('COINS HELD1'); // zero-balance token accounts are not holdings
  expect(h.querySelector('[data-testid="fw-sol-breakdown"]').textContent).toContain('2.0000 total = 0.0000 card cash + 0.0300 fee reserve + 1.9700 free');
  act(() => h.querySelector('[data-testid="fw-dry-safe"]').click()); await tick();
  expect(h.querySelector('[data-testid="fw-dryrun"]').textContent).toContain('$WIF');
  expect(h.querySelector('[data-testid="fw-dry-status"]').textContent).toContain('round 4');
  expect(h.querySelector('[data-testid="fw-ledger"]').textContent).toContain('topup');
});

test('HQ fee layout: tap a type to filter, a row to see its transaction', async () => {
  const call = jest.fn(async () => ({ rows: [{ kind: 'buy', card: 'c', cardName: 'Ape', wallet: 'WALLET99', symbol: 'A', at: 1, tradeUsd: 10, feeUsd: 0.1, sig: 'SIG1' },
    { kind: 'rounds', card: 'c', cardName: 'Ape', wallet: 'WALLET99', at: 2, tradeUsd: 0, feeUsd: 0.25, auto: true }],
    totals: { buy: { n: 1, usd: 0.1 }, swap: { n: 0, usd: 0 }, sell: { n: 0, usd: 0 }, rounds: { n: 1, usd: 0.25 } }, allUsd: 0.35, tradedUsd: 10, avgPct: 1, cards: 1,
    bundle: { on: true, perLegUsd: 0.1, maxPct: 5, maxLegUsd: 50, swapUsd: 0.1 }, rounds: { per5Usd: 0.25, compoundPay: true }, swapBps: 100,
    example: { buyUsd: 0.3, swapUsd: 0.2, per5Usd: 0.25, totalUsd: 2.55, pct: 12.75 } }));
  const h = await mount(<FuseFees call={call} />); await tick();
  expect(h.querySelector('[data-testid="fee-example"]').textContent).toContain('$2.55');
  expect(h.querySelectorAll('[data-testid^="ff-row-"]').length).toBe(2);
  act(() => h.querySelector('[data-testid="ff-rounds"]').click());
  expect(h.querySelectorAll('[data-testid^="ff-row-"]').length).toBe(1);
  act(() => h.querySelector('[data-testid="ff-all"]').click());
  act(() => h.querySelector('[data-testid="ff-row-0"]').click());
  expect(h.querySelector('[data-testid="ff-detail"] a').getAttribute('href')).toContain('SIG1');
  expect(h.querySelector('[data-testid="bundle-swap-usd"]')).toBeTruthy();
});

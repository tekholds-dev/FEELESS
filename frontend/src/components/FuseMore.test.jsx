import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FusePnl } from './FuseHQ';
import { FuseSide } from './FuseSide';
import { FuseCardMint } from './nft/FuseCardMint';
import { installTipLayer } from '../lib/tipLayer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'W' }, provider: {} }) }));
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'SES' }));
jest.mock('./EcosystemChat', () => ({ __esModule: true, default: () => <div /> }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };
const ROW = { id: 'p1', name: 'Core', at: Date.now() / 1000, pnlUsd: 1, pnlPct: 10, legs: [{ symbol: 'A', mint: 'MA', tokens: 1 }] };

test('basket limits: armed with TP / SL / trailing, explains fees are only paid on exit', async () => {
  const posts = [];
  global.fetch = jest.fn(async (url, o) => { if (o?.body) posts.push([url, JSON.parse(o.body)]); return { ok: true, json: async () => ({ positions: 1, pnlUsd: 1, pnlPct: 10, valueUsd: 11, rows: [ROW] }) }; });
  const el = await mount(<FusePnl />);
  await act(async () => { el.querySelector('[data-testid="limits-p1"]').click(); });
  expect(el.textContent).toContain('only once, when you Unfuse');
  await act(async () => { el.querySelector('[data-testid="limits-save"]').click(); }); await tick(10);
  expect(posts[0][0]).toContain('/fuses/guard'); expect(posts[0][1]).toMatchObject({ id: 'p1', tp: 50, sl: 20, session: 'SES', off: false });
});

test('creators pane: weekly season ranked by buyers P&L', async () => {
  global.fetch = jest.fn(async url => ({ json: async () => (String(url).includes('creators') ? { endsAt: Date.now() / 1000 + 86400, minBuyers: 2, rows: [{ creator: 'C'.repeat(43), handle: 'maker', buyers: 3, winRate: 67, fuses: ['Core'], pnlPct: 14.2, ranked: true }] } : { holders: [], total: 0 }) }));
  const el = await mount(<FuseSide />);
  await act(async () => { el.querySelector('[data-testid="fside-creators"]').click(); }); await tick(20);
  expect(el.querySelector('.fside-track').className).toContain('at-creators'); expect(el.textContent).toContain('@maker'); expect(el.textContent).toContain('CREATOR SEASON');
});

test('fuse cards: shows the 3 steps, asks to create the collection first', async () => {
  const call = jest.fn(async () => ({ collection: null, site: 'https://x', rows: [{ id: 'f1', name: 'Core', emoji: '⚛️', creator: 'C', creatorBps: 2500, score: { grade: 'A', points: 80 }, aprEst: 100,
    legs: [{ pairAddress: 'a', symbol: 'A', weight: 50 }, { pairAddress: 'b', symbol: 'B', weight: 50 }], stats: { creatorOwedUsd: 0 } }] }));
  const el = await mount(<FuseCardMint call={call} />);
  expect(el.textContent).toContain('Holder earns'); expect(el.querySelector('[data-testid="fcm-collection"]')).not.toBeNull();
  expect(el.querySelector('[data-testid="fcm-mint-f1"]').disabled).toBe(true);
});

test('tooltip layer: one fixed bubble, not clipped by cards', async () => {
  installTipLayer();
  const el = await mount(<button type="button" data-tip="Explains this">?</button>);
  await act(async () => { el.querySelector('button').dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); });
  const b = document.querySelector('.tip-layer');
  expect(b.textContent).toBe('Explains this'); expect(b.className).toContain('on'); expect(b.parentElement).toBe(document.body);
});

test('Fuse vs Vault shows live $1 numbers for both engines', async () => {
  const { VaultMath } = require('./FuseDeck');
  global.fetch = jest.fn(async () => ({ json: async () => ({ pools: 20, vaultAprPct: 146, vaultPerDay: { 1: 0.004, 20: 0.08, 100: 0.4 }, aprFor20c: 7300, aprFor50c: 18250, fuse1: { best: 1.4, median: 1.02, worst: 0.7 } }) }));
  const el = await mount(<VaultMath />);
  expect(el.textContent).toContain('$1 → $1.40'); expect(el.textContent).toContain('+0.40¢/day'); expect(el.textContent).toContain('7,300% APR');
});

test('trader card: medals, battles, FeeCat wins, held P&L and an X post link', async () => {
  const { TraderCard } = require('./FusePage');
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ score: 72, perf: 55, rep: 17, cards: 4,
    trader: { medals: { 1: 1, 2: 0, 3: 2 }, battles: { w: 5, l: 2, d: 1 }, catWins: 2, copies: 3, held: 2, heldPnlUsd: 4.5, bestPct: 61, closed: 2 } }) }));
  const el = await mount(<TraderCard address={'A'.repeat(43)} />);
  expect(el.textContent).toContain('🥇×1'); expect(el.textContent).toContain('🥉×2'); expect(el.textContent).not.toContain('🥈');
  expect(el.textContent).toContain('5W 2L 1D'); expect(el.querySelector('[data-testid="trader-x"]').href).toContain('x.com/intent/post');
});

test('explain this card: every coin line, honest replay + APR wording, click outside closes', async () => {
  const { CardExplain } = require('./CardExplain');
  const prev = { usd: 20, sol: 0.17, solUsd: 118, blendedAprPct: 240, backtest24hPct: -3, impactWarn: [], score: { grade: 'A', parts: [{ part: 'depth', points: 28 }] },
    legs: [{ pairAddress: 'P', symbol: 'POOL', weight: 70, usd: 14, sol: 0.12, liquidityUsd: 2e6, change24h: 2, dex: 'raydium' }, { pairAddress: 'R', symbol: 'RUN', weight: 30, usd: 6, sol: 0.05, change24h: -10, runner: true, exits: 'Sell all at +50%' }] };
  const onClose = jest.fn();
  await mount(<CardExplain prev={prev} onClose={onClose} card={<i />} />);
  const ex = document.querySelector('[data-testid="card-explain"]');
  expect(ex.textContent).toContain('POOL · 70%'); expect(ex.textContent).toContain('🏃 RUN'); expect(ex.textContent).toContain('Sell all at +50%');
  expect(ex.textContent).toContain('Not a promise'); expect(ex.textContent).toContain('not to you');
  await act(async () => { ex.querySelector('.cx').click(); }); expect(onClose).not.toHaveBeenCalled();
  await act(async () => { ex.click(); }); expect(onClose).toHaveBeenCalledTimes(1);
});

test('profile receipts: one dropdown per withdrawn card — legs + tx, moves, fees apart (explained), share', async () => {
  const { FuseReceipts } = require('./FusePage');
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ receipts: [{ id: 'c1', name: 'Moon', at: 1, closedAt: 2, costUsd: 20, realizedUsd: 26, valueUsd: 26, pnlUsd: 6, pnlPct: 30, feesUsd: 0.3, netUsd: 0.02,
    legs: [{ pairAddress: 'P', symbol: 'AAA', usd: 20, soldUsd: 26, pnlPct: 30, sig: 'SIG1' }], events: [{ kind: 'buy', at: 1, symbol: 'AAA', usd: 20 }, { kind: 'sell', at: 2, symbol: 'AAA', usd: 26 }] }] }) }));
  const { createRoot } = require('react-dom/client'); const { act } = require('react');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseReceipts address="Aaaa1111111111111111111111111111111111111111" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  const r = el.querySelector('[data-testid="receipt-c1"]');
  expect(r.textContent).toContain('$0.30 FEELESS'); expect(r.textContent).toContain('🔴 Sold'); expect(r.querySelector('a[href*="solscan.io/tx/SIG1"]')).toBeTruthy();
  expect(r.querySelector('a[href*="twitter.com/intent"]')).toBeTruthy();
});

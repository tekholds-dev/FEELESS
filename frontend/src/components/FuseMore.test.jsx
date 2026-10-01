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

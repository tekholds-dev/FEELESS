import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import fs from 'fs';
import path from 'path';

jest.mock('./terminal/TrenchChart', () => ({ TrenchChart: ({ pair }) => <div data-testid="trench-chart">chart {pair.baseToken.symbol}<button type="button">Quick trade</button></div> }));
jest.mock('./command/SwapWorkspace', () => ({ SwapWorkspace: () => <div data-testid="swap-ws">swap</div> }));
jest.mock('./terminal/MarketPrimitives', () => ({ TokenAvatar: () => <i data-testid="avatar" /> }));
jest.mock('../hooks/useMarket', () => ({ useMarket: () => ({ data: { assets: [{ id: 'fee', mint: 'FEE' }] } }) }));
jest.mock('../lib/dexscreener', () => ({ searchTokens: async () => ([{ chainId: 'solana', pairAddress: 'P2', priceUsd: '0.01', marketCap: 120000, liquidity: { usd: 30000 }, priceChange: { m5: 4.2 }, volume: { h1: 9000 }, baseToken: { address: 'M2', symbol: 'MOON', name: 'Moon' } }]) }));   // a plain function: CRA resets jest.fn implementations between tests
jest.mock('./FusePage', () => ({ FusePage: () => <div data-testid="room-fuse-page">fuse page</div> }));
jest.mock('./terminal/MetaLaunchSetup', () => ({ __esModule: true, default: () => <div data-testid="room-launch-page">launch page</div> }));
jest.mock('./command/ReputationCenter', () => ({ ReputationCenter: () => <div data-testid="room-shield-page">shield page</div> }));
const { familiaTrade, familiaSwap, familiaDocked, FamiliaTradeDock } = require('./FamiliaTrade');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const FULL = { chainId: 'solana', pairAddress: 'P1', priceUsd: '0.5', marketCap: 2e6, liquidity: { usd: 4e5 }, priceChange: { m5: -1.5 }, volume: { h1: 5e4 }, baseToken: { address: 'M1', symbol: 'FEE', name: 'FEELESS' } };

test('🏙 outside Familia a trade is the war room; inside, the dock opens the coin\'s chart + Quick trade over the room', async () => {
  const war = []; const on = e => war.push(e.detail); window.addEventListener('feeless:war-room', on);
  familiaTrade(FULL); expect(war).toHaveLength(1); expect(familiaDocked()).toBe(false);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamiliaTradeDock />); });
  expect(familiaDocked()).toBe(true);
  await act(async () => { familiaTrade(FULL); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(war).toHaveLength(1);                                                                     // no war room, no page change
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('trench-chart').textContent).toContain('FEE'); expect(q('ftd-vitals').textContent).toContain('$2.00M'); expect(q('ftd-vitals').textContent).toContain('-1.5%');
  await act(async () => { q('ftd-wide').click(); }); expect(document.querySelector('.ftd-desk').className).toContain('is-wide');
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); }); expect(q('familia-trade')).toBeNull();
  await act(async () => { familiaTrade({ chainId: 'solana', pairAddress: 'P2', baseToken: { symbol: 'MOON' } }); });   // a bare pair is looked up first
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('trench-chart').textContent).toContain('MOON'); expect(q('ftd-vitals').textContent).toContain('+4.2%');
  await act(async () => { familiaSwap({ from: 'JitoSOL', to: 'JupSOL' }); });
  expect(q('swap-ws')).not.toBeNull(); expect(JSON.parse(sessionStorage.getItem('feeless.swap.pair'))).toEqual({ input: 'JitoSOL', output: 'JupSOL' });
  await act(async () => { q('ftd-close').click(); }); expect(q('familia-trade')).toBeNull();
  act(() => root.unmount()); expect(familiaDocked()).toBe(false);
  window.removeEventListener('feeless:war-room', on);
});

test('🚫 no Familia building jumps to another FEELESS page or the war room', () => {
  const dir = __dirname; const files = ['CityAvenue.jsx', 'FamilyWorld.jsx', 'PoolHub.jsx', 'FamilyDeck.jsx', 'FamilyHQ.jsx', 'FamilyRoom.jsx', 'NightVault.jsx', 'Realtor.jsx', 'StreetChat.jsx'];
  for (const f of files) {
    const src = fs.readFileSync(path.join(dir, f), 'utf8');
    expect([f, /openWarRoom\(/.test(src)]).toEqual([f, false]);
    expect([f, /Full page ↗|full page ↗|Full profile ↗/.test(src)]).toEqual([f, false]);
  }
  const block = fs.readFileSync(path.join(dir, 'FamilyBlock.jsx'), 'utf8');
  expect(block).toMatch(/if \(familiaDocked\(\)\) \{ familiaSwap\(e\.swap\); return 'swap'; \}/);   // the swap errand stays in Familia
  expect(fs.readFileSync(path.join(dir, 'Crews.jsx'), 'utf8')).toMatch(/<FamiliaTradeDock \/>/);
});


test('🏙 Fuse cards, Launch and Rug Shield open as ROOMS inside Familia (no page jump); without a dock the link just works', async () => {
  const { familiaRoom } = require('../lib/familiaRoom');
  const ev = { prevented: false, preventDefault() { this.prevented = true; } };
  expect(familiaRoom('fuse', ev)).toBe(false); expect(ev.prevented).toBe(false);          // no Familia dock → a normal link
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamiliaTradeDock />); });
  for (const k of ['fuse', 'launch', 'shield']) {
    const e = { prevented: false, preventDefault() { this.prevented = true; } };
    await act(async () => { expect(familiaRoom(k, e)).toBe(true); });
    await act(async () => { await Promise.resolve(); await new Promise(r => setTimeout(r, 0)); });
    expect(e.prevented).toBe(true); expect(document.querySelector(`[data-testid="familia-room-${k}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="room-${k}-page"]`)).not.toBeNull();
    await act(async () => { document.querySelector('[data-testid="ftd-close"]').click(); });
  }
  expect(familiaRoom('nope', ev)).toBe(false);
  act(() => root.unmount()); expect(familiaDocked()).toBe(false);
  const world = fs.readFileSync(path.join(__dirname, 'FamilyWorld.jsx'), 'utf8');
  expect(world).not.toMatch(/href="\/terminal/);                                          // the landmark marks open rooms, not pages
});

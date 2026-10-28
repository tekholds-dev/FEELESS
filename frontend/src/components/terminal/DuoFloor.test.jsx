import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
jest.mock('./TrenchChart', () => ({ TrenchChart: ({ tools, tape }) => <div data-testid="tc" data-tools={String(tools)} data-tape={String(tape)} /> }));
jest.mock('./QuickTrade', () => ({ QuickTrade: () => <div data-testid="qt" /> }));
jest.mock('./DipRipTool', () => ({ DipRipTool: () => null }));
jest.mock('./TradeTape', () => ({ TradeTape: () => <div data-testid="tape" /> }));
jest.mock('../Shield', () => ({ ShieldBadge: () => null }));
jest.mock('../LiveTank', () => ({ LiveTank: () => <div data-testid="tank" /> }));
jest.mock('./MarketPrimitives', () => ({ TokenAvatar: () => <i /> }));
jest.mock('./LiveCells', () => ({ LivePrice: () => '$1', LiveChange24: () => '+1%', LiveMarketCap: () => '$1M' }));
jest.mock('../../hooks/useMarket', () => ({ useMarket: () => ({ data: null }) }));
jest.mock('../../hooks/useWorkspace', () => ({ useWorkspace: () => ({ has: () => false, toggle: jest.fn() }) }));
import { DuoFloor, pumpLens } from './DuoFloor';
import { pushRecent, floorFeed, stepFeed } from '../../lib/duo';

const P = (a, liq = 5e4) => ({ chainId: 'solana', pairAddress: a, baseToken: { symbol: a.toUpperCase(), address: `m-${a}` }, liquidity: { usd: liq }, priceChange: { m5: 3 } });
const q = id => document.querySelector(`[data-testid="${id}"]`);

test('📱📱 duo helpers: recents newest-first (6, one per pool) · the feed drops dust + repeats · ‹ › wraps', () => {
  let r = []; for (const a of ['a', 'b', 'a', 'c', 'd', 'e', 'f', 'g']) r = pushRecent(r, P(a));
  expect(r.map(x => x.symbol)).toEqual(['G', 'F', 'E', 'D', 'C', 'A']);
  const feed = floorFeed([P('a'), P('b'), P('dust', 10)], [P('b'), P('c')]); expect(feed.map(p => p.pairAddress)).toEqual(['a', 'b', 'c']);
  expect(stepFeed(feed, P('c'), 1).pairAddress).toBe('a'); expect(stepFeed(feed, P('a'), -1).pairAddress).toBe('c'); expect(stepFeed([], P('a'), 1)).toBeNull();
});

test('📱📱 the Duo floor: full screen, chart without its tools (they live in the dock), dock tabs switch + stick, BUY bar flips Quick trade, ‹ › steps coins', async () => {
  localStorage.clear(); const onPick = jest.fn(); const onBack = jest.fn(); const sides = []; const on = e => sides.push(e.detail); window.addEventListener('feeless:qt-side', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<DuoFloor pair={P('a')} pairs={[P('a'), P('b')]} wide={false} onPick={onPick} onBack={onBack} chat={<div data-testid="chat" />} calls={<div data-testid="calls" />} />); });
  expect(q('duo-floor')).not.toBeNull(); expect(document.body.classList.contains('duo-floor-on')).toBe(true);
  expect(q('tc').dataset.tools).toBe('false'); expect(q('tc').dataset.tape).toBe('false'); expect(q('qt')).not.toBeNull();   // TRADE is the default dock tab
  await act(async () => { q('dfl-tab-chat').click(); }); expect(q('chat')).not.toBeNull(); expect(q('qt')).toBeNull();
  expect(JSON.parse(localStorage.getItem('feeless.duo')).second).toBe('chat');
  await act(async () => { q('dfl-sell').click(); await new Promise(r => setTimeout(r, 50)); });
  expect(q('qt')).not.toBeNull(); expect(sides).toEqual([{ mint: 'm-a', side: 'sell' }]);
  await act(async () => { q('dfl-next').click(); }); expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'b' }));
  await act(async () => { q('dfl-back').click(); }); expect(onBack).toHaveBeenCalled();
  expect(JSON.parse(localStorage.getItem('feeless.duo.recent'))[0].pairAddress).toBe('a');
  act(() => root.unmount()); expect(document.body.classList.contains('duo-floor-on')).toBe(false); window.removeEventListener('feeless:qt-side', on);
});


test('💊📱📱 the Pump radar Duo app: LAUNCHES first, its lenses sort the feed (HOT = 1h move · NEW = youngest · RUNNERS = 1h volume), the tab sticks per mode', async () => {
  localStorage.clear(); const onPick = jest.fn();
  const A = { ...P('a'), pairCreatedAt: 1000, volume: { h1: 50 }, priceChange: { h1: 80 } }, B = { ...P('b'), pairCreatedAt: 3000, volume: { h1: 900 }, priceChange: { h1: 5 } }, C = { ...P('c'), pairCreatedAt: 2000, volume: { h1: 10 }, priceChange: { h1: 20 } };
  expect(pumpLens([A, B, C], 'hot').map(p => p.pairAddress)).toEqual(['a', 'c', 'b']);
  expect(pumpLens([A, B, C], 'new').map(p => p.pairAddress)).toEqual(['b', 'c', 'a']);
  expect(pumpLens([A, B, C], 'runners').map(p => p.pairAddress)).toEqual(['b', 'a', 'c']);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<DuoFloor mode="pump" pair={A} pairs={[A, B, C]} wide onPick={onPick} onBack={jest.fn()} chat={<div data-testid="chat" />} />); });
  expect(q('duo-floor').dataset.mode).toBe('pump'); expect(q('dfl-pane-launches')).not.toBeNull(); expect(q('tank')).not.toBeNull();
  expect(q('dfl-app-pump').className).toContain('is-on');                                   // the rail: the Duo apps
  await act(async () => { q('dfl-lens-runners').click(); }); await act(async () => { q('dfl-launch-0').click(); });
  expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'b' }));
  await act(async () => { q('dfl-tab-tape').click(); }); expect(localStorage.getItem('feeless.duo.tab.pump')).toBe('tape');
  expect(JSON.parse(localStorage.getItem('feeless.duo') || '{}').second).toBeUndefined();     // the Trenches' own tab is untouched
  act(() => root.unmount());
});

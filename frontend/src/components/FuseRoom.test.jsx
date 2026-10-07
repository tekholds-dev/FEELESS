import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
jest.mock('./EcosystemChat', () => ({ __esModule: true, default: ({ room }) => <div data-testid="stub-chat">{room}</div> }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('big moves keeps only the biggest activity', () => {
  const { bigMoves } = require('./FuseRoom');
  const swaps = [{ at: 5, side: 'buy', usd: 0.37, symbol: 'TINY', pct: null }, { at: 4, side: 'sell', usd: 0.65, symbol: 'STOP', pct: -15.8, label: 'Blaze', why: 'stopped' },
    { at: 3, side: 'sell', usd: 0.4, symbol: 'FLAT', pct: 2 }, { at: 2, side: 'buy', usd: 6, symbol: 'BIGBUY', pct: null }, { at: 1, side: 'sell', usd: 1, symbol: 'WIN', pct: 44 }];
  const calls = [{ at: 6, kind: 'mover', symbol: 'RAN', mint: 'R', pct: 60, live: true }, { at: 7, kind: 'leader', symbol: 'MEH', mint: 'M', pct: 4, live: true }];
  expect(bigMoves(swaps, calls).map(x => x.sym)).toEqual(['RAN', 'STOP', 'BIGBUY', 'WIN']);   // newest first; the small buy, the flat sale and the +4% callout are left out
  expect(bigMoves(null, null)).toEqual([]);
});

test('fuse room: a slim tab on the side opens a glass panel with three rooms, remembers itself and hides again', async () => {
  window.localStorage.clear();
  global.fetch = jest.fn(async u => ({ ok: true, json: async () => (String(u).includes('/proof') ? { feed: [{ at: Date.now() / 1000 - 120, side: 'sell', usd: 1.2, symbol: 'WIN', mint: 'W', pair: 'PW', pct: 31, label: '🔥 Prime Blaze', sig: 's1' }] }
    : String(u).includes('/trench/open') ? { rows: [{ mint: 'F', pairAddress: 'PF', symbol: 'FRONT', rank: 1, vol1h: 90000, chg5m: 7, safe: true, fails: [] }], feed: [] }
      : { entries: [{ mint: 'E', pairAddress: 'PE', symbol: 'ENT', ico: '🧲', name: 'Pullback', chg5m: -2, chg1h: 28, why: 'w' }] }) }));
  const { FuseRoom, FUSE_ROOMS } = require('./FuseRoom'); const { openCoin } = require('./CoinDrawer');
  expect(FUSE_ROOMS.map(r => r[0])).toEqual(['big', 'chat', 'radar']);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FuseRoom />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('fuse-room')).toBeNull(); expect(q('fuse-room-tab').textContent).toContain('FUSE ROOM'); expect(global.fetch).not.toHaveBeenCalled();   // closed = no polling
  await act(async () => { q('fuse-room-tab').click(); }); await tick(30);
  expect(q('fuse-room-big-list').textContent).toContain('$WIN'); expect(q('fuse-room-big-list').textContent).toContain('+31%');
  await act(async () => { q('fuse-room-big-list').querySelector('button').click(); }); expect(openCoin).toHaveBeenCalledWith({ mint: 'W', pairAddress: 'PW', symbol: 'WIN' });
  await act(async () => { q('fuse-room-radar').click(); }); await tick(30);
  expect(el.textContent).toContain('$ENT'); expect(el.textContent).toContain('Pullback'); expect(el.textContent).toContain('$FRONT'); expect(el.textContent).toContain('✅');
  await act(async () => { q('fuse-room-chat').click(); }); await tick(30);
  expect(q('stub-chat').textContent).toBe('fuse-lab');
  expect(JSON.parse(window.localStorage.getItem('feeless.fuseRoom'))).toEqual({ open: true, room: 'chat' });
  await act(async () => { q('fuse-room-hide').click(); }); expect(q('fuse-room')).toBeNull(); expect(q('fuse-room-tab')).not.toBeNull();
  await act(async () => { root.unmount(); });
});

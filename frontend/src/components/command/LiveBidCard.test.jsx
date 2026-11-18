import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { bidRow, ourChance, LiveBidCard } from './LiveBidCard';
import { pobFiledLine } from './CatWorkbench';

jest.mock('recharts', () => { const R = require('react'); const Box = ({ children }) => R.createElement('div', null, children); return { ResponsiveContainer: Box, LineChart: Box, Line: () => null, YAxis: () => null, ReferenceLine: () => null }; });

const F = { id: 'b1', n: 17, topic: 'Thunder vs Kings team to win', games: [{ id: '401909993', sport: 'nba', side: 'Oklahoma City Thunder', state: 'in' }],
  calls: [{ mind: 0, name: 'gpt-6.1-sol', picks: [{ pick: 'Thunder to win', confidence: 81 }] }, { mind: 1, name: 'glm-5.3', picks: [{ pick: 'Thunder to win', confidence: 72 }] }],
  kalshi: { id: 'kb1', status: 'filled', orderId: 'o1', title: 'Oklahoma City wins', side: 'yes', count: 1, filled: 1, price: 0.81, usd: 0.81, livePx: 0.9, pxHist: [[1, 0.81], [2, 0.9]] } };
const GAME = { state: 'in', status: '5:12 - 2nd', teams: [{ name: 'Oklahoma City Thunder', abbr: 'OKC', short: 'Thunder', side: 'away', score: 54 }, { name: 'Sacramento Kings', abbr: 'SAC', short: 'Kings', side: 'home', score: 41 }],
  wp: [0.4, 0.3, 0.2], plays: [{ id: 'p1', text: 'SGA makes 18-foot jumper', clock: '5:30', per: 2, a: 52, b: 41, pts: 2 }, { id: 'p2', text: 'Holmgren blocks Sabonis', clock: '5:12', per: 2, a: 54, b: 41 }], reels: [] };

test('📺 P&L is worth now minus what went in (fees never counted), and its side\'s win chance flips the home line', () => {
  expect(bidRow(F)).toMatchObject({ placed: true, cost: 0.81, now: 0.9, pnl: 0.09 });
  expect(bidRow({ ...F, kalshi: { ...F.kalshi, outcome: 'won' } }).pnl).toBe(0.19);
  expect(bidRow({ ...F, kalshi: null })).toBeNull();
  const c = ourChance(GAME, F); expect(c.team.abbr).toBe('OKC'); expect(c.rows.map(r => Math.round(r.v * 10) / 10)).toEqual([0.6, 0.7, 0.8]);   // OKC is away
  expect(pobFiledLine({ by: 'cats', open: 'bids', text: '🎲 PoB on Thunder vs Kings is filed as reading 3 in its file: 5 snapshots' })).toBe(true);
  expect(pobFiledLine({ by: 'cats', open: 'bids', text: '🎲 Filing a PoB on Thunder vs Kings.' })).toBe(false);
});

test('📺 the card shows the game, its plays, and each category on a tap; ✕ stops watching', async () => {
  const f = global.fetch; global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: async () => GAME }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const closed = jest.fn();
  await act(async () => { root.render(<LiveBidCard f={F} onClose={closed} />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(global.fetch.mock.calls[0][0]).toContain('/api/cats/tools/game/nba/401909993');
  expect(q('live-bid-score').textContent).toBe('OKC 54 – 41 SAC'); expect(q('live-bid-feed').textContent).toContain('Holmgren blocks Sabonis');
  await act(async () => { q('live-bid-pct').click(); }); expect(el.textContent).toContain('80%'); expect(el.textContent).toContain('gpt-6.1-sol');
  await act(async () => { q('live-bid-pnl').click(); }); expect(q('grm-bid-pnl').textContent).toBe('+$0.09');
  await act(async () => { q('live-bid-clips').click(); }); expect(el.textContent).toContain('HIGHLIGHTS');
  await act(async () => { q('live-bid-close').click(); }); expect(closed).toHaveBeenCalled();
  await act(async () => { root.unmount(); }); el.remove(); global.fetch = f;
});

test('🧩 the team bid and the parlay slip on the same game ride one card: "2 slips" opens both', async () => {
  const f = global.fetch; global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: async () => GAME }));
  const slip = { id: 'b2', n: 22, topic: 'Thunder vs Kings parlay slip 2 legs', games: F.games, kalshi: { id: 'kb2', kind: 'parlay', status: 'waiting', title: 'Parlay: OKC wins + SGA 30+', legs: [{ title: 'Oklahoma City wins', price: 0.81 }, { title: 'SGA 30+', price: 0.45 }], price: 0.36 } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<LiveBidCard f={F} also={[slip]} onClose={() => {}} />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('live-bid-count').textContent).toBe('2 slips');
  await act(async () => q('live-bid-count').click());
  const cards = q('live-bid-bids').querySelectorAll('[data-testid="grm-bid"]');
  expect(cards).toHaveLength(2); expect(cards[1].textContent).toContain('2-leg parlay'); expect(cards[1].textContent).toContain('SGA 30+');
  act(() => root.unmount()); global.fetch = f;
});

test('🎯 no parlay: its best picks show in the folder, and a pick he placed sits beside the team slip', async () => {
  const { KalshiPicks, noParlay } = require('./KalshiDoor'); const { sameGameSlips } = require('./CatWorkbench');
  const { createRoot } = require('react-dom/client'); const { act } = require('react-dom/test-utils');
  const g = [{ id: 'G1', sport: 'nba' }]; const pk = (id, extra = {}) => ({ id, ticker: `T${id}`, side: 'yes', title: `Pick ${id}`, price: 0.57, conf: [70], status: 'waiting', pick: true, ...extra });
  const slip = { id: 'par', games: g, kalshi: { kind: 'parlay', status: 'failed', why: 'duplicated_legs' }, kalshiPicks: [pk('a'), pk('b', { orderId: 'o9', status: 'filled', filled: 1, count: 1, usd: 0.57 })] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<KalshiPicks f={slip} catId="c" work={jest.fn()} />); });
  expect(el.querySelectorAll('[data-testid=kalshi-ticket]')).toHaveLength(2); expect(el.querySelector('[data-testid=kalshi-picks]').textContent).toContain('No parlay');
  await act(async () => { root.render(<KalshiPicks f={{ ...slip, kalshi: { kind: 'parlay', status: 'waiting' }, kalshiPicks: [pk('a')] }} catId="c" work={jest.fn()} />); });
  expect(el.querySelector('[data-testid=kalshi-picks]')).toBeNull();   // the slip is still waiting: no picks yet
  expect(noParlay({ kind: 'parlay', status: 'refused' })).toBe(true); expect(noParlay({ kind: 'parlay', status: 'sent', orderId: 'q' })).toBe(false);
  const team = { id: 'lac', games: g, kalshi: { orderId: 'o1', filled: 2 } };
  expect(sameGameSlips({ pobFolders: [team, slip] }, team).map(x => x.id)).toEqual(['par', 'par:b']);
  act(() => root.unmount());
});

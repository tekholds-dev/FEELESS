import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { GameWindow } from './GameRoom';

global.IS_REACT_ACT_ENVIRONMENT = true;

// 🎬 Owner 2026-11-15: 'see any current highlights as reels when viewing here, and prove it only investigates and does not bid'.
const reel = (id, title) => ({ id, title, secs: 21, thumb: `https://espnmedia-cdn.akamaized.net/${id}.jpg`, src: `https://espnmedia-cdn.akamaized.net/${id}.mp4`, at: '' });
const GAME = { state: 'in', status: '2:00 - 2nd', teams: [{ id: '25', name: 'San Francisco 49ers', abbr: 'SF', side: 'away', score: 17 }, { id: '6', name: 'Dallas Cowboys', abbr: 'DAL', side: 'home', score: 16 }],
  plays: [{ id: '1', at: 0.3, per: 2, clock: '2:26', type: 'Rush', text: 'B.Jones up the middle', a: 17, b: 16, side: 'b' }], stats: [], wp: [], edge: { crew: [] }, reads: [{ k: 'pace', text: 'Pace runs over the total.' }], box: {},
  reels: [reel('r2', 'Purdy to McCaffrey for 74'), reel('r1', 'Kickoff return')] };
const g = { id: '401873063', sport: 'nfl', state: 'in', status: 'live', at: '', teams: [{ name: 'San Francisco 49ers', short: '49ers' }, { name: 'Dallas Cowboys', short: 'Cowboys' }] };

let el; let root; let calls;
beforeEach(() => {
  calls = [];
  global.fetch = jest.fn((url, init) => { calls.push({ url: String(url), method: (init?.method || 'GET').toUpperCase() }); return Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('/tools/game/') ? GAME : { rows: [] }) }); });
  window.HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve());
  window.HTMLMediaElement.prototype.pause = jest.fn();
  el = document.createElement('div'); document.body.appendChild(el); root = createRoot(el);
});
afterEach(async () => { await act(async () => root.unmount()); el.remove(); });
const $ = id => document.querySelector(`[data-testid="${id}"]`);
const click = async node => { await act(async () => { node.dispatchEvent(new MouseEvent('click', { bubbles: true })); }); };
const key = async k => { await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true })); }); };

test("the game's highlights show as reels and play one after another", async () => {
  const onClose = jest.fn();
  await act(async () => { root.render(<GameWindow g={g} onClose={onClose} onCommand={() => {}} />); });
  expect($('grm-reels').textContent).toContain('2 from ESPN');
  await click($('grm-reel-r1'));
  expect($('grm-reel-player')).not.toBeNull();
  expect($('grm-reel-at').textContent).toContain('2 / 2');                       // opens on the clip you tapped
  expect($('grm-reel-video-r1').getAttribute('src')).toBe('https://espnmedia-cdn.akamaized.net/r1.mp4');
  expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled();
  await key('Escape');
  expect($('grm-reel-player')).toBeNull(); expect(onClose).not.toHaveBeenCalled();   // Esc closes the reel, not the game
  await key('Escape');
  expect(onClose).toHaveBeenCalledTimes(1);
});

test('a live game with no clips yet says so', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ ...GAME, reels: [] }) }));
  await act(async () => { root.render(<GameWindow g={g} onClose={() => {}} />); });
  expect($('grm-reels').textContent).toContain('has not posted a clip');
});

test('viewing a game only reads: every request is a GET, and its buttons only put words in the chat box', async () => {
  const onCommand = jest.fn(); const onClose = jest.fn();
  await act(async () => { root.render(<GameWindow g={g} onClose={onClose} onCommand={onCommand} onLeg={() => {}} />); });
  await click($('grm-tab-edge')); await click($('grm-prove-pace'));
  await click($('grm-tab-players')); await click($('grm-tab-plays')); await click($('grm-reel-r2')); await key('Escape');
  await click($('pgw-file'));
  expect(calls.length).toBeGreaterThan(0);
  expect(calls.filter(c => c.method !== 'GET')).toEqual([]);
  expect(calls.every(c => c.url.includes('/api/cats/tools/'))).toBe(true);
  expect(onCommand.mock.calls.map(c => c[0])).toEqual(['file a pob 49ers vs Cowboys. Test this: Pace runs over the total.', 'file a pob 49ers vs Cowboys']);
});

test('its real Kalshi bid shows in the game room: money in, worth now, P&L without fees, then the minds after the payout', async () => {
  const bid = { n: 15, ticker: 'KXNBAGAME-26NOV15OKCSAC-OKC', side: 'yes', title: 'Oklahoma City wins', price: 0.4, count: 2, filled: 2, cost: 0.8, now: 1.1, pnl: 0.3, livePx: 0.55, status: 'filled', placed: true };
  const loadCalls = jest.fn(() => Promise.resolve({ calls: [], bids: [bid], final: [{ name: 'hy4', text: 'The rest edge held.' }], agent: 'Happy Assistant' }));
  await act(async () => { root.render(<GameWindow g={g} onClose={() => {}} loadCalls={loadCalls} />); });
  const card = $('grm-bid');
  expect(card.textContent).toContain('REAL KALSHI BID'); expect(card.textContent).toContain('YES · Oklahoma City wins');
  expect(card.textContent).toContain('$0.80 2 × 0.40'); expect($('grm-bid-pnl').textContent).toBe('+$0.30');
  expect($('grm-final').textContent).toContain('The rest edge held.');
  expect(calls.filter(c => c.method !== 'GET')).toEqual([]);   // still only reads
});

test('a real parlay shows its legs in the game room', async () => {
  const bid = { n: 16, kind: 'parlay', side: 'yes', title: 'Parlay: Houston + Sengun 20+', price: 0.42, filled: 2, cost: 0.84, now: null, pnl: null, status: 'filled', placed: true, legs: [{ title: 'Houston', price: 0.75 }, { title: 'Alperen Sengun: 20+', price: 0.55 }] };
  const loadCalls = jest.fn(() => Promise.resolve({ calls: [], bids: [bid], final: [], agent: 'A' }));
  await act(async () => { root.render(<GameWindow g={g} onClose={() => {}} loadCalls={loadCalls} />); });
  expect($('grm-bid').textContent).toContain('2-leg parlay'); expect($('grm-bid-legs').textContent).toContain('Alperen Sengun: 20+');
});

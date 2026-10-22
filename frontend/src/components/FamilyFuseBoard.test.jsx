import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { FamilyFuseBoard, FamilyFuseStrip, fits } from './FamilyFuseBoard';
import { FeeCapital } from './FeeCapital';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const seat = (i, a, b, win) => ({ seat: i, a: { symbol: `A${i}`, pct: a }, b: { symbol: `B${i}`, pct: b }, win });
const LIVE = { id: 'f1', status: 'live', stake: 'mp', mp: 1000, mins: 15, left: 500, bidsOpen: true, lockIn: 100, winner: null, paid: null, at: 1,
  a: { id: 'fa', tag: 'AAA', name: 'A', color: '#45e486', card: { name: 'A card', coins: 3 }, pct: 4.2 }, b: { id: 'fb', tag: 'BBB', name: 'B', card: { name: 'B card', coins: 2 }, pct: -1.1 },
  crowd: { pool: { a: 300, b: 100 }, total: 400, pays: { a: 1.27, b: 3.8 }, bidders: 3 }, duel: { a: 2, b: 1, seats: [seat(1, 5, 1, 'a'), seat(2, 2, -3, 'a'), seat(3, -1, 0.5, 'b')] } };
const OPEN = { ...LIVE, id: 'f2', status: 'open', a: { ...LIVE.a, id: 'fc', tag: 'CCC', card: { name: 'C card', coins: 4 } }, b: { ...LIVE.b, id: 'fz', card: null, pct: null }, duel: null };
const CARDS = [{ key: 'design:1', name: 'Two', coins: 2 }, { key: 'design:2', name: 'Four', coins: 4 }, { key: 'design:3', name: 'Six', coins: 6 }];
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const setVal = (inp, v) => { Object.getOwnPropertyDescriptor(Object.getPrototypeOf(inp), 'value').set.call(inp, v); inp.dispatchEvent(new Event(inp.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); };
beforeEach(() => { global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ fights: [LIVE], cards: CARDS }) })); });

test('only cards one coin apart may answer', () => {
  expect(fits(CARDS, 4).map(c => c.coins)).toEqual([4]); expect(fits(CARDS, 3).map(c => c.coins)).toEqual([2, 4]); expect(fits(CARDS, 1).map(c => c.coins)).toEqual([2]); expect(fits(CARDS, 5).map(c => c.coins)).toEqual([4, 6]);
});

test('the board scores the fight, the crowd bids, the rival answers with a fitting card, a Don calls a family out', async () => {
  const v = { me: { id: 'fz', boss: true, bank: 9000, pts: 500 }, rules: { fuseMinMp: 2000 }, ranked: [{ id: 'fa', tag: 'AAA', name: 'A' }, { id: 'fz', tag: 'ZZZ', name: 'Z' }], blocks: [],
    ffuse: { fights: [LIVE, OPEN], cards: CARDS, mins: [15, 30, 60] } };
  let state = v; const setV = f => { state = f(state); };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FamilyFuseBoard v={v} setV={setV} addr="W" sess="s" />); });
  expect(q(el, 'ff-f1').textContent).toContain('2 ⚡ 1'); expect(q(el, 'ff-f1').textContent).toContain('×1.27');
  await act(async () => { q(el, 'ff-f1').querySelector('[data-testid="ffb-side-b"]').click(); });
  await act(async () => { q(el, 'ff-f1').querySelector('[data-testid="ffb-bid"]').click(); });
  expect(JSON.parse(global.fetch.mock.calls.at(-1)[1].body)).toMatchObject({ act: 'bid', fight: 'f1', side: 'b', amount: 100 });
  const opts = [...q(el, 'ff-f2').querySelectorAll('[data-testid="ffb-card"] option')].map(o => o.textContent);
  expect(opts.slice(1)).toEqual(['Four · 4 coins']);                                        // a 4-coin call: 3–5 coins only
  await act(async () => { setVal(q(el, 'ff-f2').querySelector('[data-testid="ffb-card"]'), 'design:2'); });
  await act(async () => { q(el, 'ff-f2').querySelector('[data-testid="ffb-accept"]').click(); });
  expect(JSON.parse(global.fetch.mock.calls.at(-1)[1].body)).toMatchObject({ act: 'accept', fight: 'f2', card: 'design:2' });
  expect(q(el, 'ffb-call')).toBeNull();                                                     // already in a fight → no new call-out
});

test('a free Don calls a rival out for MP; the strip and the pitch show the fight', async () => {
  const v = { me: { id: 'fz', boss: true, bank: 9000, pts: 0 }, rules: { fuseMinMp: 2000 }, ranked: [{ id: 'fa', tag: 'AAA', name: 'A' }], blocks: [], ffuse: { fights: [], cards: CARDS, mins: [15, 30, 60] } };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FamilyFuseBoard v={v} setV={() => {}} addr="W" sess="s" />); });
  await act(async () => { setVal(q(el, 'ffb-vs'), 'fa'); setVal(q(el, 'ffb-mycard'), 'design:1'); });
  await act(async () => { q(el, 'ffb-stake-mp').click(); });
  await act(async () => { q(el, 'ffb-send').click(); });
  expect(JSON.parse(global.fetch.mock.calls.at(-1)[1].body)).toMatchObject({ act: 'challenge', vs: 'fa', card: 'design:1', stake: 'mp', mp: 500, mins: 15 });
  const s = document.createElement('div'); document.body.appendChild(s);
  await act(async () => { createRoot(s).render(<FamilyFuseStrip />); });
  expect(q(s, 'family-fuse-strip').textContent).toContain('2 ⚡ 1');
  const c = document.createElement('div'); document.body.appendChild(c);
  await act(async () => { createRoot(c).render(<FeeCapital v={{ blocks: [], landmarks: [], cities: [], bridges: [], ffuse: { fights: [LIVE] } }} onPick={() => {}} onGo={() => {}} />); });
  expect(c.querySelectorAll('.fc-seats > i')).toHaveLength(3); expect(c.querySelector('.fc-std').className).toContain('is-fight');
  expect(c.textContent).toContain('[AAA] 2 ⚡ 1 [BBB]');
});

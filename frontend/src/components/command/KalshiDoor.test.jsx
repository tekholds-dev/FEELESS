import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { KalshiDoor, KalshiTicket } from './KalshiDoor';

const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const STATE = { cfg: { mode: 'approve', bidUsd: 1, dayUsd: 3, floorUsd: 2, minConf: 65 }, key: true, balance: 10, spentToday: 0, bids: [], hard: { bidUsd: 5, dayUsd: 20 } };
async function mount(node) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await act(async () => { await Promise.resolve(); }); return el; }

test('no On switch: with the key saved an asked PoB bids; Auto is the one switch and goes to the server', async () => {
  document.body.classList.add('fx-lite'); const sent = [];
  const work = async (_c, b) => { sent.push(b); return b.op === 'kalshi_cfg' ? { ...STATE, cfg: { ...STATE.cfg, ...b.tools } } : STATE; };
  const el = await mount(<KalshiDoor cat={{ id: 'c' }} work={work} />);
  expect(q(el, 'kd-on')).toBeNull(); expect(q(el, 'kalshi-door').textContent).toContain('A PoB you ask for bids at once'); expect(q(el, 'kalshi-door').textContent).toContain('$10.00');
  await act(async () => { q(el, 'kd-auto').click(); }); expect(sent.at(-1)).toEqual({ op: 'kalshi_cfg', tools: { ...STATE.cfg, mode: 'auto' } });
  expect(q(el, 'kalshi-door').textContent).toContain('auto runs bid by themselves too');
});

test('with no key saved Auto cannot turn on and it says where the key goes', async () => {
  const el = await mount(<KalshiDoor cat={{ id: 'c' }} work={async () => ({ ...STATE, key: false })} />);
  expect(q(el, 'kd-auto').disabled).toBe(true); expect(el.textContent).toContain('Save your Kalshi API key');
});

test('a ticket sends only on Approve, then shows what Kalshi did', async () => {
  const calls = []; const t = { id: 'kb1', ticker: 'KX-ORL', side: 'yes', title: 'Orlando wins', price: 0.4, conf: [72, 70], why: ['a', 'b'], status: 'waiting' };
  const work = async (_c, b) => { calls.push(b); return { ticket: { ...t, status: 'resting', count: 2, usd: 0.8 } }; };
  const el = await mount(<KalshiTicket t={t} catId="c" work={work} />);
  expect(calls).toHaveLength(0);
  await act(async () => { q(el, 'kd-approve').click(); }); expect(calls).toHaveLength(0);   // real money: the first tap only arms
  await act(async () => { q(el, 'kd-approve').click(); });
  expect(calls).toEqual([{ op: 'kalshi_bid', job: 'kb1' }]); expect(q(el, 'kd-status').textContent).toContain('2 × 0.40 = $0.80'); expect(q(el, 'kd-approve')).toBeNull();
});

test('after sending, the ticket shows Kalshi\'s own read-back and can re-check it (a string reason never crashes it)', async () => {
  const calls = []; const t = { id: 'kb2', ticker: 'KX-LAL', side: 'no', title: 'Lakers win', price: 0.3, conf: [80, 75], why: '1 × NO at 0.30 = $0.30', status: 'resting', count: 1, usd: 0.3, orderId: 'o9', filled: 0, confirmedAt: 1800000000 };
  const work = async (_c, b) => { calls.push(b); return { ticket: { ...t, status: 'filled', filled: 1 } }; };
  const el = await mount(<KalshiTicket t={t} catId="c" work={work} />);
  expect(q(el, 'kd-confirm').textContent).toContain('Kalshi confirmed 0 of 1 filled');
  await act(async () => { q(el, 'kd-check').click(); });
  expect(calls).toEqual([{ op: 'kalshi_check', job: 'kb2' }]); expect(q(el, 'kd-confirm').textContent).toContain('1 of 1 filled'); expect(q(el, 'kd-check')).toBeNull();
});

test('a streak only OFFERS a bigger bid; it changes on two taps to exactly the offered value; a split shows a hedge, never a bid', async () => {
  const sent = []; const S = { ...STATE, streak: 3, raise: { streak: 3, from: 1, to: 2 } };
  const work = async (_c, b) => { sent.push(b); return b.op === 'kalshi_raise' ? { ...S, raise: null, cfg: { ...S.cfg, bidUsd: 2 } } : S; };
  const el = await mount(<KalshiDoor cat={{ id: 'c' }} work={work} />);
  expect(q(el, 'kd-streak').textContent).toContain('3 real wins in a row');
  await act(async () => { q(el, 'kd-raise-go').click(); }); expect(sent.filter(b => b.op === 'kalshi_raise')).toHaveLength(0);
  await act(async () => { q(el, 'kd-raise-go').click(); });
  expect(sent.at(-1)).toEqual({ op: 'kalshi_raise', job: '2.00' });
  const { KalshiHedge } = require('./KalshiDoor');
  const h = await mount(<KalshiHedge rows={[{ name: 'A', conf: 70, side: 'yes', title: 'Lakers win', price: 0.4, ticker: 'T' }, { name: 'B', conf: 66, side: 'no', title: 'Lakers win', price: 0.62, ticker: 'T' }]} />);
  expect(h.textContent).toContain('THE MINDS SPLIT'); expect(h.textContent).toContain('0.62 on Kalshi'); expect(h.querySelector('button')).toBeNull();
});

test('a parlay slip ticket lists every leg and the most it pays a contract', async () => {
  const t = { id: 'kb1', kind: 'parlay', status: 'waiting', offer: 'hy4', price: 0.4125, maxPx: 0.536, conf: [70], title: 'Parlay: Houston + Alperen Sengun: 20+',
    legs: [{ ticker: 'A', title: 'Houston', price: 0.75, conf: [80] }, { ticker: 'B', title: 'Alperen Sengun: 20+', price: 0.55, conf: [70] }] };
  const el = await mount(<KalshiTicket t={t} catId="c" work={async () => ({})} />);
  expect(q(el, 'kalshi-ticket').textContent).toContain('KALSHI PARLAY · 2 legs · hy4');
  expect(q(el, 'kalshi-ticket').textContent).toContain('at most 0.536 a contract');
  expect(q(el, 'kd-legs').querySelectorAll('li').length).toBe(2); expect(q(el, 'kd-approve')).not.toBeNull();
});

test('the door shows each mind real Kalshi record', async () => {
  const el = await mount(<KalshiDoor cat={{ id: 'c' }} work={async () => ({ ...STATE, minds: { 'openrouter/hy4': { won: 3, lost: 1 } } })} />);
  expect(q(el, 'kd-minds').textContent).toContain('hy4 3–1');
});

test('a slip that got no quote offers Try smaller once, and it goes to the server on the second tap', async () => {
  const sent = []; const t = { id: 'kb1', kind: 'parlay', status: 'refused', why: 'No market maker quoted the slip at 0.536 or less within 25 s, so nothing was bought.', price: 0.41, maxPx: 0.536, conf: [70], legs: [] };
  const el = await mount(<KalshiTicket t={t} catId="c" work={async (_c, b) => { sent.push(b); return { ticket: { ...t, id: 'kb2', status: 'refused', retryOf: 'kb1', budgetUsd: 0.5 } }; }} />);
  await act(async () => { q(el, 'kd-smaller').click(); }); expect(sent).toEqual([]);   // first tap only arms it
  await act(async () => { q(el, 'kd-smaller').click(); }); await act(async () => { await Promise.resolve(); });
  expect(sent).toEqual([{ op: 'kalshi_smaller', job: 'kb1' }]); expect(q(el, 'kd-smaller')).toBeNull(); expect(q(el, 'kd-budget').textContent).toContain('$0.50');
});

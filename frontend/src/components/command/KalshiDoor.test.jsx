import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { KalshiDoor, KalshiTicket } from './KalshiDoor';

const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const STATE = { cfg: { on: false, mode: 'approve', bidUsd: 1, dayUsd: 3, floorUsd: 2, minConf: 65 }, key: true, balance: 10, spentToday: 0, bids: [], hard: { bidUsd: 5, dayUsd: 20 } };
async function mount(node) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await act(async () => { await Promise.resolve(); }); return el; }

test('the door is off until he switches it on, and every change goes to the server', async () => {
  document.body.classList.add('fx-lite'); const sent = [];
  const work = async (_c, b) => { sent.push(b); return b.op === 'kalshi_cfg' ? { ...STATE, cfg: { ...STATE.cfg, ...b.tools } } : STATE; };
  const el = await mount(<KalshiDoor cat={{ id: 'c' }} work={work} />);
  expect(q(el, 'kalshi-door').textContent).toContain('Off'); expect(q(el, 'kalshi-door').textContent).toContain('$10.00');
  await act(async () => { q(el, 'kd-on').click(); }); expect(sent.at(-1)).toEqual({ op: 'kalshi_cfg', tools: { ...STATE.cfg, on: true } });
  await act(async () => { q(el, 'kd-mode-auto').click(); }); expect(sent.at(-1).tools.mode).toBe('auto'); expect(q(el, 'kalshi-door').textContent).toContain('by itself inside your caps');
});

test('with no key saved the switch cannot turn on and says where the key goes', async () => {
  const el = await mount(<KalshiDoor cat={{ id: 'c' }} work={async () => ({ ...STATE, key: false })} />);
  expect(q(el, 'kd-on').disabled).toBe(true); expect(el.textContent).toContain('Save your Kalshi API key');
});

test('a ticket sends only on Approve, then shows what Kalshi did', async () => {
  const calls = []; const t = { id: 'kb1', ticker: 'KX-ORL', side: 'yes', title: 'Orlando wins', price: 0.4, conf: [72, 70], why: ['a', 'b'], status: 'waiting' };
  const work = async (_c, b) => { calls.push(b); return { ticket: { ...t, status: 'resting', count: 2, usd: 0.8 } }; };
  const el = await mount(<KalshiTicket t={t} catId="c" work={work} />);
  expect(calls).toHaveLength(0);
  await act(async () => { q(el, 'kd-approve').click(); });
  expect(calls).toEqual([{ op: 'kalshi_bid', job: 'kb1' }]); expect(q(el, 'kd-status').textContent).toContain('2 × 0.40 = $0.80'); expect(q(el, 'kd-approve')).toBeNull();
});

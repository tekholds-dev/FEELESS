import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { caOf, seatTargets, addBody, addStage, AddMyCoin, SeatStudy, MySeatsRecord } from './MySeat';

const MINT = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU';
test('a pasted address or link resolves to its mint', () => {
  expect(caOf(MINT)).toBe(MINT);
  expect(caOf(`https://pump.fun/coin/${MINT}`)).toBe(MINT);
  expect(caOf('hello')).toBe(null);
});
test('targets = the empty seat first, then each held seat (never a frozen one)', () => {
  const t = seatTargets([{ open: true }, { pair: 'P1', symbol: 'A', pct: 3 }, { pair: 'P2', symbol: 'B', state: 'frozen' }]);
  expect(t.map(x => x.k)).toEqual(['open', 'P1']);
  expect(addBody('degen', 'M', 'open')).toEqual({ fillSeat: { tpl: 'degen', to: 'M', more: true } });
  expect(addBody('degen', 'M', 'P1', true)).toEqual({ pickSwap: { tpl: 'degen', pairAddress: 'P1', to: 'M', now: true, ack: true } });
});
test('⚡ Add goes straight in — your selection needs no "add it anyway" (it sends the acknowledgement up front)', async () => {
  const call = jest.fn(async (p, o) => { if (!JSON.parse(o.body).fillSeat.ack) throw new Error('⚠ $X did not pass: under 1h'); return { ok: true }; });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AddMyCoin call={call} tpl="degen" seats={[{ open: true }]} />); });
  const inp = el.querySelector('[data-testid="my-seat-ca"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(inp, MINT); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="my-seat-go"]').click(); });
  expect(call).toHaveBeenCalledTimes(1); expect(JSON.parse(call.mock.calls[0][1].body).fillSeat).toMatchObject({ to: MINT, ack: true });
  expect(el.querySelector('[data-testid="my-seat-track"]')).toBeTruthy();
  expect(el.querySelector('[data-testid="my-seat-msg"]').textContent).toContain('sent');
});
test('pasting an address adds it at once — no button press', async () => {
  const call = jest.fn(async () => ({ ok: true }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AddMyCoin call={call} tpl="degen" seats={[{ open: true }]} />); });
  const inp = el.querySelector('[data-testid="my-seat-ca"]');
  await act(async () => { const ev = new Event('paste', { bubbles: true, cancelable: true }); ev.clipboardData = { getData: () => `https://pump.fun/coin/${MINT}` }; inp.dispatchEvent(ev); });
  expect(call).toHaveBeenCalledTimes(1); expect(JSON.parse(call.mock.calls[0][1].body).fillSeat).toMatchObject({ to: MINT, ack: true });
});
test('the tracker follows your add: queued → buying → bought, or the keeper refusal', () => {
  const tr = { mint: MINT, at: 1000 };
  expect(addStage(null, null)).toBeNull();
  expect(addStage({ seatPick: { to: MINT } }, tr, 1010).k).toBe('queued');
  const card = { legs: [{ mint: MINT, symbol: 'ABC' }], realBook: { orders: [] }, events: [] };
  expect(addStage(card, tr, 1020).k).toBe('buying');
  expect(addStage({ ...card, realBook: { orders: [{ side: 'buy', symbol: 'ABC', status: 'filled', at: 1030, usd: 0.5 }] } }, tr, 1040)).toMatchObject({ k: 'filled', t: '✅ bought $ABC · $0.50 in' });
  expect(addStage({ ...card, realBook: { orders: [{ side: 'buy', symbol: 'ABC', status: 'filled', at: 900 }] } }, tr, 1040).k).toBe('buying');   // an older fill never counts
  expect(addStage({ ...card, events: [{ at: 1030, why: 'buy refused — $ABC pool too thin' }] }, tr, 1040).k).toBe('refused');
  expect(addStage({}, tr, 1200).t).toContain('no seat yet');
});
test('your seat shows what the agents would do and its record', () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  act(() => { createRoot(el).render(<><SeatStudy s={{ seat: 2, mine: true, would: { action: 'swap', to: 'BOT', why: 'flat 30 min' }, study: [{ k: 'a', at: 1, rule: 'R7 trail', pct: 12, sell: true }] }} />
    <MySeatsRecord rec={{ n: 3, med: 4, cmp: { n: 2, you: 5, agents: 2, youBetter: 1 } }} /></>); });
  expect(el.textContent).toContain('would swap for $BOT');
  expect(el.textContent).toContain('you did better 1/2');
});

test('limits: a price makes a buy limit, a held seat gets take / stop limits from now, and ⏏ Pull sells it to card cash', async () => {
  const { addBody, sellLimitBody, SeatControls } = require('./MySeat');
  expect(addBody('degen', 'M', 'open', true, '0.002').fillSeat).toMatchObject({ limitPx: 0.002, hours: 24, ack: true });
  expect(addBody('degen', 'M', 'open', true, '').fillSeat.limitPx).toBeUndefined();
  const seat = { pair: 'P1', symbol: 'AAA', px: 2, pct: 5 };
  expect(sellLimitBody('degen', seat, 50, 50).limitSell).toMatchObject({ pairAddress: 'P1', px: 3, pct: 50, stop: false });
  expect(sellLimitBody('degen', seat, -15).limitSell).toMatchObject({ stop: true, pct: 100 }); expect(sellLimitBody('degen', seat, -15).limitSell.px).toBeCloseTo(1.7);
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cards: [{ tpl: 'degen', limits: [{ id: 'L1', word: '🎯 BUY $X into an empty seat at ≤ 0.001' }] }] }) }));
  const call = jest.fn(async () => ({ ok: true }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SeatControls call={call} tpl="degen" seats={[{ open: true }, seat]} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(el.querySelector('[data-testid="seat-limits"]').textContent).toContain('BUY $X');
  await act(async () => { el.querySelector('[data-testid="seat-pull-AAA"]').click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ manualSell: { tpl: 'degen', pairAddress: 'P1', pct: 100, ack: true } });
  await act(async () => { el.querySelector('[data-testid="seat-lim-x-L1"]').click(); });
  expect(JSON.parse(call.mock.calls[1][1].body)).toEqual({ limitCancel: { tpl: 'degen', id: 'L1' } });
});

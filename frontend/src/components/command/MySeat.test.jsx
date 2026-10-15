import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { caOf, seatTargets, addBody, AddMyCoin, SeatStudy, MySeatsRecord } from './MySeat';

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
  expect(el.querySelector('[data-testid="my-seat-warn"]')).toBeNull();
  expect(el.querySelector('[data-testid="my-seat-msg"]').textContent).toContain('queued');
});
test('your seat shows what the agents would do and its record', () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  act(() => { createRoot(el).render(<><SeatStudy s={{ seat: 2, mine: true, would: { action: 'swap', to: 'BOT', why: 'flat 30 min' }, study: [{ k: 'a', at: 1, rule: 'R7 trail', pct: 12, sell: true }] }} />
    <MySeatsRecord rec={{ n: 3, med: 4, cmp: { n: 2, you: 5, agents: 2, youBetter: 1 } }} /></>); });
  expect(el.textContent).toContain('would swap for $BOT');
  expect(el.textContent).toContain('you did better 1/2');
});

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { useTradeStream } from './tradeStream';
import { liveBar, mergeLiveBar } from './tween';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// 🕯 Slice 34 "charts are true, nothing faked": the chart and the tape read ONE trade stream. Each swap fill from the pool's live socket
// shapes the chart's forming candle (PriceChart → liveBar) AND lands on the tape (feeless:live-fill → useTradeStream). Replaying a run of
// real-shaped fills through both paths, the chart's LAST CANDLE closes at the LAST TAPE TRADE's price after every fill — across a minute
// rollover, a repeat price and a history reload whose provider bar lags behind the live one.
test('the chart\'s last candle = the last tape trade, after every fill', async () => {
  const pair = { chainId: 'solana', pairAddress: 'POOL', baseToken: { address: 'M' } };
  global.fetch = async () => ({ json: async () => ({ trades: [] }) });
  let tape = null; const Probe = () => { tape = useTradeStream(pair).trades; return null; };
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<Probe />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });

  const t0 = 1_800_000_000 - (1_800_000_000 % 60);
  let last = { time: t0 - 60, open: 1, high: 1.2, low: 0.9, close: 1.1 };   // the provider's newest bar before the stream
  const fills = [[t0 + 3, 1.15, 'buy'], [t0 + 20, 1.08, 'sell'], [t0 + 41, 1.3, 'buy'], [t0 + 61, 1.3, 'buy'], [t0 + 75, 1.22, 'sell'], [t0 + 130, 0.97, 'sell']];
  for (const [at, price, kind] of fills) {
    const t = Math.floor(at / 60) * 60;
    const bar = liveBar(last, price, t); if (bar) last = bar;   // PriceChart.apply: a real fill shapes the candle, a repeat price in a new minute draws nothing
    await act(async () => { window.dispatchEvent(new CustomEvent('feeless:live-fill', { detail: { pool: 'POOL', tx: `x${at}`, kind, usd: 10, price, wallet: 'W', ts: new Date(at * 1000).toISOString() } })); });
    expect(tape[0].price).toBe(price);
    expect(last.close).toBe(tape[0].price);   // ← the one-stream check
  }
  // a 15s history reload brings the provider's bars, which can lag the live one: the live bar is kept, so they still agree
  const provider = [{ time: t0, open: 1.15, high: 1.3, low: 1.08, close: 1.3 }, { time: t0 + 60, open: 1.3, high: 1.3, low: 1.22, close: 1.22 }];
  const merged = mergeLiveBar(provider, { ...last, iv: '1m', pool: 'POOL' }, '1m', 'POOL');   // as PriceChart keeps it: liveBarRef = { ...bar, iv, pool }
  expect(merged.at(-1).close).toBe(tape[0].price);
  expect(merged.at(-1).time).toBe(t0 + 120);
  act(() => root.unmount());
});

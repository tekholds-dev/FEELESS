import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { useTradeStream } from './tradeStream';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('⚡ a live fill from the chart stream lands on the tape at once; the next tape read never doubles it', async () => {
  const pair = { chainId: 'solana', pairAddress: 'POOL', baseToken: { address: 'M' } };
  const read = [{ tx: 'OLD', kind: 'buy', usd: 5, price: 1, wallet: 'W0', ts: new Date().toISOString() }];
  global.fetch = async () => ({ json: async () => ({ trades: read }) });
  let got = null;
  const Probe = () => { got = useTradeStream(pair); return null; };
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<Probe />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(got.trades.map(t => t.tx)).toEqual(['OLD']);
  const fill = (pool, tx) => window.dispatchEvent(new CustomEvent('feeless:live-fill', { detail: { pool, tx, kind: 'sell', usd: 12, price: 2, wallet: 'W1', ts: new Date().toISOString() } }));
  await act(async () => { fill('OTHER', 'X1'); fill('POOL', 'NEW'); fill('POOL', 'NEW'); });
  expect(got.trades.map(t => t.tx)).toEqual(['NEW', 'OLD']);                         // another pool's fill ignored; the same fill once
  expect(got.trades[0]).toMatchObject({ kind: 'sell', usd: 12, wallet: 'W1', live: true });
  act(() => root.unmount());
});

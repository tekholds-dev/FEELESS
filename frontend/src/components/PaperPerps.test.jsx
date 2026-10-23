import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'ME' } }) }));
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'sess', getChatSession: async () => 'sess' }));
const { PaperPerps } = require('./PaperPerps');
const BOOK = { cash: 9750, equity: 10012.5, start: 10000, realized: 0, trades: 0, winPct: null, closed: [], liquidated: [],
  open: [{ id: 'p1', coin: 'BTC', side: 'short', lev: 4, margin: 250, pnl: 12.5, pnlPct: 5, fund: 0.4, liq: 74000, toLiqPct: 23.1 }] };
const ROW = { coin: 'BTC', mark: 60000, fundApr: 11, maxLev: 40, venues: ['kraken'] };

test('📉 the paper desk: live book, a lit ticket, positions with liquidation meters, the real-venue handoff — paper only', async () => {
  const calls = [];
  global.fetch = jest.fn((u, o) => { calls.push([String(u), o]); return Promise.resolve({ ok: true, json: () => Promise.resolve(BOOK) }); });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<PaperPerps row={ROW} lev={10} />); });
  await act(async () => { await Promise.resolve(); });
  expect(q('paper-perps').textContent).toContain('BTC-PERP'); expect(q('pp-pos-p1').textContent).toContain('23.1% to liq');
  expect(el.querySelectorAll('a[href^="http"]')).toHaveLength(0);   // no link-outs
  await act(async () => { q('pp-m-500').click(); });
  await act(async () => { q('pp-long').click(); });
  const open = calls.find(([u, o]) => o?.method === 'POST' && JSON.parse(o.body).act === 'open');
  expect(JSON.parse(open[1].body)).toMatchObject({ coin: 'BTC', side: 'long', margin: 500, lev: 10, session: 'sess' });
  expect(calls.every(([u]) => u.includes('/api/reputation/familia/paper-perps'))).toBe(true);   // never a venue call from here
  await act(async () => { q('pp-close-p1').click(); });
  expect(calls.some(([, o]) => o?.method === 'POST' && JSON.parse(o.body).act === 'close' && JSON.parse(o.body).id === 'p1')).toBe(true);
  await act(async () => { root.unmount(); });
});

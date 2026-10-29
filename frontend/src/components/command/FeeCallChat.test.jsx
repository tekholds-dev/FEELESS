import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockOpen = jest.fn();
jest.mock('../WarRoomHost', () => ({ openWarRoom: p => mockOpen(p) }));
jest.mock('../FeeCatMark', () => ({ FeeCatMark: () => <i data-testid="mark" /> }));
const { FeeCallChat } = require('./FeeCallChat');
const now = Date.now();
const EV = [{ id: 's1', type: 'SELL', ts: now - 60_000, pairAddress: 'P1', pnlSol: 0.0181, entryMarketCapUsd: 52000, detail: 'Sold SQUADS at +18.3% — 🔮 FeeCat AI said exit. P&L +0.0181 SOL on the price move (fees apart, paper, live price).' },
  { id: 'b1', type: 'BUY', ts: now - 35 * 60_000, pairAddress: 'P1', marketCapUsd: 44000, detail: 'Bought 0.06 SOL of SQUADS at live price — 🔮 FeeCat AI favored it (1 min ago): buyers lead, pool $40K.; 🎯 HH/HL pullback · 🔮 FeeCat AI said YES' },
  { id: 'b2', type: 'BUY', ts: now - 120_000, pairAddress: 'P2', marketCapUsd: 21000, detail: 'Bought 0.05 SOL of GERM at live price — 🔮 FeeCat AI favored it: germ floor held.' },
  { id: 'l1', type: 'LEARN', ts: now - 30_000, detail: 'learned x' }];

test('🐱 N15 her calls read as a chat: her words, cap, tags, each BUY threaded to its SELL or still holding; the 24h strip; a coin opens its war room', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FeeCallChat events={EV} positions={[{ pairAddress: 'P2' }]} hunting />); });
  const msgs = el.querySelectorAll('[data-testid="fcc-msg"]');
  expect(msgs).toHaveLength(3);                                                           // LEARN is not a call
  expect(msgs[0].textContent).toContain('SELL'); expect(msgs[0].textContent).toContain('+0.0181 SOL');
  expect(msgs[2].textContent).toContain('buyers lead, pool $40K'); expect(msgs[2].textContent).toContain('@ $44.0K MC'); expect(msgs[2].textContent).toContain('🎯 HH/HL pullback');
  expect(msgs[2].querySelector('[data-testid="fcc-closed"]').textContent).toContain('held 34m');
  expect(msgs[1].querySelector('[data-testid="fcc-open"]').textContent).toContain('still holding');
  expect(el.textContent).toContain('Fee is scanning the board'); expect(el.textContent).toContain('100%');
  await act(async () => { msgs[1].querySelector('[data-testid="fcc-coin"]').click(); });
  expect(mockOpen).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'P2' }));
  await act(async () => { root.render(<FeeCallChat events={[]} positions={[]} hunting={false} />); });
  expect(el.textContent).toContain('No calls yet'); expect(el.textContent).toContain('NAPPING');
  await act(async () => { root.unmount(); });
});

import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TradeBook, AfterBook } from './FeeCatProfile';

jest.mock('../EcosystemChat', () => () => null);
jest.mock('../ShareGif', () => ({ ShareGifButton: () => null }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mount = node => { const host = document.createElement('div'); document.body.appendChild(host); act(() => createRoot(host).render(node)); return host; };
afterEach(() => { document.body.innerHTML = ''; });

const now = Date.now();
const trades = [
  { id: 's1', type: 'SELL', ts: now, pnlSol: -0.0178, detail: 'Sold iCoin at -30.0% — hard stop -25% from my average entry. P&L -0.0178 SOL on the price move (fees apart, paper, live price).' },
  { id: 'b1', type: 'BUY', ts: now, marketCapUsd: 432461, detail: 'Bought 0.06 SOL of iCoin at live price — FeeCat AI said YES' },
  { id: 's2', type: 'SELL', ts: now, pnlSol: 0.0356, detail: 'Sold ARNOLD at +0.8% — took profit' },
];

test('every trade = a summary strip + one-line rows with P&L bars, never paragraphs', () => {
  const h = mount(<TradeBook trades={trades} />);
  expect(h.querySelector('.fcp-sum').textContent).toContain('1 · 1');
  expect(h.querySelector('.fcp-sum').textContent).toContain('+0.018 SOL');
  const rows = h.querySelectorAll('.fcp-trade');
  expect(rows).toHaveLength(3);
  expect(rows[0].querySelector('.fcp-sym').textContent).toBe('$iCoin');
  expect(rows[0].querySelector('.fcp-why').textContent).toBe('hard stop -25% from my average entry');
  expect(rows[0].getAttribute('data-tip')).toContain('fees apart');   // the full note stays one hover away
  expect(rows[2].querySelector('.fcp-pnl u').style.transform).toBe('scaleX(1)');   // the biggest move fills its bar
  expect(rows[1].querySelector('.fcp-pnl small').textContent).toBe('in @ $432K');
  expect(h.querySelector('p')).toBeNull();
});

test('after the sell = a gauge per exit, a runner she left is flagged gold', () => {
  const h = mount(<AfterBook exits={[{ pairAddress: 'p1', symbol: 'iCoin', exitAt: now / 1000, why: 'hard stop', changeAtExit: -30, peakAfter: 50.5, lowAfter: -10 },
    { pairAddress: 'p2', symbol: 'CAT', exitAt: now / 1000, why: 'took profit', changeAtExit: 12, peakAfter: 5, lowAfter: -20 }]} />);
  const rows = h.querySelectorAll('.fcp-exit');
  expect(rows[0].className).toContain('missed');
  expect(rows[0].textContent).toContain('SOLD A RUNNER');
  expect(rows[1].textContent).toContain('EXIT HELD');
  expect(rows[1].querySelector('.fcp-range s').style.left).toBe('80%');   // her sale pinned at 0 between low −20 and best +5
  expect(h.querySelector('.fcp-sum').textContent).toContain('1/2');
});

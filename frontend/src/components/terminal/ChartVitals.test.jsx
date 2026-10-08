import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { ChartVitals } from './ChartVitals';

jest.mock('../PumpProfile', () => ({ usePumpProfile: () => ({ mint: 'M', graduated: true, offAthPct: -31 }) }));
jest.mock('../../lib/coinEdge', () => ({ useCoinEdge: () => ({ pulse: { buyShare: 56, m5Change: 3.5, buys: 200, sells: 182 } }) }));
jest.mock('../../lib/sharedJson', () => ({ _resetShared: () => {}, sharedJson: () => Promise.resolve({
  row: { ageH: 8.3 }, vital: { grade: 'B', score: 66, tone: 'good', word: 'GOOD', bars: { flow: 0.6 }, flags: [['🧩', 'spread — top-10 12%', 'good']] },
  tv: { kind: 'dip', call: ['🧲', 'BUY THE DIP', 'good'], meters: [['🧲 BOUNCE', 70], ['🔪 KNIFE', 20]], tags: [] } }) }));

test('the chart header is the FEELESS edge: the vital beside the read, then plain numbers', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ChartVitals pair={{ baseToken: { address: 'M', symbol: 'GARY' }, marketCap: 3190000, volume: { h1: 367000 }, liquidity: { usd: 171000 } }} />); });
  await act(async () => { await Promise.resolve(); });
  const edge = el.querySelector('[data-testid="chart-edge"]');
  expect(edge.querySelector('[data-testid="cvl-GARY"]')).not.toBeNull();          // 🫀 vital (grade ring + bars)
  expect(edge.querySelector('[data-testid="tvl-GARY"]').textContent).toContain('BUY THE DIP');
  expect(el.querySelector('.cv-nums').textContent).toContain('$3.19M');
  expect(el.textContent).not.toContain('PUMP RADAR');                               // the old tiles + radar strip are gone
});

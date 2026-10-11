import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { ChartPulse } from './ChartPulse';

jest.mock('./ChartVitals', () => ({ useCoinRead: m => (m === 'M' ? { vital: { grade: 'B', score: 71, tone: 'good', word: 'CLEAN', flags: [['🧩', 'spread', 'good']] }, tv: { call: ['🔥', 'SEND IT', 'good'] } } : null) }));
jest.mock('./PriceChart', () => ({}));

const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };

test('the FEELESS vital on a chart: grade ring, score, the read, a beat per real trade — nothing when there is no read', async () => {
  const el = await mount(<ChartPulse mint="M" beat={1.23} />);
  const b = el.querySelector('[data-testid="chart-pulse"]');
  expect(b.textContent).toContain('B'); expect(b.textContent).toContain('71'); expect(b.textContent).toContain('SEND IT');
  expect(b.className).toContain('is-good'); expect(b.getAttribute('data-tip')).toContain('FEELESS vital B');
  const none = await mount(<ChartPulse mint="X" beat={1} />);
  expect(none.querySelector('[data-testid="chart-pulse"]')).toBeNull();
});

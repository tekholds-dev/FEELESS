import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { EcoLive } from './EcoLive';

const mockCall = jest.fn();
let mockAdmin = true;
jest.mock('../../lib/adminCall', () => ({ useAdmin: () => ({ isAdmin: mockAdmin, call: mockCall }) }));

const books = { kpi: { feesUsd: 0.27, trades: 2, payers: 1, spendUsd: 1.31, calls: 197, perCallUsd: 0.0066, netUsd: -1.04, net7dUsd: -1.36, burnPerDayUsd: 0.187 },
  daily: Array.from({ length: 30 }, (_, i) => ({ d: `10-${i + 1}`, in: i === 28 ? 0.27 : 0, out: i > 26 ? 0.4 : 0, net: 0, cum: 0 })),
  byModel: [{ k: 'hy4', usd: 0.84 }, { k: 'claude-sonnet-5.5', usd: 0.39 }], byJob: [{ k: 'pos', usd: 1.3 }],
  card: { putInUsd: 54.63, open: 3, openCostUsd: 2.07, net7dUsd: -0.054, trips7d: 1, verdict: 'NO PROVEN EDGE', asOf: 1794511579 }, say: 'Models cost 4.9× what fees bring in.' };

test('🏦 PoEco live books: the owner sees his real business with nothing typed in, and nobody else sees it', async () => {
  mockCall.mockResolvedValue(books);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<EcoLive />); });
  const t = el.querySelector('[data-testid="eco-live"]').textContent;
  expect(mockCall).toHaveBeenCalledWith('/admin/eco/live');
  expect(t).toContain('4.9×'); expect(t).toContain('197 calls'); expect(t).toContain('hy4'); expect(t).toContain('NO PROVEN EDGE'); expect(t).toContain('$54.63');
  expect(t).toContain('7 DAYS');                                  // the chart starts where the money starts, at least a week
  await act(async () => { root.unmount(); });
  mockAdmin = false;
  const el2 = document.createElement('div'); document.body.appendChild(el2); const r2 = createRoot(el2);
  await act(async () => { r2.render(<EcoLive />); });
  expect(el2.innerHTML).toBe('');
  await act(async () => { r2.unmount(); }); el.remove(); el2.remove();
});

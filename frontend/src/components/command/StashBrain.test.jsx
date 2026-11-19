import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { StashBrain, stashVerdict } from './StashBrain';

jest.mock('recharts', () => { const R = require('react'); const Box = ({ children }) => R.createElement('div', null, children); return { ResponsiveContainer: Box, AreaChart: Box, Area: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null }; });

const DATA = { pages: 12, bytes: 3400000, hits: 4, browsed: 8, hitRate: 0.333, savedSecs: 50, savedUsd: 0.0012, paidEqUsd: 0.048,
  cats: [{ cat: 'nba', pages: 9, bytes: 3000000, fresh: 6, lastAt: Date.now() / 1000 - 120, numbers: 812, shots: 9, statics: 9, hits: 4, browsed: 5, savedSecs: 50, savedUsd: 0.0012, paidEqUsd: 0.048, hitRate: 0.444 },
    { cat: 'search', pages: 3, bytes: 400000, fresh: 1, lastAt: Date.now() / 1000 - 600, numbers: 20, shots: 0, statics: 3, hits: 0, browsed: 3, savedSecs: 0, savedUsd: 0, paidEqUsd: 0, hitRate: 0 }],
  days: [{ day: '2026-11-18', added: 0, total: 0, byCat: {} }, { day: '2026-11-19', added: 12, total: 12, byCat: { nba: 9, search: 3 } }],
  runs: [{ kind: 'pob', at: Date.now() / 1000 - 60, hits: 4, browsed: 2, savedSecs: 50, savedUsd: 0.0012, paidEqUsd: 0.048, proof: true }] };

test('🧠 the stash panel shows growth, hit rate and $ saved by category, from the stash API, and never a page', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => DATA }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<StashBrain />); });
  expect(global.fetch).toHaveBeenCalledWith('/api/cats/proofs/stash-brain');
  expect(el.querySelector('[data-testid="sbr-say"]').textContent).toContain('33% of 12 page reads');
  const nba = el.querySelector('[data-testid="sbr-cat-nba"]').textContent;
  expect(nba).toContain('NBA'); expect(nba).toContain('hit rate 44%'); expect(nba).toContain('812 numbers'); expect(nba).toContain('$0.05 paid-eq');
  await act(async () => { [...el.querySelectorAll('.sbr-lens button')].find(b => b.textContent === 'Last runs').click(); });
  expect(el.querySelector('[data-testid="sbr-runs"]').textContent).toContain('PoB'); expect(el.textContent).toContain('4/6');
  act(() => root.unmount()); el.remove();
});

test('🧠 an empty stash says so, and one nobody reused yet says the next related run will', () => {
  expect(stashVerdict({ pages: 0 })).toMatch(/Empty/);
  expect(stashVerdict({ pages: 5, hits: 0, browsed: 5 })).toMatch(/No brain has reused one yet/);
});

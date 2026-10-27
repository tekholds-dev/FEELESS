import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { tankDots, laneCounts, capX, TANK_LEVELS, LiveTank } from './LiveTank';

test('🫧 the intake lanes: every read lands on its own water level, across = live MC (log $1K…$10M), colour = what it is doing', () => {
  expect(capX(1e3)).toBe(0); expect(capX(1e7)).toBe(1); expect(capX(1e5)).toBeCloseTo(0.5);
  const intake = { coins: [{ mint: 'A', sym: 'A', mc: 5e4, ch: 5, status: 'READY', germ: 4, pair: 'PA' }, { mint: 'B', sym: 'B', mc: 5e5, ch: -5, status: 'CONTENDING', germ: 30 }] };
  const pump = { launches: [{ mint: 'N1', symbol: 'N1', marketCapUsd: 8000, curveProgress: 90 }, { mint: 'N2', symbol: 'N2', marketCapUsd: 4000, curveProgress: 5 }] };
  const trend = { pairs: [{ pairAddress: 'T', baseToken: { address: 'MT', symbol: 'X' }, priceChange: { h1: 40 }, marketCap: 1e6 }] };
  const dots = tankDots({ pump, intake, trend, top: null }); const lane = k => TANK_LEVELS.findIndex(l => l[0] === k);
  const n = laneCounts(dots);
  expect(n[lane('germ')]).toBe(1); expect(n[lane('desk')]).toBe(2); expect(n[lane('new')]).toBe(2); expect(n[lane('trend')]).toBe(1); expect(n[lane('top')]).toBe(0);
  expect(dots.find(d => d.id === 'g-A').tone).toBe('germ');                // at its germ floor
  expect(dots.find(d => d.id === 'd-A').tone).toBe('hot');                 // READY glows gold
  expect(dots.find(d => d.id === 'd-B').tone).toBe('dn');
  expect(dots.find(d => d.id === 'n-N1').tone).toBe('hot');                // about to graduate
  expect(dots.find(d => d.id === 'n-N2').tone).toBe('q');
  expect(dots.find(d => d.id === 'trend-T').pair.pairAddress).toBe('T');   // a tap opens its war room
  expect(tankDots({})).toEqual([]);
});

test('🔎 a tap pops the coin\'s vitals first — CHART opens its war room only from the popup', async () => {
  const intake = { coins: [{ mint: 'A', sym: 'AAA', mc: 5e4, ch: 5, status: 'READY', germ: 30, pair: 'PA' }] };
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('intake') ? intake : {}) }));
  const seen = []; const on = e => seen.push(e.detail); window.addEventListener('feeless:war-room', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<LiveTank />); }); await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  await act(async () => { document.querySelector('[data-testid="ltk-dot-d-A"]').click(); });
  expect(seen).toEqual([]);                                                   // nothing opened yet
  const pop = document.querySelector('[data-testid="ltk-pop"]'); expect(pop.textContent).toContain('$AAA'); expect(pop.textContent).toContain('READY');
  await act(async () => { document.querySelector('[data-testid="ltk-chart"]').click(); });
  expect(seen[0]).toMatchObject({ pairAddress: 'PA' }); expect(document.querySelector('[data-testid="ltk-pop"]')).toBeNull();
  window.removeEventListener('feeless:war-room', on); act(() => root.unmount());
});

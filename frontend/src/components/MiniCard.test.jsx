import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./FuseCard', () => ({ LiveFuseCard: ({ r, label }) => <div data-testid="stub-card">{r.name}|{label}|{r.legs.length}</div> }));
jest.mock('./MiniChartBody', () => ({ __esModule: true, default: ({ pair, tf, fuse }) => <div data-testid="stub-chart" data-fuse={fuse?.entry || ''}>{pair.pairAddress}:{tf}</div> }));
jest.mock('./ArenaPrime', () => ({ TIER: { blaze: { aura: 'fire', look: {} }, gold: { aura: '', look: {} } },
  usePrime: () => ({ cfg: { sl: 15 }, cards: [{ tpl: 'degen', tier: 'blaze', label: '🔥 Prime Blaze', real: true, legs: [{ pairAddress: 'PA', symbol: 'AAA', mint: 'MA', entry: 0.002 }, { pairAddress: 'PB', symbol: 'BBB', mint: 'MB', entry: 0.5 }] }] }),
  primeRow: c => ({ id: c.tpl, name: c.label, legs: c.legs.map(l => ({ ...l, pnlPct: 12.3 })) }),
  fuseLevels: (l, cf, label) => ({ card: label, entry: l.entry }) }));
jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('mini card: opens from a Fuse card, flips card ⇄ chart of any of its coins, changes size, survives a remount, closes', async () => {
  window.localStorage.clear();
  const { MiniCardHost, openMiniCard } = require('./MiniCard');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<MiniCardHost />); });
  const m = () => document.querySelector('[data-testid="mini-card"]'); const q = id => m().querySelector(`[data-testid="${id}"]`);
  expect(m()).toBeNull();
  await act(async () => { openMiniCard({ kind: 'prime', tpl: 'degen', name: '🔥 Prime Blaze' }); }); await tick(50);
  expect(m().textContent).toContain('🔥 Prime Blaze'); expect(q('stub-card').textContent).toBe('🔥 Prime Blaze|💵 REAL · FUSE WALLET|2');
  expect(m().className).toContain('sz-m');
  await act(async () => { q('mcd-side-chart').click(); }); await tick(20);               // flip to the chart: first coin, the card's entry line
  expect(q('stub-card')).toBeNull(); expect(q('stub-chart').textContent).toBe('PA:5m'); expect(q('stub-chart').dataset.fuse).toBe('0.002');
  expect(q('mcd-coin-AAA').textContent).toContain('+12.3%');
  await act(async () => { q('mcd-coin-BBB').click(); }); await act(async () => { q('mcd-tf-15m').click(); }); await tick(20);
  expect(q('stub-chart').textContent).toBe('PB:15m'); expect(q('stub-chart').dataset.fuse).toBe('0.5');
  await act(async () => { q('mcd-size').click(); }); expect(m().className).toContain('sz-l');   // expandable: m → l → s
  await act(async () => { q('mcd-size').click(); }); expect(m().className).toContain('sz-s');
  await act(async () => { root.unmount(); });                                             // leave the page…
  const el2 = document.createElement('div'); document.body.appendChild(el2); const root2 = createRoot(el2);
  await act(async () => { root2.render(<MiniCardHost />); }); await tick(50);
  expect(m().className).toContain('sz-s'); expect(q('stub-chart')).not.toBeNull();        // …same card, side and size on the next one
  await act(async () => { q('mcd-side-card').click(); }); await tick(20); expect(q('stub-card')).not.toBeNull();
  // a card you hold travels as a snapshot of its own coins
  await act(async () => { openMiniCard({ kind: 'row', name: 'My Fuse', row: { id: 'r1', name: 'My Fuse', legs: [{ pairAddress: 'PZ', symbol: 'ZZZ', usd: 2, tokens: 4 }] } }); }); await tick(50);
  expect(q('stub-card').textContent).toBe('My Fuse||1');
  await act(async () => { q('mcd-side-chart').click(); }); await tick(20); expect(q('stub-chart').dataset.fuse).toBe('0.5');   // entry = $ in ÷ coins
  await act(async () => { q('mcd-close').click(); });
  expect(m()).toBeNull(); expect(window.localStorage.getItem('feeless.miniCard')).toBeNull();
  await act(async () => { root2.unmount(); });
});

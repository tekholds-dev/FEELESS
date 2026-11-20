import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { PopDash, popNumbers, liqPrice, mindWhy, sitKind, rulerAt, STAKE_USD } from './PopDash';

jest.mock('../perps/PerpsChart', () => ({ PerpsChart: ({ asset, lines }) => <div data-testid="perps-chart" data-asset={asset} data-lines={(lines || []).map(l => `${l.id}:${l.price.toFixed(2)}`).join(',')} /> }));
global.IS_REACT_ACT_ENVIRONMENT = true;
const now = Math.floor(Date.now() / 1000);
// shaped exactly like backend/pop.py: close() files roePct + pnlUsd = COLLATERAL_USD × roe (no fee); a no-trade folder keeps each mind's raw reply
const FOLDERS = [
  { id: 'p3', n: 3, at: now - 600, status: 'closed', side: 'long', market: 'SOL', lev: 2, tp: 3, sl: 1.5, entry: 100, exit: 103, roePct: 6, pnlUsd: 0.6, won: true, closedAt: now - 300, cost: 0.01 },
  { id: 'p2', n: 2, at: now - 1200, status: 'closed', side: 'short', market: 'BTC', lev: 2, tp: 3, sl: 1.5, entry: 100, roePct: -3, pnlUsd: -0.3, won: false, closedAt: now - 900, cost: 0.01, test: { agent: 'Happy' } },
  { id: 'p1', n: 1, at: now - 3600, status: 'closed', noTrade: true, why: 'long SOL vs long BTC', reads: [{ market: 'SOL', px: 74.45, chgPct: 0.87 }], calls: [{ mind: 0, name: 'mind-a', market: 'SOL', side: 'long', lev: 2, why: 'higher lows' }, { mind: 1, name: 'mind-b', market: 'BTC', side: 'long', lev: 2, why: 'funding flat' }], cost: 0.008 },
  { id: 'p0', at: now - 7200, status: 'closed', noTrade: true, why: 'a mind called no trade', calls: [{ mind: 0, name: 'gpt-x', why: '{"market":"SOL","side":"none","lev":1.1,"tp_pct":0,"sl_pct":' }, { mind: 1, name: 'gpt-y', why: '{"market":"SOL","side":"none","why":"tight range, nothing to tra' }] },
  { id: 'g1', n: 4, at: now - 100, status: 'closed', ghost: true, proposal: true, side: 'long', market: 'ETH', roePct: 9, won: true, conviction: 'blind' },
];
const LIVE = { id: 'live1', status: 'open', side: 'long', market: 'SOL', lev: 2, tp: 3, sl: 1.5, entry: 100, mark: 101, roePct: 2, openedAt: now - 540, liqPct: 45, calls: [{ mind: 0, name: 'mind-a', why: '{"market":"SOL","side":"long","why":"breakout"}' }] };

test('📉 popNumbers: paper P&L with no fees, win rate without ghosts, sit-outs by reason, the open position', () => {
  const n = popNumbers(FOLDERS, LIVE, null);
  expect(n.trades.map(f => f.id)).toEqual(['p2', 'p3']);   // oldest first, the ghost and no-trades left out
  expect(n.pnl).toBeCloseTo(0.3); expect(n.winPct).toBe(50); expect(n.ghosts).toHaveLength(1); expect(n.ghostWon).toBe(1);
  expect(n.sits.map(f => f.id)).toEqual(['p1', 'p0']); expect(n.bySit).toEqual({ split: 1, passed: 1 });
  expect(n.open).toHaveLength(1); expect(n.openPnl).toBeCloseTo(STAKE_USD * 0.02);
  expect(popNumbers([{ id: 'x', status: 'closed', roePct: 10, side: 'long', market: 'SOL' }]).pnl).toBeCloseTo(1);   // no pnlUsd filed → stake × ROE, never a fee
});

test('☠ liquidation, the ruler and a mind\'s reason read right', () => {
  expect(liqPrice(LIVE)).toBeCloseTo(55); expect(liqPrice({ ...LIVE, side: 'short' })).toBeCloseTo(145); expect(liqPrice({ entry: 100, lev: 5, side: 'long' })).toBeCloseTo(82);
  const r = rulerAt(LIVE); expect(r.sl).toBeCloseTo(98.5); expect(r.tp).toBeCloseTo(103); expect(r.mark).toBeGreaterThan(0.62); expect(r.mark).toBeLessThan(1);
  expect(rulerAt({ ...LIVE, mark: 40 }).mark).toBe(0); expect(rulerAt({ ...LIVE, side: 'short', mark: 99 }).mark).toBeGreaterThan(0.62);
  expect(mindWhy('{"market":"SOL","side":"none","why":"tight range"}')).toBe('tight range');
  expect(mindWhy('{"market":"SOL","side":"none","why":"tight range, nothing to tra')).toBe('tight range, nothing to tra…');
  expect(mindWhy('{"market":"SOL","side":"none","lev":1.1,"tp_pct":0,"sl_pct":')).toMatch(/no trade/);
  expect(mindWhy('plain words')).toBe('plain words'); expect(sitKind(FOLDERS[2])).toBe('split'); expect(sitKind({ calls: [] })).toBe('nocall');
});

test('🖥 PopDash: the desk shows the paper position (entry / mark / liq / P&L) on the true chart; sat out and filed open their folders; the doors call the engine', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const sent = []; const opened = [];
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  await act(async () => { root.render(<PopDash d={{ popFolders: FOLDERS, popFolder: LIVE }} send={j => sent.push(j)} onOpen={id => opened.push(id)} tools={<p data-testid="old-home">tiles</p>} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('ppx-pnl').textContent).toBe('+$0.30'); expect(q('ppx-win').textContent).toBe('50%'); expect(q('ppx-open-n').textContent).toBe('1'); expect(q('ppx-sit-n').textContent).toContain('2');
  expect(q('ppx-pos-mark').textContent).toBe('$101'); expect(q('ppx-pos-liq').textContent).toBe('$55'); expect(q('ppx-pos-pnl').textContent).toBe('+$0.20');
  expect(q('ppx-pos').textContent).toContain('breakout'); expect(q('pop-start')).toBeNull();   // an open position: no second PoP
  expect(q('perps-chart').dataset.asset).toBe('SOL'); expect(q('perps-chart').dataset.lines).toContain('liq:55.00');
  await act(async () => { q('pop-stop').click(); }); expect(sent).toEqual(['stop']);
  await act(async () => { q('ppx-mk-BTC').click(); }); expect(q('perps-chart').dataset.asset).toBe('BTC'); expect(q('perps-chart').dataset.lines).toBe('');
  await act(async () => { q('ppx-tab-sit').click(); }); expect(q('ppx-sits').textContent).toContain('funding flat'); expect(q('ppx-sits').textContent).toContain('tight range, nothing to tra…');
  await act(async () => { q('ppx-sit-p1').click(); }); expect(opened).toEqual(['p1']);
  await act(async () => { q('ppx-tab-filed').click(); }); expect(q('pop-x-p3').textContent).toContain('+6.00%'); expect(q('pop-x-g1').textContent).toContain('not counted'); expect(q('pop-x-p2').querySelector('[data-testid="trc-test"]')).not.toBeNull();
  await act(async () => { q('ppx-tab-tools').click(); }); expect(q('old-home')).not.toBeNull();   // the old home lives one tab away (no back pedal)
  await act(async () => { root.render(<PopDash d={{ popFolders: FOLDERS }} send={j => sent.push(j)} onOpen={() => {}} />); });
  await act(async () => { q('ppx-tab-desk').click(); }); expect(q('ppx-lastsit').textContent).toContain('SPLIT'); expect(q('ppx-lastsit').textContent).toContain('funding flat');
  await act(async () => { q('pop-start').click(); }); await act(async () => { q('pop-propose').click(); }); expect(sent).toEqual(['stop', 'start', 'propose']);
  await act(async () => { root.unmount(); }); el.remove(); try { localStorage.removeItem('feeless.popDashTab'); } catch { /* none */ }
});

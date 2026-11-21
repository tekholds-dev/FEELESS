import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatDesk } from './CatDesk';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../terminal/PriceChart', () => ({ PriceChart: () => null }));   // lightweight-charts is ESM jest can't parse (the desk's live windows load it lazily)
const today = new Date().toISOString().slice(0, 10);
const CAT = { id: 'c1', name: 'Specter', handle: 'specter', avatar: 'Solaris Spots', look: { gear: 'crown', aura: 'gold', eyes: 'laser' }, status: 'running', level: 2, xp: 60, wallet: 'W'.repeat(44),
  balanceSol: 9.6, startingBalanceSol: 10, realizedPnlSol: -0.12, totalPnlSol: -0.08, wins: 3, losses: 5, winRate: 38, strategyLabel: 'Breakouts',
  positions: [{ symbol: 'MOON', pairAddress: 'P1', mint: 'M1', currentChange: 12.5, costSol: 0.25, openedAt: Date.now() / 1000 - 1800, reason: 'germ floor held' }, { symbol: 'RUG', pairAddress: 'P2', currentChange: -20, costSol: 0.2 }],
  pnlHistory: [{ value: 0 }, { value: 0.1 }, { value: -0.2 }, { value: -0.08 }], risk: { maxPositionSol: 0.25, maxDailyLossSol: 0.5, allowlist: [], blocklist: ['SCAM'] },
  dailyLoss: { [today]: 0.4 }, learn: { params: { runnerTrail: 25, takeProfit1: 40 }, log: [{ note: 'Sold $X at +8 %, it ran +60 % — give runners room' }] } };

// 🖥 its own file: the look change re-renders every mounted desk, so it runs apart from CatDesk.test's desks
test('🖥 Slice 34: the trading desk wears the Desk look by default (its backdrop + BG picker, no wallpaper skin), every control still there; Classic brings the skin back', async () => {
  localStorage.removeItem('feeless.deskLook'); HTMLCanvasElement.prototype.getContext = () => null;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onAct = jest.fn();
  await act(async () => { root.render(<CatDesk cat={CAT} onBack={() => {}} onAct={onAct} />); });
  const desk = el.querySelector('[data-testid="cat-desk"]'); expect(desk.className).toContain('is-dl');
  expect(el.querySelector('[data-testid="dkl-bg"]')).not.toBeNull();
  await act(async () => { el.querySelector('[data-testid="kd-dl-bg-grid"]').click(); });
  expect(JSON.parse(localStorage.getItem('feeless.deskLook')).bg).toBe('grid'); expect(el.querySelector('[data-testid="dkl-bg"]').dataset.bg).toBe('grid');
  await act(async () => { el.querySelector('[data-testid="kd-dl-classic"]').click(); });
  expect(el.querySelector('[data-testid="cat-desk"]').className).not.toContain('is-dl'); expect(el.querySelector('[data-testid="kd-dl-on"]')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove(); localStorage.removeItem('feeless.deskLook');
});

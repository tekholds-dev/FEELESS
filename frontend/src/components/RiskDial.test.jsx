import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { RiskDial, DialBoard } from './RiskDial';
import { applyRisk, RISK_DIALS } from '../lib/riskDial';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await act(() => new Promise(r => setTimeout(r, 20))); return el; };

test('one dial expands to every coin limit + profit level + collect/compound + rotation (mirrors the server)', () => {
  const legs = [{ pairAddress: 'P' }, { pairAddress: 'R', runner: true }];
  expect(applyRisk(legs, 'safe')).toEqual({ risk: 'safe', at: 25, onProfit: 'collect', mode: 'hold', legs: { P: { tp: 30, sl: 15 }, R: { tp: 30, sl: 15 } } });
  expect(applyRisk(legs, 'balanced').legs.R).toEqual({ tp: 50, sl: 30 });
  expect(applyRisk(legs, 'degen')).toMatchObject({ mode: 'swap', onProfit: 'compound', at: 100 });
  expect(Object.keys(RISK_DIALS)).toEqual(['safe', 'balanced', 'degen']);
});

test('dial shows each option\'s Arena paper proof and picks with one tap', async () => {
  const on = jest.fn();
  const el = await mount(<RiskDial value="custom" onChange={on} proofs={{ safe: { rounds: 9, avgPct: 4.2, winRate: 67, lit: true }, degen: { rounds: 9, avgPct: -3, winRate: 30 } }} />);
  expect(el.textContent).toContain('+4.2% · 67% won · 🔥'); expect(el.textContent).toContain('proving…'); expect(el.textContent).toContain('✎ Custom');
  await act(async () => { el.querySelector('[data-testid="risk-degen"]').click(); });
  expect(on).toHaveBeenCalledWith('degen');
});

test('dial board marks the best dial and the proven ones', async () => {
  const el = await mount(<DialBoard dials={{ safe: { rounds: 10, avgPct: 3, winRate: 60, per1: 1.03, lit: true }, balanced: { rounds: 10, avgPct: 6, winRate: 55, per1: 1.06 }, degen: { rounds: 0 } }} />);
  expect(el.querySelector('.dboard-tile.is-best').textContent).toContain('Balanced'); expect(el.querySelector('.is-lit').textContent).toContain('🔥 proven');
  expect(el.textContent).toContain('first rounds dealing');
});

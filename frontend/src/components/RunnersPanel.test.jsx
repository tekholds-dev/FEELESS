import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { RunnersPanel } from './RunnersPanel';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./CaseFile', () => ({ investigate: () => {} }));
jest.mock('./FuseGo', () => ({ FuseGo: ({ legs }) => <div data-testid="go">{legs.map(l => l.symbol).join(',')}</div> }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const pick = (mint, lane, extra = {}) => ({ mint, symbol: mint.toUpperCase(), pairAddress: `P${mint}`, lane, stage: lane === 'scalp' ? 'curve' : 'graduated', curve: 80, score: 72, entry: 1, now: 1.3, price: 1.3, chg1h: 40, liq: 1e5, streak: lane === 'hold' ? 3 : 1, parts: [{ part: 'momentum', points: 20, why: '+200% in 1h' }], exits: 'x', ...extra });
const DATA = proof => ({ live: [pick('aaa', 'scalp')], dropped: [{ mint: 'rug', symbol: 'RUG', gates: ['Top 10 under 30%'] }], seen: 30, nextRoundAt: Date.now() / 1000 + 300, history: [{ id: 'r', at: 1, symbols: ['A'], pct: 12 }],
  round: { picks: [pick('aaa', 'scalp'), pick('bbb', 'runner'), pick('ccc', 'hold')] }, proof, exits: { scalp: 'Sell all at +50%', runner: '⅓ at +50%', hold: 'Trail 30' }, gates: ['Under 48h old'], lightMinRounds: 8, solUsd: 200 });

test('lanes, proof gate: the Fuse button stays locked until the paper proof lights', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => DATA({ rounds: 3, avgPct: 5, winRate: 67, lights: false, per1: 1.05, need: 5 }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<RunnersPanel />); }); await tick(20);
  expect(el.textContent).toContain('SCALP'); expect(el.textContent).toContain('↻3'); expect(el.textContent).toContain('PROVING · 5 more rounds');
  expect(el.querySelector('[data-testid="rn-go"]').disabled).toBe(true); expect(el.querySelector('.rn-override')).toBeNull();   // no override for traders
});

test('lit proof unlocks one-click with every runner in the round', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => DATA({ rounds: 10, avgPct: 14, winRate: 60, lights: true, per1: 1.14, need: 0 }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<RunnersPanel />); }); await tick(20);
  expect(el.textContent).toContain('🔥 LIT');
  await act(async () => { el.querySelector('[data-testid="rn-go"]').click(); });
  expect(el.querySelector('[data-testid="go"]').textContent).toBe('AAA,BBB,CCC');
});

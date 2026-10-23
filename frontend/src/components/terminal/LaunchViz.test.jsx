import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LaunchStage, StepRing, stepFill, FeeDonut, SnipeDecay, CoinFace, launchEnds, curvePts, feeSplit, money } from './LaunchViz';
import { DEFAULT_META_LAUNCH_FORM } from './MetaLaunchSetup';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const F = { ...DEFAULT_META_LAUNCH_FORM, name: 'Degen Rocket', symbol: 'drkt' };

test('pure: the launch ends, the curve shape, step fill and the fee split', () => {
  expect(launchEnds(F, { solPx: 100 })).toMatchObject({ open: '$35K', grad: '85 SOL', gradUsd: 8500, curve: 'linear' });
  expect(launchEnds({ ...F, liquidityPair: 'USDC' }).gradUsd).toBe(85);
  expect(launchEnds({ ...F, liquidityPair: 'BONK' }, { solPx: 100 }).gradUsd).toBeNull();                 // no honest $ for a meme quote
  const rail = { params: { initialMarketCap: 30, migrationMarketCap: 500, quote: 'SOL' } };
  expect(launchEnds(F, { rail, locked: true, solPx: 100 })).toMatchObject({ open: '30 SOL', openUsd: 3000, grad: '500 SOL MC', gradUsd: 50000 });   // the rail's terms win
  expect(launchEnds(F, { pump: true })).toMatchObject({ grad: 'PumpSwap', pump: true });
  const lin = curvePts('linear'); const exp = curvePts('exponential');
  expect(lin[0][1]).toBeCloseTo(exp[0][1]); expect(lin[27][1]).toBeCloseTo(exp[27][1]);
  expect(exp[14][1]).toBeGreaterThan(lin[14][1]);                                                            // exponential stays low then rips (y grows down)
  expect(stepFill({ name: 'a', symbol: 'B' }, 1)).toBe(0.5); expect(stepFill({ name: 'a', symbol: 'B' }, 1, { symbol: 'bad' })).toBe(0.25);
  expect(stepFill(F, 2)).toBe(1);
  const s = feeSplit(F); expect(s.total).toBe(100); expect(s.perVol).toBe(100); expect(s.parts.find(p => p.k === 'creatorFeeShare').usd).toBe(40);
  expect(money(8500)).toBe('$8.5K'); expect(money(52000)).toBe('$52K'); expect(money(0)).toBe('$0');
});

test('drawn: the stage rides your step, rings fill, the fee ring + sniper decay + coin face read the form live', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<><LaunchStage form={F} solPx={100} step={2} /><StepRing fill={0.5} n={1} /><StepRing fill={1} n={2} done /><FeeDonut form={F} /><SnipeDecay tax="50" window="6" /><CoinFace form={F} /></>); });
  expect(q('launch-stage').textContent).toContain('$35K'); expect(q('launch-stage').textContent).toContain('≈ $8.5K');
  expect(el.querySelector('.lv-nodes li.is-now').textContent).toContain('CURVE'); expect(el.querySelectorAll('.lv-nodes li.is-done')).toHaveLength(1);
  const r1 = el.querySelector('.lv-rocket').style.transform;
  await act(async () => { root.render(<LaunchStage form={F} solPx={100} step={3} />); });
  expect(el.querySelector('.lv-rocket').style.transform).not.toBe(r1);                                       // the rocket climbs with the steps
  await act(async () => { root.render(<><StepRing fill={0.5} n={1} /><StepRing fill={1} n={2} done /><FeeDonut form={F} /><SnipeDecay tax="50" window="6" /><CoinFace form={F} /></>); });
  expect(q('step-ring-2').className).toContain('is-full'); expect(q('step-ring-2').textContent).toBe('✓'); expect(q('step-ring-1').textContent).toBe('1');
  expect(q('fee-donut').className).toContain('is-ok'); expect(q('fee-donut').textContent).toContain('$40.00'); expect(el.querySelectorAll('.lv-donut .seg')).toHaveLength(3);   // a 0 % side draws no arc
  expect(q('snipe-decay').textContent).toContain('sniper pays 50%'); expect(q('snipe-decay').textContent).toContain('6s');
  expect(q('coin-face').textContent).toContain('$DRKT'); expect(q('coin-face').textContent).toContain('1,000,000,000 supply');
  await act(async () => { root.render(<><FeeDonut form={{ ...F, creatorFeeShare: '30' }} /><SnipeDecay tax="0" window="6" /></>); });
  expect(q('fee-donut').className).toContain('is-off'); expect(q('fee-donut').textContent).toContain('MUST = 100');
  expect(q('snipe-decay').textContent).toContain('No opening tax');
  await act(async () => { root.unmount(); });
});

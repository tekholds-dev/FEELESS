import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { OfficeBoard, OfficeMission, ChartBox, DataLine, dqWord, DQ_CLS, PositionCard, TakeLine, actionResult, nextDuty, clock, ago, sgn, ms, entryCls, STAGE_CLS, STRUCT_CLS, DECISION_CLS } from './OfficeBoard';
import office from './__fixtures__/office.json';

const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('the mission shows the real card\'s own numbers, the lock, lives, the duty clock and what the LEDGER says of the last action', async () => {
  const el = await mount(<OfficeMission m={office.mission} />);
  expect(q(el, 'ofb-putin').textContent).toContain('$29.50');
  expect(q(el, 'ofb-value').textContent).toContain('$1.24');
  expect(q(el, 'ofb-be').textContent).toContain('−$28.26');
  expect(q(el, 'ofb-be').textContent).toContain('needs 23.8×');
  expect(q(el, 'ofb-be').textContent).toContain('BREAKEVEN $29.50');
  expect(q(el, 'ofb-phase').textContent).toContain('RECOVERY');                            // phase 1 of the real-money mission
  expect(q(el, 'ofb-double').textContent).toContain('DOUBLE TARGET $59.00');               // 2× the put-in = the graduation target
  expect(q(el, 'ofb-double').textContent).toContain('−$57.76');
  expect(q(el, 'ofb-stage').textContent).toContain('5 MIN');
  expect(q(el, 'ofb-lock').textContent).toContain('NEXT STAGE');
  expect(q(el, 'ofb-lock').textContent).toContain('LOCKED');
  expect(q(el, 'ofb-unlock').textContent).toContain('real equity ≥ $59.00');               // the unlock condition is on screen, not in a tip
  expect(q(el, 'ofb-lock').getAttribute('data-tip')).toContain('breakeven is milestone 1, not graduation');
  expect(q(el, 'ofb-lives').textContent).toContain('9 / 9');
  expect(q(el, 'ofb-duty').textContent).toContain('next duty');
  expect(q(el, 'ofb-last').textContent).toContain('FILL $c3');
  expect(q(el, 'ofb-last').textContent).toContain('CONFIRMED on-chain');
  // breakeven reached = GROWTH mode: the milestone is ticked and the next stage is STILL locked
  const grow = await mount(<OfficeMission m={{ ...office.mission, phase: 'GROWTH', toBreakeven: 1.5, toDouble: -28, value: 31, needX2: 1.9 }} />);
  expect(q(grow, 'ofb-phase').textContent).toContain('GROWTH');
  expect(q(grow, 'ofb-be').textContent).toContain('✓ reached');
  expect(q(grow, 'ofb-be').textContent).toContain('not graduation');
  expect(q(grow, 'ofb-double').textContent).toContain('−$28.00');
  expect(q(grow, 'ofb-lock').textContent).toContain('LOCKED');
  const done = await mount(<OfficeMission m={{ ...office.mission, phase: 'GRADUATED', locked: false, lock: 'ELIGIBLE', toBreakeven: 30.5, toDouble: 1, value: 60 }} />);
  expect(q(done, 'ofb-lock').textContent).toContain('ELIGIBLE');
  expect(q(done, 'ofb-double').textContent).toContain('✓ reached');
  const cold = await mount(<OfficeMission m={null} />);
  expect(q(cold, 'ofb-mission').textContent).toContain('waiting for the agents');           // no payload = it says so, it shows no number
});

test('a sent order is never shown as filled: the result line is the ledger state', () => {
  expect(actionResult({ state: 'none' })[1]).toContain('NOT CONFIRMED YET');
  expect(actionResult(undefined)[1]).toContain('NOT CONFIRMED YET');
  expect(actionResult({ state: 'failed', err: 'slippage exceeded on-chain' })[1]).toBe('FAILED — slippage exceeded on-chain');
  expect(actionResult({ state: 'refused', err: 'pool too thin' })[0]).toBe('is-obj');
  expect(actionResult({ state: 'vetoed' })[1]).toContain('nothing was sent');
  expect(actionResult({ state: 'confirmed', delta: 0.21, realPct: -4 })[1]).toBe('CONFIRMED on-chain · +0.21% vs mid · -4.0% real');
  expect(nextDuty({ control: false })).toBeNull();
  expect(nextDuty({ control: true, dutyAt: 1000, dutyEvery: 600 }, 1200)).toBe(400);
  expect(nextDuty({ control: true, dutyAt: 1000, dutyEvery: 600 }, 9999)).toBe(0);
  expect([clock(425), ago(100, 130), ago(0), sgn(null), sgn(2.345, 2), ms(0.123), ms(42.6), ms(null)]).toEqual(['7m 05s', '30s ago', '—', '—', '+2.35%', '0.12 ms', '43 ms', '—']);
});

test('the office board: the line of ten, ten live cards, and a desk opens to its rules, inputs, record and code', async () => {
  const el = await mount(<OfficeBoard o={office} />);
  const stages = [...el.querySelectorAll('.ofb-stage')];
  expect(stages.map(s => s.querySelector('button').getAttribute('data-testid'))).toEqual(['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge'].map(k => `stage-${k}`));
  expect(stages.every(s => Object.values(STAGE_CLS).some(c => s.classList.contains(c)))).toBe(true);
  expect(q(el, 'stage-devil').textContent).toMatch(/PASS|OBJECT/);
  expect(q(el, 'stage-tally').textContent).toMatch(/ms/);
  expect(q(el, 'ofb-cand').textContent).toContain(`$${office.currentCase.symbol}`);
  expect(q(el, 'ofb-checks').textContent).toContain('scan');
  expect(el.querySelectorAll('.ofb-agent').length).toBe(10);
  const reaper = q(el, 'office-reaper');
  for (const word of ['SURVIVAL', 'CONF', 'SAMPLES', 'GEN', 'LAST RUN', 'TASK', 'LAST DECISION', 'RULE IN PLAY', 'WHY THIS STATE', 'CONTRIBUTION']) expect(reaper.textContent).toContain(word);
  expect(q(el, 'office-tally').textContent).toMatch(/alive|probation/);
  expect(el.querySelector('[data-testid="detail-reaper"]')).toBeNull();
  await act(async () => { reaper.click(); });
  const d = q(el, 'detail-reaper');
  for (const id of ['sec-ideology', 'sec-ethics', 'sec-hard', 'sec-tunable', 'sec-inputs', 'sec-output', 'sec-recent', 'sec-learned', 'sec-survival', 'sec-gen', 'sec-code']) expect(d.querySelector(`[data-testid="${id}"]`)).not.toBeNull();
  expect(d.textContent).toContain('Never hold because of hope.');
  expect(d.textContent).toContain('backend/office.py');
  expect(d.textContent).toContain('reap()');
  expect(d.textContent).toContain('stopPct');
  expect(d.textContent).toContain('bounds 15 … 40');
  await act(async () => { q(el, 'stage-devil').click(); });                                   // a stage of the line opens that desk
  expect(q(el, 'detail-reaper')).toBeNull();
  expect(q(el, 'detail-devil').textContent).toContain('backend/agents.py');
  expect(q(el, 'detail-devil').textContent).toContain('devil_args()');
  await act(async () => { q(el, 'stage-devil').click(); });
  expect(q(el, 'detail-devil')).toBeNull();                                                   // … and closes it again
  const pos = q(el, 'pos-c3');
  expect(pos.textContent).toContain('REAPER: HOLD 5 MORE');
  expect(pos.textContent).toContain('🛡 ×0.5');
  expect(q(el, 'ofb-exec').textContent).toContain('HEALTHY');
  expect(q(el, 'ofb-exec').textContent).toContain('SENDS 1H');
  expect(q(el, 'ofb-perf').textContent).toContain('p95');
  expect(q(el, 'ofb-learn').textContent).toContain('in shadow');
});

test('before the first pass the board shows no numbers of its own', async () => {
  const el = await mount(<OfficeBoard o={{ cold: true, at: 0 }} />);
  expect(el.querySelectorAll('.ofb-agent').length).toBe(0);
  expect(q(el, 'office-board').textContent).toContain('waiting for the agents');
});

test('the chart box shows the structure, the four scores, and what Trigger, Devil and Warden made of the SAME snapshot', async () => {
  const cur = office.currentCase; const c = cur.chart;
  const el = await mount(<ChartBox c={c} cur={cur} />);
  const box = q(el, 'ofb-chart');
  expect(box.textContent).toContain(c.state);
  for (const m of ['TREND', 'CHOP', 'MOMENTUM', 'EXTENSION']) expect(q(el, `meter-${m}`).textContent).toContain('/100');
  expect(q(el, 'meter-TREND').textContent).toContain(String(Math.round(c.trend)));
  expect(box.textContent).toContain('FLOW');
  expect(box.textContent).toContain('LIQUIDITY');
  expect(q(el, 'chart-trigger').textContent).toContain(c.entry[0]);
  expect(q(el, 'chart-trigger').textContent).toContain(c.entry[1]);
  expect(q(el, 'chart-devil').textContent).toMatch(/NO OBJECTION|OBJECT/);
  expect(q(el, 'chart-warden').textContent).toContain('×');
  expect(q(el, 'chart-stop').textContent).toContain(`−${c.stop}%`);
  expect(q(el, 'chart-stop').textContent).toContain('catastrophic −45% (hard-coded)');
  expect(box.textContent).toContain(c.ev[0]);                                              // the evidence lines are the backend's own
  expect(box.querySelector('details').textContent).toContain('distHigh');
  // 🧪 the data-quality line is ON the chart box (not a tooltip): state + confidence, source, candles, trades, volume, liquidity, age
  const dq = q(el, 'ofb-dq');
  expect(dq.textContent).toContain('DATA QUALITY');
  expect(dq.textContent).toContain(`${dqWord(c.q)} ${c.q.conf}%`);
  expect(q(el, 'dq-source').textContent).toContain(c.q.candleSource);
  expect(q(el, 'dq-candles').textContent).toContain(c.q.label);
  expect(q(el, 'dq-volume').textContent).toMatch(/REAL|PARTIAL|UNAVAILABLE/);
  expect(q(el, 'dq-liq').textContent).toMatch(/REAL|STALE|UNKNOWN/);
  expect(q(el, 'dq-age').textContent).toContain('s ago');
  const tape = await mount(<ChartBox c={{ ...c, src: 'tape' }} cur={cur} />);
  expect(tape.textContent).toContain('RECONSTRUCTED FROM TAPE');
  expect(tape.textContent).toContain('tape readings');
  const none = await mount(<ChartBox c={null} cur={cur} />);
  expect(q(none, 'ofb-chart').textContent).toContain('nothing is claimed about its structure');  // no snapshot = no structure words
  expect([entryCls('ENTER NOW'), entryCls('SKIP'), entryCls('WAIT FOR PULLBACK')]).toEqual(['is-pass', 'is-veto', 'is-obj']);
  expect(STRUCT_CLS.CHOP).toBe('is-veto'); expect(STRUCT_CLS['PULLBACK IN UPTREND']).toBe('is-pass'); expect(STRUCT_CLS.PARABOLIC).toBe('is-obj');
});

test('a live position shows its entry thesis, the structure now, the review clock, Reaper\'s decision and the rule it obeys', async () => {
  const p = office.positions[0];
  const el = await mount(<PositionCard p={p} />);
  const t = q(el, `pos-${p.symbol}`).textContent;
  for (const w of ['ENTERED ON', 'STRUCTURE NOW', 'HELD', 'NOW', 'PEAK', 'FROM PEAK', 'NEXT REVIEW', 'LINES', 'OBEYING']) expect(t).toContain(w);
  expect(t).toContain(p.thesis.structure); expect(t).toContain(p.thesis.triggerRule); expect(t).toContain(`window ${p.window + 1} of ${p.granted}`);
  expect(t).toContain('thesis valid'); expect(t).toContain(p.obeying); expect(t).toContain(p.rule); expect(t).toContain(p.why[0]);
  expect(t).toContain(`hard ${p.hardStop}%`); expect(t).toContain('entry thesis (saved at the fill, never rewritten)');
  const exit = await mount(<PositionCard p={{ ...p, state: 'EXIT INVALIDATED', decision: 'EXIT', obeying: 'invalidation exit', rule: 'R5t thesis invalidated', evidence: '-3.0% — entered on UPTREND; now DOWNTREND', structure: 'DOWNTREND', verdict: 'invalid' }} />);
  expect(q(exit, `pos-${p.symbol}`).className).toContain('is-exit');
  expect(q(exit, `pos-${p.symbol}`).textContent).toContain('REAPER: EXIT'); expect(q(exit, `pos-${p.symbol}`).textContent).toContain('invalidation exit'); expect(q(exit, `pos-${p.symbol}`).textContent).toContain('thesis invalid');
  const old = await mount(<PositionCard p={{ ...p, thesis: null, verdict: null, window: null, why: [] }} />);
  expect(q(old, `pos-${p.symbol}`).textContent).toContain('no thesis on file');                                    // never an invented thesis
  expect(Object.keys(DECISION_CLS)).toEqual(['HOLD', 'HOLD 5 MORE', 'PROTECT', 'TAKE PROFIT', 'EXIT']);
});

test('the take line says base vs active, its source and the evidence behind a learned one', async () => {
  const base = await mount(<TakeLine t={office.take} />);
  expect(q(base, 'ofb-take').textContent).toContain('BASE TAKE+10%'); expect(q(base, 'ofb-take').textContent).toContain('ACTIVE TAKE+10%'); expect(q(base, 'ofb-take').textContent).toContain('SOURCEbase');
  expect(q(base, 'ofb-take').textContent).toContain('R6 take line');
  const learned = await mount(<TakeLine t={{ ...office.take, active: 20, source: 'learned', evidenceN: 34, shadowAvg: 1.9, adoptedAt: Date.now() / 1000 - 600, rule: 'agents.scalp_adopt — their own 5-min paths' }} />);
  const t = q(learned, 'ofb-take').textContent;
  expect(t).toContain('ACTIVE TAKE+20%'); expect(t).toContain('SOURCElearned'); expect(t).toContain('EVIDENCE N34'); expect(t).toContain('+1.90%'); expect(t).toContain('10m ago'); expect(t).toContain('scalp_adopt');
});

test('the board carries the chart box, the take line and the candle accounting in the one payload', async () => {
  const el = await mount(<OfficeBoard o={office} />);
  expect(q(el, 'ofb-chart')).not.toBeNull(); expect(q(el, 'ofb-take')).not.toBeNull();
  expect(q(el, 'ofb-candles').textContent).toContain('duplicated 0'); expect(q(el, 'ofb-candles').textContent).toContain('candle requests this pass');
  await act(async () => { q(el, 'office-reaper').click(); });
  expect(q(el, 'detail-reaper').textContent).toContain('backend/chart_intel.py'); expect(q(el, 'detail-reaper').textContent).toContain('review()');
  expect(q(el, 'detail-reaper').textContent).toContain('Never keep holding merely because a position is green.'); expect(q(el, 'detail-reaper').textContent).toContain('catastrophic stop −45%');
});

test('the data line names reconstructed, missing-volume and invalid data as exactly that — and never calls a trade count volume', async () => {
  const base = office.currentCase.chart.q;
  const tape = await mount(<DataLine q={{ ...base, state: 'NO_REAL_CANDLES', conf: 45, synthetic: true, realOhlc: false, enterOk: false, label: 'RECONSTRUCTED FROM TAPE · 22 readings', candleSource: 'RECONSTRUCTED FROM TAPE — closes only, highs / lows not measured', volume: 'UNAVAILABLE', why: 'reconstructed — not real OHLC candles' }} />);
  expect(tape.textContent).toContain('NO REAL CANDLES 45%');
  expect(tape.textContent).toContain('RECONSTRUCTED');
  expect(q(tape, 'dq-candles').textContent).toContain('RECONSTRUCTED FROM TAPE · 22 readings');
  expect(q(tape, 'dq-volume').textContent).toBe('VOLUME UNAVAILABLE');
  expect(q(tape, 'dq-why').textContent).toContain('not ENTER-grade');
  const bad = await mount(<DataLine q={{ ...base, state: 'MALFORMED', conf: 5, readOk: false, enterOk: false, why: '1 of 30 rows break high ≥ open/close ≥ low' }} degraded />);
  expect(bad.textContent).toContain('MALFORMED 5%');
  expect(bad.textContent).toContain('DATA DEGRADED');
  expect(q(bad, 'dq-why').textContent).toContain('DATA INVALID — not a verdict on the coin');
  const trades = await mount(<DataLine q={{ ...base, nTrades: 9, volume: 'UNAVAILABLE', volumeWord: 'VOLUME UNAVAILABLE' }} />);
  expect(q(trades, 'dq-trades').textContent).toContain('9 in the last 90s');                // a trade count is shown as TRADES …
  expect(q(trades, 'dq-volume').textContent).toBe('VOLUME UNAVAILABLE');                    // … and never as volume
  const none = await mount(<DataLine q={null} />);
  expect(none.textContent).toContain('NOT READ');
  expect(Object.keys(DQ_CLS)).toHaveLength(10);                                             // every one of the ten states has its look
  expect(STRUCT_CLS['DATA INVALID']).toBe('is-veto');
});

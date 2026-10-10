import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { OfficeBoard, OfficeMission, actionResult, nextDuty, clock, ago, sgn, ms, STAGE_CLS } from './OfficeBoard';
import office from './__fixtures__/office.json';

const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('the mission shows the real card\'s own numbers, the lock, lives, the duty clock and what the LEDGER says of the last action', async () => {
  const el = await mount(<OfficeMission m={office.mission} />);
  expect(q(el, 'ofb-putin').textContent).toContain('$29.50');
  expect(q(el, 'ofb-value').textContent).toContain('$1.24');
  expect(q(el, 'ofb-be').textContent).toContain('−$28.26');
  expect(q(el, 'ofb-be').textContent).toContain('needs 23.8×');
  expect(q(el, 'ofb-stage').textContent).toContain('5 MIN');
  expect(q(el, 'ofb-lock').textContent).toContain('LOCKED');
  expect(q(el, 'ofb-lock').getAttribute('data-tip')).toContain('real card value < real put-in');
  expect(q(el, 'ofb-lives').textContent).toContain('9 / 9');
  expect(q(el, 'ofb-last').textContent).toContain('FILL $c4');
  expect(q(el, 'ofb-last').textContent).toContain('CONFIRMED on-chain');
  const cleared = await mount(<OfficeMission m={{ ...office.mission, locked: false, lock: 'CLEARED', toBreakeven: 0.4, value: 29.9 }} />);
  expect(q(cleared, 'ofb-lock').textContent).toContain('CLEARED');
  expect(q(cleared, 'ofb-be').textContent).toContain('+$0.40');
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
  expect(q(el, 'stage-devil').textContent).toContain('OBJECT');
  expect(q(el, 'stage-tally').textContent).toMatch(/ms/);
  expect(q(el, 'ofb-cand').textContent).toContain(`$${office.currentCase.symbol}`);
  expect(q(el, 'ofb-checks').textContent).toContain('scan');
  expect(el.querySelectorAll('.ofb-agent').length).toBe(10);
  const reaper = q(el, 'office-reaper');
  for (const word of ['SURVIVAL', 'CONF', 'SAMPLES', 'GEN', 'LAST RUN', 'TASK', 'LAST DECISION', 'RULE IN PLAY', 'WHY THIS STATE', 'CONTRIBUTION']) expect(reaper.textContent).toContain(word);
  expect(q(el, 'office-tally').textContent).toContain('probation');
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
  const pos = q(el, 'pos-c4');
  expect(pos.textContent).toContain('PROTECT');
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

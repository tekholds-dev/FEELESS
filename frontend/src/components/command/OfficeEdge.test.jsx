import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { EdgeBand, ReadyStrip, SeatState, SwitchEval, CreatorLimits, ReviewQueue, MissedWinners, LaunchRecord, LIMIT_GROUPS, positionPolicy, optLabel } from './OfficeEdge';
import office from './__fixtures__/office.json';

// every panel here is a field of the ONE office payload (the fixture is built by the backend's own office_edge functions)
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('the band on the office: readiness · seats · switch test · your limits · review · missed winners — each opens its panel', async () => {
  const opened = [];
  const el = await mount(<EdgeBand o={office} onOpen={k => opened.push(k)} />);
  expect(q(el, 'oed-chip-ready').textContent).toContain('LIVE'); expect(q(el, 'oed-chip-seat').textContent).toContain(`${office.seat.held}/${office.seat.want}`);
  expect(q(el, 'oed-chip-seat').textContent).toContain('FILLING'); expect(q(el, 'oed-chip-switch').textContent).toContain('KEEP');
  const yours = office.policy.controls.filter(c => c.who === 'CREATOR OVERRIDE').length;
  expect(q(el, 'oed-chip-limits').textContent).toContain(`${yours} set`);
  expect(q(el, 'oed-chip-review').textContent).toContain(String(Object.values(office.review.open).reduce((a, b) => a + b, 0)));
  expect(q(el, 'oed-chip-missed').textContent).toContain(String(office.review.missedSummary.n));
  for (const k of ['ready', 'seat', 'switch', 'limits', 'review', 'missed']) await act(async () => { q(el, `oed-chip-${k}`).click(); });
  expect(opened).toEqual(['ready', 'seat', 'switch', 'limits', 'review', 'missed']);
  expect((await mount(<EdgeBand o={{ cold: true }} />)).innerHTML).toBe('');                                           // nothing before the first pass
});

test('restart readiness, the empty seat and the switch test say exactly what the payload says', async () => {
  const r = await mount(<ReadyStrip r={{ state: 'OFFICE WARMING UP', live: false, steps: [['OFFICE WARMING UP', true], ['POSITIONS RECONCILED', false], ['MARKET REFILLED', false], ['LIVE', false]], why: '0 of 2 agent passes since the restart' }} />);
  expect(q(r, 'oed-ready').className).toContain('is-warm'); expect(q(r, 'oed-ready').textContent).toContain('0 of 2 agent passes'); expect(q(r, 'oed-ready').querySelectorAll('li.is-on').length).toBe(1);
  const s = await mount(<SeatState s={office.seat} speed={office.performance.speed} />);
  expect(q(s, 'oed-seat-why').textContent).toBe(office.seat.reason); expect(q(s, 'oed-seat').querySelector('.oed-chips').textContent).toBe(office.seat.validSyms.map(x => `$${x}`).join(''));
  expect(q(s, 'oed-blockers').querySelectorAll('li').length).toBe(office.seat.blockers.length);
  expect(q(s, 'oed-seat').textContent).toContain(`${office.performance.speed.seatEmpty.med}s`);                       // measured, never invented
  expect(q(await mount(<SeatState s={null} />), 'oed-seat').textContent).toContain('next tier tick');
  const w = await mount(<SwitchEval e={office.switchEval} />);
  expect(q(w, 'oed-switch-why').textContent).toBe(office.switchEval.why); expect(q(w, 'oed-switch').textContent).toContain('SEAT KEPT');
  expect(q(w, 'oed-lines').querySelectorAll('li').length).toBe(office.switchEval.lines.length);
  expect(q(w, 'oed-lines').querySelectorAll('li.is-no').length).toBe(office.switchEval.lines.filter(l => !l[1]).length);
  expect(q(await mount(<SwitchEval e={null} />), 'oed-switch').textContent).toContain('no held coin');
});

test('your limits: grouped, AGENTS CHOOSE vs YOUR OVERRIDE unmistakable, every button posts a real setting, the rule in force per position', async () => {
  const posts = []; const save = b => posts.push(b);
  const cfg = { agentTakePct: 10, agentSeats: 4, options: { take: [5, 10, 20, 30, 50], seats: [1, 2, 3, 4] } };
  const el = await mount(<CreatorLimits policy={office.policy} mission={office.mission} cfg={cfg} o={office} save={save} />);
  expect(LIMIT_GROUPS.map(g => g[0])).toEqual(['EXITS', 'SIZE & SEATS', 'MOVES']);
  const keys = LIMIT_GROUPS.flatMap(g => g[2]);
  expect(keys).toEqual(expect.arrayContaining(['agentTp', 'agentSl', 'agentTrail', 'agentMaxHold', 'agentSizePct', 'agentSeats', 'agentSeatTarget', 'agentSwitch', 'agentEntry']));
  for (const c of office.policy.controls) {
    const row = q(el, `oed-ctl-${c.key}`); expect(row).not.toBeNull();
    expect(row.className).toBe(c.who === 'CREATOR OVERRIDE' ? 'is-you' : 'is-agents');
    expect(row.textContent).toContain(c.who === 'CREATOR OVERRIDE' ? 'YOUR OVERRIDE' : 'AGENTS CHOOSE');
    if (c.who !== 'CREATOR OVERRIDE') expect(row.textContent).toContain(c.agentsNow);                                     // what the agents use right now, from the payload
  }
  await act(async () => { q(el, 'oed-opt-agentSl-0').click(); q(el, 'oed-opt-agentTp-20').click(); q(el, 'oed-opt-agentSeats-2').click(); q(el, 'oed-opt-agentTakePct-30').click(); q(el, 'oed-auth-manual').click(); });
  expect(posts).toEqual([{ cfg: { agentSl: 0 } }, { cfg: { agentTp: 20 } }, { cfg: { agentSeats: 2 } }, { cfg: { agentTakePct: 30 } }, { cfg: { agentAuthority: 'manual' } }]);   // no dead toggle
  expect(q(el, 'oed-hard').textContent).toContain('catastrophic stop −45%'); expect(q(el, 'oed-hard').textContent).toContain('until real equity ≥ 2× put-in');
  const pp = positionPolicy(office);
  expect(pp.length).toBe(office.positions.length); expect(pp[0].take).toBe(office.positions[0].take);
  expect(q(el, 'oed-inforce').textContent).toContain(`$${office.positions[0].symbol}`);
  const ro = await mount(<CreatorLimits policy={office.policy} cfg={cfg} o={office} isOwner={false} save={save} />);
  expect([...ro.querySelectorAll('.oed-ctl button:not(.oed-info)')].every(b => b.disabled)).toBe(true);                // not the creator: nothing can be pressed
  expect(optLabel('agentTp', 0, '%')).toBe('🤖 agents'); expect(optLabel('agentSl', 15, '%')).toBe('−15%'); expect(optLabel('agentSwitch', 'conservative')).toBe('conservative');
});

test('the review queue never blocks: categories with open counts, items with what was known, marks post as display state', async () => {
  const posts = [];
  const el = await mount(<ReviewQueue review={office.review} save={b => posts.push(b)} />);
  expect(q(el, 'oed-review').textContent).toContain('NON-BLOCKING'); expect(q(el, 'oed-review').textContent).toContain('never waits on it');
  for (const k of office.review.order) expect(q(el, `oed-cat-${k}`).textContent).toContain(office.review.labels[k]);
  const it = office.review.items.missed[0];
  expect(q(el, `oed-item-${it.key}`)).not.toBeNull();
  await act(async () => { q(el, `oed-mark-disagree-${it.key}`).click(); });
  expect(posts[0]).toEqual({ review: { key: it.key, mark: 'disagree', note: (it.mark && it.mark.note) || '' } });
  const marked = office.review.items.missed.find(x => x.mark);
  expect(q(el, `oed-item-${marked.key}`).className).toContain(`is-${marked.mark.mark}`);                               // a mark already on file shows
  await act(async () => { q(el, 'oed-cat-data').click(); });
  expect(q(el, 'oed-review-empty')).not.toBeNull();                                                                    // an empty category says so
});

test('missed winners and launch context: paper-only study with counts, counterfactuals and each context on its own record', async () => {
  const el = await mount(<MissedWinners review={office.review} />);
  const ms = office.review.missedSummary;
  expect(q(el, 'oed-missed').textContent).toContain('PAPER ONLY'); expect(q(el, 'oed-missed').textContent).toContain(`${ms.correct}`);
  expect(q(el, 'oed-missed').textContent).toContain(ms.byReason[0].key); expect(q(el, 'oed-missed').textContent).toContain('Nothing here loosens a rule');
  expect(q(el, 'oed-missed').textContent).toContain('at first clear');
  const l = await mount(<LaunchRecord launch={office.launch} />);
  for (const k of Object.keys(office.launch.record)) expect(q(l, 'oed-launch').textContent).toContain(k.replace(':', ' · '));
  expect(q(l, 'oed-launch').textContent).toContain('UNKNOWN');
  expect(q(await mount(<LaunchRecord launch={{ record: {}, pads: {} }} />), 'oed-launch').textContent).toContain('no judged call carries its launch context yet');
});

// 🩺 ops line + per-seat reasons (fixture = the backend's own office_edge.seat_state / ops output)
test('every empty seat shows its own reason code and the ops line says why the agents are or are not filling', async () => {
  const { OpsLine } = require('./OfficeEdge');
  const fx = require('./__fixtures__/seatOps.json');
  const s = await mount(<SeatState s={fx.seat} />);
  const li = q(s, 'oed-seat-list').querySelectorAll('li');
  expect(li.length).toBe(fx.seat.empty);
  expect(Array.from(li).map(x => x.querySelector('.oed-tag').textContent)).toEqual(fx.seat.seats.map(x => x.code));
  const o = await mount(<OpsLine o={fx.ops} />);
  expect(q(o, 'oed-op-office').textContent).toContain('LIVE'); expect(q(o, 'oed-op-keeper').textContent).toContain('1 active');
  expect(q(o, 'oed-op-open').textContent).toContain(String(fx.ops.openSeats)); expect(q(o, 'oed-op-exec').textContent).toContain('HEALTHY');
  expect(q(o, 'oed-op-block').textContent).toContain(fx.ops.code); expect(q(o, 'oed-op-cash').textContent).toContain('$1.29');
  expect(q(o, 'oed-op-budget').textContent).toContain(`${fx.ops.budget.left} / ${fx.ops.budget.of}`);
  expect((await mount(<OpsLine o={null} />)).textContent).toBe('');
});

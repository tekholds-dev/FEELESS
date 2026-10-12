import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { OfficeHQ, RoomScene, AgentPanel, Roster, Lineage, LiveChart, TeamTrace, traceOf, roomModel, agentTag, focusOf, ticker, hotPosition, candleGeom, coinView, PANEL_TABS, AG, TAG_CLS } from './OfficeRoom';
import { VERD, rowState } from '../../lib/agentRead';
import office from './__fixtures__/office.json';

// the live chart component itself needs a canvas; here it reports what it was handed (the same pair + levels the real one draws)
jest.mock('../../lib/liveCandles', () => ({ useLiveCandles: () => null }));   // no network in tests: the wall keeps the pass's rows
jest.mock('../terminal/PriceChart', () => ({ PriceChart: p => <div data-testid="price-chart" data-pair={p.pair.pairAddress} data-interval={p.interval} data-lines={(p.fuse?.lines || []).map(l => l.title).join('|')} /> }));

const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const CHAIN = ['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge'];

test('every desk\'s word comes from the payload: the line for the current candidate, Reaper for its most urgent position', () => {
  expect(Object.keys(AG)).toEqual(CHAIN);
  expect(focusOf(office)).toBe(office.queue[0].at);
  const [tag, word] = agentTag('reaper', office);
  expect(tag).toBe(office.positions[0].decision); expect(word).toContain(`$${office.positions[0].symbol}`);
  expect(agentTag('tally', office)[0]).toBe('PASS'); expect(agentTag('judge', office)[0]).toBe('WAIT');
  expect(agentTag('warden', { ...office, currentCase: { ...office.currentCase, warden: { veto: true, requested: 0.4, allowed: 0, decided: 'W12 chart risk' } } })).toEqual(['VETO', '$0.40 → $0.00 (W12 chart risk)']);
  expect(agentTag('tally', {})).toEqual(['WAIT', 'no candidate this pass']);
  expect(hotPosition([{ symbol: 'A', decision: 'HOLD' }, { symbol: 'B', decision: 'EXIT' }, { symbol: 'C', decision: 'PROTECT' }]).symbol).toBe('B');   // an exit outranks a hold
  expect(ticker(office)).toContain(`$${office.currentCase.symbol} at`);
  expect(ticker({ ...office, positions: [{ ...office.positions[0], decision: 'EXIT', rule: 'R5t thesis invalidated' }] })).toBe(`Reaper: EXIT $${office.positions[0].symbol} — R5t thesis invalidated`);
  expect(ticker({})).toBe('no candidate this pass');
  expect(CHAIN.every(k => TAG_CLS[agentTag(k, office)[0]])).toBe(true);
});

test('the chart draws the candles the agents read and their levels — entry, take, stop, invalidation for a position', () => {
  const v = coinView(office, office.positions[0].symbol); const p = office.positions[0];
  expect(v.kind).toBe('position'); expect(v.levels.map(l => l.label)).toEqual(expect.arrayContaining(['entry', `take +${p.take}%`, `stop ${p.stop}%`, 'invalid', 'support']));
  expect(v.levels.find(l => l.label === 'entry').px).toBe(p.entry);
  expect(v.levels.find(l => l.label.startsWith('take')).px).toBeCloseTo(p.entry * (1 + p.take / 100));
  const c = coinView(office, office.currentCase.symbol);
  expect(c.kind).toBe('case'); expect(c.levels.map(l => l.label)).toEqual(expect.arrayContaining(['support', `stop −${office.currentCase.chart.stop}%`])); expect(c.note).toContain('TRIGGER');
  expect(coinView(office, 'NOPE')).toBeNull(); expect(coinView({}, 'X')).toBeNull();
  const g = candleGeom(v.bars.rows, v.levels);
  expect(g.bars.length).toBe(v.bars.rows.length); expect(g.bars.every(b => b.h <= b.l && b.h >= 0 && b.l <= g.h)).toBe(true); expect(g.lines.some(l => l.label === 'entry')).toBe(true);
  expect(candleGeom([[0, 1, 1, 1, 1]], [])).toBeNull(); expect(candleGeom(null, [])).toBeNull();
});

test('the chart is the LIVE FEELESS chart of the coin, with the agents\' levels on it — no pool, no chart', async () => {
  const el = await mount(<LiveChart view={null} />);
  expect(q(el, 'ofr-nochart').textContent).toContain('no pool');
  const v = coinView(office, office.positions[0].symbol);
  expect(v.pair).toBe(office.positions[0].pair); expect(v.mint).toBe(office.positions[0].mint);
  const ok = await mount(<LiveChart view={v} big />);
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const pc = q(ok, 'price-chart');
  expect(pc.getAttribute('data-pair')).toBe(office.positions[0].pair); expect(pc.getAttribute('data-interval')).toBe('1m');
  expect(pc.getAttribute('data-lines').split('|')).toEqual(expect.arrayContaining(['entry', `take +${office.positions[0].take}%`, `stop ${office.positions[0].stop}%`]));
  expect(q(ok, 'ofr-chart').textContent).toContain('LIVE · the FEELESS chart'); expect(q(ok, 'ofr-warroom')).not.toBeNull();
});

test('the room: ten stations in chain order, the candidate on the wall, the pass\'s case files, the live ticker', async () => {
  const picks = []; const coins = [];
  const el = await mount(<RoomScene o={office} sel="reaper" onSel={k => picks.push(k)} coin={null} onCoin={s => coins.push(s)} />);
  expect([...el.querySelectorAll('.ofr-desk button')].map(b => b.getAttribute('data-testid'))).toEqual(CHAIN.map(k => `desk-${k}`));
  expect(q(el, 'desk-reaper').textContent).toContain(office.positions[0].decision); expect(q(el, 'desk-reaper').getAttribute('aria-pressed')).toBe('true');
  expect(el.querySelector('.ofr-desk.is-focus button').getAttribute('data-testid')).toBe(`desk-${focusOf(office)}`);
  expect(q(el, 'ofr-screen').textContent).toContain(`$${office.currentCase.symbol}`); expect(q(el, 'ofr-screen').textContent).toContain(office.currentCase.chart.state);
  expect(q(el, 'ofr-status').textContent).toContain(`${office.office.cleared}cleared`); expect(q(el, 'ofr-status').textContent).toContain(office.execution.health);
  expect(q(el, 'ofr-queue').querySelectorAll('button').length).toBe(office.queue.length);
  expect(q(el, 'ofr-ticker').textContent).toBe(ticker(office));
  await act(async () => { q(el, 'desk-devil').click(); q(el, `case-${office.queue[1].symbol}`).click(); });
  expect(picks).toEqual(['devil', office.queue[1].at]); expect(coins).toEqual([office.queue[1].symbol]);
});

test('the live panel: decision, lines, the chart with its coin picker, chart intelligence, rulings, files — and four more tabs of real state', async () => {
  const a = office.agents.find(x => x.key === 'reaper'); const p = office.positions[0]; let coin = null;
  const el = await mount(<AgentPanel o={office} a={a} coin={null} onCoin={s => { coin = s; }} />);
  expect(PANEL_TABS.map(t => t[1])).toEqual(['Live decision', '🪑 Seats', 'Beliefs & ethics', 'Current inputs', 'Chart intel', 'Source code']);
  const live = q(el, 'pane-live').textContent;
  for (const w of ['CURRENT DECISION', 'RECORD', 'TAKE / STOP', 'RISK', 'POSITION SIZE', 'CHART INTELLIGENCE', 'LIVE RULINGS', 'RUNTIME last']) expect(live).toContain(w);
  expect(live).toContain(`+${p.take}% / ${p.stop}%`); expect(live).toContain(`${p.takeSource} take`);                    // Reaper opens on ITS position
  expect(q(el, 'ofr-intel').textContent).toContain(p.structure); expect(q(el, 'ofr-intel').textContent).toContain('Reaper next review'); expect(q(el, 'ofr-intel').textContent).toContain(p.thesis.triggerRule);
  expect(q(el, 'ofr-review').textContent).toContain('next review'); expect(q(el, 'ofr-chart')).not.toBeNull();
  expect(q(el, 'ofr-files').textContent).toContain('backend/office.py'); expect(q(el, 'ofr-files').textContent).toContain('reap()');
  await act(async () => { q(el, `coin-${office.currentCase.symbol}`).click(); });
  expect(coin).toBe(office.currentCase.symbol);
  await act(async () => { q(el, 'ptab-beliefs').click(); });
  expect(q(el, 'pane-live')).toBeNull(); expect(q(el, 'pane-beliefs').textContent).toContain('Never hold because of hope.'); expect(q(el, 'pane-beliefs').textContent).toContain('stopPct');
  await act(async () => { q(el, 'ptab-inputs').click(); });
  expect(q(el, 'pane-inputs').textContent).toContain('CURRENT OUTPUT'); expect(q(el, 'pane-inputs').textContent).toContain('takeLine');
  await act(async () => { q(el, 'ptab-chart').click(); });
  expect(q(el, 'pane-chart').textContent).toContain('ENTRY THESIS'); expect(q(el, 'pane-chart').textContent).toContain(p.thesis.structure);
  await act(async () => { q(el, 'ptab-code').click(); });
  expect(q(el, 'pane-code').textContent).toContain('backend/chart_intel.py'); expect(q(el, 'pane-code').textContent).toContain('review()'); expect(q(el, 'pane-code').textContent).toContain('p95');
  const tr = await mount(<AgentPanel o={office} a={office.agents.find(x => x.key === 'trigger')} coin={null} onCoin={() => {}} />);
  expect(q(tr, 'ofr-intel').textContent).toContain(office.currentCase.chart.entry[0]);                                    // Trigger opens on the candidate: its entry call
  await act(async () => { q(tr, 'ptab-chart').click(); });
  expect(q(tr, 'pane-chart').querySelector('[data-testid="ofb-chart"]')).not.toBeNull();
});

test('the roster: ten live cards with gen, status, runtime line, record and the action word; the whole office in one section', async () => {
  const picks = [];
  const r = await mount(<Roster o={office} sel="tally" onSel={k => picks.push(k)} />);
  expect([...r.querySelectorAll('.ofr-rcard')].map(b => b.getAttribute('data-testid'))).toEqual(CHAIN.map(k => `roster-${k}`));
  expect(q(r, 'ofr-roster').textContent).toContain('/ 10 ACTIVE'); expect(q(r, 'roster-reaper').textContent).toContain(office.positions[0].decision);
  expect(q(r, 'roster-tally').textContent).toContain('GEN 1 · ● ACTIVE'); expect(q(r, 'roster-tally').querySelector('polyline')).not.toBeNull();
  await act(async () => { q(r, 'roster-warden').click(); });
  expect(picks).toEqual(['warden']);
  const el = await mount(<OfficeHQ o={office} roomOn />);
  expect(q(el, 'ofr-room')).not.toBeNull(); expect(q(el, 'ofr-panel').textContent).toContain(office.agents.find(a => a.key === focusOf(office)).name.toUpperCase());   // opens on the desk the candidate stands at
  await act(async () => { q(el, 'roster-devil').click(); });
  expect(q(el, 'ofr-panel').textContent).toContain('DEVIL'); expect(q(el, 'desk-devil').getAttribute('aria-pressed')).toBe('true');
  const flat = await mount(<OfficeHQ o={office} roomOn={false} />);
  expect(q(flat, 'ofr-room')).toBeNull(); expect(q(flat, 'ofr-panel')).not.toBeNull(); expect(q(flat, 'ofr-roster')).not.toBeNull();
  const cold = await mount(<OfficeHQ o={{ cold: true }} />);
  expect(q(cold, 'office-hq').textContent).toContain('waiting for the agents');
});

test('the 3D room is handed real state only: ten stations, the candidate on the wall with its candles, each desk\'s own line', () => {
  const { roomModel, deskLine, rulingsOf, hhmm, CAMS } = require('./OfficeRoom');
  const m = roomModel(office, 'reaper', null);
  expect(m.stations.map(s => s.key)).toEqual(CHAIN); expect(m.stations.filter(s => s.focus).map(s => s.key)).toEqual([focusOf(office)]); expect(m.stations.find(s => s.key === 'reaper').selected).toBe(true);
  expect(m.stations.every(s => s.tag === agentTag(s.key, office)[0] && s.line === deskLine(s.key, office) && TAG_CLS[s.tag] === s.cls)).toBe(true);   // every station = the payload's own word
  expect(m.wall.symbol).toBe(office.currentCase.symbol); expect(m.wall.structure).toBe(office.currentCase.chart.state); expect(m.wall.decision).toBe(VERD[rowState({ k: office.currentCase })]);   // the kernel's decision — the same word the board shows
  expect(m.wall.bars).toBe(office.currentCase.bars); expect(m.wall.stage).toBe(office.agents.find(a => a.key === focusOf(office)).name);                  // the SAME candle rows, not a copy or a sketch
  expect(m.wall.devil).toMatch(/NO OBJECTION|DEVIL WARNS|BLOCKED/); expect(m.wall.devil).not.toMatch(/OBJECTED/); expect(m.status.find(x => x[1] === 'ready')).toEqual([office.office.cleared, 'ready', '#45e486']);
  const p = office.positions[0]; const w = roomModel(office, 'reaper', p.symbol).wall;
  expect(w.kind).toBe('position'); expect(w.decision).toBe(p.decision); expect(w.stage).toBe('Reaper'); expect(w.levels.map(l => l.label)).toEqual(expect.arrayContaining(['entry', 'invalid', 'support'])); expect(w.reviewAt).not.toBeNull();
  expect(roomModel({ agents: office.agents, pipeline: [] }, null, null).wall).toBeNull();                                                              // no candidate, no position → an empty wall, never a made-up coin
  expect(deskLine('tally', office)).toContain(`${office.office.coins} coins read`); expect(deskLine('courier', office)).toContain(office.execution.health);
  expect(deskLine('weather', office)).toContain(office.agents.find(a => a.key === 'weather').output.regime); expect(deskLine('reaper', office)).toContain(`$${p.symbol}`);
  expect(deskLine('trigger', {})).toBe('no candidate'); expect(deskLine('reaper', {})).toBe('no open position');
  const r = rulingsOf(office, 8);
  expect(r.length).toBeGreaterThan(0); expect(r.every(x => CHAIN.includes(x.key) && x.text && x.at)).toBe(true);
  expect(r.every(x => { const a = office.agents.find(y => y.key === x.key); return a.decision === x.text || (a.recent || []).some(z => z.text === x.text); })).toBe(true);   // every line is a recorded decision of that desk
  expect(rulingsOf({}, 8)).toEqual([]); expect(hhmm(0)).toMatch(/^\d\d:\d\d$/); expect(CAMS.map(c => c[0])).toEqual(['main', 'card', 'top', 'focus']);
  const far = candleGeom(p.bars.rows, [{ px: p.entry * 3, label: 'take +200%', cls: 'is-take' }, { px: p.entry * 0.2, label: 'stop', cls: 'is-stop' }]);
  expect(far.lines).toEqual([]); expect(far.off.map(l => [l.label, l.up])).toEqual([['take +200%', true], ['stop', false]]);                             // a far level is named at the edge, the candles keep their scale
  expect(far.hi).toBe(Math.max(...p.bars.rows.map(x => x[2])));
});

test('the office: room above the roster, a station pick drives the panel, and the camera controls only exist with a real 3D room', async () => {
  const el = await mount(<OfficeHQ o={office} roomOn gl={false} />);
  const kids = [...q(el, 'office-hq').children].map(n => n.className);
  expect(kids.findIndex(c => c.includes('ofr-main'))).toBeLessThan(kids.findIndex(c => c.includes('ofr-roster')));
  expect(q(el, 'ofr-stage')).not.toBeNull(); expect(q(el, 'cam-main')).toBeNull(); expect(q(el, 'cam-rotate')).toBeNull();                              // no GPU → no camera buttons that would do nothing
  await act(async () => { q(el, 'desk-courier').click(); });
  expect(q(el, 'ofr-panel').textContent).toContain('COURIER'); expect(q(el, 'roster-courier').getAttribute('aria-pressed')).toBe('true');
  await act(async () => { q(el, 'roster-judge').click(); });
  expect(q(el, 'ofr-panel').textContent).toContain('JUDGE'); expect(q(el, 'desk-judge').getAttribute('aria-pressed')).toBe('true');
  expect(q(el, 'ofr-rulings').querySelectorAll('li').length).toBeGreaterThan(0);
});

test('volume bars exist only where a bar carries its own measured figure, and a tape is drawn as a labelled reconstruction', async () => {
  const rows = office.currentCase.bars.rows;
  const full = candleGeom(rows, []);
  expect(full.vols).toHaveLength(rows.filter(r => r[5] > 0).length);                        // one volume bar per MEASURED figure
  const some = rows.map((r, i) => [...r.slice(0, 5), i < 4 ? r[5] : null]);
  expect(candleGeom(some, []).vols).toHaveLength(4);                                        // 4 figures → 4 bars: nothing is filled in for the rest
  expect(candleGeom(rows.map(r => [...r.slice(0, 5), null]), []).vols).toEqual([]);         // no figure at all → no volume bars at all
});

test('the team trace: each desk answers its own question for the candidate, then FINAL and WHY — all from the payload', async () => {
  const t = traceOf(office, office.currentCase.symbol);
  expect(t.lines.map(l => l[0])).toEqual(['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper']);
  expect(t.lines[0][1]).toMatch(/^DATA [A-Z ]+ \d+%$/);                                     // Tally's data confidence leads the trace
  const el = await mount(<TeamTrace t={t} />);
  t.lines.forEach(l => expect(q(el, 'ofr-trace').textContent).toContain(l[1]));
  expect(q(el, 'ofr-final').textContent).toContain(t.final);
  expect(q(el, 'ofr-final').textContent).toContain(t.why);
  office.queue.forEach(x => { expect(x.trace.final).toBeTruthy(); expect(x.data.state).toBeTruthy(); });   // every candidate of the pass has one, with its data state
  const waiting = office.queue.find(x => x.data.state !== 'TRUSTED');
  expect(waiting.trace.final).not.toBe('GO');                                               // not ENTER-grade data never ends in GO
  const panel = await mount(<AgentPanel o={office} a={office.agents[0]} coin={office.currentCase.symbol} onCoin={() => {}} />);
  expect(q(panel, 'ofr-trace')).not.toBeNull();
  await act(async () => { q(panel, 'ptab-beliefs').click(); });
  expect(q(panel, 'ofr-job').textContent).toContain('MARKET TRUTH');                        // each desk's own job
  expect(q(panel, 'pane-beliefs').textContent).toContain('Never certify market data merely because it rendered successfully.');
  await act(async () => { q(panel, 'ptab-inputs').click(); });
  expect(q(panel, 'ofr-contrib').textContent).toContain('data errors caught');
  expect(new Set(office.agents.map(a => a.job)).size).toBe(10);
});

test('the room reacts to each desk\'s REAL activity word and draws the card, the cases, the switch test and who decides', () => {
  const { activityOf, roomModel, seatsOf, policyRows, ACT_FX } = require('./OfficeRoom');
  expect(activityOf('tally', office)).toEqual(['SCAN', `${office.office.coins} coins read this pass`]);
  expect(activityOf('archivist', office)[0]).toBe('LOGGING'); expect(activityOf('courier', office)[0]).toBe('CONFIRMED');   // the last real action is confirmed on the ledger
  expect(activityOf('courier', { ...office, execution: { ...office.execution, pending: { side: 'buy', sym: 'X' } } })).toEqual(['SUBMITTED', 'buy $X in flight']);
  expect(activityOf('courier', { ...office, execution: { health: 'BAD', why: 'stuck' }, mission: {} })[0]).toBe('VETO');
  expect(activityOf('reaper', office)[0]).toBe('HOLD'); expect(activityOf('reaper', { ...office, positions: [{ ...office.positions[0], decision: 'EXIT' }] })[0]).toBe('EXIT');
  expect(activityOf('judge', { ...office, judge: { rulings: 4 } })[0]).toBe('JUDGE REVIEW'); expect(activityOf('judge', { pipeline: [] })[0]).toBe('WAIT');
  expect(activityOf('warden', { ...office, currentCase: { ...office.currentCase, warden: { veto: false, requested: 0.4, allowed: 0.2, decided: 'W2' } } })[0]).toBe('SIZED');
  const m = roomModel(office, 'reaper', null, null);
  expect(m.stations.every(s => s.act && ACT_FX[s.act] && s.actWhy && s.color)).toBe(true);
  expect(m.cases.length).toBe(Math.min(6, office.queue.length)); expect(m.cases[0].current).toBe(true); expect(m.cases.every(c => c.at && c.symbol)).toBe(true);
  expect(m.ready.live).toBe(true); expect(m.swap.from).toBe(office.switchEval.current.symbol); expect(m.limits.rows.length).toBe(office.policy.controls.length);
  expect(m.missed.n).toBe(office.review.missedSummary.n); expect(m.wall.facts.length).toBeGreaterThan(0);
  const seats = seatsOf(office, { seats: [{ kind: 'agent', symbol: office.positions[0].symbol, pct: 2.5 }, { kind: 'open' }] }, office.positions[0].symbol);
  expect(seats[0]).toMatchObject({ kind: 'agent', pct: 2.5, decision: office.positions[0].decision, selected: true });
  expect(seats.length).toBe(office.seat.want); expect(seats.slice(1).every(x => x.kind === 'open' && x.decision === office.seat.state)).toBe(true);   // open seats carry the seat state
  const rows = policyRows(office, office.positions[0]);
  expect(rows.map(r => r[0])).toEqual(['Take profit', 'Stop-loss', 'Max hold', 'Trailing', 'Seat size', 'Switching']);
  expect(rows[1][1]).toBe('−15%'); expect(rows[0][3]).toContain(`+${office.positions[0].take}%`);                          // your stop vs the take in force
});

test('the panel shows your limit vs the agents vs the rule in force, the launch context, and the room\'s flow overlay', async () => {
  const p = office.positions[0];
  const el = await mount(<AgentPanel o={office} a={office.agents.find(x => x.key === 'reaper')} coin={p.symbol} onCoin={() => {}} />);
  expect(q(el, 'ofr-policy').textContent).toContain('YOU'); expect(q(el, 'ofr-policy').textContent).toContain('IN FORCE'); expect(q(el, 'ofr-policy').textContent).toContain('−15%');
  expect(q(el, 'ofr-launch').textContent).toContain(p.launch.pad); expect(q(el, 'ofr-launch').textContent).toContain('UNKNOWN');
  expect(q(el, 'ptab-live').getBoundingClientRect).toBeDefined();
  const hq = await mount(<OfficeHQ o={office} roomOn gl={false} card={{ seats: [{ kind: 'open' }] }} onEdge={() => {}} />);
  expect(q(hq, 'oed-band')).not.toBeNull(); expect(q(hq, 'ofr-cardrow').textContent).toContain('THE REAL CARD');
  expect(q(hq, 'ofr-cardrow').querySelectorAll('.ofr-seat').length).toBe(office.seat.want);
});

test('the roster shows each desk\'s REAL-money record — never a sum of % (Reaper read "−468%" = 158 exits added up)', async () => {
  const o2 = { ...office, agents: (office.agents || []).map(a => a.key === 'reaper' ? { ...a, card: { ...(a.card || {}), n: 158, profit: 257, loss: -725.6 } } : a),
    deskStats: { reaper: { decisions: 80, winResp: 25, lossResp: 3, accuracy: 38, medNet: -0.86 } } };
  const r = await mount(<Roster o={o2} sel="tally" onSel={() => {}} />);
  const el = q(r, 'roster-net-reaper');
  expect(el.textContent).toContain('med'); expect(el.textContent).not.toContain('468');
  expect(el.getAttribute('data-tip')).toContain('3 losses the Judge pinned');
  expect(q(r, 'roster-reaper').textContent).toContain('real 80 · W25 · L3'); expect(q(r, 'roster-reaper').textContent).toContain('38%');
});

test('a replaced generation is shown as SHADOW / RETIRED under the ACTIVE one, with why, what changed and the shadow record', async () => {
  const o2 = { ...office, generations: office.generations.map(g => (g.role === 'reaper' ? { ...g, generation: 2, status: 'ACTIVE', lineage: [{ gen: 1, status: 'SHADOW', at: 5, why: 'real money: 4 losses pinned vs 1 win', changed: 'arms its trail at +4%',
    shadow: { n: 8, old: -3.1, new: -0.4, edge: 2.7, verdict: 'new generation better' } }] } : g)) };
  const r = await mount(<Roster o={o2} sel="tally" onSel={() => {}} />);
  expect(q(r, 'roster-status-reaper').textContent).toContain('ACTIVE'); expect(q(r, 'roster-reaper').textContent).toContain('GEN 2');
  const t = q(r, 'lineage-reaper-1').textContent;
  expect(t).toContain('REAPER GEN 2 · ACTIVE'); expect(t).toContain('old gen 1 · SHADOW'); expect(t).toContain('arms its trail at +4%'); expect(t).toContain('new generation better');
});

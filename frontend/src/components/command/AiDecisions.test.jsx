import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AiPane } from './AiDecisions';
import { ChartPnl } from '../terminal/ChartPnl';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../ShareGif', () => ({ ShareGifButton: () => null }));
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const AI = { active: 'local', model: 'qwen', providers: [{ key: 'local', label: 'LOCAL LM STUDIO', enabled: true, state: 'ONLINE', lastMs: 900 }], totals: { answered: 2, cached: 1 }, lastAt: Date.now() / 1000 - 5,
  log: [{ at: 10, role: 'devil', mint: 'A', symbol: 'AAA', label: 'LOCAL AI', ms: 900, stance: 'WAIT', delta: -0.2, summary: 'fake breakout warning', kernel: 'CONTENDING', trigger: 'ARM' },
    { at: 20, role: 'sherlock', mint: 'B', symbol: 'BBB', label: 'LOCAL AI', ms: 1200, stance: 'AVOID', delta: -0.25, summary: 'bundled launch', kernel: 'READY' }] };

test("the model's decisions are listed newest first beside the kernel's own word, and the owner can ask about a coin", async () => {
  const call = jest.fn(async () => ({ ok: true, symbol: 'AAA', answer: { label: 'LOCAL AI', advice: { stance: 'WATCH', summary: 'thin evidence' } }, ai: AI })); const picked = [];
  const el = await mount(<AiPane ai={AI} call={call} focus="A" focusSym="AAA" onPick={m => picked.push(m)} onProviders={() => {}} />);
  const rows = [...q(el, 'cai-log').querySelectorAll('.cai-row')];
  expect(rows).toHaveLength(2); expect(rows[0].textContent).toContain('$BBB'); expect(rows[0].textContent).toContain('AVOID'); expect(rows[0].textContent).toContain('DISAGREES');
  expect(rows[1].textContent).toContain('fake breakout warning'); expect(rows[1].textContent).toContain('AGREES');
  await act(async () => { rows[0].querySelector('button').click(); }); expect(picked).toEqual(['B']);
  await act(async () => { q(el, 'cai-scope-coin').click(); }); expect(q(el, 'cai-log').querySelectorAll('.cai-row')).toHaveLength(1);
  expect(q(el, 'cai-ask-input').value).toBe('A');   // the ask box follows the coin on the chart
  await act(async () => { q(el, 'cai-role-devil').click(); }); await act(async () => { q(el, 'cai-ask-go').click(); });
  expect(call).toHaveBeenCalledWith('/admin/ai/ask', expect.objectContaining({ method: 'POST', body: JSON.stringify({ input: 'A', role: 'devil' }) }));
  expect(q(el, 'cai-answer').textContent).toContain('thin evidence');
});

test('no model online says so (and never pretends a decision)', async () => {
  const el = await mount(<AiPane ai={{ providers: [], log: [] }} call={jest.fn()} focus={null} />);
  expect(el.textContent).toContain('NO MODEL ONLINE'); expect(q(el, 'cai-empty')).not.toBeNull(); expect(q(el, 'cai-ask-go').disabled).toBe(true);
});

test('a chart draws the P&L ticker itself: a seat position handed in, nothing when switched off or flat', async () => {
  const pair = { chainId: 'solana', pairAddress: 'P', baseToken: { address: 'Mpump', symbol: 'AAA' }, priceUsd: '0.00002' };
  const el = await mount(<ChartPnl pair={pair} price={0.00003} pnl={{ label: 'SEAT', pos: { tokensHeld: 1000, avgEntry: 0.00002, investedPoolUsd: 0.02 } }} />);
  const b = q(el, 'my-pnl'); expect(b).not.toBeNull(); expect(b.textContent).toContain('SEAT'); expect(b.textContent).toContain('+50');
  expect(q(await mount(<ChartPnl pair={pair} price={0.00003} pnl={false} />), 'my-pnl')).toBeNull();
  expect(q(await mount(<ChartPnl pair={pair} price={0.00003} />), 'my-pnl')).toBeNull();   // no wallet connected: nothing to show
});

test('the live trade strip on the cockpit chart: where now sits between the stop and the take', () => {
  const { tradeBar } = require('../../lib/cockpitControls');
  const b = tradeBar({ entry: 1, stop: 20, take: 40 }, 1.1);
  expect(Math.round(b.pct)).toBe(10); expect(b.lo).toBe(-20); expect(b.hi).toBe(40); expect(b.at).toBeCloseTo(0.5); expect(b.zero).toBeCloseTo(1 / 3);
  expect(tradeBar({ entry: 1, stop: 20, take: 40 }, 5).at).toBeGreaterThan(0.99); expect(tradeBar({ entry: 1, stop: 20, take: 40 }, 0.1).at).toBeLessThan(0.02);   // the bar widens: now is always on it
  const r = tradeBar({ entry: 1, stop: 15, take: 50, mfe: 22, mae: -4, trailAt: 11, armAt: 6 }, 1.12);
  expect(r.peak).toBe(22); expect(r.low).toBe(-4); expect(r.trail).toBe(11); expect(r.giveBack).toBeCloseTo(10); expect(r.toTake).toBeCloseTo(38);
  expect(r.peakAt).toBeGreaterThan(r.at); expect(r.trailAt).toBeLessThan(r.at); expect(r.stopAt).toBeLessThan(r.zero);
  expect(tradeBar({ entry: 0 }, 1)).toBeNull(); expect(tradeBar({ entry: 1 }, 1.2).hasStop).toBe(false);
});

test("🧠 the model's trench intel: narrative, creator, conflict and risk flags on every answer; the queue cell; the live router counters", async () => {
  const { AiIntel, AiCell } = require('./AiDecisions');
  const a = { stance: 'CAUTION', summary: 'cat meta copy, dev fresh', risk_flags: ['site shows a different mint', 'top10 41%'], narrative: 'cat meta — third copy today', creator_context: 'fresh dev, 1 launch', conflict_resolution: null };
  const el = await mount(<AiIntel a={a} testid="v" />);
  expect(q(el, 'v').querySelectorAll('.avt-intel li')).toHaveLength(2); expect(q(el, 'v').textContent).toContain('NARRATIVE'); expect(q(el, 'v').textContent).toContain('fresh dev');
  expect(q(el, 'v').querySelectorAll('.avt-flag.is-risk')).toHaveLength(2); expect(q(el, 'v').textContent).toContain('cat meta copy');
  expect((await mount(<AiIntel a={{ stance: 'NEUTRAL' }} testid="none" />)).querySelector('[data-testid="none"]')).toBeNull();   // nothing said = nothing drawn
  expect((await mount(<AiIntel a={{ stance: 'NEUTRAL', summary: 'x' }} mini testid="m" />)).querySelector('[data-testid="m"]')).toBeNull();   // a log row prints the summary itself
  const cell = await mount(<AiCell a={a} />);
  expect(cell.textContent).toContain('CAUTION'); expect(cell.querySelector('.avt-rugs').textContent).toBe('🚩2');
  expect((await mount(<AiCell a={null} />)).textContent).toBe('—');
  const learn = { state: 'LEARNING', why: 'x', open: 0, minN: 20, judgeMin: 15, rows: [], vitals: [{ bucket: 'FLAGS:2+', label: '2+ risk flags', n: 12, med: -40, up: 8, factor: 1, proven: false }, { bucket: 'FLAGS:0', label: 'no risk flag', n: 0, med: null, up: null, factor: 1 }] };
  const metrics = { queue: 2, active: 1, callsPerMin: 3, cacheHitPct: 61, avgMs: 4200, provider: 'local', deferred: 5, skipped: 9 };
  const pane = await mount(<AiPane ai={{ ...AI, learn, metrics, log: [{ at: 5, role: 'sherlock', mint: 'A', symbol: 'A', stance: 'CAUTION', summary: 's', narrative: 'dog meta', risk_flags: ['dev selling'] }] }} call={jest.fn()} focus="A" />);
  expect(q(pane, 'cai-learn-vitals').textContent).toContain('2+ risk flags'); expect(q(pane, 'cai-learn-vitals').textContent).not.toContain('no risk flag');   // only judged buckets
  expect(q(pane, 'cai-log').textContent).toContain('dog meta'); expect(q(pane, 'cai-log').textContent).toContain('dev selling');
  const m = q(pane, 'cai-metrics').textContent;
  ['QUEUE2', 'ACTIVE1', 'CALLS / MIN3', 'CACHE HIT61%', 'AVG LATENCY4.2s', 'PROVIDERLOCAL', '5 · 9'].forEach(x => expect(m).toContain(x));
});

test("the model's record is on the page: what the agents learned from it, and whether it is used yet", async () => {
  const learn = { state: 'LEARNING', why: '6 of 20 judged calls — the model is shown, not used', open: 3, minN: 20, judgeMin: 15, rows: [{ stance: 'AVOID', n: 6, med: -8.2, up: 17, factor: 1, proven: false }] };
  const el = await mount(<AiPane ai={{ ...AI, learn }} call={jest.fn()} focus="A" />);
  expect(q(el, 'cai-learn').textContent).toContain('LEARNING'); expect(q(el, 'cai-learn').textContent).toContain('6 judged'); expect(q(el, 'cai-learn').textContent).toContain('3 calls waiting');
  const used = await mount(<AiPane ai={{ ...AI, learn: { ...learn, state: 'IN USE', rows: [{ stance: 'AVOID', n: 25, med: -12, up: 20, factor: 0.9, proven: true }] } }} call={jest.fn()} focus="A" />);
  expect(q(used, 'cai-learn').textContent).toContain('rank ×0.9');
});

test('the live pulse reads only real clocks and the kernel\'s own counters', () => {
  const { pulseOf } = require('./AgentCockpit');
  const o = { cycle: { at: 100, nextIn: 18 }, kernel: { metrics: { mints: 122, rejudged: 394, eventsPerSec: 1.5, uniqueMintsPerMin: 22, latencyMs: { agents: { p50: 0.016 }, priceToReaper: { p50: 0.064 } }, byStatus: { TRACKING: 112, CONTENDING: 8, READY: 2 } } },
    tape: [{ at: 90, agent: 'tally', action: 'SCAN' }, { at: 104, agent: 'trigger', action: 'ARM', symbol: 'AAA' }], ai: { log: [{ at: 95, stance: 'WAIT', symbol: 'BBB' }] } };
  const p = pulseOf(o, 109000);
  expect(p.passAge).toBe(9); expect(p.fill).toBe(0.5); expect(p.late).toBe(false); expect(p.mints).toBe(122); expect(p.brainMs).toBeCloseTo(16); expect(p.wakeMs).toBeCloseTo(64);
  expect([p.tracking, p.contending, p.ready, p.held]).toEqual([112, 8, 2, 0]); expect(p.last).toMatchObject({ age: 5, agent: 'trigger', action: 'ARM', symbol: 'AAA' }); expect(p.ai).toMatchObject({ age: 14, stance: 'WAIT' });
  expect(pulseOf(o, 160000).late).toBe(true);                       // a pass that is overdue is said so
  expect(pulseOf(null).passAge).toBeNull(); expect(pulseOf({}).last).toBeNull();
});

test('🧪 the rule lab shows each rule with its unseen record and what each desk learned', async () => {
  const lab = { trades: 41, lessons: { trigger: ['🚫 top tick'] }, said: { summary: 'losers were bought at the top' },
    rules: [{ id: 'avoid:high:top', act: 'avoid', when: ['high:top'], name: 'top tick', desk: 'trigger', status: 'live', door: 'walk-forward', test: { n: 7, avg: -11.2, rest: -2.4 } },
      { id: 'avoid:cls:BUNDLED', act: 'avoid', when: ['cls:BUNDLED'], name: 'bundled', desk: 'devil', status: 'proposed', lossHits: 2 }] };
  const el = await mount(<AiPane ai={AI} lab={lab} call={jest.fn()} focus="A" />);
  const t = q(el, 'cai-lab').textContent;
  ['RULE LAB', '41 real trades', '1 live', 'top tick', 'unseen 7: -11.2% vs -2.4%', 'TESTING', '2 recent real losses fit it'].forEach(x => expect(t).toContain(x));
  expect(q(el, 'cai-lessons').textContent).toContain('trigger');
});

test('🧭 a general question comes back in normal language — no stance chip, no trench schema', async () => {
  const call = jest.fn(async () => ({ ok: true, mode: 'general', answer: { label: 'OPENROUTER', text: 'The cloud model does the reading; the local 7B is the backup.' }, ai: AI }));
  const el = await mount(<AiPane ai={AI} call={call} focus="A" focusSym="AAA" onPick={() => {}} onProviders={() => {}} />);
  await act(async () => { q(el, 'cai-ask-go').click(); });
  expect(q(el, 'cai-general').textContent).toBe('The cloud model does the reading; the local 7B is the backup.');
  expect(q(el, 'cai-answer').querySelector('.cai-stance')).toBeNull();
  expect(q(el, 'cai-ask-input').placeholder).toMatch(/or any question/);
});

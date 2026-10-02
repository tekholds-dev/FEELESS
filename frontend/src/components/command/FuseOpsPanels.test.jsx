import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ArenaOps, ContractStatus } from './FuseOpsPanels';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };

test('Arena ops: stage mix, live battles with the leader marked, season board vs FeeCat', async () => {
  const ARENA = { mega: [{ kind: 'auto' }, { kind: 'user' }, { kind: 'user' }], battles: { endsAt: Date.now() / 1000 + 600, pairs: [{ a: { key: 'a', name: 'Alpha', now: 4.2 }, b: { key: 'b', name: 'Beta', now: -1 } }],
    log: [{ a: 'Alpha', b: 'Beta', winner: 'Alpha', aMove: 3, bMove: 1 }] } };
  const SEASON = { cards: 7, endsAt: Date.now() / 1000 + 86400, feecat: { pct: 2.5, winPts: 8 }, board: [{ id: 'c', rank: 1, name: 'Moon', handle: '@x', pnlPct: 12, beatsCat: true }], past: [] };
  global.fetch = jest.fn(async url => ({ json: async () => (String(url).includes('season') ? SEASON : ARENA) }));
  const el = await mount(<ArenaOps />);
  expect(el.textContent).toContain('👤 Trader 2'); expect(el.querySelector('.fops-fight .lead').textContent).toContain('Alpha');
  expect(el.textContent).toContain('🏆 Alpha beat Beta'); expect(el.textContent).toContain('🐱 beat FeeCat');
});

test('Contract status never claims deployment and lists what is still blocked', async () => {
  const el = await mount(<ContractStatus />);
  expect(el.textContent).toContain('LOCALNET ONLY · NOT AUDITED · NOT DEPLOYED');
  expect(el.querySelectorAll('.fops-steps li.ok').length).toBeGreaterThan(0); expect(el.textContent).toContain('Audited venue adapter');
});

test('FeeCat tunes the engine in one click: best proven dial + stronger settings', async () => {
  const { FeeCatTune, bestDial } = require('./FuseOpsPanels');
  const dials = { safe: { rounds: 30, avgPct: -3.8, winRate: 40 }, balanced: { rounds: 30, avgPct: 1.3, winRate: 52 }, degen: { rounds: 30, avgPct: 18.3, winRate: 55 } };
  expect(bestDial(dials)[0]).toBe('degen'); expect(bestDial({ degen: { rounds: 3, avgPct: 50 } })).toBe(null);
  global.fetch = jest.fn(async () => ({ json: async () => ({ dials, engineDial: 'balanced' }) }));
  const call = jest.fn(async (p, o) => (o ? {} : { suggestions: [{ key: 'minBuyShare', now: 50, to: 55, why: 'fewer dumps' }] }));
  const el = document.createElement('div'); document.body.appendChild(el);
  const { createRoot } = require('react-dom/client'); const { act } = require('react');
  await act(async () => { createRoot(el).render(<FeeCatTune call={call} />); });
  expect(el.textContent).toContain('degen'); expect(el.textContent).toContain('+18.3% avg');
  await act(async () => { el.querySelector('[data-testid="feecat-tune-go"]').click(); });
  const posts = call.mock.calls.filter(c => c[1]).map(c => JSON.parse(c[1].body));
  expect(posts).toEqual([{ dial: 'degen' }, { cfg: { minBuyShare: 55 } }]);
});

test('engine playground: scenario counts, ready-for-Arena list with evidence, dials across windows', async () => {
  const { EnginePlayground } = require('./FuseOpsPanels');
  const call = jest.fn(async () => ({ counts: { arenaRuns: 42, settled: 30, open: 12, bloodline: 5, dialScenarios: 540, runnerRounds: 60, litCards: 4, tierCards: 5, published: 2 },
    ready: [{ kind: 'dial', name: 'degen', why: '6h +3.0% · 24h +2.3%' }], proving: [{ kind: 'strategy', name: 'steady', why: 'needs 2 more runs' }],
    dials: { '6h': { degen: { rounds: 10, avgPct: 3 } }, '24h': { degen: { rounds: 60, avgPct: 2.3 } } }, board: [], autoLog: [], engineDial: 'degen', autoTune: true }));
  const { createRoot } = require('react-dom/client'); const { act } = require('react');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<EnginePlayground call={call} />); });
  expect(el.textContent).toContain('540'); expect(el.textContent).toContain('Ready for the Arena'); expect(el.textContent).toContain('6h +3.0%');
  expect(el.textContent).toContain('needs 2 more runs'); expect(el.textContent).toContain('+2.3% · 60r');
});

test('playground battles: live pairs with swaps + records, controls post to Cmd Ctr, winners publishable', async () => {
  const { PlaygroundBattles } = require('./FuseOpsPanels');
  const side = (id, name, pct) => ({ id, name, pct, legs: [{ symbol: 'SOL', role: 'anchor' }, { symbol: 'A', role: 'runner' }], swaps: [{ why: 'dead', out: 'OLD', in: 'A' }], record: { w: 2, l: 1, d: 0 } });
  const view = { cfg: { on: true, roundMins: 5, cards: 2, swapOnTp: true, swapOnSl: true, swapDead: true, deadMins: 10 }, endsAt: Date.now() / 1000 + 120,
    pairs: [{ a: side('s1', '🚀 Moon v.03', 3.2), b: side('s2', '🦍 Ape v.01', -1.1) }], log: [{ at: 1, a: 's1', b: 's2', aName: '🚀 Moon v.03', bName: '🦍 Ape v.01', winner: 's1', aPct: 2, bPct: -1 }] };
  const posts = []; const call = jest.fn(async (url, o) => { if (o) posts.push(JSON.parse(o.body)); return view; });
  const pub = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<PlaygroundBattles call={call} onPublish={pub} />); });
  const pair = el.querySelector('[data-testid="pgb-pair-0"]');
  expect(pair.className).toContain('a-lead'); expect(pair.textContent).toContain('+3.20%'); expect(pair.textContent).toContain('💀 dead $OLD→$A'); expect(pair.textContent).toContain('2–1');
  await act(async () => { el.querySelector('[data-testid="pgb-roundMins-15"]').click(); });
  expect(posts[0]).toEqual({ cfg: { roundMins: 15 } });
  await act(async () => { el.querySelector('.pgb-res .m-btn').click(); });
  expect(pub).toHaveBeenCalledWith('s1');
});

test('engine doctor: filters ranked, the applied one highlighted, tap to override', async () => {
  const { EngineDoctor } = require('./FuseOpsPanels');
  const p = { doctor: { filter: 'score70', sitOut: false, why: 'Score ≥ 70: +12%' }, filters: {
    '24h': { _all: { avgPct: -8, picks: 40 }, score70: { label: '🏅 Score ≥ 70', avgPct: 12, picks: 10, winRate: 60, ready: true }, grad: { label: '🎓 Graduated only', avgPct: -20, picks: 9, winRate: 20, ready: true } },
    '72h': { score70: { avgPct: 6 }, grad: { avgPct: -15 } } } };
  const posts = []; const call = jest.fn(async (url, o) => { posts.push(JSON.parse(o.body)); return { filter: '', sitOut: false }; });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<EngineDoctor p={p} call={call} />); });
  expect(el.textContent).toContain('Applying 🏅 Score ≥ 70'); expect(el.querySelector('[data-testid="pg-filter-score70"]').className).toContain('is-on');
  await act(async () => { el.querySelector('[data-testid="pg-filter-grad"]').click(); });
  expect(posts[0]).toEqual({ filter: 'grad', sitOut: false });
});

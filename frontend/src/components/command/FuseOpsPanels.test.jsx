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
  expect(el.querySelectorAll('.fops-steps li.ok').length).toBeGreaterThan(0); expect(el.textContent).toContain('swap adapters');
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

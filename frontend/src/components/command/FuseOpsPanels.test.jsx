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

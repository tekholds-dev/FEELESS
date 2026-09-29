import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CaseFileView } from './CaseFile';

const mount = async ui => { const host = document.createElement('div'); document.body.appendChild(host); await act(async () => createRoot(host).render(ui)); await act(async () => {}); return host; };

test('wallet case: verdict gauge, cited evidence and the funding trail', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ kind: 'wallet', address: 'Sus1111111111111111111111111111111111111111', score: 75, level: 'high', label: 'High risk',
    summary: 'Sniped 2 launches.', evidence: [{ kind: 'sniper', weight: 30, claim: 'Sniped 2 launches.', source: 'Launch forensics' }],
    trail: { fundedBy: 'Boss111111111111111111111111111111111111111', fundedWallets: [] }, identity: {} }) }));
  const host = await mount(<CaseFileView address="Sus1111111111111111111111111111111111111111" />);
  expect(host.querySelector('.cf-gauge').textContent).toContain('75');
  expect(host.querySelector('.cf-evidence').textContent).toContain('+30Sniped 2 launches.Launch forensics');
  expect(host.textContent).toContain('Funded by Boss…1111');
});

test('coin case: authorities, clusters and the creator case', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ kind: 'coin', address: 'Coin111111111111111111111111111111111111111', score: 70, level: 'danger',
    evidence: [{ kind: 'freeze', weight: 40, claim: 'Freeze authority is live.', source: 'Mint account' }], authorities: { freezeAuthority: 'X', mintAuthority: null },
    holders: { top10Pct: 40 }, launch: { bundled: 3, snipers: 6 }, clusters: { clusters: [{ funder: 'F1111111111111111111111111111111111111111', wallets: ['A', 'B'], pct: 12 }], linkedPct: 12 },
    creatorCase: { address: 'Dev1111111111111111111111111111111111111111', level: 'suspect', label: 'Suspect', score: 45, summary: 'Rugged 1 launch.' } }) }));
  const host = await mount(<CaseFileView address="Coin111111111111111111111111111111111111111" />);
  expect(host.querySelector('.cf-chips').textContent).toContain('Freeze LIVE');
  expect(host.querySelector('.cf-chips').textContent).toContain('Mint revoked');
  expect(host.querySelector('.cf-cluster').textContent).toContain('12%');
  expect(host.querySelector('.cf-creator').textContent).toContain('Rugged 1 launch.');
});

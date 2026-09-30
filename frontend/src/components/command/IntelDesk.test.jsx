import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../CaseFile', () => ({ InvestigatePanel: () => <div>lookup</div>, investigate: (...a) => mockInvestigate(...a) }));
const mockInvestigate = jest.fn();
const { IntelDesk } = require('./IntelDesk');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const NOW = Date.now() / 1000;
const DESK = {
  totals: { actors: 42, rugger: 5, funder: 7, bundler: 12, sniper: 30, rings: 4, active24h: 9, new7d: 14 },
  history: [{ day: '2026-09-29', actors: 38 }, { day: '2026-09-30', actors: 42 }],
  wanted: [{ address: 'FundXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX1', roles: ['funder', 'sniper'], strikes: 6, launches: 4, funded: 9, threat: 72, ring: 'FundXX', lastSeen: NOW - 600, fundedBy: null,
    evidence: [{ claim: 'Bankrolled offenders on 4 launch(es) (9 puppet wallets)', weight: 40, source: 'Funder graph' }], moves: [{ move: 'Loading fresh wallets for the next snipe', confidence: 'medium', why: 'Funded offenders in the last 24h', eta: null }] }],
  rings: [{ id: 'FundXX', core: 'FundXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX1', size: 10, launchesHit: 4, rugs: 2, threat: 80, lastActive: NOW - 600, members: ['FundXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX1', 'PupXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX2'] }],
  moves: [{ move: 'Next launch due', eta: NOW + 7200, confidence: 'high', why: 'Launches every ~6h (5 launches on record)', address: 'RugXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX3', threat: 68, ring: null }],
};

test('intel desk: most wanted with cited evidence, crews, next moves', async () => {
  const call = jest.fn(async () => DESK);
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<IntelDesk call={call} />); });
  expect(el.textContent).toContain('42');
  await act(async () => { el.querySelector('.id-main').click(); });
  expect(el.textContent).toContain('Bankrolled offenders on 4 launch');
  expect(el.textContent).toContain('Loading fresh wallets');
  if (process.env.DUMP_PANEL) require('fs').writeFileSync('/tmp/claude-0/panels.html', el.innerHTML);
  await act(async () => { [...el.querySelectorAll('[role="tab"]')].find(b => b.textContent.startsWith('Crews')).click(); });
  expect(el.textContent).toContain('2 rugs');
  await act(async () => { [...el.querySelectorAll('[role="tab"]')].find(b => b.textContent.startsWith('Next moves')).click(); });
  await act(async () => { el.querySelector('.id-move').click(); });
  expect(mockInvestigate).toHaveBeenCalledWith('RugXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX3');
  act(() => root.unmount());
});

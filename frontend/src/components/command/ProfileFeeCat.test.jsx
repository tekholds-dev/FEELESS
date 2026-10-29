import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockAdmin = { isAdmin: false, call: jest.fn() };
jest.mock('../../lib/adminCall', () => ({ useAdmin: () => mockAdmin }));
jest.mock('../../lib/feeLeader', () => ({ useLeaderProfile: () => ({ cat: { name: 'Fee', status: 'running', realizedPnlSol: -0.2378, positions: [{}] }, discipline: { pause: 'out of lives' }, stats: { winRate: 38 } }) }));
jest.mock('../Panther', () => ({ Panther: () => <i data-testid="panther" /> }));
jest.mock('./FeeCatStage', () => ({ FeeCatStage: () => <div data-testid="stage">STAGE</div> }));
jest.mock('./FeeLiveTab', () => ({ FeeLiveTab: () => <div data-testid="live">LIVE DESK</div> }));
jest.mock('./FeeCatDesk', () => ({ FeeCatDesk: ({ call }) => <div data-testid="nexa-desk">NEXA DESK {typeof call}</div> }));
jest.mock('./FeeOwnerBar', () => ({ FeeOwnerBar: ({ cat }) => <div data-testid="owner-bar">{cat?.name}</div> }));
jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
const { ProfileFeeCat, ProfileFeeBanner } = require('./ProfileFeeCat');

const mount = async el => { const d = document.createElement('div'); document.body.appendChild(d); const r = createRoot(d);
  await act(async () => { r.render(el); }); await act(async () => { await new Promise(x => setTimeout(x, 0)); }); return { d, r }; };

test('🐆 N14 a visitor on the creator profile sees FEECAT (hero + live desk + get your own cat) — never NEXA', async () => {
  mockAdmin.isAdmin = false;
  const { d, r } = await mount(<ProfileFeeCat mine={false} />);
  expect(d.querySelector('[data-testid="stage"]')).not.toBeNull(); expect(d.querySelector('[data-testid="live"]')).not.toBeNull();
  expect(d.querySelector('[data-testid="nexa-desk"]')).toBeNull(); expect(d.textContent).not.toMatch(/NEXA/);
  expect(d.querySelector('[data-testid="profile-fee-cta"]').getAttribute('href')).toBe('/terminal/feecat/cats');
  await act(async () => { r.unmount(); });
  const b = await mount(<ProfileFeeBanner onOpen={() => {}} mine={false} />);
  expect(b.d.textContent).toContain('FEECAT'); expect(b.d.textContent).not.toMatch(/NEXA/); expect(b.d.textContent).toContain('−0.238 SOL'); expect(b.d.textContent).toContain('38%'); expect(b.d.textContent).toContain('napping');   // her hero's rule, not the raw status
  await act(async () => { b.r.unmount(); });
});

test('🐆 N14 the creator on their own profile gets the NEXA desk (the buyer dashboard) and a 👁 switch to what visitors see', async () => {
  mockAdmin.isAdmin = true;
  const { d, r } = await mount(<ProfileFeeCat mine />);
  expect(d.querySelector('[data-testid="nexa-desk"]').textContent).toContain('function');
  expect(d.querySelector('[data-testid="owner-bar"]')).toBeNull();                                  // the NEXA desk draws its OWN creator bar — never a second one
  await act(async () => { d.querySelector('[data-testid="profile-fee-public"]').click(); });
  await act(async () => { await new Promise(x => setTimeout(x, 0)); });
  expect(d.querySelector('[data-testid="live"]')).not.toBeNull(); expect(d.querySelector('[data-testid="profile-fee-cta"]')).toBeNull();
  await act(async () => { r.unmount(); });
  mockAdmin.isAdmin = false;   // the creator's address but not signed in as admin: the public view only
  const p = await mount(<ProfileFeeCat mine />);
  expect(p.d.querySelector('[data-testid="nexa-desk"]')).toBeNull();
  await act(async () => { p.r.unmount(); });
});

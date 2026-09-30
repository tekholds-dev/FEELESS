import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { IntelRail, SeasonRail } from './ProfileRails';

jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
jest.mock('sonner', () => ({ toast: { success: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const W = 'Wa11et1111111111111111111111111111111111111';
const replies = {
  [`/api/reputation/case/${W}`]: { score: 55, level: 'suspect', label: 'Suspect', summary: 'Sniped 2 launches', evidence: [{ weight: 30, claim: 'Sniped 2 launches', source: 'Launch forensics' }, { weight: -10, claim: 'winner', source: 'x' }], trail: { fundedBy: 'Fund1111111111111111111111111111111111111111' } },
  [`/api/reputation/season?address=${W}`]: { season: { id: 's1' }, me: { tier: 'Gold', score: 2500, rank: 4, next: 'Diamond', toNext: 2500 }, tiers: [['Recruit', 0], ['Gold', 2000], ['Diamond', 5000]] },
  [`/api/reputation/season/reserve?address=${W}`]: { active: true, potSol: 2, me: { sol: 0.4 } },
};

test('rails cite the case evidence and show season tier + reserve share', async () => {
  global.fetch = jest.fn(async url => ({ ok: true, json: async () => replies[String(url).replace(/^https?:\/\/[^/]+/, '')] || {} }));
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<><IntelRail address={W} /><SeasonRail address={W} /></>); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const t = el.textContent;
  expect(t).toContain('Suspect');
  expect(t).toContain('Launch forensics');
  expect(t).not.toContain('winner');
  expect(t).toContain('Gold');
  expect(t).toContain('≈ 0.4 SOL');
  expect(el.querySelector('.wpr-bar i').style.width).toBe('16.666666666666664%');
});

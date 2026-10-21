import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { FamilyHero, FamilyTable, FamilyWire, byRank, usdTxt, agoTxt, initials } from './FamilyRoom';

const NOW = Date.now() / 1000;
export const SAMPLE = {
  id: 'c1', name: 'Sicario', tag: 'SIC', seats: 10,
  badge: null, war: { wins: 3, losses: 1, chest: 1250 },
  vitals: { usd: 42.5, wonPct: 61, trades: 18, active: 3, members: 4, heat: 72, respect: 78, hot: { w: 'B', name: 'Vega', heat: 91 }, streak: { w: 'B', name: 'Vega', n: 4 } },
  roles: { hitter: ['🔫', 'Hitter'], scout: ['🔭', 'Scout'], caller: ['🗣', 'Caller'], enforcer: ['🛡', 'Enforcer'], book: ['💼', 'Bookkeeper'], wild: ['🎲', 'Wildcard'] },
  promote: ['underboss', 'consigliere', 'capo', 'soldier'],
  members: [
    { address: 'A'.repeat(40), name: 'Mr. Sicario', owner: true, rank: 'don', rankLabel: '🎩 Don', trades: 6, wonPct: 66, usd: 21.4, heat: 64, status: 'active', streak: 2, last: { sym: 'BONK', pct: 18.2, at: NOW - 600 } },
    { address: 'B'.repeat(40), name: 'Vega', rank: 'underboss', rankLabel: '🥃 Underboss', role: 'hitter', roleIcon: '🔫', roleLabel: 'Hitter', trades: 9, wonPct: 70, usd: 30.1, heat: 91, status: 'fire', streak: 4, last: { sym: 'WIF', pct: 32.5, at: NOW - 120 } },
    { address: 'C'.repeat(40), name: 'Kai', rank: 'capo', rankLabel: '🔫 Capo', role: 'scout', roleIcon: '🔭', roleLabel: 'Scout', trades: 3, wonPct: 33, usd: -9, heat: 30, status: 'active', streak: 0, last: { sym: 'POPCAT', pct: -12.4, at: NOW - 5400 } },
    { address: 'D'.repeat(40), name: 'Nexa', rank: 'associate', rankLabel: '🤝 Associate', trades: 0, usd: 0, heat: 0, status: 'new', streak: 0, last: null },
  ],
  wire: [
    { w: 'B', name: 'Vega', rank: '🥃 Underboss', sym: 'WIF', pct: 32.5, usd: 6.5, at: NOW - 120 },
    { w: 'A', name: 'Mr. Sicario', rank: '🎩 Don', sym: 'BONK', pct: 18.2, usd: 3.6, at: NOW - 600 },
    { w: 'C', name: 'Kai', rank: '🔫 Capo', sym: 'POPCAT', pct: -12.4, usd: -2.5, at: NOW - 5400 },
  ],
};

test('helpers', () => {
  expect(usdTxt(4.5)).toBe('+$4.50'); expect(usdTxt(-120)).toBe('−$120'); expect(usdTxt(null)).toBe('—');
  expect(agoTxt(NOW - 90, NOW)).toBe('2m'); expect(initials('Mr. Sicario')).toBe('MR');
  expect(byRank(SAMPLE.members).map(m => m.rank)).toEqual(['don', 'underboss', 'capo', 'associate']);
});

test('hero, table and wire draw the family', () => {
  const html = renderToStaticMarkup(<div className="crw crw-noir"><FamilyHero mine={SAMPLE} busy="" onLeave={() => {}} /><div className="frm-room"><FamilyTable mine={SAMPLE} owner addr="A" sess="S" /><FamilyWire mine={SAMPLE} /></div></div>);
  expect(html).toContain('Sicario'); expect(html).toContain('RESPECT'); expect(html).toContain('🔫 Hitter'); expect(html).toContain('cashed');
  expect(html).toContain('frm-set');
  if (process.env.FAM_DUMP) require('fs').writeFileSync(process.env.FAM_DUMP, html);
});

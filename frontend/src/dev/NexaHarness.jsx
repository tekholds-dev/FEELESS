import React, { useState } from 'react';
import { CatBrainSwitch } from '../components/command/CatBrainSwitch';
import { FeeOwnerBar } from '../components/command/FeeOwnerBar';

// 🧪 DEV ONLY (`/dev/nexa`; `?owner` adds the creator's 👑 bar — style Fee + her wallet — as the owner sees it): HQ › Fee › NEXA's desk on fixtures — a live FeeCat trade (2-min held checks), SKIM, her stop / take chips and a
// silent call as an icon. `?flat` = FeeCat holds nothing (the 5-min round). Nothing reaches the server: /api/cats/leader is answered here.
const now = Date.now() / 1000;
const LEAD = { cat: { balanceSol: 21.4, wins: 6, losses: 4, positions: [{ symbol: 'GERM', pairAddress: 'PH', currentChange: 6.2, costSol: 0.4, nexa: true },
  { symbol: 'SSS', pairAddress: 'PS', currentChange: 31.5, costSol: 0.2 }] }, scan: { safetyRejects: [{ symbol: 'LUKE', why: 'top 10 wallets hold 41%' }] } };
const DESK = [{ pair: 'PA', symbol: 'AAA', word: 'YES', why: 'graduated, buyers lead', line: '$AAA · graduated · MC 28K · age 40m · buyers 64%', ms: 9100, at: now - 260 },
  { pair: 'PN', symbol: 'NNN', word: 'NO', why: 'top10 over 35%', line: '$NNN · MC 90K · top10 44%', ms: 8800, at: now - 250 },
  { pair: 'PZ', symbol: 'ZZZ', word: null, why: 'no provider answered — deterministic only', line: '$ZZZ · MC 12K', ms: 0, at: now - 240 },
  { pair: 'PS', symbol: 'SSS', word: 'SKIM', why: 'spike into thin pool', line: '$SSS · you +31.5% (peak +38.0%) held 22m', ms: 7400, at: now - 70 },
  { pair: 'PH', symbol: 'GERM', word: 'HOLD', why: 'buyers still lead', lines: { sl: 12, tp: 60 }, line: '$GERM · you +6.2% (peak +9.0%) held 41m', ms: 6900, at: now - 40 }];
const flat = window.location.search.includes('flat');
const real = window.fetch;   // answered before the desk's first poll (a child effect runs before a parent's)
window.fetch = (u, o) => (String(u).includes('/api/cats/leader') ? Promise.resolve({ ok: true, json: () => Promise.resolve(flat ? { cat: { ...LEAD.cat, positions: [] } } : LEAD) }) : real(u, o));
export default function NexaHarness() {
  const [trade, setTrade] = useState(true);
  const d = { trade, provider: { on: true }, desk: DESK, deskAt: now - 250, heldAt: now - 40, deskEvery: 300, heldEvery: 120, deskCalls: 3,
    record: { favor: { n: 147, rightPct: 43, typical: -1.55 } } };
  return <div style={{ minHeight: '100vh', padding: 16, background: '#07040d', boxSizing: 'border-box' }}><div style={{ maxWidth: 640, margin: '0 auto' }}>
    {window.location.search.includes('owner') ? <div style={{ marginBottom: 12 }}><FeeOwnerBar devOwner devAddress="DEV1111111111111111111111111111111111111111"
      cat={{ id: 'leader', name: 'FeeCat', isLeader: true, look: { coat: 'royal', gear: 'crown', eyes: 'laser', aura: 'nebula' }, mode: 'real', realWallet: 'DEV1111111111111111111111111111111111111111', budgetSol: 0.05,
        proposals: [{ id: 'p1', side: 'buy', mint: 'M1', pair: 'P1', symbol: 'AAA', why: '🔮 FeeCat AI said YES · graduated, buyers lead', at: now - 60, until: now + 840, status: 'pending', sol: 0.05 }], realHeld: {} }} /></div> : null}
    <CatBrainSwitch d={d} act={a => setTrade(!!a.trade)} /></div></div>;
}

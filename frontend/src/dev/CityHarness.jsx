import React from 'react';
import { FamilyWorld, FundMeter } from '../components/FamilyWorld';
import '../styles/familyWorld.css';
import WORLD from './world.fixture.json';
import '../styles/familyNoir.css';

// 🧪 DEV ONLY (`/dev/city`): Fee City on a captured public world view + an injected family (two Fee City plots: one SHUT, one funded with a
// launch spire) and a live raid on it — the incoming siren, the fund meter, the dark building. Reads answered locally; nothing is sent.
const ME = '22376b'; const now = Date.now() / 1000;
const blocks = WORLD.blocks.map(b => (b.id === 'fee-4' ? { ...b, owner: ME, tag: 'FRT', name: 'Feeless Family', kind: 'family', mine: true, power: 900, state: 'shut', fundH: 0 }
  : b.id === 'fee-7' ? { ...b, owner: ME, tag: 'FRT', name: 'Feeless Family', kind: 'family', mine: true, power: 2400, state: 'active', fundH: 40, launch: { mint: 'So11111111111111111111111111111111111111112', symbol: 'FEECAT' } }
    : b.owner === ME ? { ...b, mine: true } : b));
const V = { ...WORLD, blocks, rules: { ...(WORLD.rules || {}), upkeepMp: 10 },
  me: { id: ME, tag: 'FRT', name: 'Feeless Family', home: 'hills-5', turf: ['harbor-0', 'harbor-1', 'fee-4', 'fee-7'], pts: 800, bank: 12000, boss: true, reach: {}, prices: {}, errands: [], challenges: [], hitters: [], rewards: [], redeems: [] },
  raids: [{ id: 'r1', status: 'live', kind: 'cpu', a: { id: 'cpu-1', tag: 'RUG', name: 'Rugpull Racketeers' }, b: { id: ME, tag: 'FRT', name: 'Feeless Family' }, round: 1, rounds: 2, turn: 'b', stash: 1840, loot: 120, deadline: now + 214, board: [], moves: [], actions: {} }] };
const real = window.fetch.bind(window);
const json = d => Promise.resolve(new Response(JSON.stringify(d), { status: 200, headers: { 'Content-Type': 'application/json' } }));
// 💬 THE STREETS on fixtures: crests, a Don, a call with its receipt, an @you line, reactions, who's on the block
const crest = (c1, c2, charge, shape, frame, tag, name) => ({ shape, field: 'split', charge, frame, banner: 'ribbon', c1, c2, c3: '#ffffff', tag, name, fx: 'none' });
const FAM = { SIC: { id: 'c1', tag: 'SIC', name: 'Sicario', color: '#d4af37', badge: crest('#d4af37', '#7a0f1f', 'skull', 'heater', 'gold', 'SIC', 'Sicario') },
  FRT: { id: ME, tag: 'FRT', name: 'Feeless Family', color: '#15d16a', badge: crest('#15d16a', '#0b2a19', 'snake', 'kite', 'silver', 'FRT', 'Feeless Family') },
  RUG: { id: 'c3', tag: 'BNK', name: 'Bonk Boys', color: '#ff5fa2', badge: crest('#ff5fa2', '#1b3a6b', 'dice', 'round', 'iron', 'BNK', 'Bonk Boys') } };
const ms = Date.now();
const STREET = { room: 'city-fee', reacts: ['🔥', '💀', '🫡', '💰'], mod: { staff: false, don: true, famId: ME }, me: { fam: FAM.FRT, handle: 'dev' }, hereN: 17,
  here: [['Don Vito', FAM.SIC], ['dev', FAM.FRT], ['bonkmaxi', FAM.RUG], ['lurker', null], ['kid', FAM.SIC]].map(([name, fam], i) => ({ address: `w${i}`, name, fam: fam && { ...fam, don: i === 0 } })),
  vitals: { spark: [1, 0, 2, 3, 1, 4, 6, 3, 5, 8, 4, 7], hour: 44, families: ['SIC', 'FRT', 'BNK'], hot: { symbol: 'WIF', peakX: 3.1, x: 2.4, by: 'Don Vito', fam: 'SIC' } },
  lines: [
    { id: 'l1', ts: ms - 900e3, name: 'Don Vito', handle: 'donvito', text: 'Fee City belongs to Sicario. Pay the toll or swim.', fam: { ...FAM.SIC, don: true }, reacts: { '🫡': { n: 6, mine: false }, '💀': { n: 2, mine: false } } },
    { id: 'l2', ts: ms - 600e3, name: 'bonkmaxi', text: '📞 CALL $WIF EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm — sending it to the moon', fam: { ...FAM.RUG, don: false },
      calls: [{ symbol: 'WIF', x: 2.4, peakX: 3.1, mcAtCall: 1.2e6, pairAddress: 'EKpQ', chain: 'solana' }], reacts: { '🔥': { n: 9, mine: true }, '💰': { n: 4, mine: false } } },
    { id: 'l3', ts: ms - 300e3, name: 'kid', text: '@dev your boys left the dock open, we taking harbor-1 tonight', fam: { ...FAM.SIC, don: false }, atMe: true },
    { id: 'l4', ts: ms - 120e3, name: 'dev', text: '🛡 RALLY — [FRT] hold the block. $BONK dip is a gift', fam: { ...FAM.FRT, don: true }, mine: true,
      calls: [{ symbol: 'BONK', x: 0.82, peakX: 1.04, mcAtCall: 1.9e9, pairAddress: 'BONKP', chain: 'solana' }], reacts: { '🫡': { n: 3, mine: false } } },
    { id: 'l5', ts: ms - 30e3, name: 'lurker', text: 'gm streets, who is buying the next plot on the avenue?', fam: null }] };
window.fetch = (u, o) => (String(u).includes('/familia-world') ? json(V) : String(u).includes('/familia/street/') ? json(STREET) : real(u, o));

export default function CityHarness() {
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 12, background: '#070504', color: '#e9d3a0' }}>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 640, marginBottom: 12 }} data-testid="fund-preview">
      <aside className="fwd-side m-card t-mine"><b>[FRT] fee-4 · turf</b><FundMeter x={blocks.find(b => b.id === 'fee-4')} me={V.me} act={() => {}} busy={false} upkeep={10} /></aside>
      <aside className="fwd-side m-card t-mine"><b>[FRT] fee-7 · turf</b><FundMeter x={blocks.find(b => b.id === 'fee-7')} me={V.me} act={() => {}} busy={false} upkeep={10} /></aside></div>
    <FamilyWorld addr="dev" sess="dev" onEnter={() => {}} onJoin={() => {}} />
  </div>;
}

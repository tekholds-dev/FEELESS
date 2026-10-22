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
window.fetch = (u, o) => (String(u).includes('/familia-world') ? json(V) : real(u, o));

export default function CityHarness() {
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 12, background: '#070504', color: '#e9d3a0' }}>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 640, marginBottom: 12 }} data-testid="fund-preview">
      <aside className="fwd-side m-card t-mine"><b>[FRT] fee-4 · turf</b><FundMeter x={blocks.find(b => b.id === 'fee-4')} me={V.me} act={() => {}} busy={false} upkeep={10} /></aside>
      <aside className="fwd-side m-card t-mine"><b>[FRT] fee-7 · turf</b><FundMeter x={blocks.find(b => b.id === 'fee-7')} me={V.me} act={() => {}} busy={false} upkeep={10} /></aside></div>
    <FamilyWorld addr="dev" sess="dev" onEnter={() => {}} onJoin={() => {}} />
  </div>;
}

import React from 'react';
import { FamilyWorld, FundMeter } from '../components/FamilyWorld';
import { FamiliaTradeDock } from '../components/FamiliaTrade';
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
// 👑 OVERWATCH on fixtures (the creator's view): a fake HQ session so the owner-signed call goes through to the fixture below
V.staff = true;
try { localStorage.setItem('feeless:cc-session', JSON.stringify({ ts: Math.floor(Date.now() / 1000), sig: 'dev' })); } catch { /* private window */ }
const mem = (name, don, trades, usd, wonPct) => ({ address: `${name}Wa11et${name.length}xyzABCD`, name, don, trades, usd, wonPct });
const OW = { totals: { families: 3, members: 9, bankMp: 31840, trades7d: 41, usd7d: 1288.4, paidUsd: 60, turf: 6, pools: 2, houseMp: 900 },
  pricing: { createUsd: 25, packUsd: 5, badgeUsd: 5, baseSeats: 5 }, limits: { familiesPerWallet: 2, upkeepMp: 10, fuseMinMp: 2000 },
  custody: 'Family wallets that hold real money wait on the custody pick (CLAUDE.md P5) — every member trades from their own wallet today.',
  families: [
    { id: ME, tag: 'FRT', name: 'Sicario Family', creator: true, badge: FAM.FRT.badge, owner: { name: 'the creator' }, seats: 10, power: 2400, bankMp: 12000, chest: 1400, record: { wins: 3, losses: 1 },
      home: 'hills-5', turf: ['harbor-0', 'harbor-1', 'fee-4', 'fee-7'], pools: [{ block: 'fee-7', name: 'JLP', apy: 21.4 }, { block: 'harbor-0', name: 'SOL-USDC CLMM', apy: 38.2 }],
      week: { trades: 22, usd: 940.2, pct: 18.4, wonPct: 64 }, paidUsd: 0, payments: 0, launch: { symbol: 'FEE' }, members: [mem('creator', true, 12, 610, 70), mem('vito', false, 6, 288, 60), mem('kid', false, 4, 42.2, 50)] },
    { id: 'c1', tag: 'SIC', name: 'Sicario', badge: FAM.SIC.badge, owner: { name: 'Don Vito' }, seats: 5, power: 1800, bankMp: 15840, chest: 900, record: { wins: 2, losses: 2 }, home: 'fee-2', turf: ['fee-9'],
      pools: [], week: { trades: 15, usd: 401.3, pct: 9.1, wonPct: 55 }, paidUsd: 30, payments: 2, members: [mem('Don Vito', true, 9, 380, 60), mem('lefty', false, 6, 21.3, 50), mem('paulie', false, 0, 0, null)] },
    { id: 'c3', tag: 'BNK', name: 'Bonk Boys', badge: FAM.RUG.badge, owner: { name: 'bonkmaxi' }, seats: 5, power: 600, bankMp: 4000, chest: 300, record: { wins: 0, losses: 2 }, home: 'bay-1', turf: [],
      pools: [], week: { trades: 4, usd: -53.1, pct: -12.5, wonPct: 25 }, paidUsd: 30, payments: 1, members: [mem('bonkmaxi', true, 3, -60, 33), mem('pup', false, 1, 6.9, 100), mem('dog', false, 0, 0, null)] }] };
// 💤 THE NIGHT VAULT on fixtures (the live endpoint is /familia-pools/sleep)
const RK = { contract: 1, depeg: 1, il: 0, liq: 0, note: 'LSTs track SOL + staking rewards.' };
const NV = { kamino: true, at: now, rows: [
    { id: 'n1', kind: 'stake', sym: 'JUPSOL', proto: 'Jupiter', apy: 7.42, base: 7.42, tvl: 9.1e8, hold: 'jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v', app: 'https://jup.ag/', d7: 0.2 },
    { id: 'n2', kind: 'stake', sym: 'JITOSOL', proto: 'Jito', apy: 6.91, base: 6.91, tvl: 2.1e9, hold: 'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', app: 'https://www.jito.network/staking/', d7: -0.1 },
    { id: 'n3', kind: 'lend', sym: 'USDC', proto: 'Jupiter Lend', project: 'jupiter-lend', apy: 6.12, base: 5.4, reward: 0.72, tvl: 4.9e8, stable: true, mints: ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'], app: 'https://jup.ag/lend/earn' },
    { id: 'n4', kind: 'perps', sym: 'JLP', proto: 'Jupiter Perps', apy: 19.8, base: 19.8, tvl: 1.2e9, hold: '27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4', app: 'https://jup.ag/perps-earn' },
    { id: 'n5', kind: 'vault', sym: 'SOL-USDC', proto: 'Kamino Vaults', apy: 31.4, base: 22, reward: 9.4, tvl: 6.2e6, il: true, app: 'https://app.kamino.finance/liquidity' }],
  strategies: [
    { key: 'lst', name: '🥩 STAKE STACK', sub: 'SOL → a liquid staking token: staking yield, still liquid', risk: RK, rows: ['n1', 'n2'], apy: 7.42, top: 'JUPSOL' },
    { key: 'stable', name: '💵 STABLE SLEEP', sub: 'lend USDC / USDT — interest from borrowers', risk: { ...RK, note: 'Lending USDC.' }, rows: ['n3'], apy: 6.12, top: 'USDC' },
    { key: 'jlp', name: '🎰 BE THE HOUSE · JLP', sub: "earn Jupiter perps' fees as the counterparty", risk: { contract: 1, depeg: 2, il: 2, liq: 0, note: 'JLP = the house.' }, rows: ['n4'], apy: 19.8, top: 'JLP' },
    { key: 'vault', name: '🌀 AUTO-COMPOUND', sub: 'vaults that rebalance + compound a DEX position', risk: { contract: 2, depeg: 1, il: 2, liq: 0, note: 'IL is yours.' }, rows: ['n5'], apy: 31.4, top: 'SOL-USDC' },
    { key: 'loop', name: '🔁 LOOP IT · MULTIPLY', sub: 'stake → borrow SOL at 5.3% on Kamino → stake again', risk: { contract: 2, depeg: 2, il: 0, liq: 3, note: 'Liquidation past the cushion.' }, rows: [], apy: 9.54, top: 'JUPSOL ×2',
      loops: [{ id: 'n1', sym: 'JUPSOL', proto: 'Jupiter', lstApy: 7.42, borrow: 5.3, maxLtv: 0.65, app: 'https://app.kamino.finance/multiply', plays: [{ x: 1.5, apy: 8.48, ltv: 0.333, cushion: 0.487 }, { x: 2, apy: 9.54, ltv: 0.5, cushion: 0.231 }] }] }] };
window.fetch = (u, o) => (String(u).includes('/familia-pools/sleep') ? json(NV) : String(u).includes('/familia-world') ? json(V) : String(u).includes('/familia/street/') ? json(STREET) : String(u).includes('/admin/familia/overwatch') ? json(OW) : real(u, o));

export default function CityHarness() {
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 12, background: '#070504', color: '#e9d3a0' }}>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 640, marginBottom: 12 }} data-testid="fund-preview">
      <aside className="fwd-side m-card t-mine"><b>[FRT] fee-4 · turf</b><FundMeter x={blocks.find(b => b.id === 'fee-4')} me={V.me} act={() => {}} busy={false} upkeep={10} /></aside>
      <aside className="fwd-side m-card t-mine"><b>[FRT] fee-7 · turf</b><FundMeter x={blocks.find(b => b.id === 'fee-7')} me={V.me} act={() => {}} busy={false} upkeep={10} /></aside></div>
    <FamilyWorld addr="dev" sess="dev" onEnter={() => {}} onJoin={() => {}} />
    <FamiliaTradeDock />
  </div>;
}

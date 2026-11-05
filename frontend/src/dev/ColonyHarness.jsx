import React from 'react';
import '../index.css';
import '../styles/meta.css';
import { ColonyGrid } from '../components/command/HiveBoard';
import { BoostFolder } from '../components/command/BoostFolder';
import { CollectiveOwner } from '../components/command/CollectiveOwner';
import { SplitFlow } from '../components/command/SplitFlow';
import { BoostCoin } from '../components/command/DeskShell';
import { CollectivePrint, DeskPrint, ProofprintFolder } from '../components/command/Proofprint';

// 🧪 The Colony on fixtures: every number here is made up for the design check.
const agent = (id, name, honey, right, graded, won, trades, pnlSol, extra = {}) => ({ id, name, honey, right, graded, won, trades, pnlSol, proofs: trades, kind: 'trading', owedSol: 0, sharePct: 10, ...extra });
const FLOW = {
  shares: { owedSol: 0.042, count: 4, sharing: 3 }, pot: { sol: 1.84, address: 'Fixture1111111111111111111111111111111111111' }, epoch: { honey: 38, secondsLeft: 40000 },
  proofs: [{ id: 'p1', kind: 'PoW', label: '$BONK', agent: 'Rex', pct: 82.4, stamp: { state: 'proved' }, sent: { sol: 0.0124, sig: '5DMYabcdefGHJKLMNPQRSTUVWXYZ23456789abcdefghijkmnop', link: 'https://solscan.io/tx/5DMY', receipt: '/api/cats/receipt/none' } }, { id: 'p2', kind: 'PoB', label: 'lakers parlays', agent: 'Happy', stamp: { state: 'waiting', dueAt: Date.now() / 1000 + 18000 }, games: [{ id: '1', label: 'Lakers at Bulls', score: '54 - 48', status: 'Q3 4:12' }] }, { id: 'p3', kind: 'PoP', label: 'BTC', agent: 'Nova', pct: -4.1, stamp: { state: 'not' } }, { id: 'p4', kind: 'PoW', label: '$WIF', agent: 'Kit', stamp: { state: 'live' } }, { id: 'p5', kind: 'PoW', label: '$POPCAT', agent: 'Happy', pct: 12, stamp: { state: 'proved' } }, { id: 'p6', kind: 'PoB', label: 'nfl week', agent: 'Rex', stamp: { state: 'proved' } }],
  convos: [{ id: 'c1', aName: 'Happy', bName: 'Rex', lines: [{ by: 'Happy', text: 'My pump coin won because buyers held; my last loss chased a spike.' }, { by: 'Rex', text: 'Agreed. Wait for the second push.' }], joint: { label: '$BONK', call: 'up', why: 'buyers hold' }, dueAt: Date.now() / 1000 + 40000 }],
  airdrop: { next: Date.now() / 1000 + 18000, cadence: 'daily', paidSol: 0.31 }, sentSol: 0.42, pnlSol: 0.7, ledger: [],
  tree: { agents: [agent('a', 'Happy', 14, 9, 12, 5, 7, 0.21, { active: true, boosts: 15, face: { id: 'sarah' } }), agent('b', 'Nova', 9, 6, 9, 3, 5, 0.08, { face: { id: 'amara' } }), agent('c', 'Kit', -3, 2, 7, 1, 4, -0.04, { face: { id: 'kit' } }), agent('d', 'Rex', 21, 11, 13, 6, 8, 0.33, { active: true, boosts: 20, face: { id: 'rex' } }), agent('e', 'Sora', 0, 0, 0, 0, 0, 0), agent('f', 'Theo', 5, 4, 6, 2, 3, 0.02, { face: { id: 'theo' } })],
    wins: [{ id: 'w1', kind: 'PoW', sym: 'BONK', pnlPct: 18.2, state: 'sent', honeySol: 0.012, name: 'Rex' }, { id: 'w2', kind: 'PoW', sym: 'WIF', pnlPct: 6.4, state: 'owed', honeySol: 0.004, name: 'Happy' }] },
};
const COLONY = { agents: FLOW.tree.agents.slice(0, 2).map(a => ({ ...a, colonized: true, status: 'working', windows: [] })), total: 6, colonized: 3, page: 0, more: false };
const api = async url => (url.includes('/flow') ? FLOW : COLONY);
const RULES = { skimPct: 20, splitPct: 75, splitMaxPct: 78, halfLifeDays: 30, halfLifeMinDays: 15, potPct: 30, potHalfLifeDays: 30, weightMaxX: 2, capPct: 3, earnRoomX: 1, boostFadeDays: 60, depositPct: 10, firstMinUsd: 50, txnSmallPct: 5, txnMidPct: 3, txnBigPct: 1, txnSmallUsd: 10, txnBigUsd: 100, boostMode: 'payout' };
const BOUNDS = { skimPct: [0, 50], splitPct: [50, 100], splitMaxPct: [50, 100], halfLifeDays: [7, 180], halfLifeMinDays: [3, 180], potPct: [0, 100], potHalfLifeDays: [7, 180], weightMaxX: [1, 5], capPct: [1, 100], earnRoomX: [0, 5], boostFadeDays: [7, 365], depositPct: [0, 20], firstMinUsd: [0, 500], txnSmallPct: [0, 5], txnMidPct: [0, 5], txnBigPct: [0, 5], txnSmallUsd: [1, 1000], txnBigUsd: [1, 100000] };
const OWNER = { cfg: RULES, defaults: RULES, bounds: BOUNDS, totals: { usd: { keep: 412.5, pot: 96.4, locked: 180.2, owed: 38.7 }, in: { deposit: 300, topup: 90, txn: 64, proofs: 48, release: 22, task: 6 }, agents: 7, ratePerSecUsd: 0.00004 }, chain: { short: [], tokens: { SOL: { chain: 3.2e9, need: 1.4e9 }, USDC: { chain: 120e6, need: 40e6 } } }, agents: [{ id: 'a', name: 'Happy', sentUsd: 54, lockedUsd: 31, owedUsd: 9.1, levers: { splitPct: 76.5 } }, { id: 'b', name: 'Nova', sentUsd: 30, lockedUsd: 18, owedUsd: 4.2, levers: { splitPct: 75 } }], log: [] };
const POOL = { pool: { owedUsd: 9.1234, ratePerSecUsd: 0.0000213, lockedUsd: 31, sentUsd: 54, earnedUsd: 3.4, levers: { splitPct: 76.5 } }, rules: RULES, points: 45, printLevel: 34, boostNow: 0.3, boostLog: [{ ref: 'a', pts: 10, why: 'Proof BONK paid the Pool' }, { ref: 'b', pts: 5, why: 'Convo call on WIF proved' }] };
const ownerCall = async (u, o) => (o ? { ...OWNER, cfg: { ...RULES, ...JSON.parse(o.body).cfg } } : OWNER);
const poolWork = async (id, b) => (b?.op === 'print_style' ? { printStyle: { shape: b.text, ink: b.job } } : POOL);
const pcts = [62, -18, 84, 12, 55, -40, 71, 96, -6, 48, 33, 120, -22, 66, 9, 77, -31, 58, 140, 21];
const PRINT_D = { powFolders: pcts.map((p, i) => ({ id: `w${i}`, at: 1790000000 + i * 90000, soldAt: 1790000000 + i * 90000, name: `PoW #${i + 1}`, sym: ['BONK', 'WIF', 'POPCAT'][i % 3], status: 'closed', pnlPct: p, pnlSol: p / 100, whys: { 0: 'Fresh buyers, deep pool, no dump from the top wallets' } })), popFolders: [8, -12, 31, 44, -3, 19].map((v, i) => ({ id: `p${i}`, n: i + 1, status: 'closed', at: 1790000000 + i * 200000, closedAt: 1790000000 + i * 200000, roePct: v, market: 'SOL', side: 'long' })), pobFolders: [1, 1, -1, 1].map((v, i) => ({ id: `b${i}`, n: i + 1, topic: 'NFL picks', at: 1790000000 + i * 300000, closedAt: 1790000000 + i * 300000, status: 'closed', graded: v > 0 ? 'right' : 'wrong' })) };
const FEED = [['Happy', 62], ['Happy', 84], ['Nova', 71], ['Rex', 96], ['Rex', 55], ['Nova', 120], ['Happy', 58], ['Rex', 66]].map(([agent, pct], i) => ({ id: `s${i}`, kind: 'PoW', label: '$BONK', agent, pct, sent: { sig: `x${i}`, sol: 0.01 } }));
function BoostHarness() {
  return <div style={{ background: '#050714', minHeight: '100vh', padding: 12, display: 'grid', gap: 16, maxWidth: 1180, margin: '0 auto' }}><div style={{ display: 'flex', gap: 12, alignItems: 'center' }}><button type="button" className="dsk-ico is-boost" style={{ position: 'static' }}><i className="dsk-ico-art"><BoostCoin /></i><span>Boosts</span></button></div>
    <div style={{ position: 'relative', height: 420, overflow: 'hidden', borderRadius: 18, border: '1px solid #223', background: '#071020' }}><DeskPrint d={PRINT_D} style={{ shape: 'whorl', ink: 'proof' }} level={34} /></div><ProofprintFolder cat={{ id: 'x' }} d={PRINT_D} work={poolWork} pool={{ ...POOL, readAt: Date.now() }} /><CollectivePrint feed={FEED} /><div style={{ maxWidth: 520 }}><SplitFlow rules={RULES} /></div><BoostFolder cat={{ id: 'x' }} work={poolWork} /><CollectiveOwner call={ownerCall} /></div>;
}
export default function ColonyHarness() {
  if (window.location.search.includes('boost')) return <BoostHarness />;
  return <div style={{ background: '#050403', minHeight: '100vh', padding: 12 }}><ColonyGrid api={api} /></div>;
}

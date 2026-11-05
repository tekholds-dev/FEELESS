import React from 'react';
import '../index.css';
import '../styles/meta.css';
import { ColonyGrid } from '../components/command/HiveBoard';

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
export default function ColonyHarness() {
  return <div style={{ background: '#050403', minHeight: '100vh', padding: 12 }}><ColonyGrid api={api} /></div>;
}

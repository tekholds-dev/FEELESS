import React from 'react';
import '../index.css';
import '../styles/meta.css';
import { ColonyGrid } from '../components/command/HiveBoard';

// 🧪 The Colony on fixtures: every number here is made up for the design check.
const agent = (id, name, honey, right, graded, won, trades, pnlSol, extra = {}) => ({ id, name, honey, right, graded, won, trades, pnlSol, proofs: trades, kind: 'trading', owedSol: 0, sharePct: 10, ...extra });
const FLOW = {
  shares: { owedSol: 0.042, count: 4, sharing: 3 }, pot: { sol: 1.84, address: 'Fixture1111111111111111111111111111111111111' }, epoch: { honey: 38, secondsLeft: 40000 },
  airdrop: { next: Date.now() / 1000 + 18000, cadence: 'daily', paidSol: 0.31 }, sentSol: 0.42, pnlSol: 0.7, ledger: [],
  tree: { agents: [agent('a', 'Happy', 14, 9, 12, 5, 7, 0.21), agent('b', 'Nova', 9, 6, 9, 3, 5, 0.08), agent('c', 'Kit', -3, 2, 7, 1, 4, -0.04), agent('d', 'Rex', 21, 11, 13, 6, 8, 0.33), agent('e', 'Sora', 0, 0, 0, 0, 0, 0), agent('f', 'Theo', 5, 4, 6, 2, 3, 0.02)],
    wins: [{ id: 'w1', kind: 'PoW', sym: 'BONK', pnlPct: 18.2, state: 'sent', honeySol: 0.012, name: 'Rex' }, { id: 'w2', kind: 'PoW', sym: 'WIF', pnlPct: 6.4, state: 'owed', honeySol: 0.004, name: 'Happy' }] },
};
const COLONY = { agents: FLOW.tree.agents.slice(0, 2).map(a => ({ ...a, colonized: true, status: 'working', windows: [] })), total: 6, colonized: 3, page: 0, more: false };
const api = async url => (url.includes('/flow') ? FLOW : COLONY);
export default function ColonyHarness() {
  return <div style={{ background: '#050403', minHeight: '100vh', padding: 12 }}><ColonyGrid api={api} /></div>;
}

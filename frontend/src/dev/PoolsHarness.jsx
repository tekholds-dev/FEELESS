import React from 'react';
import { PoolHub } from '../components/PoolHub';
import CHART from './poolChart.fixture.json';
import '../styles/familyWorld.css';
const real = window.fetch.bind(window);
window.fetch = (u, o) => (String(u).includes('/familia-pools/chart/') ? Promise.resolve(new Response(JSON.stringify(CHART), { status: 200, headers: { 'Content-Type': 'application/json' } })) : real(u, o));

// 🧪 DEV ONLY (`/dev/pools`): the Pool Hub on fixture rows (a Jupiter Lend market opens the deposit-here drawer), no wallet, nothing sent.
const USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const POOLS = [
  { id: 'jl-usdc', src: 'llama', kind: 'lend', project: 'jupiter-lend', proto: 'Jupiter Lend', sym: 'USDC', tvl: 499308781, apy: 5.07, base: 5.07, reward: 0, d7: 0.4, rise: 0.4, mints: [USDC], app: 'https://jup.ag/lend/earn' },
  { id: 'jl-sol', src: 'llama', kind: 'lend', project: 'jupiter-lend', proto: 'Jupiter Lend', sym: 'SOL', tvl: 188000000, apy: 4.9, d7: -0.2, rise: -0.2, mints: ['So11111111111111111111111111111111111111112'], app: 'https://jup.ag/lend/earn' },
  { id: 'kam', src: 'llama', kind: 'vault', project: 'kamino-liquidity', proto: 'Kamino Vaults', sym: 'SOL-USDC', tvl: 52000000, apy: 18.4, d7: 2.1, rise: 2.1, mints: [], app: 'https://app.kamino.finance/liquidity' },
];
export default function PoolsHarness() {
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#050806', color: '#dfe' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · Pool Hub + deposit here (fixtures)</h2>
    <PoolHub pools={{ pools: POOLS }} start="all" />
  </div>;
}

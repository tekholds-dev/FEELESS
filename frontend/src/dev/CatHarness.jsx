import React, { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { CatDesk } from '../components/command/CatDesk';
import { CatReal } from '../components/command/CatReal';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/cats`): one agent's desk with REAL MODE on a fixture cat — paper (go-real) and real (proposals) — nothing reaches the server.
const DEV = 'DEV1111111111111111111111111111111111111111';
const now = Date.now() / 1000;
const REC = { trades: 14, wonPct: 57, pnlSol: 0.084 };
const BASE = { id: 'h1', name: 'Mittens', handle: 'mittens', avatar: 'Ginger', status: 'running', level: 3, xp: 140, wallet: 'PAPERw411et000000000000000000000000000000', wins: 8, losses: 6, winRate: 57,
  realizedPnlSol: 0.084, totalPnlSol: 0.11, balanceSol: 10.11, startingBalanceSol: 10, risk: { maxPositionSol: 0.3, maxDailyLossSol: 1 }, dailyLoss: {},
  pnlHistory: [0, 0.02, -0.01, 0.03, 0.06, 0.04, 0.09, 0.11].map(value => ({ value })),
  positions: [{ symbol: 'GERM', pairAddress: 'P1', mint: 'M1', currentChange: 18.4, costSol: 0.2, openedAt: now - 1260, reason: 'buyers lead · germ floor held' }] };
const PROPS = [{ id: 'a1', side: 'buy', mint: 'M2', pair: 'P2', symbol: 'NEXT', why: 'fresh pump · 41 buyers vs 9 sellers · pool $38K', at: now - 60, until: now + 840, status: 'pending', sol: 0.05, record: REC },
  { id: 'a2', side: 'sell', mint: 'M1', pair: 'P1', symbol: 'GERM', why: 'first take +30 %', at: now - 200, until: now + 700, status: 'pending', fraction: 0.5, record: REC },
  { id: 'a3', side: 'buy', mint: 'M1', pair: 'P1', symbol: 'GERM', why: 'germ floor held twice', at: now - 1300, until: now - 400, status: 'done', sig: '5xSig', sol: 0.05, record: REC },
  { id: 'a4', side: 'buy', mint: 'M3', pair: 'P3', symbol: 'RUGME', why: 'volume spike', at: now - 2000, until: now - 1100, status: 'expired', sol: 0.05, record: REC }];
export default function CatHarness() {
  const [mode, setMode] = useState(window.location.search.includes('paper') ? 'paper' : 'real');
  const cat = mode === 'real' ? { ...BASE, mode: 'real', realWallet: DEV, budgetSol: 0.05, proposals: PROPS, realHeld: { M1: { symbol: 'GERM' } } } : BASE;
  const act = async a => { if (a === 'real') setMode('real'); if (a === 'paper') setMode('paper'); };
  return <MemoryRouter><WalletProvider><div style={{ minHeight: '100vh', padding: 16, background: '#07040d', boxSizing: 'border-box' }}><div style={{ maxWidth: 1180, margin: '0 auto' }}>
    <CatDesk cat={cat} onBack={() => {}} onAct={act} Real={<CatReal cat={cat} onAct={act} devAddress={DEV} />} /></div></div></WalletProvider></MemoryRouter>;
}

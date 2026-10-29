import React, { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { CatDesk } from '../components/command/CatDesk';
import { CatReal } from '../components/command/CatReal';
import { BrainPanel } from '../components/command/LaunchCat';
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
// 👛 its own wallet on fixtures: ?wallet = made + funded (else the make button); /agent-wallet answers locally
const AGT = 'AGTw4LLet9xQ2vRkZb7mNcY1pHf3sJd8uTeW5gK6oLqA';
const realFetch = window.fetch.bind(window);
const FUND = { plan: { usd: 25, feeUsd: 2, catUsd: 23, solUsd: 187.42, totalLamports: 133390000, feeLamports: 10671220, catLamports: 122718780 }, transaction: 'dev', expiresIn: 90 };
window.fetch = (u, o) => (String(u).endsWith('/fund') ? Promise.resolve(new Response(JSON.stringify(FUND), { headers: { 'Content-Type': 'application/json' } })) : String(u).includes('/agent-wallet') ? Promise.resolve(new Response(JSON.stringify({ wallet: { address: AGT, mode: 'approve' }, balance: { sol: 0.4213, usdc: 12.5 } }), { headers: { 'Content-Type': 'application/json' } })) : realFetch(u, o));
export default function CatHarness() {
  const [mode, setMode] = useState(window.location.search.includes('paper') ? 'paper' : 'real');
  const [aw, setAw] = useState(window.location.search.includes('wallet') ? { address: AGT, mode: 'approve', provider: 'crossmint' } : null);
  const cat0 = mode === 'real' ? { ...BASE, mode: 'real', realWallet: DEV, budgetSol: 0.05, proposals: PROPS, realHeld: { M1: { symbol: 'GERM' } } } : BASE;
  const cat = { ...cat0, ...(aw ? { agentWallet: aw } : {}) };
  const act = async (a, x = {}) => { if (a === 'real') setMode('real'); if (a === 'paper') setMode('paper'); if (a === 'agent_wallet') setAw({ address: AGT, mode: 'approve', provider: 'crossmint' }); if (a === 'agent_mode') setAw(w => ({ ...w, mode: x.mode })); };
  // 🧭 ?general = a General AI cat: its brain panel with YOUR ORDERS (one proposed, one filled on paper, one stopped by a guard)
  const gen = window.location.search.includes('general');
  const g = gen ? { ...cat, brainsCfg: { kind: 'general', brains: ['openai/gpt-oss-20b'], brainMode: 'turns', credit: 9.2, asks: 3, spent: 0.8, owed: 0, billing: 'profit', prompt: 'small buys only', decisions: [], chime: [] },
    orders: [{ at: now - 900, text: 'buy 1 SOL of $RUG', order: { side: 'buy', coin: 'RUG', sol: 1 }, state: 'refused', why: '💧 pool $3,000 — under the $5,000 floor (you could not get out)' },
      { at: now - 400, text: 'sell half of $GERM', order: { side: 'sell', coin: 'GERM', fraction: 0.5 }, state: 'filled', why: '📄 paper: sold 50% at the live price' },
      { at: now - 60, text: 'buy 0.05 SOL of $JUP', order: { side: 'buy', coin: 'JUP', sol: 0.05 }, state: 'proposed', why: '✍ buy 0.05 SOL — guards passed, waiting for your wallet\'s signature' }] } : cat;
  return <MemoryRouter><WalletProvider><div style={{ minHeight: '100vh', padding: 16, background: '#07040d', boxSizing: 'border-box' }}><div style={{ maxWidth: 1180, margin: '0 auto' }}>
    <CatDesk cat={g} onBack={() => {}} onAct={act} Real={<CatReal cat={g} onAct={act} devAddress={DEV} />}
      Brains={gen ? <BrainPanel cat={g} api={async () => ({ cat: g })} onChanged={() => {}} /> : null} /></div></div></WalletProvider></MemoryRouter>;
}

import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { WalletContext } from '../hooks/useWallet';
import { RewardsDash } from '../components/RewardsDash';
import '../index.css';

// 🧪 The rewards dash on fixtures, signed in, no wallet (/dev/rewards). ?out = signed out.
const art = ['feeless/recruit'];
const BADGES = Array.from({ length: 22 }, (_, i) => ({ id: `b${i}`, name: ['Recruit', 'Trader', 'Caller', 'Diamond Hands', 'Fuse Master', 'Fee Whale'][i % 6], tier: ['common', 'rare', 'epic', 'legendary'][i % 4], art: `/assets/badges/${art[0]}`, earned: i < 5, pct: i < 5 ? 100 : Math.max(5, 90 - i * 4), tasks: [{ metric: 'trades', label: 'Make 25 trades on FEELESS', done: false }] }));
const DATA = {
  '/rewards/': { address: 'me', total: 2840, streak: 5, rank: 12, log: [], items: [{ id: 'daily', label: 'Daily check-in', how: 'Come back every day', amount: 35, claimable: true }, { id: 'profile', label: 'Complete your profile', how: 'Name, handle, pic and bio', amount: 50, claimable: false, once: true, claimed: 1 }, { id: 'post', label: 'Post in the Trenches', how: 'Post today', amount: 5, claimable: true }, { id: 'call-hit', label: 'Call hits 2×', how: 'Each call that reached 2×', amount: 100, claimable: false }, { id: 'invite', label: 'Invite a friend', how: 'Each wallet from your link', amount: 75, claimable: false }, { id: 'fee-holder', label: 'Hold $FEE', how: 'Hold $1+ of $FEE', amount: 20, claimable: true }, { id: 'link', label: 'Link Solana + EVM', how: 'Link both', amount: 40, claimable: false, once: true }] },
  '/shop': { points: 2840, spent: 340, boosts: 2, tickets: 6, unlocks: {}, items: [{ id: 'mp100', kind: 'mp', label: '10 MP to the bank', cost: 500, grant: {} }, { id: 'mp500', kind: 'mp', label: '60 MP to the bank', cost: 2500, grant: {} }, { id: 'mp1k', kind: 'mp', label: '130 MP to the bank', cost: 5000, grant: {} }, { id: 'boost', kind: 'boost', label: 'Coin boost credit', cost: 200, grant: { boosts: 1 } }, { id: 'raffle', kind: 'raffle', label: 'Raffle ticket', cost: 100, grant: {} }, { id: 'style', kind: 'style', label: 'Gold chat name, 30 d', cost: 800, grant: { color: 'gold' } }, { id: 'bg', kind: 'style', label: 'Noir chat wall, 30 d', cost: 1200, grant: { bg: 'noir' } }] },
  '/quests-leaderboard': { season: { name: 'Season 1' }, paused: true, rows: [] },
  '/quests/': { level: { level: 4, name: 'Soldier', xp: 840, next: 1200 }, earned: 5, total: 45, next: ['b5', 'b6', 'b7'], rarity: { b0: 62 }, editions: {}, editionCap: 100, season: { score: 0 }, badges: BADGES },
  '/rewards-board': { rows: [['degenking', 18200], ['happy', 9400], ['noir', 7200], ['fee', 3100], ['you', 2840]].map(([handle, points], i) => ({ address: i === 4 ? 'me' : handle, handle, points, streak: 3 })) },
};
const real = window.fetch.bind(window);
window.fetch = async (u, o) => { const url = String(u); if (!url.includes('/api/reputation/')) return real(u, o);
  const key = ['/rewards-board', '/quests-leaderboard', '/quests/', '/rewards/', '/shop'].find(k => url.includes(k));
  return new Response(JSON.stringify(url.includes('/claim') ? { ok: true, gained: 35, total: 2875, streak: 6 } : url.includes('/buy') ? { ok: true } : (DATA[key] || {})), { status: 200, headers: { 'Content-Type': 'application/json' } }); };
const out = new URLSearchParams(window.location.search).has('out');
export default function RewardsHarness() {
  return <BrowserRouter><WalletContext.Provider value={{ wallet: out ? null : { address: 'me' }, signMessage: async () => new Uint8Array(64), connect: () => {} }}><div style={{ padding: 16, background: '#020604', minHeight: '100vh' }}><RewardsDash /></div><Toaster /></WalletContext.Provider></BrowserRouter>;
}

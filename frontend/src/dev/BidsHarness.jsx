import React, { useState } from 'react';
import { ProofTools } from '../components/command/ProofTools';
import { PobShelf } from '../components/command/CatWorkbench';
import { LiveBidCard } from '../components/command/LiveBidCard';
import '../styles/meta.css';
import '../styles/terminal.css';

// 🧪 DEV ONLY (`/dev/bids`): the Bids desk's games on the live public board (ESPN, Polymarket, Kalshi prices). No agent, no wallet, no key: a button that would fill the chat box only shows its words here.
// `?bid`: every game room shows a fixture real bid (filled, worth more now) and the minds' after-payout words.
const BID = { agent: 'Happy Assistant', calls: [], bids: [{ n: 15, ticker: 'KXNBAGAME-X', side: 'yes', title: 'Oklahoma City wins', price: 0.4, count: 2, filled: 2, cost: 0.8, now: 1.1, pnl: 0.3, livePx: 0.55, status: 'filled', placed: true, hist: [[1, 0.8], [2, 0.7], [3, 0.92], [4, 0.88], [5, 1.1]] }], final: [{ name: 'hy4', text: 'Rest and the line moved our way; the edge held.' }, { name: 'gpt-6.1-terra', text: 'I passed on odds; next time read Kalshi first.' }] };
// `?slip`: the same, with a real 3-leg parlay (team + two players) instead.
const SLIP = { ...BID, bids: [{ n: 16, kind: 'parlay', side: 'yes', title: 'Parlay', price: 0.21, count: 4, filled: 4, cost: 0.84, now: 1.6, pnl: 0.76, livePx: 0.4, status: 'filled', placed: true, legs: [{ title: 'Houston', side: 'yes', price: 0.75 }, { title: 'Alperen Sengun: 20+', side: 'yes', price: 0.55 }, { title: 'Amen Thompson: 15+', side: 'yes', price: 0.6 }] }] };
// `?file`: the PoB shelf with three readings of one game (two say Thunder vs Kings, one OKC Sacramento: same ESPN game) and one other game.
const T = 1794788221; const OKC = [{ id: '401909993' }];
const FILE = [
  { id: 'f3', n: 17, at: T + 1800, status: 'closed', topic: 'Thunder vs Kings parlay slip', games: OKC, calls: [{ mind: 0, picks: [{ pick: 'Thunder to win', confidence: 74, why: 'rest edge' }, { pick: 'SGA 30+ points', confidence: 66, why: 'pace' }] }, { mind: 1, picks: [{ pick: 'Thunder to win', confidence: 70, why: 'net rating' }] }], agreed: ['Thunder to win'], kalshi: { kind: 'parlay', status: 'waiting', title: 'Parlay', legs: [{ title: 'Oklahoma City wins' }, { title: 'SGA 30+' }], price: 0.31, count: 3, usd: 0.93 } },
  { id: 'f2', n: 16, at: T + 600, status: 'closed', topic: 'OKC Sacramento', games: OKC, calls: [{ mind: 0, picks: [{ pick: 'Thunder to win', confidence: 78, why: 'home form' }] }, { mind: 1, pass: 'no odds' }] },
  { id: 'f9', n: 14, at: T - 3600, status: 'closed', topic: 'Mavericks vs Celtics', games: [{ id: '401909989' }], graded: 'wrong' },
  { id: 'f1', n: 15, at: T, status: 'closed', topic: 'Thunder vs Kings team to win', games: OKC, calls: [{ mind: 0, picks: [{ pick: 'Thunder to win', confidence: 78, why: 'rest' }] }, { mind: 1, picks: [{ pick: 'Kings +9.5', confidence: 55, why: 'spread' }] }], kalshi: { kind: 'single', status: 'filled', orderId: 'o1', title: 'Oklahoma City wins', price: 0.81, count: 1, usd: 0.81 } },
];
function FileShelf() {
  const [open, setOpen] = useState('');
  return <section className="cwb" style={{ maxWidth: 820 }}><button type="button" className="m-btn" onClick={() => setOpen('')} data-testid="pob-up">↑ shelf</button><PobShelf d={{ pobFolders: FILE }} open={open} setOpen={setOpen} catId="dev" onMark={() => {}} /></section>;
}
export default function BidsHarness() {
  const [said, setSaid] = useState([]);
  if (window.location.search.includes('watch')) return <main className="terminal-app" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', color: 'var(--m-text)' }}><section className="cwb" style={{ maxWidth: 720 }}><LiveBidCard f={{ ...FILE[3], games: [{ id: new URLSearchParams(window.location.search).get('watch') || '401909993', sport: 'nba', side: 'Oklahoma City Thunder', state: 'pre' }] }} onClose={() => {}} /></section></main>;   // `?watch=<espn id>`: the 📺 card on a real game
  if (window.location.search.includes('file')) return <main className="terminal-app" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', color: 'var(--m-text)' }}><FileShelf /></main>;
  return <main className="terminal-app" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', color: 'var(--m-text)' }}>
    <ProofTools kind="bids" onCommand={t => setSaid(x => [t, ...x].slice(0, 5))} loadCalls={window.location.search.includes('slip') ? () => Promise.resolve(SLIP) : window.location.search.includes('bid') ? () => Promise.resolve(BID) : null} />
    <aside data-testid="bids-said" style={{ marginTop: 12, fontFamily: 'var(--f-mono)', fontSize: 11, opacity: 0.75 }}>{said.length ? said.map((t, i) => <div key={i}>chat box ← {t}</div>) : 'Nothing put in the chat box yet.'}</aside>
  </main>;
}

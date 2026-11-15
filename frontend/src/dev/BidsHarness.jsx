import React, { useState } from 'react';
import { ProofTools } from '../components/command/ProofTools';
import '../styles/meta.css';
import '../styles/terminal.css';

// 🧪 DEV ONLY (`/dev/bids`): the Bids desk's games on the live public board (ESPN, Polymarket, Kalshi prices). No agent, no wallet, no key: a button that would fill the chat box only shows its words here.
// `?bid`: every game room shows a fixture real bid (filled, worth more now) and the minds' after-payout words.
const BID = { agent: 'Happy Assistant', calls: [], bids: [{ n: 15, ticker: 'KXNBAGAME-X', side: 'yes', title: 'Oklahoma City wins', price: 0.4, count: 2, filled: 2, cost: 0.8, now: 1.1, pnl: 0.3, livePx: 0.55, status: 'filled', placed: true, hist: [[1, 0.8], [2, 0.7], [3, 0.92], [4, 0.88], [5, 1.1]] }], final: [{ name: 'hy4', text: 'Rest and the line moved our way; the edge held.' }, { name: 'gpt-6.1-terra', text: 'I passed on odds; next time read Kalshi first.' }] };
// `?slip`: the same, with a real 3-leg parlay (team + two players) instead.
const SLIP = { ...BID, bids: [{ n: 16, kind: 'parlay', side: 'yes', title: 'Parlay', price: 0.21, count: 4, filled: 4, cost: 0.84, now: 1.6, pnl: 0.76, livePx: 0.4, status: 'filled', placed: true, legs: [{ title: 'Houston', side: 'yes', price: 0.75 }, { title: 'Alperen Sengun: 20+', side: 'yes', price: 0.55 }, { title: 'Amen Thompson: 15+', side: 'yes', price: 0.6 }] }] };
export default function BidsHarness() {
  const [said, setSaid] = useState([]);
  return <main className="terminal-app" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', color: 'var(--m-text)' }}>
    <ProofTools kind="bids" onCommand={t => setSaid(x => [t, ...x].slice(0, 5))} loadCalls={window.location.search.includes('slip') ? () => Promise.resolve(SLIP) : window.location.search.includes('bid') ? () => Promise.resolve(BID) : null} />
    <aside data-testid="bids-said" style={{ marginTop: 12, fontFamily: 'var(--f-mono)', fontSize: 11, opacity: 0.75 }}>{said.length ? said.map((t, i) => <div key={i}>chat box ← {t}</div>) : 'Nothing put in the chat box yet.'}</aside>
  </main>;
}

import React, { useState } from 'react';
import { ProofTools } from '../components/command/ProofTools';
import '../styles/meta.css';
import '../styles/terminal.css';

// 🧪 DEV ONLY (`/dev/bids`): the Bids desk's games on the live public board (ESPN, Polymarket, Kalshi prices). No agent, no wallet, no key: a button that would fill the chat box only shows its words here.
export default function BidsHarness() {
  const [said, setSaid] = useState([]);
  return <main className="terminal-app" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', color: 'var(--m-text)' }}>
    <ProofTools kind="bids" onCommand={t => setSaid(x => [t, ...x].slice(0, 5))} />
    <aside data-testid="bids-said" style={{ marginTop: 12, fontFamily: 'var(--f-mono)', fontSize: 11, opacity: 0.75 }}>{said.length ? said.map((t, i) => <div key={i}>chat box ← {t}</div>) : 'Nothing put in the chat box yet.'}</aside>
  </main>;
}

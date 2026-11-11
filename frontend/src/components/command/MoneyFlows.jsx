import React from 'react';
import { Ic3 } from '../../lib/icon3d';

// Plain-language map of every way FEELESS earns and where each one lands: ONE closed disclosure at the foot of Money › Treasury
// (owner 2026-11-10: HQ tabs cluttered — it used to open on two tabs, above the data, plus three more explainer cards).
export function MoneyFlows({ more = [] }) {
  return <details className="tr-explain money-flows" data-testid="money-flows"><summary><Ic3 e="ⓘ" /> How the money flows: 4 streams, fee accounts, splits</summary>
      <div className="mf-grid">
        <div><b>1 · Trading fee</b><small>Every trade on FEELESS</small><p>Paid inside the trade itself into your <b>fee accounts</b> the moment it confirms. Nothing to claim.</p></div>
        <div><b>2 · Launch fee share</b><small>Coins launched on your configs</small><p>Waits <b>inside each coin's pool</b> until the config's fee claimer claims it (Launch tab › fee share to claim).</p></div>
        <div><b>3 · Pool swap fees</b><small>Pools you create in the Pools tab</small><p>Earned by the <b>wallet that created the pool</b>. Claim them from that pool's position, locked or not.</p></div>
        <div><b>4 · Creator share</b><small>Coins your wallet launched</small><p>Claimable by the <b>creator wallet</b> on the coin's page (Claim creator fees).</p></div>
      </div>
      <h4><Ic3 e="👛" /> Did it make new Phantom accounts?</h4>
      <p><b>No new accounts or wallets.</b> "Fee accounts" are two token accounts — one for wrapped SOL (wSOL), one for USDC — that belong to the fee wallet you picked when you created them (usually your connected creator wallet). Phantom shows them simply as that wallet's <b>wSOL</b> and <b>USDC</b> balances. Every trade's fee drops straight in; nobody else can move it.</p>
      <p><b>wSOL</b> is SOL in token form (needed so fees can be paid inside swaps). Unwrap it in Phantom, or send it on with Treasury › Split now. If you want fees kept apart from your personal funds, create them for a <b>separate Phantom account</b> (Phantom › Add account: same recovery phrase, new address) or a Squads multisig.</p>
      {more.map(([t, body]) => <React.Fragment key={t}><h4>{t}</h4>{body}</React.Fragment>)}
    </details>;
}

import React from 'react';

// Plain-language map of every way FEELESS earns and where each one lands. Shown on Trading & fees and Treasury.
export function MoneyFlows() {
  return <div className="money-flows" data-testid="money-flows">
    <details className="tr-explain" open><summary>💸 Where does the money go? (4 streams, none hidden)</summary>
      <div className="mf-grid">
        <div><b>1 · Trading fee</b><small>Every trade on FEELESS</small><p>Paid inside the trade itself into your <b>fee accounts</b> the moment it confirms. Nothing to claim.</p></div>
        <div><b>2 · Launch fee share</b><small>Coins launched on your configs</small><p>Waits <b>inside each coin's pool</b> until the config's fee claimer claims it (Launch tab › fee share to claim).</p></div>
        <div><b>3 · Pool swap fees</b><small>Pools you create in the Pools tab</small><p>Earned by the <b>wallet that created the pool</b>. Claim them from that pool's position, locked or not.</p></div>
        <div><b>4 · Creator share</b><small>Coins your wallet launched</small><p>Claimable by the <b>creator wallet</b> on the coin's page (Claim creator fees).</p></div>
      </div></details>
    <details className="tr-explain"><summary>👛 Did it make new Phantom accounts? Where do trading fees actually land?</summary>
      <p><b>No new accounts or wallets.</b> "Fee accounts" are two token accounts — one for wrapped SOL (wSOL), one for USDC — that belong to the fee wallet you picked when you created them (usually your connected creator wallet). Phantom shows them simply as that wallet's <b>wSOL</b> and <b>USDC</b> balances. Every trade's fee drops straight in; nobody else can move it.</p>
      <p><b>wSOL</b> is SOL in token form (needed so fees can be paid inside swaps). Unwrap it in Phantom, or send it on with Treasury › Split now. If you want fees kept apart from your personal funds, create them for a <b>separate Phantom account</b> (Phantom › Add account: same recovery phrase, new address) or a Squads multisig.</p></details>
  </div>;
}

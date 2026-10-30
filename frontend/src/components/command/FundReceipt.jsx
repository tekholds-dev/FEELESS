import React, { useEffect, useState } from 'react';
import { sharedJson } from '../../lib/sharedJson';
import { useWallet } from '../../hooks/useWallet';
import '../../styles/createCat.css';

// 💵 THE FUNDING RECEIPT at the end of BOTH cat flows (Create a cat · Launch a cat) — owner 2026-10-29: "create a cat doesn't show top up X amount at the end".
// DECISIONS #2 (W01 agent wallets): going real, the cat gets ITS OWN wallet; your wallet signs ONE funding transaction — the one-time FEELESS fee
// (HQ › Fees, none for a creator wallet) + the rest into the cat's wallet; then it trades inside the server caps. The live rules come from
// /cats/fund-rules (the same the funding card uses); the buy picker shows what the cat's wallet needs per buy (the buy + swap fee + network / rent).
const BUYS = [0.02, 0.05, 0.1, 0.25];
const GAS_SOL = 0.003;   // network fee + a new coin account's rent, per first buy of a coin
export const fundPlan = (buySol, bps) => { const fee = buySol * (Number(bps) || 0) / 10000; return { fee, need: buySol + fee + GAS_SOL }; };
export function FundReceipt({ general = false }) {
  const [bps, setBps] = useState(null); const [buy, setBuy] = useState(0.05); const [rules, setRules] = useState(null);
  const addr = (useWallet() || {}).wallet?.address || '';
  useEffect(() => { let on = true; sharedJson('/api/reputation/fees/pricing', { maxAge: 60000 }).then(d => { if (on) setBps(Number(d?.swapBps) || 0); }).catch(() => on && setBps(null)); return () => { on = false; }; }, []);
  useEffect(() => { let on = true; sharedJson(`/api/reputation/cats/fund-rules?address=${encodeURIComponent(addr)}`, { maxAge: 60000 }).then(d => { if (on && d) setRules(d); }).catch(() => {}); return () => { on = false; }; }, [addr]);
  const p = fundPlan(buy, bps); const fee = rules ? Number(rules.feeUsd) || 0 : null;
  return <div className="cct-fund" data-testid="cat-fund"><span className="m-label">💵 GOING REAL · WHAT IT COSTS</span>
    <div className="cct-fund-rows">
      <span data-tip={rules?.staff ? 'Your wallet is a FEELESS creator wallet — no fee' : 'Taken once, out of the first funding only — never again on top-ups'}><small>ONE-TIME FEE</small><b className="m-num">{fee == null ? '…' : fee ? `$${fee}` : 'none'}</b></span>
      <span data-tip="The least a first funding may be — the fee comes out of it, the rest lands in the cat's own wallet"><small>FIRST FUNDING ≥</small><b className="m-num">{rules ? `$${rules.minUsd}` : '…'}</b></span>
      <span data-tip={bps == null ? 'Reading the live fee…' : `The FEELESS swap fee right now: ${(bps / 100).toFixed(2)}% of each swap`}><small>FEE / SWAP</small><b className="m-num">{bps == null ? '…' : `${(bps / 100).toFixed(bps % 100 ? 2 : 0)}%`}</b></span>
    </div>
    {general ? <p className="cct-fund-note">The fee and minimum apply once. Money it spends on your tasks comes from its own wallet, and the swap fee applies only when it trades a coin.</p> : <><div className="m-seg" role="radiogroup" aria-label="One buy">{BUYS.map(b => <button key={b} type="button" role="radio" aria-checked={buy === b} className={buy === b ? 'active' : ''} onClick={() => setBuy(b)} data-tip={`What its wallet needs for one ${b} SOL buy`} data-testid={`cat-fund-${b}`}>{b} SOL</button>)}</div>
    <div className="cct-fund-rows"><span className="is-need" data-tip="Its wallet needs at least this for one buy of that size: the buy + the swap fee + network fee and a new coin account"><small>ONE {buy} SOL BUY NEEDS</small><b className="m-num">≥ {p.need.toFixed(3)} SOL</b></span>
      <span data-tip="Server caps on every move from its wallet"><small>CAPS</small><b className="m-num">≤ 0.5 SOL a buy · daily cap</b></span></div>
    <p className="cct-fund-note">After launch, give it <b>its own wallet</b> from the cat's 💵 panel: your wallet signs <b>one</b> funding transaction, then it trades inside the caps — a general cat asks you (one tap) before each move until you switch it to auto. FEELESS never sees your wallet's keys.</p></>}
  </div>;
}

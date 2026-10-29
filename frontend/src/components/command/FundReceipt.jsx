import React, { useEffect, useState } from 'react';
import { sharedJson } from '../../lib/sharedJson';
import '../../styles/createCat.css';

// 💵 THE FUNDING RECEIPT at the end of BOTH cat flows (Create a cat · Launch a cat) — owner 2026-10-29: "create a cat doesn't show top up X amount at the end". Option A (DECISIONS #2):
// a cat never holds money — going real later, it PROPOSES and YOUR wallet signs each trade. So the end of the flow says exactly what that costs:
// pick the most one buy may be → the FEELESS fee on it (the LIVE swap fee from /fees/pricing) → what your wallet should hold to take its proposals.
const BUYS = [0.02, 0.05, 0.1, 0.25];
const GAS_SOL = 0.003;   // network fee + a new coin account's rent, per first buy of a coin
export const fundPlan = (buySol, bps) => { const fee = buySol * (Number(bps) || 0) / 10000; return { fee, need: buySol + fee + GAS_SOL }; };
export function FundReceipt() {
  const [bps, setBps] = useState(null); const [buy, setBuy] = useState(0.05);
  useEffect(() => { let on = true; sharedJson('/api/reputation/fees/pricing', { maxAge: 60000 }).then(d => { if (on) setBps(Number(d?.swapBps) || 0); }).catch(() => on && setBps(null)); return () => { on = false; }; }, []);
  const p = fundPlan(buy, bps);
  return <div className="cct-fund" data-testid="cat-fund"><span className="m-label">💵 GOING REAL LATER · WHAT IT COSTS</span>
    <div className="m-seg" role="radiogroup" aria-label="The most one buy may be">{BUYS.map(b => <button key={b} type="button" role="radio" aria-checked={buy === b} className={buy === b ? 'active' : ''} onClick={() => setBuy(b)} data-tip={`It never proposes a buy above ${b} SOL`} data-testid={`cat-fund-${b}`}>{b} SOL</button>)}</div>
    <div className="cct-fund-rows">
      <span data-tip="The most one proposal may spend"><small>ONE BUY ≤</small><b className="m-num">{buy} SOL</b></span>
      <span data-tip={bps == null ? 'Reading the live fee…' : `The FEELESS swap fee right now: ${(bps / 100).toFixed(2)}% of each swap`}><small>FEE / SWAP</small><b className="m-num">{bps == null ? '…' : `${(bps / 100).toFixed(bps % 100 ? 2 : 0)}% · ${p.fee.toFixed(4)} SOL`}</b></span>
      <span className="is-need" data-tip="Keep at least this in YOUR wallet to sign one proposal (the buy + its fee + network fee and a new coin account)"><small>KEEP IN YOUR WALLET</small><b className="m-num">≥ {p.need.toFixed(3)} SOL</b></span>
    </div>
    <p className="cct-fund-note">No top-up to FEELESS: your cat proposes, <b>your wallet</b> signs every trade — FEELESS never holds your SOL or a key. Switch it real from the cat's 💵 panel.</p>
  </div>;
}

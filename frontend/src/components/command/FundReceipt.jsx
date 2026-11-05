import React, { useEffect, useState } from 'react';
import { sharedJson } from '../../lib/sharedJson';
import { useWallet } from '../../hooks/useWallet';
import '../../styles/createCat.css';
import { Ic3 } from '../../lib/icon3d';

// 💵 THE FUNDING RECEIPT at the end of BOTH cat flows (Create an agent · Launch an agent) — owner 2026-10-29: "create an agent doesn't show top up X amount at the end".
// DECISIONS #2 (W01 agent wallets): going real, the agent gets ITS OWN wallet; your wallet signs ONE funding transaction — the one-time FEELESS fee
// (HQ › Fees, none for a creator wallet) + the rest into the agent's wallet; then it trades inside the server caps. The live rules come from
// /cats/fund-rules (the same the funding card uses); the buy picker shows what the agent's wallet needs per buy (the buy + swap fee + network / rent).
const BUYS = [0.02, 0.05, 0.1, 0.25];
const GAS_SOL = 0.003;   // network fee + a new coin account's rent, per first buy of a coin
export const fundPlan = (buySol, bps) => { const fee = buySol * (Number(bps) || 0) / 10000; return { fee, need: buySol + fee + GAS_SOL }; };
export function FundReceipt({ general = false }) {
  const [bps, setBps] = useState(null); const [buy, setBuy] = useState(0.05); const [rules, setRules] = useState(null);
  const addr = (useWallet() || {}).wallet?.address || '';
  useEffect(() => { let on = true; sharedJson('/api/reputation/fees/pricing', { maxAge: 60000 }).then(d => { if (on) setBps(Number(d?.swapBps) || 0); }).catch(() => on && setBps(null)); return () => { on = false; }; }, []);
  useEffect(() => { let on = true; sharedJson(`/api/reputation/cats/fund-rules?address=${encodeURIComponent(addr)}`, { maxAge: 60000 }).then(d => { if (on && d) setRules(d); }).catch(() => {}); return () => { on = false; }; }, [addr]);
  const p = fundPlan(buy, bps);
  return <div className="cct-fund" data-testid="cat-fund"><span className="m-label"><Ic3 e="💵" /> GOING REAL · WHAT IT COSTS</span>
    <div className="cct-fund-rows">
      <span data-tip={rules?.staff ? 'Your wallet is a FEELESS creator wallet: no fee' : 'First deposit and $50 or more: 10%. Under $50: 5%, and every 3rd is 10%. Half FEELESS, half the Collective'}><small>DEPOSIT FEE</small><b className="m-num">{rules ? (rules.staff ? 'None' : '5–10%') : '…'}</b></span>
      <span data-tip="The least a first deposit may be. The fee comes out of it, the rest goes where you choose"><small>FIRST DEPOSIT ≥</small><b className="m-num">{rules ? `$${rules.minUsd}` : '…'}</b></span>
      <span data-tip={bps == null ? 'Reading the live fee…' : `The FEELESS swap fee right now: ${(bps / 100).toFixed(2)}% of each swap`}><small>FEE / SWAP</small><b className="m-num">{bps == null ? '…' : `${(bps / 100).toFixed(bps % 100 ? 2 : 0)}%`}</b></span>
    </div>
    {general ? <p className="cct-fund-note">The minimum applies once. Money it spends on your tasks comes from its own wallet, and the swap fee applies only when it trades a coin.</p> : <><div className="m-seg" role="radiogroup" aria-label="One buy">{BUYS.map(b => <button key={b} type="button" role="radio" aria-checked={buy === b} className={buy === b ? 'active' : ''} onClick={() => setBuy(b)} data-tip={`What its wallet needs for one ${b} SOL buy`} data-testid={`cat-fund-${b}`}>{b} SOL</button>)}</div>
    <div className="cct-fund-rows"><span className="is-need" data-tip="Its wallet needs at least this for one buy of that size: the buy + the swap fee + network fee and a new coin account"><small>ONE {buy} SOL BUY NEEDS</small><b className="m-num">≥ {p.need.toFixed(3)} SOL</b></span>
      <span data-tip="Server caps on every move from its wallet"><small>CAPS</small><b className="m-num">≤ 0.5 SOL a buy · daily cap</b></span></div>
    <p className="cct-fund-note">After launch, give it <b>its own wallet</b> from the agent's <Ic3 e="💵" /> panel: your wallet signs <b>one</b> funding transaction, then it trades inside the caps — a general cat asks you (one tap) before each move until you switch it to auto. FEELESS never sees your wallet's keys.</p></>}
  </div>;
}

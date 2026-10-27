import React from 'react';
import { STAKES, setStake, useStake } from '../lib/earnStake';
import '../styles/earnStake.css';

// 💸 WHAT YOUR MONEY DOES HERE (owner, 2026-10-23: "pools + perps must earn … what $5 / $100 earns, live"):
// · StakeSeg — the one stake picker ($5 · $100 · $1K) every Pool Hall row quotes at.
export function StakeSeg({ label = 'IF YOU PUT IN' }) {
  const v = useStake(); const [txt, setTxt] = React.useState(String(v)); React.useEffect(() => { setTxt(String(v)); }, [v]);
  return <span className="es-seg" data-testid="stake-seg"><em>{label}</em><span className="m-seg" role="radiogroup" aria-label="Stake">{STAKES.map(s => <button key={s} type="button" role="radio"
    aria-checked={v === s} className={v === s ? 'active' : ''} onClick={() => setStake(s)} data-tip={`Quote every earning on this page at $${s.toLocaleString('en-US')}`} data-testid={`stake-${s}`}>${s >= 1000 ? `${s / 1000}K` : s}</button>)}</span><label className="es-in" data-tip="Type any amount — every earning on the page re-quotes"><span>$</span><input type="number" min="1" step="any" value={txt} onChange={e => { setTxt(e.target.value); setStake(Number(e.target.value)); }} aria-label="Dollars to quote" data-testid="stake-in" /></label></span>;
}


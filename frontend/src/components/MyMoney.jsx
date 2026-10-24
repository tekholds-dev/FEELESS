import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { useGlide } from '../lib/useGlide';
import { cash } from '../lib/earnStake';
import { familiaTrade } from './FamiliaTrade';
import { FamEmpty } from './FamEmpty';
import { EarnTicker } from './EarnTicker';
import '../styles/myMoney.css';

// 💵 YOUR MONEY (owner 1e: "one YOUR MONEY tower in the capital — every proved position, live"): the Avenue building's room. Your positions
// as a drawn TOWER (one lit floor per position, wider = more of your money, green / red by the coin's 24 h move, gold = a market earning
// APY), the proved total ticking on the crown, and each row one tap from its trade desk — inside Familia. Data: GET /familia/my-money
// (my_money.py) — coins from your verified FEELESS trades, markets from your family block's on-chain reads; never a fee-tainted P&L.
const FLOORS = 9;
export function towerFloors(positions) {
  const ps = (positions || []).slice(0, FLOORS);
  return ps.map((x, i) => ({ ...x, w: 40 + Math.sqrt(Math.min(1, x.share || 0)) * 84, tone: x.kind === 'market' ? 'gold' : (x.ch24 ?? 0) >= 0 ? 'up' : 'dn', i }));
}

export default function MyMoney({ devAddress = '' }) {   // devAddress: the /dev/money preview only (no wallet there)
  const { wallet } = useWallet() || {}; const addr = (wallet?.chain === 'solana' ? wallet.address : '') || devAddress;
  const sess = addr ? readChatSession(addr) : '';
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!addr) { setD(null); return undefined; }
    let on = true; let t = null;
    const go = () => sharedJson(`/api/reputation/familia/my-money?address=${addr}${sess ? `&session=${encodeURIComponent(sess)}` : ''}`, { maxAge: 40000 })
      .then(x => on && x && setD(x)).catch(() => {}).finally(() => { if (on) t = setTimeout(go, document.hidden ? 120000 : 45000); });
    go(); return () => { on = false; clearTimeout(t); };
  }, [addr, sess]);
  const total = useGlide(d?.total || 0);
  if (!addr) return <FamEmpty art="tower" title="CONNECT TO LIGHT YOUR TOWER" note="Your money tower lights one floor for every position FEELESS can prove — coins you traded here and your family block's markets." testid="ym-empty" />;
  if (!d) return <div className="ym-load" aria-busy="true"><i /><i /><i /><span>counting your money…</span></div>;
  const fl = towerFloors(d.positions);
  const yr = (d.positions || []).filter(x => x.kind === 'market' && x.apy > 0).reduce((t, x) => t + (x.usd || 0) * x.apy / 100, 0);   // $ a year the markets pay, live APY
  const H = 22 + fl.length * 17;
  return <div className="ym" data-testid="my-money">
    <div className="ym-hero">
      <svg className="ym-tower" viewBox={`0 0 140 ${H + 40}`} aria-label={`Your money tower: ${fl.length} floors`}>
        <path className="ym-crown" d={`M45 ${32} L70 8 L95 ${32} Z`} /><circle className="ym-beacon" cx="70" cy="6" r="3.5" />
        {fl.slice().reverse().map((f, k) => { const y = 34 + k * 17; return <g key={f.key} className={`ym-floor is-${f.tone}`} style={{ '--i': fl.length - 1 - k }}>
          <rect x={70 - f.w / 2} y={y} width={f.w} height="14" rx="2" />{Array.from({ length: Math.max(2, Math.round(f.w / 14)) }, (_, j) => <rect key={j} className="ym-win" x={70 - f.w / 2 + 5 + j * 12} y={y + 4} width="5" height="6" />)}</g>; })}
        <rect className="ym-base" x="30" y={34 + fl.length * 17} width="80" height="6" rx="2" />
      </svg>
      <span className="ym-total" data-tip="Proved = coins from your verified FEELESS trades + your family block's on-chain positions. P&L lives on each trade's receipt — fees never mixed in."><em>YOUR MONEY · PROVED · LIVE</em><b className="m-num" key={Math.round(d.total)}>{cash(total)}</b>
        <small>{d.coins} coin{d.coins === 1 ? '' : 's'} · {d.markets} market{d.markets === 1 ? '' : 's'}{d.dust ? ` · ${d.dust} dust` : ''}{d.unpriced ? ` · ${d.unpriced} unpriced` : ''}</small>
        <i className="ym-legend"><u className="up" />coin up 24h <u className="dn" />coin down <u className="gold" />market earning APY</i>
        {yr > 0 ? <EarnTicker perYear={yr} label="YOUR MARKETS · EARNING NOW" tip="Your block's markets at their live APY — what they earn while you look" testid="ym-earn" /> : null}</span>
    </div>
    {!(d.positions || []).length ? <FamEmpty art="tower" title="NO PROVED POSITIONS YET" note="Trade a coin through FEELESS or build a market on your family block — each one lights a floor." testid="ym-none" />
      : <ol className="ym-list">{d.positions.map((x, i) => <li key={x.key} style={{ '--i': i }} className={`is-${x.kind}`} data-testid={`ym-row-${x.key}`}>
        {x.image ? <img src={x.image} alt="" loading="lazy" /> : <i className="ym-dot" />}
        <span className="ym-id"><b>{x.kind === 'coin' ? `$${x.sym}` : x.sym}</b><small>{x.kind === 'coin' ? `24h ${x.ch24 == null ? '—' : `${x.ch24 >= 0 ? '+' : ''}${x.ch24.toFixed(1)}%`}` : `${x.name || 'market'} · APY ${x.apy == null ? '—' : `${x.apy.toFixed(1)}%`}`}</small></span>
        <u className="ym-share" aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, x.share || 0)})` }} /></u>
        <b className="m-num ym-usd">{cash(x.usd)}</b>
        {x.kind === 'coin' && x.pair ? <button type="button" className="m-btn m-go ym-go" onClick={() => familiaTrade({ chainId: 'solana', pairAddress: x.pair, baseToken: { address: x.key, symbol: x.sym } })}
          data-tip={`$${x.sym}: its chart + Quick trade, right here — your wallet signs`} data-testid={`ym-trade-${x.key}`}>⚡ Trade</button> : <small className="ym-tag">on your block</small>}</li>)}</ol>}
  </div>;
}

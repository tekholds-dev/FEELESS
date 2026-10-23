import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../hooks/useWallet';
import { useGlide } from '../lib/useGlide';
import { cash } from '../lib/earnStake';
import { SIZES, levMarkets, levPlan, levPnl, levOpen, levBuy, levClose, readLev } from '../lib/leverage';
import '../styles/leverage.css';

// ⚡ REAL LEVERAGE — the Perps building's REAL-money door (owner, 2026-10-23: "too many damn steps to do perps with coinbase — find another
// way"): a Jupiter Lend loan from your own wallet — lock SOL / BTC / JUP, borrow USDC, buy more with it → 1.3–1.7× long with a liquidation
// price, two signatures, no account, no KYC, no link-out (backend/lend_borrow.py · DECISIONS #7). Not a perp: interest instead of funding,
// longs only (Jupiter has no stable-collateral vaults to short with). The paper desk below keeps 50× shorts for practice.
const px = v => (v >= 1000 ? `$${Math.round(v).toLocaleString('en-US')}` : v >= 1 ? `$${v.toFixed(2)}` : `$${Number(v || 0).toPrecision(3)}`);
const sgn = v => `${Number(v) < 0 ? '−' : '+'}${cash(Math.abs(Number(v) || 0))}`;

export function RealLeverage({ coin = '', devAddress = '' }) {   // devAddress: the /dev preview only
  const { wallet, provider, connect } = useWallet() || {}; const addr = (wallet?.chain === 'solana' ? wallet.address : '') || devAddress;
  const [mk, setMk] = useState(null); const [pick, setPick] = useState(''); const [usd, setUsd] = useState(25); const [lev, setLev] = useState(1.5);
  const [st, setSt] = useState(''); const [busy, setBusy] = useState(false); const [mine, setMine] = useState([]);
  const load = useCallback(() => levMarkets(addr).then(setMk).catch(() => {}), [addr]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (!busy) setMine(addr ? readLev(addr) : []); }, [addr, busy]);
  const rows = mk?.markets || []; const m = rows.find(r => r.coin === (pick || coin)) || rows[0];
  const levs = m ? [...[1.3, 1.5].filter(l => l < m.maxLev), m.maxLev] : [1.3, 1.5];
  const L = m ? Math.min(lev, m.maxLev) : lev; const p = levPlan(m, usd, L);
  const exp = useGlide(p?.expUsd || 0);
  const priceOf = c => rows.find(r => r.coin === c)?.price;
  const known = new Set(mine.map(r => r.nftId)); const elsewhere = (mk?.positions || []).filter(x => !known.has(x.nftId));
  const run = async (fn, ok) => {
    if (!wallet?.address || !provider) { await connect?.('solana'); return; }
    setBusy(true);
    try { await fn(); toast.success(ok); load(); } catch (e) { toast.error(e.message); } finally { setSt(''); setBusy(false); }
  };
  const go = () => run(() => levOpen({ provider, address: addr, m, usd, lev: L, onStatus: setSt }), `⚡ ${L}× long ${m.coin} is open — liquidated at ${px(p.liq)}`);
  const step = st.startsWith('②') ? 2 : st.startsWith('①') ? 1 : 0;
  const rail = p ? Math.max(4, Math.min(92, (p.liq / (m.price * 1.08)) * 100)) : 0;
  if (!m) return <section className="lv" data-testid="real-leverage"><p className="lv-dim">{mk ? 'Jupiter Lend has no leverage market open right now.' : 'Reading Jupiter Lend…'}</p></section>;
  return <section className="lv" data-testid="real-leverage">
    <header className="lv-head"><span><em>⚡ REAL LEVERAGE · YOUR WALLET SIGNS · NO ACCOUNT</em><b>Long {m.coin} up to {m.maxLev}× on Jupiter Lend</b></span>
      <i className="lv-apr" data-tip="What the borrowed USDC costs a year on Jupiter Lend right now (instead of funding)">borrow {m.borrowApr}%/yr</i></header>
    <div className="m-seg lv-seg" role="radiogroup" aria-label="Coin">{rows.map(r => <button key={r.coin} type="button" role="radio" aria-checked={r.coin === m.coin} className={r.coin === m.coin ? 'active' : ''}
      onClick={() => setPick(r.coin)} data-tip={`${r.coin} at ${px(r.price)} · up to ${r.maxLev}× · ${cash(r.borrowableUsd)} left to borrow`} data-testid={`lv-c-${r.coin}`}><b>{r.coin}</b><small>{px(r.price)}</small></button>)}</div>
    <div className="lv-pick">
      <span className="m-seg" role="radiogroup" aria-label="You lock">{SIZES.map(s => <button key={s} type="button" role="radio" aria-checked={usd === s} className={usd === s ? 'active' : ''} onClick={() => setUsd(s)}
        data-tip={`Lock $${s} of ${m.coin} as collateral`} data-testid={`lv-u-${s}`}>${s}</button>)}</span>
      <span className="m-seg" role="radiogroup" aria-label="Leverage">{levs.map(l => <button key={l} type="button" role="radio" aria-checked={L === l} className={L === l ? 'active' : ''} onClick={() => setLev(l)}
        data-tip={`${l}×: borrow ${Math.round((l - 1) * 100)}% of what you lock and buy ${m.coin} with it`} data-testid={`lv-l-${l}`}>{l}×</button>)}</span>
    </div>
    {p ? <div className="lv-pic">
      <div className="lv-stack" data-tip={`You lock ${cash(p.usd)} · Jupiter lends ${cash(p.debt)} · you hold ${cash(p.expUsd)} of ${m.coin}`}>
        <s className="lv-lent" /><s className="lv-own" style={{ transform: `scaleX(${p.usd / p.expUsd})` }} /><small>YOURS {cash(p.usd)}</small><small>LENT {cash(p.debt)}</small></div>
      <div className="lv-rail" data-tip={`Liquidated if ${m.coin} falls to ${px(p.liq)} — ${p.toLiqPct.toFixed(1)}% below now (Jupiter takes a ${m.penalty}% penalty)`}>
        <s className="lv-zone" style={{ transform: `scaleX(${rail / 100})` }} /><i className="lv-liq" style={{ left: `${rail}%` }}>☠</i><i className="lv-now" style={{ left: `${(1 / 1.08) * 100}%` }} /></div>
      <div className="lv-nums">
        <span><em>YOU HOLD</em><b className="m-num" key={Math.round(p.expUsd)}>{cash(exp)}</b><small>{p.exposure.toPrecision(4)} {m.coin}</small></span>
        <span className="is-dn"><em>LIQUIDATED AT</em><b className="m-num">{px(p.liq)}</b><small>−{p.toLiqPct.toFixed(1)}% from {px(m.price)}</small></span>
        <span><em>COSTS</em><b className="m-num">{cash(p.dayCost)}</b><small>a day in interest</small></span>
      </div></div> : null}
    <ol className="lv-steps" aria-label="Steps">{[`LOCK + BORROW ${p ? cash(p.debt) : ''}`, `BUY ${m.coin}`].map((t, i) => <li key={t} className={step === i + 1 ? 'is-on' : step > i + 1 ? 'is-done' : ''}><b>{i + 1}</b>{t}</li>)}</ol>
    <button type="button" className="m-btn m-go lv-go" disabled={busy || !p || p.tooSmall} onClick={go} data-testid="lv-go"
      data-tip={p?.tooSmall ? `Jupiter lends at least $${m.minDebt} — lock $${p.minUsd}+ at ${L}×` : `Two signatures: ① lock ${cash(usd)} of ${m.coin} + borrow ${cash(p?.debt)} USDC ② buy ${m.coin} with it`}>
      {busy ? st || 'Working…' : !addr ? '🔌 Connect wallet to go real' : p?.tooSmall ? `Min $${p.minUsd} at ${L}×` : `⚡ GO ${L}× LONG ${m.coin} · ${cash(usd)}`}</button>
    {mine.length || elsewhere.length ? <ol className="lv-pos">{mine.map((r, i) => { const v = levPnl(r, priceOf(r.coin)); return <li key={r.nftId} className={(v?.pnl ?? 0) >= 0 ? 'is-up' : 'is-dn'} style={{ '--i': i }} data-testid={`lv-pos-${r.nftId}`}>
      <b className="lv-tag">▲ {r.coin} {r.lev}×</b>
      <span className="lv-n"><em className="m-num">{v ? sgn(v.pnl) : '—'}</em><small>{v ? `${v.pnlPct >= 0 ? '+' : ''}${v.pnlPct.toFixed(1)}% · interest ${cash(v.interest)}` : 'reading the price…'}</small></span>
      <span className="lv-meter" data-tip={`Liquidated at ${px(r.liq)}`}><u><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, (v?.toLiqPct || 0) / 45))})` }} /></u><small>{v ? `${v.toLiqPct.toFixed(1)}% to liq` : ''}</small></span>
      <span className="lv-acts">{!r.bought ? <button type="button" className="m-btn" disabled={busy} onClick={() => run(() => levBuy({ provider, address: addr, rec: r, onStatus: setSt }), `⚡ Bought ${r.coin} — ${r.lev}× is on`)}
        data-tip="Step ② didn't finish: the borrowed USDC is in your wallet — buy the coin with it" data-testid={`lv-buy-${r.nftId}`}>② Buy {r.coin}</button> : null}
        <button type="button" className="m-btn" disabled={busy} onClick={() => run(() => levClose({ provider, address: addr, rec: r, price: priceOf(r.coin), onStatus: setSt }), `✅ ${r.coin} ${r.lev}× closed — collateral back in your wallet`)}
          data-tip="① sell enough to repay ② repay all + unlock all — the rest comes back to your wallet" data-testid={`lv-close-${r.nftId}`}>Close</button></span></li>; })}
      {elsewhere.map(x => <li key={x.nftId} className="is-up"><b className="lv-tag">▲ {x.coin} #{x.nftId}</b><span className="lv-n"><small>opened on another device — close repays from the USDC in your wallet</small></span><span />
        <span className="lv-acts"><button type="button" className="m-btn" disabled={busy} onClick={() => run(() => levClose({ provider, address: addr, rec: { ...x, bought: false }, onStatus: setSt }), `✅ #${x.nftId} closed`)} data-tip="Repay all + unlock all" data-testid={`lv-close-${x.nftId}`}>Close</button></span></li>)}</ol> : null}
    <p className="lv-lede">⚠ Leverage cuts both ways: at {L}× a {p ? p.toLiqPct.toFixed(0) : '—'}% drop liquidates the loan and Jupiter keeps a {m.penalty}% penalty. Not a perp: a Jupiter Lend loan in your own wallet, longs only, interest instead of funding. FEELESS never holds it.</p>
  </section>;
}

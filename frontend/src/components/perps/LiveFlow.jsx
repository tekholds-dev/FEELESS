import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { useGlide } from '../../lib/useGlide';
import { useTicker, flowOf, whales, moveOf, rvol, WHALE_USD } from '../../lib/cbFeed';

// 🌊 LIVE FLOW — the real-time order flow beside your positions (every number from real prints, re-read 4× a second):
// · TAKER PRESSURE — who is hitting the book: buy vs sell $ over 60 s (the hero) and 5 min (Coinbase trades; `side` = the maker's).
// · MOMENTUM — the move over 1 m / 5 m / 15 m / 1 h from 1-second samples · RVOL — the last hour's realized volatility, annualized.
// · 🐋 WHALE PRINTS — every trade ≥ WHALE_USD as it lands (newest flashes in).
// · 🏆 JUPITER THIS WEEK — the market's perps volume + the top traders by P&L (tap one → their case file).
const big = v => (v == null ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${v.toFixed(0)}`);
const pc = (v, d = 2) => (v == null || !Number.isFinite(v) ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(d)}%`);
const ago = ms => (ms < 60000 ? `${Math.max(0, Math.round(ms / 1000))}s` : `${Math.round(ms / 60000)}m`);

export function LiveFlow({ asset }) {
  const tk = useTicker(asset); const now = Date.now();
  const f60 = flowOf(tk?.flow, 60000, now); const f5 = flowOf(tk?.flow, 300000, now);
  const share = useGlide(f60.share == null ? 50 : Math.round(f60.share * 1000) / 10, 400);
  const mv = [['1M', 60000], ['5M', 300000], ['15M', 900000], ['1H', 3600000]].map(([l, ms]) => [l, moveOf(tk?.px, ms, now)]);
  const vol = rvol(tk?.px); const wh = whales(tk?.flow, WHALE_USD[asset] || 25000);
  const [lead, setLead] = useState(null);
  useEffect(() => { let on = true; setLead(null);
    const load = () => fetch(apiUrl(`/api/reputation/familia/perps-real/leaders?asset=${asset}`)).then(r => (r.ok ? r.json() : null)).then(x => on && x && setLead(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 300000); return () => { on = false; clearInterval(t); }; }, [asset]);
  const topPnl = Math.max(1, ...((lead?.pnl || []).map(r => Math.abs(r.pnl || 0))));
  const open = w => window.dispatchEvent(new CustomEvent('feeless:investigate', { detail: w }));
  return <aside className={`lf ${f60.share == null ? '' : f60.share >= 0.5 ? 'is-up' : 'is-dn'}`} data-testid="live-flow">
    <header className="lf-h"><b>🌊 LIVE FLOW</b><small>{asset} · TRUE PRINTS · {f60.n} / MIN</small></header>
    <div className="lf-press" data-tip="Taker pressure: the $ of market BUYS vs market SELLS hitting the book in the last 60 s (5 min under it)">
      <span className="lf-hero"><em>BUY PRESSURE · 60S</em><b className="m-num">{f60.share == null ? '—' : `${share.toFixed(0)}%`}</b></span>
      <span className="lf-amts"><small className="is-up m-num">▲ {big(f60.buy)}</small><small className="is-dn m-num">▼ {big(f60.sell)}</small></span>
      <div className="lf-split" aria-hidden="true"><s className="is-up" style={{ transform: `scaleX(${share / 100})` }} /><s className="is-dn" style={{ transform: `scaleX(${1 - share / 100})` }} /></div>
      <div className="lf-split is-thin" aria-hidden="true" data-tip="5 min"><s className="is-up" style={{ transform: `scaleX(${f5.share ?? 0.5})` }} /><s className="is-dn" style={{ transform: `scaleX(${1 - (f5.share ?? 0.5)})` }} /></div>
    </div>
    <div className="lf-mv">{mv.map(([l, v]) => <span key={l} className={(v ?? 0) >= 0 ? 'is-up' : 'is-dn'} data-tip={`The move over the last ${l.toLowerCase()} of true prints`}><em>{l}</em><b className="m-num">{pc(v, 2)}</b>
      <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, Math.abs(v || 0) / 2)})` }} /></u></span>)}
      <span className={vol != null && vol > 80 ? 'is-hot' : ''} data-tip="Realized volatility of the last hour of prints, annualized — how wild the tape is right now"><em>RVOL</em><b className="m-num">{vol == null ? '—' : `${vol.toFixed(0)}%`}</b>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, (vol || 0) / 150)})` }} /></u></span></div>
    <div className="lf-whales" data-tip={`Every single trade of ${big(WHALE_USD[asset])}+ as it prints`}><em>🐋 WHALE PRINTS · {big(WHALE_USD[asset])}+</em>
      {wh.length ? <ol>{wh.map((x, i) => <li key={x.t + x.usd} className={`${x.buy ? 'is-up' : 'is-dn'} ${i === 0 && now - x.t < 4000 ? 'is-new' : ''}`}>
        <b>{x.buy ? '▲ BUY' : '▼ SELL'}</b><i className="m-num">{big(x.usd)}</i><small className="m-num">{ago(now - x.t)}</small></li>)}</ol>
        : <p className="lf-dim">waiting for the first {big(WHALE_USD[asset])}+ print…</p>}</div>
    <div className="lf-lead"><em>🏆 JUPITER {asset}-PERP · THIS WEEK</em><b className="m-num">{lead?.vol ? `${big(lead.vol)} traded` : '…'}</b>
      <ol>{(lead?.pnl || []).map((r, i) => <li key={r.wallet} style={{ '--i': i }}><button type="button" onClick={() => open(r.wallet)} data-tip={`${r.wallet} · ${big(r.vol)} volume — open their case file`}>
        <i>{i + 1}</i><span>{r.wallet.slice(0, 4)}…{r.wallet.slice(-4)}</span><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.abs(r.pnl || 0) / topPnl})` }} /></u>
        <b className={`m-num ${(r.pnl || 0) >= 0 ? 'is-up' : 'is-dn'}`}>{(r.pnl || 0) >= 0 ? '+' : '−'}{big(Math.abs(r.pnl || 0))}</b></button></li>)}</ol></div>
  </aside>;
}

import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { FuseLeg } from './FusePanel';
import '../styles/fuseLab.css';

// ⚛️ FUSE LAB: browse the chain's real pools, tick 2–6, and see live how FEELESS auto-weighs them (fee APR × depth,
// 10–70% each) and where one SOL amount goes. Preview is read-only; "Fuse in" = one normal wallet-signed swap per pool.
const LENSES = [['popular', 'Popular'], ['yield', 'Top yield'], ['deep', 'Deepest'], ['new', 'New 72h']];
const MAX = 6;
const usd = v => (v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${(v || 0).toFixed(v < 10 ? 2 : 0)}`);
const pct = v => (Math.abs(v) >= 1000 ? `${(1 + v / 100).toFixed(1)}x` : `${v >= 0 ? "+" : ""}${(v || 0).toFixed(1)}%`);
const apr = v => (v >= 1000 ? `${(v / 100).toFixed(0)}x` : `${Math.round(v || 0)}%`);

export function FuseLab({ chain = 'solana' }) {
  const [lens, setLens] = useState('popular');
  const [pools, setPools] = useState(null);
  const [q, setQ] = useState('');
  const [picked, setPicked] = useState([]);
  const [sol, setSol] = useState('1');
  const [prev, setPrev] = useState(null);
  const [err, setErr] = useState('');
  const [going, setGoing] = useState(false);

  useEffect(() => { let alive = true; setPools(null);
    fetch(apiUrl(`/api/reputation/fuses/discover?lens=${lens}&chain=${chain}`)).then(r => (r.ok ? r.json() : { pools: [] })).then(d => alive && setPools(d.pools || [])).catch(() => alive && setPools([]));
    return () => { alive = false; }; }, [lens, chain]);

  const key = picked.map(p => p.pairAddress).join(',');
  useEffect(() => {
    setGoing(false);
    if (picked.length < 2) { setPrev(null); setErr(''); return undefined; }
    const t = setTimeout(() => fetch(apiUrl('/api/reputation/fuses/preview'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pools: picked.map(p => ({ chainId: p.chainId, pairAddress: p.pairAddress, symbol: p.symbol })), sol: Number(sol) || 0 }) })
      .then(async r => { const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Preview failed'); setPrev(d); setErr(''); }).catch(e => setErr(e.message)), 250);
    return () => clearTimeout(t);
  }, [key, sol]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => { const s = q.trim().toLowerCase(); return (pools || []).filter(p => !s || `${p.symbol}/${p.quote} ${p.dex}`.toLowerCase().includes(s)); }, [pools, q]);
  const isOn = p => picked.some(x => x.pairAddress === p.pairAddress);
  const toggle = p => setPicked(list => (isOn(p) ? list.filter(x => x.pairAddress !== p.pairAddress) : list.length >= MAX ? list : [...list, p]));

  return <section className="m-card m-live fl" data-testid="fuse-lab">
    <header className="fl-head">
      <div><span className="m-label">⚛️ FUSE LAB</span><h3>Many pools. One buy.</h3>
        <p className="m-dim">Pick 2–6 live pools. FEELESS weighs them for you and shows exactly where your SOL goes.</p></div>
      <span className="m-chip ok fl-chain"><i />{chain.toUpperCase()}</span>
    </header>
    <ol className="fl-steps"><li><b>1</b><span>Pick pools</span></li><li><b>2</b><span>Auto-weigh<small>fee APR × depth · 10–70% each</small></span></li><li><b>3</b><span>One amount in<small>split into swaps you sign</small></span></li></ol>
    <div className="fl-body">
      <div className="fl-browse">
        <div className="fl-tools"><div className="m-seg" role="radiogroup" aria-label="Pool lens">{LENSES.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)}>{l}</button>)}</div>
          <input className="m-input fl-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Filter $SYMBOL or DEX" aria-label="Filter pools" /></div>
        <div className="fl-list" role="listbox" aria-multiselectable="true" aria-label="Pools">
          {pools == null ? Array.from({ length: 6 }, (_, i) => <div key={i} className="fl-row is-ghost" />)
            : !shown.length ? <p className="m-dim fl-empty">No live pools in this lens right now.</p>
            : shown.map(p => { const on = isOn(p); const full = !on && picked.length >= MAX;
              return <button type="button" role="option" aria-selected={on} key={p.pairAddress} className={`fl-row ${on ? 'is-on' : ''}`} disabled={full} onClick={() => toggle(p)} data-testid={`fl-pool-${p.pairAddress}`} title={full ? `Max ${MAX} pools` : undefined}>
                <span className="fl-check" aria-hidden="true">{on ? '✓' : '+'}</span>
                <span className="fl-logo">{p.logo ? <img src={p.logo} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} /> : (p.symbol || '?').slice(0, 2)}</span>
                <span className="fl-name"><b>{p.symbol}<small>/{p.quote}</small></b><em>{p.dex}</em></span>
                <span className="fl-cell"><small>LIQ</small><b className="m-num">{usd(p.liquidityUsd)}</b></span>
                <span className="fl-cell"><small>VOL 24H</small><b className="m-num">{usd(p.volume24h)}</b></span>
                <span className="fl-cell"><small>APR EST</small><b className="m-num m-pos">{apr(p.aprEst)}</b></span>
                <span className="fl-cell"><small>24H</small><b className={`m-num ${p.change24h >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(p.change24h)}</b></span>
              </button>; })}
        </div>
      </div>
      <aside className="fl-mix" aria-live="polite">
        <div className="fl-mix-head"><span className="m-label">YOUR FUSE · {picked.length}/{MAX}</span>{picked.length > 0 && <button type="button" className="m-btn fl-clear" onClick={() => setPicked([])}>Clear</button>}</div>
        {picked.length < 2 ? <div className="fl-hint"><b>{picked.length ? 'Pick one more pool' : 'Tap pools on the left'}</b><small>The preview builds live as you pick.</small></div> : <>
          <label className="m-field fl-amt"><span>SOL in</span><div className="fl-amt-row"><input className="m-input m-num" inputMode="decimal" value={sol} onChange={e => setSol(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="SOL amount" />
            <div className="m-seg">{['0.5', '1', '5'].map(v => <button type="button" key={v} className={sol === v ? 'active' : ''} onClick={() => setSol(v)}>{v}</button>)}</div></div>
            {prev && <small className="m-dim">≈ {usd(prev.usd)} at {usd(prev.solUsd)}/SOL</small>}</label>
          {err ? <div className="m-note bad">{err}</div> : !prev ? <div className="fl-row is-ghost" /> : <>
            <div className="fl-bar">{prev.legs.map(l => <i key={l.pairAddress} style={{ flexGrow: l.weight }} title={`${l.symbol} ${l.weight}%`}><span>{l.symbol} {Math.round(l.weight)}%</span></i>)}</div>
            <ul className="fl-legs">{prev.legs.map(l => <li key={l.pairAddress}><b>{l.symbol}</b><span className="m-num">{l.weight.toFixed(0)}%</span><span className="m-num">{l.sol} SOL</span><span className="m-num m-dim">{usd(l.usd)}</span><span className="m-num m-pos" title="Est. fee yield per day at this size">{usd(l.dailyUsd)}/d</span></li>)}</ul>
            <div className="fl-kpis">
              <div className="m-stat"><small>GRADE</small><b className={`fl-grade g-${prev.score.grade}`} title={prev.score.parts.map(p => `${p.part}: ${p.why}`).join('\n')}>{prev.score.grade}</b></div>
              <div className="m-stat"><small>BLENDED APR</small><b className="m-num m-pos">{apr(prev.blendedAprPct)}</b></div>
              <div className="m-stat"><small>EST / DAY</small><b className="m-num">{usd(prev.dailyUsd)}</b></div>
            </div>
            <details className="fl-why"><summary>Why these weights?</summary><p>Each pool scores <b>fee APR</b> (24h volume × 0.25% ÷ liquidity, capped 400%) × <b>depth</b> (log of liquidity). Shares are clamped to 10–70% so one pool never runs the fuse. Grade = depth + healthy turnover + calm 24h moves + forensics safety.</p>
              <ul>{prev.score.parts.map(p => <li key={p.part}><span>{p.part}</span><b className="m-num">{p.points}</b><small>{p.why}</small></li>)}</ul></details>
            {!going ? <button type="button" className="m-btn primary m-go wide" disabled={!(Number(sol) > 0)} onClick={() => setGoing(true)} data-testid="fl-go">⚡ Fuse in {Number(sol) || 0} SOL</button>
              : <div className="fl-go">{prev.legs.map(l => <div key={l.pairAddress} className="fz-split"><span>{l.symbol} · {Math.round(l.weight)}%</span><FuseLeg leg={l} sol={l.sol} /></div>)}
                <small className="m-dim">Each pool is its own swap your wallet signs · normal FEELESS fees.</small></div>}
            <small className="m-dim fl-fine">Preview only — nothing moves until you sign. Yields are estimates from the last 24h.</small>
          </>}
        </>}
      </aside>
    </div>
  </section>;
}

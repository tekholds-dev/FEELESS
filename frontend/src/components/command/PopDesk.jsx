import React, { useEffect, useState } from 'react';
import '../../styles/popDesk.css';

// 📉 PROOF OF PERPS: both minds read the live market on their own, and a paper trade runs on true prices only when they agree. No real order is ever sent from here.
const roeText = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(2)}%`;

// Where the price sits between the stop and the take profit: the same read a trader wants in five seconds.
function Band({ t }) {
  const mv = ((t.mark / t.entry - 1) * 100) * (t.side === 'long' ? 1 : -1); const span = t.sl + t.tp; const at = Math.max(0, Math.min(1, (mv + t.sl) / span));
  return <span className="pop-band" data-tip={`Stop −${t.sl}% · take profit +${t.tp}% of price · now ${mv >= 0 ? '+' : ''}${mv.toFixed(2)}%`}><u><s style={{ transform: `scaleX(${t.sl / span})` }} /><i style={{ left: `${at * 100}%` }} /></u><small>STOP −{t.sl}%</small><small>TAKE +{t.tp}%</small></span>;
}

function Calls({ calls }) {
  return <ul className="pop-calls">{(calls || []).map(c => <li key={c.mind} className={`m-glass is-m${c.mind}`}><b>{c.name}</b>{c.side ? <em className={`is-${c.side}`}>{c.side} {c.market} · {c.lev}×</em> : <em>no trade</em>}<small>{c.why || 'gave no usable call'}</small></li>)}</ul>;
}

function Live({ t }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const c = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(c); }, []);
  const mins = Math.max(0, Math.floor((now - t.openedAt) / 60));
  return <article className={`pop-live m-glass m-live is-${t.roePct >= 0 ? 'up' : 'dn'}`} data-testid="pop-live"><header><em className={`pop-side is-${t.side}`}>{t.side}</em><b>{t.market}-PERP</b><small>{t.lev}× · paper · {mins} min</small></header>
    <b className="pop-roe m-num" key={t.mark}>{roeText(t.roePct)}</b>
    <Band t={t} />
    <div className="pop-nums"><span><em>ENTRY</em><b className="m-num">${Number(t.entry).toLocaleString()}</b></span><span><em>MARK</em><b className="m-num">${Number(t.mark).toLocaleString()}</b></span><span><em>☠ LIQ AT</em><b className="m-num">−{t.liqPct}%</b></span></div>
    <Calls calls={t.calls} /></article>;
}

export function PopDesk({ d, send, busy, err }) {
  const live = d?.popFolder; const rows = d?.popFolders || []; const done = rows.filter(r => !r.noTrade); const won = done.filter(r => r.won).length; const paper = done.reduce((a, r) => a + (r.pnlUsd || 0), 0);
  return <section className="pop" data-testid="pop-desk">
    <header className="pop-head m-glass"><span><b>📉 PROOF OF PERPS</b><small>Both minds must agree. True prices, paper fills: no real order is sent.</small></span>
      {live ? <button type="button" className="m-btn" disabled={busy} onClick={() => send('stop')} data-tip="Ends this PoP at the live price" data-testid="pop-stop">■ Stop</button>
        : <button type="button" className="m-btn m-go" disabled={busy} onClick={() => send('start')} data-tip="Each mind makes one small paid model call, then a paper trade runs if they agree" data-testid="pop-start">File a PoP</button>}</header>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <div className="pop-stats">{[['PROOFS', rows.length], ['TRADES', done.length], ['WON', done.length ? `${Math.round(100 * won / done.length)}%` : '—'], ['PAPER P/L', `${paper >= 0 ? '+' : '−'}$${Math.abs(paper).toFixed(2)}`]].map(([k, v]) => <span key={k} className="m-glass"><em>{k}</em><b className="m-num">{v}</b></span>)}</div>
    {live ? <Live t={live} /> : null}
    {rows.length ? <ol className="pop-list">{rows.map((r, i) => <li key={r.id} className={`m-glass ${r.noTrade ? 'is-none' : r.won ? 'is-up' : 'is-dn'}`} style={{ '--i': i }}><span><b>{r.noTrade ? 'No trade' : `${r.side} ${r.market}-PERP · ${r.lev}×`}</b><small>{new Date(r.at * 1000).toLocaleString()} · {r.why}</small></span>
      {r.noTrade ? null : <b className="m-num pop-roe-s">{roeText(r.roePct)}</b>}<Calls calls={r.calls} /></li>)}</ol>
      : !live ? <p className="dsk-note">No proofs yet. Type “file a PoP” in its chat, or tap the button.</p> : null}
  </section>;
}

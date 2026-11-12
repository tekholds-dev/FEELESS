import { boxRef } from '../../lib/boxRef';
import React, { useEffect, useState } from 'react';
import '../../styles/popDesk.css';
import { Ic3 } from '../../lib/icon3d';

// 📉 PROOF OF PERPS: both minds read the live market on their own, and a paper trade runs on true prices only when they agree. No real order is ever sent from here.
const roeText = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(2)}%`;

// Where the price sits between the stop and the take profit: the same read a trader wants in five seconds.
function Band({ t }) {
  const mv = ((t.mark / t.entry - 1) * 100) * (t.side === 'long' ? 1 : -1); const span = t.sl + t.tp; const at = Math.max(0, Math.min(1, (mv + t.sl) / span));
  return <span className="pop-band" data-tip={`Stop −${t.sl}% · take profit +${t.tp}% of price · now ${mv >= 0 ? '+' : ''}${mv.toFixed(2)}%`}><u><s style={{ transform: `scaleX(${t.sl / span})` }} /><i style={{ left: `${at * 100}%` }} /></u><small>STOP −{t.sl}%</small><small>TAKE +{t.tp}%</small></span>;
}

export function Calls({ calls }) {
  return <ul className="pop-calls">{(calls || []).map(c => <li key={c.mind} className={`m-glass is-m${c.mind}`}><b>{c.name}{c.changed ? ' · changed its call' : ''}</b>{c.side ? <em className={`is-${c.side}`}>{c.side} {c.market} · {c.lev}×</em> : <em>no trade</em>}<small>{c.why || 'gave no usable call'}</small></li>)}</ul>;
}

export function Live({ t }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const c = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(c); }, []);
  const mins = Math.max(0, Math.floor((now - t.openedAt) / 60));
  return <article className={`pop-live m-glass m-live is-${t.roePct >= 0 ? 'up' : 'dn'}`} data-testid="pop-live"><header><em className={`pop-side is-${t.side}`}>{t.side}</em><b>{t.market}-PERP</b><small>{t.lev}× · paper · {mins} min</small></header>
    <b className="pop-roe m-num" key={t.mark}>{roeText(t.roePct)}</b>
    <Band t={t} />
    <div className="pop-nums"><span><em>ENTRY</em><b className="m-num">${Number(t.entry).toLocaleString()}</b></span><span><em>MARK</em><b className="m-num">${Number(t.mark).toLocaleString()}</b></span><span><em>☠ LIQ AT</em><b className="m-num">−{t.liqPct}%</b></span></div>
    <Calls calls={t.calls} /></article>;
}

const CONVICTION = { blind: ['🕶 BLIND AGREE', 'Both minds picked this without seeing each other'], argued: ['🗣 ARGUED', 'They split at first, then agreed after reading each other. A weaker signal than a blind agree'], solo: ['☝ ONE MIND', 'One mind only, so nothing checked it'] };
const STATE = { waiting: '', passed: 'You passed. Its ghost keeps tracking what you skipped.', expired: 'Its 15 minutes ran out. Its ghost keeps tracking it.' };

// 💡 pPoP: the agreed trade as a card. Nothing is open: Run makes it a normal paper PoP at the live price, while the setup still holds.
export function ProposalCard({ c, send, busy }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const left = Math.max(0, c.expiresAt - now); const open = c.state === 'waiting' && left > 0; const room = Number(c.room || 0); const [tag, tip] = CONVICTION[c.conviction] || CONVICTION.solo;
  return <article className={`pop-live pop-card m-glass is-${c.roePct >= 0 ? 'up' : 'dn'}`} data-testid="pop-card"><header><em className="pop-tag"><Ic3 e="💡" /> PROPOSED</em><em className={`pop-side is-${c.side}`}>{c.side}</em><b>{c.market}-PERP</b><small>{c.lev}× · nothing open</small><em className="pop-tag is-how" data-tip={tip}>{tag}</em></header>
    <div className="pop-ghost"><span><em>IF IT WERE OPEN</em><b className="pop-roe m-num" key={c.mark}>{roeText(c.roePct)}</b></span>
      {open ? <span className="pop-clock" data-tip="After this it can no longer run"><em>{Math.floor(left / 60)}:{String(Math.floor(left % 60)).padStart(2, '0')} TO RUN IT</em><u><s style={{ transform: `scaleX(${left / 900})` }} /></u><em className={room >= 0.35 ? 'is-hot' : ''} data-tip="At half its way to the stop or take profit, Run is refused">{Math.round(room * 100)}% OF ITS ROOM USED</em><u className="is-room"><s style={{ transform: `scaleX(${Math.min(1, room * 2)})` }} /></u></span> : <small>{STATE[c.state] || STATE.expired}</small>}</div>
    <Band t={c} />
    <div className="pop-nums"><span><em>ENTRY</em><b className="m-num">${Number(c.entry).toLocaleString()}</b></span><span><em>MARK</em><b className="m-num">${Number(c.mark).toLocaleString()}</b></span><span><em>☠ LIQ AT</em><b className="m-num">−{c.liqPct}%</b></span></div>
    <Calls calls={c.calls} />
    {c.refused ? <p className="kd-err" role="alert" data-testid="pop-refused">⚠ {c.refused}</p> : null}
    {open ? <div className="pop-acts"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => send('adopt')} data-tip="Opens a paper PoP at the live price with these numbers. No real order is sent" data-testid="pop-run">▶ Run on paper</button>{c.alt ? <button type="button" className="m-btn" disabled={busy} onClick={() => send('adopt_alt')} data-tip="The minds split. This runs the other mind's call on paper instead" data-testid="pop-run-alt">▶ Run {c.alt.side} {c.alt.market} instead</button> : null}<button type="button" className="m-btn" disabled={busy} onClick={() => send('pass')} data-tip="Skips it. Its ghost still shows what would have happened" data-testid="pop-pass">Pass</button><a className="m-btn" href="https://crypto.com/app" target="_blank" rel="noopener noreferrer" data-tip="Agents only propose perps. To trade this for real, place it yourself on Crypto.com. FEELESS sends nothing" data-testid="pop-cdc">Try it on Crypto.com ↗</a></div> : null}
  </article>;
}

// Did their proposals work? The only way to learn if a blind agree beats an argued one, from their own record.
function ProposalScore({ rows }) {
  const closed = rows.filter(r => r.ghost); if (!closed.length) return null;
  return <div className="pop-score" data-testid="pop-score"><em>THEIR PROPOSALS</em>{Object.entries(CONVICTION).map(([k, [tag]]) => { const xs = closed.filter(r => r.conviction === k); return xs.length ? <span key={k} className="m-chip">{tag} {xs.filter(r => r.won).length}/{xs.length}</span> : null; })}</div>;
}
const popBox = boxRef([520]);   // 📐 its own width, no @container (lib/boxRef.js)
export function PopDesk({ d, send, busy, asking = false, err, children = null, price = '' }) {
  const live = d?.popFolder; const card = d?.popCard; const rows = d?.popFolders || []; const done = rows.filter(r => !r.noTrade && !r.proposal); const won = done.filter(r => r.won).length; const paper = done.reduce((a, r) => a + (r.pnlUsd || 0), 0);
  return <section ref={popBox} className="pop" data-testid="pop-desk">
    <header className="pop-head m-glass"><span><b><Ic3 e="📉" /> PROOF OF PERPS</b><small>Both minds must agree. True prices, paper fills: no real order is sent.</small></span>
      <span className="pop-head-acts">{!card ? <button type="button" className="m-btn" disabled={busy} onClick={() => send('propose')} data-tip="The same paid call, filed as a card. Nothing opens until you press Run. Or type propose a perp" data-testid="pop-propose"><Ic3 e="💡" /> Propose</button> : null}{live ? <button type="button" className="m-btn" disabled={busy} onClick={() => send('stop')} data-tip="Ends this PoP at the live price" data-testid="pop-stop">■ Stop</button>
        : <button type="button" className="m-btn m-go" disabled={busy} onClick={() => send('start')} data-tip="Each mind reads its own sources against the chart and makes one small paid model call. A paper trade runs if they agree. Or type file a perp" data-testid="pop-start">File a PoP{price ? ` · ${price}` : ''}</button>}</span></header>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <div className="pop-stats">{[['PROOFS', rows.filter(r => !r.proposal).length], ['TRADES', done.length], ['WON', done.length ? `${Math.round(100 * won / done.length)}%` : '—'], ['PAPER P/L', `${paper >= 0 ? '+' : '−'}$${Math.abs(paper).toFixed(2)}`]].map(([k, v]) => <span key={k} className="m-glass"><em>{k}</em><b className="m-num">{v}</b></span>)}</div>
    {asking ? <p className="pop-asking m-glass" role="status" data-testid="pop-asking"><i aria-hidden="true" />{d?.popRead ? 'Each mind is reading sites in its own window. Watch its monitors…' : 'Each mind is reading its own sources against the chart…'}</p> : null}
    <ProposalScore rows={rows} />
    {children}
  </section>;
}

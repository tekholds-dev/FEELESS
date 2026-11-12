import React, { useEffect, useState } from 'react';
import { HqVitals } from './ccTabInfo';

// 🎯 THE REAL-BID DOOR (owner 2026-11-11: "kalshi signed in with $10, they should be able to bid"). Off until he switches it on. His own Kalshi
// API key (saved in this agent's Keys) sends a LIMIT order to his own Kalshi account only when both minds backed the same market and side and
// every guard passes (backend kalshi_bid.py). Approve each (default) waits for his tap on the ticket; Auto sends inside his caps.
const STATUS = { waiting: 'Waiting for your tap', resting: 'On Kalshi, waiting to fill', filled: 'Filled', sent: 'Sent', refused: 'Not sent', failed: 'Kalshi refused it', skipped: 'You skipped it' };

export function KalshiDoor({ cat, work }) {
  const [s, setS] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [f, setF] = useState(null);
  const load = () => work(cat.id, { op: 'kalshi_state' }).then(j => { setS(j); setF(j.cfg); }).catch(e => setErr(e.message));
  useEffect(() => { load(); }, [cat.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const save = async next => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'kalshi_cfg', tools: next }); setS(x => ({ ...x, ...j })); setF(j.cfg); } catch (e) { setErr(e.message); } setBusy(false); };
  if (!s || !f) return <p className="dsk-note" data-testid="kd-wait">{err || 'Reading the Kalshi door…'}</p>;
  const on = f.on && s.key; const bal = s.balance;
  return <section className={`kd m-glass${on ? ' is-on' : ''}`} data-testid="kalshi-door">
    <header className="kd-h"><span><b>🎯 REAL BIDS ON KALSHI</b><small>{!s.key ? 'Save your Kalshi API key in this agent’s Keys (key id, a space, then the private key) to use it.' : on ? (f.mode === 'auto' ? 'On · it bids by itself inside your caps when both minds agree.' : 'On · each bid waits for your tap.') : 'Off · its PoB stays research and free chips.'}</small></span>
      <label className="m-toggle" data-tip={s.key ? 'Real money on your own Kalshi account' : 'Save the key first'}><input type="checkbox" checked={!!f.on} disabled={busy || !s.key} onChange={e => save({ ...f, on: e.target.checked })} data-testid="kd-on" />{f.on ? 'On' : 'Off'}</label></header>
    <HqVitals tiles={[{ label: 'Kalshi balance', value: bal, pre: '$', dec: 2, tone: 'up', tip: s.balanceErr || 'Read live from your Kalshi account' }, { label: 'Spent today', value: s.spentToday, pre: '$', dec: 2, of: f.dayUsd, tone: 'gold' }, { label: 'Per bid cap', value: f.bidUsd, pre: '$', dec: 2, of: s.hard.bidUsd, tone: 'violet' }, { label: 'Bids', value: (s.bids || []).filter(b => ['resting', 'filled', 'sent'].includes(b.status)).length, tone: 'pink' }]} />
    {s.balanceErr ? <p className="dsk-note" role="alert" data-testid="kd-balerr">Kalshi: {s.balanceErr}</p> : null}
    <div className="kd-set">
      <span className="m-seg" role="radiogroup" aria-label="How a bid goes out">{[['approve', 'Approve each', 'Every bid waits for your tap on its ticket'], ['auto', 'Auto in caps', 'It sends by itself, never over your caps']].map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={f.mode === k} className={f.mode === k ? 'active' : ''} disabled={busy} onClick={() => save({ ...f, mode: k })} data-tip={tip} data-testid={`kd-mode-${k}`}>{l}</button>)}</span>
      {[['bidUsd', 'Per bid $', s.hard.bidUsd, 'Most one bid may spend'], ['dayUsd', 'Per day $', s.hard.dayUsd, 'Most all its bids may spend in 24 h'], ['floorUsd', 'Keep at least $', 10000, 'It never bids your Kalshi balance below this'], ['minConf', 'Both minds ≥ %', 100, 'Each mind must be at least this sure']].map(([k, l, hi, tip]) => <label key={k} className="kd-num" data-tip={tip}><small>{l}</small><input className="m-input" type="number" min={0} max={hi} step={k === 'minConf' ? 1 : 0.5} value={f[k]} onChange={e => setF(x => ({ ...x, [k]: e.target.value }))} onBlur={() => save(f)} disabled={busy} data-testid={`kd-${k}`} /></label>)}
    </div>
    {(s.bids || []).length ? <ol className="kd-bids" aria-label="Its real bids" data-testid="kd-bids">{s.bids.slice(0, 6).map((b, i) => <li key={b.id || i} className={`is-${b.status}`} style={{ '--i': i }}><b>{b.side?.toUpperCase()} · {b.title || b.ticker}</b><small>{STATUS[b.status] || b.status}{b.usd ? ` · ${b.count} × ${Number(b.price).toFixed(2)} = $${Number(b.usd).toFixed(2)}` : ''}{b.why && !b.usd ? ` · ${b.why}` : ''}</small></li>)}</ol> : null}
    {err ? <p className="dsk-note" role="alert">{err}</p> : null}
  </section>;
}

export function KalshiTicket({ t: t0, catId, work, onDone }) {
  const [t, setT] = useState(t0); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const act = async op => { setBusy(op); setErr(''); try { const j = await work(catId, { op, job: t.id }); setT(j.ticket); onDone?.(j); } catch (e) { setErr(e.message); } setBusy(''); };
  return <section className={`kd-ticket m-glass is-${t.status}`} data-testid="kalshi-ticket"><span className="kd-tk-h"><b>🎯 KALSHI · {t.side?.toUpperCase()} · {t.title}</b><small className="m-num">{t.ticker} · ask {t.price != null ? Number(t.price).toFixed(2) : '—'} · minds {(t.conf || []).join('% / ')}%</small></span>
    <small className="kd-tk-why">{(t.why || []).filter(Boolean).join(' · ')}</small>
    {t.status === 'waiting' ? <span className="kd-tk-go"><button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('kalshi_bid')} data-tip="Re-reads the price and your balance, checks every cap, then sends ONE limit order on your own Kalshi key" data-testid="kd-approve">{busy === 'kalshi_bid' ? 'Sending…' : 'Approve real bid'}</button><button type="button" className="m-btn" disabled={!!busy} onClick={() => act('kalshi_skip')} data-tip="Nothing is sent" data-testid="kd-skip">Skip</button></span>
      : <b className={`kd-tk-st is-${t.status}`} role="status" data-testid="kd-status">{STATUS[t.status] || t.status}{t.usd ? ` · ${t.count} × ${Number(t.price).toFixed(2)} = $${Number(t.usd).toFixed(2)}` : ''}{t.why && !t.usd ? ` · ${t.why}` : ''}</b>}
    {err ? <p className="dsk-note" role="alert">{err}</p> : null}
  </section>;
}

import { ActBtn } from '../ActBtn';
import React, { useEffect, useState } from 'react';
import { HqVitals } from './ccTabInfo';

// 🎯 THE REAL-BID DOOR (owner 2026-11-11: "kalshi signed in with $10, they should be able to bid"). His own Kalshi API key (saved in this
// agent's Keys) sends a LIMIT order to his own Kalshi account only when both minds backed the same market and side and every guard passes
// (backend kalshi_bid.py). No On switch (owner 2026-11-15: "i shouldnt have to cut on pob or kalshi"): a PoB he asks for bids at once, inside
// his caps. AUTO is the one switch: on, his scheduled auto runs bid by themselves too; off, their tickets wait for his tap.
const STATUS = { waiting: 'Waiting for your tap', resting: 'On Kalshi, waiting to fill', filled: 'Filled', sent: 'Sent', refused: 'Not sent', failed: 'Kalshi refused it', skipped: 'You skipped it', canceled: 'Canceled on Kalshi, nothing filled' };
const hhmm = at => new Date(at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
// ✅ what Kalshi itself said when the agent read the order back (owner 2026-11-14: "they should check and confirm the bid on kalshi works")
const resultLine = b => (b.outcome ? `🏁 Kalshi settled ${String(b.result || '').toUpperCase()} · this bid ${b.outcome === 'won' ? 'WON' : 'lost'}` : b.livePx != null ? `Now ${Number(b.livePx).toFixed(2)} on Kalshi (bid at ${Number(b.price).toFixed(2)})` : '');
const confirmLine = b => (b.confirmedAt ? `✅ Kalshi confirmed ${b.filled ?? 0} of ${b.count} filled · ${hhmm(b.confirmedAt)}` : b.confirmErr ? `⚠ Not confirmed yet: ${b.confirmErr}` : '');

export function KalshiDoor({ cat, work }) {
  const [s, setS] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [f, setF] = useState(null);
  const load = () => work(cat.id, { op: 'kalshi_state' }).then(j => { setS(j); setF(j.cfg); }).catch(e => setErr(e.message));
  useEffect(() => { load(); }, [cat.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const save = async next => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'kalshi_cfg', tools: next }); setS(x => ({ ...x, ...j })); setF(j.cfg); } catch (e) { setErr(e.message); } setBusy(false); };
  if (!s || !f) return <p className="dsk-note" data-testid="kd-wait">{err || 'Reading the Kalshi door…'}</p>;
  const on = !!s.key; const auto = f.mode === 'auto'; const bal = s.balance;
  return <section className={`kd m-glass${on ? ' is-on' : ''}`} data-testid="kalshi-door">
    <header className="kd-h"><span><b>🎯 REAL BIDS ON KALSHI</b><small>{!s.key ? 'Save your Kalshi API key in this agent’s Keys (key id, a space, then the private key) to use it.' : auto ? 'A PoB you ask for bids at once inside your caps · Auto on: its auto runs bid by themselves too.' : 'A PoB you ask for bids at once inside your caps, when both minds agree.'}</small></span>
      <label className="m-toggle" data-tip={s.key ? 'Auto: its scheduled auto runs bid by themselves too, never over your caps. Off: their tickets wait for your tap' : 'Save the key first'}><input type="checkbox" checked={auto} disabled={busy || !s.key} onChange={e => save({ ...f, mode: e.target.checked ? 'auto' : 'approve' })} data-testid="kd-auto" />Auto {auto ? 'on' : 'off'}</label></header>
    <HqVitals tiles={[{ label: 'Kalshi balance', value: bal, pre: '$', dec: 2, tone: 'up', tip: s.balanceErr || 'Read live from your Kalshi account' }, { label: 'Spent today', value: s.spentToday, pre: '$', dec: 2, of: f.dayUsd, tone: 'gold' }, { label: 'Per bid cap', value: f.bidUsd, pre: '$', dec: 2, of: s.hard.bidUsd, tone: 'violet' }, { label: 'Bids', value: (s.bids || []).filter(b => ['resting', 'filled', 'sent'].includes(b.status)).length, tone: 'pink' }]} />
    {s.balanceErr ? <p className="dsk-note" role="alert" data-testid="kd-balerr">Kalshi: {s.balanceErr}</p> : null}
    <div className="kd-set">
      {[['bidUsd', 'Per bid $', s.hard.bidUsd, 'Most one bid may spend'], ['dayUsd', 'Per day $', s.hard.dayUsd, 'Most all its bids may spend in 24 h'], ['floorUsd', 'Keep at least $', 10000, 'It never bids your Kalshi balance below this'], ['minConf', 'Both minds ≥ %', 100, 'Each mind must be at least this sure']].map(([k, l, hi, tip]) => <label key={k} className="kd-num" data-tip={tip}><small>{l}</small><input className="m-input" type="number" min={0} max={hi} step={k === 'minConf' ? 1 : 0.5} value={f[k]} onChange={e => setF(x => ({ ...x, [k]: e.target.value }))} onBlur={() => save(f)} disabled={busy} data-testid={`kd-${k}`} /></label>)}
    </div>
    {s.streak ? <p className="kd-streak" data-testid="kd-streak">🔥 {s.streak} real win{s.streak === 1 ? '' : 's'} in a row on Kalshi</p> : null}
    {s.raise ? <span className="kd-raise m-glass" data-testid="kd-raise"><small>{s.raise.streak} wins in a row. Bigger bids are your call: nothing changes unless you tap.</small>
      <ActBtn money className="m-btn" disabled={busy} run={() => work(cat.id, { op: 'kalshi_raise', job: Number(s.raise.to).toFixed(2) })} onDone={j => { setS(x => ({ ...x, ...j })); setF(j.cfg); }} confirm={`Tap again: per bid $${Number(s.raise.from).toFixed(2)} → $${Number(s.raise.to).toFixed(2)}`} done="Raised" data-tip="Raises only the per-bid cap, to exactly this value. Your daily cap and floor stay" data-testid="kd-raise-go">Raise per bid to ${Number(s.raise.to).toFixed(2)}</ActBtn></span> : null}
    {(s.bids || []).length ? <ol className="kd-bids" aria-label="Its real bids" data-testid="kd-bids">{s.bids.slice(0, 6).map((b, i) => <li key={b.id || i} className={`is-${b.status}`} style={{ '--i': i }}><b>{b.side?.toUpperCase()} · {b.title || b.ticker}</b><small>{STATUS[b.status] || b.status}{b.usd ? ` · ${b.count} × ${Number(b.price).toFixed(2)} = $${Number(b.usd).toFixed(2)}` : ''}{b.why && !b.usd ? ` · ${b.why}` : ''}{b.orderId ? <em className="kd-ok">{resultLine(b) || confirmLine(b)}</em> : null}</small></li>)}</ol> : null}
    {err ? <p className="dsk-note" role="alert">{err}</p> : null}
  </section>;
}

export function KalshiTicket({ t: t0, catId, work, onDone }) {
  const [t, setT] = useState(t0); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const act = async op => { setBusy(op); setErr(''); try { const j = await work(catId, { op, job: t.id }); if (j.ticket) setT(j.ticket); if (j.checkErr) setErr(j.checkErr); onDone?.(j); } catch (e) { setErr(e.message); } setBusy(''); };
  return <section className={`kd-ticket m-glass is-${t.status}`} data-testid="kalshi-ticket"><span className="kd-tk-h"><b>🎯 KALSHI · {t.side?.toUpperCase()} · {t.title}</b><small className="m-num">{t.ticker} · ask {t.price != null ? Number(t.price).toFixed(2) : '—'} · minds {(t.conf || []).join('% / ')}%</small></span>
    {Array.isArray(t.why) ? <small className="kd-tk-why">{t.why.filter(Boolean).join(' · ')}</small> : null}
    {t.status === 'waiting' ? <span className="kd-tk-go"><ActBtn money className="m-btn m-go" disabled={!!busy} run={() => work(catId, { op: 'kalshi_bid', job: t.id })} onDone={j => { setT(j.ticket); onDone?.(j); }} confirm={`Tap again: real bid ${t.side?.toUpperCase()} @ ${t.price != null ? Number(t.price).toFixed(2) : '—'}`} done="Sent" data-tip="Real money: two taps. Re-reads the price and your balance, checks every cap, then sends ONE limit order on your own Kalshi key" data-testid="kd-approve">Approve real bid</ActBtn><button type="button" className="m-btn" disabled={!!busy} onClick={() => act('kalshi_skip')} data-tip="Nothing is sent" data-testid="kd-skip">Skip</button></span>
      : <b className={`kd-tk-st is-${t.status}`} role="status" data-testid="kd-status">{STATUS[t.status] || t.status}{t.usd ? ` · ${t.count} × ${Number(t.price).toFixed(2)} = $${Number(t.usd).toFixed(2)}` : ''}{typeof t.why === 'string' && !t.usd ? ` · ${t.why}` : ''}</b>}
    {t.orderId ? <span className="kd-tk-ok"><small className="kd-ok" data-testid="kd-confirm">{confirmLine(t) || 'Sent to Kalshi'}</small>{resultLine(t) ? <small className={`kd-ok kd-res${t.outcome ? ` is-${t.outcome}` : ''}`} data-testid="kd-result">{resultLine(t)}</small> : null}{['sent', 'resting'].includes(t.status) || t.confirmErr ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => act('kalshi_check')} data-tip="Reads this order back from your Kalshi account. Nothing is sent" data-testid="kd-check">Check on Kalshi</button> : null}</span> : null}
    {err ? <p className="dsk-note" role="alert">{err}</p> : null}
  </section>;
}

// ⚖ HEDGE (owner 2026-11-14): the minds did not agree on one Kalshi side, so there is no ticket. Each mind's side and the live odds, nothing to send.
export function KalshiHedge({ rows }) {
  return <section className="kd-hedge m-glass" data-testid="kalshi-hedge"><b>⚖ THE MINDS SPLIT · no real bid</b><small>A real bid needs both minds on the same market and side. Here is each side with Kalshi's live price.</small>
    <ol>{rows.map((r, i) => <li key={`${r.ticker}-${r.side}-${i}`} className={`is-${r.side}`}><em>{r.name || `Mind ${'AB'[i]}`} · {r.conf}%</em><b>{r.side?.toUpperCase()} · {r.title}</b><small className="m-num">{r.price != null ? `${Number(r.price).toFixed(2)} on Kalshi` : 'no price'}{r.why ? ` · ${r.why}` : ''}</small></li>)}</ol></section>;
}

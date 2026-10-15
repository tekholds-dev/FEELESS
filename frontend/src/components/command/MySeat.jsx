import React, { useState } from 'react';
import '../../styles/mySeat.css';

// 👤 YOUR COIN IN A SEAT (owner, 2026-10-15: "still no way to add my own coins into seats — they track my every move and study during that seat,
// AI also suggests"). Paste a contract address → it takes an EMPTY seat (fillSeat) or swaps out the seat you choose (pickSwap, now). It goes
// through the card's normal checks; a warning comes back as "add it anyway" (the server's 409 + ack). On your seat the agents never move by
// themselves: Reaper ASKS (✅ / ✋ above), the AI reads it first, and every ruling is filed so the study can compare you with them.
const CA = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
export function caOf(text) {
  const t = String(text || '').trim();
  const m = t.match(/[1-9A-HJ-NP-Za-km-z]{32,44}/g) || [];   // a pasted link (pump.fun / dexscreener / solscan) still carries the address
  return CA.test(t) ? t : m.length ? m[m.length - 1] : null;
}
export function seatTargets(seats) {
  const open = (seats || []).filter(s => s.open).length;
  return [...(open ? [{ k: 'open', label: `🪑 empty seat (${open} open)` }] : []),
    ...(seats || []).filter(s => !s.open && s.pair && s.state !== 'frozen').map(s => ({ k: s.pair, label: `⇄ swap out $${s.symbol}${s.pct != null ? ` (${s.pct >= 0 ? '+' : ''}${s.pct.toFixed(1)}%)` : ''}` }))];
}
export function addBody(tpl, mint, target, ack) {
  return target === 'open' ? { fillSeat: { tpl, to: mint, more: true, ...(ack ? { ack: true } : {}) } }
    : { pickSwap: { tpl, pairAddress: target, to: mint, now: true, ...(ack ? { ack: true } : {}) } };
}

export function AddMyCoin({ call, tpl, seats, reload }) {
  const targets = seatTargets(seats);
  const [text, setText] = useState(''); const [to, setTo] = useState(''); const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null); const [warn, setWarn] = useState(null);
  const target = targets.some(t => t.k === to) ? to : targets[0]?.k;
  const mint = caOf(text);
  if (!tpl || !call) return null;
  // ✋ YOUR SELECTION, NO GATE (owner, 2026-10-15: "should be no restrictions on my selections"): ⚡ Add sends the acknowledgement up front —
  // the checks still run and their words are filed on the seat, but nothing stops your coin.
  const go = async ack => {
    if (!mint || !target) return;
    setBusy(true); setMsg(null);
    try {
      await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(addBody(tpl, mint, target, ack)) });
      setWarn(null); setText('');
      setMsg({ ok: true, t: target === 'open' ? '🪑 queued — it takes the seat on this tick. The agents study it with you.' : '⇄ swapping now — your coin takes that seat.' });
      reload?.();
    } catch (e) {
      const t = String(e?.message || e);
      if (t.startsWith('⚠')) setWarn(t); else setMsg({ ok: false, t });
    } finally { setBusy(false); }
  };
  return <div className="mys" data-testid="my-seat-add">
    <b className="mys-h">👤 ADD MY COIN</b>
    <input className="m-input mys-in" value={text} placeholder="paste a contract address or a pump.fun / dex link" onChange={e => { setText(e.target.value); setWarn(null); setMsg(null); }}
      onKeyDown={e => { if (e.key === 'Enter') go(true); }} data-testid="my-seat-ca" aria-label="Coin contract address" />
    <select className="m-input mys-to" value={target || ''} onChange={e => setTo(e.target.value)} data-testid="my-seat-to" aria-label="Which seat">
      {targets.map(t => <option key={t.k} value={t.k}>{t.label}</option>)}</select>
    <button type="button" className="m-btn m-go" disabled={busy || !mint || !target} onClick={() => go(true)} data-testid="my-seat-go">{busy ? 'Adding…' : '⚡ Add'}</button>
    {text && !mint ? <small className="mys-note is-bad">That is not a Solana address yet.</small> : null}
    {warn ? <span className="mys-warn" data-testid="my-seat-warn">{warn}<button type="button" className="m-btn" disabled={busy} onClick={() => go(true)} data-testid="my-seat-ack">I understand — add it anyway</button></span> : null}
    {msg ? <small className={`mys-note ${msg.ok ? 'is-ok' : 'is-bad'}`} data-testid="my-seat-msg">{msg.t}</small> : null}
  </div>;
}

// 👤 on YOUR seat: what the agents would do right now + the last rulings they filed while you held it
export function SeatStudy({ s }) {
  if (!s?.mine) return null;
  const w = s.would || (s.agentsWould ? { action: 'pull', why: `${s.agentsWould.rule} at ${s.agentsWould.pct >= 0 ? '+' : ''}${s.agentsWould.pct}%` } : null);
  const last = (s.study || []).slice(-2).reverse();
  return <div className="mys-study" data-testid={`my-seat-study-${s.seat}`}>
    <span className="mys-tag">👤 YOURS · agents only suggest</span>
    {w ? <span className="mys-would" data-testid={`my-seat-would-${s.seat}`}>🤖 would {w.action === 'swap' ? `swap for $${w.to || '?'}` : w.action === 'pull' ? 'sell' : w.action}{w.why ? ` — ${String(w.why).slice(0, 90)}` : ''}</span>
      : <span className="mys-would is-calm">🤖 agree: hold</span>}
    {last.map(x => <small key={x.k + x.at} className="mys-log">{x.sell ? '✋' : '·'} {x.rule} {x.pct >= 0 ? '+' : ''}{x.pct}%</small>)}
  </div>;
}

// 📊 your closed seats vs where the agents would have sold (office.owner_seats)
export function MySeatsRecord({ rec }) {
  if (!rec?.n) return <small className="mys-rec" data-testid="my-seats-rec">👤 Your seats: none closed yet — every one you add is studied against the agents.</small>;
  const c = rec.cmp || {}; const s = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v}%`);
  return <small className="mys-rec" data-testid="my-seats-rec">👤 Your seats: {rec.n} closed · typical {s(rec.med)}
    {c.n ? <> · vs the agents' exit on the same coins: you {s(c.you)} · them {s(c.agents)} · you did better {c.youBetter}/{c.n}</> : null}</small>;
}

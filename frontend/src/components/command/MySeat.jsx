import React, { useEffect, useRef, useState } from 'react';
import { sharedJson, markFresh } from '../../lib/sharedJson';
import NumInput from '../NumInput';
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
export function addBody(tpl, mint, target, ack, limitPx) {
  const lim = Number(limitPx) > 0 ? { limitPx: Number(limitPx), hours: 24 } : {};   // 🎯 a price = a BUY LIMIT (fires when the live price is ≤ it, 24h)
  return target === 'open' ? { fillSeat: { tpl, to: mint, more: true, ...(ack ? { ack: true } : {}), ...lim } }
    : { pickSwap: { tpl, pairAddress: target, to: mint, now: true, ...(ack ? { ack: true } : {}), ...lim } };
}
// 🎯 one sell limit on a held seat: take (≥) or stop (≤) at a % from NOW, pct of the coin
export function sellLimitBody(tpl, seat, movePct, pct = 100) {
  const px = Number(seat?.px); if (!(px > 0)) return null;
  return { limitSell: { tpl, pairAddress: seat.pair, px: px * (1 + movePct / 100), pct, stop: movePct < 0, hours: 24 } };
}
export const LIMIT_MOVES = [25, 50, 100, -15, -30];

// pure: where YOUR add stands right now, read from the live card (no extra fetch): sent → queued → buying → bought, or the keeper's own
// refusal from the card's events. `since` = when you pressed Add (s), so an older fill of the same coin never counts.
export const ADD_STEPS = [['sent', 'sent'], ['queued', 'queued'], ['buying', 'buying'], ['filled', 'bought']];
export function addStage(card, track, now = Date.now() / 1000) {
  if (!track?.mint) return null;
  card = card || {};
  const leg = (card.legs || []).find(l => l.mint === track.mint);
  const sym = leg?.symbol || track.symbol;
  const since = Number(track.at) - 5;
  const fill = sym && (card.realBook?.orders || []).find(o => o.side === 'buy' && o.symbol === sym && o.status === 'filled' && Number(o.at) >= since);
  if (fill) return { k: 'filled', sym, t: `✅ bought $${sym} · $${Number(fill.usd || 0).toFixed(2)} in`, sig: fill.sig };
  const bad = (card.events || []).find(e => Number(e.at) >= since && (JSON.stringify(e).includes(track.mint) || (sym && JSON.stringify(e).includes(`$${sym}`)))
    && /refus|not bought|never landed|back to cash|skipp|no route|too thin/i.test(String(e.why || e.text || e.msg || '')));
  if (bad) return { k: 'refused', sym, t: `✕ ${String(bad.why || bad.text || bad.msg).slice(0, 140)}` };
  if (leg) return { k: 'buying', sym, t: `⏳ $${sym || 'coin'} has its seat — the keeper sends the buy on its next pass` };
  if (JSON.stringify([card.seatPick, card.seatQueue, (card.legs || []).map(l => l.swapTo)]).includes(track.mint) || (sym && JSON.stringify(card.seatPick || '').includes(sym)))
    return { k: 'queued', sym, t: '🪑 queued — it takes the seat on the next tick' };
  return { k: 'sent', sym, t: now - Number(track.at) > 90 ? '… no seat yet — the card may be full or the coin left the lists; try ⇄ swap out a coin' : '📨 sent to the card' };
}

export function AddMyCoin({ call, tpl, seats, reload }) {
  const targets = seatTargets(seats);
  const [text, setText] = useState(''); const [lim, setLim] = useState(''); const [to, setTo] = useState(''); const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null); const [opts, setOpts] = useState(false); const [track, setTrack] = useState(null); const [card, setCard] = useState(null);
  const target = targets.some(t => t.k === to) ? to : targets[0]?.k;
  const mint = caOf(text);
  const stage = addStage(card, track);
  const goRef = useRef(null);
  useEffect(() => {   // 📡 follow YOUR add on the shared card read until it is bought or refused (2 min of tracking at most)
    if (!track || !tpl) return undefined;
    let alive = true;
    const tick = () => sharedJson('/api/reputation/fuses/prime', { maxAge: 2500 }).then(d => { if (alive) setCard((d?.cards || []).find(x => x.tpl === tpl) || null); }).catch(() => {});
    tick(); const t = setInterval(tick, 3000);
    return () => { alive = false; clearInterval(t); };
  }, [track, tpl]);
  useEffect(() => { if (stage && (stage.k === 'filled' || stage.k === 'refused')) { const t = setTimeout(() => setTrack(null), 60000); return () => clearTimeout(t); } return undefined; }, [stage?.k]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {   // 📋 paste a coin ANYWHERE on the Agents tab (not inside a text box) → it goes in, same as pasting into the box
    if (!tpl || !call) return undefined;
    const on = e => {
      const tg = e.target; if (tg && (tg.closest?.('input, textarea, select, [contenteditable="true"]'))) return;
      const ca = caOf(e.clipboardData?.getData('text')); if (ca) { e.preventDefault(); setText(ca); goRef.current?.(ca); }
    };
    document.addEventListener('paste', on); return () => document.removeEventListener('paste', on);
  }, [tpl, call]);
  if (!tpl || !call) return null;
  // ✋ YOUR SELECTION, NO GATE (owner, 2026-10-15/16: "should be no restrictions on my selections" · "adding my coin should be easy"): paste = added.
  // The acknowledgement goes up front, the checks still run and their words are filed on the seat, and the strip below follows it to the fill.
  const go = async (ca = mint) => {
    if (!ca || !target || busy) return;
    setBusy(true); setMsg(null);
    try {
      await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(addBody(tpl, ca, target, true, lim)) });
      setText(''); const wasLim = Number(lim) > 0; setLim('');
      if (wasLim) { setMsg({ ok: true, t: '🎯 buy limit set — it fires when the live price is at or under your price (24h).' }); reload?.(); return; }
      markFresh(); setTrack({ mint: ca, at: Date.now() / 1000 }); reload?.();
    } catch (e) { setMsg({ ok: false, t: String(e?.message || e).replace(/^⚠\s*/, '') }); } finally { setBusy(false); }
  };
  goRef.current = go;
  return <div className="mys" data-testid="my-seat-add">
    <b className="mys-h">👤 ADD MY COIN</b>
    <input className="m-input mys-in" value={text} placeholder={target ? 'paste a contract address or link (anywhere on this tab) — it goes in' : 'no seat to use (all frozen)'} disabled={busy}
      onChange={e => { setText(e.target.value); setMsg(null); }}
      onPaste={e => { const ca = caOf(e.clipboardData?.getData('text')); if (ca && !Number(lim)) { e.preventDefault(); setText(ca); go(ca); } }}
      onKeyDown={e => { if (e.key === 'Enter') go(); }} data-testid="my-seat-ca" aria-label="Coin contract address" />
    <button type="button" className="m-btn m-go" disabled={busy || !mint || !target} onClick={() => go()} data-testid="my-seat-go">{busy ? 'Adding…' : Number(lim) > 0 ? '🎯 Set limit' : '⚡ Add'}</button>
    <button type="button" className={`m-btn mys-opt ${opts ? 'is-on' : ''}`} onClick={() => setOpts(o => !o)} aria-expanded={opts} data-testid="my-seat-opts" data-tip="Which seat, or a buy limit price">⚙</button>
    {opts ? <span className="mys-opts">
      <select className="m-input mys-to" value={target || ''} onChange={e => setTo(e.target.value)} data-testid="my-seat-to" aria-label="Which seat">
        {targets.map(t => <option key={t.k} value={t.k}>{t.label}</option>)}</select>
      <input className="m-input mys-lim" value={lim} placeholder="limit price (blank = now)" inputMode="decimal" onChange={e => setLim(e.target.value.replace(/[^0-9.]/g, ''))} data-testid="my-seat-limit" aria-label="Buy limit price" data-tip="Leave blank to buy now. A price = a buy limit: FEELESS places your pick when the live price is at or under it (24h)." />
    </span> : <small className="mys-note">→ {targets.find(t => t.k === target)?.label || 'no seat'}</small>}
    {text && !mint ? <small className="mys-note is-bad">That is not a Solana address yet.</small> : null}
    {stage ? <div className={`mys-track k-${stage.k}`} data-testid="my-seat-track">
      <ol>{ADD_STEPS.map(([k, w], i) => { const at = ADD_STEPS.findIndex(x => x[0] === stage.k); return <li key={k} className={stage.k === 'refused' ? (i === 0 ? 'done' : '') : i < at ? 'done' : i === at ? 'now' : ''}>{w}</li>; })}</ol>
      <small data-testid="my-seat-msg">{stage.t}</small></div> : null}
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

// ✂ SELL AN AMOUNT (owner, 2026-10-16: "need more access to sell my x amount or enter amount to sell"): a % of the coin, or a $ amount turned into
// that coin's % at its live value (capped 100). Pure; the sell itself is the card's own ✂ manualSell path (proceeds held as card cash for you).
export function sellPct(mode, n, valueUsd) {
  const v = Number(n);
  if (!(v > 0)) return null;
  if (mode === '$') return Number(valueUsd) > 0 ? Math.max(1, Math.min(100, Math.round((v / Number(valueUsd)) * 1000) / 10)) : null;
  return Math.max(1, Math.min(100, Math.round(v * 10) / 10));
}

function SellBox({ s, valueUsd, busy, onSell }) {
  const [mode, setMode] = useState('%'); const [n, setN] = useState('');
  const pct = sellPct(mode, n, valueUsd);
  const go = p => { if (p) { onSell(p); setN(''); } };
  return <span className="mys-sell" role="group" aria-label={`Sell part of $${s.symbol}`}>
    {[25, 50].map(p => <button key={p} type="button" className="m-btn mys-chip is-cut" disabled={!!busy} onClick={() => go(p)} data-testid={`seat-cut-${s.symbol}-${p}`} data-tip={`Sell ${p}% of $${s.symbol} now — the rest stays on its seat`}>✂ {p}%</button>)}
    <NumInput className="m-input mys-sellin" value={n} onChange={e => setN(e.target.value)} placeholder={mode === '$' ? '$ amt' : '% amt'} aria-label={`Amount of $${s.symbol} to sell`}
      onKeyDown={e => { if (e.key === 'Enter') go(pct); }} data-testid={`seat-sell-in-${s.symbol}`} />
    <button type="button" className="m-btn mys-chip mys-unit" onClick={() => setMode(m => (m === '%' ? '$' : '%'))} data-testid={`seat-sell-unit-${s.symbol}`}
      data-tip={valueUsd > 0 ? `Switch % ⇄ $ — this coin is worth $${valueUsd.toFixed(2)} now` : 'Switch % ⇄ $'}>{mode}</button>
    <button type="button" className="m-btn mys-chip is-cut" disabled={!!busy || !pct} onClick={() => go(pct)} data-testid={`seat-sell-go-${s.symbol}`}
      data-tip={pct ? `Sell ${pct}% of $${s.symbol}${valueUsd > 0 ? ` (≈ $${(valueUsd * pct / 100).toFixed(2)})` : ''} — the agents study it as your move` : 'Type an amount'}>✂ Sell{pct ? ` ${pct}%` : ''}</button>
  </span>;
}

// ⏏ PULL + 🎯 SELL LIMITS on every held seat, and your open limits (owner, 2026-10-15: "a way to pull seat", "do limit orders")
export const GSTOPS = [['off', 'off'], ['1m', '1m'], ['5m', '5m'], ['both', '1–5m']];   // 🦠 Gstop lenses (arena_prime.GSTOP_MODES)

export function SeatControls({ call, tpl, seats, reload }) {
  const [busy, setBusy] = useState(null); const [msg, setMsg] = useState(null); const [lims, setLims] = useState([]); const [legs, setLegs] = useState({}); const [rebuy, setRebuy] = useState([]);
  const load = () => sharedJson('/api/reputation/fuses/prime', { maxAge: 4000 }).then(d => { const c = (d?.cards || []).find(x => x.tpl === tpl) || {};
    setLims(c.limits || []); setLegs(Object.fromEntries((c.legs || []).map(l => [l.pairAddress, l]))); setRebuy(c.germRebuy || []); }).catch(() => {});
  useEffect(() => { if (!tpl) return undefined; load(); const t = setInterval(() => { if (!document.hidden) load(); }, 10000); return () => clearInterval(t); }, [tpl]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (!tpl || !call) return null;
  const send = async (key, body, ok) => {
    if (!body) return; setBusy(key); setMsg(null);
    try { await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }); setMsg({ ok: true, t: ok }); markFresh(); load(); reload?.(); }
    catch (e) { setMsg({ ok: false, t: String(e?.message || e) }); } finally { setBusy(null); }
  };
  const held = (seats || []).filter(s => !s.open && s.pair);
  return <div className="mys-ctl" data-testid="seat-controls">
    {held.map(s => <div key={s.pair} className="mys-row">
      <b>${s.symbol}</b><small className={s.pct >= 0 ? 'm-pos' : 'm-neg'}>{s.pct != null ? `${s.pct >= 0 ? '+' : ''}${s.pct.toFixed(1)}%` : '—'}</small>
      <span className="mys-lims" role="group" aria-label={`Sell limit for $${s.symbol}`}>{LIMIT_MOVES.map(m => <button key={m} type="button" className={`m-btn mys-chip ${m < 0 ? 'is-stop' : ''}`} disabled={!!busy || !(s.px > 0)}
        onClick={() => send(`${s.pair}${m}`, sellLimitBody(tpl, s, m, m > 0 && m < 100 ? 50 : 100), `🎯 ${m > 0 ? 'take' : 'stop'} limit set on $${s.symbol}: ${m > 0 ? '+' : ''}${m}% from now`)}
        data-testid={`seat-lim-${s.symbol}-${m}`} data-tip={m > 0 ? `Sell ${m < 100 ? 50 : 100}% when the live price is ${m}% above now` : `Sell all if it falls ${-m}% from now`}>{m > 0 ? `💰 +${m}%` : `🛑 ${m}%`}</button>)}</span>
      <button type="button" className={`m-btn mys-cert ${legs[s.pair]?.certified ? 'is-on' : ''}`} disabled={!!busy} aria-pressed={!!legs[s.pair]?.certified}
        onClick={() => send(`cert-${s.pair}`, { leg: { tpl, pairAddress: s.pair, certified: !legs[s.pair]?.certified } }, legs[s.pair]?.certified ? `🛡 $${s.symbol} un-certified — the agents may advise again` : `🛡 $${s.symbol} certified — you hold it: only your stop, your Gstop, a pulled pool and −45% act`)}
        data-testid={`seat-cert-${s.symbol}`} data-tip="Certified = you hold it. No agent advice, no soft exit; only your own stop, your Gstop, a pulled pool and the −45% floor act.">🛡 {legs[s.pair]?.certified ? 'Certified' : 'Certify'}</button>
      <button type="button" className={`m-btn mys-cert mys-lock ${legs[s.pair]?.pickLock ? 'is-on' : ''}`} disabled={!!busy} aria-pressed={!!legs[s.pair]?.pickLock}
        onClick={() => send(`lock-${s.pair}`, { leg: { tpl, pairAddress: s.pair, pickLock: !legs[s.pair]?.pickLock } }, legs[s.pair]?.pickLock ? `🔒 half-lock off on $${s.symbol} — your own stops and skims only` : `🔒 half-lock on $${s.symbol}: once +10%, half is banked if it gives back half its peak`)}
        data-testid={`seat-lock-${s.symbol}`} data-tip="OFF by default — your own stops and skims rule. ON: once this coin has been +10% and falls under half its peak, half of it is banked once; the rest rides your stop.">🔒 {legs[s.pair]?.pickLock ? 'Half-lock on' : 'Half-lock'}</button>
      <span className="m-seg mys-gstop" role="group" aria-label={`Germ stop for $${s.symbol}`}>{GSTOPS.map(([v, w]) => <button key={v} type="button" disabled={!!busy} className={(legs[s.pair]?.gstop || 'off') === v ? 'active' : ''}
        onClick={() => send(`g-${s.pair}-${v}`, { leg: { tpl, pairAddress: s.pair, gstop: v } }, v === 'off' ? `🦠 Gstop off on $${s.symbol}` : `🦠 Gstop ${w} on $${s.symbol}: sold when it loses its germ floor, bought back on a new one`)}
        data-testid={`seat-gstop-${s.symbol}-${v}`} data-tip={v === 'off' ? 'No germ stop' : `Sell when the price loses its ${w} germ floor; bought back when a NEW germ floor is confirmed (inside your germ line)`}>{v === 'off' ? '🦠 off' : w}</button>)}</span>
      <span className="mys-tp" role="group" aria-label={`Take profit from $${s.symbol}`}>{[['card', '💰→coins', 'profit into your other coins'], ['round', '🅿 park', 'profit parked in card cash for 2 rounds, then back in'], ['cash', '🏦 cash', 'profit held as card cash for you'], ['stake', '🏠 initial', 'take your initial out — only the profit rides']].map(([to, w, tip]) =>
        <button key={to} type="button" className="m-btn mys-chip is-take" disabled={!!busy || !(s.pct > 0)} data-testid={`seat-skim-${s.symbol}-${to}`} data-tip={`${tip} (needs the coin in profit) — the agents file it as your move`}
          onClick={() => send(`skim-${s.pair}-${to}`, { skim: to === 'stake' ? { tpl, pairAddress: s.pair, to: 'cash', stake: true } : to === 'round' ? { tpl, pairAddress: s.pair, to: 'round', rounds: 2 } : { tpl, pairAddress: s.pair, to } }, `💰 $${s.symbol}: ${tip} — once it confirms`)}>{w}</button>)}</span>
      <button type="button" className={`m-btn mys-cert ${legs[s.pair]?.frozen ? 'is-on' : ''}`} disabled={!!busy} aria-pressed={!!legs[s.pair]?.frozen} data-testid={`seat-frz-${s.symbol}`}
        onClick={() => send(`frz-${s.pair}`, { leg: { tpl, pairAddress: s.pair, frozen: !legs[s.pair]?.frozen } }, legs[s.pair]?.frozen ? `$${s.symbol} unfrozen` : `❄ $${s.symbol} frozen — never rotated or stopped by the engine`)}
        data-tip="Freeze: the engine never rotates or stops this coin (a pulled pool and −45% still act)">❄ {legs[s.pair]?.frozen ? 'Frozen' : 'Freeze'}</button>
      <SellBox s={s} busy={busy} valueUsd={Number(legs[s.pair]?.units) * Number(s.px) || 0}
        onSell={p => send(`cut-${s.pair}`, { manualSell: { tpl, pairAddress: s.pair, pct: p, ack: true } }, `✂ sold ${p}% of $${s.symbol} — held as card cash for you; the agents file it as your move`)} />
      <button type="button" className="m-btn mys-pull" disabled={!!busy} onClick={() => send(`pull-${s.pair}`, { manualSell: { tpl, pairAddress: s.pair, pct: 100, ack: true } }, `⏏ $${s.symbol} pulled — sold to card cash, the seat opens`)} data-testid={`seat-pull-${s.symbol}`} data-tip="Sell this whole coin to card cash now — the seat opens">⏏ Pull</button>
    </div>)}
    {rebuy.length ? <p className="mys-rebuy" data-testid="seat-germ-rebuy">🦠 watching for a new germ floor: {rebuy.map(r => `$${r.symbol} (${r.lens})`).join(' · ')}</p> : null}
    {lims.length ? <ul className="mys-open" data-testid="seat-limits">{lims.map(x => <li key={x.id}><span>{x.word}</span>
      <button type="button" className="m-btn mys-x" disabled={!!busy} onClick={() => send(`x-${x.id}`, { limitCancel: { tpl, id: x.id } }, 'limit cancelled')} aria-label="Cancel limit" data-testid={`seat-lim-x-${x.id}`}>✕</button></li>)}</ul> : null}
    {msg ? <small className={`mys-note ${msg.ok ? 'is-ok' : 'is-bad'}`} data-testid="seat-ctl-msg">{msg.t}</small> : null}
  </div>;
}

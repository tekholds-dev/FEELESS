import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { sharedJson } from '../lib/sharedJson';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import '../styles/dailyCall.css';

import { tiny } from '../lib/num';
// ⚡ FREE CALL (Radar › Signals, top): every hour the engine's doors put a coin each on a ballot — pick the one that leads the next hour. Free, points only:
// +10 season points for a right call, a streak adds more; feeds the daily / weekly quests. Judged on recorded prices. GET /predict · POST /predict/pick.
export const fmtLeft = s => { const t = Math.max(0, Math.floor(s)); return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`; };
export const pctText = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(Math.abs(v) >= 10 ? 1 : 2)}%`);
export const lastLine = l => {
  if (!l) return '';
  const lead = `$${l.symbol} led the last hour${l.moves?.[l.winner] != null ? ` (${pctText(l.moves[l.winner])})` : ''}`;
  return l.won ? `✅ ${lead} — you called it.` : l.mine ? `${lead}. Your call missed.` : `${lead}.`;
};
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });

export function DailyCall() {
  const { wallet } = useWallet() || {}; const addr = wallet?.address || '';
  const [d, setD] = useState(null); const [now, setNow] = useState(Date.now() / 1000); const [busy, setBusy] = useState(false);
  const load = fresh => sharedJson(`/api/reputation/predict${addr ? `?address=${addr}` : ''}`, { maxAge: 8000, fresh }).then(setD).catch(() => {});
  useEffect(() => { let alive = true; const go = () => { if (alive && !document.hidden) load(); }; load(); const a = setInterval(go, 12000), t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => { alive = false; clearInterval(a); clearInterval(t); }; }, [addr]);   // eslint-disable-line react-hooks/exhaustive-deps
  const r = d?.round;
  if (!r) return null;
  const left = r.closesAt - now, locked = r.locked || left <= 120;
  const pick = async c => {
    const s = addr && readChatSession(addr);
    if (!s) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(true);
    try { await post('/api/reputation/predict/pick', { address: addr, session: s, round: r.id, mint: c.mint }); toast.success(`⚡ Called $${c.symbol} — result at the bell`); sharedJson.freshAt = Date.now(); await load(true); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <section className="dcl m-card m-live" data-testid="daily-call">
    <header><span className="m-label">⚡ FREE CALL</span><b className={`dcl-clock m-num ${locked ? 'is-locked' : ''}`} data-tip="Time to the bell. Picks close 2 minutes before it.">{fmtLeft(left)}</b>
      <small>{r.players} caller{r.players === 1 ? '' : 's'} this hour</small>
      {d.me?.streak > 0 && <span className="m-chip dcl-streak" data-tip="Right calls in a row — each adds bonus points">🔥 {d.me.streak} in a row</span>}</header>
    <p className="dcl-q">Which leads the next hour?</p>
    <div className="dcl-cands" role="group" aria-label="This hour's ballot">{r.cands.map((c, i) => <button key={c.mint} type="button" style={{ '--i': i }} className={`dcl-c ${r.mine === c.mint ? 'is-mine' : ''}`} disabled={busy || locked || !!r.mine}
      onClick={() => pick(c)} data-testid={`dcl-${c.symbol}`} data-tip={`${c.doorLabel}. In at ${c.px0 >= 1 ? c.px0.toFixed(2) : tiny(c.px0, 3)} — the biggest move since this hour opened wins.`}>
      <b>${c.symbol}</b><small>{c.doorLabel}</small><em className={`m-num ${c.pct == null ? '' : c.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pctText(c.pct)}</em>{r.mine === c.mint && <i>locked in ✓</i>}</button>)}</div>
    <footer><small className="dcl-last">{lastLine(d.last)}</small>
      <details className="dcl-board"><summary data-tip={d.rule}>🏆 this week{d.me ? ` · you ${d.me.wins || 0}/${d.me.picks || 0}` : ''}</summary>
        {(d.board || []).length ? <ol>{d.board.map(b => <li key={b.address}><a href={`/terminal/profile/${b.address}`}>{b.name}</a><em>{b.wins}/{b.picks}</em>{b.streak > 1 ? <i>🔥{b.streak}</i> : null}</li>)}</ol> : <small className="m-dim">No calls this week yet — be first.</small>}
        <small className="m-dim">{d.rule}</small></details></footer>
  </section>;
}

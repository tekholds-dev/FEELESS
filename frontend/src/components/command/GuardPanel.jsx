import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/tips.css';

// Cmd Ctr › Security › 🛡 Guard: floods get a breather and Cmd Ctr brute force cools down AUTOMATICALLY — but nobody is
// blocked by a machine. Suspects wait here with their evidence; a block (or lifting one) is your approval, audited.
const ago = t => { const s = Math.max(0, Date.now() / 1000 - t); return s < 90 ? `${Math.round(s)}s` : s < 5400 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };

export function GuardPanel({ call }) {
  const [g, setG] = useState(null);
  const [busy, setBusy] = useState('');
  useEffect(() => {
    let alive = true; const load = () => !document.hidden && call('/admin/security/guard').then(x => alive && setG(x)).catch(() => {});
    call('/admin/security/guard').then(x => alive && setG(x)).catch(() => {}); const t = setInterval(load, 20000);
    return () => { alive = false; clearInterval(t); };
  }, [call]);
  if (!g) return <div className="fl-row is-ghost" />;
  const act = (ip, action) => { setBusy(ip + action);
    call('/admin/security/guard', { method: 'POST', body: JSON.stringify({ ip, action }) })
      .then(x => { setG(x); toast.success(`${action === 'block' ? '⛔ Blocked' : action === 'unblock' ? '✓ Unblocked' : '✓ Cleared'} ${ip}`); })
      .catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const r = g.rules;
  return <section className="m-card gd" data-testid="guard-panel">
    <div className="m-row"><span className="m-label">🛡 GUARD · BRUTE PROTECTION · NO AUTO-BLOCKS</span><small className="m-dim">every block is your approval</small></div>
    <div className="gd-rules">
      <span data-tip="Writes per IP per minute before a short breather (reads never limited)"><small>WRITES / MIN</small><b className="m-num">{r.writesPerMin}</b></span>
      <span data-tip={`${r.adminFails} failed Cmd Ctr signatures in ${r.adminWindowMin} min → that IP's admin requests cool down`}><small>SIGN-IN FAILS</small><b className="m-num">{r.adminFails}/{r.adminWindowMin}m</b></span>
      <span data-tip="How long a brute-forcing IP waits — trading and chat still work for it"><small>COOL-DOWN</small><b className="m-num">{r.adminCoolMin}m</b></span>
      <span><small>COOLING NOW</small><b className={`m-num ${g.cooling.length ? 'm-neg' : ''}`}>{g.cooling.length}</b></span>
    </div>
    <div className="gd-cols">
      <div className="gd-box"><header><b>⏳ Waiting for your call</b><small className="m-dim">{g.suspects.length} suspect{g.suspects.length === 1 ? '' : 's'}</small></header>
        {!g.suspects.length ? <p className="m-dim">Nobody flagged. Floods only got a breather.</p> : g.suspects.map((s, i) => <article key={s.ip} className="gd-sus" style={{ '--i': i }}>
          <div className="m-row"><code>{s.ip}</code><small className="m-dim">last {ago(s.last)} ago</small></div>
          <ul>{s.evidence.slice(-3).map((e, k) => <li key={k}><i>{e.rule}</i>{e.claim}</li>)}</ul>
          <div className="m-row"><button type="button" className="m-btn danger" disabled={!!busy} onClick={() => act(s.ip, 'block')} data-testid={`gd-block-${s.ip}`}>⛔ Approve block</button>
            <button type="button" className="m-btn" disabled={!!busy} onClick={() => act(s.ip, 'dismiss')}>✓ Not a bot</button></div></article>)}</div>
      <div className="gd-box"><header><b>⛔ Blocked by staff</b><small className="m-dim">writes refused · reads still load</small></header>
        {!g.blocks.length ? <p className="m-dim">No blocks.</p> : g.blocks.map(b => <div key={b.ip} className="gd-row"><code>{b.ip}</code><small className="m-dim">{b.by?.slice(0, 4)}… · {ago(b.at)} ago{b.note ? ` · ${b.note}` : ''}</small>
          <button type="button" className="m-btn" disabled={!!busy} onClick={() => act(b.ip, 'unblock')}>Lift</button></div>)}
        {g.busiest.length > 0 && <><header><b>📈 Busiest right now</b><small className="m-dim">writes in the last minute</small></header>
          {g.busiest.map(x => <div key={x.ip} className="gd-row"><code>{x.ip}</code><b className="m-num">{x.writes1m}</b></div>)}</>}</div>
    </div>
    {g.log.length > 0 && <small className="m-dim">Last decisions: {g.log.slice(0, 4).map(l => `${l.action} ${l.ip} (${ago(l.at)})`).join(' · ')}</small>}
  </section>;
}

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ApprovalsCheck } from '../ApprovalsCheck';
import '../../styles/defence.css';

// HQ › Security › 🧠 DEFENCE THAT LEARNS (backend/defence.py) + 🗄 NO HOARDING (backend/store_caps.py). Decoys a scanner probes block that
// fingerprint (24h, doubling); a scanner TOOL seen from many IPs becomes a rule; scrapers and replayed HQ signatures are slowed, never blocked.
// Every incident carries a plain abuse report — FEELESS reports, it never attacks back. The stores map is read-only: money is kept whole.
const ago = s => (s < 90 ? `${Math.round(s)}s` : s < 5400 ? `${Math.round(s / 60)}m` : s < 172800 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`);
const CLASS_COLOR = { money: '#d4af37', cache: '#6fd3ff', log: '#9b5cff', memory: '#45e486', snapshot: '#ff9f45', other: '#8a93a6' };
// pure: the stores' classes as one stacked bar (share of the total)
export function classBar(byClass) { const tot = Object.values(byClass || {}).reduce((a, c) => a + c.mb, 0) || 1; return Object.entries(byClass || {}).sort((a, b) => b[1].mb - a[1].mb).map(([k, c]) => ({ k, mb: c.mb, n: c.n, w: c.mb / tot })); }

export function DefencePanel({ call }) {
  const [d, setD] = useState(null); const [st, setSt] = useState(null); const [busy, setBusy] = useState('');
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; call('/admin/security/defence').then(x => on && setD(x)).catch(() => {}); call('/admin/security/stores').then(x => on && setSt(x)).catch(() => {}); };
    go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);
  const lift = body => { setBusy(body.fp || body.ua); call('/admin/security/defence/lift', { method: 'POST', body: JSON.stringify(body) }).then(x => { setD(x); toast.success('Lifted'); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const copy = t => { try { navigator.clipboard.writeText(t); toast.success('Report copied — send it to the network\'s abuse contact'); } catch { toast.error('Copy blocked'); } };
  const bar = classBar(st?.byClass);
  return <section className="m-card dfn" data-testid="defence-panel">
    <div className="m-row"><span className="m-label">🧠 DEFENCE THAT LEARNS · NEVER ATTACKS BACK</span><small className="m-dim">decoys · learned rules · tarpits · abuse reports</small></div>
    {d ? <div className="dfn-vit">{[['BLOCKED NOW', d.blocks.length, 'Fingerprints that probed a decoy (24h, doubling)'], ['LEARNED RULES', d.rules.length, 'Scanner tools seen from many IPs'], ['SLOWED', d.tarpit, 'Scrapers / replayed sessions in the tarpit'], ['INCIDENTS', d.incidents.length, 'Each with its evidence + abuse report']].map(([k, n, tip], i) =>
      <span key={k} style={{ '--i': i }} data-tip={tip}><em>{k}</em><b>{n}</b></span>)}</div> : <div className="fl-row is-ghost" />}
    {d ? <p className="dfn-pots" data-tip="Paths no trader ever opens — a scanner that tries one is blocked and gets a plain 404">🪤 {d.honeypots.length} decoys: {d.honeypots.slice(0, 8).join(' · ')}…</p> : null}
    {d?.blocks?.length ? <ul className="dfn-list">{d.blocks.slice(0, 12).map((b, i) => <li key={b.fp} style={{ '--i': i }}><b>⛔ {b.fp}</b><span>{b.why}</span><small>{b.n > 1 ? `×${b.n} · ` : ''}{ago(b.left)} left</small>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => lift({ fp: b.fp })} data-tip="Lift this block (audited)">Lift</button></li>)}</ul> : null}
    {d?.rules?.length ? <ul className="dfn-list is-rule">{d.rules.map((r, i) => <li key={r.ua} style={{ '--i': i }}><b>🧠 {r.ua.slice(0, 50)}</b><span>{r.why}</span><small>{r.hits} caught</small>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => lift({ ua: r.ua })}>Drop</button></li>)}</ul> : null}
    {d?.incidents?.length ? <details className="dfn-inc"><summary>📄 {d.incidents.length} incidents · evidence + abuse reports</summary>
      <ul className="dfn-list">{d.incidents.slice(0, 20).map((x, i) => <li key={`${x.fp}-${x.kind}`} style={{ '--i': i }} className={`k-${x.kind}`}><b>{x.kind}</b><span>{x.ip} · {x.n} requests · {x.action}</span><small>{ago(Date.now() / 1000 - x.last)} ago</small>
        <button type="button" className="m-btn" onClick={() => copy(x.report)} data-tip="Copy the plain abuse report">Copy report</button></li>)}</ul></details> : d ? <p className="m-dim dfn-quiet">Quiet — no attack seen yet. The decoys are set.</p> : null}
    <div className="m-row dfn-h"><span className="m-label">🗄 NO HOARDING · EVERY STORE</span><small className="m-dim">{st ? `${st.totalMb} MB · ${st.over} over cap · ${st.stale} stale snapshots (${st.staleMb} MB)` : 'reading…'}</small></div>
    {st ? <><div className="dfn-bar" data-tip="What the data folder holds, by kind">{bar.map(b => <i key={b.k} style={{ flexGrow: Math.max(0.01, b.w), background: CLASS_COLOR[b.k] }} data-tip={`${b.k}: ${b.mb} MB in ${b.n} files`} />)}</div>
      <p className="dfn-legend">{bar.map(b => <span key={b.k}><i style={{ background: CLASS_COLOR[b.k] }} />{b.k} {b.mb} MB</span>)}</p>
      <ul className="dfn-stores">{st.stores.filter(r => r.state !== 'ok' && r.state !== 'keep').slice(0, 14).map((r, i) => <li key={r.name} className={`s-${r.state}`} style={{ '--i': i }}>
        <b>{r.name}</b><em>{r.class}</em><u><s style={{ transform: `scaleX(${Math.min(1, (r.pct ?? 100) / 100)})` }} /></u><small>{r.mb} MB{r.capMb ? ` / ${r.capMb}` : ''}{r.state === 'stale' ? ` · ${Math.round(r.ageD)}d old` : ''}</small></li>)}</ul>
      <p className="m-dim dfn-note">Money records are never trimmed. Over-cap caches rebuild smaller; stale snapshots are yours to archive — nothing here deletes anything.</p></> : null}
    <ApprovalsCheck compact />
  </section>;
}

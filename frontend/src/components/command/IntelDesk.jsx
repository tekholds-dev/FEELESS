import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { InvestigatePanel, investigate } from '../CaseFile';
import { shortAddress } from '../../lib/dexscreener';
import { errorText } from '../../lib/api';

// Cmd Ctr › Investigate: the reputation department. A living database of ruggers, dumpers, snipers, bundlers and
// the wallets that fund them, grouped into crews, with each actor's likely next move. FeeCat, the rug shield and
// the radar read the same database, so every catch here sharpens the platform's tools.
const ROLE = { rugger: ['🧨', 'bad'], dumper: ['📉', 'bad'], funder: ['🏦', 'warn'], bundler: ['📦', 'warn'], sniper: ['🎯', ''] };
const VIEWS = [['wanted', 'Most wanted'], ['crews', 'Crews'], ['moves', 'Next moves'], ['lookup', 'Lookup']];
const ago = t => { if (!t) return '—'; const s = Math.max(0, Date.now() / 1000 - t); return s < 3600 ? `${Math.floor(s / 60)}m ago` : s < 86400 ? `${Math.floor(s / 3600)}h ago` : `${Math.floor(s / 86400)}d ago`; };
const eta = t => { if (!t) return ''; const s = t - Date.now() / 1000; return s <= 0 ? 'overdue' : s < 3600 ? `in ~${Math.ceil(s / 60)}m` : s < 86400 ? `in ~${Math.round(s / 3600)}h` : `in ~${Math.round(s / 86400)}d`; };
const tone = n => (n >= 60 ? 'bad' : n >= 30 ? 'warn' : 'ok');

function Threat({ n }) {
  return <span className={`id-threat t-${tone(n)}`} title={`Threat ${n}/100`}><i style={{ transform: `scaleX(${Math.max(0.04, n / 100)})` }} /><b>{n}</b></span>;
}

export function IntelDesk({ call }) {
  const [d, setD] = useState(null);
  const [view, setView] = useState('wanted');
  const [open, setOpen] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => call('/admin/intel-desk').then(setD).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  const sweep = async () => { setBusy(true); try { await call('/admin/intel-desk/sweep', { method: 'POST' }); await load(); toast.success('Sweep done — database rebuilt.'); } catch (e) { toast.error(errorText(e)); } finally { setBusy(false); } };
  const t = d?.totals || {};
  const hist = d?.history || [];
  const peak = Math.max(1, ...hist.map(h => h.actors || 0));
  return <section className="cc-panel intel-desk m-stack" data-testid="intel-desk">
    <div className="m-card is-hot id-head">
      <div className="m-stack"><span className="m-label">INTEL DESK <em>reputation department · sweeps every 30 min</em></span>
        <p className="m-dim">Every rugger, sniper, bundler and the wallets bankrolling them, in one database. Crews are linked by who funded whom. FeeCat vetoes coins with a known crew inside; the rug shield and radar cite the same records.</p></div>
      <div className="id-kpis">{[['Tracked', t.actors], ['Ruggers', t.rugger], ['Funders', t.funder], ['Bundlers', t.bundler], ['Snipers', t.sniper], ['Crews', t.rings], ['Active 24h', t.active24h], ['New 7d', t.new7d]].map(([l, v]) =>
        <div key={l} className="m-stat"><small>{l}</small><b className="m-num sm">{v ?? '…'}</b></div>)}</div>
      <div className="id-trend"><small className="m-dim">Database size, last 30 days</small><div className="m-bars">{(hist.length ? hist : [{}]).map((h, i) => <i key={i} className={h.actors ? '' : 'zero'} style={{ transform: `scaleY(${Math.max(0.06, (h.actors || 0) / peak)})` }} title={`${h.day || ''} · ${h.actors || 0} tracked`} />)}</div></div>
      <button type="button" className="m-btn" disabled={busy} onClick={sweep}>{busy ? 'Sweeping…' : '↻ Sweep now'}</button>
    </div>
    <div className="m-seg" role="tablist">{VIEWS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'active' : ''} onClick={() => setView(k)}>{l}{k === 'moves' && d?.moves?.length ? ` ${d.moves.length}` : ''}</button>)}</div>

    {view === 'lookup' && <InvestigatePanel />}
    {view !== 'lookup' && !d && <p className="cc-empty">Opening the files…</p>}

    {view === 'wanted' && d && <div className="m-card id-list m-scroll">{!d.wanted.length ? <p className="m-dim">Nobody on file yet. Every coin FEELESS inspects adds its snipers, bundlers and their funders here.</p>
      : d.wanted.map(a => <div key={a.address} className={`id-row ${open === a.address ? 'is-open' : ''}`}>
        <button type="button" className="id-main" onClick={() => setOpen(open === a.address ? null : a.address)} aria-expanded={open === a.address}>
          <Threat n={a.threat} /><code>{shortAddress(a.address)}</code>
          <span className="id-roles">{a.roles.map(r => <span key={r} className={`m-chip ${ROLE[r]?.[1] || ''}`}>{ROLE[r]?.[0]} {r}</span>)}</span>
          <span className="m-dim">{a.strikes} strikes · {a.launches} launches{a.funded ? ` · ${a.funded} funded` : ''}</span>
          {a.ring && <span className="m-chip warn">crew {a.ring}</span>}<em className="m-dim">{ago(a.lastSeen)}</em></button>
        {open === a.address && <div className="id-detail m-pop">
          <dl className="m-kv">{a.evidence.map((e, i) => <React.Fragment key={i}><dt>+{e.weight} · {e.source}</dt><dd>{e.claim}</dd></React.Fragment>)}</dl>
          {a.moves.length > 0 && <div className="m-stack">{a.moves.map((m, i) => <div key={i} className={`m-note ${m.confidence === 'high' ? 'bad' : 'warn'}`}><b>{m.move} {eta(m.eta)}</b>{m.why} · {m.confidence} confidence</div>)}</div>}
          <div className="m-row">{a.fundedBy && <button type="button" className="m-btn" onClick={() => setOpen(a.fundedBy)}>↑ Funded by {shortAddress(a.fundedBy)}</button>}
            <button type="button" className="m-btn primary" onClick={() => investigate(a.address)}>🔎 Open case file</button></div>
        </div>}
      </div>)}</div>}

    {view === 'crews' && d && <div className="m-grid">{!d.rings.length ? <p className="m-dim">No crews linked yet. A crew appears when one wallet funds two or more offenders.</p>
      : d.rings.map(r => <div key={r.id} className={`m-card id-crew t-${tone(r.threat)}`}>
        <div className="m-row"><span className="m-label">CREW {r.id}</span><Threat n={r.threat} /></div>
        <div className="m-row"><span className="m-chip">{r.size} wallets</span><span className="m-chip">{r.launchesHit} launches hit</span>{r.rugs > 0 && <span className="m-chip bad">{r.rugs} rugs</span>}<span className="m-dim">active {ago(r.lastActive)}</span></div>
        <div className="m-stack id-members m-scroll">{r.members.slice(0, 12).map(m => <button key={m} type="button" className="m-btn" onClick={() => investigate(m)}>{m === r.core ? '🏦 ' : ''}{shortAddress(m)}</button>)}</div>
      </div>)}</div>}

    {view === 'moves' && d && <div className="m-card m-stack">{!d.moves.length ? <p className="m-dim">No predicted moves right now.</p>
      : d.moves.map((m, i) => <button key={i} type="button" className={`m-note ${m.confidence === 'high' ? 'bad' : m.confidence === 'medium' ? 'warn' : ''} id-move`} onClick={() => investigate(m.address)}>
        <b>{m.move} {eta(m.eta)}</b><span>{shortAddress(m.address)}{m.ring ? ` · crew ${m.ring}` : ''} · threat {m.threat} · {m.why}</span></button>)}</div>}
  </section>;
}

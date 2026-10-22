import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { useGlide } from '../../lib/useGlide';
import { FamilyCrest } from '../FamilyCrest';
import '../../styles/overwatch.css';

// 👑 OVERWATCH — the creator's eye on every family (owner, 2026-10-22; backend admin_familia_overwatch, owner-signed, read-only). Lives in
// HQ › 🏙 Familia and pops out in the city from the creator's own door. Each family = a drawn dossier card: crest, the creator's crown, power
// against the top family, bank + war chest meters, the week's verified trades as a P&L ring, seats filled, W/L, turf + home, buildings set to
// real pools (live APY), fees paid, every member's wallet (tap to copy) with their own week. Up top: the city's totals that glide, sort chips.
const n0 = x => Math.round(Number(x) || 0).toLocaleString('en-US');
const usd = v => { const a = Math.abs(Number(v) || 0); const s = a >= 1e6 ? `${(a / 1e6).toFixed(1)}M` : a >= 1e3 ? `${(a / 1e3).toFixed(1)}K` : a.toFixed(a >= 100 ? 0 : 2); return `${Number(v) < 0 ? '-' : ''}$${s}`; };
const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '—');
const SORTS = [['power', 'POWER'], ['bankMp', 'BANK'], ['pnl', 'P&L 7D'], ['members', 'CREW']];
// pure: the families in the chosen order (the creator's family stays first)
export function owSort(fams, by) {
  const k = f => (by === 'pnl' ? f.week?.usd || 0 : by === 'members' ? (f.members || []).length : f[by] || 0);
  return [...(fams || [])].sort((a, b) => (b.creator - a.creator) || (k(b) - k(a)));
}

function Kpi({ label, v, fmt = n0, i }) {
  const g = useGlide(Number(v) || 0);
  return <span className="ow-kpi" style={{ '--i': i }}><b className={Number(v) < 0 ? 'is-neg' : ''}>{fmt(g)}</b><em>{label}</em></span>;
}

function Ring({ pct }) {
  const p = Math.max(-100, Math.min(100, Number(pct) || 0)); const C = 2 * Math.PI * 16;
  return <svg className={`ow-ring ${p < 0 ? 'is-neg' : ''}`} viewBox="0 0 40 40" aria-hidden><circle cx="20" cy="20" r="16" className="ow-rbg" />
    <circle cx="20" cy="20" r="16" className="ow-rfg" strokeDasharray={`${(C * Math.max(3, Math.abs(p))) / 100} ${C}`} /></svg>;
}

function Dossier({ f, top, i, open, onOpen }) {
  const w = f.week || {}; const seats = Math.max(1, f.seats || 5); const filled = (f.members || []).length;
  const copy = a => { try { navigator.clipboard.writeText(a); toast.success('Wallet copied'); } catch { toast.error('Copy blocked by the browser'); } };
  return <article className={`ow-card ${f.creator ? 'is-creator' : ''}`} style={{ '--i': i, '--fc': f.badge?.c1 || '#d4af37' }} data-testid={`ow-fam-${f.id}`}>
    <span className="ow-sheen" aria-hidden />
    <header className="ow-head">
      <span className="ow-crest">{f.badge ? <FamilyCrest b={f.badge} px={44} banner={false} sheen={false} /> : null}{f.creator ? <b className="ow-crown" aria-hidden /> : null}</span>
      <span className="ow-name"><em>[{f.tag}]{f.creator ? ' · CREATOR' : ''}</em><b>{f.name}</b><small>Don {f.owner?.name || short(f.owner?.address)}</small></span>
      <span className="ow-pnl" data-tip={`${w.trades || 0} verified FEELESS trades by members this week · ${w.wonPct ?? '—'}% won`}><Ring pct={w.pct} />
        <b className={(w.usd || 0) < 0 ? 'is-neg' : 'is-pos'}>{usd(w.usd || 0)}</b><small>{w.trades || 0} TRADES · 7D</small></span>
    </header>
    <div className="ow-bars">
      <p data-tip="Family power against the strongest family"><em>POWER</em><u><s style={{ transform: `scaleX(${Math.max(0.02, (f.power || 0) / Math.max(1, top.power))})` }} /></u><b>{n0(f.power)}</b></p>
      <p data-tip="MP in the family bank"><em>BANK</em><u><s style={{ transform: `scaleX(${Math.max(0.02, (f.bankMp || 0) / Math.max(1, top.bankMp))})` }} /></u><b>{n0(f.bankMp)} MP</b></p>
      <p data-tip="War chest (points) and the war record"><em>CHEST</em><u><s style={{ transform: `scaleX(${Math.max(0.02, (f.chest || 0) / Math.max(1, top.chest))})` }} /></u><b>{n0(f.chest)} · {f.record?.wins || 0}W {f.record?.losses || 0}L</b></p>
      <p data-tip={`${filled} of ${seats} seats filled`}><em>SEATS</em><span className="ow-seats">{Array.from({ length: Math.min(seats, 20) }, (_, k) => <i key={k} className={k < filled ? 'is-on' : ''} />)}</span><b>{filled}/{seats}</b></p>
    </div>
    <div className="ow-chips">
      <span data-tip="Home block + turf">🏠 {f.home || '—'}{(f.turf || []).length ? ` · +${f.turf.length} turf` : ''}</span>
      <span data-tip="Fees this family paid FEELESS (create, seats, badge)">💳 {usd(f.paidUsd || 0)} · {f.payments || 0} paid</span>
      {(f.pools || []).map(p => <span key={p.block} className="is-pool" data-tip={`${p.block} is set to this pool`}>🏦 {p.name}{p.apy != null ? ` · ${Number(p.apy).toFixed(1)}%` : ''}</span>)}
      {f.launch ? <span className="is-launch" data-tip="The family's pinned launch">🚀 ${f.launch.symbol}</span> : null}
    </div>
    <button type="button" className="ow-more" aria-expanded={open} onClick={onOpen} data-testid={`ow-open-${f.id}`} data-tip="Every member's wallet and their verified week">{open ? '▾' : '▸'} {filled} member{filled === 1 ? '' : 's'} · wallets + trades</button>
    {open ? <ol className="ow-mem">{(f.members || []).map((m, k) => <li key={m.address} style={{ '--i': k }}>
      <b>{m.don ? '👑 ' : ''}{m.name}</b><button type="button" className="ow-addr" onClick={() => copy(m.address)} data-tip="Tap to copy the wallet">{short(m.address)}</button>
      <small>{m.trades || 0} trades{m.wonPct != null ? ` · ${m.wonPct}% won` : ''}</small><em className={(m.usd || 0) < 0 ? 'is-neg' : 'is-pos'}>{usd(m.usd || 0)}</em></li>)}</ol> : null}
  </article>;
}

export function FamiliaOverwatch({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [by, setBy] = useState('power'); const [q, setQ] = useState(''); const [open, setOpen] = useState(null);
  useEffect(() => { let on = true;
    const go = () => Promise.resolve().then(() => call('/admin/familia/overwatch')).then(x => { if (on) { setD(x); setErr(''); } }).catch(e => { if (on) setErr(String(e?.message || e)); });
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 30000); return () => { on = false; clearInterval(t); }; }, [call]);
  const fams = useMemo(() => owSort((d?.families || []).filter(f => !q || `${f.tag} ${f.name}`.toLowerCase().includes(q.toLowerCase())), by), [d, by, q]);
  const top = useMemo(() => ({ power: Math.max(1, ...(d?.families || []).map(f => f.power || 0)), bankMp: Math.max(1, ...(d?.families || []).map(f => f.bankMp || 0)), chest: Math.max(1, ...(d?.families || []).map(f => f.chest || 0)) }), [d]);
  if (!d) return <p className="ow-wait">{err || 'Opening the files…'}</p>;
  const t = d.totals || {};
  return <section className="ow" data-testid="familia-overwatch">
    <header className="ow-top"><span className="ow-title"><em>CREATOR ONLY</em><b>👑 OVERWATCH</b><small>every family · read-only · refreshes every 30s</small></span>
      <div className="m-seg ow-sort" role="radiogroup" aria-label="Sort families">{SORTS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={by === k} className={by === k ? 'active' : ''} onClick={() => setBy(k)} data-testid={`ow-sort-${k}`}>{l}</button>)}</div>
      <input className="m-input ow-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Find a family…" aria-label="Find a family" /></header>
    <div className="ow-kpis">{[['FAMILIES', t.families], ['MEMBERS', t.members], ['MP IN BANKS', t.bankMp], ['TRADES 7D', t.trades7d], ['P&L 7D', t.usd7d, usd], ['FEES PAID', t.paidUsd, usd], ['TURF', t.turf], ['POOL BUILDINGS', t.pools]]
      .map(([l, v, f], i) => <Kpi key={l} label={l} v={v} fmt={f} i={i} />)}</div>
    <div className="ow-grid">{fams.map((f, i) => <Dossier key={f.id} f={f} top={top} i={i} open={open === f.id} onOpen={() => setOpen(o => (o === f.id ? null : f.id))} />)}
      {!fams.length ? <p className="ow-wait">No family matches.</p> : null}</div>
    <div className="ow-rules"><span className="ow-lbl">💵 PRICING · LIMITS</span>
      {[['Start a family', usd(d.pricing?.createUsd)], ['+5 seats', usd(d.pricing?.packUsd)], ['Badge restyle', usd(d.pricing?.badgeUsd)], ['Seats at start', d.pricing?.baseSeats],
        ...Object.entries(d.limits || {}).map(([k, v]) => [k.replace(/([A-Z])/g, ' $1').toLowerCase(), n0(v)])].map(([k, v]) => <span key={k} className="ow-rule"><em>{k}</em><b>{v}</b></span>)}
      <p className="ow-note">{d.custody} Prices + rules are set in HQ › 🏙 Familia.</p></div>
  </section>;
}

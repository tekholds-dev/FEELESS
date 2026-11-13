import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { toast } from 'sonner';
import { useCountUp } from '../../lib/useCountUp';
import { isCalm } from '../../lib/fxPause';
import '../../styles/warRoom.css';

// ⚔️ SEC-1 WAR ROOM (owner-only, HQ › Safety). One live dashboard over backend/war_room.py: the attempts feed, a 24h timeline, decoy
// captures, canary tokens + who opened them, auto-banned subnets + hardening moves, an on-chain trace + evidence pack, the bounty scope,
// the exploit→hardening list and the defender's attacker-methods encyclopedia. Everything is observed on FEELESS's own property; it never
// contacts an attacker (that stays OFF THE TABLE). Polls every 8s; tokens only; transform/opacity animation.
const KIND_META = {
  probe: ['👁', 'probe'], block: ['⛔', 'block'], decoy: ['🪤', 'decoy served'], tarpit: ['🐢', 'tarpit'], replay: ['♻️', 'session replay'],
  canary: ['🔔', 'canary opened'], 'canary-key': ['🔑', 'planted key used'], harden: ['🛡', 'auto-harden'], guard: ['🚧', 'guard'],
  report: ['📨', 'bounty report'], trace: ['🔗', 'trace'],
};
const ago = s => (s < 90 ? `${Math.round(s)}s` : s < 5400 ? `${Math.round(s / 60)}m` : s < 172800 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`);
const clock = at => { try { return new Date(at * 1000).toLocaleTimeString(); } catch { return '—'; } };

function Kpi({ k, n, tip }) { const v = useCountUp(Number(n) || 0); return <span data-tip={tip}><em>{k}</em><b className="m-num">{n == null ? '—' : v}</b></span>; }

function Timeline({ rows }) {
  const data = useMemo(() => (rows || []).map(r => {
    const { h, ...k } = r; const total = Object.values(k).reduce((a, c) => a + c, 0);
    return { t: new Date(h * 1000).getHours() + ':00', total };
  }), [rows]);
  if (!data.length) return null;
  return <div className="war-tl" data-testid="war-timeline"><ResponsiveContainer width="100%" height={90}>
    <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barSize={9}>
      <XAxis dataKey="t" tick={{ fontSize: 9, fill: 'var(--m-mute)' }} interval={3} axisLine={false} tickLine={false} />
      <YAxis hide /><Tooltip cursor={{ fill: 'color-mix(in srgb, var(--m-accent) 10%, transparent)' }} contentStyle={{ background: 'var(--m-surface)', border: '1px solid var(--m-line)', borderRadius: 8, fontSize: 11 }} />
      <Bar dataKey="total" fill="var(--m-accent)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
    </BarChart></ResponsiveContainer></div>;
}

function Feed({ feed }) {
  if (!feed?.length) return <p className="m-dim war-quiet">Quiet — no probe seen yet. The decoys and canaries are set.</p>;
  return <ul className="war-feed" data-testid="war-feed">{feed.slice(0, 40).map((e, i) => {
    const [ic, lbl] = KIND_META[e.kind] || ['•', e.kind];
    return <li key={e.seq} style={{ '--i': i }} className={`k-${e.kind}`}><span className="war-ic" aria-hidden="true">{ic}</span>
      <b>{lbl}</b><span className="war-src">{e.ip || '—'}{e.net ? ` · ${e.net}` : ''}</span>
      <span className="war-what">{e.method} {e.path}{e.action ? ` — ${e.action}` : ''}</span><small>{clock(e.at)}</small></li>;
  })}</ul>;
}

export function WarRoom({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [wallet, setWallet] = useState(''); const [trace, setTrace] = useState(null); const [busy, setBusy] = useState('');
  const load = useCallback(() => { if (document.hidden) return; call('/admin/security/war-room').then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message || 'load failed')); }, [call]);
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, [load]);

  const runTrace = () => { const w = wallet.trim(); if (!w) return; setBusy('trace');
    call('/admin/security/war-room/trace', { method: 'POST', body: JSON.stringify({ wallet: w }) })
      .then(x => { setTrace(x); toast.success('Traced — evidence pack ready'); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const copy = (t, msg) => { try { navigator.clipboard.writeText(t); toast.success(msg || 'Copied'); } catch { toast.error('Copy blocked'); } };
  const evidence = () => { setBusy('ev'); call('/admin/security/war-room/evidence', { method: 'POST', body: '{}' }).then(x => copy(x.pack, 'Evidence pack copied — send it to the exchange / IC3')).catch(e => toast.error(e.message)).finally(() => setBusy('')); };

  if (err && !d) return <section className="m-card war" data-testid="war-room"><div className="m-row"><span className="m-label">⚔️ War Room</span></div><p className="m-dim">{err}</p></section>;
  const c = d?.counts || {}; const live = d?.feed?.length && (Date.now() / 1000 - d.feed[0].at) < 60;

  return <div className="war" data-testid="war-room">
    <section className="m-card war-hero">
      <div className="m-row"><span className="m-label">⚔️ WAR ROOM · LIVE</span><small className="m-dim">every probe on FEELESS, our decoys + canaries, auto-hardening, tracing — all on our own property, never a counter-attack</small>
        <span className={`war-dot${live ? ' is-on' : ''}`} aria-hidden="true" /></div>
      <div className="war-kpis">
        <Kpi k="EVENTS" n={c.events} tip="Security events in the ring" />
        <Kpi k="DECOY HITS" n={c.captures} tip="Scanner requests served a fake page + captured" />
        <Kpi k="CANARIES" n={c.canaries} tip="Tracking tokens planted in decoys" />
        <Kpi k="OPENED" n={c.opens} tip="Canaries later opened → opener's real IP/UA logged" />
        <Kpi k="KEY TRIPS" n={c.keyUses} tip="Planted fake keys presented back to our API" />
        <Kpi k="SUBNETS BANNED" n={c.nets} tip="/24 (or /48) banned for running scanners" />
        <Kpi k="SESSIONS REVOKED" n={c.revoked} tip="HQ sessions reused from a 2nd device → revoked" />
        <Kpi k="REPORTS" n={c.reports} tip="Bounty / disclosure reports in the inbox" />
      </div>
      <Timeline rows={d?.timeline} />
    </section>

    <div className="war-grid">
      <section className="m-card"><div className="m-row"><span className="m-label">📡 LIVE ATTEMPTS</span><small className="m-dim">newest first</small></div><Feed feed={d?.feed} /></section>

      <section className="m-card"><div className="m-row"><span className="m-label">🔔 CANARY TOKENS · WHO OPENED</span><small className="m-dim">a beacon only phones home — it runs nothing</small></div>
        {d?.hits?.length ? <ul className="war-list">{d.hits.slice(0, 12).map((h, i) => <li key={`${h.tok}-${h.at}`} style={{ '--i': i }}><b>🔔 {h.ip}</b><span>{h.ua?.slice(0, 48) || '—'}{h.lang ? ` · ${h.lang}` : ''}</span><small>{clock(h.at)}</small></li>)}</ul>
          : <p className="m-dim war-quiet">No canary opened yet. {c.canaries || 0} planted and waiting.</p>}
        {d?.captures?.length ? <details className="war-cap"><summary>🪤 {d.captures.length} decoy captures · payloads</summary>
          <ul className="war-list">{d.captures.slice(0, 10).map((x, i) => <li key={`${x.ip}-${x.at}`} style={{ '--i': i }}><b>{x.method} {x.path}</b><span>{x.ip} · {x.ua?.slice(0, 40)}</span><small>{x.bodyLen ? `${x.bodyLen}B body` : ''} {clock(x.at)}</small></li>)}</ul></details> : null}
      </section>

      <section className="m-card"><div className="m-row"><span className="m-label">🛡 AUTO-HARDENING · LIVE MOVES</span></div>
        {d?.moves?.length ? <ul className="war-list is-move">{d.moves.slice(0, 10).map((m, i) => <li key={`${m.kind}-${m.at}`} style={{ '--i': i }}><b>{m.kind === 'ban-net' ? '⛔ banned subnet' : m.kind === 'revoke-session' ? '♻️ revoked session' : m.kind}</b><span>{m.net || m.why}</span><small>{clock(m.at)}</small></li>)}</ul>
          : <p className="m-dim war-quiet">No auto-move yet — nothing crossed a pattern.</p>}
        {d?.nets?.length ? <p className="war-nets" data-tip="Subnets currently banned">⛔ {d.nets.length} subnets banned: {d.nets.slice(0, 4).map(n => n.net).join(' · ')}{d.nets.length > 4 ? '…' : ''}</p> : null}
      </section>

      <section className="m-card"><div className="m-row"><span className="m-label">🔗 ON-CHAIN TRACE → EVIDENCE PACK</span></div>
        <p className="m-dim war-note">Follow a suspect wallet's outbound transfers (read-only). Build a plain evidence pack for an exchange / IC3 — a freeze on cash-out, never a counter-hack.</p>
        <div className="war-trace-in"><input className="m-input" placeholder="suspect wallet address" value={wallet} onChange={e => setWallet(e.target.value)} data-testid="war-trace-wallet" />
          <button type="button" className="m-btn" disabled={busy === 'trace' || !wallet.trim()} onClick={runTrace}>{busy === 'trace' ? 'Tracing…' : 'Trace'}</button>
          <button type="button" className="m-btn" disabled={busy === 'ev'} onClick={evidence} data-tip="Copy the current evidence pack">Evidence pack</button></div>
        {trace?.trace ? <div className="war-trace-out"><b className="m-num sm">{trace.trace.outCount} out · {trace.trace.counterparties} counterparties</b>
          <ul className="war-list">{(trace.trace.hops || []).slice(0, 8).map((h, i) => <li key={h.to} style={{ '--i': i }}><b>{h.amount} SOL</b><span>→ {h.to}</span><small>{h.n}×</small></li>)}</ul>
          <button type="button" className="m-btn" onClick={() => copy(trace.pack, 'Evidence pack copied')}>Copy pack</button></div> : null}
      </section>

      <section className="m-card war-wide"><div className="m-row"><span className="m-label">🧱 EXPLOIT RESEARCH → FEELESS HARDENING</span><small className="m-dim">recent real attacks, each a concrete defence</small></div>
        {d?.hardening?.items?.length ? <ul className="war-hard">{d.hardening.items.map((h, i) => <li key={h.id} style={{ '--i': i }} className={`s-${h.state}`}>
          <div className="war-hard-h"><b>{h.attack}</b><em className={`war-chip is-${h.state}`}>{h.state}</em></div>
          <span className="war-how">{h.how}</span><span className="war-fix">✓ {h.item}</span><small className="m-dim">source: {h.source}</small></li>)}</ul> : <p className="m-dim">Loading…</p>}
      </section>

      <section className="m-card war-wide"><div className="m-row"><span className="m-label">📖 ATTACKER METHODS · FOR DEFENDERS</span><small className="m-dim">{d?.encyclopedia?.intro}</small></div>
        {d?.encyclopedia?.entries?.length ? <ul className="war-enc">{d.encyclopedia.entries.map((e, i) => <li key={e.id} style={{ '--i': i }}>
          <b>{e.name}</b><span className="war-how">{e.how}</span><span className="war-fix">🛡 {e.defence}</span></li>)}</ul> : null}
      </section>

      <section className="m-card war-wide"><div className="m-row"><span className="m-label">🏆 BOUNTY · RESPONSIBLE DISCLOSURE</span><small className="m-dim">turns probing into paid testing</small></div>
        {d?.bounty ? <div className="war-bounty"><p className="m-dim">{d.bounty.intro}</p>
          <div className="war-bounty-cols">
            <div><h5>In scope</h5><ul>{d.bounty.inScope.map(x => <li key={x}>✓ {x}</li>)}</ul></div>
            <div><h5>Out of scope</h5><ul>{d.bounty.outOfScope.map(x => <li key={x}>✕ {x}</li>)}</ul></div>
            <div><h5>Rules</h5><ul>{d.bounty.rules.map(x => <li key={x}>• {x}</li>)}</ul></div>
          </div>
          <p className="m-dim war-note">Public form: <code>POST /api/reputation/security/bounty</code>. Reports land in the feed above; you decide every payout.</p></div> : null}
        {d?.reports?.length ? <ul className="war-list">{d.reports.slice(0, 6).map((r, i) => <li key={r.at} style={{ '--i': i }}><b>{r.wallet || r.url || 'anon'}</b><span>{r.detail?.slice(0, 80)}</span><small>{clock(r.at)}</small></li>)}</ul> : null}
      </section>
    </div>
  </div>;
}

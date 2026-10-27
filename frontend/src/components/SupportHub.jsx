import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { readChatSession } from '../lib/chatSession';
import { ReportBug } from './ReportBug';
import '../styles/supportHub.css';

// 🛟 SUPPORT HUB (owner, 2026-10-20: "support with a visual live animated grid of bugs / reports auto-sorted by importance, community polls —
// enough votes climb the ladder of approval — a support button in vital areas that leads to roadmap + whitepaper, and its own huge section").
// One page, three lenses: 🐞 Reports (live grid, importance-sorted, +1 "me too") · 🗳 Polls (propose, vote, the ladder) · 📝 Report it.
export const LENSES = [['reports', '🐞 Reports'], ['ideas', '💡 Ideas'], ['polls', '🗳 Polls'], ['send', '📝 Report it']];
const STATUS = { open: ['🟠', 'OPEN'], fixing: ['🔨', 'FIXING'], fixed: ['✅', 'FIXED'], wontfix: ['✕', "WON'T FIX"] };
const KIND = { bug: '🐞', idea: '💡', security: '🔒' };
export const heat = i => (i >= 70 ? 'hot' : i >= 40 ? 'warm' : 'cool');

export function SupportButton({ compact }) {
  return <Link to="/terminal/support" className={`sup-btn${compact ? ' is-compact' : ''}`} data-testid="support-btn" data-tip="Report a bug, vote on what we build next, read the roadmap">🛟 {compact ? '' : 'Support'}</Link>;
}

function Ladder({ ladder, polls }) {
  const n = k => polls.filter(p => p.stage?.key === k).length;
  return <ol className="sup-ladder" aria-label="Approval ladder">{[...ladder, { key: 'roadmap', label: '🗺 ON THE ROADMAP', at: null }].map((r, i) => <li key={r.key} style={{ '--i': i }}>
    <b>{r.label}</b><small>{r.at != null ? `${r.at}+ votes` : 'the owner decides'}</small><i>{n(r.key)}</i></li>)}</ol>;
}

// 👍 👎 💬 on every card (owner 2026-10-26): one vote per wallet (tap again to clear), comments drop down under the card
function CardActs({ id, d, act, busy }) {
  const [open, setOpen] = useState(false); const [t, setT] = useState('');
  const r = d?.reacts?.[id] || { up: 0, down: 0, mine: 0 }; const cs = d?.comments?.[id] || [];
  return <div className="sup-acts" data-testid={`sup-acts-${id}`}>
    <button type="button" className={r.mine === 1 ? 'is-on' : ''} disabled={!!busy} onClick={() => act({ react: id, v: 1 }, `r${id}`)} aria-pressed={r.mine === 1} data-tip="Like">👍 {r.up || ''}</button>
    <button type="button" className={r.mine === -1 ? 'is-on is-dn' : ''} disabled={!!busy} onClick={() => act({ react: id, v: -1 }, `r${id}`)} aria-pressed={r.mine === -1} data-tip="Dislike">👎 {r.down || ''}</button>
    <button type="button" className={open ? 'is-on' : ''} onClick={() => setOpen(!open)} aria-expanded={open} data-tip="Comments">💬 {cs.length || ''}</button>
    {open ? <div className="sup-thread"><ul>{cs.map((c, i) => <li key={i}><b>{c.by.slice(0, 4)}…{c.by.slice(-4)}</b><span>{c.text}</span></li>)}{!cs.length ? <li className="sup-none">No comments yet.</li> : null}</ul>
      <form onSubmit={async e => { e.preventDefault(); if (await act({ comment: id, text: t }, `c${id}`)) setT(''); }}><input className="m-input" value={t} maxLength={280} placeholder="Add a comment…" onChange={e => setT(e.target.value)} aria-label="Comment" />
        <button type="submit" className="m-btn" disabled={t.trim().length < 2 || !!busy}>Send</button></form></div> : null}
  </div>;
}

export function SupportHub() {
  const { wallet } = useWallet() || {}; const me = wallet?.address || ''; const sess = me ? readChatSession(me) : '';
  const [lens, setLens] = useState('reports'); const [d, setD] = useState(null); const [kind, setKind] = useState('all'); const [busy, setBusy] = useState('');
  const [q, setQ] = useState(''); const [opts, setOpts] = useState(['', '']); const [idea, setIdea] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/support${me ? `?wallet=${me}` : ''}`)).then(r => r.json()).then(setD).catch(() => {}), [me]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [load]);
  const act = async (body, tag) => {
    if (!me || !sess) { toast.error('Connect your wallet and open chat once to sign in (one signature, 7 days).'); return false; }
    setBusy(tag);
    try { const r = await fetch(apiUrl('/api/reputation/support'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ wallet: me, session: sess, ...body }) });
      const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Could not save'); setD(x); return true; } catch (e) { toast.error(e.message); return false; } finally { setBusy(''); }
  };
  const rows = useMemo(() => (d?.reports || []).filter(r => kind === 'all' || r.kind === kind), [d, kind]);
  const c = d?.counts || {};
  return <section className="sup" data-testid="support-hub">
    <div className="sup-hero m-card m-live"><div><span className="eyebrow">FEELESS · SUPPORT</span><h1>Tell us. Vote on it. <em>Watch it ship.</em></h1>
      <p>Every report lands here, sorted by how many people it hits. Ideas go to a vote — enough votes climb the ladder, and the top of the ladder goes on the roadmap.</p>
      <div className="sup-links"><Link to="/terminal/roadmap">🗺 Roadmap</Link><Link to="/terminal/whitepaper">📄 Whitepaper</Link><Link to="/terminal/learn">📚 Learn</Link></div></div>
      <div className="sup-kpis">{[['OPEN', c.open, 'warn'], ['FIXING', c.fixing, ''], ['FIXED', c.fixed, 'ok'], ['POLLS', c.polls, '']].map(([k, v, t], i) => <span key={k} className={t ? `t-${t}` : ''} style={{ '--i': i }}><em>{k}</em><b key={String(v)}>{v ?? '—'}</b></span>)}</div></div>
    <nav className="sup-lens m-seg" role="tablist">{LENSES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`sup-lens-${k}`}>{l}</button>)}</nav>
    {lens === 'reports' ? <>
      <div className="sup-filter">{[['all', 'All'], ['bug', '🐞 Bugs'], ['idea', '💡 Ideas'], ['security', '🔒 Security']].map(([k, l]) => <button key={k} type="button" className={kind === k ? 'on' : ''} onClick={() => setKind(k)}>{l}</button>)}</div>
      {!d ? <p className="sup-empty">Reading the board…</p> : !rows.length ? <p className="sup-empty">🟢 Nothing reported here. Seen something? 📝 Report it.</p>
        : <div className="sup-grid" data-testid="sup-grid">{rows.map((r, i) => { const [ic, st] = STATUS[r.status] || STATUS.open; const mine = (d.mine || []).includes(r.id);
          return <article key={r.id} className={`sup-card h-${heat(r.importance)} s-${r.status}`} style={{ '--i': Math.min(i, 20) }} data-testid="sup-card">
            <header><i>{KIND[r.kind] || '🐞'}</i><span className="sup-area">{r.area}</span><span className="sup-st">{ic} {st}</span></header>
            <b className="sup-title">{r.title}</b>
            <div className="sup-imp"><u style={{ transform: `scaleX(${Math.max(0.04, r.importance / 100)})` }} /></div>
            <footer><small>{r.count}× hit · importance {r.importance}</small>
              <button type="button" className={`sup-plus${mine ? ' is-on' : ''}`} disabled={!!busy} aria-pressed={mine} onClick={() => act({ plus: r.id }, r.id)} data-testid="sup-plus">👍 me too {r.plus || ''}</button></footer>
            <CardActs id={r.id} d={d} act={act} busy={busy} />
          </article>; })}</div>}
    </> : null}
    {lens === 'polls' ? <>
      <Ladder ladder={d?.ladder || []} polls={d?.polls || []} />
      <form className="sup-new m-card" onSubmit={async e => { e.preventDefault(); if (await act({ q, options: opts }, 'new')) { setQ(''); setOpts(['', '']); toast.success('🗳 poll is live'); } }}>
        <b>🗳 Ask the community</b>
        <input className="m-input" value={q} maxLength={140} placeholder="What should FEELESS build next?" onChange={e => setQ(e.target.value)} aria-label="Question" />
        <div className="sup-opts">{opts.map((o, i) => <input key={i} className="m-input" value={o} maxLength={60} placeholder={`Option ${i + 1}`} aria-label={`Option ${i + 1}`} onChange={e => setOpts(x => x.map((y, j) => (j === i ? e.target.value : y)))} />)}
          {opts.length < 5 ? <button type="button" className="m-btn" onClick={() => setOpts(x => [...x, ''])}>＋ option</button> : null}</div>
        <button type="submit" className="m-btn m-go" disabled={busy === 'new' || q.trim().length < 8 || opts.filter(o => o.trim()).length < 2} data-testid="sup-post">Post poll</button>
      </form>
      <div className="sup-polls">{(d?.polls || []).map((p, i) => { const tot = Math.max(1, p.votes);
        return <article key={p.id} className={`sup-poll k-${p.stage?.key}`} style={{ '--i': Math.min(i, 20) }} data-testid="sup-poll">
          <header><span className="sup-stage">{p.stage?.label}</span><small>{p.votes} vote{p.votes === 1 ? '' : 's'}{p.stage?.next ? ` · ${p.stage.next.need} more → ${p.stage.next.label}` : ''}</small></header>
          <b>{p.q}</b>{p.note ? <p className="sup-note">📌 {p.note}</p> : null}
          <CardActs id={p.id} d={d} act={act} busy={busy} />
          <ul>{p.options.map((o, j) => <li key={j}><button type="button" className={p.mine === j ? 'is-mine' : ''} disabled={!!busy || ['roadmap', 'building', 'shipped', 'declined'].includes(p.stage?.key)}
            onClick={() => act({ poll: p.id, opt: j }, p.id)} data-testid={`sup-vote-${j}`}><span>{o}</span><i style={{ transform: `scaleX(${p.tally[j] / tot})` }} /><b>{Math.round((100 * p.tally[j]) / tot)}%</b></button></li>)}</ul>
        </article>; })}{!(d?.polls || []).length ? <p className="sup-empty">No polls yet — ask the first question.</p> : null}</div>
    </> : null}
    {lens === 'ideas' ? <>
      <form className="sup-new m-card" onSubmit={async e => { e.preventDefault(); if (await act({ idea: true, text: idea }, 'idea')) { setIdea(''); toast.success('💡 idea posted'); } }}>
        <b>💡 Pitch an idea</b><textarea className="m-input" rows="2" value={idea} maxLength={280} placeholder="What would make FEELESS better? One or two lines." onChange={e => setIdea(e.target.value)} aria-label="Your idea" />
        <button type="submit" className="m-btn m-go" disabled={busy === 'idea' || idea.trim().length < 8} data-testid="sup-idea-post">Post idea</button></form>
      <div className="sup-grid" data-testid="sup-ideas">{(d?.ideas || []).map((x, i) => { const rr = d?.reacts?.[x.id] || {}; return <article key={x.id} className="sup-card sup-idea" style={{ '--i': Math.min(i, 20) }}>
        <header><i>💡</i><span className="sup-area">{x.by.slice(0, 4)}…{x.by.slice(-4)}</span><span className="sup-st">▲ {(rr.up || 0) - (rr.down || 0)}</span></header>
        <b className="sup-title">{x.text}</b><CardActs id={x.id} d={d} act={act} busy={busy} /></article>; })}
        {!(d?.ideas || []).length ? <p className="sup-empty">No ideas yet — pitch the first one.</p> : null}</div>
    </> : null}
    {lens === 'send' ? <div className="sup-send m-card"><p>Bugs, ideas and security reports go straight to the FEELESS team. The same crash on the same page is merged into one card with a count.</p><ReportBug address={me} /></div> : null}
  </section>;
}

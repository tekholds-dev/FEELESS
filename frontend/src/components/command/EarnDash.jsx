import React, { useEffect, useState } from 'react';
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, YAxis } from 'recharts';
import { ChevronDown, ExternalLink, Zap } from 'lucide-react';
import { EcoLive } from './EcoLive';
import { boxRef } from '../../lib/boxRef';
import '../../styles/earnDash.css';

// 💼 Slice 28 · THE PoEco DESK (owner 2026-11-20: "each proof type will have a user in it for hours"; "PoEco needs to show how much it would cost
// and the brains / models needed to make it successful"). One read (earn_view → dash): jobs found with their expected profit, bids waiting for
// his approve, work in progress, money paid against what the minds cost (fees live on the receipt, never here), and the market calls.
// Find work = one tap by skill, a live feed of jobs AI can really win (few bids, clear scope, fast), and on every job what it takes to win.
const TABS = [['find', 'Find work'], ['pipe', 'Bids & work'], ['paid', 'Paid'], ['calls', 'Market calls'], ['books', 'Books']];
const TAB_KEY = 'feeless.earnDashTab';
const SKILL = { writing: 'Writing', code: 'Code', data: 'Data', research: 'Research', design: 'Design', translation: 'Translation' };
const PLAT = { superteam: 'Superteam', freelancer: 'Freelancer', algora: 'Algora' };
const STAGE = { bid: 'Waiting for your approve', bid_approved: 'Approved · send it', sent: 'Sent', won: 'Won · do the work', work: 'Work done', checked: 'Checked · approve delivery', delivery_approved: 'Delivered · mark paid' };
const STALE_MS = 30 * 60 * 1000;
const dashBox = boxRef([560, 900]);   // 📐 the window's own width (a half window on a big screen is phone-narrow), no @container
export const usd = v => (v == null ? '—' : !v ? '$0' : `${v < 0 ? '−' : ''}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v) >= 10 ? Math.abs(v).toFixed(0) : Math.abs(v) >= 0.1 ? Math.abs(v).toFixed(2) : Math.abs(v).toFixed(3)}`);
const ago = at => { const s = Math.max(0, Date.now() / 1000 - (at || 0)); return !at ? 'never read' : s < 90 ? 'read just now' : s < 3600 ? `read ${Math.round(s / 60)} min ago` : `read ${Math.round(s / 3600)} h ago`; };
const readTab = () => { try { return localStorage.getItem(TAB_KEY) || 'find'; } catch { return 'find'; } };

function Meter({ v, tone = '' }) { return <span className={`edb-meter ${tone}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></span>; }

// 🧮 the five numbers an earner opens the folder for; each one taps through to its tab
function Hero({ d, go }) {
  const up = (d.netUsd || 0) >= 0; const curve = d.curve?.length ? [{ net: 0 }, ...d.curve] : [];
  const tot = (d.paidUsd || 0) + (d.mindsUsd || 0);
  return <section className="edb-hero" data-testid="edb-hero">
    <button type="button" className={`edb-kpi edb-money m-glass m-live ${up ? 'is-up' : 'is-dn'}`} style={{ '--i': 0 }} onClick={() => go('paid')} data-tip="What the platforms paid you minus what the minds cost. Fees live on each receipt, never here" data-testid="edb-money">
      <small className="m-label">Paid − minds</small><b className={`m-num ${up ? 'm-pos' : 'm-neg'}`} data-testid="edb-net">{usd(d.netUsd)}</b>
      <em><span className="m-num">{usd(d.paidUsd)}</span> paid · <span className="m-num">{usd(d.mindsUsd)}</span> minds</em>
      <Meter v={tot ? (d.paidUsd || 0) / tot : 0} tone="is-good" />
      {curve.length > 1 ? <span className="edb-spark"><ResponsiveContainer width="100%" height={34}><AreaChart data={curve} margin={{ top: 3, right: 0, bottom: 0, left: 0 }}>
        <defs><linearGradient id="edbFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--m-accent)" stopOpacity={0.4} /><stop offset="100%" stopColor="var(--m-accent)" stopOpacity={0} /></linearGradient></defs>
        <YAxis hide domain={['dataMin', 'dataMax']} /><ReferenceLine y={0} stroke="var(--m-line-hi)" strokeDasharray="3 3" />
        <Area type="monotone" dataKey="net" stroke="var(--m-accent)" strokeWidth={1.6} fill="url(#edbFill)" isAnimationActive={false} /></AreaChart></ResponsiveContainer></span> : null}
    </button>
    <button type="button" className="edb-kpi m-glass" style={{ '--i': 1 }} onClick={() => go('find')} data-tip="Open faceless jobs on the board now, and what they could make after the minds' cost" data-testid="edb-found">
      <small className="m-label">Jobs found</small><b className="m-num">{d.found || 0}</b><em><span className="m-num">{usd(d.expUsd)}</span> expected · {d.feed || 0} AI can win</em><Meter v={d.found ? (d.feed || 0) / d.found : 0} /></button>
    <button type="button" className={`edb-kpi m-glass${d.waiting ? ' is-hot' : ''}`} style={{ '--i': 2 }} onClick={() => go('pipe')} data-tip="Bids both minds drafted. Nothing goes out until you approve and send it from your own account" data-testid="edb-waiting">
      <small className="m-label">Bids to approve</small><b className="m-num">{d.waiting || 0}</b><em>{d.sentOut || 0} approved or sent</em></button>
    <button type="button" className="edb-kpi m-glass" style={{ '--i': 3 }} onClick={() => go('pipe')} data-tip="Won jobs: the minds' work, the Collective's check, your delivery" data-testid="edb-work">
      <small className="m-label">In work</small><b className="m-num">{d.inWork || 0}</b><em>{d.paidN || 0} paid · {d.lost || 0} lost</em></button>
    <button type="button" className="edb-kpi m-glass" style={{ '--i': 4 }} onClick={() => go('calls')} data-tip="Sealed calls on live Solana pools, graded by the real numbers a day later" data-testid="edb-calls">
      <small className="m-label">Market calls</small><b className="m-num">{d.calls?.right || 0}<small>–{d.calls?.wrong || 0}</small></b><em>{d.calls?.open || 0} waiting for reality</em>
      <Meter v={(d.calls?.right || 0) + (d.calls?.wrong || 0) ? d.calls.right / (d.calls.right + d.calls.wrong) : 0} tone="is-violet" /></button>
  </section>;
}

// 🧠 WHAT IT TAKES TO WIN, before he starts (owner): the minds and models, each one's expected $, the time, the competition and the chance
export function WinPanel({ r, onBid, busy }) {
  const n = r.needs || {}; const real = r.real || {}; const c = r.competes || {};
  return <div className="edb-win" data-testid={`edb-win-${r.id}`}>
    <section><small className="m-label">Minds &amp; models</small>
      <ul className="edb-minds">{(n.minds || []).map(m => <li key={m.model}><b>{m.name}</b><span>{m.calls} calls</span><em className="m-num">{m.local ? 'free' : usd(m.usd)}</em></li>)}</ul>
      <span className="edb-kits">{(n.kits || []).join(' · ')}</span></section>
    <section><small className="m-label">Cost &amp; time</small>
      <p><b className="m-num">{usd(n.cost ?? r.cost)}</b> of model calls ({n.calls || '—'})</p>
      <p><b className="m-num">{n.days || real.minDays || 1} day{(n.days || real.minDays || 1) > 1 ? 's' : ''}</b> for the minds + your review</p>
      <p>A person: <b className="m-num">≈{real.humanHours ?? '—'} h</b> at <span className="m-num">${real.humanRate}/h</span></p></section>
    <section><small className="m-label">Competition</small>
      <p><b className="m-num">{r.rivals ?? 0}</b> already bid{n.avgBid ? <> · avg bid <b className="m-num">{usd(n.avgBid)}</b></> : null}</p>
      <span className="edb-flags">{[['few', 'Few bids'], ['clear', 'Clear scope'], ['fast', 'Fast']].map(([k, l]) => <i key={k} className={c[k] ? 'is-ok' : 'is-no'}>{c[k] ? '✓' : '✗'} {l}</i>)}</span>
      <small className="edb-why">{(c.why || []).join(' · ')}</small></section>
    <section><small className="m-label">Win</small>
      <p><b className="m-num">{Math.round((r.chance || 0) * 100)}%</b> chance <Meter v={(r.chance || 0) / 0.35} tone="is-good" /></p>
      <p>Expected <b className={`m-num ${(r.expProfit || 0) > 0 ? 'is-up' : ''}`}>{usd(r.expProfit)}</b></p>
      {real.priceHi ? <p>Realistic bid <b className="m-num">{usd(real.priceLo)}–{usd(real.priceHi)}</b> in ≥{real.minDays} d</p> : null}
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => onBid(r.id)} data-tip="Opens the 3-step start: direction, kits, research. Nothing is sent" data-testid={`edb-start-${r.id}`}>Start this job</button></section>
  </div>;
}

// 🔥 the live feed: jobs where AI can really compete, as one dense row each, with what it takes one tap away
function FeedRow({ r, i, open, onOpen, busy, onBid }) {
  return <li className={`edb-feed-row${open ? ' is-open' : ''}`} style={{ '--i': Math.min(i, 6) }} data-testid={`edb-feed-${i}`}>
    <span className="edb-row-top"><Zap size={13} aria-hidden="true" className="edb-zap" />
      <a href={r.url} target="_blank" rel="noopener noreferrer" className="edb-title" title={r.title}>{r.title}<ExternalLink size={10} aria-hidden="true" /></a>
      <span className="edb-facts"><em>{PLAT[r.src] || r.src}</em><em>{r.cat}</em><span>{r.pay}</span><span>{r.rivals} bids</span><span>{r.needs?.days || 1} d</span></span>
      <b className={`m-num edb-exp ${(r.expProfit || 0) > 0 ? 'is-up' : ''}`}>{usd(r.expProfit)}</b>
      <button type="button" className="m-btn edb-more" aria-expanded={open} onClick={() => onOpen(open ? '' : r.id)} data-tip="What it takes to win: minds, models, cost, time, competition" data-testid={`edb-more-${i}`}>What it takes<ChevronDown size={12} aria-hidden="true" /></button></span>
    {open ? <WinPanel r={r} onBid={onBid} busy={busy} /> : null}
  </li>;
}

function FindTab({ v, busy, call, onBid, openId, setOpenId }) {
  const b = v?.board || {}; const feed = b.feed || []; const skills = b.skills || {}; const all = Object.values(skills).reduce((a, n) => a + n, 0);
  const pick = skill => call({ op: 'earn_find', tools: { skill, fresh: false } });
  return <div className="edb-find">
    <div className="edb-bar"><span className="m-seg edb-skills" role="group" aria-label="Find work by skill">
      {[['', 'All', all], ...Object.keys(SKILL).map(k => [k, SKILL[k], skills[k] || 0])].map(([k, l, n]) =>
        <button key={k || 'all'} type="button" className={(b.skill || '') === k ? 'active' : ''} aria-pressed={(b.skill || '') === k} disabled={busy} onClick={() => pick(k)} data-tip={k ? `One tap: only ${l.toLowerCase()} jobs` : 'Every kind of faceless work'} data-testid={`edb-skill-${k || 'all'}`}>{l}<em className="m-num"> {n}</em></button>)}</span>
      <span className="edb-fresh" data-testid="edb-fresh">{ago(b.at)}</span>
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => call({ op: 'earn_find', tools: { skill: b.skill || '' } })} data-tip="Reads every kept platform's public feed now. No login" data-testid="edb-read">{busy ? 'Reading…' : 'Find me work'}</button></div>
    <section className="edb-feed m-card" data-testid="edb-feed"><header><b>AI CAN WIN</b><span>few bids · clear scope · fast first</span></header>
      {feed.length ? <ol>{feed.map((r, i) => <FeedRow key={r.id} r={r} i={i} open={openId === r.id} onOpen={setOpenId} busy={busy} onBid={onBid} />)}</ol>
        : <p className="edb-say">{b.at ? 'No open job right now has few bids and a clear scope. The full board is below.' : 'Tap Find me work: it reads Superteam Earn, Freelancer.com and Algora bounties (public feeds only).'}</p>}</section>
  </div>;
}

function PipeTab({ earns, onOpen }) {
  const live = earns.filter(f => STAGE[f.stage]);
  if (!live.length) return <p className="edb-say" data-testid="edb-pipe-empty">No bid is waiting. Find work, then Start this job: both minds draft the bid blind, and you approve it.</p>;
  return <ol className="edb-pipe" data-testid="edb-pipe">{live.map((f, i) => { const l = f.listing || {}; const b = f.bid || {};
    return <li key={f.id} style={{ '--i': Math.min(i, 8) }}><button type="button" className={`edb-pipe-row is-${f.stage}`} onClick={() => onOpen(f)} data-tip="Open the filing: both bids, the approve door, its record" data-testid={`edb-pipe-${f.id}`}>
      <em className="edb-stage">{STAGE[f.stage]}</em><b className="edb-title">PoEco #{f.n} · {l.title}</b>
      <span className="edb-facts"><span>{f.platform?.name}</span><span>bid {usd(b.price)} in {b.days || '—'} d</span>{b.realistic && !b.realistic.ok ? <i className="is-bad">not realistic</i> : null}{f.test || f.testRun ? <i>TEST</i> : null}</span>
      <span className="m-num edb-cost">{usd(f.cost)} minds</span><b className="m-num edb-exp is-up">{usd(l.expProfit)}</b></button></li>; })}</ol>;
}

function PaidTab({ earns, d, onOpen }) {
  const done = earns.filter(f => f.graded);
  return <div className="edb-paid" data-testid="edb-paid">
    <p className="edb-sum"><span><small>PAID</small><b className="m-num is-up">{usd(d.paidUsd)}</b></span><span><small>MINDS</small><b className="m-num">{usd(d.mindsUsd)}</b></span><span><small>NET</small><b className={`m-num ${(d.netUsd || 0) >= 0 ? 'is-up' : 'is-bad'}`}>{usd(d.netUsd)}</b></span><span className="edb-note">Platform fees stay on each receipt, never in the profit.</span></p>
    {done.length ? <ol className="edb-pipe">{done.map(f => <li key={f.id}><button type="button" className={`edb-pipe-row is-${f.graded.result}`} onClick={() => onOpen(f)} data-testid={`edb-paid-${f.id}`}>
      <em className="edb-stage">{f.graded.result.toUpperCase()}</em><b className="edb-title">PoEco #{f.n} · {f.listing?.title}</b><span className="edb-facts"><span>{f.graded.why}</span></span>
      <span className="m-num edb-cost">{usd(f.graded.cost)} minds</span><b className={`m-num edb-exp ${(f.graded.profit || 0) > 0 ? 'is-up' : ''}`}>{usd(f.graded.profit)}</b></button></li>)}</ol>
      : <p className="edb-say">Nothing graded yet. A job is graded when you mark it paid, lost or unpaid: what the platform paid you minus what the minds cost.</p>}
  </div>;
}

function CallsTab({ rows, onOpen }) {
  const calls = rows.filter(f => f.kind === 'market');
  return calls.length ? <ol className="edb-pipe" data-testid="edb-calls-list">{calls.map(f => <li key={f.id}><button type="button" className={`edb-pipe-row is-${f.graded || 'open'}`} onClick={() => onOpen(f)} data-testid={`edb-call-${f.id}`}>
    <em className="edb-stage">{f.graded ? f.graded.toUpperCase() : 'OPEN'}</em><b className="edb-title">PoEco #{f.n} · {f.q}</b><span className="edb-facts"><span>{f.rule}</span></span></button></li>)}</ol>
    : <p className="edb-say" data-testid="edb-calls-empty">No market call yet. File one from the right: it seals live pool numbers and reality grades it in 24 h.</p>;
}

export function EarnDash({ v, rows, busy, call, onBid, onOpen, board }) {
  const [tab, setTab] = useState(readTab); const [openId, setOpenId] = useState('');
  const go = k => { setTab(k); try { localStorage.setItem(TAB_KEY, k); } catch { /* private mode: the tab still changes */ } };
  const d = v?.dash || {}; const earns = v?.earns || [];
  const at = v?.board?.at;
  useEffect(() => { if (v && !busy && (!at || Date.now() - at * 1000 > STALE_MS)) call({ op: 'earn_find', tools: { skill: v?.board?.skill || '' } }); }, [!!v]);   // eslint-disable-line react-hooks/exhaustive-deps -- 🔥 a live feed: an old board is read again on open
  const counts = { find: d.found, pipe: (d.waiting || 0) + (d.sentOut || 0) + (d.inWork || 0), paid: (d.paidN || 0) + (d.lost || 0), calls: d.calls?.n };
  return <section ref={dashBox} className="edb" data-testid="edb">
    <Hero d={d} go={go} />
    <div className="m-seg edb-tabs" role="tablist" aria-label="PoEco desk">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => go(k)} data-testid={`edb-tab-${k}`}>{l}{counts[k] ? <em className="m-num"> {counts[k]}</em> : null}</button>)}</div>
    <div className="edb-body" role="tabpanel">
      {tab === 'find' ? <><FindTab v={v} busy={busy} call={call} onBid={onBid} openId={openId} setOpenId={setOpenId} />{board}</> : null}
      {tab === 'pipe' ? <PipeTab earns={earns} onOpen={onOpen} /> : null}
      {tab === 'paid' ? <PaidTab earns={earns} d={d} onOpen={onOpen} /> : null}
      {tab === 'calls' ? <CallsTab rows={rows} onOpen={onOpen} /> : null}
      {tab === 'books' ? <EcoLive /> : null}
    </div>
  </section>;
}

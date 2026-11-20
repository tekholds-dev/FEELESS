import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { boxRef } from '../../lib/boxRef';
import { fileOf, fmt } from './PocStudio';
import { DAYS } from './ClipFarm';
import { TestTag } from './TrueRecord';
import '../../styles/pocDash.css';

// 📣 THE PoC DESK DASHBOARD (Slice 24 · the desk bar, RULINGS 2026-11-20: "all this big ass shit, horrible styles and ui cmon, each proof type will
// have a user in it for hours"). The PoC folder opens on its content work, not a wall: what is trending now, what waits for his approve, what is
// posted with its reach and cost per 1,000 views, this week's plan, and every filing, one tap each. Every number is read from its PoC folders
// (reach from the 24 h / 7 d reads, cost = minds + maker) or from the live trend reader (`/api/cats/tools/content`); nothing is made up here.
const POLL_MS = 60000;
const TAB_KEY = 'feeless.pocDashTab';
const TABS = [['trend', 'Trending'], ['approve', 'To approve'], ['posts', 'Posts'], ['week', 'Week'], ['filed', 'All filed']];
const SWAP_SPOT = 'feeless.swapClip';   // the PoC studio's Swap panel reads it (MediaStudio.jsx SWAP_SPOT), same key as ProofTools
const box = boxRef([640, 900]);
const usd = v => (v == null ? '—' : v >= 1 ? `$${v.toFixed(2)}` : `$${v.toFixed(v < 0.01 ? 4 : 3)}`);
const clock = s => `${Math.floor((s || 0) / 60)}:${String(Math.floor((s || 0) % 60)).padStart(2, '0')}`;
const readTab = () => { try { return localStorage.getItem(TAB_KEY) || 'trend'; } catch { return 'trend'; } };
const costOf = f => Number(f?.cost || 0) + Number(f?.studio?.maker?.usd || 0);

/** Pure: every number on the dashboard, from its PoC folders. `today` = 0 (Mon) … 6 (Sun). */
export function pocNumbers(pocs, today = (new Date().getDay() + 6) % 7) {
  const rows = (pocs || []).filter(Boolean);
  const posted = rows.filter(f => f.posted).sort((a, b) => (b.posted.at || 0) - (a.posted.at || 0));
  const views = posted.reduce((a, f) => a + (Number(f.reach?.last?.views) || 0), 0);
  const spent = posted.reduce((a, f) => a + costOf(f), 0);
  const goal = posted.reduce((a, f) => a + (f.studio?.goal?.type === 'reach' ? Number(f.studio.goal.target) || 0 : 0), 0);
  const waiting = rows.filter(f => f.studio && !f.posted).sort((a, b) => (b.at || 0) - (a.at || 0) || (a.studio.clip?.rank || 0) - (b.studio.clip?.rank || 0));
  const week = DAYS.map((d, i) => ({ day: d, today: i === today, rows: waiting.concat(posted).filter(f => f.studio?.slot === d) }));
  return { posted, views, spent, goal, cpm: views ? spent / views * 1000 : null, waiting, week, planned: week.filter(w => w.rows.length).length,
    unplanned: waiting.filter(f => !f.studio.slot).length, all: rows.slice().sort((a, b) => (b.n || 0) - (a.n || 0)), total: rows.reduce((a, f) => a + costOf(f), 0) };
}

function Meter({ v, tone = '' }) { return <span className={`pcd-meter ${tone}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></span>; }

function Hero({ n, onTab }) {
  return <div className="pcd-hero" data-testid="pcd-hero">
    <div className="pcd-kpi is-reach" style={{ '--i': 0 }} data-tip="Views on its posted PoCs, from the last 24 h / 7 d read of each platform">
      <small>REACH</small><b className="m-num" data-testid="pcd-views">{fmt(n.views)}</b><Meter v={n.goal ? n.views / n.goal : 0} /><em>{n.posted.length ? `${n.posted.length} posted · goal ${fmt(n.goal)}` : 'nothing posted yet'}</em></div>
    <div className="pcd-kpi" style={{ '--i': 1 }} data-tip="Minds + maker cost of its posted PoCs, per 1,000 views. Fees never count">
      <small>PER 1K VIEWS</small><b className="m-num" data-testid="pcd-cpm">{n.cpm == null ? '—' : usd(n.cpm)}</b><em>{usd(n.total)} spent on {n.all.length}</em></div>
    <button type="button" className="pcd-kpi is-go" style={{ '--i': 2 }} onClick={() => onTab('approve')} data-tip="Made and waiting: nothing posts until you approve it in its studio" data-testid="pcd-kpi-approve">
      <small>TO APPROVE</small><b className="m-num" data-testid="pcd-waiting">{n.waiting.length}</b><em>{n.waiting.length ? 'tap to see them' : 'nothing waiting'}</em></button>
    <button type="button" className="pcd-kpi is-go" style={{ '--i': 3 }} onClick={() => onTab('week')} data-tip="Days of this week with a clip planned (the day buttons on the Clip board)" data-testid="pcd-kpi-week">
      <small>THIS WEEK</small><b className="m-num">{n.planned}<small>/7</small></b>
      <span className="pcd-dots" aria-hidden="true">{n.week.map(w => <i key={w.day} className={`${w.rows.length ? 'is-on' : ''}${w.today ? ' is-today' : ''}`} />)}</span><em>{n.unplanned ? `${n.unplanned} without a day` : 'every clip has a day'}</em></button>
  </div>;
}

function Trending({ d, err, onCommand }) {
  const [sent, setSent] = useState('');
  if (!d) return <p className="pcd-none">{err ? 'The trend reader could not be read. It tries again in a minute.' : 'Reading what is moving now…'}</p>;
  const clips = (d.clips || []).slice(0, 8); const hot = c => (c.views != null ? c.views : c.likes || 0); const max = Math.max(1, ...clips.map(hot));
  const topics = Object.entries(d.trends || {}).flatMap(([k, v]) => (v || []).slice(0, 3).map(t => [k, t])).slice(0, 10);
  return <><p className="pcd-src">{(d.sources || []).map(s => <span key={s.name} className={s.on ? 'is-on' : ''} data-tip={`${s.use}. ${s.on ? 'Read just now' : 'Not read'}`}><i aria-hidden="true" />{s.name}</span>)}</p>
    {clips.length ? <ol className="pcd-rows" data-testid="pcd-trend">{clips.map((c, i) => <li key={c.url} className="pcd-row" style={{ '--i': i }}>
      <a className="pcd-thumb" href={c.url} target="_blank" rel="noopener noreferrer" aria-label={`Open the clip by ${c.by}`} data-tip="Open the post where it lives">{c.thumb ? <img src={c.thumb} alt="" loading="lazy" /> : <span aria-hidden="true">▶</span>}</a>
      <span className="pcd-t"><b>{c.text || 'No words, just the clip.'}</b><small>{c.src === 'youtube' ? `${c.by} · YouTube` : `@${c.by}`}</small></span>
      <span className="pcd-n"><b className="m-num">{c.views != null ? `▶ ${fmt(c.views)}` : `♥ ${fmt(c.likes)}`}</b><Meter v={hot(c) / max} /></span>
      <span className="pcd-act">{c.src !== 'youtube' && /^https:\/\/bsky\.app\/profile\/[^/]+\/post\//.test(String(c.url || '')) ? <button type="button" className={`m-btn${sent === c.url ? ' is-on' : ''}`} onClick={() => { try { localStorage.setItem(SWAP_SPOT, JSON.stringify({ url: c.url, title: `@${String(c.by || '').split('.')[0]}: ${String(c.text || '').slice(0, 50)}` })); } catch { /* private window */ } setSent(c.url); }}
        data-tip="Your PoC folder's studio gets this clip: open it, tick the rights box, Add it, then Swap. Only clips you have the rights to" data-testid={`pcd-swap-${i}`}>{sent === c.url ? '✓ In studio' : 'Swap in'}</button> : null}
        {onCommand ? <button type="button" className="m-btn" onClick={() => onCommand(`file a poc on the angle behind this trending clip: "${String(c.text || '').slice(0, 80)}"`)} data-tip="Puts the filing in the chat box. You press send" data-testid={`pcd-angle-${i}`}>Write the angle</button> : null}</span>
    </li>)}</ol> : <p className="pcd-none">No trending clips right now. It tries again in a minute.</p>}
    {topics.length ? <div className="pcd-topics" data-testid="pcd-topics">{topics.map(([k, t]) => <button key={k + t} type="button" className="m-chip" onClick={() => onCommand?.(`file a poc about ${t}`)} data-tip={`${k} · puts the filing in the chat box. You press send`}>{String(t).length > 44 ? `${String(t).slice(0, 44)}…` : t}</button>)}</div> : null}</>;
}

function Approve({ rows, onOpen }) {
  if (!rows.length) return <p className="pcd-none">Nothing waits for your approve. Clip a video in a PoC folder's Clips tab, or file a PoC: what it makes lands here.</p>;
  return <ol className="pcd-rows" data-testid="pcd-approve">{rows.map((f, i) => { const s = f.studio; const cov = fileOf(s.files, 'image', 'story') || fileOf(s.files, 'image', 'feed'); const made = (s.files || []).filter(x => x.url && !x.error).length;
    return <li key={f.id} className="pcd-row" style={{ '--i': Math.min(i, 12) }}><button type="button" className="pcd-open" onClick={() => onOpen(f)} data-tip="Open its studio: the goal, the platforms and Approve and post" data-testid={`pcd-approve-${f.id}`}>
      <span className="pcd-thumb is-tall">{cov ? <img src={apiUrl(cov.url)} alt="" loading="lazy" /> : <span aria-hidden="true">✂</span>}</span>
      <span className="pcd-t"><b>{s.hook || f.topic}</b><small>PoC #{f.n} · {s.clip ? `${clock(s.clip.s)}–${clock(s.clip.e)} of ${s.clip.from}` : s.trend?.text || 'its trend'}{s.slot ? ` · ${s.slot}` : ''}</small></span>
      <span className="pcd-n"><b className="m-num">{made}/{s.clip ? 9 : 12}</b><small>files</small></span>
      <span className="pcd-n"><b className="m-num">{fmt(Number(s.goal?.target) || 0)}</b><small>{s.goal?.type === 'reach' || !s.goal?.type ? 'views goal' : `${s.goal.type} goal`}</small></span>
      <span className="pcd-n"><b className="m-num">{usd(costOf(f))}</b><small>cost</small></span><TestTag f={f} /></button></li>; })}</ol>;
}

const VERDICT = { hit: 'is-up', 'on pace': 'is-up', missed: 'is-dn', behind: 'is-dn' };
function Posts({ rows, onOpen }) {
  if (!rows.length) return <p className="pcd-none">Nothing posted yet. Approve one in To approve: its views are read back at 24 h and 7 d and graded against its goal, with the cost per 1,000 views.</p>;
  return <ol className="pcd-rows" data-testid="pcd-posts">{rows.map((f, i) => { const last = f.reach?.last; const g = f.grade || last?.grade || {}; const goal = Number(f.studio?.goal?.target) || 0;
    return <li key={f.id} className="pcd-row" style={{ '--i': Math.min(i, 12) }}><button type="button" className="pcd-open" onClick={() => onOpen(f)} data-tip={g.why || 'Open its studio and reach'} data-testid={`pcd-post-${f.id}`}>
      <span className="pcd-t"><b>{f.studio?.hook || f.topic}</b><small>PoC #{f.n} · {Object.keys(f.posted.platforms || {}).join(', ') || 'posted'} · {last?.label || 'first read at 24 h'}</small></span>
      <span className="pcd-n is-wide"><b className="m-num">{fmt(last?.views)}<small> / {fmt(goal)}</small></b><Meter v={goal ? (last?.views || 0) / goal : 0} tone={VERDICT[g.verdict] || ''} /></span>
      <span className="pcd-n"><b className="m-num">{g.cpm == null ? '—' : usd(g.cpm)}</b><small>per 1K</small></span>
      <span className={`pcd-v ${VERDICT[g.verdict] || ''}`}>{g.verdict || 'waiting'}</span></button></li>; })}</ol>;
}

function Week({ n, onOpen }) {
  return <><ol className="pcd-week" data-testid="pcd-week">{n.week.map((w, i) => <li key={w.day} className={w.today ? 'is-today' : ''} style={{ '--i': i }}>
    <small>{w.day}{w.today ? ' · today' : ''}</small>{w.rows.length ? w.rows.map(f => <button key={f.id} type="button" className={`pcd-chip${f.posted ? ' is-posted' : ''}`} onClick={() => onOpen(f)} data-tip={`PoC #${f.n}${f.posted ? ' · posted' : ' · waiting for your approve'}`}>{f.studio?.hook || f.topic}</button>) : <em>—</em>}</li>)}</ol>
    {n.unplanned ? <p className="pcd-none">{n.unplanned} made clip{n.unplanned === 1 ? '' : 's'} without a day: pick one on the Clip board (a PoC folder › Clips).</p> : null}</>;
}

function Filed({ rows, onOpen }) {
  if (!rows.length) return <p className="pcd-none">No PoC filed yet. Name one above, or pick a starter in Features.</p>;
  return <ol className="pcd-rows is-dense" data-testid="pcd-filed">{rows.map((f, i) => <li key={f.id} className="pcd-row" style={{ '--i': Math.min(i, 12) }}><button type="button" className="pcd-open" onClick={() => onOpen(f)} data-testid={`pdk-open-${f.id}`}>
    <em className="m-num pcd-num">#{f.n}</em><span className="pcd-t"><b>{f.studio?.hook || f.topic || f.name}</b><small>{f.posted ? 'Posted' : f.graded === 'right' ? 'It worked' : f.graded === 'wrong' ? 'It did not' : f.studio ? 'Made · waiting for your approve' : 'Waiting for your mark'}</small></span>
    <span className="pcd-n"><b className="m-num">{usd(costOf(f))}</b></span><TestTag f={f} /></button></li>)}</ol>;
}

export function PocDash({ pocs, onOpen, onCommand }) {
  const [tab, setTab] = useState(readTab); const [d, setD] = useState(null); const [err, setErr] = useState(false);
  useEffect(() => { let on = true; let first = true; const go = () => { if (document.hidden && !first) return; first = false;
    fetch(apiUrl('/api/cats/tools/content')).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { if (on) { setD(j); setErr(false); } }).catch(() => on && setErr(true)); };
  go(); const t = setInterval(go, POLL_MS); return () => { on = false; clearInterval(t); }; }, []);
  const n = useMemo(() => pocNumbers(pocs), [pocs]);
  const go = k => { setTab(k); try { localStorage.setItem(TAB_KEY, k); } catch { /* private window */ } };
  const counts = { trend: (d?.clips || []).length, approve: n.waiting.length, posts: n.posted.length, week: n.planned, filed: n.all.length };
  return <section className="pcd" data-testid="pcd">
    <Hero n={n} onTab={go} />
    <div className="m-seg pcd-tabs" role="tablist" aria-label="PoC dashboard">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => go(k)} data-testid={`pcd-tab-${k}`}>
      {k === 'trend' ? <i className="pcd-onair" aria-hidden="true" /> : null}{l}{counts[k] ? <em className="m-num"> {counts[k]}</em> : null}</button>)}</div>
    <div key={tab} className="pcd-pane" role="tabpanel">
      {tab === 'trend' ? <Trending d={d} err={err} onCommand={onCommand} /> : tab === 'approve' ? <Approve rows={n.waiting} onOpen={onOpen} /> : tab === 'posts' ? <Posts rows={n.posted} onOpen={onOpen} />
        : tab === 'week' ? <Week n={n} onOpen={onOpen} /> : <Filed rows={n.all} onOpen={onOpen} />}
    </div>
  </section>;
}

/** The PoC home: the dashboard with its live tools beside it (side column on a wide window, under it on a narrow one). */
export function PocHome({ pocs, onOpen, onCommand, side }) {
  return <div ref={box} className="pcd-wrap" data-testid="pcd-wrap"><PocDash pocs={pocs} onOpen={onOpen} onCommand={onCommand} /><aside className="pcd-side" aria-label="Live tools">{side}</aside></div>;
}

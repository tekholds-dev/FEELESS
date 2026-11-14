import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import '../../styles/weekBoard.css';

// 🗓 POC-PLAY items 4 + 5 (owner 2026-11-13): a week of posts ON A BOARD (Mon–Sun × platform). Its minds write three different weeks
// (launch / steady drip / hype into event); each one is filed as its own PoC proof and graded like any other. Drag a post to another day or
// platform, edit its words or time, Save keeps your version (the minds' original stays on the proof). Nothing is posted from here.
export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export const PLATFORMS = ['x', 'instagram', 'tiktok', 'youtube', 'linkedin', 'threads'];
const PLAT = { x: 'X', instagram: 'Instagram', tiktok: 'TikTok', youtube: 'YouTube', linkedin: 'LinkedIn', threads: 'Threads' };
const STYLE = { launch: 'Launch week', drip: 'Steady drip', hype: 'Hype into event' };

/** Pure: move post #i to a day + platform; it lands last that day by time order. */
export function movePost(posts, i, day, platform) {
  return posts.map((p, k) => (k === i ? { ...p, day, platform } : p)).sort((a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || a.time.localeCompare(b.time));
}

export default function WeekBoard({ cat, work, wsId, pocs, media, onPocs }) {
  const weeks = useMemo(() => (pocs || []).filter(f => f.week), [pocs]);
  const [pick, setPick] = useState(null); const f = weeks.find(w => w.id === pick) || weeks[0];
  const [posts, setPosts] = useState(f?.week.posts || []); const [edit, setEdit] = useState(null); const [drag, setDrag] = useState(null);
  const [topic, setTopic] = useState(''); const [msg, setMsg] = useState(''); const [busy, setBusy] = useState('');
  useEffect(() => { setPosts(f?.week.posts || []); setEdit(null); }, [f?.id, f?.week]);
  const dirty = !!f && JSON.stringify(posts) !== JSON.stringify(f.week.posts);
  const rows = PLATFORMS.filter(p => posts.some(x => x.platform === p) || (drag != null));
  const pic = id => (media || []).find(m => m.id === id);
  const make = async () => { setMsg(''); setBusy('make'); try { await work(cat.id, { op: 'week_plans', job: wsId, text: topic }); setMsg('Its minds are writing three different weeks. Each one files here as a PoC in a minute or two.'); setTopic(''); } catch (e) { setMsg(e.message); } setBusy(''); };
  const save = async () => { setMsg(''); setBusy('save'); try { const j = await work(cat.id, { op: 'week_save', job: f.id, cap: { idea: f.week.idea, posts } }); onPocs?.(j.pocFolders); setMsg('Saved. The minds’ original week stays on the proof.'); } catch (e) { setMsg(e.message); } setBusy(''); };
  const set = (i, patch) => setPosts(ps => ps.map((p, k) => (k === i ? { ...p, ...patch } : p)));
  return <div className="wkb" data-testid="week-board">
    <form className="wkb-make" onSubmit={e => { e.preventDefault(); make(); }}>
      <input className="m-input" value={topic} onChange={e => setTopic(e.target.value)} placeholder="What the week is about (optional)" aria-label="Week topic" data-testid="week-topic" />
      <button type="submit" className="m-btn m-go" disabled={!!busy} data-tip="Its minds each write a whole week in a different style; each files as a PoC" data-testid="week-make">{busy === 'make' ? 'Asking…' : 'Make 3 week plans'}</button>
    </form>
    {msg ? <small className="wkb-msg" role="status">{msg}</small> : null}
    {!weeks.length ? <p className="wkb-none" data-testid="week-none">No week plan yet. Its minds write three (launch, steady drip, hype into event) and each one is filed as a proof you can mark.</p> : <>
      <div className="m-seg wkb-tabs" role="tablist" aria-label="Week plans">{weeks.map(w => <button key={w.id} type="button" role="tab" aria-selected={w.id === f.id} className={w.id === f.id ? 'active' : ''} onClick={() => setPick(w.id)} data-testid={`week-tab-${w.id}`}>{STYLE[w.week.style] || 'Week'} <small className="m-num">#{w.n}</small></button>)}</div>
      <p className="wkb-idea"><span className="m-label">THE WEEK</span> {f.week.idea || '—'} <small className="m-num">{posts.length} posts{f.week.edited ? ' · your edit' : ''}{f.graded ? ` · marked ${f.graded}` : ''}</small></p>
      <div className="wkb-grid" role="grid" aria-label="Posting week" style={{ '--rows': rows.length || 1 }}>
        <span className="wkb-corner" />{DAYS.map(d => <b key={d} className="wkb-day" role="columnheader">{d}</b>)}
        {(rows.length ? rows : ['x']).map(pl => <React.Fragment key={pl}>
          <b className="wkb-plat" role="rowheader">{PLAT[pl]}</b>
          {DAYS.map(d => <div key={d} role="gridcell" className={`wkb-cell${drag != null ? ' is-drop' : ''}`} data-testid={`week-cell-${pl}-${d}`} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (drag != null) setPosts(ps => movePost(ps, drag, d, pl)); setDrag(null); }}>
            {posts.map((p, i) => (p.platform === pl && p.day === d ? <article key={`${i}-${p.caption.slice(0, 8)}`} className={`wkb-post${edit === i ? ' is-edit' : ''}`} draggable onDragStart={() => setDrag(i)} onDragEnd={() => setDrag(null)} onClick={() => setEdit(i)} data-testid={`week-post-${i}`}>
              <small className="m-num">{p.time}</small>
              {p.media && pic(p.media) ? (pic(p.media).kind === 'video' ? <video src={apiUrl(pic(p.media).url)} muted /> : <img src={apiUrl(pic(p.media).url)} alt="" />) : null}
              {edit === i ? <><textarea className="m-input" value={p.caption} maxLength={280} onChange={e => set(i, { caption: e.target.value })} aria-label="Caption" data-testid="week-caption" />
                <input className="m-input" type="time" value={p.time} onChange={e => set(i, { time: e.target.value })} aria-label="Time" />
                <button type="button" className="m-btn danger" onClick={e => { e.stopPropagation(); setPosts(ps => ps.filter((_x, k) => k !== i)); setEdit(null); }}>Remove</button></>
                : <p>{p.caption}</p>}
            </article> : null))}
          </div>)}
        </React.Fragment>)}
      </div>
      <div className="wkb-foot"><button type="button" className="m-btn m-go" disabled={!dirty || !!busy} onClick={save} data-testid="week-save">{busy === 'save' ? 'Saving…' : 'Save my week'}</button>
        <button type="button" className="m-btn" disabled={!dirty} onClick={() => setPosts(f.week.posts)}>Undo changes</button>
        <small>Drag a post to another day or platform. Click it to edit. Nothing is posted from here.</small></div>
    </>}
  </div>;
}

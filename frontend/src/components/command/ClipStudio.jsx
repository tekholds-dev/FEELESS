import React, { useEffect, useMemo, useRef, useState } from 'react';
import { DndContext, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from '@dnd-kit/core';
import { AnimatePresence, motion } from 'motion/react';
import { Brain, CalendarDays, Check, Grid3x3, LayoutTemplate, Loader2, MessageSquare, Pencil, Play, RotateCcw, Send, Sparkles, Undo2, Wand2, X } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { boxRef } from '../../lib/boxRef';
import { DAYS, PLATS, RATIO, bySource, clipStatus, describe, filterClips, fullLook, moveSlot, sig, twinOf } from '../../lib/clipLook';
import ClipEdit from './ClipEdit';
import ClipTemplates from './ClipTemplates';
import '../../styles/clipStudio.css';

// 🎨🗓 Slice 29 (owner 2026-11-20: "clip farming should show file folder with some cool smart way to show a grid and easy way for user to plan a
// week or have agent plan and user able to chat in file of the plan etc, able to edit captions and different transition and effects user or ai can
// use"). Three views on one agent's clips: the GRID (every clip as a playable tile, by source, hover-play, score, hook, status, quick filters), the
// WEEK (drag clips onto Mon–Sun with a time and platforms, or "Agent plans it": a why on every slot; a chat inside the plan changes the plan AND
// the clips; every version undoable) and EDIT (captions, transition, effects with a live preview; ffmpeg renders it, $0, no two clips alike).
// Nothing here posts: a clip goes out only from its studio's Approve and post (Slice 5).
const box = boxRef([640, 980, 1240]);
const VIEW_KEY = 'feeless.clipStudioView';
const STATUS = [['all', 'All'], ['approve', 'To approve'], ['planned', 'Planned'], ['posted', 'Posted']];
const STATUS_WORD = { approve: 'to approve', planned: 'planned', posted: 'posted' };
const fileOf = (f, piece, fmt) => (f?.studio?.files || []).find(x => x.piece === piece && x.format === fmt && x.url && !x.error);
const clock = s => `${Math.floor((s || 0) / 60)}:${String(Math.floor((s || 0) % 60)).padStart(2, '0')}`;
const ago = at => { const m = Math.max(0, Math.round((Date.now() / 1000 - (at || 0)) / 60)); return m < 1 ? 'now' : m < 60 ? `${m} m` : m < 1440 ? `${Math.round(m / 60)} h` : `${Math.round(m / 1440)} d`; };
const readView = () => { try { return localStorage.getItem(VIEW_KEY) || 'grid'; } catch { return 'grid'; } };

/** The score ring: the clip's one hero number (both minds' score out of 10). */
function Score({ v }) {
  const n = Number(v) || 0;
  return <span className={`cst-score${n >= 8 ? ' is-hot' : ''}`} data-tip="Both minds' score for the moment, out of 10" style={{ '--p': Math.min(1, n / 10) }}><b className="m-num">{v ?? '—'}</b></span>;
}

function Tile({ f, fmt, i, rendering, onEdit, onOpen, onSlot, links, busy: slotBusy }) {
  const v = useRef(null); const s = f.studio; const vid = fileOf(f, 'video', fmt); const cov = fileOf(f, 'image', fmt); const st = clipStatus(f);
  const busy = rendering || s.render?.state === 'running';
  const play = () => { const el = v.current; if (el && vid) { el.muted = true; el.play().catch(() => {}); } };
  const stop = () => { const el = v.current; if (el) { el.pause(); el.currentTime = 0; } };
  return <motion.article layout className={`cst-tile is-${fmt}`} style={{ '--i': Math.min(i, 12) }} data-testid={`cst-tile-${f.id}`}
    onMouseEnter={play} onMouseLeave={stop} onFocus={play} onBlur={stop} tabIndex={-1}>
    <div className="cst-media" style={{ aspectRatio: RATIO[fmt] }}>
      {vid ? <video ref={v} src={apiUrl(vid.url)} poster={cov ? apiUrl(cov.url) : undefined} muted loop playsInline preload="none" data-testid={`cst-vid-${f.id}`} /> : cov ? <img src={apiUrl(cov.url)} alt="" loading="lazy" /> : <span className="cst-nofile">not made</span>}
      <Score v={s.clip.both} />
      <span className={`cst-st is-${st}`}>{STATUS_WORD[st]}{st === 'planned' ? ` · ${s.slot}${s.slotTime ? ` ${s.slotTime}` : ''}` : ''}</span>
      {busy ? <span className="cst-busy"><Loader2 size={12} className="cst-spin" /> rendering</span> : s.render?.state === 'failed' ? <span className="cst-busy is-bad" data-tip={s.render.err}>render failed</span> : null}
      <span className="cst-play" aria-hidden="true"><Play size={14} /></span>
    </div>
    <div className="cst-tile-b">
      <b title={s.hook}>{s.hook}</b>
      <small className="m-num">#{f.n} · {Math.round(s.clip.dur || 0)} s · {clock(s.clip.s)} in{f.testRun || f.test ? ' · TEST' : ''}</small>
      {s.tpl ? <small className={`cst-tplchip is-${s.tpl.by}`} data-testid={`cst-tplchip-${f.id}`}><LayoutTemplate size={11} aria-hidden="true" /><b>{s.tpl.name}{s.tpl.edited ? ' · edited' : ''}</b>
        <span>{s.tpl.by === 'minds' ? 'minds' : s.tpl.by === 'code' ? 'by mood' : s.tpl.by === 'owner' ? 'yours' : s.tpl.by}: {s.tpl.why}</span></small> : null}
      <small className="cst-look" data-tip="Its look: font · caption style · transition · effects">{describe(s.look)}</small>
    </div>
    <div className="cst-tile-act">
      <button type="button" className="m-btn" onClick={() => onEdit(f.id)} disabled={!!f.posted} data-tip={f.posted ? 'Posted: its look is locked' : 'Captions, transition, effects'} data-testid={`cst-edit-${f.id}`}><Pencil size={12} /> Edit</button>
      <button type="button" className="m-btn" onClick={() => onOpen?.(f)} data-tip="Its studio: the goal, the platforms and Approve and post" data-testid={`cst-open-${f.id}`}>{f.posted ? 'Reach' : 'Approve…'}</button>
      {onSlot ? <select className="m-input cst-daypick" value={s.slot || ''} disabled={slotBusy || !!f.posted} onChange={e => onSlot(f.id, e.target.value)} aria-label="Day to post" data-tip="Its day in the week plan" data-testid={`cfm-day-${f.id}`}>
        <option value="">No day</option>{DAYS.map(d => <option key={d} value={d}>{d}</option>)}</select> : null}
    </div>
    {links ? <div className="cst-links">{links(f)}</div> : null}
  </motion.article>;
}

function Grid({ clips, rendering, onEdit, onOpen, onSlot, links, busy }) {
  const [status, setStatus] = useState('all'); const [run, setRun] = useState('all'); const [min, setMin] = useState(0); const [fmt, setFmt] = useState('story'); const [sort, setSort] = useState('score');
  const runs = useMemo(() => bySource(clips), [clips]);
  const rows = useMemo(() => filterClips(clips, { status, run, min, sort }), [clips, status, run, min, sort]);
  const groups = bySource(rows); const count = k => (k === 'all' ? clips.length : clips.filter(f => clipStatus(f) === k).length);
  return <div className="cst-grid-wrap" data-testid="cst-grid">
    <div className="cst-bar">
      <div className="m-seg" role="group" aria-label="Status">{STATUS.map(([k, l]) => <button key={k} type="button" aria-pressed={status === k} className={status === k ? 'active' : ''} onClick={() => setStatus(k)} data-testid={`cst-f-${k}`}>{l}<em className="m-num">{count(k)}</em></button>)}</div>
      <div className="m-seg" role="group" aria-label="Score">{[[0, 'Any'], [6, '6+'], [8, '8+']].map(([k, l]) => <button key={k} type="button" aria-pressed={min === k} className={min === k ? 'active' : ''} onClick={() => setMin(k)} data-tip="Both minds' score">{l}</button>)}</div>
      <div className="m-seg" role="group" aria-label="Format">{[['story', '9:16'], ['feed', '1:1'], ['wide', '16:9']].map(([k, l]) => <button key={k} type="button" aria-pressed={fmt === k} className={fmt === k ? 'active' : ''} onClick={() => setFmt(k)} data-testid={`cst-fmt-${k}`}>{l}</button>)}</div>
      {runs.length > 1 ? <select className="m-input cst-sel" value={run} onChange={e => setRun(e.target.value)} aria-label="Source"><option value="all">Every upload</option>{runs.map(r => <option key={r.run} value={r.run}>{r.from}</option>)}</select> : null}
      <button type="button" className="m-btn cst-sort" onClick={() => setSort(s => (s === 'score' ? 'new' : 'score'))} data-tip="Sort by score or newest">{sort === 'score' ? 'Best first' : 'Newest first'}</button>
    </div>
    {!rows.length ? <p className="cst-none">{clips.length ? 'No clip matches these filters.' : 'Drop a video above: its clips land here as tiles.'}</p> : groups.map(g => <section key={g.run} className="cst-src" aria-label={`From ${g.from}`}>
      <header><span className="m-label">FROM</span><b>{g.from}</b><small className="m-num">{g.rows.length} clip{g.rows.length === 1 ? '' : 's'} · {ago(g.at)} ago</small></header>
      <motion.div layout className={`cst-tiles is-${fmt}`}>{g.rows.map((f, i) => <Tile key={f.id} f={f} fmt={fmt} i={i} rendering={rendering.includes(f.id)} onEdit={onEdit} onOpen={onOpen} onSlot={onSlot} links={links} busy={busy} />)}</motion.div>
    </section>)}
  </div>;
}

// ── the week ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
function Drag({ id, children, className, disabled }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id, disabled });
  return <div ref={setNodeRef} className={`${className}${isDragging ? ' is-drag' : ''}`} style={transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined} {...listeners} {...attributes} data-testid={`cst-drag-${id}`}>{children}</div>;
}
function Drop({ id, children, className, label }) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return <div ref={setNodeRef} className={`${className}${isOver ? ' is-over' : ''}`} aria-label={label} data-testid={`cst-drop-${id}`}>{children}</div>;
}
function Mini({ f }) {
  const cov = fileOf(f, 'image', 'story'); const s = f.studio;
  return <><span className="cst-mini-im">{cov ? <img src={apiUrl(cov.url)} alt="" draggable={false} /> : null}</span><span className="cst-mini-t"><b>{s.hook}</b><small className="m-num">#{f.n} · {s.clip.both ?? '—'}/10 · {Math.round(s.clip.dur || 0)} s</small></span></>;
}

function Slot({ s, f, onSet, onOff, locked }) {
  return <div className={`cst-slot${locked ? ' is-locked' : ''}`}>
    <Drag id={s.job} className="cst-slot-h" disabled={locked}><Mini f={f} /></Drag>
    <div className="cst-slot-row">
      <input className="m-input" type="time" value={s.time} disabled={locked} onChange={e => onSet({ time: e.target.value })} aria-label="Time" data-testid={`cst-time-${s.job}`} />
      {locked ? null : <button type="button" className="cst-x" onClick={onOff} aria-label="Take it off the week" data-tip="Take it off the week"><X size={12} /></button>}
    </div>
    <div className="cst-plats" role="group" aria-label="Platforms">{PLATS.map(([k, l]) => { const on = (s.plats || []).includes(k); return <button key={k} type="button" disabled={locked} aria-pressed={on} className={on ? 'is-on' : ''}
      onClick={() => onSet({ plats: on ? (s.plats || []).filter(x => x !== k) : [...(s.plats || []), k] })} data-testid={`cst-plat-${s.job}-${k}`}>{l}</button>; })}</div>
    {s.why ? <small className="cst-why">{s.why}</small> : null}
  </div>;
}

function Chat({ plan, busy, onSend, onUndo }) {
  const [t, setT] = useState(''); const end = useRef(null); const msgs = plan?.chat || []; const vs = plan?.versions || [];
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'nearest' }); }, [msgs.length, busy]);
  const prev = v => { const k = vs.findIndex(x => x.v === v); return k > 0 ? vs[k - 1].v : null; };
  const ideas = ['Move the best one to Friday', 'Make Tuesday funnier', 'Calmer captions on the slow one', 'Spread them over the weekend'];
  return <aside className="cst-chat" aria-label="Chat in the plan" data-testid="cst-chat">
    <header><MessageSquare size={13} /><b>Plan chat</b><small>the minds change the plan and the clips</small></header>
    <ol className="cst-msgs">{!msgs.length ? <li className="cst-msg is-hint">Ask in plain words. Every change is a new version you can undo.</li> : null}
      {msgs.map((m, i) => <motion.li key={`${m.at}-${i}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className={`cst-msg is-${m.by === 'mind' ? 'mind' : 'me'}`}>
        <small>{m.by === 'mind' ? (m.mind || 'mind') : m.by === 'TEST' ? 'TEST' : 'you'} · {ago(m.at)}</small><p>{m.text}</p>
        {m.v ? <span className="cst-msg-v"><em className="m-num">plan v{m.v}{m.looks?.length ? ` · ${m.looks.length} look${m.looks.length === 1 ? '' : 's'} changed` : ''}{m.cost ? ` · $${m.cost.toFixed(4)}` : ''}</em>
          {prev(m.v) ? <button type="button" className="m-btn" disabled={busy} onClick={() => onUndo(prev(m.v))} data-tip={`Back to plan v${prev(m.v)}: its days and each clip's look`} data-testid={`cst-chat-undo-${m.v}`}><Undo2 size={11} /> Undo</button> : null}</span> : null}
      </motion.li>)}
      {busy === 'chat' ? <li className="cst-msg is-mind is-wait"><Loader2 size={12} className="cst-spin" /> thinking…</li> : null}<li ref={end} aria-hidden="true" /></ol>
    <div className="cst-ideas">{ideas.map(x => <button key={x} type="button" className="m-chip" onClick={() => setT(x)}>{x}</button>)}</div>
    <form className="cst-say" onSubmit={e => { e.preventDefault(); if (t.trim() && !busy) { onSend(t.trim()); setT(''); } }}>
      <input className="m-input" value={t} onChange={e => setT(e.target.value)} placeholder="Move the best one to Friday, make Tuesday funnier…" aria-label="Ask the plan" data-testid="cst-chat-in" />
      <button type="submit" className="m-btn m-go" disabled={!t.trim() || !!busy} aria-label="Send" data-testid="cst-chat-send"><Send size={13} /></button>
    </form>
  </aside>;
}

function Week({ clips, plan, busy, onSave, onAgent, onChat, onUndo }) {
  const cur = (plan?.versions || []).slice(-1)[0]; const base = useMemo(() => cur?.slots || [], [cur]);
  const [draft, setDraft] = useState(base); const [showV, setShowV] = useState(false);
  useEffect(() => { setDraft(base); }, [base]);
  const dirty = JSON.stringify(draft) !== JSON.stringify(base);
  const byId = Object.fromEntries(clips.map(f => [f.id, f]));
  const tray = clips.filter(f => !draft.some(s => s.job === f.id) && !f.posted);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }), useSensor(KeyboardSensor));
  const today = (new Date().getDay() + 6) % 7;
  const onEnd = ({ active, over }) => { if (!over) return; const day = over.id === 'tray' ? '' : over.id; if (byId[active.id]?.posted) return; setDraft(d => moveSlot(d, String(active.id), day)); };
  const set = (job, patch) => setDraft(d => d.map(s => (s.job === job ? { ...s, ...patch } : s)));
  return <div className="cst-week" data-testid="cst-week">
    <div className="cst-bar">
      <button type="button" className="m-btn m-go" disabled={!!busy || !clips.length} onClick={onAgent} data-tip="The minds fill the week from the clip scores and what is trending, with a why on every slot" data-testid="cst-agent"><Brain size={13} /> {busy === 'agent' ? 'Planning…' : 'Agent plans it'}</button>
      <button type="button" className="m-btn" disabled={!dirty || !!busy} onClick={() => onSave(draft)} data-testid="cst-save"><Check size={13} /> {busy === 'save' ? 'Saving…' : 'Save week'}</button>
      <button type="button" className="m-btn" disabled={!dirty} onClick={() => setDraft(base)}><RotateCcw size={12} /> Discard</button>
      <button type="button" className={`m-btn${showV ? ' is-on' : ''}`} onClick={() => setShowV(x => !x)} data-tip="Every saved version of the week" data-testid="cst-versions">{cur ? `v${cur.v} · ${cur.by}` : 'No plan yet'}</button>
      <small className="cst-hint">{dirty ? 'Unsaved: drag more, then Save.' : 'Drag a clip onto a day. Nothing posts from here: each one still waits for your approve.'}</small>
    </div>
    <AnimatePresence>{showV ? <motion.ol className="cst-vers" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} data-testid="cst-ver-list">
      {(plan?.versions || []).slice().reverse().map(v => <li key={v.v} className={v.v === cur?.v ? 'is-cur' : ''}><em className="m-num">v{v.v}</em><span className={`cst-by is-${v.by}`}>{v.by}</span><small>{v.why}</small><small className="m-num">{(v.slots || []).length} slots · {ago(v.at)}</small>
        {v.v !== cur?.v ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => onUndo(v.v)} data-testid={`cst-back-${v.v}`}><Undo2 size={11} /> Back to this</button> : <b>now</b>}</li>)}
    </motion.ol> : null}</AnimatePresence>
    {cur?.why ? <p className="cst-planwhy"><Sparkles size={12} /> {cur.why}{cur.cost ? <em className="m-num"> · ${Number(cur.cost).toFixed(4)}</em> : null}</p> : null}
    <div className="cst-week-main">
      <DndContext sensors={sensors} onDragEnd={onEnd}>
        <div className="cst-board">
          <Drop id="tray" className="cst-tray" label="Clips without a day">
            <span className="m-label">NO DAY · {tray.length}</span>
            {tray.map(f => <Drag key={f.id} id={f.id} className="cst-mini"><Mini f={f} /></Drag>)}
            {!tray.length ? <small className="cst-none">Every clip has a day.</small> : null}
          </Drop>
          <div className="cst-days">{DAYS.map((d, i) => { const rows = draft.filter(s => s.day === d); return <Drop key={d} id={d} className={`cst-day${i === today ? ' is-today' : ''}`} label={d}>
            <header><b>{d}</b>{i === today ? <small>today</small> : null}<em className="m-num">{rows.length || ''}</em></header>
            {rows.map(s => (byId[s.job] ? <Slot key={s.job} s={s} f={byId[s.job]} locked={!!byId[s.job].posted} onSet={p => set(s.job, p)} onOff={() => setDraft(x => moveSlot(x, s.job, ''))} /> : null))}
          </Drop>; })}</div>
        </div>
      </DndContext>
      <Chat plan={plan} busy={busy} onSend={onChat} onUndo={onUndo} />
    </div>
  </div>;
}

export default function ClipStudio({ cat, clips, plan, kit, templates, rendering = [], runs = [], api, onPocs, onPlan, onTemplates, onOpen, onSlot, links, busy: slotBusy }) {
  const [view, setView] = useState(readView); const [edit, setEdit] = useState(null); const [busy, setBusy] = useState(''); const [msg, setMsg] = useState(''); const [seed, setSeed] = useState(null);
  const go = k => { setView(k); if (k !== 'edit') setSeed(null); try { localStorage.setItem(VIEW_KEY, k); } catch { /* private window */ } };
  const call = async (key, path, body) => { setBusy(key); setMsg(''); try { const j = await api(path, body); if (j.plan) onPlan?.(j.plan); if (j.templates) onTemplates?.(j.templates); if (j.pocFolders) onPocs?.(j.pocFolders); return j; } catch (e) { setMsg(e.message); return null; } finally { setBusy(''); } };
  const f = clips.find(x => x.id === edit) || clips.find(x => !x.posted) || null;
  const uniq = useMemo(() => new Set(clips.filter(x => x.studio.look).map(x => sig(x.studio.look))).size, [clips]);
  const planned = clips.filter(x => x.studio.slot).length;
  const TABS = [['grid', 'Clips', Grid3x3, clips.length], ['week', 'Week', CalendarDays, planned ? `${planned}/${clips.length}` : ''], ['tpl', 'Templates', LayoutTemplate, (templates?.list || []).filter(x => !x.legacy).length || ''], ['edit', 'Edit', Wand2, '']];
  const tplOf = look => ((templates?.list || []).some(x => x.id === look?.preset) ? { tpl: look.preset } : {});
  return <section ref={box} className="cst" data-testid="clip-studio">
    <div className="cst-top">
      <div className="m-seg cst-tabs" role="tablist" aria-label="Clip studio">{TABS.map(([k, l, Ic, n]) => <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'active' : ''} onClick={() => go(k)} data-testid={`cst-tab-${k}`}><Ic size={13} /> {l}{n ? <em className="m-num">{n}</em> : null}</button>)}</div>
      <span className="cst-stats"><span data-tip="Clips with a look no other clip has"><b className="m-num">{uniq}</b>/{clips.length} unique looks</span>{rendering.length ? <span className="is-busy"><Loader2 size={11} className="cst-spin" /> {rendering.length} rendering</span> : null}</span>
    </div>
    {msg ? <small className="cst-err" role="alert" data-testid="cst-err">{msg}</small> : null}
    <motion.div key={view} className="cst-pane" initial={{ y: 4 }} animate={{ y: 0 }} transition={{ duration: 0.16 }}>
      {view === 'grid' ? <Grid clips={clips} rendering={rendering} onEdit={id => { setEdit(id); go('edit'); }} onOpen={onOpen} onSlot={onSlot} links={links} busy={slotBusy} />
        : view === 'tpl' ? <ClipTemplates clips={clips} templates={templates} busy={busy} call={call} onEdit={x => { setSeed({ look: x.look, tpl: x, at: Date.now() }); go('edit'); }} />
        : view === 'week' ? <Week clips={clips} plan={plan} busy={busy} onSave={slots => call('save', '/plan', { slots })} onAgent={() => call('agent', '/plan/agent', {})}
          onChat={text => call('chat', '/plan/chat', { text })} onUndo={v => call('undo', '/plan/undo', { v })} />
          : f ? <ClipEdit key={f.id} cat={cat} f={f} clips={clips} kit={kit} run={runs.find(r => r.id === f.studio.clip.run)} api={api} busy={busy} rendering={rendering.includes(f.id)}
            pick={<select className="m-input cst-sel" value={f.id} onChange={e => { setEdit(e.target.value); setSeed(null); }} aria-label="Clip to edit" data-testid="cst-edit-pick">{clips.map(x => <option key={x.id} value={x.id} disabled={!!x.posted}>#{x.n} {x.studio.hook}</option>)}</select>}
            templates={templates} seed={seed} onSaveTpl={body => call('tsave', '/template/save', body)}
            onLook={(look, why) => call('look', '/look', { job: f.id, look, why, ...tplOf(look) })} onMind={ask => call('mind', '/look/mind', { job: f.id, ask })} onUndo={v => call('lundo', '/look/undo', { job: f.id, v })} twin={l => twinOf(l, clips, f.id)} />
            : <p className="cst-none">No clip to edit yet.</p>}
    </motion.div>
  </section>;
}
export { fullLook };

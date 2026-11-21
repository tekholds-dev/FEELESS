import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Md, stamp } from './DeskLook';
import { OwnWindow } from '../command/ProofWorkspace';
import { pollMs } from '../../lib/saverMode';
import { ENDED, STATE_WORD, elapsed, inScope, isLive, thoughtLabel, thoughtsFor, tone, usd } from '../../lib/taskChats';
import '../../styles/taskChat.css';

// 🧵 SLICE 35 · TASK CHATS (owner 2026-11-20: "the same brain runs a separate convo window in that same original chat that redirects to the new chat
// that's doing that task live … a dropdown for that thought before the mind processes something else … just like your chat!").
// A card in the chat it came from (title · state · current step · elapsed · cost, one click opens it), and the task chat itself: the checklist on
// top (done ✓ · doing spinner · pending dashed), each thought a fold-open dropdown that closes once the mind moves on, tool / log rows with their
// times, the cost per step, and a line to steer it, pause, resume, stop or raise its cap. It docks beside the chat or pops out to its own window;
// at phone width it is a sheet. Every button calls the server's own op (fc_taskchat.op): text work only, nothing here can move money.

const Ctx = createContext(null);
export const useTaskChats = () => useContext(Ctx);

/** <TaskChatProvider call={body => work(catId, body)}> — one poll for the whole desk (no request waterfall), the open task, dock or pop-out. */
export function TaskChatProvider({ call, children }) {
  const [cards, setCards] = useState([]); const [parallel, setParallel] = useState(1);
  const [openId, setOpenId] = useState(null); const [mode, setMode] = useState('dock'); const [err, setErr] = useState('');
  const callRef = useRef(call); callRef.current = call; const contRef = useRef(null); const [canCont, setCanCont] = useState(false);   // ↪ the chat that can take a recap and carry on from it (no chat → no button)
  const refresh = useCallback(() => callRef.current({ op: 'task_list' }).then(j => { if (j?.tasks) { setCards(j.tasks); setParallel(j.parallel || 1); } }).catch(() => {}), []);
  const live = cards.some(c => isLive(c.state));
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { const t = setTimeout(() => { if (!document.hidden) refresh(); }, pollMs(live ? 2500 : 15000)); return () => clearTimeout(t); }, [cards, live, refresh]);
  const split = useCallback(async (brief, scope = 'desk') => {
    setErr('');
    try { const j = await callRef.current({ op: 'task_new', text: brief, job: scope }); if (j?.tasks) setCards([...j.tasks].reverse()); if (j?.task) setOpenId(j.task.id); return j?.task || null; }
    catch (e) { setErr(e.message || 'It did not split.'); return null; }
  }, []);
  const setPar = useCallback(async n => { const j = await callRef.current({ op: 'task_parallel', cap: n }); setParallel(j?.parallel || n); refresh(); return j; }, [refresh]);
  const value = useMemo(() => ({ cards, parallel, setParallel: setPar, split, refresh, open: id => { setOpenId(id); setMode(m => (m === 'own' ? 'own' : 'dock')); }, openId, call: b => callRef.current(b), err, canContinue: canCont, continueWith: c => contRef.current?.(c), onContinue: fn => { contRef.current = fn; setCanCont(!!fn); } }),
    [cards, parallel, setPar, split, refresh, openId, err, canCont]);
  const pane = openId ? <TaskChatPane id={openId} onClose={() => setOpenId(null)} onOwn={() => setMode('own')} own={mode === 'own'} /> : null;
  return <Ctx.Provider value={value}>{children}
    {pane && mode === 'own' ? <OwnWindow title="Task chat" onClose={why => { setMode('dock'); if (why !== 'blocked') setOpenId(null); }}>{pane}</OwnWindow> : null}
    {pane && mode !== 'own' ? createPortal(<aside className="tch-dock" role="dialog" aria-label="Task chat" data-testid="tch-dock">{pane}</aside>, document.body) : null}
  </Ctx.Provider>;
}

/** The card a task leaves in the chat it came from. */
export function TaskCard({ c }) {
  const ctx = useTaskChats();
  if (!c) return null;
  const ended = ENDED.includes(c.state);
  return <div className={`tch-card is-${tone(c.state)}`} data-testid={`tch-card-${c.id}`} data-state={c.state}>
    <span className="tch-card-h"><i className="tch-glyph" aria-hidden="true" /><b>{c.title}</b><span className="tch-sp" />{c.test ? <span className="dkl-chip is-warn">TEST</span> : null}
      <span className={`dkl-chip tch-st is-${tone(c.state)}`} data-testid="tch-card-state">{STATE_WORD[c.state] || c.state}</span></span>
    {!ended ? <span className="tch-now">{c.steps ? <span className="m-num">{Math.min(c.stepN || 0, c.steps)}/{c.steps}</span> : null}<span>{c.step || c.why || (c.state === 'queued' ? 'waiting its turn' : 'planning the steps')}</span></span> : null}
    {c.steps ? <span className="tch-bar" aria-hidden="true"><i style={{ transform: `scaleX(${Math.min(1, (c.stepN || 0) / c.steps)})` }} /></span> : null}
    {ended && (c.recap || c.why) ? <p className="tch-recap" data-testid="tch-card-recap">{c.recap || c.why}</p> : null}
    <span className="tch-card-f"><span className="m-num" data-testid="tch-card-time">{elapsed(c.secs)}</span><span className="m-num" data-testid="tch-card-cost">{usd(c.cost)}</span><span className="tch-sp" />
      {ended && c.recap && ctx?.canContinue ? <button type="button" className="tch-btn" onClick={() => ctx.continueWith(c)} data-testid={`tch-continue-${c.id}`}>Continue from it</button> : null}
      <button type="button" className="tch-btn is-go" onClick={() => ctx?.open(c.id)} data-testid={`tch-open-${c.id}`}>Open task chat</button></span>
  </div>;
}

/** The task chats of one place (the desk, or a proof's chat): live ones up top, a split line, the last few ended. */
export function TaskStrip({ scope = 'desk', title = 'Task chats', max = 3, hideEmpty = false }) {
  const ctx = useTaskChats(); const [brief, setBrief] = useState(''); const [busy, setBusy] = useState(false);
  if (!ctx) return null;
  const mine = ctx.cards.filter(c => inScope(c, scope));
  if (hideEmpty && !mine.length) return null;
  const live = mine.filter(c => isLive(c.state)); const ended = mine.filter(c => !isLive(c.state)).slice(0, Math.max(0, max - live.length));
  const go = async e => { e.preventDefault(); const b = brief.trim(); if (b.length < 3 || busy) return; setBusy(true); const t = await ctx.split(b, scope); setBusy(false); if (t) setBrief(''); };
  return <section className="tch-strip" aria-label={title} data-testid={`tch-strip-${scope.split(':')[0]}`}>
    <header><b>{title}</b>{live.length ? <span className="dkl-chip is-live">{live.length} live</span> : null}<span className="tch-sp" /><small className="m-num">{ctx.parallel} at a time</small></header>
    {[...live, ...ended].map(c => <TaskCard key={c.id} c={c} />)}
    <form className="tch-split" onSubmit={go}>
      <input value={brief} onChange={e => setBrief(e.target.value)} placeholder="Split a task: what done looks like…" aria-label="Split a task" data-testid={`tch-split-in-${scope.split(':')[0]}`} maxLength={600} />
      <button type="submit" className="tch-btn is-go" disabled={busy || brief.trim().length < 3} data-testid={`tch-split-go-${scope.split(':')[0]}`}>Split</button>
    </form>
    {ctx.err ? <p className="tch-err" role="status">{ctx.err}</p> : null}
  </section>;
}

function Check({ s }) {
  return <i className={`tch-ck is-${s}`} aria-label={s === 'done' ? 'done' : s === 'doing' ? 'doing' : 'pending'}>{s === 'done' ? '✓' : null}</i>;
}

/** One thought as a fold-open dropdown: open while it is the mind's newest, closed once it moves on (your own click wins). */
function Thought({ t, newest }) {
  const [mine, setMine] = useState(null);
  return <details className="tch-thought" open={mine ?? newest} onToggle={e => { if (e.currentTarget.open !== newest) setMine(e.currentTarget.open); }} data-testid="tch-thought">
    <summary>{thoughtLabel(t)}</summary><p>{t.text}</p></details>;
}

/** The task chat itself. */
export function TaskChatPane({ id, onClose, onOwn, own = false }) {
  const ctx = useTaskChats(); const [t, setT] = useState(null); const [line, setLine] = useState(''); const [cap, setCap] = useState(''); const [say, setSay] = useState('');
  const load = useCallback(() => ctx?.call({ op: 'task_get', job: id }).then(j => j?.task && setT(j.task)).catch(e => setSay(e.message)), [ctx, id]);
  useEffect(() => { setT(null); load(); }, [load]);
  const live = t && isLive(t.state);
  useEffect(() => { if (!live) return undefined; const k = setTimeout(() => { if (!document.hidden) load(); }, pollMs(1500)); return () => clearTimeout(k); }, [t, live, load]);
  const act = async (op, extra = {}) => { setSay(''); try { const j = await ctx.call({ op, job: id, ...extra }); if (j?.task) setT(j.task); ctx.refresh(); } catch (e) { setSay(e.message); } };
  if (!t) return <div className="tch-pane" data-testid="tch-pane"><p className="tch-empty">{say || 'Opening the task chat…'}</p></div>;
  const lastThought = (t.thoughts || []).length - 1;
  const idx = th => (t.thoughts || []).indexOf(th);
  const logsFor = k => (t.logs || []).filter(l => l.step === k);
  const general = (t.logs || []).filter(l => l.step == null);
  const firstAt = Math.min(...t.checklist.map(s => Number(s.at) || Infinity));   // general rows before the first step sit above the steps, the rest below
  const before = general.filter(l => l.at <= firstAt + 0.05); const after = general.filter(l => !(l.at <= firstAt + 0.05));   // log times are rounded to 0.01 s
  const doing = t.checklist.findIndex(s => s.state === 'doing');
  return <div className="tch-pane" data-testid="tch-pane" data-state={t.state}>
    <header className="tch-pane-h"><i className="tch-glyph" aria-hidden="true" /><b>{t.title}</b><span className={`dkl-chip tch-st is-${tone(t.state)}`} data-testid="tch-pane-state">{STATE_WORD[t.state]}</span><span className="tch-sp" />
      <span className="m-num" data-tip="Time on it">{elapsed(t.secs)}</span><span className="m-num" data-tip="Spent of its cap" data-testid="tch-pane-cost">{usd(t.cost)} / {usd(t.cap)}</span>
      {!own && onOwn ? <button type="button" className="tch-ic" onClick={onOwn} aria-label="Open in its own window" data-tip="Its own window (a second screen)" data-testid="tch-own">⧉</button> : null}
      {onClose ? <button type="button" className="tch-ic" onClick={onClose} aria-label="Close the task chat" data-testid="tch-close">✕</button> : null}</header>
    <p className="tch-brief"><small>{t.by === 'mind' ? 'Its mind split this off' : 'You split this off'} · {String(t.model || '').split('/').pop() || 'its mind'}{t.scope?.kind && t.scope.kind !== 'desk' ? ` · from its ${t.scope.kind.toUpperCase()}` : ''}</small>{t.brief}</p>
    <ol className="tch-list" aria-label="Checklist" data-testid="tch-checklist">
      {t.checklist.length ? t.checklist.map((s, k) => <li key={k} className={`is-${s.state}`} data-testid={`tch-step-${k}`}><Check s={s.state} /><span>{s.text}</span>{s.cost ? <small className="m-num">{usd(s.cost)}</small> : null}</li>)
        : <li className="is-doing"><Check s="doing" /><span>Planning the steps</span></li>}
    </ol>
    <div className="tch-flow" aria-live="polite">
      {thoughtsFor(t, -1).map(th => <Thought key={`p${idx(th)}`} t={th} newest={live && idx(th) === lastThought && doing < 0} />)}
      {before.map((l, i) => <p key={`g${i}`} className="tch-log"><time className="m-num">{stamp(l.at)}</time><span>{l.text}</span></p>)}
      {t.checklist.map((s, k) => s.state === 'pending' ? null : <section key={k} className="tch-stepblock" data-testid={`tch-block-${k}`}>
        <h5><Check s={s.state} />{k + 1}. {s.text}{s.secs ? <small className="m-num">{s.secs}s · {usd(s.cost)}</small> : null}</h5>
        {thoughtsFor(t, k).map(th => <Thought key={`t${idx(th)}`} t={th} newest={live && idx(th) === lastThought && doing < 0} />)}
        {logsFor(k).map((l, i) => <p key={i} className="tch-log"><time className="m-num">{stamp(l.at)}</time><span>{l.text}</span></p>)}
        {s.did ? <div className="tch-did"><Md text={s.did} /></div> : s.state === 'doing' ? <p className="tch-thinking"><span className="dkl-typing" aria-hidden="true"><i /><i /><i /></span>thinking</p> : null}
      </section>)}
      {after.map((l, i) => <p key={`h${i}`} className="tch-log"><time className="m-num">{stamp(l.at)}</time><span>{l.text}</span></p>)}
      {t.recap ? <div className="tch-recapbox" data-testid="tch-recap"><b>Recap</b><Md text={t.recap} /></div> : null}
      {t.state === 'waiting' ? <p className="tch-ask" data-testid="tch-ask">{t.why}</p> : null}
    </div>
    {!ENDED.includes(t.state) ? <form className="tch-steer" onSubmit={e => { e.preventDefault(); const v = line.trim(); if (!v) return; setLine(''); act('task_say', { text: v }); }}>
      <input value={line} onChange={e => setLine(e.target.value)} placeholder={t.state === 'waiting' ? 'Answer it to go on…' : 'Steer it: the next step reads this'} aria-label="Steer the task" maxLength={400} data-testid="tch-steer-in" />
      <button type="submit" className="tch-btn is-go" disabled={!line.trim()} data-testid="tch-steer-go">Send</button>
      {t.state === 'paused' ? <button type="button" className="tch-btn" onClick={() => act('task_resume')} data-testid="tch-resume">Resume</button>
        : <button type="button" className="tch-btn" onClick={() => act('task_pause')} disabled={!['working', 'starting', 'queued'].includes(t.state)} data-testid="tch-pause">Pause</button>}
      <button type="button" className="tch-btn is-bad" onClick={() => act('task_stop')} data-testid="tch-stop">Stop</button>
      {t.state === 'waiting' && /cap/.test(t.why || '') ? <span className="tch-cap"><input value={cap} onChange={e => setCap(e.target.value)} inputMode="decimal" placeholder={String(t.cap * 2)} aria-label="New cap in dollars" data-testid="tch-cap-in" />
        <button type="button" className="tch-btn" onClick={() => act('task_cap', { cap: Number(cap) || t.cap * 2 })} data-testid="tch-cap-go">Raise cap</button></span> : null}
    </form> : null}
    {say ? <p className="tch-err" role="status">{say}</p> : null}
  </div>;
}

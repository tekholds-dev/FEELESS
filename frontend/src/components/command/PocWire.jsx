import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import rough from 'roughjs';
import { Check, Send, X } from 'lucide-react';
import '../../styles/pocWire.css';

// ✏️ CREATOR WORKFLOW (owner 2026-11-15, his IMG4: "IMG4 IS KINDA WHAT IMG3 SHOULD BE"). The PoC picture is step 1; the agent then browses sources,
// drafts the week and waits for your approval, drawn by hand (roughjs strokes, Excalidraw's own hand font). Every step is real: Browse and Draft
// send this proof's agent its normal paid PoC ask (op ws_build), its replies land in the chat box, and the week is read from its own words.
// Plan myself = no model calls, you write the days. AI draft = you press each step. Auto-plan weekly = Browse → Draft run on their own, again
// each time the board opens 7+ days after the last approved week. The board state is kept in this browser per picture.
export const STEPS = [['char', 'Character PoC'], ['browse', 'Browse sources'], ['draft', 'Draft the week'], ['review', 'Review & approve']];
export const MODES = [['self', 'Plan myself', 'You write the week yourself. No model calls.'], ['ai', 'AI draft', 'The agent browses and drafts when you press each step. Paid model calls.'], ['auto', 'Auto-plan weekly', 'Browse and Draft run on their own, and again each week you open this. Paid model calls.']];
const DAY_RE = /^\W*(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?\s*[:\-–—]\s*(.+)$/i;
const DAY_KEY = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' };
const WEEK = Object.values(DAY_KEY);
const WEEK_S = 7 * 86400;
const KEY = (doc, pic) => `feeless:pocflow:${doc || 'x'}:${pic || 'x'}`;
export const browseAsk = t => `Browse YouTube for hook patterns and TikTok for clip formats that would fit ${t} (the character in this proof). Reply with 3 hooks and 3 clip formats, one line each, and name the site each came from.`;
export const draftAsk = t => `Draft a week of posts for ${t}, using the hooks and formats you found. One line per post day, each line starting with the day, like "Mon: …", "Wed: …", "Fri: …". Three to five days.`;
const blankWeek = () => [{ d: 'Mon', text: '' }, { d: 'Wed', text: '' }, { d: 'Fri', text: '' }];

// Pure (tested): the week, read from the agent's own reply. "**Mon:** Draft 3 hooks" → { d: 'Mon', text: 'Draft 3 hooks' }; one line per day, first wins.
export function parseDays(text) {
  const out = []; const seen = new Set();
  String(text || '').replace(/\*\*|__/g, '').split(/\n+/).forEach(l => { const m = l.match(DAY_RE); if (!m) return; const d = DAY_KEY[m[1].toLowerCase()]; if (seen.has(d)) return; seen.add(d); out.push({ d, text: m[2].trim().slice(0, 140) }); });
  return out.sort((a, b) => WEEK.indexOf(a.d) - WEEK.indexOf(b.d));
}
// Pure (tested): the agent's answer to an ask sent at `at` (seconds): its newest worded message after it.
export function replyAfter(doc, at) {
  if (!at) return null;
  const rows = (doc?.messages || []).filter(m => m && m.by !== 'you' && !m.media && String(m.text || '').trim() && Number(m.at) >= at - 1);
  return rows.length ? rows[rows.length - 1] : null;
}
// Pure (tested): each step's state from the board record + the live doc → { char, browse, draft, review: 'done'|'running'|'todo'|'waiting', at: the current step }
export function flowState(rec, doc, picReady) {
  const busy = !!doc?.busy; const s = { char: picReady ? 'done' : 'todo' };
  const bRep = replyAfter(doc, rec.browseAt); const dRep = replyAfter(doc, rec.draftAt);
  s.browse = rec.mode === 'self' ? (rec.browseDone ? 'done' : 'todo') : !rec.browseAt ? 'todo' : rec.draftAt || (rec.days || []).length ? 'done' : busy ? 'running' : bRep ? 'done' : 'todo';
  s.draft = (rec.days || []).length ? 'done' : !rec.draftAt ? 'todo' : busy ? 'running' : dRep ? 'done' : 'todo';
  s.review = rec.approvedAt ? 'done' : s.draft === 'done' ? 'todo' : 'waiting';
  const at = STEPS.findIndex(([k]) => s[k] !== 'done');
  return { ...s, at: at < 0 ? STEPS.length : at, bRep, dRep };
}

function useSketch(draw, deps) {   // a hand-drawn layer that redraws when its box resizes
  const box = useRef(null); const svg = useRef(null);
  useLayoutEffect(() => {
    const el = box.current; const s = svg.current; if (!el || !s) return undefined;
    const go = () => { const w = el.offsetWidth; const h = el.offsetHeight; if (w < 8 || h < 8) return; s.setAttribute('width', w); s.setAttribute('height', h); s.setAttribute('viewBox', `0 0 ${w} ${h}`); while (s.firstChild) s.removeChild(s.firstChild); try { draw(rough.svg(s), w, h, s); } catch { /* no SVG layout here (tests): the box still shows */ } };
    go(); const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(go) : null; ro?.observe(el); return () => ro?.disconnect();
  }, deps);   // eslint-disable-line react-hooks/exhaustive-deps
  return [box, svg];
}
const rr = (x, y, w, h, r) => `M${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h} H${x + r} Q${x},${y + h} ${x},${y + h - r} V${y + r} Q${x},${y} ${x + r},${y} Z`;
function Box({ seed = 1, hot = false, r = 18, className = '', children, ...rest }) {
  const [box, svg] = useSketch((rc, w, h, s) => { s.appendChild(rc.path(rr(3, 3, w - 6, h - 6, r), { seed, roughness: 1.15, bowing: 1.4, strokeWidth: hot ? 3 : 2, stroke: 'currentColor' })); }, [seed, hot, r]);
  return <div ref={box} className={`cwf-box${hot ? ' is-hot' : ''} ${className}`} {...rest}><svg ref={svg} className="cwf-ink" aria-hidden="true" />{children}</div>;
}
function Pill({ children, seed = 3, tone = '' }) {
  const [box, svg] = useSketch((rc, w, h, s) => { s.appendChild(rc.path(rr(2, 2, w - 4, h - 4, (h - 4) / 2), { seed, roughness: .9, strokeWidth: 1.6, stroke: 'currentColor' })); }, [seed]);
  return <span ref={box} className={`cwf-pill ${tone}`}><svg ref={svg} className="cwf-ink" aria-hidden="true" />{children}</span>;
}
function Arrow({ seed = 7 }) {   // → between steps (↓ on a phone, turned by CSS)
  const [box, svg] = useSketch((rc, w, h, s) => {
    const o = { seed, roughness: 1, strokeWidth: 2.2, stroke: 'currentColor' }; const y = h / 2;
    s.appendChild(rc.line(4, y, w - 6, y, o)); s.appendChild(rc.line(w - 6, y, w - 16, y - 9, o)); s.appendChild(rc.line(w - 6, y, w - 16, y + 9, o));
  }, [seed]);
  return <div ref={box} className="cwf-arrow" aria-hidden="true"><svg ref={svg} className="cwf-ink" /></div>;
}
function Branch({ n, seed = 11 }) {   // the week plan forks to each day
  const [box, svg] = useSketch((rc, w, h, s) => {
    const o = { seed, roughness: 1.1, strokeWidth: 2.2, stroke: 'currentColor' }; const cx = w / 2;
    for (let i = 0; i < n; i += 1) { const x = (w / n) * (i + 0.5); s.appendChild(rc.curve([[cx, 2], [cx + (x - cx) * 0.55, h * 0.35], [x, h - 6]], o)); s.appendChild(rc.line(x, h - 3, x - 8, h - 13, o)); s.appendChild(rc.line(x, h - 3, x + 8, h - 13, o)); }
  }, [n, seed]);
  return <div ref={box} className="cwf-branch" aria-hidden="true"><svg ref={svg} className="cwf-ink" /></div>;
}
function Underline({ seed = 5 }) {
  const [box, svg] = useSketch((rc, w, h, s) => { s.appendChild(rc.curve([[2, h * 0.6], [w * 0.4, h * 0.2], [w - 2, h * 0.7]], { seed, roughness: 1.4, strokeWidth: 2.4, stroke: 'currentColor' })); }, [seed]);
  return <span ref={box} className="cwf-under" aria-hidden="true"><svg ref={svg} className="cwf-ink" /></span>;
}
const Status = ({ st, run }) => <Pill tone={`is-${st}`}>{st === 'done' ? 'Done' : st === 'running' ? run : 'To do'}</Pill>;

export default function PocWire({ src, kind = 'image', from = null, title = 'Picture', cat = null, doc = null, work = null, setDoc = null, onClose }) {
  const [rec, setRec] = useState(() => { try { return { mode: 'ai', ...(JSON.parse(localStorage.getItem(KEY(doc?.id, from)) || 'null') || {}) }; } catch { return { mode: 'ai' }; } });
  const [ask, setAsk] = useState(''); const [err, setErr] = useState(''); const [sending, setSending] = useState(false);
  const pic = kind === 'image' ? src : null; const live = !!(cat && doc && work);
  useEffect(() => { try { localStorage.setItem(KEY(doc?.id, from), JSON.stringify(rec)); } catch { /* blocked: the board still works */ } }, [rec, doc?.id, from]);
  useEffect(() => { document.body.classList.add('has-pwr'); const k = e => { if (e.key === 'Escape') onClose?.(); }; window.addEventListener('keydown', k); return () => { document.body.classList.remove('has-pwr'); window.removeEventListener('keydown', k); }; }, [onClose]);
  const st = useMemo(() => flowState(rec, doc, !!src), [rec, doc, src]);
  useEffect(() => {   // the agent's reply to Draft becomes the week (once; your edits after that stay yours)
    if (st.dRep && !doc?.busy && !(rec.days || []).length && !rec.draftRead) { const days = parseDays(st.dRep.text); setRec(r => ({ ...r, draftRead: true, days: days.length ? days : blankWeek(), draftLoose: !days.length })); }
  }, [st.dRep, doc?.busy]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {   // while it works, read its page every 4 s
    if (!live || !doc?.busy) return undefined;
    const t = setInterval(() => { if (!document.hidden) work(cat.id, { op: 'ws_open', text: doc.id }).then(j => j?.doc && setDoc?.(j.doc)).catch(() => {}); }, 4000);
    return () => clearInterval(t);
  }, [live, doc?.busy, doc?.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const send = useCallback(async text => {
    if (!live) { setErr('Open this from a PoC folder to talk to its agent.'); return false; }
    setErr(''); setSending(true);
    try { const j = await work(cat.id, { op: 'ws_build', job: doc.id, text, to: 'both' }); if (j?.doc) setDoc?.(j.doc); setSending(false); return true; } catch (e) { setErr(e.message || 'The agent could not take that.'); setSending(false); return false; }
  }, [live, cat?.id, doc?.id, work, setDoc]);   // eslint-disable-line react-hooks/exhaustive-deps
  const now = () => Date.now() / 1000;
  const browse = async () => { if (rec.mode === 'self') { setRec(r => ({ ...r, browseDone: true })); return; } const at = now(); if (await send(browseAsk(title))) setRec(r => ({ ...r, browseAt: at, draftAt: null, days: [], draftRead: false, approvedAt: null })); };
  const draft = async () => { if (rec.mode === 'self') { setRec(r => ({ ...r, days: blankWeek(), approvedAt: null })); return; } const at = now(); if (await send(draftAsk(title))) setRec(r => ({ ...r, draftAt: at, days: [], draftRead: false, approvedAt: null })); };
  useEffect(() => {   // 🔁 Auto-plan weekly: Browse → Draft on their own; a week after the last approval it starts over
    if (rec.mode !== 'auto' || !live || doc?.busy || sending) return;
    if (rec.approvedAt && now() - rec.approvedAt > WEEK_S) { setRec(r => ({ ...r, browseAt: null, draftAt: null, days: [], approvedAt: null, draftRead: false })); return; }
    if (st.char === 'done' && st.browse === 'todo' && !rec.browseAt) browse(); else if (st.browse === 'done' && st.draft === 'todo' && !rec.draftAt) draft();
  }, [rec.mode, st.browse, st.draft, doc?.busy]);   // eslint-disable-line react-hooks/exhaustive-deps
  const setDay = (i, text) => setRec(r => ({ ...r, approvedAt: null, days: r.days.map((x, k) => (k === i ? { ...x, text } : x)) }));
  const addDay = () => setRec(r => { const used = new Set((r.days || []).map(x => x.d)); const d = WEEK.find(x => !used.has(x)); return d ? { ...r, days: [...(r.days || []), { d, text: '' }].sort((a, b) => WEEK.indexOf(a.d) - WEEK.indexOf(b.d)) } : r; });
  const approve = () => setRec(r => ({ ...r, approvedAt: now() }));
  const askNow = async e => { e.preventDefault(); const q = ask.trim(); if (!q) return; if (await send(`About the "${STEPS[Math.min(st.at, 3)][1]}" step for ${title}: ${q}`)) setAsk(''); };
  const lastSaid = [...(doc?.messages || [])].reverse().find(m => m && m.by !== 'you' && !m.media && String(m.text || '').trim());
  const days = rec.days || []; const self = rec.mode === 'self'; const working = !!doc?.busy || sending;
  const here = Math.min(st.at, 3); const hot = k => STEPS[here][0] === k && st.at < 4;
  const tag = k => (st[k] === 'done' ? 'DONE' : st[k] === 'running' || hot(k) ? 'NOW' : st[k] === 'waiting' ? 'WAITING' : 'NEXT');
  const hooks = st.bRep ? String(st.bRep.text).split(/\n+/).map(l => l.replace(/^\W+/, '').replace(/\*\*/g, '').trim()).filter(l => l.length > 6).slice(0, 3) : [];

  return <div className="pwr cwf" role="dialog" aria-modal="true" aria-label={`Creator workflow: ${title}`} data-testid="poc-wire">
    <header className="cwf-head">
      <h2 className="cwf-title">CREATOR WORKFLOW<Underline /></h2>
      <div className="cwf-modes" role="radiogroup" aria-label="How the week is planned">{MODES.map(([k, l, tip], i) => <button key={k} type="button" role="radio" aria-checked={rec.mode === k} className={`cwf-mode${rec.mode === k ? ' is-on' : ''}`} onClick={() => setRec(r => ({ ...r, mode: k }))} data-tip={tip} data-testid={`cwf-mode-${k}`}><Box seed={20 + i} r={14} hot={rec.mode === k}>{l}</Box></button>)}</div>
      <button type="button" className="cwf-x" onClick={onClose} aria-label="Close" data-tip="Close (Esc)" data-testid="pwr-close"><X size={20} /></button>
    </header>
    {err ? <p className="cwf-err" role="alert">⚠ {err}</p> : null}
    <div className="cwf-board">
      <p className="cwf-here" style={{ '--col': st.at >= 4 ? 5 : here * 2 + 1 }} data-testid="cwf-here"><i aria-hidden="true">≈</i>{st.at >= 4 ? 'WEEK APPROVED · 4/4' : `YOU ARE HERE · ${here + 1}/4`}<i aria-hidden="true">≈</i></p>
      <div className="cwf-flow">
        <Box seed={2} className="cwf-char" hot={hot('char')} data-testid="cwf-step-char">
          {pic ? <img src={pic} alt="" draggable={false} /> : <span className="cwf-nopic">{kind === 'video' ? 'Video' : 'No picture'}</span>}
          <span className="cwf-cap">{String(title).slice(0, 22)} · {st.char === 'done' ? 'Ready' : 'Not ready'}</span>
          {st.char === 'done' ? <span className="cwf-tick" aria-label="Ready"><Check size={16} strokeWidth={3.5} /></span> : null}
        </Box>
        <Arrow seed={31} />
        <Box seed={4} className="cwf-step" hot={hot('browse')} data-testid="cwf-step-browse">
          <b className="cwf-h">Browse sources</b>
          <ul className="cwf-src">
            {[['YouTube', 'Find hook patterns'], ['TikTok', 'Compare clip formats']].map(([site, job]) => <li key={site}><span className={`cwf-chk is-${st.browse}`} aria-hidden="true">{st.browse === 'done' ? <Check size={14} strokeWidth={3.5} /> : null}</span><span className="cwf-job">{site} · {job}</span><Status st={st.browse} run="Browsing" /></li>)}
          </ul>
          {hooks.length ? <ol className="cwf-found" data-testid="cwf-found">{hooks.map((h, i) => <li key={i}>{h.slice(0, 90)}</li>)}</ol> : null}
          {st.browse !== 'running' ? <button type="button" className="cwf-go" disabled={working || st.char !== 'done'} onClick={browse} data-tip={self ? 'Mark it done: you browsed yourself' : 'The agent browses YouTube and TikTok for this character. Paid model call'} data-testid="cwf-browse">{self ? (st.browse === 'done' ? 'Browsed ✓' : 'I browsed') : st.browse === 'done' ? 'Browse again' : 'Browse now'}</button> : null}
        </Box>
        <Arrow seed={33} />
        <Box seed={6} className="cwf-step" hot={hot('draft')} data-testid="cwf-step-draft">
          <Pill seed={41}>{tag('draft')}</Pill><b className="cwf-h">Draft the week</b>
          {st.draft !== 'running' ? <button type="button" className="cwf-go" disabled={working || (!self && st.browse !== 'done')} onClick={draft} data-tip={self ? 'Start Mon / Wed / Fri cards to write yourself' : 'The agent drafts the week from what it found. Paid model call'} data-testid="cwf-draft">{self ? 'Write it' : days.length ? 'Draft again' : 'Draft it'}</button> : <small className="cwf-wait">Drafting…</small>}
        </Box>
        <Arrow seed={35} />
        <Box seed={8} className="cwf-step" hot={hot('review')} data-testid="cwf-step-review">
          <Pill seed={43} tone={st.review === 'done' ? 'is-done' : ''}>{st.review === 'done' ? 'APPROVED' : tag('review')}</Pill><b className="cwf-h">Review &amp; approve</b>
          {st.review !== 'waiting' ? <button type="button" className="cwf-go" disabled={!days.some(x => x.text.trim())} onClick={approve} data-tip="Locks this week. Editing a day opens it again" data-testid="cwf-approve">{st.review === 'done' ? 'Approved ✓' : 'Approve week'}</button> : null}
        </Box>
      </div>
      <div className="cwf-lower">
        <div className="cwf-chatcol"><span className="cwf-stem" aria-hidden="true" />
          <Box seed={12} className="cwf-chat" data-testid="cwf-chat">
            <b className="cwf-h is-s">Chat with agent</b>
            <p className="cwf-said" data-testid="cwf-said">{working ? 'Working on it…' : lastSaid ? String(lastSaid.text).replace(/\*\*/g, '').slice(0, 220) : live ? 'Nothing said yet. Ask it about this step.' : 'Open this from a PoC folder to talk to its agent.'}</p>
            <form className="cwf-ask" onSubmit={askNow}><Box seed={14} r={12}><input value={ask} onChange={e => setAsk(e.target.value)} placeholder="Ask about this step…" aria-label="Ask about this step" disabled={!live || working} data-testid="cwf-ask" />
              <button type="submit" disabled={!live || working || !ask.trim()} aria-label="Send" data-tip="Sends it to this proof's agent. Paid model call" data-testid="cwf-send"><Send size={18} /></button></Box></form>
          </Box>
        </div>
        <div className="cwf-weekcol">
          <span className="cwf-stem" aria-hidden="true" />
          <p className="cwf-wk"><i aria-hidden="true">≈</i>Week plan · {st.review === 'done' ? 'approved' : days.length ? 'draft' : 'empty'}<i aria-hidden="true">≈</i></p>
          {days.length ? <><Branch n={days.length} />
            <div className="cwf-days" style={{ '--n': days.length }}>{days.map((x, i) => <Box key={x.d} seed={50 + i} r={14} className="cwf-day" data-testid={`cwf-day-${x.d}`}>
              <b>{x.d}<Underline seed={60 + i} /></b>
              <textarea value={x.text} onChange={e => setDay(i, e.target.value)} rows={3} maxLength={140} placeholder="What goes out" aria-label={`${x.d} post`} />
            </Box>)}</div>
            {days.length < 7 ? <button type="button" className="cwf-add" onClick={addDay} data-tip="Add another post day" data-testid="cwf-add">+ day</button> : null}
            {rec.draftLoose ? <small className="cwf-wait">It did not write the days as "Mon: …", so the cards start empty. Its reply is in the chat.</small> : null}</>
            : <small className="cwf-wait">{st.draft === 'running' ? 'Drafting the week…' : 'The week shows here once it is drafted.'}</small>}
        </div>
      </div>
    </div>
  </div>;
}

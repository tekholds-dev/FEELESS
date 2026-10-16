// 🧠 THE BRAIN — direct LM chat + owner-approved agent updates (backend/ai_chat.py). One component, three places: the 🧠 AI tab in HQ ›
// Agents, the creator's mini cat (🧠 Brain tab) and a full-window pop-out (⤢). Its own state: an answer patches THIS panel only — never the
// agent hub, the chart, the stream or the P&L. It LEARNS on the owner's tap (🧠 Remember → a lesson every model case reads) and FIXES
// agents only on the owner's call (🛠 proposals → ✅ Approve). Modes: 💬 Chat · 🔎 Case review · 🛠 Fix agents.
import { AiPlayground } from './AiPlayground';
import { AiActivity } from './AiActivity';
import React, { forwardRef, memo, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { uploadImage } from '../../lib/adminCall';
import { holdFx } from '../../lib/fxPause';
import '../../styles/brainChat.css';

export const CHAT_MODES = [['chat', '💬 Chat', 'Talk to the model in normal language — it sees the desk\'s current state'],
  ['case', '🔎 Case', 'The structured read of the coin on the chart (validated JSON → shown as a verdict)'],
  ['improve', '🛠 Fix agents', 'The model may PROPOSE agent changes. Nothing changes until you approve each one.'],
  ['build', '🧱 Build', 'The model proposes things to BUILD (a vital, a meter, a check, a test). Ideas only — filed for you, nothing is applied.']];
// one-tap prompts, per mode (trench words; each is just a message — nothing is pre-approved)
export const QUICK = {
  chat: [['🩸 Why are we bleeding?', 'Why did the last real trades lose? Use the outcomes and the money record. Be blunt.'], ['👀 Best seat right now?', 'Which coin on the desk right now is the cleanest setup, and what kills it?'],
    ['🧟 Who is the weak agent?', 'Which of the ten agents is costing us the most right now, and why?'], ['🔥 Roast the last trade', 'Roast the last real trade in two lines, then say what a sharp trencher would have done.']],
  case: [['🔎 Full read', ''], ['☠ What rugs it?', 'What is the single most likely way this rugs or bleeds?'], ['🚪 Where is the exit?', 'If we are in this, what is the sign to leave?']],
  improve: [['🛠 Fix what is losing', 'Look at the outcomes, the money record and the trail. Propose the changes that fix what is losing.'], ['🎓 Teach from the last loss', 'Turn the last real loss into ONE lesson the model should read on every fitting case.'],
    ['⚖ Rank down the leak', 'Which cause from the vocabulary keeps showing up in the losses? Propose a rank weight for it.'], ['🎚 Tune the exits', 'Winners are banked small and rugs cost a seat. Propose ONE exit notch for a shadow test.']],
  build: [['🫀 Missing vital', 'Which vital is UNKNOWN or PENDING most often in CONTEXT and would have changed a recent decision? Propose how to collect and draw it.'], ['📊 New live meter', 'Propose ONE new live visual for the desk that shows a number the owner cannot see today.'],
    ['🧪 Test for the last loss', 'Which check or test would have caught the last real loss? Propose it.'], ['🧹 What is clutter?', 'What on the desk is duplicate or never changes a decision? Propose what to cut.']],
};
const KIND = { cfg: '⚙ switch', lesson: '🎓 lesson', weight: '⚖ rank weight', tune: '🎚 exit notch → shadow', idea: '💡 idea' };
const show = v => (v === true ? 'ON' : v === false ? 'OFF' : v == null ? '—' : String(v));

// pure: the meta line under an answer (provider · model · latency · tokens)
export const metaLine = r => [r?.provider, r?.model, r?.ms != null ? `${(r.ms / 1000).toFixed(1)}s` : null, r?.tokens ? `${r.tokens.in}→${r.tokens.out} tok` : null].filter(Boolean).join(' · ');
// pure: the header's mood from real state (never a canned ticker)
export function brainMood(busy, brain, last) {
  if (busy) return { key: 'work', word: '⚡ COOKING', line: 'the model is reading the desk…' };
  const b = last?.provider ? last : brain;
  if (!b?.provider) return { key: 'off', word: '💤 NO MODEL', line: 'no provider is online — start LM Studio or add a key' };
  return { key: 'on', word: '🟢 LOCKED IN', line: metaLine(b) };
}

// 💻 the local lane's 24h watch: one bar per hour (height = reads that answered, red tick = failures, amber = paused for browser lag)
export function LocalWatch({ w }) {
  if (!w) return null;
  const hrs = w.hours || []; const top = Math.max(1, ...hrs.map(h => h.n));
  return <div className="cch-watch" data-testid="cch-watch">
    <p><b>{w.reads24h ?? 0}</b> local reads in 24h · <b>{w.fails24h ?? 0}</b> failed · <b>{w.paused24h ?? 0}</b> paused for lag{w.every ? ` · next every ${w.every}s (${w.why})` : ''}</p>
    <span className="cch-wbars" aria-hidden="true">{hrs.map(h => <i key={h.hour} className={h.paused ? 'is-paused' : h.fail ? 'is-fail' : ''} style={{ transform: `scaleY(${Math.max(0.06, h.n / top)})` }}
      data-tip={`${new Date(h.hour * 1000).getHours()}:00 · ${h.ok} answered${h.avgSec ? ` (${h.avgSec}s avg)` : ''} · ${h.fail} failed · ${h.paused} paused`} />)}</span></div>;
}

function Proposal({ p, busy, onDecide }) {
  return <li className={`cch-prop is-${p.status}`} data-testid={`cch-prop-${p.id}`}>
    <p className="cch-phead"><b>{String(p.agent).toUpperCase()}</b><em>{KIND[p.kind] || p.kind}</em><span>{p.key}</span>{p.status !== 'pending' ? <u>{p.status.toUpperCase()}</u> : null}</p>
    {p.kind === 'idea' ? <p className="cch-diff"><span className="is-new"><small>BUILD</small>{show(p.new)}</span></p>   /* an idea has no "now" value — only what would be built */
      : <p className="cch-diff"><span className="is-old"><small>NOW</small>{show(p.old)}</span><i aria-hidden>→</i><span className="is-new"><small>PROPOSED</small>{show(p.new)}</span></p>}
    <details className="cch-more"><summary>why · effect · rollback</summary>
      {p.reason ? <p className="cch-why"><small>WHY</small>{p.reason}</p> : null}
      {p.effect ? <p className="cch-why"><small>EFFECT</small>{p.effect}</p> : null}
      <p className="cch-why"><small>ROLLBACK</small>{p.rollback}</p></details>
    {p.applied ? <p className="cch-why is-applied"><small>APPLIED</small>{p.applied}</p> : null}
    {p.status === 'pending' ? <p className="cch-acts"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onDecide(p.id, true)} data-testid={`cch-approve-${p.id}`}>✅ Approve</button>
      <button type="button" className="m-btn" disabled={busy} onClick={() => onDecide(p.id, false)} data-testid={`cch-reject-${p.id}`}>✕ Reject</button></p> : null}
  </li>;
}

// 🧵 the log is its own memoized piece: a hub tick, a seat price or a settings tap never re-renders (or re-animates) the messages.
// Only messages added in THIS mode since the last send animate in (`from`); switching modes / panes shows a thread still.
// 📚 what an answer was built from: FEELESS's own records for the asked window (LIVE FEELESS · PARTIAL · NO HISTORY) + what was missing
export const DATA_TONE = { 'LIVE FEELESS': 'is-live', PARTIAL: 'is-part', 'NO HISTORY': 'is-none' };
export function DataChip({ d }) {
  return <em className={`cch-data ${DATA_TONE[d.state] || 'is-none'}`} data-testid="cch-data" data-tip={(d.gaps || []).length ? `missing: ${d.gaps.join(' · ')}` : 'every source answered for this window'}>
    DATA: {d.state}{d.window ? ` · ${d.window}` : ''}{d.exits ? ` · ${d.exits} real exits` : ''}</em>;
}

// 🌐 the web results the answer was built from — each a real link the owner can open
export function WebSrc({ w }) {
  return <span className="cch-web" data-testid="cch-web"><small>🌐 SOURCES</small>{w.slice(0, 5).map((x, i) => {
    let host = ''; try { host = new URL(x.url).hostname.replace(/^www\./, ''); } catch { host = 'link'; }
    return /^https?:\/\//.test(x.url || '') ? <a key={x.url} href={x.url} target="_blank" rel="noopener noreferrer" data-tip={x.title}>{i + 1} · {host}</a> : null;
  })}</span>;
}

const ChatLog = memo(function ChatLog({ hist, err, busy, from, onRemember, onBuild, onEdit, onDelete }) {
  const end = useRef(null);
  useEffect(() => { const el = end.current; if (el && el.parentNode) el.parentNode.scrollTop = el.parentNode.scrollHeight; }, [hist, busy]);
  return <ol className="cch-log" data-testid="cch-log" aria-live="polite">
    {err && !hist.length ? <li className="cch-nil is-warn" data-testid="cch-err">⚠ {err}</li> : null}
    {hist.length ? hist.map((t, i) => <li key={`${i}-${t.text.slice(0, 12)}`} className={`cch-msg is-${t.role} ${i >= from ? 'is-fresh' : ''}`}><small>{t.role === 'user' ? 'YOU' : 'BRAIN'}</small>{t.meta?.img ? <img className="cch-img" src={t.meta.img} alt="attached" loading="lazy" /> : null}<span>{t.text}</span>
      {t.meta?.data ? <DataChip d={t.meta.data} /> : null}
      {t.meta?.web?.length ? <WebSrc w={t.meta.web} /> : null}
      <i className="cch-mact">{t.role !== 'user' && t.text.length >= 8 && !t.text.startsWith('⚠') ? <><button type="button" onClick={() => onRemember(t.text)} data-tip="Remember this: it becomes a lesson every fitting model read sees" data-testid={`cch-rem-${i}`}>🧠 Remember</button>
          <button type="button" onClick={() => onBuild(t.text)} data-tip="Build this: your tap is the permission — it joins the build queue the next build session ships" data-testid={`cch-build-${i}`}>🧱 Build this</button></> : null}
        {t.role === 'user' ? <button type="button" onClick={() => onEdit(i, t.text)} disabled={busy} data-tip="Edit: rewinds the chat to here and puts your words back in the box" data-testid={`cch-edit-${i}`}>✏ Edit</button> : null}
        <button type="button" onClick={() => onDelete(i)} data-tip="Delete this message" aria-label="Delete this message" data-testid={`cch-del-${i}`}>✕</button></i></li>)
      : !err ? <li className="cch-nil">Sees the desk. Learns what you 🧠 remember. Fixes only on your ✅.</li> : null}
    {busy ? <li className="cch-msg is-assistant is-wait is-fresh" role="status"><small>BRAIN</small><span><i /><i /><i /></span></li> : null}<li ref={end} aria-hidden className="cch-end" /></ol>;
});

// ⌨ the box owns its own text: a keystroke re-renders only this form, never the Brain, its log or the fixes (typing used to redraw everything)
const Composer = memo(forwardRef(function Composer({ mode, busy, upl, isOwner, focusSym, qOn, onQ, onSend, onDraw, onAttach }, ref) {
  const [txt, setTxt] = useState(''); const fileRef = useRef(null);
  useImperativeHandle(ref, () => ({ set: setTxt, get: () => txt }), [txt]);
  const send = e => { e?.preventDefault(); const v = txt; if (busy || (!String(v).trim() && mode !== 'case')) return; setTxt(''); onSend(v); };
  return <form className="cch-form" onSubmit={send} autoComplete="off">
    <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={e => { onAttach(e.target.files?.[0]); e.target.value = ''; }} data-testid="cch-file" />
    <button type="button" className="cch-ico cch-clip" onClick={() => fileRef.current?.click()} disabled={!isOwner || busy || upl || mode === 'case'} data-tip="Attach a picture (a chart, a screen): a cloud model that can see images reads it" aria-label="Attach a picture" data-testid="cch-attach">{upl ? '…' : '📎'}</button>
    <button type="button" className="cch-ico cch-clip" onClick={() => { const v = String(txt).trim(); if (v.length < 3) { toast.error('Describe the picture in the box first'); return; } setTxt(''); onDraw(v); }} disabled={!isOwner || busy || mode === 'case'} data-tip="Draw it: the text in the box becomes a picture (OpenRouter image model, a few cents)" aria-label="Generate a picture" data-testid="cch-draw">🎨</button>
    <input className="m-input" value={txt} onChange={e => setTxt(e.target.value)} disabled={!isOwner || busy} spellCheck={false} aria-label="Message to the model" data-testid="cch-input"
      placeholder={mode === 'case' ? `${focusSym ? `$${focusSym}` : 'the coin on the chart'} — ask about it (optional)` : mode === 'improve' ? 'what should the agents do better?' : mode === 'build' ? 'what should we build next?' : 'talk to the brain…'} />
    <button type="button" className="cch-ico cch-qt" onClick={onQ} aria-pressed={qOn} data-tip="One-tap prompts" aria-label="One-tap prompts" data-testid="cch-qt">⚡</button>
    <button type="submit" className="m-btn m-go cch-go" disabled={!isOwner || busy || (!String(txt).trim() && mode !== 'case')} data-testid="cch-send">{busy ? '…' : 'SEND IT'}</button></form>;
}));

export const AiChat = memo(function AiChat({ call, isOwner = true, focus, focusSym, variant = 'full', extras = [] }) {
  const [mode, setMode] = useState('chat'); const comp = useRef(null); const [busy, setBusyS] = useState(false); const [pop, setPop] = useState(false);
  const [threads, setThreads] = useState({}); const [build, setBuild] = useState(null); const [showDone, setShowDone] = useState(false);
  const [provs, setProvs] = useState([]); const [prov, setProvS] = useState(() => { try { return localStorage.getItem('feeless.brainProv') || 'auto'; } catch { return 'auto'; } });
  const setProv = v => { setProvS(v); try { localStorage.setItem('feeless.brainProv', v); } catch { /* private window */ } };
  const [saved, setSaved] = useState([]); const [sets, setSets] = useState(null); const [showSet, setShowSet] = useState(false); const [showSaved, setShowSaved] = useState(false); const [pane, setPane] = useState('talk');
  const [img, setImg] = useState(null); const [upl, setUpl] = useState(false); const [props, setProps] = useState({ pending: [], decided: [] }); const [last, setLast] = useState(null);
  const [brain, setBrain] = useState(null); const [learned, setLearned] = useState(null); const [err, setErr] = useState(null); const [local, setLocal] = useState(null);
  const [openP, setOpenP] = useState(null); const [fresh, setFresh] = useState({ mode: null, from: Infinity }); const [showQ, setShowQ] = useState(null);   // ⚡ one-tap prompts: open on an empty chat, folded once you are talking   // the mini cat keeps the fixes folded under one bar so the conversation keeps its room
  const hist = threads[mode] || [];
  // 🧠 while the model answers, the page's big endless layers rest (a local model shares the GPU Chrome draws with — that was the stutter on send)
  const setBusy = setBusyS;
  useEffect(() => { if (!busy) return undefined; holdFx(true); return () => holdFx(false); }, [busy]);   // 🧵 one thread per mode: chat · case · fix · build never mix
  const addMsg = (m, msg) => setThreads(t => ({ ...t, [m]: [...(t[m] || []), msg] }));
  const markFresh = m => setFresh({ mode: m, from: (threads[m] || []).length });   // what you send now + its answer animate in; nothing older
  const pickMode = k => { setFresh({ mode: null, from: Infinity }); setMode(k); };
  const take = useCallback(r => { if (!r) return; if (r.threads) setThreads(r.threads); else if (r.history) setThreads(t => ({ ...t, [r.mode || 'chat']: r.history })); if (r.build) setBuild(r.build); if (r.providers) setProvs(r.providers); if (r.saved) setSaved(r.saved); if (r.settings) setSets(r.settings); if (r.proposals) setProps(r.proposals); if (r.learned != null) setLearned(r.learned); if (r.brain) setBrain(r.brain); if (r.local) setLocal(r.local); }, []);
  useEffect(() => { let on = true; if (isOwner && typeof call === 'function') Promise.resolve().then(() => call('/admin/ai/chat')).then(r => { if (on) { take(r); setErr(null); } }).catch(x => { if (on) setErr(x.message); }); return () => { on = false; }; }, [call, isOwner, take]);
  useEffect(() => { if (!pop) return undefined; const k = e => { if (e.key === 'Escape') setPop(false); }; document.addEventListener('keydown', k); return () => document.removeEventListener('keydown', k); }, [pop]);
  const say = async (text, m = mode) => {
    const v = String(text || '').trim(); if (busy || (!v && m !== 'case')) return;
    const pic = m === 'case' ? null : img; setImg(null);
    setBusy(true); markFresh(m); addMsg(m, { role: 'user', ...(pic ? { meta: { img: pic } } : {}), text: m === 'case' ? `[case review] $${focusSym || focus || '?'} ${v}`.trim() : v });
    try { const r = await call('/admin/ai/chat', { method: 'POST', body: JSON.stringify({ text: v, mode: m, focus: focus || null, provider: prov, ...(pic ? { image: pic } : {}) }) });
      take(r); setLast(r); setErr(null);
      if (r.routed) pickMode(r.mode);   /* a chat message that asked for a change ran as 🛠 Fix agents */
      if (!r.ok) toast.error(r.why || 'no provider answered'); else if ((r.new || []).length) { setOpenP(true); toast.success(`🛠 ${r.new.length} fix${r.new.length === 1 ? '' : 'es'} waiting for your call`); }
    } catch (x) { toast.error(x.message); addMsg(m, { role: 'assistant', text: `⚠ ${x.message}` }); } finally { setBusy(false); }
  };
  const clear = useCallback(async index => { try { take(await call('/admin/ai/chat/clear', { method: 'POST', body: JSON.stringify(index == null ? { mode } : { index, mode }) })); if (index == null) setLast(null); } catch (x) { toast.error(x.message); } }, [call, mode, take]);
  const remember = useCallback(async text => { try { const r = await call('/admin/ai/chat/remember', { method: 'POST', body: JSON.stringify({ text: String(text).slice(0, 400) }) }); if (r.learned != null) setLearned(r.learned); toast.success('🧠 remembered — every fitting model read sees it now'); } catch (x) { toast.error(x.message); } }, [call]);
  // ✏ edit = rewind this thread to the message and put its text back in the box · ＋ new = a fresh thread for this mode
  const edit = useCallback(async (i, text) => { try { take(await call('/admin/ai/chat/clear', { method: 'POST', body: JSON.stringify({ mode, from: i }) })); comp.current?.set(text.replace(/^\[case review\] \S+ ?/, '')); } catch (x) { toast.error(x.message); } }, [call, mode, take]);
  const attach = async f => { if (!f) return; setUpl(true); try { const u = await uploadImage(f); const url = typeof u === 'string' ? u : u?.url; if (url) setImg(url); } catch (x) { toast.error(x.message); } finally { setUpl(false); } };
  const savedDo = async body => { try { const r = await call('/admin/ai/chat/saved', { method: 'POST', body: JSON.stringify(body) }); take(r); if (body.clearAll) setShowSaved(false); } catch (x) { toast.error(String(x?.message || x)); } };
  const openConvo = async id => { if (!id) return; try { const r = await call('/admin/ai/chat/open', { method: 'POST', body: JSON.stringify({ id }) }); take(r); if (r.mode) pickMode(r.mode); } catch (x) { toast.error(x.message); } };
  const saveSet = async patch => { setSets(v => ({ ...(v || {}), ...patch })); try { take(await call('/admin/ai/chat/settings', { method: 'POST', body: JSON.stringify(patch) })); } catch (x) { toast.error(x.message); } };
  // 🎨 the Brain DRAWS: the text in the box is the prompt → OpenRouter's image model → the picture lands in this thread (saved in our uploads)
  const draw = async v => {
    if (busy || String(v || '').length < 3) return;
    setBusy(true); markFresh(mode); addMsg(mode, { role: 'user', text: `🎨 ${v}` });
    try { const r = await call('/admin/ai/image', { method: 'POST', body: JSON.stringify({ prompt: v, mode }) }); take(r); toast.success(`🎨 drawn${r.usd ? ` · $${Number(r.usd).toFixed(3)}` : ''}`); }
    catch (x) { toast.error(x.message); addMsg(mode, { role: 'assistant', text: `⚠ ${x.message}` }); } finally { setBusy(false); }
  };
  const queueBuild = useCallback(async text => { try { const r = await call('/admin/ai/build', { method: 'POST', body: JSON.stringify({ text: String(text).slice(0, 600), title: String(text).replace(/\s+/g, ' ').slice(0, 60), src: `chat · ${mode}` }) }); setBuild(r.build); toast.success('📋 queued — say "build the queue" to Claude Code and it gets built'); } catch (x) { toast.error(x.message); } }, [call, mode]);
  const moveBuild = async (id, status) => { try { const r = await call('/admin/ai/build', { method: 'POST', body: JSON.stringify({ id, status }) }); setBuild(r.build); } catch (x) { toast.error(x.message); } };
  const decide = async (id, approve) => {
    if (busy) return; setBusy(true);
    try { const r = await call('/admin/ai/proposals/decide', { method: 'POST', body: JSON.stringify({ id, approve }) }); take(r);
      toast.success(approve ? `✅ applied — ${r.applied || 'done'}` : '✕ rejected — nothing changed'); } catch (x) { toast.error(x.message); } finally { setBusy(false); }
  };
  const mood = brainMood(busy, brain, last); const pend = (props.pending || []).length;
  const sideOpen = pop || (openP ?? (variant !== 'mini' && (mode === 'improve' || mode === 'build')));   // fixes fold outside 🛠 / 🧱 so the conversation keeps its room
  const body = <section className={`cch is-${pop ? 'pop' : variant} is-${mood.key} ${(showQ ?? !hist.length) ? 'is-q' : ''}`} data-testid="cch" data-mode={mode}>
    <header className="cch-head">
      <span className="cch-orb" aria-hidden="true"><i /><i /><b>🧠</b></span>
      <span className="cch-title"><b>BRAIN{local?.boost ? <i className="cch-boostchip" data-testid="cch-boostchip" data-tip={`Local boost: ${local.why || ''} · every ${local.every ?? '—'}s · ${local.leftH}h left`}>💻 BOOST</i> : null}</b><small data-testid="cch-mood" data-mood={mood.key}><em>{mood.word}</em>{mood.line}</small></span>
      <span className="cch-kpis"><u data-testid="cch-learned" data-tip="Lessons you taught the desk (🧠 Remember + 🎓 Teach): every fitting model read sees them">🎓 {learned ?? '—'}<small>LEARNED</small></u>
        <u className={pend ? 'is-hot' : ''} data-tip="Fixes the model proposed, waiting for your Approve / Reject">🛠 {pend}<small>YOUR CALL</small></u>
        <u data-testid="cch-bq" data-tip="Approved to build. The model in the app cannot write code: Claude Code builds these when you say: build the queue">📋 {build?.open ?? 0}<small>TO BUILD</small></u></span>
      <select className="cch-model" value={prov} onChange={e => setProv(e.target.value)} aria-label="Which model answers" data-testid="cch-model" data-tip="Which model answers: Auto = the normal order · Duet = Gemma answers, Qwen reads it and agrees or pushes back (both shown)">
        <option value="auto">🤖 Auto</option><option value="duet">🤝 Duet · Gemma + Qwen</option>{provs.map(p => <option key={p.key} value={p.key}>{p.state === 'ONLINE' ? '🟢' : p.state === 'UNTESTED' ? '⚪' : '🔴'} {p.label}{p.model ? ` · ${String(p.model).split('/').pop()}` : ''}</option>)}</select>
      {saved.length ? <span className="cch-svwrap"><button type="button" className={`cch-model cch-saved ${showSaved ? 'is-on' : ''}`} onClick={() => setShowSaved(v => !v)} aria-expanded={showSaved} data-testid="cch-saved" data-tip="Saved chats: open · rename · delete">🗂 {saved.length} saved</button>
        {showSaved ? <div className="cch-svpop" data-testid="cch-saved-list">{saved.map(c => <div key={c.id} className="cch-svrow">
          <button type="button" className="cch-svopen" onClick={() => { setShowSaved(false); openConvo(c.id); }} data-testid={`cch-sv-open-${c.id}`}><i>{(CHAT_MODES.find(m => m[0] === c.mode)?.[1] || '').split(' ')[0]}</i>{c.title}<small>{c.n} msgs</small></button>
          <button type="button" className="cch-svact" onClick={() => { const t = window.prompt('Rename this chat', c.title); if (t && t.trim()) savedDo({ id: c.id, title: t.trim() }); }} aria-label="Rename" data-testid={`cch-sv-ren-${c.id}`}>✏</button>
          <button type="button" className="cch-svact is-del" onClick={() => savedDo({ id: c.id, delete: true })} aria-label="Delete" data-testid={`cch-sv-del-${c.id}`}>🗑</button></div>)}
          <button type="button" className="cch-svclear" onClick={() => { if (window.confirm(`Delete all ${saved.length} saved chats?`)) savedDo({ clearAll: true }); }} data-testid="cch-sv-clear">🗑 clear all saved</button></div> : null}</span> : null}
      <button type="button" className={`cch-ico ${showSet ? 'is-on' : ''}`} onClick={() => setShowSet(v => !v)} aria-expanded={showSet} data-testid="cch-set" data-tip="Brain settings: how the model answers + what it may do on its own" aria-label="Brain settings">⚙</button>
      <button type="button" className="cch-ico cch-new" onClick={() => clear()} disabled={busy || !hist.length} data-testid="cch-clear" data-tip="New chat: a fresh thread for this mode" aria-label="New chat">＋</button>
      <button type="button" className="cch-ico" onClick={() => setPop(p => !p)} data-testid="cch-pop" data-tip={pop ? 'Close (Esc)' : 'Pop out — full window'} aria-label={pop ? 'Close the pop-out' : 'Pop out'}>{pop ? '✕' : '⤢'}</button>
    </header>
    <i className="cch-scan" aria-hidden="true" />
    {showSet ? <div className="cch-sets" data-testid="cch-sets">
      <p><small>🌡 HOW WILD</small>{[[0.1, 'exact'], [0.3, 'sharp'], [0.6, 'loose'], [0.9, 'wild']].map(([v, l]) => <button key={v} type="button" className={sets?.temp === v ? 'active' : ''} onClick={() => saveSet({ temp: v })} data-testid={`cch-temp-${v}`}>{l}</button>)}</p>
      <p><small>📏 ANSWER</small>{['short', 'normal', 'long'].map(v => <button key={v} type="button" className={sets?.len === v ? 'active' : ''} onClick={() => saveSet({ len: v })} data-testid={`cch-len-${v}`}>{v}</button>)}</p>
      <p><small>🤝 SMALL THINGS</small><button type="button" className={sets?.allowSmall ? 'active' : ''} onClick={() => saveSet({ allowSmall: !sets?.allowSmall })} aria-pressed={!!sets?.allowSmall} data-testid="cch-small">{sets?.allowSmall ? 'ON — lessons + build ideas apply by themselves' : 'OFF — every fix waits for your ✅'}</button></p>
      <p><small>💻 LOCAL BOOST</small><button type="button" className={local?.boost ? 'active' : ''} onClick={() => saveSet({ localBoost: !local?.boost })} aria-pressed={!!local?.boost} data-testid="cch-boost">{local?.boost ? `ON · ${local.leftH}h left` : 'OFF — tap for 24h'}</button></p>
      <LocalWatch w={local} />
      <p className="cch-setnote">Switches, rank weights and exit notches always wait for your ✅. Execution, limits and the wallet are never reachable.</p></div> : null}
    <div className="cch-shell">
    {isOwner ? <div className="cch-panes" role="tablist" aria-label="Brain sections">{[['talk', '💬 Talk'], ...extras.map(([k, l]) => [k, l]), ['play', '🧩 Code lab'], ['log', '📜 Activity']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={pane === k} className={pane === k ? 'active' : ''} onClick={() => setPane(k)} data-testid={`cch-pane-${k}`}>{l}</button>)}</div> : null}
    {extras.map(([k, , node]) => <div key={k} className="cch-extra" hidden={pane !== k} data-testid={`cch-extra-${k}`}>{node}</div>)}
    {isOwner && pane === 'play' ? <div className="cch-extra" data-testid="cch-extra-play"><AiPlayground call={call} prov={prov} /></div> : null}
    {isOwner && pane === 'log' ? <div className="cch-extra" data-testid="cch-extra-log"><AiActivity call={call} /></div> : null}
    <div className="cch-talkpane" hidden={pane !== 'talk'}><div className="cch-modes" data-testid="cch-modes" role="radiogroup" aria-label="Chat mode">{CHAT_MODES.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''}
      onClick={() => pickMode(k)} data-tip={tip} data-testid={`cch-mode-${k}`}><i aria-hidden="true">{l.split(' ')[0]}</i><span>{l.split(' ').slice(1).join(' ')}</span></button>)}</div>
    <div className="cch-main">
      <div className="cch-talk">
        <ChatLog hist={hist} err={err} busy={busy} from={fresh.mode === mode ? fresh.from : Infinity} onRemember={remember} onBuild={queueBuild} onEdit={edit} onDelete={clear} />
        <div className="cch-quick" data-testid="cch-quick">{(QUICK[mode] || []).map(([l, q]) => <button key={l} type="button" disabled={!isOwner || busy} onClick={() => say(q)} data-testid={`cch-chip-${l.split(' ')[1] || l}`}>{l}</button>)}</div>
        {last && metaLine(last) ? <p className="cch-meta" data-testid="cch-meta">{metaLine(last)}{(last.refused || []).length ? ` · ${last.refused.length} suggestion${last.refused.length === 1 ? '' : 's'} refused (execution / money is out of reach)` : ''}</p> : null}
        {img ? <p className="cch-att" data-testid="cch-att"><img src={img} alt="to send" /><span>picture attached · goes to a cloud model that can see images</span><button type="button" className="cch-ico" onClick={() => setImg(null)} aria-label="Remove the picture">✕</button></p> : null}
        <Composer ref={comp} mode={mode} busy={busy} upl={upl} isOwner={isOwner} focusSym={focusSym} qOn={!!(showQ ?? !hist.length)} onQ={() => setShowQ(!(showQ ?? !hist.length))}
          onSend={t => say(t)} onDraw={t => draw(t)} onAttach={attach} />
      </div>
      <div className="cch-side">
      {mode === 'build' && (build?.items || []).length ? <div className="cch-bqlist" data-testid="cch-bqlist"><p className="cch-bqh"><b>📋 BUILD QUEUE · {build.open} open</b><small>your ✅ = permission to build · Claude Code builds the queue when you open a session and say "build the queue" · ✅ SHIPPED when it is live</small></p>
        <ul>{build.items.slice(0, 6).map(b => <li key={b.id} className={`is-${b.status}`}><em>{b.status.toUpperCase()}</em><span data-tip={b.text}>{b.title}</span>
          {b.status === 'queued' ? <button type="button" className="cch-ico" onClick={() => moveBuild(b.id, 'dropped')} aria-label="Drop it" data-testid={`cch-bq-drop-${b.id}`}>✕</button> : null}</li>)}</ul></div> : null}
      {pend || (props.decided || []).length ? <div className={`cch-props ${sideOpen ? '' : 'is-shut'}`} data-testid="cch-props">
        <button type="button" className="cch-ptitle" onClick={() => setOpenP(!sideOpen)} aria-expanded={sideOpen} data-testid="cch-props-toggle"><b>🛠 FIXES — YOUR CALL{pend ? ` · ${pend}` : ''}</b><small>nothing changes until you approve · execution, limits and the wallet are out of reach</small><i aria-hidden>{sideOpen ? '▾' : '▸'}</i></button>
        <ul hidden={!sideOpen}>{(props.pending || []).map(p => <Proposal key={p.id} p={p} busy={busy} onDecide={decide} />)}
          {(props.decided || []).length ? <li><button type="button" className="cch-done" onClick={() => setShowDone(x => !x)} aria-expanded={showDone} data-testid="cch-done">{showDone ? '▾' : '▸'} {props.decided.length} decided</button></li> : null}
          {showDone ? (props.decided || []).slice(0, pop ? 8 : 4).map(p => <Proposal key={p.id} p={p} busy={busy} onDecide={decide} />) : null}</ul></div> : null}</div>
    </div></div>
    </div>
  </section>;
  return pop && typeof document !== 'undefined' ? <>{createPortal(<div className="cch-shade" data-testid="cch-shade" onMouseDown={e => { if (e.target === e.currentTarget) setPop(false); }}>{body}</div>, document.body)}
    <button type="button" className="cch-back" onClick={() => setPop(false)} data-testid="cch-popped">🧠 Brain is popped out — tap to bring it back</button></> : body;
});

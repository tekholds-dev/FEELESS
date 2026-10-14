// 🧠 THE BRAIN — direct LM chat + owner-approved agent updates (backend/ai_chat.py). One component, three places: the 🧠 AI tab in HQ ›
// Agents, the creator's mini cat (🧠 Brain tab) and a full-window pop-out (⤢). Its own state: an answer patches THIS panel only — never the
// agent hub, the chart, the stream or the P&L. It LEARNS on the owner's tap (🧠 Remember → a lesson every model case reads) and FIXES
// agents only on the owner's call (🛠 proposals → ✅ Approve). Modes: 💬 Chat · 🔎 Case review · 🛠 Fix agents.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
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

function Proposal({ p, busy, onDecide }) {
  return <li className={`cch-prop is-${p.status}`} data-testid={`cch-prop-${p.id}`}>
    <p className="cch-phead"><b>{String(p.agent).toUpperCase()}</b><em>{KIND[p.kind] || p.kind}</em><span>{p.key}</span>{p.status !== 'pending' ? <u>{p.status.toUpperCase()}</u> : null}</p>
    <p className="cch-diff"><span className="is-old"><small>NOW</small>{show(p.old)}</span><i aria-hidden>→</i><span className="is-new"><small>PROPOSED</small>{show(p.new)}</span></p>
    {p.reason ? <p className="cch-why"><small>WHY</small>{p.reason}</p> : null}
    {p.effect ? <p className="cch-why"><small>EFFECT</small>{p.effect}</p> : null}
    <p className="cch-why"><small>ROLLBACK</small>{p.rollback}</p>
    {p.applied ? <p className="cch-why is-applied"><small>APPLIED</small>{p.applied}</p> : null}
    {p.status === 'pending' ? <p className="cch-acts"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onDecide(p.id, true)} data-testid={`cch-approve-${p.id}`}>✅ Approve</button>
      <button type="button" className="m-btn" disabled={busy} onClick={() => onDecide(p.id, false)} data-testid={`cch-reject-${p.id}`}>✕ Reject</button></p> : null}
  </li>;
}

export function AiChat({ call, isOwner = true, focus, focusSym, variant = 'full' }) {
  const [mode, setMode] = useState('chat'); const [txt, setTxt] = useState(''); const [busy, setBusy] = useState(false); const [pop, setPop] = useState(false);
  const [threads, setThreads] = useState({}); const [build, setBuild] = useState(null); const [showDone, setShowDone] = useState(false); const [props, setProps] = useState({ pending: [], decided: [] }); const [last, setLast] = useState(null);
  const [brain, setBrain] = useState(null); const [learned, setLearned] = useState(null); const [err, setErr] = useState(null);
  const [openP, setOpenP] = useState(variant !== 'mini'); const [showQ, setShowQ] = useState(null);   // ⚡ one-tap prompts: open on an empty chat, folded once you are talking   // the mini cat keeps the fixes folded under one bar so the conversation keeps its room
  const end = useRef(null); const hist = threads[mode] || [];   // 🧵 one thread per mode: chat · case · fix · build never mix
  const addMsg = (m, msg) => setThreads(t => ({ ...t, [m]: [...(t[m] || []), msg] }));
  const take = useCallback(r => { if (!r) return; if (r.threads) setThreads(r.threads); else if (r.history) setThreads(t => ({ ...t, [r.mode || 'chat']: r.history })); if (r.build) setBuild(r.build); if (r.proposals) setProps(r.proposals); if (r.learned != null) setLearned(r.learned); if (r.brain) setBrain(r.brain); }, []);
  useEffect(() => { let on = true; if (isOwner && typeof call === 'function') Promise.resolve().then(() => call('/admin/ai/chat')).then(r => { if (on) { take(r); setErr(null); } }).catch(x => { if (on) setErr(x.message); }); return () => { on = false; }; }, [call, isOwner, take]);
  useEffect(() => { const el = end.current; if (el && el.parentNode) el.parentNode.scrollTop = el.parentNode.scrollHeight; }, [hist, busy, pop]);
  useEffect(() => { if (!pop) return undefined; const k = e => { if (e.key === 'Escape') setPop(false); }; document.addEventListener('keydown', k); return () => document.removeEventListener('keydown', k); }, [pop]);
  const say = async (text, m = mode) => {
    const v = String(text || '').trim(); if (busy || (!v && m !== 'case')) return;
    setBusy(true); addMsg(m, { role: 'user', text: m === 'case' ? `[case review] $${focusSym || focus || '?'} ${v}`.trim() : v }); setTxt('');
    try { const r = await call('/admin/ai/chat', { method: 'POST', body: JSON.stringify({ text: v, mode: m, focus: focus || null }) });
      take(r); setLast(r); setErr(null);
      if (r.routed) setMode(r.mode);   /* a chat message that asked for a change ran as 🛠 Fix agents */
      if (!r.ok) toast.error(r.why || 'no provider answered'); else if ((r.new || []).length) { setOpenP(true); toast.success(`🛠 ${r.new.length} fix${r.new.length === 1 ? '' : 'es'} waiting for your call`); }
    } catch (x) { toast.error(x.message); addMsg(m, { role: 'assistant', text: `⚠ ${x.message}` }); } finally { setBusy(false); }
  };
  const send = e => { e?.preventDefault(); say(txt); };
  const clear = async index => { try { take(await call('/admin/ai/chat/clear', { method: 'POST', body: JSON.stringify(index == null ? { mode } : { index, mode }) })); if (index == null) setLast(null); } catch (x) { toast.error(x.message); } };
  const remember = async text => { try { const r = await call('/admin/ai/chat/remember', { method: 'POST', body: JSON.stringify({ text: String(text).slice(0, 400) }) }); if (r.learned != null) setLearned(r.learned); toast.success('🧠 remembered — every fitting model read sees it now'); } catch (x) { toast.error(x.message); } };
  const queueBuild = async text => { try { const r = await call('/admin/ai/build', { method: 'POST', body: JSON.stringify({ text: String(text).slice(0, 600), title: String(text).replace(/\s+/g, ' ').slice(0, 60), src: `chat · ${mode}` }) }); setBuild(r.build); toast.success('📋 queued for the build — the next build session ships it'); } catch (x) { toast.error(x.message); } };
  const moveBuild = async (id, status) => { try { const r = await call('/admin/ai/build', { method: 'POST', body: JSON.stringify({ id, status }) }); setBuild(r.build); } catch (x) { toast.error(x.message); } };
  const decide = async (id, approve) => {
    if (busy) return; setBusy(true);
    try { const r = await call('/admin/ai/proposals/decide', { method: 'POST', body: JSON.stringify({ id, approve }) }); take(r);
      toast.success(approve ? `✅ applied — ${r.applied || 'done'}` : '✕ rejected — nothing changed'); } catch (x) { toast.error(x.message); } finally { setBusy(false); }
  };
  const mood = brainMood(busy, brain, last); const pend = (props.pending || []).length;
  const body = <section className={`cch is-${pop ? 'pop' : variant} is-${mood.key} ${(showQ ?? !hist.length) ? 'is-q' : ''}`} data-testid="cch" data-mode={mode}>
    <header className="cch-head">
      <span className="cch-orb" aria-hidden="true"><i /><i /><b>🧠</b></span>
      <span className="cch-title"><b>BRAIN</b><small data-testid="cch-mood" data-mood={mood.key}><em>{mood.word}</em>{mood.line}</small></span>
      <span className="cch-kpis"><u data-testid="cch-learned" data-tip="Lessons you taught the desk (🧠 Remember + 🎓 Teach): every fitting model read sees them">🎓 {learned ?? '—'}<small>LEARNED</small></u>
        <u className={pend ? 'is-hot' : ''} data-tip="Fixes the model proposed, waiting for your Approve / Reject">🛠 {pend}<small>YOUR CALL</small></u>
        <u data-testid="cch-bq" data-tip="Approved to build: queued for the next build session (nothing is coded by the model in the app)">📋 {build?.open ?? 0}<small>TO BUILD</small></u></span>
      <button type="button" className="cch-ico" onClick={() => clear()} disabled={busy || !hist.length} data-testid="cch-clear" data-tip="Delete the whole chat" aria-label="Clear chat">🗑</button>
      <button type="button" className="cch-ico" onClick={() => setPop(p => !p)} data-testid="cch-pop" data-tip={pop ? 'Close (Esc)' : 'Pop out — full window'} aria-label={pop ? 'Close the pop-out' : 'Pop out'}>{pop ? '✕' : '⤢'}</button>
    </header>
    <i className="cch-scan" aria-hidden="true" />
    <div className="cch-modes" role="radiogroup" aria-label="Chat mode">{CHAT_MODES.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''}
      onClick={() => setMode(k)} data-tip={tip} data-testid={`cch-mode-${k}`}><i aria-hidden="true">{l.split(' ')[0]}</i><span>{l.split(' ').slice(1).join(' ')}</span></button>)}</div>
    <div className="cch-main">
      <div className="cch-talk">
        <ol className="cch-log" data-testid="cch-log" aria-live="polite">
          {err && !hist.length ? <li className="cch-nil is-warn" data-testid="cch-err">⚠ {err}</li> : null}
          {hist.length ? hist.map((t, i) => <li key={`${i}-${t.text.slice(0, 12)}`} className={`cch-msg is-${t.role}`}><small>{t.role === 'user' ? 'YOU' : 'BRAIN'}</small><span>{t.text}</span>
            <i className="cch-mact">{t.role !== 'user' && t.text.length >= 8 && !t.text.startsWith('⚠') ? <><button type="button" onClick={() => remember(t.text)} data-tip="Remember this: it becomes a lesson every fitting model read sees" data-testid={`cch-rem-${i}`}>🧠 Remember</button>
                <button type="button" onClick={() => queueBuild(t.text)} data-tip="Build this: your tap is the permission — it joins the build queue the next build session ships" data-testid={`cch-build-${i}`}>🧱 Build this</button></> : null}
              <button type="button" onClick={() => clear(i)} data-tip="Delete this message" aria-label="Delete this message" data-testid={`cch-del-${i}`}>✕</button></i></li>)
            : !err ? <li className="cch-nil">Sees the desk. Learns what you 🧠 remember. Fixes only on your ✅.</li> : null}
          {busy ? <li className="cch-msg is-assistant is-wait" role="status"><small>BRAIN</small><span><i /><i /><i /></span></li> : null}<li ref={end} aria-hidden className="cch-end" /></ol>
        <div className="cch-quick" data-testid="cch-quick">{(QUICK[mode] || []).map(([l, q]) => <button key={l} type="button" disabled={!isOwner || busy} onClick={() => say(q)} data-testid={`cch-chip-${l.split(' ')[1] || l}`}>{l}</button>)}</div>
        {last && metaLine(last) ? <p className="cch-meta" data-testid="cch-meta">{metaLine(last)}{(last.refused || []).length ? ` · ${last.refused.length} suggestion${last.refused.length === 1 ? '' : 's'} refused (execution / money is out of reach)` : ''}</p> : null}
        <form className="cch-form" onSubmit={send} autoComplete="off">
          <input className="m-input" value={txt} onChange={e => setTxt(e.target.value)} disabled={!isOwner || busy} spellCheck={false} aria-label="Message to the model" data-testid="cch-input"
            placeholder={mode === 'case' ? `${focusSym ? `$${focusSym}` : 'the coin on the chart'} — ask about it (optional)` : mode === 'improve' ? 'what should the agents do better?' : mode === 'build' ? 'what should we build next?' : 'talk to the brain…'} />
          <button type="button" className="cch-ico cch-qt" onClick={() => setShowQ(!(showQ ?? !hist.length))} aria-pressed={!!(showQ ?? !hist.length)} data-tip="One-tap prompts" aria-label="One-tap prompts" data-testid="cch-qt">⚡</button>
          <button type="submit" className="m-btn m-go cch-go" disabled={!isOwner || busy || (!String(txt).trim() && mode !== 'case')} data-testid="cch-send">{busy ? '…' : 'SEND IT'}</button></form>
      </div>
      {mode === 'build' && (build?.items || []).length ? <div className="cch-bqlist" data-testid="cch-bqlist"><p className="cch-bqh"><b>📋 BUILD QUEUE · {build.open} open</b><small>your approval = permission · the next build session reads it first · the model never codes in the app</small></p>
        <ul>{build.items.slice(0, 6).map(b => <li key={b.id} className={`is-${b.status}`}><em>{b.status.toUpperCase()}</em><span data-tip={b.text}>{b.title}</span>
          {b.status === 'queued' ? <button type="button" className="cch-ico" onClick={() => moveBuild(b.id, 'dropped')} aria-label="Drop it" data-testid={`cch-bq-drop-${b.id}`}>✕</button> : null}</li>)}</ul></div> : null}
      {pend || (props.decided || []).length ? <div className={`cch-props ${openP || pop ? '' : 'is-shut'}`} data-testid="cch-props">
        <button type="button" className="cch-ptitle" onClick={() => setOpenP(o => !o)} aria-expanded={openP || pop} data-testid="cch-props-toggle"><b>🛠 FIXES — YOUR CALL{pend ? ` · ${pend}` : ''}</b><small>nothing changes until you approve · execution, limits and the wallet are out of reach</small><i aria-hidden>{openP || pop ? '▾' : '▸'}</i></button>
        <ul hidden={!(openP || pop)}>{(props.pending || []).map(p => <Proposal key={p.id} p={p} busy={busy} onDecide={decide} />)}
          {(props.decided || []).length ? <li><button type="button" className="cch-done" onClick={() => setShowDone(x => !x)} aria-expanded={showDone} data-testid="cch-done">{showDone ? '▾' : '▸'} {props.decided.length} decided</button></li> : null}
          {showDone ? (props.decided || []).slice(0, pop ? 8 : 4).map(p => <Proposal key={p.id} p={p} busy={busy} onDecide={decide} />) : null}</ul></div> : null}
    </div>
  </section>;
  return pop && typeof document !== 'undefined' ? <>{createPortal(<div className="cch-shade" data-testid="cch-shade" onMouseDown={e => { if (e.target === e.currentTarget) setPop(false); }}>{body}</div>, document.body)}
    <button type="button" className="cch-back" onClick={() => setPop(false)} data-testid="cch-popped">🧠 Brain is popped out — tap to bring it back</button></> : body;
}

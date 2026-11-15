import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import '../../styles/compVoice.css';

// 🗣 COMP VOICE chat (owner 2026-11-15 "yes dooo alll"): talk to COMP's own voice adapter, the degen web3 brain trained on this Mac
// (scripts/comp-voice.py). It runs as a local MLX server only while you use it (comp_voice.py): Wake loads the 9B (about half a minute),
// it sleeps by itself after 20 quiet minutes. Thinking is off, so answers come straight back. Owner only.
const ASKS = ['How do I spot a rug before it happens?', 'What is a sandwich attack?', 'How big should a bet be?', 'Roast my bags.'];
const when = t => (t ? new Date(t * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '');

export function CompVoice({ call }) {
  const [s, setS] = useState(null); const [err, setErr] = useState(''); const [q, setQ] = useState(''); const [busy, setBusy] = useState(''); const [ask, setAsk] = useState('');
  const callRef = useRef(call); callRef.current = call; const end = useRef(null);
  const state = !s ? 'wait' : s.listening ? 'up' : s.running ? 'waking' : 'asleep';
  const has = typeof call === 'function';
  useEffect(() => { if (!has) return undefined; let on = true;
    const read = () => callRef.current('/admin/model-lab/voice').then(x => { if (on) { setS(x); setErr(''); } }).catch(e => on && setErr(e.message));
    read(); const t = setInterval(() => { if (!document.hidden) read(); }, state === 'waking' ? 3000 : 15000);
    return () => { on = false; clearInterval(t); }; }, [state, has]);
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'nearest' }); }, [s?.chat?.length, ask]);
  const op = async (o, text = '') => { setBusy(o); setErr(''); if (o === 'ask') setAsk(text);
    try { setS(await callRef.current('/admin/model-lab/voice', { method: 'POST', body: JSON.stringify({ op: o, text }) })); if (o === 'ask') setQ(''); }
    catch (e) { setErr(e.message); } setBusy(''); setAsk(''); };
  const send = text => { const t = (text || '').trim(); if (t && !busy) op('ask', t); };
  const chat = s?.chat || [];
  if (!has) return null;
  return <section className="cv" data-testid="comp-voice" aria-label="COMP Voice">
    <header className="cv-h"><span className={`cv-dot is-${state}`} aria-hidden="true" /><b>COMP VOICE</b>
      <small data-testid="cv-state">{state === 'up' ? 'Awake · thinking off, answers come straight back' : state === 'waking' ? 'Waking up · loading the 9B, about half a minute' : state === 'asleep' ? `Asleep · wakes on this Mac only, sleeps after ${s?.idleMin || 20} quiet minutes` : 'Reading…'}</small>
      {s ? <em className="m-num" data-tip={`${s.base} with the voice adapter (${s.adapter || 'none yet'})`}>{s.rows} lessons{s.trainedAt ? ` · trained ${when(s.trainedAt)}` : ''}</em> : null}
      {state === 'asleep' ? <button type="button" className="m-btn m-go" disabled={!!busy || !s?.ready} onClick={() => op('start')} data-testid="cv-wake">{busy === 'start' ? '…' : 'Wake COMP'}</button>
        : state !== 'wait' ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => op('stop')} data-tip="Frees its memory now" data-testid="cv-sleep">Sleep</button> : null}
      {chat.length ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => op('clear')} aria-label="Clear the chat" data-testid="cv-clear">Clear</button> : null}</header>
    {err ? <p className="cv-err" role="alert">⚠ {err}</p> : null}
    {s && !s.ready ? <p className="cv-err">The voice is not trained yet. Run <code>.venv/bin/python scripts/comp-voice.py</code> on this Mac.</p> : null}
    <ol className="cv-log" data-testid="cv-log" aria-live="polite">
      {!chat.length && !ask ? <li className="cv-empty">Ask COMP anything about Solana, perps, prediction markets, scams to spot, or FEELESS itself. It will not pick coins for you, and it never helps anyone rug or drain.</li> : null}
      <AnimatePresence initial={false}>{chat.map((m, i) => <motion.li key={`${m.at}-${i}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`cv-msg is-${m.role}`} data-testid={`cv-${m.role}`}>
        <p>{m.content}</p>{m.role === 'assistant' && m.secs != null ? <small className="m-num">{m.secs}s{m.tokens ? ` · ${m.tokens} tokens` : ''}</small> : null}</motion.li>)}
        {ask ? <motion.li key="ask" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="cv-msg is-user"><p>{ask}</p></motion.li> : null}
        {ask ? <motion.li key="typing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="cv-msg is-assistant cv-typing" aria-label="COMP is answering"><i /><i /><i /></motion.li> : null}</AnimatePresence>
      <li ref={end} className="cv-end" aria-hidden="true" /></ol>
    {state === 'up' && !chat.length ? <div className="cv-asks">{ASKS.map(a => <button key={a} type="button" className="m-btn" disabled={!!busy} onClick={() => send(a)}>{a}</button>)}</div> : null}
    <form className="cv-q" onSubmit={e => { e.preventDefault(); send(q); }}>
      <input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder={state === 'up' ? 'Ask COMP…' : 'Wake COMP to ask'} disabled={state !== 'up'} maxLength={1200} aria-label="Ask COMP" data-testid="cv-q" />
      <button type="submit" className="m-btn m-go" disabled={state !== 'up' || !!busy || !q.trim()} data-testid="cv-send">{busy === 'ask' ? '…' : 'Ask'}</button></form>
  </section>;
}

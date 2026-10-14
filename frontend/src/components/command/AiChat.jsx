// 💬 DIRECT LM CHAT + OWNER-APPROVED AGENT UPDATES (backend/ai_chat.py). Its own state: an answer patches THIS panel only — it never touches
// the agent hub, the chart, the stream or the P&L. Three modes: CHAT (normal language) · CASE REVIEW (the structured read of the coin on
// the chart) · AGENT IMPROVEMENT (the model may PROPOSE; only APPROVE applies anything, and only the safe kinds).
import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

export const CHAT_MODES = [['chat', '💬 Chat', 'Talk to the model in normal language — it sees the desk\'s current state'],
  ['case', '🔎 Case review', 'The structured read of the coin on the chart (validated JSON → shown as a verdict)'],
  ['improve', '🛠 Agent improvement', 'The model may PROPOSE agent changes. Nothing changes until you approve each one.']];
const KIND = { cfg: '⚙ switch', lesson: '🎓 lesson', weight: '⚖ rank weight', tune: '🎚 exit notch → shadow', idea: '💡 idea' };
const show = v => (v === true ? 'ON' : v === false ? 'OFF' : v == null ? '—' : String(v));

// pure: the meta line under an answer (provider · model · latency · tokens)
export const metaLine = r => [r?.provider, r?.model, r?.ms != null ? `${(r.ms / 1000).toFixed(1)}s` : null, r?.tokens ? `${r.tokens.in}→${r.tokens.out} tok` : null].filter(Boolean).join(' · ');

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

export function AiChat({ call, isOwner = true, focus, focusSym }) {
  const [mode, setMode] = useState('chat'); const [txt, setTxt] = useState(''); const [busy, setBusy] = useState(false);
  const [hist, setHist] = useState([]); const [props, setProps] = useState({ pending: [], decided: [] }); const [last, setLast] = useState(null);
  const end = useRef(null);
  useEffect(() => { let on = true; if (isOwner && typeof call === 'function') Promise.resolve().then(() => call('/admin/ai/chat')).then(r => { if (on && r) { setHist(r.history || []); setProps(r.proposals || { pending: [], decided: [] }); } }).catch(() => {}); return () => { on = false; }; }, [call, isOwner]);
  useEffect(() => { const el = end.current; if (el && el.parentNode) el.parentNode.scrollTop = el.parentNode.scrollHeight; }, [hist, busy]);
  const send = async e => {
    e?.preventDefault(); const v = String(txt || '').trim(); if (busy || (!v && mode !== 'case')) return;
    setBusy(true); setHist(h => [...h, { role: 'user', text: mode === 'case' ? `[case review] $${focusSym || focus || '?'} ${v}`.trim() : v }]); setTxt('');
    try { const r = await call('/admin/ai/chat', { method: 'POST', body: JSON.stringify({ text: v, mode, focus: focus || null }) });
      setHist(r.history || []); setProps(r.proposals || props); setLast(r);
      if (!r.ok) toast.error(r.why || 'no provider answered'); else if ((r.new || []).length) toast.success(`🛠 ${r.new.length} proposal${r.new.length === 1 ? '' : 's'} waiting for your review`);
    } catch (x) { toast.error(x.message); setHist(h => [...h, { role: 'assistant', text: `⚠ ${x.message}` }]); } finally { setBusy(false); }
  };
  const clear = async () => { try { const r = await call('/admin/ai/chat/clear', { method: 'POST', body: '{}' }); setHist(r.history || []); setLast(null); } catch (x) { toast.error(x.message); } };
  const decide = async (id, approve) => {
    if (busy) return; setBusy(true);
    try { const r = await call('/admin/ai/proposals/decide', { method: 'POST', body: JSON.stringify({ id, approve }) }); setProps(r.proposals || props);
      toast.success(approve ? `✅ applied — ${r.applied || 'done'}` : '✕ rejected — nothing changed'); } catch (x) { toast.error(x.message); } finally { setBusy(false); }
  };
  return <section className="cch" data-testid="cch">
    <header className="cch-head"><b>💬 AI / LM CHAT</b>
      <span className="m-seg cch-modes" role="radiogroup" aria-label="Chat mode">{CHAT_MODES.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''}
        onClick={() => setMode(k)} data-tip={tip} data-testid={`cch-mode-${k}`}>{l}</button>)}</span>
      <button type="button" className="m-btn cch-clear" onClick={clear} disabled={busy || !hist.length} data-testid="cch-clear">Clear chat</button></header>
    <ol className="cch-log" data-testid="cch-log" aria-live="polite">
      {hist.length ? hist.map((t, i) => <li key={i} className={`cch-msg is-${t.role}`}><small>{t.role === 'user' ? 'YOU' : 'MODEL'}</small><span>{t.text}</span></li>)
        : <li className="cch-nil">Ask it anything about the desk — it sees the ten agents, the seats, the coin on the chart, execution health and the last real results. It can suggest; only you can change.</li>}
      {busy ? <li className="cch-msg is-assistant is-wait" role="status"><small>MODEL</small><span><i /><i /><i /></span></li> : null}<li ref={end} aria-hidden className="cch-end" /></ol>
    {last && metaLine(last) ? <p className="cch-meta" data-testid="cch-meta">{metaLine(last)}{(last.refused || []).length ? ` · ${last.refused.length} suggestion${last.refused.length === 1 ? '' : 's'} refused (execution / money is out of reach)` : ''}</p> : null}
    <form className="cch-form" onSubmit={send} autoComplete="off">
      <input className="m-input" value={txt} onChange={e => setTxt(e.target.value)} disabled={!isOwner || busy} spellCheck={false} aria-label="Message to the model" data-testid="cch-input"
        placeholder={mode === 'case' ? `case review of ${focusSym ? `$${focusSym}` : 'the coin on the chart'} — add a question (optional)` : mode === 'improve' ? 'what should the agents do better?' : 'talk to the model…'} />
      <button type="submit" className="m-btn m-go" disabled={!isOwner || busy || (!String(txt).trim() && mode !== 'case')} data-testid="cch-send">{busy ? 'Thinking…' : 'Send'}</button></form>
    {(props.pending || []).length || (props.decided || []).length ? <div className="cch-props" data-testid="cch-props">
      <p className="cch-ptitle"><b>🛠 PROPOSALS</b><small>{(props.pending || []).length} waiting · nothing changes until you approve · execution, limits and the wallet are out of reach</small></p>
      <ul>{(props.pending || []).map(p => <Proposal key={p.id} p={p} busy={busy} onDecide={decide} />)}{(props.decided || []).slice(0, 4).map(p => <Proposal key={p.id} p={p} busy={busy} onDecide={decide} />)}</ul></div> : null}
  </section>;
}

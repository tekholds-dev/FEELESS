import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { hubApply } from '../../lib/agentHub';
import { TAPE_AGENT } from '../../lib/cockpit';
import { STANCE_TONE, agreeOf, aiRows, deltaFill, agreeStats } from '../../lib/aiRead';
import { AG } from './agentWords';
import { vitalRows, hasVitals, TIMING_TONE } from '../../lib/cockpitControls';
import '../../styles/cockpitAi.css';
import '../../styles/agentControls.css';

// 🧠 THE MODEL'S DECISIONS (HQ › Agents › decision panel › 🧠 AI; owner, 2026-10-12: "I wanna see the LM model's decisions as well — fix
// the AI input"). Every answer the local model (or the next provider) gave, newest first: which desk asked, the coin, its STANCE, how
// far it moved its confidence, its own sentence — beside what the KERNEL decided at that moment (AGREES / DISAGREES). And one input:
// ASK the model about any coin on the desk, now. Advisory only: nothing shown here changes a rank, a size, READY, an order or a stop.
const ago = at => { if (!at) return '—'; const s = Math.max(0, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${(s / 3600).toFixed(1)}h`; };
export const ASK_ROLES = [['owner', '👤 Plain read', 'What the evidence shows, in plain words'], ['sherlock', '🔍 Sherlock', 'Research: what is supported, what is still unknown'], ['devil', '⚖ Devil', 'The strongest reason this could be wrong']];

function Delta({ d }) {
  const f = deltaFill(d);
  return <span className="cai-delta" data-tip={`confidence ${Number(d) >= 0 ? '+' : ''}${Number(d || 0).toFixed(2)} (advisory — shown, never applied to the rank)`}>
    <i className={f >= 0 ? 'is-up' : 'is-dn'} style={{ transform: `scaleX(${Math.abs(f)})` }} /><u /></span>;
}

// 🫀 THE MODEL'S VITALS (owner, 2026-10-12: "pull more vital info from the AI provider"): rug risk (high = bad) · narrative · crowd (people vs
// bots) · momentum as meters, where the coin is in its run, and the ≤ 4 facts the model says decide it. Advisory: a vital weighs on the
// rank only once its own judged record proves it (the 🎓 box below).
export function AiVitals({ a, mini, testid }) {
  if (!hasVitals(a)) return null;
  const rows = vitalRows(a);
  return <div className={`avt ${mini ? 'is-mini' : ''}`} data-testid={testid}>
    {rows.length ? <ul className="avt-meters">{rows.map(r => <li key={r.k} className={r.tone} data-tip={`${r.label} ${r.v}/100 — the model's read from this case${r.k === 'rug' ? ' (high = more likely a pull or dump)' : ''}`}>
      <small>{r.label}</small><span className="avt-bar"><i style={{ transform: `scaleX(${r.fill})` }} /></span><b>{r.v}</b></li>)}</ul> : null}
    {a.timing || (a.flags || []).length ? <p className="avt-foot">{a.timing ? <em className={`avt-time ${TIMING_TONE[a.timing] || ''}`}>⏱ {a.timing}</em> : null}
      {mini ? null : (a.flags || []).map((f, i) => <span key={i} className="avt-flag">{f}</span>)}</p> : null}
  </div>;
}
// the review queue's cell: the stance + the rug meter + the timing word, in one line
export function AiCell({ a }) {
  if (!a?.stance) return <small className="avt-none">—</small>;
  const rug = vitalRows(a).find(r => r.k === 'rug');
  return <span className="avt-cell" data-tip={`${a.stance}${a.timing ? ` · ${a.timing}` : ''}${rug ? ` · rug ${rug.v}/100` : ''} — ${a.summary || ''}`}>
    <em className={`cai-stance ${STANCE_TONE[a.stance] || 'is-hold'}`}>{a.stance}</em>
    {rug ? <span className={`avt-rug ${rug.tone}`}><i style={{ transform: `scaleX(${rug.fill})` }} /></span> : null}
    {a.timing ? <small className={`avt-time ${TIMING_TONE[a.timing] || ''}`}>{a.timing}</small> : null}</span>;
}

export function AiRow({ r, onPick }) {
  const [ic, nm] = TAPE_AGENT[r.role] || (r.role === 'owner' ? ['👤', 'You asked'] : ['🧠', r.role]); const ag = agreeOf(r);
  return <li className={`cai-row ${r.asked ? 'is-asked' : ''}`} style={{ '--ag': AG[r.role] || '#c9b8ff' }} data-testid={`cai-row-${r.at}`}>
    <button type="button" onClick={() => r.mint && onPick?.(r.mint)} disabled={!r.mint}>
      <span className="cai-top"><b className="cai-who">{ic} {nm}</b><b className="cai-sym">{r.symbol ? `$${r.symbol}` : '—'}</b>
        {r.stance ? <em className={`cai-stance ${STANCE_TONE[r.stance] || 'is-hold'}`}>{r.stance}</em> : <em className="cai-stance is-off">NO ANSWER</em>}
        {r.stance ? <Delta d={r.delta} /> : null}<small className="cai-age">{ago(r.at)} ago</small></span>
      <span className="cai-say">{r.summary || r.why || '—'}</span>
      {hasVitals(r) ? <AiVitals a={r} mini /> : null}
      <span className="cai-foot"><i className="cai-src">{r.label || r.source || 'AI'}</i>{r.ms != null ? <small>{r.ms >= 1000 ? `${(r.ms / 1000).toFixed(1)}s` : `${r.ms}ms`}</small> : null}
        {r.kernel ? <small>kernel: <b>{String(r.kernel).replace('_', ' ')}</b>{r.trigger ? ` · ⏱ ${r.trigger}` : ''}</small> : null}
        {ag ? <em className={`cai-agree ${ag.cls}`}>{ag.word}</em> : null}{r.deep ? <small className="cai-deep" data-tip="the model asked for a deeper review of this coin">deep review</small> : null}</span>
    </button></li>;
}

export function AiPane({ ai, call, isOwner = true, focus, focusSym, onPick, onProviders }) {
  const [txt, setTxt] = useState(focus || ''); const [role, setRole] = useState('owner'); const [busy, setBusy] = useState(false); const [scope, setScope] = useState('all'); const [ans, setAns] = useState(null);
  const [typed, setTyped] = useState(false);
  useEffect(() => { if (!typed) setTxt(focus || ''); }, [focus, typed]);   // follows the coin on the chart until the owner types their own
  const live = (ai?.providers || []).find(p => p.key === ai?.active); const st = agreeStats(ai);
  const rows = aiRows(ai, { mint: scope === 'coin' ? focus : null });
  const ask = async e => {
    e?.preventDefault(); const v = String(txt || '').trim(); if (!v || busy) return;
    setBusy(true); setAns(null);
    try { const r = await call('/admin/ai/ask', { method: 'POST', body: JSON.stringify({ input: v, role }) });
      if (r?.ai) hubApply({ kind: 'ai_update', data: r.ai });
      setAns(r); if (r?.ok) toast.success(`🧠 ${r.answer?.label || 'model'} answered`); else toast.error(r?.answer?.why || 'no provider answered');
    } catch (x) { toast.error(x.message); setAns({ ok: false, answer: { why: x.message } }); } finally { setBusy(false); }
  };
  return <div className="cai" data-testid="ack-pane-ai">
    <div className="cai-head"><span className={`cai-dot ${live ? 'is-on' : ''}`} aria-hidden />
      <b>{live ? live.label : 'NO MODEL ONLINE'}</b><small>{ai?.model || (live ? '' : 'the kernel runs deterministic only')}</small>
      <small className="cai-stat">{ai?.totals ? `${ai.totals.answered} answers · ${ai.totals.cached} cached` : ''}{live?.lastMs != null ? ` · ${live.lastMs}ms` : ''}{ai?.lastAt ? ` · last round ${ago(ai.lastAt)} ago` : ''}</small>
      <button type="button" className="m-btn" onClick={onProviders} data-testid="cai-providers">⚙ providers</button></div>
    {st.n ? <div className="cai-agreebar" data-tip="How often the model's stance matched what the kernel itself decided (the kernel never reads the model)"><small>MODEL vs KERNEL</small>
      <span className="cai-meter"><i style={{ transform: `scaleX(${(st.pct || 0) / 100})` }} /></span><b>{st.pct}% agree</b><small>{st.agree} of {st.n}</small></div> : null}
    {ai?.learn ? <div className={`cai-learn is-${String(ai.learn.state).toLowerCase().replace(/\s+/g, '-')}`} data-testid="cai-learn"
      data-tip={`Every stance the model gives is noted at that price and judged ${ai.learn.judgeMin} min later. A stance moves the agents' ranking (±10% at most) only once ${ai.learn.minN} of its calls are judged AND its coins really did better / worse than the model's other calls.`}>
      <span className="cai-lhead"><b>🎓 AGENTS LEARNING FROM THE MODEL</b><em>{ai.learn.state}</em></span><small>{ai.learn.why}{ai.learn.open ? ` · ${ai.learn.open} call${ai.learn.open === 1 ? '' : 's'} waiting for their ${ai.learn.judgeMin} min` : ''}</small>
      {(ai.learn.rows || []).length ? <ul className="cai-lrows">{ai.learn.rows.slice(0, 6).map(r => <li key={r.stance} className={r.factor > 1 ? 'is-up' : r.factor < 1 ? 'is-dn' : ''}>
        <em className={`cai-stance ${STANCE_TONE[r.stance] || 'is-hold'}`}>{r.stance}</em>
        <span className="cai-meter"><i style={{ transform: `scaleX(${Math.min(1, r.n / ai.learn.minN)})` }} /></span>
        <small>{r.n} judged · typical <b className={r.med > 0 ? 'm-pos' : r.med < 0 ? 'm-neg' : ''}>{r.med > 0 ? '+' : ''}{r.med}%</b> · {r.up}% up</small>
        <u>{r.factor !== 1 ? `rank ×${r.factor}` : r.proven ? 'no edge' : 'learning'}</u></li>)}</ul> : null}
      {(ai.learn.vitals || []).some(r => r.n) ? <ul className="cai-lrows avt-lrows" data-testid="cai-learn-vitals">{ai.learn.vitals.filter(r => r.n).map(r => <li key={r.bucket} className={r.factor > 1 ? 'is-up' : r.factor < 1 ? 'is-dn' : ''}>
        <em className="avt-bucket">{r.label}</em><span className="cai-meter"><i style={{ transform: `scaleX(${Math.min(1, r.n / ai.learn.minN)})` }} /></span>
        <small>{r.n} judged · typical <b className={r.med > 0 ? 'm-pos' : r.med < 0 ? 'm-neg' : ''}>{r.med > 0 ? '+' : ''}{r.med}%</b> · {r.up}% up</small>
        <u>{r.factor !== 1 ? `rank ×${r.factor}` : r.proven ? 'no edge' : 'learning'}</u></li>)}</ul> : null}</div> : null}
    <form className="cai-ask" onSubmit={ask} autoComplete="off" data-testid="cai-ask">
      <label className="cai-lab" htmlFor="cai-ask-in">🧠 ASK THE MODEL{focusSym && !typed ? <small> · ${focusSym} (the coin on the chart)</small> : null}</label>
      <div className="cai-askrow"><input id="cai-ask-in" className="m-input" value={txt} onChange={e => { setTxt(e.target.value); setTyped(true); }} placeholder="coin on the desk — CA / mint or a pump.fun · dexscreener link" aria-label="Coin to ask the model about"
        disabled={!isOwner || busy} spellCheck={false} data-testid="cai-ask-input" />
        {typed && focus ? <button type="button" className="m-btn" onClick={() => { setTyped(false); setTxt(focus); }} data-tip="Back to the coin on the chart" data-testid="cai-ask-reset">↺</button> : null}
        <button type="submit" className="m-btn m-go" disabled={!isOwner || busy || !String(txt || '').trim()} data-testid="cai-ask-go">{busy ? 'Thinking…' : 'Ask'}</button></div>
      <div className="m-seg cai-roles" role="group" aria-label="Who asks">{ASK_ROLES.map(([k, l, tip]) => <button key={k} type="button" className={role === k ? 'active' : ''} onClick={() => setRole(k)} data-tip={tip} data-testid={`cai-role-${k}`}>{l}</button>)}</div>
      {busy ? <p className="cai-think" role="status"><i /><i /><i />the model is reading the kernel's case…</p> : null}
      {ans && !busy ? <p className={`cai-ans ${ans.ok ? '' : 'is-warn'}`} data-testid="cai-answer">{ans.ok ? <><em className={`cai-stance ${STANCE_TONE[ans.answer?.advice?.stance] || 'is-hold'}`}>{ans.answer?.advice?.stance}</em>{ans.symbol ? <b>${ans.symbol}</b> : null} {ans.answer?.advice?.summary}</> : (ans.answer?.why || 'no provider answered — deterministic only')}</p> : null}
      <small className="cai-never">advisory only — the model never buys, sizes, blocks or sells; the kernel never waits on it</small></form>
    <div className="cai-loghead"><b>DECISIONS</b><span className="m-seg" role="group" aria-label="Which decisions">
      <button type="button" className={scope === 'all' ? 'active' : ''} onClick={() => setScope('all')} data-testid="cai-scope-all">All {(ai?.log || []).length}</button>
      <button type="button" className={scope === 'coin' ? 'active' : ''} onClick={() => setScope('coin')} disabled={!focus} data-testid="cai-scope-coin">{focusSym ? `$${focusSym}` : 'This coin'}</button></span></div>
    {rows.length ? <ol className="cai-log" data-testid="cai-log">{rows.map(r => <AiRow key={`${r.at}-${r.role}-${r.mint}`} r={r} onPick={onPick} />)}</ol>
      : <p className="ack-nil" data-testid="cai-empty">{scope === 'coin' ? 'The model has not been asked about this coin yet — Ask above.' : live ? 'No model decision yet — the desk asks one about every 15s when a case is worth it (a conflicted coin, the top contender, a closed real trade).' : 'No model is online. Start LM Studio (or add a key under ⚙ providers) and its decisions appear here.'}</p>}
  </div>;
}

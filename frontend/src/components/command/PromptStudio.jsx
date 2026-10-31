import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/promptStudio.css';
import { avatarOf } from '../../lib/aiAvatars';

// 🎭 PROMPT STUDIO (owner, 2026-10-22: "context prompts and suggested prompts for all models — 3 auto-generated ELITE SUPREME PERSONAS and DEGEN
// TRENCH prompts for each model … auto-tuned to fix the mindset, quick but patient when in profit"). Brain › 🎭 Prompts: pick G4 · OSSY →
// what it reads (the context window, layer by layer), how it is doing (its real record + what the record says is wrong), and four sets written
// from that record. Apply = every call that model gets carries the set (LM Studio / llamafile); the desk's rules and money checks never change.
const SET_ART = {
  elite: <svg viewBox="0 0 48 48" aria-hidden="true"><defs><linearGradient id="pstG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe08a" /><stop offset="1" stopColor="#c8901e" /></linearGradient></defs>
    <path d="M8 34 L6 14 L17 23 L24 9 L31 23 L42 14 L40 34 Z" fill="url(#pstG)" stroke="#fff3c4" strokeWidth="1.2" /><rect x="8" y="35" width="32" height="5" rx="2" fill="#c8901e" />
    <circle cx="24" cy="27" r="3" fill="#15d16a" /><circle cx="15" cy="29" r="2" fill="#ff8fa3" /><circle cx="33" cy="29" r="2" fill="#5fd4ff" /></svg>,
  degen: <svg viewBox="0 0 48 48" aria-hidden="true"><g stroke="#45e486" strokeWidth="2" strokeLinecap="round">{[0, 45, 90, 135, 180, 225, 270, 315].map(a => <line key={a} x1="24" y1="24" x2={24 + 19 * Math.cos(a * Math.PI / 180)} y2={24 + 19 * Math.sin(a * Math.PI / 180)} />)}</g>
    <circle cx="24" cy="24" r="12" fill="#0b3a1f" stroke="#15d16a" strokeWidth="2" /><path d="M17 28 L21 23 L25 26 L31 18" fill="none" stroke="#b6ffd2" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /><circle cx="31" cy="18" r="2" fill="#fff" /></svg>,
  progressive: <svg viewBox="0 0 48 48" aria-hidden="true"><rect x="7" y="30" width="7" height="11" rx="1.5" fill="#1d6b8a" /><rect x="17" y="23" width="7" height="18" rx="1.5" fill="#2aa7c9" />
    <rect x="27" y="15" width="7" height="26" rx="1.5" fill="#45e486" /><path d="M8 24 L20 14 L28 18 L41 7" fill="none" stroke="#b6ffd2" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /><path d="M35 7 L41 7 L41 13" fill="none" stroke="#b6ffd2" strokeWidth="2.4" strokeLinecap="round" /></svg>,
  tuned: <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 32 A17 17 0 0 1 40 32" fill="none" stroke="#3b2a66" strokeWidth="6" strokeLinecap="round" /><path d="M8 32 A17 17 0 0 1 30 16.5" fill="none" stroke="#b79bff" strokeWidth="6" strokeLinecap="round" />
    <line className="pst-needle" x1="24" y1="32" x2="33" y2="19" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" /><circle cx="24" cy="32" r="3.5" fill="#b79bff" /><path d="M14 40 h20" stroke="#6a4fc9" strokeWidth="2" strokeLinecap="round" /></svg>,
};
const LAYER_TIP = { job: 'The prompt its main job sends — the seat rules', identity: 'Who it is, sent on chat calls',
  brain: 'The owner brain prompt its background coin reads carry', studio: 'The mindset you applied here — appended to every call it gets' };
const sgn = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const ago = at => { const s = Math.max(0, Math.round(Date.now() / 1000 - (Number(at) || 0))); return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

// pure: the context window as segments — each layer's share of the loaded context (an unknown window is drawn against the prompt itself)
export function windowOf(m) {
  const layers = (m?.layers || []).filter(l => l.tok > 0);
  const used = layers.reduce((a, l) => a + l.tok, 0);
  const total = Math.max(used, Number(m?.ctx) || 0) || 1;
  return { used, total, known: !!m?.ctx, pct: Math.round((100 * used) / total), segs: layers.map(l => ({ k: l.k, label: l.label, tok: l.tok, w: l.tok / total })) };
}

function Dials({ d, dials }) {
  return <span className="pst-dials">{(dials || ['speed', 'patience', 'risk', 'discipline']).map(k => <span key={k} data-tip={`${k}: ${d?.[k] ?? '—'} / 100`}>
    <em>{k.toUpperCase()}</em><i><b style={{ transform: `scaleX(${Math.max(0.04, (d?.[k] || 0) / 100)})` }} /></i><small key={d?.[k]}>{d?.[k] ?? '—'}</small></span>)}</span>;
}

function SetCard({ s, m, i, active, busy, onApply, onRevert, dials }) {
  const [edit, setEdit] = useState(false); const [txt, setTxt] = useState(s.text); const [open, setOpen] = useState(false);
  useEffect(() => { if (!edit) setTxt(s.text); }, [s.text, edit]);
  const max = m.key === 'win' ? 320 : 900;
  return <article className={`pst-set k-${s.set}${active ? ' is-on' : ''}`} style={{ '--i': i }} data-testid={`pst-set-${s.set}`}>
    <header><span className="pst-art">{SET_ART[s.set]}</span><span><b>{s.label}</b><small>{s.tag}</small></span>
      {active ? <em className="pst-on" data-tip={`Applied ${ago(active.at)} ago${active.edited ? ' (your edit)' : ''}`}>ACTIVE</em> : null}</header>
    <Dials d={s.dials} dials={dials} />
    {edit ? <label className="pst-edit"><textarea className="m-input" value={txt} maxLength={max} onChange={e => setTxt(e.target.value)} rows={6} data-testid={`pst-edit-${s.set}`} />
      <small className={txt.length > max * 0.9 ? 'is-hot' : ''}>{txt.length} / {max}</small></label>
      : <p className={`pst-text${open ? ' is-open' : ''}`} data-testid={`pst-text-${s.set}`}>{s.text}</p>}
    <p className="pst-why">{s.why}</p>
    {active ? <p className={`pst-proof ${active.seen?.ok ? 'is-live' : 'is-wait'}`} data-testid="pst-proof"
      data-tip={m.key === 'fee' ? "FEELESS sends this mindset inside the system prompt of every buy / sell call her brains make" : "FEELESS sends this mindset inside the system prompt of EVERY call it makes to this model (LM Studio / llamafile) — a model reload never loses it; LM Studio's own preset box is only for its own chat window"}>
      {active.seen?.ok ? <><b>✓ IN USE</b><span>last call {ago(active.seen.at)} ago carried it</span></> : active.seen ? <><b>⚠ SENT</b><span>its last call {ago(active.seen.at)} ago failed — the next one carries it again</span></>
        : <><b>⏳ APPLIED</b><span>rides {m.name}'s next call</span></>}</p> : null}
    {active ? <LmsMirror m={m} /> : null}
    {active ? <p className="pst-since" data-testid="pst-since" data-tip="Trades that opened after you applied this set">
      <b>SINCE APPLIED</b><span>{active.since?.n ? `${active.since.n} trades · ${active.since.wonPct}% won · ${sgn(active.since.avgPct)} avg` : 'no trade closed yet'}</span></p> : null}
    <footer>
      {edit ? <button type="button" className="m-btn m-go" disabled={busy || !txt.trim()} onClick={() => { onApply(s.set, txt.trim() !== s.text ? txt.trim() : null); setEdit(false); }}
        data-tip="Apply your edited version to this model" data-testid={`pst-apply-edit-${s.set}`}>Apply edit</button>
        : <button type="button" className="m-btn m-go" disabled={busy || (active && !active.edited)} onClick={() => onApply(s.set, null)}
          data-tip={`Every call ${m.name} gets carries this mindset from the next call on`} data-testid={`pst-apply-${s.set}`}>{active ? 'Applied' : `Apply to ${m.name}`}</button>}
      <button type="button" className="m-btn" onClick={() => setEdit(!edit)} data-tip="Tweak the words before you apply" data-testid={`pst-edit-btn-${s.set}`}>{edit ? 'Cancel' : '✎ Edit'}</button>
      {!edit ? <button type="button" className="m-btn" onClick={() => setOpen(!open)} aria-expanded={open} data-tip="Read the whole prompt">{open ? 'Less' : 'Full prompt'}</button> : null}
      {active ? <button type="button" className="m-btn pst-revert" disabled={busy} onClick={onRevert} data-tip={`Back to ${m.name}'s plain prompt`} data-testid="pst-revert">Revert</button> : null}
    </footer>
  </article>;
}

// 📌 WHERE THE MINDSET SHOWS IN LM STUDIO (owner, 2026-10-23: "I don't see the Prompt Studio updates in LM Studio's System Prompt box"): LM
// Studio's own preset box only feeds its chat window. OSSY (this Mac): FEELESS writes what it really sends into the preset "FEELESS LIVE · OSSY" —
// pick it in LM Studio and the box shows the live brain. G4 (the desktop): copy the exact prompt and paste it into its preset there.
export function lmsPrompt(m) {
  return (m?.layers || []).filter(l => l.k === 'job' || l.k === 'studio').map(l => l.text).filter(Boolean).join('\n\n');
}
function LmsMirror({ m }) {
  if (m.key === 'win' || m.key === 'fee') return null;
  const copy = () => { try { navigator.clipboard.writeText(lmsPrompt(m)); toast.success(`${m.name}'s live prompt copied — paste it into its LM Studio preset`); } catch { toast.error('Copy blocked by the browser'); } };
  return <p className="pst-lms" data-testid="pst-lms">
    <b>📌 IN LM STUDIO</b>
    {m.lms ? <span>pick the preset <em>{m.lms.name}</em> — written {ago(m.lms.at)} ago with this mindset</span>
      : <span>{m.key === 'local' ? 'the preset FEELESS LIVE · OSSY appears once LM Studio is on this Mac' : `${m.name}'s LM Studio is on the desktop — paste its live prompt there`}</span>}
    <button type="button" className="m-btn" onClick={copy} data-tip="Copies the exact system prompt FEELESS sends this model (seat prompt + this mindset)" data-testid="pst-lms-copy">📋 Copy prompt</button></p>;
}

// pure: the auto-tune strip's state — RED (the switch acts), GREEN, PROVING (too few trades), WAITING (an applied set is in its cooldown)
export function autoState(a) {
  if (!a) return { tone: 'idle', word: '—' };
  const r = a.recent || {};
  if ((r.n || 0) < 5) return { tone: 'idle', word: `proving — ${r.n || 0} of 5 trades` };
  if (!a.red) return { tone: 'ok', word: `GREEN — ${a.word}` };
  if (a.coolUntil && a.coolUntil > Date.now() / 1000) return { tone: 'wait', word: `RED — ${a.word} · the applied set proves itself until ${new Date(a.coolUntil * 1000).toTimeString().slice(0, 5)}` };
  return { tone: 'red', word: `RED — ${a.word}${a.on ? ' · AUTO-TUNED goes on next round' : ' · switch on to auto-tune'}` };
}

function AutoTune({ m, busy, onToggle }) {
  const a = m.auto || {}; const st = autoState(a); const r = a.recent || {};
  return <section className={`pst-auto is-${st.tone}`} data-testid="pst-auto">
    <span className="pst-auto-art" aria-hidden="true"><svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="15" fill="none" stroke="currentColor" strokeOpacity=".25" strokeWidth="3" />
      <circle className="pst-auto-arc" cx="20" cy="20" r="15" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeDasharray={`${Math.round(0.94 * (r.wonPct ?? 0))} 100`} transform="rotate(-90 20 20)" pathLength="94" />
      <path d="M14 21 l4 4 l8 -10" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
    <span className="pst-auto-mid"><b>🤖 AUTO-TUNE · {m.name}</b><small key={st.word}>{st.word}</small>
      <span className="pst-auto-bar" data-tip={`Won % of the last ${a.n || 10} trades — under ${a.won || 40}% while losing on average = RED`}><i style={{ transform: `scaleX(${Math.max(0.02, (r.wonPct || 0) / 100)})` }} /><b style={{ left: `${a.won || 40}%` }} aria-hidden="true" /></span>
      {a.last ? <small className="pst-auto-last" data-testid="pst-auto-last">last auto-tune {ago(a.last.at)} ago · {(a.last.fixes || []).join(' · ') || a.last.why}</small> : null}</span>
    <label className="m-toggle pst-auto-sw" data-tip={a.on ? `On: when ${m.name}'s last ${a.n || 10} trades turn red, its AUTO-TUNED set is applied (any applied set gets 6 h first)` : `Off: ${m.name} keeps whatever you applied`}>
      <input type="checkbox" role="switch" checked={!!a.on} disabled={busy} onChange={e => onToggle(e.target.checked)} data-testid="pst-auto-switch" aria-label={`Auto-tune ${m.name}`} /><span>{a.on ? 'ON' : 'OFF'}</span></label>
  </section>;
}

// 🐱 FEE: no auto switch (owner 2026-10-31: "you approve each") — AUTO-TUNED rewrites itself from her record; a stronger version waits for Apply
function Approve({ m, busy, onApply }) {
  const r = m.record || {}; const tuned = (m.sets || []).find(s => s.set === 'tuned');
  return <section className={`pst-auto ${m.fresh ? 'is-wait' : 'is-ok'}`} data-testid="pst-approve">
    <span className="pst-auto-art" aria-hidden="true"><svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="15" fill="none" stroke="currentColor" strokeOpacity=".25" strokeWidth="3" />
      <circle className="pst-auto-arc" cx="20" cy="20" r="15" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeDasharray={`${Math.round(0.94 * (r.wonPct ?? 0))} 100`} transform="rotate(-90 20 20)" pathLength="94" />
      <path d="M14 21 l4 4 l8 -10" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
    <span className="pst-auto-mid"><b>🧑‍⚖️ YOU APPROVE · {m.name}</b>
      <small key={String(m.fresh)}>{m.fresh ? '🆕 her record moved — a stronger AUTO-TUNED version is written and waits for your Apply' : `AUTO-TUNED rewrites itself from her record (${m.fixes?.length || 0} habit${m.fixes?.length === 1 ? '' : 's'} found) · nothing goes on until you press Apply`}</small></span>
    {m.fresh && tuned ? <button type="button" className="m-btn m-go" disabled={busy} onClick={() => onApply('tuned')} data-tip="Put the rewritten AUTO-TUNED version on her brains from their next call — Revert any time" data-testid="pst-approve-go">Apply new version</button> : <span />}
  </section>;
}

const MEDAL = ['#f5c451', '#cfd8e3', '#d08a4e'];
function Ladder({ m }) {
  const rows = m.ladder || []; const top = Math.max(5, ...rows.map(r => Math.abs(r.avgPct || 0)));
  return <section className="pst-lad" data-testid="pst-ladder">
    <p className="pst-h"><b>🏆 MINDSET LADDER · {m.name}</b><small>each trade counts for the mindset that was on when it opened · ranked by average %</small></p>
    <ol>{rows.map((r, i) => { const tried = r.n > 0; const v = r.avgPct || 0;
      return <li key={r.set} className={`k-${r.set}${r.active ? ' is-on' : ''}${tried ? '' : ' is-untried'}`} style={{ '--i': i }} data-testid={`pst-rung-${r.set}`}>
        <span className="pst-medal" style={tried && !r.proving && i < 3 ? { '--mc': MEDAL[i] } : undefined}>{tried ? i + 1 : '·'}</span>
        <span className="pst-rung"><b>{r.label}</b>{r.active ? <em className="pst-chip is-on">ON NOW</em> : null}{r.proving ? <em className="pst-chip">proving</em> : null}{!tried ? <em className="pst-chip is-dim">not tried</em> : null}</span>
        <span className="pst-div" data-tip={tried ? `${r.n} trades · ${r.wonPct}% won · ${sgn(r.avgPct)} average` : 'No trade opened while this mindset was on'}>
          <i className={v >= 0 ? 'is-up' : 'is-dn'} style={{ transform: `scaleX(${tried ? Math.max(0.03, Math.min(1, Math.abs(v) / top)) : 0})` }} /></span>
        <span className="pst-rnum"><b className={v >= 0 ? 'is-up' : 'is-dn'} key={r.avgPct}>{tried ? sgn(r.avgPct) : '—'}</b><small>{tried ? `${r.n} · ${r.wonPct}% won${r.usd != null ? ` · ${r.usd >= 0 ? '+' : '−'}$${Math.abs(r.usd).toFixed(2)}` : ''}` : ''}</small></span>
      </li>; })}</ol>
  </section>;
}

export function PromptStudio({ call, only }) {
  const [d, setD] = useState(null); const [key, setKey] = useState(only?.[0] || 'lan'); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [peek, setPeek] = useState(null);
  const load = useCallback(async () => { try { setD(await call('/admin/ai/prompts')); setErr(''); } catch (e) { setErr(String(e?.message || e)); } }, [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => clearInterval(t); }, [load]);
  const models = useMemo(() => (d?.models || []).filter(x => !only || only.includes(x.key)), [d, only]);
  const m = useMemo(() => models.find(x => x.key === key) || models[0], [models, key]);
  const post = async (body, word) => {
    setBusy(true);
    try { const r = await call('/admin/ai/prompts', { method: 'POST', body: JSON.stringify(body) }); setD(r); toast.success(word); } catch (e) { toast.error(String(e?.message || e)); } finally { setBusy(false); }
  };
  if (!d || !m) return <div className="pst m-card is-load" data-testid="pst">{err || d ? <p className="m-note">🎭 {err || 'that brain did not answer — is its service up?'}</p> : <p className="pst-wait"><i /><i /><i /> reading every model's prompt + record…</p>}</div>;
  const w = windowOf(m); const r = m.record || {};
  const won = r.wonPct;
  return <div className="pst m-card m-live" data-testid="pst">
    <header className="pst-head"><span><b className="m-label">🎭 PROMPT STUDIO</b><small>what each model reads · how it trades · the mindset you give it</small></span>
      <div className="m-seg pst-models" role="tablist" aria-label="Model">{models.map(x => <button key={x.key} type="button" role="tab" aria-selected={x.key === m.key} className={x.key === m.key ? 'active' : ''}
        onClick={() => { setKey(x.key); setPeek(null); }} data-testid={`pst-model-${x.key}`} data-tip={`${x.name} · ${x.model || 'model'} · ${x.state || 'state unknown'}`}>
        {avatarOf(x.name) ? <img src={avatarOf(x.name)} alt="" /> : null}<b>{x.name}</b><i className={`pst-dot ${x.state === 'ONLINE' ? 'is-on' : ''}`} />{x.active ? <small className={x.active.seen?.ok ? 'is-live' : ''}>{x.active.seen?.ok ? '✓ ' : ''}{x.active.set.toUpperCase()}</small> : null}</button>)}</div></header>
    {m.approve ? <Approve m={m} busy={busy} onApply={set => post({ key: m.key, set }, `🎭 the new AUTO-TUNED version is on ${m.name}'s brains — from their next call`)} /> : <AutoTune m={m} busy={busy} onToggle={on => post({ key: m.key, auto: on }, on ? `🤖 auto-tune ON for ${m.name} — it acts when the record turns red` : `auto-tune OFF for ${m.name}`)} />}
    <div className="pst-body">
      <section className="pst-ctx" data-testid="pst-ctx">
        <p className="pst-h"><b>LIVE CONTEXT</b><small>{m.model || '—'}</small></p>
        <div className="pst-win" data-tip={w.known ? `${w.used.toLocaleString()} of ${w.total.toLocaleString()} tokens of the loaded window` : 'Window size unknown — drawn against the prompt itself'}>
          <span className="pst-ring" style={{ '--p': Math.min(100, w.pct) }}><b key={w.pct}>{w.known ? `${w.pct}%` : '—'}</b><small>of window</small></span>
          <span className="pst-bar">{w.segs.map(s => <i key={s.k} className={`s-${s.k}`} style={{ flexGrow: s.w }} />)}<i className="s-free" style={{ flexGrow: Math.max(0, 1 - w.used / w.total) }} /></span>
          <small className="pst-winw">{w.used.toLocaleString()} tok{w.known ? ` · ${w.total.toLocaleString()} ctx` : ''}</small></div>
        <ol className="pst-layers">{(m.layers || []).map((l, i) => <li key={l.k} style={{ '--i': i }} className={`s-${l.k}${peek === l.k ? ' is-open' : ''}`}>
          <button type="button" onClick={() => setPeek(peek === l.k ? null : l.k)} aria-expanded={peek === l.k} data-tip={LAYER_TIP[l.k] || l.label} data-testid={`pst-layer-${l.k}`}>
            <i /><b>{l.label}</b><small>{l.tok ? `${l.tok.toLocaleString()} tok` : l.note || '—'}{l.note && l.tok ? ` · ${l.note}` : ''}</small></button>
          {peek === l.k && l.text ? <pre className="pst-pre">{l.text}</pre> : null}</li>)}</ol>
      </section>
      <section className="pst-rec" data-testid="pst-rec">
        <p className="pst-h"><b>THE RECORD</b><small>{m.key === 'fee' ? `her last ${r.n || 0} closed trades · price move at exit` : 'real closed seat trades · ledger'}</small></p>
        <div className="pst-vit">
          <span className="pst-ring is-won" style={{ '--p': won ?? 0 }} data-tip="Share of its real trades that closed green"><b key={won}>{won == null ? '—' : `${won}%`}</b><small>won</small></span>
          <span className="pst-kv"><em>TRADES</em><b key={r.n}>{r.n || 0}</b></span>
          <span className={`pst-kv ${r.avgPct >= 0 ? 'is-up' : 'is-dn'}`}><em>AVG / TRADE</em><b key={r.avgPct}>{sgn(r.avgPct)}</b></span>
          <span className="pst-kv"><em>MED HOLD</em><b>{r.medHeld == null ? '—' : `${Math.round(r.medHeld)}m`}</b></span>
          <span className="pst-kv"><em>ANSWERS</em><b>{r.answerPct == null ? '—' : `${r.answerPct}%`}</b></span>
          <span className="pst-kv"><em>THINK</em><b>{r.medMs == null ? '—' : `${(r.medMs / 1000).toFixed(0)}s`}</b></span></div>
        <p className="pst-h"><b>WHAT THE RECORD SAYS</b><small>{m.fixes?.length ? `${m.fixes.length} habit${m.fixes.length === 1 ? '' : 's'} to fix` : 'nothing to fix'}</small></p>
        {m.fixes?.length ? <ul className="pst-fixes">{m.fixes.map((f, i) => <li key={f.key} style={{ '--i': i }} data-tip={f.rule}><b>{f.title}</b><small>{f.evidence}</small></li>)}</ul>
          : <p className="pst-ok">✓ {r.n || r.yesN ? 'no losing habit shows in the record' : 'no closed record yet — the sets still use the trench theory'}</p>}
      </section>
    </div>
    <Ladder m={m} />
    <p className="pst-h pst-seth"><b>FOUR MINDSETS FOR {m.name}</b><small>written from its record · apply one, revert any time · the desk's rules and money checks never change</small></p>
    <div className="pst-sets">{(m.sets || []).map((s, i) => <SetCard key={`${m.key}-${s.set}`} s={s} m={m} i={i} busy={busy} dials={d.dials}
      active={m.active && m.active.set === s.set ? m.active : null}
      onApply={(set, text) => post({ key: m.key, set, ...(text ? { text } : {}) }, `🎭 ${s.label} applied to ${m.name} — from its next call`)}
      onRevert={() => post({ key: m.key, revert: true }, `${m.name} is back on its plain prompt`)} />)}</div>
  </div>;
}

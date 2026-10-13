import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/agentCockpit.css';

// 🔑 AI API KEY (HQ › Agents › 🔑 AI key; owner, 2026-10-12). Paste a key → the server tests it with ONE read-only list-models request
// (no tokens spent), saves it to backend/.env and sets it in the running service. The page never gets the key back: only the provider,
// "set" and its last 4 characters. The AI router may then use that provider for ADVISORY notes only (ai_router.py).
export const AI_PROVIDERS = [['groq', 'Groq', 'gsk_…'], ['openrouter', 'OpenRouter', 'sk-or-…'], ['openai', 'OpenAI', 'sk-…'], ['xai', 'xAI', 'xai-…'], ['custom', 'Other (OpenAI-compatible)', 'your key']];

export function AiKeyBox({ call, isOwner = true }) {
  const [st, setSt] = useState(null); const [prov, setProv] = useState('groq'); const [key, setKey] = useState(''); const [base, setBase] = useState(''); const [model, setModel] = useState('');
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(null); const [models, setModels] = useState([]);
  useEffect(() => { let on = true; call('/admin/ai-key').then(r => { if (on) setSt(r); }).catch(e => { if (on) setErr(e.message); }); return () => { on = false; }; }, [call]);
  const save = async e => {
    e.preventDefault(); if (busy || !key.trim()) return;
    setBusy(true); setErr(null);
    try { const r = await call('/admin/ai-key', { method: 'POST', body: JSON.stringify({ provider: prov, key: key.trim(), base: prov === 'custom' ? base.trim() : undefined, model: model.trim() || undefined }) });
      setSt(r); setKey(''); setModels(r.models || []); toast.success(`🔑 ${AI_PROVIDERS.find(p => p[0] === prov)?.[1]} key tested and saved (${r.ms} ms)`);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  const clear = async p => { if (busy) return; setBusy(true); setErr(null);
    try { const r = await call('/admin/ai-key', { method: 'POST', body: JSON.stringify({ provider: p, clear: true }) }); setSt(r); toast.success('🔑 key removed'); } catch (x) { setErr(x.message); } finally { setBusy(false); } };
  const rows = (st?.providers || []).filter(r => AI_PROVIDERS.some(p => p[0] === r.key));   // the providers the AI router can use
  return <section className="ack-ai" data-testid="ai-key-box">
    <header><b>🔑 AI API KEY</b><small>tested with one read-only request, stored on the server only — this page never sees it again</small></header>
    {rows.length ? <ul className="ack-ai-list" data-testid="ai-key-list">{rows.map(r => <li key={r.key} className={`${r.set ? 'is-set' : ''} ${r.active ? 'is-active' : ''}`} data-testid={`ai-key-${r.key}`}>
      {r.label}{r.set ? ` · set ${r.hint || ''}` : ''}{r.set && isOwner ? <button type="button" className="m-btn" onClick={() => clear(r.key)} disabled={busy} aria-label={`Remove the ${r.label} key`} data-testid={`ai-key-clear-${r.key}`}>✕</button> : null}</li>)}</ul> : null}
    <form onSubmit={save} className="ack-ai-f" autoComplete="off">
      <div className="m-seg ack-ai-prov" role="group" aria-label="AI provider">{AI_PROVIDERS.map(([k, l]) => <button key={k} type="button" className={prov === k ? 'active' : ''} onClick={() => setProv(k)} data-testid={`ai-prov-${k}`}>{l}</button>)}</div>
      <div className="ack-ai-row">
        <input className="m-input" type="password" value={key} onChange={e => setKey(e.target.value)} placeholder={`${AI_PROVIDERS.find(p => p[0] === prov)?.[2]} API key`} aria-label="API key" disabled={!isOwner || busy} autoComplete="new-password" spellCheck={false} data-testid="ai-key-input" />
        <input className="m-input" value={model} onChange={e => setModel(e.target.value)} placeholder="model (optional)" aria-label="Model" disabled={!isOwner || busy} spellCheck={false} data-testid="ai-key-model" />
        {prov === 'custom' ? <input className="m-input" value={base} onChange={e => setBase(e.target.value)} placeholder="https://api.provider.com/v1" aria-label="API base URL" disabled={!isOwner || busy} spellCheck={false} data-testid="ai-key-base" /> : null}
        <button type="submit" className="m-btn m-go" disabled={!isOwner || busy || !key.trim() || (prov === 'custom' && !base.trim())} data-testid="ai-key-save">{busy ? 'Testing…' : 'Test & save'}</button></div></form>
    {err ? <p className="ack-ai-note is-warn" data-testid="ai-key-err">{err}</p> : null}
    {models.length ? <p className="ack-ai-note" data-testid="ai-key-models">The key answered — models it can use include: {models.join(' · ')}</p> : null}
    <p className="ack-ai-note" data-testid="ai-key-note">{st?.active ? `Active: ${rows.find(r => r.active)?.label}${st.model ? ` · ${st.model}` : ''}${st.base ? ` · ${st.base}` : ''}. ` : ''}{st?.note || 'Advisory only — a model never places, sizes, blocks or sells anything; a stance moves the ranking (±10% at most) only once it is proven on its own judged record.'}</p>
  </section>;
}

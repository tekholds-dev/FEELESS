import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { AiKeyBox } from './AiKeyBox';

// 🧠 AI PROVIDERS (HQ › Agents › the AI chip; owner, 2026-10-12): the AI router's providers in their fallback order — local LM Studio
// first, then Groq / OpenRouter / OpenAI / xAI / any OpenAI-compatible host. Per row: on / off, ▲▼ priority, Test, state, model, last
// latency, last success, failures. Keys never reach this page (the server says only "set" + the last 4); they are pasted in the key box
// below or in backend/.env. Everything a model says is ADVISORY — shown beside the desk that asked, never a rank, size, order or stop.
const STATE_CLS = { ONLINE: 'is-on', 'RATE LIMITED': 'is-warn', OFFLINE: 'is-bad', 'BAD ANSWER': 'is-bad', 'KEY MISSING': 'is-off', 'MODEL MISSING': 'is-off', DISABLED: 'is-off', 'NOT CONFIGURED': 'is-off', UNTESTED: 'is-wait' };
const ago = at => { if (!at) return 'never'; const s = Math.max(0, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${(s / 3600).toFixed(1)}h ago`; };

// the compact status chip: "AI · LOCAL ● 42ms · GROQ ○ …" from the router's own rows (no request of its own)
export function aiChip(ai) {
  const rows = ai?.providers || [];
  if (!rows.length) return { cls: 'is-off', parts: [['none', 'not loaded', 'is-off']], tip: 'AI router status arrives with the next agent pass' };
  const shown = rows.filter(r => r.enabled && r.state !== 'KEY MISSING').slice(0, 3);
  const parts = (shown.length ? shown : rows.slice(0, 1)).map(r => [r.key, `${r.key === 'local' ? 'LOCAL' : r.label.split(' ')[0]} ${r.state === 'ONLINE' ? '●' : '○'}${r.state === 'ONLINE' && r.lastMs != null ? ` ${r.lastMs}ms` : ''}`, STATE_CLS[r.state] || 'is-wait']);
  const on = rows.some(r => r.state === 'ONLINE');
  return { cls: on ? 'is-on' : 'is-off', parts, tip: `${on ? 'advisory AI online' : 'no AI provider online — the kernel runs deterministic only'} · ${ai?.totals?.answered ?? 0} answers · ${ai?.totals?.fallbacks ?? 0} fallbacks · tap for providers` };
}

export function AiProviders({ call, isOwner = true, ai, close }) {
  const [v, setV] = useState(ai || null); const [busy, setBusy] = useState(null);
  useEffect(() => { let on = true; call('/admin/ai/providers').then(r => { if (on && r) setV(r); }).catch(() => {}); return () => { on = false; }; }, [call]);
  useEffect(() => { const k = e => { if (e.key === 'Escape') close(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [close]);
  const rows = v?.providers || [];
  const post = async (path, body, msg) => { setBusy(path + (body.provider || '')); try { const r = await call(path, { method: 'POST', body: JSON.stringify(body) }); setV(r); if (msg) msg(r); return r; } catch (e) { toast.error(e.message); return null; } finally { setBusy(null); } };
  const order = rows.map(r => r.key);
  const move = (k, dir) => { const i = order.indexOf(k); const j = i + dir; if (j < 0 || j >= order.length) return; const nx = [...order]; [nx[i], nx[j]] = [nx[j], nx[i]]; post('/admin/ai/providers', { order: nx }); };
  const toggle = r => post('/admin/ai/providers', { enabled: { [r.key]: !r.enabled } });
  const test = r => post('/admin/ai/test', { provider: r.key }, x => (x.ok ? toast.success(`${r.label}: online · ${x.ms}ms`) : toast.error(`${r.label}: ${x.state || 'failed'} — ${x.err || ''}`)));
  return <div className="aip-shade" onMouseDown={e => { if (e.target === e.currentTarget) close(); }} data-testid="ai-providers-shade">
    <aside className="aip" role="dialog" aria-label="AI providers" data-testid="ai-providers">
      <header><b>🧠 AI PROVIDERS</b><small>fallback order · advisory only</small><button type="button" className="m-btn" onClick={close} aria-label="Close" data-testid="aip-close">✕</button></header>
      <p className="aip-note">{v?.note || 'Advisory only: an AI answer is shown next to the desk that asked; it never places, sizes, blocks or sells anything; a stance moves the ranking (±10% at most) only once it is proven on its own judged record.'}
        {' '}Never asked by: {(v?.never || ['tally', 'trigger', 'reaper', 'courier', 'warden']).join(' · ')}.</p>
      <ol className="aip-list" data-testid="aip-list">{rows.map((r, i) => <li key={r.key} className={`${r.enabled ? '' : 'is-disabled'}`} data-testid={`aip-row-${r.key}`}>
        <span className="aip-pri">{r.priority}</span>
        <span className="aip-name"><b>{r.label}</b><small>{r.model || 'model —'}{r.host ? ` · ${r.host}` : ''}{r.keySet ? ` · key ${r.hint || 'set'}` : ''}</small></span>
        <i className={`aip-state ${STATE_CLS[r.state] || 'is-wait'}`} data-testid={`aip-state-${r.key}`}>{r.state}</i>
        <span className="aip-stat"><small>last {r.lastMs != null ? `${r.lastMs}ms` : '—'} · ok {ago(r.lastOkAt)}</small><small>{r.requests} req · {r.failures} fail{r.timeouts ? ` · ${r.timeouts} timeout` : ''}{r.coolSec ? ` · resting ${r.coolSec}s` : ''}</small>
          {r.lastErr ? <small className="aip-err">{r.lastErr}</small> : r.why && r.state !== 'DISABLED' ? <small className="aip-err">{r.why}</small> : null}</span>
        <span className="aip-acts">
          <button type="button" className="m-btn" disabled={!isOwner || !!busy || i === 0} onClick={() => move(r.key, -1)} aria-label={`Move ${r.label} up`} data-testid={`aip-up-${r.key}`}>▲</button>
          <button type="button" className="m-btn" disabled={!isOwner || !!busy || i === rows.length - 1} onClick={() => move(r.key, 1)} aria-label={`Move ${r.label} down`} data-testid={`aip-down-${r.key}`}>▼</button>
          <button type="button" className={`m-toggle ${r.enabled ? 'is-on' : ''}`} role="switch" aria-checked={r.enabled} disabled={!isOwner || !!busy} onClick={() => toggle(r)} data-testid={`aip-on-${r.key}`}>{r.enabled ? 'ON' : 'OFF'}</button>
          <button type="button" className="m-btn" disabled={!isOwner || !!busy || !r.enabled} onClick={() => test(r)} data-testid={`aip-test-${r.key}`}>{busy === `/admin/ai/test${r.key}` ? 'Testing…' : 'Test'}</button></span></li>)}</ol>
      <p className="aip-tot" data-testid="aip-totals">{v?.totals ? `${v.totals.asked} asked · ${v.totals.answered} answered · ${v.totals.fallbacks} fallbacks · ${v.totals.cached} cached · ${v.totals.none} deterministic only` : 'no requests yet'}
        {v?.lastAt ? ` · last advisory round ${ago(v.lastAt)}${v.lastMs != null ? ` (${v.lastMs}ms)` : ''}` : ''}</p>
      <AiKeyBox call={call} isOwner={isOwner} />
      <p className="aip-note">Local LM Studio: <code>LOCAL_LLM_ENABLED</code> · <code>LOCAL_LLM_BASE_URL</code> (this machine only) · <code>LOCAL_LLM_MODEL</code> in backend/.env. Set <code>LOCAL_LLM_ENABLED=false</code> to switch it off at once — the kernel never waits on a model.</p>
    </aside></div>;
}

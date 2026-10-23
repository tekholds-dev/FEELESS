import React, { useCallback, useEffect, useState } from 'react';
import '../../styles/modelDesk.css';
import { ModelRig } from './ModelRig';

// 🧠 THE MODEL DESK (owner, 2026-10-23: "the Models tab should really show all this — server settings, MCP, load, inference … more vitals for all
// models, and fix how the models look in the Brain"): LM Studio's own model panel, inside FEELESS. On top, VITALS for every model (tokens / s from
// real usage, ok %, median + p90 time, queue, context fill, last answer, the mindset it carries); below, the picked model's INFO · LOAD ·
// INFERENCE · SERVER · MCP — read from what LM Studio, NEXA's llamafile and FEELESS's MCP server really report. One model at a time: nothing cut off.
const AV = { lan: '/assets/ai-pfp/g4.gif', local: '/assets/ai-pfp/ossy.gif', win: null };
const TABS = [['info', 'ℹ INFO'], ['load', '⚙ LOAD'], ['infer', '🌡 INFERENCE'], ['server', '🖥 SERVER'], ['mcp', '🔌 MCP']];
const k1 = v => (v == null ? '—' : v >= 1024 ? `${v % 1024 ? (v / 1024).toFixed(1) : v / 1024}K` : String(v));
const secs = ms => (ms == null ? '—' : `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)}s`);
const ago = at => { if (!at) return '—'; const s = Math.max(0, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
// the Inference panel's knobs (LM Studio's own names) — 'desk' = FEELESS's default (nothing sent)
export const KNOBS = [
  ['temp', 'TEMPERATURE', [null, 0.2, 0.4, 0.6, 0.8, 1.0], 'How loose the answers get. FEELESS desk calls use 0.1 for clean JSON — higher = more creative, more broken answers', 'temperature'],
  ['maxTok', 'LIMIT RESPONSE LENGTH', [null, 250, 500, 1000, 2000], 'Max tokens per answer (NEXA stays capped for speed)', null],
  ['topP', 'TOP-P', [null, 0.8, 0.9, 0.95, 1.0], 'Sampling: keep the smallest set of tokens whose probability adds up to this', 'top_p'],
  ['topK', 'TOP-K', [null, 20, 40, 80], 'Sampling: only the K most likely tokens are considered', 'top_k'],
  ['minP', 'MIN-P', [null, 0.02, 0.05, 0.1], 'Sampling: drop tokens under this share of the top token\'s probability', 'min_p'],
  ['repeatPenalty', 'REPEAT PENALTY', [null, 1.0, 1.05, 1.1, 1.2], 'Penalise repeating itself (1.0 = off)', 'repeat_penalty'],
  ['seed', 'SEED', [null, 42], 'Fixed seed = the same answer to the same prompt (debugging); default = random', 'seed'],
];

// pure: one knob's chip words — the override, else FEELESS's desk default, else what the runtime uses on its own
export function knobWord(k, inf) {
  const [f, , , , rt] = k; const o = inf?.infer?.[f];
  if (o != null) return { v: o, src: 'yours' };
  if (f === 'temp') return { v: inf?.desk?.temp ?? 0.1, src: 'desk' };
  if (f === 'maxTok') return { v: inf?.desk?.maxTok ?? null, src: 'desk' };
  const r = rt ? inf?.runtime?.[rt] : null;
  return r != null ? { v: r, src: 'runtime' } : { v: null, src: 'model default' };
}

function Ring({ p, label, tone }) {
  return <span className={`mdk-ring ${tone || ''}`} style={{ '--p': Math.max(0, Math.min(100, p ?? 0)) }}><b key={p}>{p == null ? '—' : `${p}%`}</b><small>{label}</small></span>;
}
function Bar({ v, max, label, word, tip }) {
  return <span className="mdk-bar" data-tip={tip}><em>{label}</em><i><s style={{ transform: `scaleX(${v == null ? 0 : Math.max(0.03, Math.min(1, v / max))})` }} /></i><b key={word}>{word}</b></span>;
}

function VitalCard({ m, on, onPick, i }) {
  const v = m.vitals || {}; const live = String(m.state || '').toUpperCase() === 'ONLINE';
  return <button type="button" className={`mdk-vc k-${m.key}${on ? ' is-on' : ''}`} style={{ '--i': i }} onClick={onPick} aria-pressed={on} data-testid={`mdk-vc-${m.key}`}
    data-tip={`${m.name}: tap to open its INFO · LOAD · INFERENCE · SERVER · MCP`}>
    <span className="mdk-vh">{AV[m.key] ? <img src={AV[m.key]} alt="" /> : <i className="mdk-av" aria-hidden="true">N</i>}<b>{m.name}</b><i className={`mdk-dot ${live ? 'is-on' : ''}`} />
      <small>{String(m.model || '—').split('/').pop()}</small>{v.queue ? <u className="mdk-q" data-tip="Calls in flight right now">{v.queue} thinking</u> : null}</span>
    <span className="mdk-vb"><Ring p={v.okPct} label="answered" tone={v.okPct != null && v.okPct < 70 ? 'is-bad' : ''} />
      <span className="mdk-bars">
        <Bar label="TOK/S" v={v.tokPerSec} max={60} word={v.tokPerSec == null ? '—' : v.tokPerSec} tip="Real completion tokens per second (from the model's own usage report)" />
        <Bar label="MED · P90" v={v.medMs} max={60000} word={`${secs(v.medMs)} · ${secs(v.p90Ms)}`} tip="Median and 90th-percentile answer time over the last calls" />
        <Bar label="CTX FILL" v={v.ctxFill} max={1} word={v.ctxFill == null ? '—' : `${Math.round(v.ctxFill * 100)}%`} tip="How much of the loaded context the last prompt used" />
      </span></span>
    <span className="mdk-vf"><small>{v.calls || 0} calls · last answer {ago(v.lastOkAt)} ago</small>{v.errors ? <u className="mdk-err" data-tip={v.lastErr || ''}>✕ {v.errors}</u> : null}
      {v.mindset ? <u className="mdk-mind" data-tip="The 🎭 mindset its last call carried">🎭 {v.mindset}</u> : null}</span>
  </button>;
}

function KV({ rows }) {
  return <dl className="mdk-kv">{rows.filter(Boolean).map(([k, v, tip], i) => <div key={k} style={{ '--i': i }} data-tip={tip}><dt>{k}</dt><dd>{v == null || v === '' ? '—' : v}</dd></div>)}</dl>;
}

function Info({ m }) {
  const i = m.info;
  if (!i) return <p className="m-note">{m.name}'s server did not answer — {m.server?.err || 'no model info'}. Start its server (LM Studio › Developer › Start, or NEXA's llamafile).</p>;
  if (m.key === 'win') return <><KV rows={[['MODEL FILE', i.model], ['FORMAT', i.format], ['QUANT', i.quant], ['CONTEXT / SLOT', k1(i.ctxPerSlot)], ['SLOTS', i.slots != null ? `${i.busy || 0} busy of ${i.slots}` : null], ['SPECULATIVE', i.speculative ? 'on' : 'off']]} />
    <p className="mdk-note">Read live from llamafile's own /props + /slots.</p></>;
  const fill = i.loadedCtx && i.maxCtx ? Math.log2(i.loadedCtx / 2048) / Math.log2(Math.max(4096, i.maxCtx) / 2048) : 0;
  return <>
    <div className="mdk-ctx" data-tip="Loaded context against the model's max (log scale)"><span><em>LOADED CONTEXT</em><b>{k1(i.loadedCtx)}</b><small>of {k1(i.maxCtx)} max</small></span>
      <i><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, fill))})` }} /></i></div>
    <KV rows={[['MODEL', i.name], ['PUBLISHER', i.publisher], ['ARCHITECTURE', i.arch], ['FORMAT', i.format], ['QUANT', i.quant ? `${i.quant}${i.bits ? ` · ${i.bits}-bit` : ''}` : null], ['SIZE', i.sizeGb ? `${i.sizeGb} GB` : null],
      ['PARAMS', i.params], ['PARALLEL', i.parallel ? `×${i.parallel}` : null], ['INSTANCES', i.instances], ['VARIANT', i.variant ? i.variant.split('@').pop() : null]]} />
    <p className="mdk-caps">{i.toolUse ? <u className="is-on" data-tip="Trained for tool use — it can call FEELESS's MCP tools">🛠 tool use</u> : <u>🛠 no tool use</u>}
      <u className={i.vision ? 'is-on' : ''}>👁 {i.vision ? 'vision' : 'no vision'}</u>
      {i.reasoning ? <u className="is-on" data-tip="Reasoning effort this model offers (LM Studio's own setting)">🧠 reasoning {i.reasoning.options.join(' / ')} · default {i.reasoning.default}</u> : null}</p>
    <p className="mdk-note">Read live from LM Studio's own model list (GET /api/v1/models).</p></>;
}

function Infer({ m, call, onSaved }) {
  const inf = m.inference || {}; const [busy, setBusy] = useState(''); const [stop, setStop] = useState('');
  const save = async (f, v) => { setBusy(f); try { await call('/admin/ai/rig', { method: 'POST', body: JSON.stringify({ [m.key]: { infer: { [f]: v } } }) }); onSaved(); } catch (e) { window.dispatchEvent(new CustomEvent('feeless:toast', { detail: String(e?.message || e) })); } setBusy(''); };
  const stops = inf.infer?.stop || [];
  return <>
    <section className="mdk-sys" data-testid="mdk-sys"><em>📜 SYSTEM PROMPT · what FEELESS sends</em>
      <p>Its job prompt (seat / desk rules) {inf.mindset ? <>+ the <b>🎭 {inf.mindset.set.toUpperCase()}</b> mindset {inf.mindset.seen?.ok ? <u className="is-on">✓ in use · last call {ago(inf.mindset.seen.at)} ago</u> : <u>rides the next call</u>}</> : '· no mindset applied'} — read or change it in 🎭 Prompts.
        LM Studio's own preset box only feeds its own chat window; FEELESS's calls carry their own system prompt.</p></section>
    <div className="mdk-knobs">{KNOBS.map((k, i) => { const [f, label, opts, tip] = k; const w = knobWord(k, inf);
      return <div key={f} className="mdk-knob" style={{ '--i': i }} data-tip={tip} data-testid={`mdk-knob-${f}`}>
        <em>{label}<small className={`src-${w.src.replace(/\s/g, '-')}`}>{w.v == null ? w.src : `${w.v} · ${w.src}`}</small></em>
        <div className="mdk-seg">{opts.map(v => { const active = v == null ? inf.infer?.[f] == null : inf.infer?.[f] === v;
          return <button key={String(v)} type="button" className={active ? 'active' : ''} disabled={!!busy} aria-busy={busy === f} onClick={() => save(f, v)}
            data-testid={`mdk-${f}-${v == null ? 'def' : v}`}>{v == null ? (f === 'temp' || f === 'maxTok' ? 'desk' : f === 'seed' ? 'random' : 'default') : v}</button>; })}</div></div>; })}
      <div className="mdk-knob" data-tip="Stop strings: the answer ends when the model writes one of these (≤ 4)" data-testid="mdk-knob-stop"><em>STOP STRINGS<small>{stops.length ? `${stops.length} set` : 'none'}</small></em>
        <form className="mdk-stop" onSubmit={e => { e.preventDefault(); if (stop.trim()) { save('stop', [...stops, stop.trim()].slice(0, 4)); setStop(''); } }}>
          {stops.map(x => <button key={x} type="button" className="mdk-chip" onClick={() => save('stop', stops.filter(y => y !== x))} aria-label={`Remove stop string ${x}`}>{x} ✕</button>)}
          <input className="m-input" value={stop} onChange={e => setStop(e.target.value)} maxLength={24} placeholder="type a string · Enter" aria-label="Add a stop string" /></form></div></div>
    <KV rows={[['CONTEXT OVERFLOW', m.key === 'win' ? 'llamafile shifts the window' : 'LM Studio load setting (your preset)', 'FEELESS keeps each prompt inside the window with its prompt budget'],
      ['STRUCTURED OUTPUT', 'one JSON object, parsed by FEELESS', 'The schema rides in the prompt; a broken answer is retried or skipped'],
      ['SPECULATIVE DECODING', m.key === 'win' ? (inf.speculative ? 'on' : 'off') : 'off — needs a draft model loaded in LM Studio'],
      inf.reasoning ? ['REASONING EFFORT', `${inf.reasoning.options.join(' / ')} · default ${inf.reasoning.default}`, 'gpt-oss reasoning effort, set in LM Studio'] : null]} />
    <div className="mdk-chat"><em>💬 BRAIN CHAT · temperature + length for your Talk tab</em><ModelRig call={call} cards={false} /></div>
  </>;
}

function Server({ m }) {
  const s = m.server || {};
  return <><div className={`mdk-srv ${s.ok ? 'is-ok' : 'is-bad'}`}><i aria-hidden="true" /><b>{s.ok ? 'ANSWERING' : 'NOT ANSWERING'}</b><small>{s.ok ? `${s.ms ?? '—'} ms round trip` : s.err || ''}</small></div>
    <KV rows={[['ENDPOINT', s.endpoint], ['API', s.api], ['AUTH TOKEN', s.keySet ? 'set (sent as Bearer)' : 'none'], ['STATE (FEELESS)', s.state], ['LAST GOOD ANSWER', s.lastOkAt ? `${ago(s.lastOkAt)} ago` : null],
      m.key === 'win' ? ['SLOTS', s.slots != null ? `${s.busy || 0} busy of ${s.slots}` : null] : ['MODELS LISTED', s.listed], m.key === 'win' ? null : ['LOADED INSTANCES', s.instances],
      ['TIMEOUT', s.timeout ? `${s.timeout}s` : null, 'FEELESS gives up on a call after this (⚙ LOAD › SENDS)'], ['AT ONCE', s.parallel ? `×${s.parallel}` : null], ['PACE', s.perMin ? `${s.perMin} calls / min` : null]]} /></>;
}

function Mcp({ mcp, m }) {
  if (!mcp) return null;
  return <><div className={`mdk-srv ${mcp.ok ? 'is-ok' : 'is-bad'}`}><i aria-hidden="true" /><b>{mcp.ok ? 'FEELESS MCP ONLINE' : 'FEELESS MCP NOT ANSWERING'}</b><small>{mcp.ok ? `${mcp.n} tools · ${mcp.ms} ms · ${mcp.endpoint}` : mcp.err || ''}</small></div>
    <p className="mdk-note">{m.key === 'win' ? 'NEXA answers one word on her desk — tools are for the LM Studio models.' : m.info?.toolUse ? `${m.name} is trained for tool use — LM Studio hands it these tools (mcp.json on its machine).` : `${m.name} is not marked for tool use.`}</p>
    <div className="mdk-tools">{(mcp.tools || []).map((t, i) => <span key={t.name} style={{ '--i': i }} data-tip={t.desc}><b>{t.name}</b><small>{t.desc}</small></span>)}</div></>;
}

export function ModelDesk({ call }) {
  const [d, setD] = useState(null); const [key, setKey] = useState('lan'); const [tab, setTab] = useState('info'); const [err, setErr] = useState('');
  const load = useCallback(async () => { try { setD(await call('/admin/ai/models')); setErr(''); } catch (e) { setErr(String(e?.message || e)); } }, [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 5000); return () => clearInterval(t); }, [load]);
  if (!d?.models?.length) return <p className="mdk-wait">{err || 'reading every model…'}</p>;   // an old / partial payload never crashes the Brain
  const m = d.models.find(x => x.key === key) || d.models[0];
  return <div className="mdk" data-testid="model-desk">
    <div className="mdk-vit">{d.models.map((x, i) => <VitalCard key={x.key} m={x} i={i} on={x.key === m.key} onPick={() => setKey(x.key)} />)}</div>
    <section className={`mdk-panel k-${m.key}`} data-testid={`mdk-panel-${m.key}`}>
      <header className="mdk-ph"><b>{m.name}</b><span>{m.info?.name || m.model}</span>
        <small>{[m.info?.publisher, m.info?.arch, m.info?.quant, m.info?.format].filter(Boolean).join(' · ')}</small></header>
      <nav className="mdk-tabs m-seg" role="tablist" aria-label={`${m.name} settings`}>{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''}
        onClick={() => setTab(k)} data-testid={`mdk-tab-${k}`}>{l}</button>)}</nav>
      <div className="mdk-body" key={`${m.key}-${tab}`}>
        {tab === 'info' ? <Info m={m} /> : null}
        {tab === 'load' ? <ModelRig call={call} only={m.key} bare /> : null}
        {tab === 'infer' ? <Infer m={m} call={call} onSaved={load} /> : null}
        {tab === 'server' ? <Server m={m} /> : null}
        {tab === 'mcp' ? <Mcp mcp={d.mcp} m={m} /> : null}
      </div>
    </section>
  </div>;
}

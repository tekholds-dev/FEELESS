import React, { useCallback, useEffect, useState } from 'react';
import { useGlide } from '../../lib/useGlide';
import '../../styles/modelRig.css';

// 🎛 LM STUDIO RIG (Brain › Models) — ONE view of every model setting (owner, 2026-10-21: "one full LM Studio Load + Inference view"):
//   LOADED NOW = what LM Studio itself reports (GET /api/v1/models) · LOAD = what the model should be loaded with (⚡ Reload = your tap, never
//   a timer) · SENDS = what FEELESS sends it (live at once) · INFERENCE = the Brain's temperature + answer length. A chat line in Talk
//   ("ossy context 16k, temp 0.6") lands here as a proposal you ✅ — the same settings, the same gate (backend/ai_rig.py).
const FIELDS = [['ctx', '🧠 PROMPT BUDGET', v => (v ? `${v / 1024}K` : 'auto'), 'How much of the context FEELESS fills per call (auto = what the model is loaded with)'],
  ['parallel', '⚡ SLOTS', v => `×${v}`, 'Calls FEELESS sends at once'], ['timeout', '⏱ TIMEOUT', v => `${v}s`, 'Seconds a call may take before it counts as a miss'],
  ['perMin', '📞 CALLS / MIN', v => `${v}`, 'Background calls a minute (your own chat is never capped)'], ['every', '🔁 READ EVERY', v => `${v / 60}m`, 'How often NEXA reads FeeCat\'s desk']];
const LOAD = [['ctx', '🧠 CONTEXT', v => `${v / 1024}K`, 'Context length the model is LOADED with (LM Studio Load › Context Length)'],
  ['par', '⚡ AT ONCE', v => `×${v}`, 'Max concurrent predictions — LM Studio Load › Max Concurrency'],
  ['flash', '⚡ FLASH ATTN', v => (v ? 'ON' : 'OFF'), 'Flash attention — less memory, faster (llama.cpp / GGUF only)'],
  ['kv', '💾 KV CACHE', v => (v ? 'GPU' : 'RAM'), 'Where the KV cache lives — GPU is faster, RAM frees VRAM (GGUF only)'],
  ['batch', '📦 EVAL BATCH', v => `${v}`, 'Prompt tokens processed per batch (GGUF only)']];
const TEMPS = [[0.1, 'exact'], [0.3, 'sharp'], [0.6, 'loose'], [0.9, 'wild']];
const SAY = ['ossy context 16k', 'g4 max concurrent 1', 'temp 0.6 and long answers', 'both models context 32k'];
const AV = { lan: '/assets/ai-pfp/g4.gif', local: '/assets/ai-pfp/ossy.gif', win: null };
const k1 = v => (v ? `${(v / 1024).toFixed(v % 1024 ? 1 : 0)}K` : '—');

// 🪟 NEXA's runtime: what you saved vs what llamafile itself reports (/props + /slots). ACTIVE only when the runtime says so.
export const NX_STATE = { active: ['✅ ACTIVE', 'ok'], applying: ['⏳ APPLYING', 'busy'], differs: ['⚠ NOT APPLIED', 'warn'], unreachable: ['✕ NEXA OFFLINE', 'bad'] };
const ctxWord = k1;
export function NexaRuntime({ n, busy, onAct }) {
  if (!n) return null;
  const [word, tone] = NX_STATE[n.state] || ['—', ''];
  const want = n.desired; const got = n.actual;
  const same = k => want && got && want[k] === got[k];
  return <div className={`mrg-nx t-${tone}`} data-testid="nexa-runtime">
    <div className="mrg-nxh"><b>{word}</b><small>{n.controller?.reachable ? '🟢 controller online' : '🔴 controller offline — settings are saved, NEXA is not changed'}</small></div>
    <div className="mrg-nxg">
      <span><em>WANTED</em><b>{want ? `${ctxWord(want.ctx)} × ${want.slots}` : 'auto'}</b></span>
      <i aria-hidden>{n.state === 'applying' ? '⟳' : '→'}</i>
      <span className={got ? (same('ctx') && same('slots') ? 'is-ok' : 'is-off') : ''}><em>RUNNING</em><b>{got ? `${ctxWord(got.ctx)} × ${got.slots}` : 'not answering'}</b>{got?.model ? <small>{got.model}</small> : null}</span>
    </div>
    {n.state === 'applying' ? <span className="mrg-nxbar" aria-hidden><i /></span> : null}
    {n.job?.msg ? <p className="mrg-nxmsg">{n.job.msg}</p> : null}
    {n.auto ? <p className="mrg-nxmsg">Pick a context (not auto) to control NEXA's runtime.</p> : null}
    <div className="mrg-nxacts">
      <button type="button" className="m-btn primary" disabled={!!busy || n.auto || n.state === 'applying'} onClick={() => onAct('apply')} data-testid="nexa-apply" data-tip="Restart NEXA's llamafile with the wanted context × slots">Apply to NEXA</button>
      <button type="button" className="m-btn" disabled={!!busy || n.state === 'applying'} onClick={() => onAct('restart')} data-testid="nexa-restart" data-tip="Restart her llamafile as it is">⟳ Restart NEXA</button>
    </div>
  </div>;
}

// 🧠 the loaded context as a drawn ring (loaded ÷ the model's max) + one dot per concurrent slot — LM Studio's own numbers
export function LoadedNow({ lm }) {
  const inst = lm?.loaded?.[0];
  const ctx = useGlide(inst?.ctx ?? 0);
  if (!lm) return <div className="mrg-now is-off" data-testid="lms-now"><b>LM Studio not answering</b><small>start its server (Developer › Start) — the settings below still save</small></div>;
  if (!inst) return <div className="mrg-now is-off" data-testid="lms-now"><b>NOTHING LOADED</b><small>{lm.model} is on disk · tap ⚡ Load below</small></div>;
  const pct = lm.maxCtx > 2048 ? Math.min(1, Math.max(0, Math.log2(inst.ctx / 2048) / Math.log2(lm.maxCtx / 2048))) : 0.5; const C = 2 * Math.PI * 22;   // log scale: 8K of 128K reads as a third, not a sliver
  return <div className="mrg-now" data-testid="lms-now">
    <svg className="mrg-ring" viewBox="0 0 56 56" aria-hidden data-tip="Loaded context on a log scale, from 2K to the model's max"><circle cx="28" cy="28" r="22" className="mrg-rbg" />
      <circle cx="28" cy="28" r="22" className="mrg-rfg" strokeDasharray={`${C * Math.max(0.03, pct)} ${C}`} /></svg>
    <span className="mrg-nowtxt"><em>LOADED NOW · LM STUDIO</em><b>{k1(ctx)}<small> of {k1(lm.maxCtx)}</small></b>
      <span className="mrg-slots" data-tip={`${inst.par || 1} prediction${(inst.par || 1) > 1 ? 's' : ''} at once`}>{Array.from({ length: Math.max(1, inst.par || 1) }, (_, i) => <i key={i} style={{ '--i': i }} />)}<small>×{inst.par || 1}</small></span></span>
    <span className="mrg-tags"><u>{String(lm.fmt || '?').toUpperCase()}</u>{lm.sizeGb ? <u>{lm.sizeGb} GB</u> : null}{lm.params ? <u>{lm.params}</u> : null}
      {inst.flash != null ? <u className={inst.flash ? 'is-on' : ''}>FLASH {inst.flash ? 'ON' : 'OFF'}</u> : null}{inst.kv != null ? <u>KV {inst.kv ? 'GPU' : 'RAM'}</u> : null}</span>
  </div>;
}

// 🔖 a model's presets: save its rig now under a name, tap one to apply it (G4 / OSSY still reload only on ⚡), ✕ to drop
function Presets({ k, list, busy, onAct }) {
  const [name, setName] = useState('');
  return <div className="mrg-grp mrg-pre" data-testid={`rig-${k}-presets`}><em className="mrg-lbl">🔖 PRESETS <small>save · pick · apply</small></em>
    {list.length ? <div className="mrg-pchips">{list.map((p, i) => <span key={p.name} className="mrg-pchip" style={{ '--i': i }}>
      <button type="button" disabled={!!busy} onClick={() => onAct({ act: 'apply', key: k, name: p.name })} data-tip={`Apply "${p.name}"${p.words ? ` — ${p.words}` : ''}`} data-testid={`rig-${k}-preset-${p.name}`}>{p.name}</button>
      <button type="button" className="mrg-pdrop" disabled={!!busy} onClick={() => onAct({ act: 'drop', key: k, name: p.name })} aria-label={`Delete preset ${p.name}`} data-tip="Delete this preset">✕</button></span>)}</div> : null}
    <form className="mrg-psave" onSubmit={e => { e.preventDefault(); if (name.trim()) { onAct({ act: 'save', key: k, name }); setName(''); } }}>
      <input className="m-input" value={name} maxLength={32} onChange={e => setName(e.target.value)} placeholder="name this setup…" aria-label="Preset name" data-testid={`rig-${k}-preset-name`} />
      <button type="submit" className="m-btn" disabled={!!busy || !name.trim()} data-tip="Save this model's settings right now as a preset" data-testid={`rig-${k}-preset-save`}>Save</button></form></div>;
}

export function ModelRig({ call }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [note, setNote] = useState(null);
  const load = useCallback(() => call('/admin/ai/rig').then(setD).catch(e => setErr(String(e?.message || e))), [call]);
  const applying = d?.nexa?.state === 'applying' || (d?.reloading || []).length > 0;
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, applying ? 3000 : 20000); return () => clearInterval(t); }, [load, applying]);
  const post = async (tag, body) => {
    setBusy(tag);
    try { const r = await call('/admin/ai/rig', { method: 'POST', body: JSON.stringify(body) }); setD(r); setErr(''); if (r.reload) setNote(r.reload); } catch (e) { setErr(String(e?.message || e)); }
    setBusy('');
  };
  const save = (key, f, v) => post(`${key}.${f}`, { [key]: { [f]: v } });
  const want = (key, f, v) => post(`${key}.load.${f}`, { [key]: { load: { [f]: v } } });
  const nexa = act => post(`nexa.${act}`, { nexa: act });
  const preset = async body => { setBusy(`preset.${body.key}`); try { setD(await call('/admin/ai/rig/preset', { method: 'POST', body: JSON.stringify(body) })); setErr(''); } catch (e) { setErr(String(e?.message || e)); } setBusy(''); };
  const chatSet = async patch => {
    setBusy(`chat.${Object.keys(patch)[0]}`);
    try { await call('/admin/ai/chat/settings', { method: 'POST', body: JSON.stringify(patch) }); setD(x => ({ ...x, chat: { ...x.chat, ...patch } })); } catch (e) { setErr(String(e?.message || e)); }
    setBusy('');
  };
  const say = t => window.dispatchEvent(new CustomEvent('feeless:brain-say', { detail: { text: t } }));
  if (!d?.rows) return <p className="mrg-wait">{err || 'reading the rig…'}</p>;
  return <div className="mrg" data-testid="model-rig">
    <header className="mrg-head"><b>🎛 LM STUDIO RIG</b><small>LOADED = what LM Studio reports · LOAD = applied only when you tap ⚡ Reload · SENDS + INFERENCE = live at once</small></header>
    {d.chat ? <section className="mrg-inf" data-testid="rig-inference"><em className="mrg-lbl">🌡 INFERENCE · BRAIN CHAT</em>
      <div className="mrg-seg" data-tip="Temperature: how loose the answers get">{TEMPS.map(([v, l]) => <button key={v} type="button" className={d.chat.temp === v ? 'active' : ''} disabled={!!busy}
        onClick={() => chatSet({ temp: v })} data-testid={`rig-chat-temp-${v}`}>{l}<small>{v}</small></button>)}</div>
      <div className="mrg-seg" data-tip="Response length (max tokens per answer)">{Object.entries(d.chat.lens || {}).map(([k, n]) => <button key={k} type="button" className={d.chat.len === k ? 'active' : ''} disabled={!!busy}
        onClick={() => chatSet({ len: k })} data-testid={`rig-chat-len-${k}`}>{k}<small>{n}</small></button>)}</div></section> : null}
    <p className="mrg-say"><em>💬 OR SAY IT</em>{SAY.map(t => <button key={t} type="button" onClick={() => say(t)} data-tip="Puts this line in Talk — it becomes a proposal you ✅" data-testid={`rig-say-${t.split(' ')[0]}`}>“{t}”</button>)}</p>
    {note ? <p className={`mrg-note ${note.ok ? 'is-ok' : 'is-bad'}`} data-testid="rig-reload-note">{note.ok ? `✅ reloaded in ${(note.ms / 1000).toFixed(1)}s${note.note ? ` · ${note.note}` : ''}` : `✕ reload failed — ${note.err}`}</p> : null}
    <div className="mrg-grid">{d.rows.map((r, i) => { const lv = d.live?.[r.key] || {}; const lm = r.lms; const gguf = String(lm?.fmt || 'gguf').toLowerCase() === 'gguf';
      const inst = lm?.loaded?.[0] || {}; const diff = Object.keys(r.diff || {}); const reloading = (d.reloading || []).includes(r.key) || busy === `reload.${r.key}`;
      return <section key={r.key} className={`mrg-card k-${r.key} ${diff.length ? 'is-diff' : ''}`} style={{ '--i': i }} data-testid={`rig-${r.key}`}>
        <header><span className="mrg-sweep" aria-hidden />{AV[r.key] ? <img src={AV[r.key]} alt="" /> : <i className="mrg-av">🪟</i>}<b>{r.name}</b>{lm?.name ? <small className="mrg-model">{String(lm.name).split('/').pop()}</small> : null}
          <span className={`mrg-st s-${String(lv.state || 'untested').toLowerCase().replace(/\s+/g, '-')}`}>{lv.state || 'UNTESTED'}{lv.lastMs ? ` · ${(lv.lastMs / 1000).toFixed(1)}s` : ''}</span></header>
        {r.load ? <>
          <LoadedNow lm={lm} />
          <div className="mrg-grp"><em className="mrg-lbl">⚙ LOAD <small>reload to apply</small></em>
            {LOAD.map(([f, label, word, tip]) => { const off = !gguf && ['flash', 'kv', 'batch'].includes(f); const cur = inst[f]; const w = r.load[f];
              return <div key={f} className={`mrg-row ${off ? 'is-na' : ''}`} data-tip={off ? `${tip} — not used by ${String(lm?.fmt || '').toUpperCase()} models` : tip}><em>{label}</em>
                <div className="mrg-seg">{(d.loadOptions?.[f] || []).map(v => <button key={v} type="button" className={`${(w ?? cur) === v ? 'active' : ''} ${cur === v ? 'is-cur' : ''}`} disabled={!!busy || off}
                  aria-busy={busy === `${r.key}.load.${f}`} onClick={() => want(r.key, f, v)} data-testid={`rig-${r.key}-load-${f}-${v}`}>{word(v)}</button>)}</div></div>; })}
            {reloading ? <span className="mrg-nxbar is-load" aria-hidden><i /></span> : null}
            <button type="button" className={`m-btn ${diff.length || !inst.id ? 'm-go' : ''} mrg-reload`} disabled={!!busy || reloading || !lm} onClick={() => post(`reload.${r.key}`, { reload: r.key })}
              data-testid={`rig-${r.key}-reload`} data-tip={`Unloads ${r.name} and loads it again with these settings — it is offline for a few seconds. Your tap is the approval.`}>
              {reloading ? `⏳ reloading ${r.name}…` : !inst.id ? `⚡ Load ${r.name}` : diff.length ? `⚡ Reload ${r.name} · ${diff.map(f => `${LOAD.find(x => x[0] === f)?.[1].split(' ').slice(1).join(' ').toLowerCase()} ${LOAD.find(x => x[0] === f)?.[2](r.load[f])}`).join(' · ')}` : `✓ ${r.name} runs these settings`}</button></div></> : null}
        <div className="mrg-grp"><em className="mrg-lbl">📤 SENDS <small>live at once</small></em>
          {FIELDS.filter(([f]) => r[f] !== undefined).map(([f, label, word, tip]) => <div key={f} className="mrg-row" data-tip={tip}><em>{label}</em>
            <div className="mrg-seg">{(d.options[f] || []).map(v => <button key={v} type="button" className={r[f] === v ? 'active' : ''} disabled={!!busy}
              aria-busy={busy === `${r.key}.${f}`} onClick={() => save(r.key, f, v)} data-testid={`rig-${r.key}-${f}-${v}`}>{word(v)}</button>)}</div></div>)}</div>
        <Presets k={r.key} list={d.presets?.[r.key] || []} busy={busy} onAct={preset} />
        {r.key === 'win' ? <NexaRuntime n={d.nexa} busy={busy} onAct={nexa} /> : <code className="mrg-cmd" data-tip="The same load as a terminal command (run it where the model lives)">{r.cmd}</code>}
      </section>; })}</div>
    {err ? <p className="mrg-err">{err}</p> : null}
  </div>;
}

import React, { useState } from 'react';

// 🎛 MODEL-CFG (owner 2026-11-13): one compact control cluster per picked model. It shows ONLY what OpenRouter's live model list says that
// model supports (row.efforts from `reasoning.supported_efforts`, row.knobs from `supported_parameters`, built in backend/launch_cat.knobs_of).
// A model with nothing extra shows a clean "provider defaults" line. Values ride with every request the agent makes (feecat _or_call).
const fmt = (k, v) => (v == null || v === '' ? 'default' : k.kind === 'slider' ? Number(v).toFixed(k.step < 0.1 ? 2 : 1) : String(v));

export function ModelKnobs({ model, effort, onEffort, value, onChange, testid }) {
  const [open, setOpen] = useState(false);
  const knobs = model?.knobs || []; const efforts = model?.efforts || [];
  const set = (key, v) => onChange?.({ ...(value || {}), [key]: v });
  const reset = key => { const n = { ...(value || {}) }; delete n[key]; onChange?.(n); };
  const touched = Object.keys(value || {}).length + (effort ? 1 : 0);
  const name = String(model?.name || model?.id || '').split(':').pop().trim();
  if (!knobs.length && !efforts.length) return <div className="mkn is-plain" data-testid={testid}><b>{name}</b><small>Provider defaults · this model has no extra knobs</small></div>;
  return <div className={`mkn${open ? ' is-open' : ''}`} data-testid={testid}>
    <button type="button" className="mkn-head" onClick={() => setOpen(o => !o)} aria-expanded={open} data-tip="Only the controls this model really supports (read live from OpenRouter)">
      <b>{name}</b><small>{efforts.length ? `effort ${effort || model.defaultEffort || 'default'}` : ''}{efforts.length && knobs.length ? ' · ' : ''}{knobs.length ? `${knobs.length} knob${knobs.length > 1 ? 's' : ''}` : ''}{touched ? ` · ${touched} set` : ''}</small><i aria-hidden="true">{open ? '−' : '+'}</i></button>
    {open ? <div className="mkn-body">
      {efforts.length ? <label className="mkn-row"><span>Reasoning effort</span>
        <select className="m-input" aria-label={`${name} effort`} value={effort || ''} onChange={e => onEffort?.(e.target.value)}><option value="">Provider default{model.defaultEffort ? ` (${model.defaultEffort})` : ''}</option>{efforts.map(e => <option key={e}>{e}</option>)}</select></label> : null}
      {knobs.map(k => { const v = (value || {})[k.key]; return <label key={k.key} className="mkn-row" data-tip={k.help}><span>{k.label}<em className="m-num">{fmt(k, v)}</em></span>
        {k.kind === 'slider' ? <input type="range" min={k.min} max={k.max} step={k.step} value={v ?? k.default} onChange={e => set(k.key, Number(e.target.value))} aria-label={`${name} ${k.label}`} />
          : k.kind === 'choice' ? <select className="m-input" value={v ?? ''} onChange={e => (e.target.value ? set(k.key, e.target.value) : reset(k.key))} aria-label={`${name} ${k.label}`}><option value="">default</option>{k.options.map(o => <option key={o}>{o}</option>)}</select>
          : <input className="m-input" type="number" min={k.min} max={k.max} value={v ?? ''} placeholder={String(k.default)} onChange={e => (e.target.value === '' ? reset(k.key) : set(k.key, Number(e.target.value)))} aria-label={`${name} ${k.label}`} />}
        {v != null ? <button type="button" className="mkn-x" onClick={() => reset(k.key)} aria-label={`Reset ${k.label}`}>reset</button> : null}</label>; })}
    </div> : null}
  </div>;
}

import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { FamilyBadge } from './FamilyBadge';
import { FamilyCrest } from './FamilyCrest';
import '../styles/familyCrest.css';

// ⚒ THE CREST FORGE (owner, 2026-10-22: "badge customizing sucks"; research: Call of Duty's emblem editor — layers you move / scale / rotate /
// flip / colour, a grid, a live canvas, "change shape keeps the adjustments"). FEELESS twist: a crest on a turntable under the family's
// spotlight, a LAYER LIST (Shape · Field · Charge · Frame · Banner · FX), the picked layer's tiles (each tile IS that option on your crest),
// the charge's own scale / rotate / flip, locked tiles with the family's real progress to them, 🎲 roll, Forge / Restyle (cost from HQ).
export const LAYERS = [['shape', 'Shape', 'shape'], ['field', 'Field', 'field'], ['emblem', 'Charge', 'charge'], ['frame', 'Frame', 'frame'], ['banner', 'Banner', 'banner'], ['fx', 'FX', 'fx']];
export const COLOR_PAIRS = [['#d4af37', '#111111'], ['#ff4d6d', '#111111'], ['#15d16a', '#ffd36b'], ['#9b5cff', '#6fd3ff'], ['#ffffff', '#ff4d6d'], ['#ff9f45', '#9b5cff'], ['#7a0f1f', '#d4af37'], ['#1b3a6b', '#ffffff']];
export const LAYER_TIP = {
  shape: 'The shield itself. Changing it keeps the charge’s size, turn and flip.', field: 'How the shield is painted: split, bend, chevron, quarters or stripes in your MAIN + TRIM colours.',
  emblem: 'The drawn charge on the shield. Scale, rotate and flip it — the rarer charges unlock from what the family really did.', frame: 'The metal rim. Gold, blood oath, holo, black card and warlord are earned.',
  banner: 'The ribbon under the shield carries your tag; the motto shows under the crest everywhere.', fx: 'A calm earned effect behind the crest on every card.',
};
// pure: how far a locked option is from unlocking (0–1), or null when the line is a place ('best') / unknown
export function unlockProgress(o, metrics) {
  if (o.ok) return 1;
  if (!o.metric || o.metric === 'best' || !o.min) return null;
  return Math.max(0, Math.min(1, (Number((metrics || {})[o.metric]) || 0) / o.min));
}
// pure: a random crest from the UNLOCKED options only + a listed colour pair; the charge keeps its own adjustments
export function rollBadge(cat, d) {
  const pick = rows => { const ok = (rows || []).filter(o => o.ok); return ok.length ? ok[Math.floor(Math.random() * ok.length)].key : null; };
  const pair = COLOR_PAIRS[Math.floor(Math.random() * COLOR_PAIRS.length)];
  const out = { ...d, c1: pair[0], c2: pair[1] };
  LAYERS.forEach(([k]) => { const v = pick(cat.parts[k]); if (v) out[k] = v; });
  return out;
}
const pct = v => `${Math.round(v * 100)}%`;

export function CrestForge({ mine, owner, addr, sess, costWord, act, busy }) {
  const [cat, setCat] = useState(null); const [d, setD] = useState(null); const [layer, setLayer] = useState('emblem'); const [grid, setGrid] = useState(false);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/crews/badge/catalog?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : null))
    .then(x => { if (on && x) { const b = x.badge || {}; setCat(x); setD(cur => cur || { shape: b.shape, field: b.field, emblem: b.emblem, frame: b.frame, fx: b.fx, banner: b.banner, c1: b.c1 || x.colors[0], c2: b.c2 || x.colors[1], c3: b.c3 || '#ffffff', es: b.es ?? 1, er: b.er ?? 0, ef: !!b.ef, motto: b.motto || '' }); } }).catch(() => {});
    return () => { on = false; }; }, [addr, sess, mine?.badge?.v]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (!cat || !d) return <p className="m-dim crw-hint">opening the crest forge…</p>;
  const prev = { ...d, tag: mine.tag, name: mine.name, ranks: cat.metrics };
  const set = patch => owner && setD(x => ({ ...x, ...patch }));
  const all = Object.values(cat.parts).flat(); const open = all.filter(o => o.ok).length;
  const rows = cat.parts[layer] || [];
  const label = (k, v) => (cat.parts[k] || []).find(o => o.key === v)?.label || v;
  const A = cat.adjust || { es: { min: 0.7, max: 1.3 }, er: { min: -30, max: 30 } };
  const swatches = (k, word) => <span className="cf-sw" key={k}><em>{word}</em>{cat.colors.map(c => <button key={c} type="button" disabled={!owner} className={d[k] === c ? 'active' : ''} style={{ background: c }} onClick={() => set({ [k]: c })} aria-label={`${word} ${c}`} data-tip={`${word} colour`} />)}</span>;
  return <div className="cf" data-testid="badge-builder">
    <section className="cf-stage" aria-label="Your crest">
      <i className="cf-spot" aria-hidden="true" /><i className="cf-floor" aria-hidden="true" /><span className="cf-dust" aria-hidden="true">{[0, 1, 2, 3, 4, 5, 6].map(i => <i key={i} style={{ '--i': i }} />)}</span>
      <header className="cf-hud"><span className="m-label">⚒ CREST FORGE</span><b>{LAYERS.find(l => l[0] === layer)[1].toUpperCase()}</b>
        <button type="button" className={`cf-gridbtn ${grid ? 'active' : ''}`} aria-pressed={grid} onClick={() => setGrid(g => !g)} data-tip="Alignment grid over the shield (like the emblem editor's)" data-testid="cf-grid">▦ Grid</button></header>
      <div className="cf-turn"><FamilyBadge b={prev} size="lg" px={196} grid={grid} chips={false} /></div>
      <p className="cf-open" data-tip="Parts your family has unlocked — every lock reads a tracked number"><em><b>{open}</b>/{all.length} parts unlocked</em><span><i style={{ transform: `scaleX(${open / Math.max(1, all.length)})` }} /></span></p>
      <p className="cf-met">{Object.entries(cat.metrics).filter(([k]) => cat.metricWords[k]).map(([k, v], i) => <span key={k} style={{ '--i': i }} data-tip={cat.metricWords[k]}><b>{v ?? '—'}</b><small>{cat.metricWords[k]}</small></span>)}</p>
      {owner ? <div className="cf-acts"><button type="button" className="m-btn" onClick={() => setD(x => rollBadge(cat, x))} data-tip="A random crest from your unlocked parts" data-testid="fbb-roll">🎲 Roll</button>
        <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('/api/reputation/crews/badge', { badge: d }, cat.built ? '🌹 crest restyled' : '🌹 crest forged', cat.built && !cat.free ? 'badge' : undefined)} data-tip={cat.built ? 'Save the new look — every family sees it on the board, podium, cards and chips' : 'The first crest is free'} data-testid="fbb-save">
          {cat.built ? `Restyle · ${cat.free ? 'free' : costWord || `$${cat.restyleUsd}`}` : 'Forge it · free'}</button></div> : <p className="m-dim crw-hint">Only the Don forges the crest — every unlock comes from what the family really did.</p>}
    </section>
    <section className="cf-side">
      <nav className="cf-layers" role="tablist" aria-label="Crest layers">{LAYERS.map(([k, w, only], i) => { const rs = cat.parts[k] || []; const ok = rs.filter(o => o.ok).length;
        return <button key={k} type="button" role="tab" aria-selected={layer === k} className={`cf-layer ${layer === k ? 'active' : ''}`} style={{ '--i': i }} onClick={() => setLayer(k)} data-tip={LAYER_TIP[k]} data-testid={`fbb-tab-${k}`}>
          <span className="cf-lthumb"><FamilyCrest b={prev} px={30} banner={only === 'banner'} only={only === 'fx' ? undefined : only} sheen={false} title={w} /></span>
          <b>{w}</b><small>{label(k, d[k])}</small><em>{ok}/{rs.length}</em></button>; })}</nav>
      <div className="cf-ctl" key={layer}>
        <div className="cf-tiles">{rows.map((o, i) => { const pr = unlockProgress(o, cat.metrics); const look = { ...prev, [layer]: o.key };
          return <button key={o.key} type="button" disabled={!o.ok || !owner} style={{ '--i': i }} className={`cf-tile ${d[layer] === o.key ? 'active' : ''} ${o.ok ? '' : 'is-locked'}`}
            onClick={() => set({ [layer]: o.key })} data-tip={o.ok ? o.label : `🔒 ${o.need}`} data-testid={`fbb-${layer}-${o.key}`}>
            <span className="cf-mini">{layer === 'fx' ? <FamilyBadge b={look} size="md" px={58} chips={false} /> : <FamilyCrest b={look} px={58} banner={layer === 'banner'} sheen={false} title={o.label} />}</span><small>{o.label}</small>
            {o.ok ? null : <><i className="cf-lock" aria-hidden="true">🔒</i>{pr != null ? <span className="cf-prog"><b style={{ transform: `scaleX(${Math.max(0.04, pr)})` }} /></span> : null}<em>{o.need}</em></>}</button>; })}</div>
        {layer === 'field' ? <div className="cf-colors">
          <div className="cf-pairs">{COLOR_PAIRS.filter(p => p.every(c => cat.colors.includes(c))).map(([a1, a2]) => <button key={a1 + a2} type="button" disabled={!owner} className={d.c1 === a1 && d.c2 === a2 ? 'active' : ''} onClick={() => set({ c1: a1, c2: a2 })} aria-label={`colours ${a1} and ${a2}`} data-tip="A family colour pair"><i style={{ background: a1 }} /><i style={{ background: a2 }} /></button>)}</div>
          {swatches('c1', 'MAIN')}{swatches('c2', 'TRIM')}</div> : null}
        {layer === 'emblem' ? <div className="cf-adjust" data-testid="cf-adjust">
          {swatches('c3', 'ACCENT')}
          <label className="cf-slide" data-tip="Scale the charge (70–130 %)"><em>SCALE</em><input type="range" min={A.es.min} max={A.es.max} step="0.01" value={d.es} disabled={!owner} onChange={e => set({ es: +e.target.value })} aria-label="Charge scale" data-testid="cf-scale" /><b>{pct(d.es)}</b></label>
          <label className="cf-slide" data-tip="Turn the charge (−30° to 30°)"><em>ROTATE</em><input type="range" min={A.er.min} max={A.er.max} step="1" value={d.er} disabled={!owner} onChange={e => set({ er: +e.target.value })} aria-label="Charge rotation" data-testid="cf-rotate" /><b>{d.er}°</b></label>
          <span className="cf-row"><button type="button" className={`m-btn ${d.ef ? 'active' : ''}`} aria-pressed={d.ef} disabled={!owner} onClick={() => set({ ef: !d.ef })} data-tip="Mirror the charge" data-testid="cf-flip">⇋ Flip</button>
            <button type="button" className="m-btn" disabled={!owner} onClick={() => set({ es: 1, er: 0, ef: false })} data-tip="Back to centre, 100 %, no turn">↺ Reset</button></span>
          <small className="cf-note">Change the shape — the charge keeps its size, turn and flip.</small></div> : null}
        {layer === 'banner' ? <div className="cf-motto"><input className="m-input" value={d.motto} maxLength={cat.mottoMax} disabled={!owner} placeholder="Famiglia prima di tutto" onChange={e => set({ motto: e.target.value })} aria-label="Family motto" />
          <small>{d.motto.length}/{cat.mottoMax} · the ribbon carries [{mine.tag}], the motto shows under the crest on every card</small></div> : null}
      </div>
    </section>
  </div>;
}

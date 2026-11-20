import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Brain, Film, LayoutTemplate, Loader2, Pencil, Sparkles, Star, Trash2 } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { PLATS, describe } from '../../lib/clipLook';
import { TplSample } from './ClipCaption';

// 🎨 Slice 29 add-on (owner 2026-11-20: "should be able to set edit formats and templates … i was speaking of the clip farming too, help them
// understand better templating"). A TEMPLATE is a whole look saved by name: caption style, font, accent, safe area, transition, effects, and which
// files it is for. The farm makes every new clip in one (the owner's pick, or the minds pick one per clip, all different, with a why); the
// defaults below decide it for every new run, per format and per platform. One tap puts a template on a clip, its run or the week: the clips
// re-render on this machine ($0). Nothing here posts.
const FMTS = [['story', '9:16'], ['feed', '1:1'], ['wide', '16:9']];
const FMT_NAME = { story: '9:16', feed: '1:1', wide: '16:9' };
const fileOf = (f, piece, fmt) => (f?.studio?.files || []).find(x => x.piece === piece && x.format === fmt && x.url && !x.error);

function Pick({ id, label, value, opts, onPick, none, busy, tip }) {
  return <label className="cst-def" data-tip={tip}><span className="m-label">{label}</span>
    <select className="m-input" value={value || ''} disabled={busy} onChange={e => onPick(e.target.value)} data-testid={`cst-def-${id}`}>
      {none ? <option value={none[0]}>{none[1]}</option> : null}{opts.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>;
}

export default function ClipTemplates({ clips, templates, busy, call, onEdit }) {
  const list = templates?.list || []; const d = templates?.defaults || {}; const mine = list.filter(x => !x.builtin); const modern = list.filter(x => x.builtin && !x.legacy);
  const older = list.filter(x => x.legacy); const usable = [...modern, ...mine];
  const open = clips.filter(f => !f.posted); const [job, setJob] = useState(''); const f = open.find(x => x.id === job) || open[0] || null;
  const [tick, setTick] = useState(0); const [ask, setAsk] = useState('');
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setTick(x => x + 1); }, 650); return () => clearInterval(t); }, []);
  const img = useMemo(() => { const c = fileOf(f, 'image', 'story'); return c ? apiUrl(c.url) : ''; }, [f]);
  const inUse = useMemo(() => { const m = {}; clips.forEach(x => { const id = x.studio.tpl?.id; if (id) m[id] = (m[id] || 0) + 1; }); return m; }, [clips]);
  const setDef = (key, tpl) => call('def', '/template/default', { key, tpl });
  const apply = (tpl, scope) => call(`apply-${tpl}`, '/template/apply', { tpl, ...(scope === 'clip' ? { job: f.id } : scope === 'run' ? { run: f.studio.clip.run } : { week: true }) });
  const planned = clips.some(x => x.studio.slot && !x.posted);
  const card = (x, i) => <motion.article key={x.id} className={`cst-tpl${x.builtin ? '' : ' is-mine'}`} style={{ '--i': Math.min(i, 12) }} initial={{ y: 6, opacity: 0 }} animate={{ y: 0, opacity: 1 }} data-testid={`cst-tpl-${x.id}`}>
    <TplSample look={x.look} img={img} tick={tick + i} hook={f?.studio?.hook || undefined} />
    <div className="cst-tpl-b">
      <header><b>{x.name}</b>{inUse[x.id] ? <em className="m-num" data-tip="Clips in this template now">{inUse[x.id]}</em> : null}</header>
      <small className="cst-tpl-by">{x.builtin ? 'FEELESS' : x.by === 'minds' ? `the minds${x.mind ? ` · ${x.mind}` : ''}` : 'yours'} · {(x.fmts || []).length === 3 ? 'every format' : (x.fmts || []).map(k => FMT_NAME[k]).join(' + ')}</small>
      <small className="cst-tpl-d">{x.describe || describe(x.look)}</small>
      {x.why ? <small className="cst-tpl-why">{x.why}</small> : null}
      <div className="cst-tpl-act">
        <span className="m-label">PUT ON</span>
        <button type="button" className="m-btn" disabled={!f || !!busy} onClick={() => apply(x.id, 'clip')} data-tip={f ? `PoC #${f.n}: re-rendered, $0` : 'No clip yet'} data-testid={`cst-tpl-apply-${x.id}-clip`}>This clip</button>
        <button type="button" className="m-btn" disabled={!f || !!busy} onClick={() => apply(x.id, 'run')} data-tip="Every clip from the same upload, each nudged so no two look the same" data-testid={`cst-tpl-apply-${x.id}-run`}>Its run</button>
        <button type="button" className="m-btn" disabled={!planned || !!busy} onClick={() => apply(x.id, 'week')} data-tip={planned ? 'Every clip planned this week' : 'No clip is planned yet'} data-testid={`cst-tpl-apply-${x.id}-week`}>The week</button>
        <button type="button" className="m-btn cst-ic" onClick={() => onEdit(x)} aria-label={`Edit ${x.name}`} data-tip={x.builtin ? 'Open it in the editor: change it, save it under your own name' : 'Open it in the editor, change it, Update'} data-testid={`cst-tpl-edit-${x.id}`}><Pencil size={12} /></button>
        {!x.builtin ? <button type="button" className="m-btn cst-ic" disabled={!!busy} onClick={() => call('del', '/template/delete', { id: x.id })} aria-label={`Delete ${x.name}`} data-tip="Delete it (clips keep their look)" data-testid={`cst-tpl-del-${x.id}`}><Trash2 size={12} /></button> : null}
      </div>
    </div>
  </motion.article>;
  return <div className="cst-tpls" data-testid="cst-templates">
    <p className="cst-tpl-intro"><LayoutTemplate size={14} aria-hidden="true" /><span><b>A template is a whole look saved by name</b>: caption style, font, accent, where captions sit (never over a face),
      transition, effects and which files it is for. <b>The clip farm makes every new clip in one.</b> Put one on a clip, a whole run or the week in one tap: it re-renders on this machine, $0.</span></p>

    <section className="cst-defs" aria-label="Defaults">
      <header><Star size={13} aria-hidden="true" /><b>Defaults</b><small>what the farm uses for every new run</small></header>
      <div className="cst-defs-g">
        <Pick id="farm" label="NEW RUNS START IN" value={d.farm} opts={usable} none={['minds', 'Minds pick one per clip']} onPick={v => setDef('farm', v)} busy={!!busy}
          tip="Minds pick: each clip gets the template that fits its mood and hook, all different, with a why on its tile" />
        {FMTS.map(([k, l]) => <Pick key={k} id={k} label={`${l} FILE`} value={d[k]} opts={usable} none={['', 'Same as the clip']} onPick={v => setDef(k, v)} busy={!!busy} tip={`Every ${l} file in this template, whatever the run picked`} />)}
      </div>
      <div className="cst-defs-g is-plats">
        {PLATS.map(([k, l]) => <Pick key={k} id={k} label={`${l.toUpperCase()} · ${FMT_NAME[templates?.platFmt?.[k] || 'story']}`} value={d[k]} opts={usable} none={['', 'No default']} onPick={v => setDef(k, v)} busy={!!busy}
          tip={`${l} posts the ${FMT_NAME[templates?.platFmt?.[k] || 'story']} file: its template goes on that file (a format's own default wins)`} />)}
      </div>
      <small className="cst-defs-now" data-testid="cst-defs-now">{Object.keys(templates?.inForce || {}).length ? `In force: ${Object.entries(templates.inForce).map(([k, id]) => `${FMT_NAME[k]} → ${(list.find(x => x.id === id) || {}).name || id}`).join(' · ')}` : 'No per-file default: each file uses its clip\'s template.'}</small>
    </section>

    <div className="cst-bar cst-tpl-bar">
      <span className="m-label">PREVIEW ON</span>
      <select className="m-input cst-sel" value={f?.id || ''} onChange={e => setJob(e.target.value)} aria-label="Clip the templates are shown on and put on" data-testid="cst-tpl-clip">
        {open.map(x => <option key={x.id} value={x.id}>#{x.n} {x.studio.hook}{x.studio.tpl ? ` · ${x.studio.tpl.name}` : ''}</option>)}</select>
      <button type="button" className="m-btn m-go" disabled={!f || !!busy} onClick={() => call('tminds', '/template/minds', { run: f.studio.clip.run })} data-tip="The minds pick a template per clip of this run, all different, each with a why; they re-render" data-testid="cst-tpl-minds-run">
        {busy === 'tminds' ? <Loader2 size={13} className="cst-spin" /> : <Brain size={13} />} Minds pick for its run</button>
      {planned ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => call('tminds', '/template/minds', { week: true })} data-testid="cst-tpl-minds-week"><Brain size={13} /> …for the week</button> : null}
    </div>

    <div className="cst-tpl-grid" data-testid="cst-tpl-grid">{usable.map(card)}</div>
    {older.length ? <details className="cst-tpl-older"><summary>Older looks ({older.length}): the first Slice 29 presets</summary><div className="cst-tpl-grid">{older.map((x, i) => card(x, i + usable.length))}</div></details> : null}

    <form className="cst-tpl-design" onSubmit={e => { e.preventDefault(); call('tdesign', '/template/mind', { ask }); setAsk(''); }} aria-label="The minds design a template">
      <Sparkles size={13} aria-hidden="true" /><input className="m-input" value={ask} onChange={e => setAsk(e.target.value)} placeholder="Ask the minds for a new template: late-night calm, loud sports, finance numbers…" aria-label="What the new template is for" data-testid="cst-tpl-ask" />
      <button type="submit" className="m-btn" disabled={!!busy} data-tip="The lead mind designs a new template unlike the ones here and saves it under its own name" data-testid="cst-tpl-design">{busy === 'tdesign' ? <Loader2 size={13} className="cst-spin" /> : <Brain size={13} />} Minds design one</button>
      <small><Film size={11} aria-hidden="true" /> Or make one in Edit and tap “Save as template”.</small>
    </form>
  </div>;
}

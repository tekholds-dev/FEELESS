import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import { AttnExplained } from './CompExplain';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/forge2.css';

// 🏗 COMPAI · the model forge (owner 2026-11-12: "elite dev's dash … live view of whatever it's learning … one model: COMP Flagship v1.02").
// ONE model, built in VERSIONS: every build is the family name + the next version, and continues from the newest version with the same shape
// (its weights + tokenizer), so v1.01 starts where v1.00 ended. A real transformer (backend/model_forge.py, hand-written backprop, AdamW) trains
// on THIS Mac from the owner's own text. Nothing is rented.
// 🎨 Redone 2026-11-14 (owner: "redo COMP", slice 2): the answer first — how much better than guessing the newest version is and what the next
// build will be, with ONE button — then what it is made of (one bar: embeddings + a segment per block), what it reads, ONE live run panel with
// ONE loss chart, and the versions as a table. The nine-row control wall, the guardrail form and the engine readouts fold away; nothing pulses.
const SEG = { tok: [['char', 'Characters', 'One token per letter: small vocabulary, learns spelling first'], ['bpe', 'Word pieces', 'Byte-pair pieces trained on your text: words in fewer tokens']],
  vocab: [256, 512, 1024, 2048], d: [32, 64, 128, 192, 256, 384], heads: [1, 2, 3, 4, 6, 8], ctx: [32, 64, 128, 256], steps: [200, 600, 1000, 2000, 5000], batch: [8, 16, 32],
  lr: [3e-4, 6e-4, 1e-3, 3e-3], maxChars: [200, 400, 600, 1000] };
const fmt = n => (n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${Math.round(n || 0)}`);
const secs = s => (s >= 3600 ? `${(s / 3600).toFixed(1)} h` : s >= 60 ? `${Math.round(s / 60)} min` : `${Math.max(1, Math.round(s || 0))} s`);
const bytes = b => (b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : b >= 1e3 ? `${(b / 1e3).toFixed(1)} KB` : `${b} B`);
const vnum = v => Number(String(v || '').replace(/^v/, '')) || 0;
const gain = c => (c?.perplexity ? c.baselinePerplexity / c.perplexity : 0);   // × better than guessing at random
const LIVE = new Set(['tokenizing', 'training']);
const SHAPE = ['d', 'layers', 'heads', 'ctx', 'tok'];
const LABS = [['RMSNorm', 'LLaMA, Mistral', 'Normalises by size only: a bit faster, same quality'], ['SwiGLU', 'LLaMA, PaLM', 'A gated MLP: better loss for the same compute'],
  ['RoPE', 'LLaMA, Qwen', 'Position by rotation: handles longer text'], ['GQA', 'LLaMA 3, Mistral', 'Heads share keys and values: less memory when it answers']];
const tipStyle = { background: 'var(--m-surface)', border: '1px solid var(--m-line-hi)', borderRadius: 8, fontSize: 11, color: 'var(--m-text)' };
const axis = { fontSize: 10, fill: 'var(--m-dim)' };
function Big({ v, f = fmt }) { const n = useCountUp(Number(v) || 0); return <b className="m-num">{f(n)}</b>; }
const show = t => t.replace(/\n/g, '⏎').replace(/ /g, '·');

function Seg({ label, k, opts, cfg, set, tip, show: sh = x => x, ok = () => true }) {
  return <div className="frg-field" data-tip={tip}><small className="m-label">{label}</small>
    <div className="m-seg" role="radiogroup" aria-label={label}>{opts.map(o => { const [v, l, t] = Array.isArray(o) ? o : [o, sh(o)]; const can = ok(v);
      return <button key={v} type="button" role="radio" aria-checked={cfg[k] === v} className={cfg[k] === v ? 'active' : ''} disabled={!can} data-tip={t}
        onClick={() => set({ ...cfg, [k]: v })} data-testid={`mlf-${k}-${v}`}>{l}</button>; })}</div></div>;
}

function Chips({ label, list, onChange, tip, testid }) {
  const [t, setT] = useState('');
  const add = () => { const v = t.trim(); if (v && !list.includes(v)) onChange([...list, v].slice(0, 30)); setT(''); };
  return <div className="frg-field" data-tip={tip}><small className="m-label">{label}</small>
    <div className="frg-chips">{list.map(w => <button key={w} type="button" className="m-chip" onClick={() => onChange(list.filter(x => x !== w))} data-tip="Click to remove">{w} ✕</button>)}
      <input className="m-input" value={t} maxLength={60} onChange={e => setT(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} placeholder="add + Enter" aria-label={`Add to ${label}`} data-testid={testid} /></div></div>;
}

// 🧱 WHAT IT IS MADE OF: one bar of where its numbers live (embeddings, then one segment per block, then the final norm) + the shape in a line
function Anatomy({ cfg, sp }) {
  const p = sp?.params || {}; const total = Math.max(1, (p.embed || 0) + (p.position || 0) + (p.per_block || 0) * cfg.layers + (p.final_norm || 0));
  const w = n => `${Math.max(1.5, ((n || 0) / total) * 100)}%`;
  return <div className="frg-anat" data-testid="mlf-stack">
    <div className="frg-anat-bar" role="img" aria-label={`${cfg.layers} blocks`}>
      <i className="frg-emb" style={{ width: w((p.embed || 0) + (p.position || 0)) }} data-tip={`Embeddings: ${fmt(p.embed)} for the tokens + ${fmt(p.position)} for positions`} />
      {Array.from({ length: cfg.layers }).map((_, i) => <i key={i} className="frg-blk" style={{ width: w(p.per_block), '--i': i }} data-tip={`Block ${i + 1}: ${cfg.heads}-head attention + MLP ${cfg.d}→${cfg.d * 4}→${cfg.d} · ${fmt(p.per_block)} numbers`} />)}
      <i className="frg-nrm" style={{ width: w(p.final_norm) }} data-tip={`Final norm: ${fmt(p.final_norm)}`} /></div>
    <ul className="c2-key"><li style={{ '--c': 'var(--frg-emb)' }}><i />embeddings {fmt((p.embed || 0) + (p.position || 0))}</li><li style={{ '--c': 'var(--m-accent)' }}><i />{cfg.layers} blocks × {fmt(p.per_block)}</li></ul>
    <p className="frg-shape"><b>{cfg.layers}</b> blocks · <b>{cfg.heads}</b> heads · width <b>{cfg.d}</b> · sees <b>{cfg.ctx}</b> tokens · {cfg.tok === 'bpe' ? <><b>{cfg.vocab}</b> word pieces</> : 'one token per letter'}</p>
  </div>;
}

function Learning({ job }) {   // WHAT it learns: its own words at each checkpoint + its top-5 guesses for the next token + where it looks
  const s = job.samples || []; const pk = job.peek; if (!s.length && !pk) return null; const now = s[s.length - 1];
  return <div className="frg-learn" data-testid="mlf-learn">
    {now ? <div className="frg-says"><small className="m-label">WHAT IT WRITES NOW · STEP {now.step}</small><pre key={now.step}>{now.text || '…'}</pre>
      <ol className="frg-past">{s.slice(0, -1).reverse().slice(0, 3).map(x => <li key={x.step}><em className="m-num">{x.step}</em>{x.text.slice(0, 90)}</li>)}</ol></div> : null}
    {pk ? <div className="frg-top" data-testid="mlf-top"><small className="m-label">ITS TOP 5 GUESSES FOR THE NEXT TOKEN</small>{pk.top.map((t, i) => <span key={`${t.tok}${i}`} data-tip={`${(t.p * 100).toFixed(1)}% sure the next token is “${show(t.tok)}”`}>
      <code>{show(t.tok)}</code><i className="c2-bar"><u style={{ transform: `scaleX(${Math.max(0.02, t.p)})` }} /></i><b className="m-num">{(t.p * 100).toFixed(1)}%</b></span>)}</div> : null}
    <AttnExplained peek={pk} /></div>;
}

function Versions({ built, pick, setPick }) {   // the version table + the scaling chart (parameters vs held-out loss: lower right = bigger and better)
  const best = Math.min(...built.map(j => j.card.val ?? 99)); const top = Math.max(1, ...built.map(j => gain(j.card)));
  const pts = built.map(j => ({ x: j.card.spec?.paramsTotal || 0, y: j.card.val, z: j.card.totalSteps || j.card.steps, v: j.version || j.card.name }));
  return <div className="frg-vers">
    <ul className="frg-vtab" role="listbox" aria-label="Versions">{built.map((j, i) => <li key={j.id} style={{ '--i': i }}><button type="button" role="option" aria-selected={pick === j.id} className={pick === j.id ? 'is-on' : ''} onClick={() => setPick(j.id)} data-testid={`mlf-model-${j.id}`}
      data-tip={`Perplexity ${j.card.perplexity} (guessing at random = ${j.card.baselinePerplexity}) · held-out loss ${j.card.val} · built in ${secs(j.card.seconds)}`}>
      <span className="frg-vname"><b>{j.version || j.card.name}</b>{j.card.val === best ? <em className="m-chip ok">BEST</em> : null}{j.card.base ? <small>from {j.card.base}</small> : null}</span>
      <span className="frg-vfact m-num">{fmt(j.card.spec?.paramsTotal)}<small>params</small></span><span className="frg-vfact m-num">{fmt(j.card.totalSteps || j.card.steps)}<small>steps</small></span>
      <i className="c2-bar"><u style={{ transform: `scaleX(${Math.max(0.02, gain(j.card) / top)})` }} /></i><b className="m-num frg-vx">{gain(j.card).toFixed(1)}×</b></button></li>)}</ul>
    {pts.length > 1 ? <div className="frg-chart" data-tip="Every version: size vs held-out loss. Lower = better. Bigger dot = more training steps"><small className="m-label">SIZE VS HELD-OUT LOSS</small><ResponsiveContainer width="100%" height={170}><ScatterChart margin={{ top: 8, right: 10, bottom: 0, left: -14 }}>
      <CartesianGrid stroke="var(--m-line)" strokeDasharray="2 4" /><XAxis dataKey="x" type="number" scale="log" domain={['auto', 'auto']} tickFormatter={fmt} tick={axis} name="params" /><YAxis dataKey="y" type="number" domain={['auto', 'auto']} tick={axis} name="held-out" />
      <ZAxis dataKey="z" range={[40, 220]} name="steps" /><Tooltip contentStyle={tipStyle} formatter={(v, n) => (n === 'params' ? fmt(v) : v)} /><Scatter data={pts} fill="var(--m-accent)" isAnimationActive={false} /></ScatterChart></ResponsiveContainer></div> : null}
  </div>;
}

function Files({ job, folder, call, setErr }) {   // WHERE it lives: this version's own files on this Mac, each one downloadable
  const [got, setGot] = useState('');
  const save = async n => { try { const r = await call(`/admin/model-lab/forge/${job.id}/file/${n}`); const raw = Uint8Array.from(atob(r.b64), ch => ch.charCodeAt(0));
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([raw])); a.download = `${job.id}-${n}`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); setGot(n); } catch (e) { setErr(e.message); } };
  return <div className="frg-files" data-testid="mlf-files"><code className="frg-path" data-tip="The folder on this Mac">{folder}/{job.id}/</code>
    <ul>{(job.files || []).map(f => <li key={f.name}><span><b>{f.name}</b><small>{f.say}</small></span><em className="m-num">{bytes(f.bytes)}</em>
      <button type="button" className="m-btn" onClick={() => save(f.name)} data-tip={`Download ${f.name}`} data-testid={`mlf-file-${f.name}`}>{got === f.name ? '✓' : '⬇'}</button></li>)}</ul></div>;
}

function Rails({ job, call, setErr }) {   // the guardrail suite: every rule tripped on purpose, plus one real answer through them
  const [r, setR] = useState(null); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); try { setR(await call(`/admin/model-lab/forge/${job.id}/railtest`, { method: 'POST' })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  useEffect(() => { setR(null); }, [job.id]);
  return <div className="frg-rails" data-testid="mlf-rails"><div className="frg-rails-go"><button type="button" className="m-btn" disabled={busy} onClick={run} data-tip="Trips every guardrail of this version on purpose and checks it held" data-testid="mlf-railtest">{busy ? 'Testing…' : 'Test the guardrails'}</button>
    {r ? <b className={`m-num frg-score${r.passed === r.total ? ' is-ok' : ' is-bad'}`}>{r.passed}/{r.total} held</b> : <small>trips each rule on purpose</small>}</div>
    {r ? <ul>{r.tests.map(t => <li key={t.rule + t.test} className={t.pass ? 'is-ok' : 'is-bad'} data-tip={`It answered: ${t.got}`}><i>{t.pass ? '✓' : '✕'}</i><b>{t.rule}</b><small>{t.test}</small></li>)}</ul> : null}</div>;
}

export function ModelForge({ call, family }) {
  const [f, setF] = useState(null); const [err, setErr] = useState(''); const [cfg, setCfg] = useState(null); const [sp, setSp] = useState(null);
  const [rails, setRails] = useState(null); const [extra, setExtra] = useState(''); const [src, setSrc] = useState(null); const [job, setJob] = useState(null); const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState(null); const [q, setQ] = useState('### PoW · won · '); const [temp, setTemp] = useState(0.8); const [ans, setAns] = useState(null); const [cont, setCont] = useState(true);
  const load = useCallback(() => (!call ? Promise.resolve(setErr('Sign in as the owner to build a model.')) : call('/admin/model-lab/forge').then(x => {
    setF(x); setErr(''); setCfg(c => c || { ...(x.presets.flagship || x.presets.nano), preset: x.presets.flagship ? 'flagship' : 'nano' }); setRails(r => r || x.rails); setSrc(s => s || (x.sources || []).map(y => y.k));
    const run = x.jobs.find(j => j.id === x.running) || null; setJob(j => run || (j && x.jobs.find(y => y.id === j.id)) || x.jobs[0] || null);
    setPick(p => p || x.jobs.find(j => j.card)?.id || null);
  }).catch(e => setErr(e.message))), [call]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {   // specs follow the design (debounced: one read after the clicks settle)
    if (!cfg || !call) return undefined; const t = setTimeout(() => call('/admin/model-lab/forge/spec', { method: 'POST', body: JSON.stringify({ cfg, extra, sources: src || [] }) }).then(setSp).catch(e => setErr(e.message)), 250);
    return () => clearTimeout(t);
  }, [cfg, extra, src, call]);
  const live = job && LIVE.has(job.status); const timer = useRef(null);
  useEffect(() => {   // a running build is read every 1.5 s until it ends, then the list refreshes once
    if (!live) return undefined;
    timer.current = setInterval(() => call(`/admin/model-lab/forge/${job.id}`).then(j => { setJob(j); if (!LIVE.has(j.status)) { load(); setPick(j.card ? j.id : null); } }).catch(() => {}), 1500);
    return () => clearInterval(timer.current);
  }, [live, job?.id, call, load]);
  const versions = useMemo(() => (f?.jobs || []).filter(j => j.card && j.version).sort((a, b) => vnum(b.version) - vnum(a.version)), [f]);
  const base = useMemo(() => (cfg ? versions.find(j => SHAPE.every(k => j.card.cfg?.[k] === cfg[k])) : null), [versions, cfg]);
  const build = async () => { setBusy(true); setErr(''); try { const r = await call('/admin/model-lab/forge/build', { method: 'POST', body: JSON.stringify({ cfg, rails, extra, sources: src || [], cont }) }); setJob({ id: r.id, version: r.version, base: r.base, status: 'tokenizing', history: [], steps: cfg.steps, spec: r.spec }); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const stop = () => call(`/admin/model-lab/forge/${job.id}/stop`, { method: 'POST' }).catch(e => setErr(e.message));
  const ask = async () => { setBusy(true); try { setAns(await call(`/admin/model-lab/forge/${pick}/ask`, { method: 'POST', body: JSON.stringify({ prompt: q, temperature: temp, max_new: 220 }) })); setErr(''); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (!f || !cfg || !rails || !src) return <p className="mlb-none">{err ? `⚠ ${err}` : 'Opening the forge…'}</p>;
  const preset = k => setCfg({ ...f.presets[k], preset: k }); const set = c => setCfg({ ...c, preset: 'custom' });
  const pctCap = sp ? Math.min(1, sp.paramsTotal / f.limits.params) : 0; const built = f.jobs.filter(j => j.card);
  const board = versions.length ? versions : built; const picked = built.find(j => j.id === pick); const newest = board[0];
  const famName = family || f.family?.name || 'COMP Flagship'; const nextV = f.next || 'v1.00';
  const chart = (job?.history || []).map(([s, l, v, lr, g]) => ({ s, train: l, val: v, lr, g })); const lastPt = chart[chart.length - 1] || {};
  const srcChars = (f.sources || []).filter(s => src.includes(s.k)).reduce((a, s) => a + s.chars, 0); const srcTop = Math.max(1, ...(f.sources || []).map(s => s.chars));
  const phase = live ? 'train' : job?.status === 'failed' ? 'fail' : 'idle';
  return <div className="frg" data-testid="model-forge">
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}

    <section className="c2-hero frg-hero m-card" data-testid="frg-hero">
      <div className="c2-big">
        <small className="m-label">{famName.toUpperCase()} · {newest ? `NEWEST ${newest.version || newest.card.name}` : 'NOT BUILT YET'}</small>
        <span className="c2-pct">{newest ? <Big v={gain(newest.card)} f={n => `${n.toFixed(1)}×`} /> : <b className="m-num">—</b>}</span>
        <span className="c2-sub">{newest ? 'better than guessing at its next word, on text it never trained on' : 'press Train to build its first version'}</span>
        {newest ? <span className="c2-vs" data-tip="Held-out loss: how surprised it is by text it never trained on (lower = better)">{fmt(newest.card.spec?.paramsTotal)} params · {fmt(newest.card.totalSteps || newest.card.steps)} steps · loss {newest.card.val}</span> : null}
      </div>
      <div className="frg-next">
        <small className="m-label">NEXT BUILD · {nextV}</small>
        <div className="m-seg frg-presets" role="radiogroup" aria-label="Size">{Object.entries(f.presets).map(([k, p]) => <button key={k} type="button" role="radio" aria-checked={cfg.preset === k} className={cfg.preset === k ? 'active' : ''} onClick={() => preset(k)} data-tip={`${p.layers} blocks · width ${p.d} · ${p.steps} steps`} data-testid={`mlf-preset-${k}`}>{p.name}</button>)}
          {cfg.preset === 'custom' ? <button type="button" role="radio" aria-checked className="active" disabled data-tip="You changed a setting under Fine-tune the design">Custom</button> : null}</div>
        {sp ? <div className="c2-facts frg-facts" data-testid="mlf-specs">
          <span data-tip={`Parameters: every number it learns. This Mac's cap is ${fmt(f.limits.params)}`}><small>SIZE · PARAMETERS</small><Big v={sp.paramsTotal} /><i className="c2-prog"><u style={{ transform: `scaleX(${Math.max(0.02, pctCap)})` }} /></i><em>{Math.round(pctCap * 100)}% of this Mac's cap</em></span>
          <span data-tip="Estimated on this Mac's measured speed"><small>BUILD TIME</small><b className="m-num">≈ {secs(sp.estSec)}</b><em>{sp.trainMb} MB memory</em></span>
          <span data-tip="Tokens of your text per parameter. Big models want ~20; below 1 it mostly learns your voice and repeats it"><small>DATA PER PARAMETER</small><b className={`m-num${sp.tokensPerParam < 1 ? ' is-low' : ''}`}>{sp.tokensPerParam}</b><em>reads it {sp.epochs}×</em></span>
        </div> : <p className="mlb-none">Reading the specs…</p>}
        {sp ? <p className={`c2-verdict${sp.tooBig ? ' is-bad' : ''}`}>{sp.verdict}</p> : null}
        <div className="c2-go">
          <button type="button" className="m-btn m-go" disabled={busy || live || sp?.tooBig} onClick={build} data-tip="Starts the build as its own process on this Mac, one at a time; the site keeps its speed" data-testid="mlf-build">Train {famName} {nextV}</button>
          {base ? <label className="m-toggle" data-tip={`On: ${nextV} starts from ${base.version}'s weights and tokenizer (${fmt(base.card.totalSteps || base.card.steps)} steps already learned). Off: it starts from random numbers`}><input type="checkbox" checked={cont} onChange={e => setCont(e.target.checked)} data-testid="mlf-cont" /> Continue from {base.version}</label>
            : <small className="frg-hint">{versions.length ? 'No version with this shape yet: it starts fresh' : 'The first version: it starts fresh'}</small>}
          {live ? <button type="button" className="m-btn" onClick={stop} data-tip="Ends at the next step and keeps the weights it reached" data-testid="mlf-stop">Stop</button> : null}
        </div>
      </div>
    </section>

    {job ? <section className={`c2-card c2-train m-card frg-run is-${phase}`} data-testid="mlf-run">
      <header className="c2-train-head">
        <span className="c2-state"><i className={live ? 'is-on' : ''} aria-hidden="true" />{live ? 'LEARNING LIVE' : job.status === 'failed' ? 'Build failed' : job.status === 'stopped' ? 'Stopped' : 'LAST BUILD'} · {job.version || job.name || job.id}{job.base ? <small>from {job.base}</small> : null}</span>
        <b className="m-num">{job.step || 0}/{job.steps} <small>steps</small></b>
        <i className="c2-prog" data-tip={`${job.step || 0} of ${job.steps} steps`}><u style={{ transform: `scaleX(${Math.max(0.02, job.steps ? (job.step || 0) / job.steps : 0)})` }} /></i>
        <span className="c2-loss" data-tip="How surprised it still is by your text (lower = better)">loss <b className="m-num">{job.loss ?? '—'}</b></span>
      </header>
      <div className="c2-facts frg-runfacts">
        <span data-tip="The same, on text it never trained on: the honest number"><small>HELD-OUT LOSS</small><b className="m-num">{job.val ?? '—'}</b></span>
        <span><small>SPEED</small><b className="m-num">{job.tps ? fmt(job.tps) : '—'}</b><em>tokens / s</em></span>
        <span><small>{live ? 'TIME LEFT' : 'TOOK'}</small><b className="m-num">{live ? secs(job.eta) : secs(job.elapsed)}</b></span>
        <span data-tip="Starts the next build from these weights when the shape matches"><small>STATUS</small><b>{job.status}</b></span>
      </div>
      {job.error ? <p className="kd-err">⚠ {job.error}</p> : null}
      {chart.length > 1 ? <div className="frg-chart" data-tip="Falling = learning. Held-out = text it never trained on: if it rises while training falls, it is memorising">
        <ResponsiveContainer width="100%" height={180}><LineChart data={chart} margin={{ top: 6, right: 10, bottom: 0, left: -14 }}>
          <CartesianGrid stroke="var(--m-line)" strokeDasharray="2 4" vertical={false} /><XAxis dataKey="s" tick={axis} tickLine={false} /><YAxis tick={axis} tickLine={false} axisLine={false} domain={['auto', 'auto']} /><Tooltip contentStyle={tipStyle} />
          <Line type="monotone" dataKey="train" stroke="var(--m-accent)" strokeWidth={2} dot={false} isAnimationActive={false} name="on its training text" /><Line type="monotone" dataKey="val" stroke="var(--frg-held)" strokeWidth={2} strokeDasharray="4 3" dot={false} isAnimationActive={false} name="on held-out text" /></LineChart></ResponsiveContainer>
        <ul className="c2-key"><li style={{ '--c': 'var(--m-accent)' }}><i />loss on its training text</li><li style={{ '--c': 'var(--frg-held)' }}><i />on held-out text</li></ul></div> : null}
      <Learning job={job} />
      <details className="frg-more"><summary>Engine readouts · learning rate {lastPt.lr ? lastPt.lr.toExponential(1) : '—'} · GRAD NORM {lastPt.g ?? '—'}</summary>
        {chart.some(x => x.lr) ? <div className="frg-chart" data-tip="Learning rate warms up then cools on a cosine. Gradient norm = how hard the step pushes (clipped at 1)"><ResponsiveContainer width="100%" height={150}><LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -14 }}>
          <XAxis dataKey="s" tick={axis} tickLine={false} /><YAxis yAxisId="lr" tick={axis} tickLine={false} axisLine={false} tickFormatter={v => v.toExponential(0)} /><YAxis yAxisId="g" orientation="right" tick={axis} tickLine={false} axisLine={false} /><Tooltip contentStyle={tipStyle} />
          <Line yAxisId="lr" type="monotone" dataKey="lr" stroke="var(--m-accent)" strokeWidth={1.6} dot={false} isAnimationActive={false} name="learning rate" /><Line yAxisId="g" type="monotone" dataKey="g" stroke="var(--frg-held)" strokeWidth={1.4} dot={false} isAnimationActive={false} name="grad norm" /></LineChart></ResponsiveContainer>
          <ul className="c2-key"><li style={{ '--c': 'var(--m-accent)' }}><i />learning rate</li><li style={{ '--c': 'var(--frg-held)' }}><i />grad norm</li></ul></div> : <p className="mlb-none">No readouts logged for this build.</p>}
        <p className="frg-how">Every step: text → token ids → each position guesses the next token → loss (how surprised it was) → backprop sends the blame through every block → AdamW nudges each number, clipped at gradient norm 1.</p>
      </details>
    </section> : null}

    <div className="c2-two">
      <section className="c2-card m-card" data-testid="frg-anatomy"><h4 className="c2-h">WHAT IT IS MADE OF <small>where its {sp ? fmt(sp.paramsTotal) : '…'} numbers live</small></h4>
        <Anatomy cfg={cfg} sp={sp} />
        <details className="frg-more" data-testid="frg-design"><summary>Fine-tune the design</summary>
          <div className="frg-form">
            <Seg label="TOKENS" k="tok" opts={SEG.tok} cfg={cfg} set={set} tip="How text becomes numbers" />
            {cfg.tok === 'bpe' ? <Seg label="WORD PIECES" k="vocab" opts={SEG.vocab} cfg={cfg} set={set} tip="How many word pieces it may learn" /> : null}
            <Seg label="WIDTH" k="d" opts={SEG.d} cfg={cfg} set={c => set({ ...c, heads: c.d % c.heads ? 1 : c.heads })} tip="Numbers per token inside the model: wider = more capacity, slower" />
            <div className="frg-field" data-tip="Blocks stacked on each other: deeper = more steps of thought per token"><small className="m-label">BLOCKS</small>
              <div className="frg-step"><button type="button" className="m-btn" disabled={cfg.layers <= f.limits.layers[0]} onClick={() => set({ ...cfg, layers: cfg.layers - 1 })} aria-label="One block fewer" data-testid="mlf-layers-down">−</button>
                <b className="m-num">{cfg.layers}</b><button type="button" className="m-btn" disabled={cfg.layers >= f.limits.layers[1]} onClick={() => set({ ...cfg, layers: cfg.layers + 1 })} aria-label="One block more" data-testid="mlf-layers-up">+</button></div></div>
            <Seg label="HEADS" k="heads" opts={SEG.heads} cfg={cfg} set={set} ok={h => cfg.d % h === 0} tip="Parallel ways of looking back at the text (must divide the width)" />
            <Seg label="SEES BACK" k="ctx" opts={SEG.ctx} cfg={cfg} set={set} tip="How many tokens back it can see" />
            <Seg label="STEPS" k="steps" opts={SEG.steps} cfg={cfg} set={set} tip="How long this version studies (on top of the version it continues from)" />
            <Seg label="BATCH" k="batch" opts={SEG.batch} cfg={cfg} set={set} tip="Pieces of text per step" />
            <Seg label="LEARNING RATE" k="lr" opts={SEG.lr} cfg={cfg} set={set} show={v => v.toExponential(0)} tip="How big each correction is (warms up, then cools down)" />
          </div>
          {sp ? <dl className="frg-kv">{[['Weights', `${sp.weightsMb} MB`], ['Compute per token', `${fmt(sp.flopsPerToken)} FLOPs`], ['This Mac', sp.flopsRate ? `${sp.flopsRate} GFLOP/s` : '—'],
            ['Head size', sp.headDim], ['Your data', `${fmt(sp.corpusTokens)} tokens`]].map(([k, v]) => <div key={k}><dt>{k}</dt><dd className="m-num">{v}</dd></div>)}</dl> : null}
        </details>
      </section>

      <section className="c2-card m-card" data-testid="frg-reads"><h4 className="c2-h">WHAT IT READS <small>{srcChars.toLocaleString()} characters of your text, scrubbed</small></h4>
        <ul className="frg-srcs" role="group" aria-label="What it learns from">{(f.sources || []).map(s => <li key={s.k} className={src.includes(s.k) ? '' : 'is-off'}>
          <label className="m-toggle" data-tip={`${s.blocks} pieces · scrubbed of wallets, keys, emails, phones`}><input type="checkbox" checked={src.includes(s.k)} onChange={e => setSrc(e.target.checked ? [...src, s.k] : src.filter(x => x !== s.k))} data-testid={`mlf-src-${s.k}`} /> <span>{s.label}</span></label>
          <i className="c2-bar"><u style={{ transform: `scaleX(${Math.max(0.02, s.chars / srcTop)})` }} /></i><b className="m-num">{fmt(s.chars)}</b></li>)}</ul>
        <details className="frg-more" data-testid="frg-rails-set"><summary>Guardrails · {rails.refuse.length} refusals · {rails.scrub ? 'scrub on' : 'scrub OFF'} · ends “{rails.footer}”</summary>
          <Chips label="REFUSE WHEN ASKED ABOUT" list={rails.refuse} onChange={v => setRails({ ...rails, refuse: v })} tip="A prompt with any of these gets a refusal, the model never runs" testid="mlf-refuse" />
          <Chips label="NEVER SAY" list={rails.block} onChange={v => setRails({ ...rails, block: v })} tip="Masked out of every answer" testid="mlf-block" />
          <label className="m-toggle" data-tip="Wallets, keys, emails and phone numbers are replaced in every answer"><input type="checkbox" checked={rails.scrub} onChange={e => setRails({ ...rails, scrub: e.target.checked })} data-testid="mlf-scrub" /> Scrub wallets, keys, emails, phones</label>
          <Seg label="LONGEST ANSWER" k="max_chars" opts={SEG.maxChars} cfg={rails} set={setRails} show={v => `${v} chars`} tip="Answers are cut here" />
          <label className="frg-field"><small className="m-label">ALWAYS END WITH</small><input className="m-input" value={rails.footer} maxLength={120} onChange={e => setRails({ ...rails, footer: e.target.value })} data-testid="mlf-footer" /></label>
          <label className="frg-field"><small className="m-label">EXTRA TEXT TO LEARN FROM (optional)</small><textarea className="m-input frg-extra" value={extra} maxLength={400000} onChange={e => setExtra(e.target.value)} placeholder="Paste your own writing: it is added to the proofs" data-testid="mlf-extra" /></label>
        </details>
      </section>
    </div>

    {built.length ? <section className="c2-card m-card" data-testid="mlf-models"><h4 className="c2-h">{versions.length ? `${famName.toUpperCase()} · VERSIONS` : 'YOUR MODELS'} <small>× better than guessing · pick one to ask it</small></h4>
      <Versions built={board} pick={pick} setPick={id => { setPick(id); setAns(null); }} />
      {pick ? <div className="frg-ask"><textarea className="m-input" value={q} maxLength={2000} onChange={e => setQ(e.target.value)} aria-label="Ask your model" data-testid="mlf-q" />
        <div className="frg-ask-go"><label className="frg-temp" data-tip="Low = safest guess each time · high = more surprising"><small className="m-label">CREATIVITY {temp.toFixed(1)}</small><input type="range" min="0.1" max="1.6" step="0.1" value={temp} onChange={e => setTemp(Number(e.target.value))} /></label>
          <button type="button" className="m-btn m-go" disabled={busy || !q.trim()} onClick={ask} data-testid="mlf-ask">Ask {picked?.version || 'it'}</button></div>
        {ans ? <div className="frg-ans" data-testid="mlf-ans"><div><small className="m-label">WHAT YOU SEE (guardrails on)</small><pre>{ans.answer}</pre></div><div><small className="m-label">RAW MODEL</small><pre>{ans.raw || '— the model never ran —'}</pre></div>
          <span className="frg-fired">{ans.fired.length ? ans.fired.map(x => <em key={x.rule + x.detail} className="m-chip">{x.rule}: {x.detail}</em>) : <em className="m-chip ok">no rule fired</em>}{ans.ms ? <small>{ans.ms} ms</small> : null}</span></div> : null}
        {picked?.card?.sample ? <small className="frg-sample">Its own words at the end of the build: “{picked.card.sample.slice(0, 160)}”</small> : null}</div> : null}
      {picked ? <div className="c2-two frg-ops"><div><small className="m-label">GUARDRAIL CHECK · {picked.version || picked.card.name}</small><Rails job={picked} call={call} setErr={setErr} /></div>
        <div><small className="m-label">ITS FILES ON THIS MAC</small><Files job={picked} folder={f.folder} call={call} setErr={setErr} /></div></div> : null}
    </section> : null}

    <section className="c2-card m-card" data-testid="mlf-labs"><h4 className="c2-h">FROM THE LABS <small>what the big labs use; each becomes a switch here once the engine runs it and a test checks it</small></h4>
      <ul className="c2-ways">{LABS.map(([t, who, say], i) => <li key={t} className="is-todo" style={{ '--i': i }} data-tip={say}><i aria-hidden="true">○</i><b>{t} <small className="frg-who">{who}</small></b><u>{say}</u><em className="m-chip">not built</em></li>)}</ul>
    </section>
  </div>;
}

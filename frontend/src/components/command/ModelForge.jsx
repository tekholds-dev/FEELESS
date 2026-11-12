import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { boxRef } from '../../lib/boxRef';
import { useCountUp } from '../../lib/useCountUp';

// 🏗 MODEL FORGE (owner 2026-11-12: "create my full own model and my own guardrails … a model build playground that truly works and shows specs
// … I click and it builds"). Pick the blueprint, see its specs live, set the guardrails, press Build: a real transformer (backend/model_forge.py,
// hand-written backprop) trains on THIS Mac from the owner's proofs, its loss drawn live; then ask it, with the guardrails on. Nothing is rented.
const SEG = { tok: [['char', 'Characters', 'One token per letter: small vocabulary, learns spelling first'], ['bpe', 'BPE pieces', 'Byte-pair pieces trained on your text: words in fewer tokens']],
  vocab: [256, 512, 1024, 2048], d: [32, 64, 128, 192, 256, 384], heads: [1, 2, 3, 4, 6, 8], ctx: [32, 64, 128, 256], steps: [200, 500, 1000, 2000, 5000], batch: [8, 16, 32],
  lr: [3e-4, 1e-3, 3e-3], maxChars: [200, 400, 600, 1000] };
const fmt = n => (n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${Math.round(n || 0)}`);
const secs = s => (s >= 3600 ? `${(s / 3600).toFixed(1)} h` : s >= 60 ? `${Math.round(s / 60)} min` : `${Math.max(1, Math.round(s || 0))} s`);
const LIVE = new Set(['tokenizing', 'training']);
const forgeBox = boxRef([720]);   // 📐 one column when its window is narrow (the desk window, a Duo half), not only on a small screen
function Big({ v, f = fmt }) { const n = useCountUp(Number(v) || 0); return <b className="m-num">{f(n)}</b>; }

function Seg({ label, k, opts, cfg, set, tip, show = x => x, ok = () => true }) {
  return <div className="mlf-field" data-tip={tip}><small className="m-label">{label}</small>
    <div className="m-seg" role="radiogroup" aria-label={label}>{opts.map(o => { const [v, l, t] = Array.isArray(o) ? o : [o, show(o)]; const can = ok(v);
      return <button key={v} type="button" role="radio" aria-checked={cfg[k] === v} className={cfg[k] === v ? 'active' : ''} disabled={!can} data-tip={t}
        onClick={() => set({ ...cfg, [k]: v })} data-testid={`mlf-${k}-${v}`}>{l}</button>; })}</div></div>;
}

function Stack({ cfg, sp }) {   // the model, drawn as the slabs it is made of, bottom (your text) to top (the next token)
  const p = sp?.params || {}; const blocks = Array.from({ length: cfg.layers });
  return <div className="mlf-stack" aria-label="The model, layer by layer" data-testid="mlf-stack">
    <span className="mlf-slab is-out"><b>Next token</b><small>head shares the embedding · {fmt(sp?.vocab || 0)} choices</small></span>
    <span className="mlf-slab is-norm"><b>LayerNorm</b><small>{fmt(p.final_norm)}</small></span>
    {blocks.map((_, i) => <span key={i} className="mlf-slab is-block" style={{ '--i': cfg.layers - i }}><b>Block {cfg.layers - i}</b>
      <small>{cfg.heads}-head attention · MLP {cfg.d}→{cfg.d * 4}→{cfg.d} · {fmt(p.per_block)}</small><i className="mlf-flow" aria-hidden="true" /></span>)}
    <span className="mlf-slab is-emb"><b>Embeddings</b><small>{fmt(p.embed)} token + {fmt(p.position)} position · width {cfg.d} · sees {cfg.ctx} tokens</small></span>
    <span className="mlf-slab is-tok"><b>{cfg.tok === 'bpe' ? `BPE tokenizer · ${cfg.vocab}` : 'Character tokenizer'}</b><small>your proofs → numbers</small></span>
  </div>;
}

function Chips({ label, list, onChange, tip, testid }) {
  const [t, setT] = useState('');
  const add = () => { const v = t.trim(); if (v && !list.includes(v)) onChange([...list, v].slice(0, 30)); setT(''); };
  return <div className="mlf-field" data-tip={tip}><small className="m-label">{label}</small>
    <div className="mlf-chips">{list.map(w => <button key={w} type="button" className="m-chip" onClick={() => onChange(list.filter(x => x !== w))} data-tip="Click to remove">{w} ✕</button>)}
      <input className="m-input" value={t} maxLength={60} onChange={e => setT(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} placeholder="add + Enter" aria-label={`Add to ${label}`} data-testid={testid} /></div></div>;
}

export function ModelForge({ call }) {
  const [f, setF] = useState(null); const [err, setErr] = useState(''); const [cfg, setCfg] = useState(null); const [sp, setSp] = useState(null);
  const [rails, setRails] = useState(null); const [extra, setExtra] = useState(''); const [src, setSrc] = useState(null); const [job, setJob] = useState(null); const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState(null); const [q, setQ] = useState('### PoW · won · '); const [temp, setTemp] = useState(0.8); const [ans, setAns] = useState(null);
  const load = useCallback(() => (!call ? Promise.resolve(setErr('Sign in as the owner to build a model.')) : call('/admin/model-lab/forge').then(x => {
    setF(x); setErr(''); setCfg(c => c || { ...x.presets.nano, preset: 'nano' }); setRails(r => r || x.rails); setSrc(s => s || (x.sources || []).map(y => y.k));
    const run = x.jobs.find(j => j.id === x.running) || null; setJob(j => run || (j && x.jobs.find(y => y.id === j.id)) || x.jobs[0] || null);
    setPick(p => p || x.jobs.find(j => j.card)?.id || null);
  }).catch(e => setErr(e.message))), [call]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {   // specs follow the blueprint (debounced: one read after the clicks settle)
    if (!cfg || !call) return undefined; const t = setTimeout(() => call('/admin/model-lab/forge/spec', { method: 'POST', body: JSON.stringify({ cfg, extra, sources: src || [] }) }).then(setSp).catch(e => setErr(e.message)), 250);
    return () => clearTimeout(t);
  }, [cfg, extra, src, call]);
  const live = job && LIVE.has(job.status); const timer = useRef(null);
  useEffect(() => {   // a running build is read every 1.5 s until it ends, then the list refreshes once
    if (!live) return undefined;
    timer.current = setInterval(() => call(`/admin/model-lab/forge/${job.id}`).then(j => { setJob(j); if (!LIVE.has(j.status)) { load(); setPick(j.card ? j.id : null); } }).catch(() => {}), 1500);
    return () => clearInterval(timer.current);
  }, [live, job?.id, call, load]);
  const build = async () => { setBusy(true); setErr(''); try { const r = await call('/admin/model-lab/forge/build', { method: 'POST', body: JSON.stringify({ cfg, rails, extra, sources: src || [] }) }); setJob({ id: r.id, status: 'tokenizing', history: [], steps: cfg.steps, spec: r.spec }); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const stop = () => call(`/admin/model-lab/forge/${job.id}/stop`, { method: 'POST' }).catch(e => setErr(e.message));
  const ask = async () => { setBusy(true); try { setAns(await call(`/admin/model-lab/forge/${pick}/ask`, { method: 'POST', body: JSON.stringify({ prompt: q, temperature: temp, max_new: 220 }) })); setErr(''); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (!f || !cfg || !rails || !src) return <p className="mlb-none">{err ? `⚠ ${err}` : 'Opening the forge…'}</p>;
  const preset = k => setCfg({ ...f.presets[k], preset: k }); const set = c => setCfg({ ...c, preset: 'custom' });
  const pctCap = sp ? Math.min(1, sp.paramsTotal / f.limits.params) : 0; const built = f.jobs.filter(j => j.card);
  const chart = (job?.history || []).map(([s, l, v]) => ({ s, train: l, val: v }));
  return <div ref={forgeBox} className="mlf" data-testid="model-forge">
    <p className="mlf-truth">A real transformer, written from scratch, trained on <b>this Mac</b> from <b>{(f.sources || []).filter(s => src.includes(s.k)).reduce((a, s) => a + s.chars, 0).toLocaleString()}</b> characters of your own text. It learns its voice and shape, not world knowledge — the more you give it, the smarter it gets. Nothing is rented or spent.</p>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <section className="mlf-grid">
      <div className="mlf-card m-live"><h4>① BLUEPRINT</h4>
        <div className="m-seg mlf-presets" role="radiogroup" aria-label="Preset">{Object.entries(f.presets).map(([k, p]) => <button key={k} type="button" role="radio" aria-checked={cfg.preset === k} className={cfg.preset === k ? 'active' : ''} onClick={() => preset(k)} data-tip={`${p.layers} layers · width ${p.d} · ${p.steps} steps`} data-testid={`mlf-preset-${k}`}>{p.name}</button>)}
          <button type="button" role="radio" aria-checked={cfg.preset === 'custom'} className={cfg.preset === 'custom' ? 'active' : ''} disabled data-tip="Change any setting below and it becomes yours">Custom</button></div>
        <label className="mlf-field"><small className="m-label">NAME</small><input className="m-input" value={cfg.name} maxLength={40} onChange={e => set({ ...cfg, name: e.target.value })} data-testid="mlf-name" /></label>
        <Seg label="TOKENIZER" k="tok" opts={SEG.tok} cfg={cfg} set={set} tip="How text becomes numbers" />
        {cfg.tok === 'bpe' ? <Seg label="VOCABULARY" k="vocab" opts={SEG.vocab} cfg={cfg} set={set} tip="How many word pieces it may learn" /> : null}
        <Seg label="WIDTH" k="d" opts={SEG.d} cfg={cfg} set={c => set({ ...c, heads: c.d % c.heads ? 1 : c.heads })} tip="Numbers per token inside the model: wider = more capacity, slower" />
        <div className="mlf-field" data-tip="Transformer blocks stacked on each other: deeper = more steps of thought per token"><small className="m-label">LAYERS</small>
          <div className="mlf-step"><button type="button" className="m-btn" disabled={cfg.layers <= f.limits.layers[0]} onClick={() => set({ ...cfg, layers: cfg.layers - 1 })} aria-label="One layer fewer" data-testid="mlf-layers-down">−</button>
            <b className="m-num">{cfg.layers}</b><button type="button" className="m-btn" disabled={cfg.layers >= f.limits.layers[1]} onClick={() => set({ ...cfg, layers: cfg.layers + 1 })} aria-label="One layer more" data-testid="mlf-layers-up">+</button></div></div>
        <Seg label="ATTENTION HEADS" k="heads" opts={SEG.heads} cfg={cfg} set={set} ok={h => cfg.d % h === 0} tip="Parallel ways of looking back at the text (must divide the width)" />
        <Seg label="CONTEXT" k="ctx" opts={SEG.ctx} cfg={cfg} set={set} tip="How many tokens back it can see" />
        <Seg label="TRAINING STEPS" k="steps" opts={SEG.steps} cfg={cfg} set={set} tip="How long it studies" />
        <Seg label="BATCH" k="batch" opts={SEG.batch} cfg={cfg} set={set} tip="Pieces of text per step" />
        <Seg label="LEARNING RATE" k="lr" opts={SEG.lr} cfg={cfg} set={set} show={v => v.toExponential(0)} tip="How big each correction is (warms up, then cools down)" />
      </div>
      <div className="mlf-card"><h4>② THE MODEL YOU ARE BUILDING</h4><Stack cfg={cfg} sp={sp} /></div>
      <div className="mlf-card"><h4>③ SPECS · LIVE</h4>
        {sp ? <div className="mlf-specs" data-testid="mlf-specs">
          <span className="mlf-ring" style={{ '--k': pctCap }} data-tip={`Parameters: every number it learns. Cap on this Mac ${fmt(f.limits.params)}`}><Big v={sp.paramsTotal} /><small>PARAMETERS</small></span>
          <dl className="mlf-kv">
            <dt>Weights</dt><dd className="m-num">{sp.weightsMb} MB</dd><dt>Training memory</dt><dd className="m-num">{sp.trainMb} MB</dd>
            <dt>Compute per token</dt><dd className="m-num">{fmt(sp.flopsPerToken)} FLOPs</dd><dt>Head size</dt><dd className="m-num">{sp.headDim}</dd>
            <dt>Your data</dt><dd className="m-num">{fmt(sp.corpusTokens)} tokens</dd><dt>Reads it</dt><dd className="m-num">{sp.epochs}×</dd>
            <dt>Estimated build</dt><dd className="m-num">≈ {secs(sp.estSec)}</dd></dl>
          <span className="mlf-meter" data-tip="Tokens of your text per parameter. Big models want ~20; below 1 it mostly memorises"><small>DATA PER PARAMETER</small><i><u style={{ transform: `scaleX(${Math.min(1, sp.tokensPerParam / 20)})` }} /></i><b className="m-num">{sp.tokensPerParam}</b></span>
          <p className={`mlf-verdict${sp.tooBig ? ' is-bad' : ''}`}>{sp.verdict}</p></div> : <p className="mlb-none">Reading the specs…</p>}
      </div>
      <div className="mlf-card"><h4>④ WHAT IT READS · ITS GUARDRAILS</h4>
        <div className="mlf-srcs" role="group" aria-label="What it learns from">{(f.sources || []).map(s => <label key={s.k} className="m-toggle" data-tip={`${s.blocks} pieces · scrubbed of wallets, keys, emails, phones`}><input type="checkbox" checked={src.includes(s.k)} onChange={e => setSrc(e.target.checked ? [...src, s.k] : src.filter(x => x !== s.k))} data-testid={`mlf-src-${s.k}`} /> {s.label}<b className="m-num">{fmt(s.chars)}</b></label>)}</div>
        <Chips label="REFUSE WHEN ASKED ABOUT" list={rails.refuse} onChange={v => setRails({ ...rails, refuse: v })} tip="A prompt with any of these gets a refusal, the model never runs" testid="mlf-refuse" />
        <Chips label="NEVER SAY" list={rails.block} onChange={v => setRails({ ...rails, block: v })} tip="Masked out of every answer" testid="mlf-block" />
        <label className="m-toggle" data-tip="Wallets, keys, emails and phone numbers are replaced in every answer"><input type="checkbox" checked={rails.scrub} onChange={e => setRails({ ...rails, scrub: e.target.checked })} data-testid="mlf-scrub" /> Scrub wallets, keys, emails, phones</label>
        <Seg label="LONGEST ANSWER" k="max_chars" opts={SEG.maxChars} cfg={rails} set={setRails} show={v => `${v} chars`} tip="Answers are cut here" />
        <label className="mlf-field"><small className="m-label">ALWAYS END WITH</small><input className="m-input" value={rails.footer} maxLength={120} onChange={e => setRails({ ...rails, footer: e.target.value })} data-testid="mlf-footer" /></label>
        <label className="mlf-field"><small className="m-label">EXTRA TEXT TO LEARN FROM (optional)</small><textarea className="m-input mlf-extra" value={extra} maxLength={400000} onChange={e => setExtra(e.target.value)} placeholder="Paste your own writing: it is added to the proofs" data-testid="mlf-extra" /></label>
      </div>
    </section>
    <div className="mlf-go"><button type="button" className="m-btn m-go" disabled={busy || live || sp?.tooBig} onClick={build} data-tip="Starts the build as its own process on this Mac, one at a time; the site keeps its speed" data-testid="mlf-build">🔨 Build {cfg.name || 'it'}</button>
      <small>{live ? 'A build is running — watch it below.' : `≈ ${sp ? secs(sp.estSec) : '…'} on this Mac · stop any time, it keeps what it learned`}</small></div>
    {job ? <section className="mlf-card mlf-run" data-testid="mlf-run"><h4>⑤ {live ? 'BUILDING' : 'LAST BUILD'} · {job.name || job.id}<span className={`m-chip${job.status === 'failed' ? ' bad' : job.status === 'done' ? ' ok' : ' warn'}`}>{job.status}</span></h4>
      <div className="mlf-runbar" data-tip={`${job.step || 0} of ${job.steps} steps`}><u style={{ transform: `scaleX(${job.steps ? (job.step || 0) / job.steps : 0})` }} /></div>
      <div className="mlf-runstats"><span><small>STEP</small><b className="m-num">{job.step || 0}/{job.steps}</b></span><span><small>LOSS</small><b className="m-num">{job.loss ?? '—'}</b></span><span><small>HELD-OUT LOSS</small><b className="m-num">{job.val ?? '—'}</b></span>
        <span><small>SPEED</small><b className="m-num">{job.tps ? `${fmt(job.tps)} tok/s` : '—'}</b></span><span><small>{live ? 'LEFT' : 'TOOK'}</small><b className="m-num">{live ? secs(job.eta) : secs(job.elapsed)}</b></span>
        {live ? <button type="button" className="m-btn" onClick={stop} data-tip="Ends at the next step and keeps the weights it reached" data-testid="mlf-stop">⏹ Stop</button> : null}</div>
      {job.error ? <p className="kd-err">⚠ {job.error}</p> : null}
      {chart.length > 1 ? <div className="mlf-chart" data-tip="Loss = how surprised it is by the next token. Falling = learning. Held-out = text it never trained on"><ResponsiveContainer width="100%" height={190}><LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
        <XAxis dataKey="s" tick={{ fontSize: 9, fill: '#9c93bd' }} /><YAxis tick={{ fontSize: 9, fill: '#9c93bd' }} domain={['auto', 'auto']} /><Tooltip contentStyle={{ background: '#120b2c', border: '1px solid #9b6bff55', fontSize: 11 }} />
        <Line type="monotone" dataKey="train" stroke="#b48cff" strokeWidth={2} dot={false} isAnimationActive={false} name="loss" /><Line type="monotone" dataKey="val" stroke="#3ee7ff" strokeWidth={2} dot={false} isAnimationActive={false} name="held-out" /></LineChart></ResponsiveContainer></div> : null}
    </section> : null}
    {built.length ? <section className="mlf-card" data-testid="mlf-models"><h4>⑥ YOUR MODELS · ASK ONE</h4>
      <ul className="mlf-models">{built.map((j, i) => <li key={j.id} style={{ '--i': i }}><button type="button" className={`mlf-model${pick === j.id ? ' is-on' : ''}`} onClick={() => { setPick(j.id); setAns(null); }} data-testid={`mlf-model-${j.id}`}
        data-tip={`Perplexity ${j.card.perplexity} (guessing at random = ${j.card.baselinePerplexity}): lower means it predicts your text better`}><b>{j.card.name}</b><small>{fmt(j.card.spec?.paramsTotal)} params · {j.card.cfg.layers} layers · loss {j.card.val} · {secs(j.card.seconds)}</small>
        <i className="mlb-bar"><u style={{ transform: `scaleX(${Math.max(0.02, 1 - j.card.perplexity / j.card.baselinePerplexity)})` }} /></i></button></li>)}</ul>
      {pick ? <div className="mlf-ask"><textarea className="m-input" value={q} maxLength={2000} onChange={e => setQ(e.target.value)} aria-label="Ask your model" data-testid="mlf-q" />
        <label className="mlf-temp" data-tip="Low = safest guess each time · high = more surprising"><small className="m-label">CREATIVITY {temp.toFixed(1)}</small><input type="range" min="0.1" max="1.6" step="0.1" value={temp} onChange={e => setTemp(Number(e.target.value))} /></label>
        <button type="button" className="m-btn m-go" disabled={busy || !q.trim()} onClick={ask} data-testid="mlf-ask">Ask it</button>
        {ans ? <div className="mlf-ans" data-testid="mlf-ans"><div><small className="m-label">WHAT YOU SEE (guardrails on)</small><pre>{ans.answer}</pre></div><div><small className="m-label">RAW MODEL</small><pre>{ans.raw || '— the model never ran —'}</pre></div>
          <span className="mlf-fired">{ans.fired.length ? ans.fired.map(x => <em key={x.rule + x.detail} className="m-chip">{x.rule}: {x.detail}</em>) : <em className="m-chip ok">no rule fired</em>}{ans.ms ? <small>{ans.ms} ms</small> : null}</span></div> : null}
        {built.find(j => j.id === pick)?.card?.sample ? <small className="mlf-sample">Its own words at the end of the build: “{built.find(j => j.id === pick).card.sample.slice(0, 160)}”</small> : null}</div> : null}
    </section> : null}
  </div>;
}

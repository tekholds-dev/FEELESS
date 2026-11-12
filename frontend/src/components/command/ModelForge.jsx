import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import { boxRef } from '../../lib/boxRef';
import { useCountUp } from '../../lib/useCountUp';

// 🏗 COMPAI · the model forge (owner 2026-11-12: "elite dev's dash … live view of whatever it's learning … one model: COMP Flagship v1.02").
// ONE model, built in VERSIONS: every build is the family name + the next version, and continues from the newest version with the same shape
// (its weights + tokenizer), so v1.01 starts where v1.00 ended. A real transformer (backend/model_forge.py, hand-written backprop, AdamW) trains
// on THIS Mac from the owner's own text. Live: loss, learning rate, gradient norm, what it writes, its top-5 next-token guesses and where its last
// layer looks (attention, per head). Then: the version board + scaling chart, its files on disk, the guardrail suite, ask it. Nothing is rented.
const SEG = { tok: [['char', 'Characters', 'One token per letter: small vocabulary, learns spelling first'], ['bpe', 'BPE pieces', 'Byte-pair pieces trained on your text: words in fewer tokens']],
  vocab: [256, 512, 1024, 2048], d: [32, 64, 128, 192, 256, 384], heads: [1, 2, 3, 4, 6, 8], ctx: [32, 64, 128, 256], steps: [200, 600, 1000, 2000, 5000], batch: [8, 16, 32],
  lr: [3e-4, 6e-4, 1e-3, 3e-3], maxChars: [200, 400, 600, 1000] };
const fmt = n => (n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${Math.round(n || 0)}`);
const secs = s => (s >= 3600 ? `${(s / 3600).toFixed(1)} h` : s >= 60 ? `${Math.round(s / 60)} min` : `${Math.max(1, Math.round(s || 0))} s`);
const bytes = b => (b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : b >= 1e3 ? `${(b / 1e3).toFixed(1)} KB` : `${b} B`);
const vnum = v => Number(String(v || '').replace(/^v/, '')) || 0;
const LIVE = new Set(['tokenizing', 'training']);
const SHAPE = ['d', 'layers', 'heads', 'ctx', 'tok'];
const PIPE = [['tok', 'TOKENIZE', 'Text → token ids'], ['fwd', 'PREDICT', 'Every position guesses the next token'], ['loss', 'LOSS', 'How surprised it was (cross-entropy)'],
  ['bwd', 'BACKPROP', 'The blame, sent back through every layer'], ['opt', 'ADAMW', 'Each number nudged, clipped at gradient norm 1']];
const LABS = [['RMSNorm', 'LLaMA, Mistral', 'Normalises by size only (no mean): a bit faster, same quality.'], ['SwiGLU', 'LLaMA, PaLM', 'A gated MLP: better loss for the same compute.'],
  ['RoPE', 'LLaMA, Qwen', 'Rotates queries and keys by position: handles longer text than learned positions.'], ['GQA', 'LLaMA 3, Mistral', 'Heads share keys and values: less memory when it answers.']];
const forgeBox = boxRef([720]);   // 📐 one column when its window is narrow (the desk window, a Duo half), not only on a small screen
const tipStyle = { background: '#120b2c', border: '1px solid #9b6bff55', fontSize: 11 };
const axis = { fontSize: 9, fill: '#9c93bd' };
function Big({ v, f = fmt }) { const n = useCountUp(Number(v) || 0); return <b className="m-num">{f(n)}</b>; }
const show = t => t.replace(/\n/g, '⏎').replace(/ /g, '·');

function Seg({ label, k, opts, cfg, set, tip, show: sh = x => x, ok = () => true }) {
  return <div className="mlf-field" data-tip={tip}><small className="m-label">{label}</small>
    <div className="m-seg" role="radiogroup" aria-label={label}>{opts.map(o => { const [v, l, t] = Array.isArray(o) ? o : [o, sh(o)]; const can = ok(v);
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

function Pipe({ live, status }) {   // HOW it learns: the five things every training step does, a pulse running through them while it trains
  return <ol className={`mlf-pipe${live ? ' is-live' : ''}`} aria-label="How it learns, every step" data-testid="mlf-pipe">{PIPE.map(([k, t, say], i) =>
    <li key={k} style={{ '--i': i }} className={status === 'tokenizing' && k === 'tok' ? 'is-on' : ''} data-tip={say}><b>{t}</b><small>{say}</small></li>)}</ol>;
}

function Attn({ peek }) {   // WHERE it looks: the last block's attention for one fixed probe, one grid per head (row = token, column = what it reads)
  const [h, setH] = useState(0); const a = peek?.attn; if (!a?.heads?.length) return null; const m = a.heads[Math.min(h, a.heads.length - 1)]; const T = a.tokens.length;
  return <div className="mlf-attn" data-testid="mlf-attn"><div className="mlf-attn-head"><small className="m-label">WHERE IT LOOKS · LAST BLOCK · STEP {peek.step}</small>
    <div className="m-seg" role="radiogroup" aria-label="Attention head">{a.heads.map((_, i) => <button key={i} type="button" role="radio" aria-checked={h === i} className={h === i ? 'active' : ''} onClick={() => setH(i)} data-tip={`Head ${i + 1}: each head learns its own way to look back`}>H{i + 1}</button>)}</div></div>
    <div className="mlf-attn-grid" style={{ '--t': T }} role="img" aria-label={`Attention of head ${h + 1}`}>{m.map((row, i) => row.map((v, j) =>
      <i key={`${i}-${j}`} style={{ opacity: j > i ? 0 : Math.max(0.05, v) }} data-tip={`“${show(a.tokens[i])}” reads “${show(a.tokens[j])}” ${(v * 100).toFixed(0)}%`} />))}</div>
    <div className="mlf-attn-toks" style={{ '--t': T }}>{a.tokens.map((t, i) => <span key={i}>{show(t)}</span>)}</div></div>;
}

function Learning({ job }) {   // WHAT it learns: its own words at each checkpoint + its top-5 guesses for the next token after the probe
  const s = job.samples || []; const pk = job.peek; if (!s.length && !pk) return null; const now = s[s.length - 1];
  return <div className="mlf-learn" data-testid="mlf-learn">
    {now ? <div className="mlf-says"><small className="m-label">WHAT IT WRITES NOW · STEP {now.step}</small><pre key={now.step}>{now.text || '…'}</pre>
      <ol className="mlf-past">{s.slice(0, -1).reverse().slice(0, 4).map(x => <li key={x.step}><em className="m-num">{x.step}</em>{x.text.slice(0, 90)}</li>)}</ol></div> : null}
    {pk ? <div className="mlf-top" data-testid="mlf-top"><small className="m-label">TOP-5 NEXT TOKEN</small>{pk.top.map((t, i) => <span key={`${t.tok}${i}`} style={{ '--i': i }} data-tip={`${(t.p * 100).toFixed(1)}% sure the next token is “${show(t.tok)}”`}>
      <code>{show(t.tok)}</code><i className="mlb-bar"><u style={{ transform: `scaleX(${t.p})` }} /></i><b className="m-num">{(t.p * 100).toFixed(1)}%</b></span>)}</div> : null}
    <Attn peek={pk} /></div>;
}

function Versions({ built, pick, setPick }) {   // the version board + the scaling chart (parameters vs held-out loss: lower right = bigger and better)
  const pts = built.map(j => ({ x: j.card.spec?.paramsTotal || 0, y: j.card.val, z: j.card.totalSteps || j.card.steps, v: j.version || j.card.name }));
  const best = Math.min(...built.map(j => j.card.val ?? 99));
  return <div className="mlf-board">
    <ul className="mlf-models">{built.map((j, i) => <li key={j.id} style={{ '--i': i }}><button type="button" className={`mlf-model${pick === j.id ? ' is-on' : ''}`} onClick={() => setPick(j.id)} data-testid={`mlf-model-${j.id}`}
      data-tip={`Perplexity ${j.card.perplexity} (guessing at random = ${j.card.baselinePerplexity}): lower means it predicts your text better`}>
      <span className="mlf-model-top"><b>{j.version || j.card.name}</b>{j.card.val === best ? <em className="m-chip ok">BEST</em> : null}{j.card.base ? <em className="m-chip">from {j.card.base}</em> : null}</span>
      <small>{fmt(j.card.spec?.paramsTotal)} params · {j.card.cfg.layers} layers · {fmt(j.card.totalSteps || j.card.steps)} steps · held-out {j.card.val} · {secs(j.card.seconds)}</small>
      <i className="mlb-bar"><u style={{ transform: `scaleX(${Math.max(0.02, 1 - j.card.perplexity / j.card.baselinePerplexity)})` }} /></i></button></li>)}</ul>
    {pts.length > 1 ? <div className="mlf-chart" data-tip="Every version: parameters vs held-out loss. Bigger dot = more training steps"><ResponsiveContainer width="100%" height={170}><ScatterChart margin={{ top: 8, right: 10, bottom: 0, left: -14 }}>
      <CartesianGrid stroke="#ffffff0d" /><XAxis dataKey="x" type="number" scale="log" domain={['auto', 'auto']} tickFormatter={fmt} tick={axis} name="params" /><YAxis dataKey="y" type="number" domain={['auto', 'auto']} tick={axis} name="held-out" />
      <ZAxis dataKey="z" range={[40, 220]} name="steps" /><Tooltip contentStyle={tipStyle} formatter={(v, n) => (n === 'params' ? fmt(v) : v)} /><Scatter data={pts} fill="#ff3fa4" isAnimationActive={false} /></ScatterChart></ResponsiveContainer></div> : null}
  </div>;
}

function Files({ job, folder, call, setErr }) {   // WHERE it lives: this version's own files on this Mac, each one downloadable
  const [got, setGot] = useState('');
  const save = async n => { try { const r = await call(`/admin/model-lab/forge/${job.id}/file/${n}`); const raw = Uint8Array.from(atob(r.b64), ch => ch.charCodeAt(0));
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([raw])); a.download = `${job.id}-${n}`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); setGot(n); } catch (e) { setErr(e.message); } };
  return <div className="mlf-files" data-testid="mlf-files"><code className="mlf-path" data-tip="The folder on this Mac">{folder}/{job.id}/</code>
    <ul>{(job.files || []).map((f, i) => <li key={f.name} style={{ '--i': i }}><span><b>{f.name}</b><small>{f.say}</small></span><em className="m-num">{bytes(f.bytes)}</em>
      <button type="button" className="m-btn" onClick={() => save(f.name)} data-tip={`Download ${f.name}`} data-testid={`mlf-file-${f.name}`}>{got === f.name ? '✓' : '⬇'}</button></li>)}</ul></div>;
}

function Rails({ job, call, setErr }) {   // the guardrail suite: every rule tripped on purpose, plus one real answer through them
  const [r, setR] = useState(null); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); try { setR(await call(`/admin/model-lab/forge/${job.id}/railtest`, { method: 'POST' })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  useEffect(() => { setR(null); }, [job.id]);
  return <div className="mlf-rails" data-testid="mlf-rails"><div className="mlf-rails-go"><button type="button" className="m-btn m-go" disabled={busy} onClick={run} data-tip="Trips every guardrail of this version on purpose and checks it held" data-testid="mlf-railtest">🛡 {busy ? 'Testing…' : 'Run the guardrail suite'}</button>
    {r ? <b className={`m-num mlf-score${r.passed === r.total ? ' is-ok' : ' is-bad'}`}>{r.passed}/{r.total} held</b> : null}</div>
    {r ? <ul>{r.tests.map((t, i) => <li key={t.rule + t.test} style={{ '--i': i }} className={t.pass ? 'is-ok' : 'is-bad'} data-tip={`It answered: ${t.got}`}><i>{t.pass ? '✓' : '✕'}</i><b>{t.rule}</b><small>{t.test}</small></li>)}</ul> : null}</div>;
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
  const versions = useMemo(() => (f?.jobs || []).filter(j => j.card && j.version).sort((a, b) => vnum(b.version) - vnum(a.version)), [f]);
  const base = useMemo(() => (cfg ? versions.find(j => SHAPE.every(k => j.card.cfg?.[k] === cfg[k])) : null), [versions, cfg]);
  const build = async () => { setBusy(true); setErr(''); try { const r = await call('/admin/model-lab/forge/build', { method: 'POST', body: JSON.stringify({ cfg, rails, extra, sources: src || [], cont }) }); setJob({ id: r.id, version: r.version, base: r.base, status: 'tokenizing', history: [], steps: cfg.steps, spec: r.spec }); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const stop = () => call(`/admin/model-lab/forge/${job.id}/stop`, { method: 'POST' }).catch(e => setErr(e.message));
  const ask = async () => { setBusy(true); try { setAns(await call(`/admin/model-lab/forge/${pick}/ask`, { method: 'POST', body: JSON.stringify({ prompt: q, temperature: temp, max_new: 220 }) })); setErr(''); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (!f || !cfg || !rails || !src) return <p className="mlb-none">{err ? `⚠ ${err}` : 'Opening the forge…'}</p>;
  const preset = k => setCfg({ ...f.presets[k], preset: k }); const set = c => setCfg({ ...c, preset: 'custom' });
  const pctCap = sp ? Math.min(1, sp.paramsTotal / f.limits.params) : 0; const built = f.jobs.filter(j => j.card);
  const board = versions.length ? versions : built; const picked = built.find(j => j.id === pick);
  const famName = family || f.family?.name || 'COMP Flagship'; const nextV = f.next || 'v1.00';
  const chart = (job?.history || []).map(([s, l, v, lr, g]) => ({ s, train: l, val: v, lr, g }));
  return <div ref={forgeBox} className="mlf" data-testid="model-forge">
    <p className="mlf-truth">One model, built in versions: <b>{famName}</b>. A real transformer written from scratch, trained on <b>this Mac</b> from <b>{(f.sources || []).filter(s => src.includes(s.k)).reduce((a, s) => a + s.chars, 0).toLocaleString()}</b> characters of your own text. Each version continues from the last one with the same shape. It learns your voice and structure, not world knowledge. Nothing is rented or spent.</p>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <section className="mlf-grid">
      <div className="mlf-card m-live"><h4>① BLUEPRINT</h4>
        <div className="m-seg mlf-presets" role="radiogroup" aria-label="Preset">{Object.entries(f.presets).map(([k, p]) => <button key={k} type="button" role="radio" aria-checked={cfg.preset === k} className={cfg.preset === k ? 'active' : ''} onClick={() => preset(k)} data-tip={`${p.layers} layers · width ${p.d} · ${p.steps} steps`} data-testid={`mlf-preset-${k}`}>{p.name}</button>)}
          <button type="button" role="radio" aria-checked={cfg.preset === 'custom'} className={cfg.preset === 'custom' ? 'active' : ''} disabled data-tip="Change any setting below and it becomes yours">Custom</button></div>
        <Seg label="TOKENIZER" k="tok" opts={SEG.tok} cfg={cfg} set={set} tip="How text becomes numbers" />
        {cfg.tok === 'bpe' ? <Seg label="VOCABULARY" k="vocab" opts={SEG.vocab} cfg={cfg} set={set} tip="How many word pieces it may learn" /> : null}
        <Seg label="WIDTH" k="d" opts={SEG.d} cfg={cfg} set={c => set({ ...c, heads: c.d % c.heads ? 1 : c.heads })} tip="Numbers per token inside the model: wider = more capacity, slower" />
        <div className="mlf-field" data-tip="Transformer blocks stacked on each other: deeper = more steps of thought per token"><small className="m-label">LAYERS</small>
          <div className="mlf-step"><button type="button" className="m-btn" disabled={cfg.layers <= f.limits.layers[0]} onClick={() => set({ ...cfg, layers: cfg.layers - 1 })} aria-label="One layer fewer" data-testid="mlf-layers-down">−</button>
            <b className="m-num">{cfg.layers}</b><button type="button" className="m-btn" disabled={cfg.layers >= f.limits.layers[1]} onClick={() => set({ ...cfg, layers: cfg.layers + 1 })} aria-label="One layer more" data-testid="mlf-layers-up">+</button></div></div>
        <Seg label="ATTENTION HEADS" k="heads" opts={SEG.heads} cfg={cfg} set={set} ok={h => cfg.d % h === 0} tip="Parallel ways of looking back at the text (must divide the width)" />
        <Seg label="CONTEXT" k="ctx" opts={SEG.ctx} cfg={cfg} set={set} tip="How many tokens back it can see" />
        <Seg label="TRAINING STEPS" k="steps" opts={SEG.steps} cfg={cfg} set={set} tip="How long this version studies (on top of the version it continues from)" />
        <Seg label="BATCH" k="batch" opts={SEG.batch} cfg={cfg} set={set} tip="Pieces of text per step" />
        <Seg label="LEARNING RATE" k="lr" opts={SEG.lr} cfg={cfg} set={set} show={v => v.toExponential(0)} tip="How big each correction is (warms up, then cools down)" />
      </div>
      <div className="mlf-card"><h4>② THE MODEL YOU ARE BUILDING</h4><Stack cfg={cfg} sp={sp} /></div>
      <div className="mlf-card"><h4>③ SPECS · LIVE</h4>
        {sp ? <div className="mlf-specs" data-testid="mlf-specs">
          <span className="mlf-ring" style={{ '--k': pctCap }} data-tip={`Parameters: every number it learns. Cap on this Mac ${fmt(f.limits.params)}`}><Big v={sp.paramsTotal} /><small>PARAMETERS</small></span>
          <dl className="mlf-kv">
            <dt>Weights</dt><dd className="m-num">{sp.weightsMb} MB</dd><dt>Training memory</dt><dd className="m-num">{sp.trainMb} MB</dd>
            <dt>Compute per token</dt><dd className="m-num">{fmt(sp.flopsPerToken)} FLOPs</dd><dt>This Mac</dt><dd className="m-num">{sp.flopsRate ? `${sp.flopsRate} GFLOP/s` : '—'}</dd>
            <dt>Head size</dt><dd className="m-num">{sp.headDim}</dd><dt>Your data</dt><dd className="m-num">{fmt(sp.corpusTokens)} tokens</dd><dt>Reads it</dt><dd className="m-num">{sp.epochs}×</dd>
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
    <div className="mlf-go"><button type="button" className="m-btn m-go" disabled={busy || live || sp?.tooBig} onClick={build} data-tip="Starts the build as its own process on this Mac, one at a time; the site keeps its speed" data-testid="mlf-build">🔨 Train {famName} {nextV}</button>
      {base ? <label className="m-toggle" data-tip={`On: ${nextV} starts from ${base.version}'s weights and tokenizer (${fmt(base.card.totalSteps || base.card.steps)} steps already learned). Off: it starts from random numbers`}><input type="checkbox" checked={cont} onChange={e => setCont(e.target.checked)} data-testid="mlf-cont" /> Continue from {base.version}</label>
        : <small className="mlf-fresh">{versions.length ? 'No version with this shape yet: it starts fresh' : 'The first version: it starts fresh'}</small>}
      <small>{live ? 'A build is running — watch it learn below.' : `≈ ${sp ? secs(sp.estSec) : '…'} on this Mac · stop any time, it keeps what it learned`}</small></div>
    {job ? <section className="mlf-card mlf-run" data-testid="mlf-run"><h4>⑤ {live ? 'LEARNING LIVE' : 'LAST BUILD'} · {job.version || job.name || job.id}{job.base ? <em className="m-chip">from {job.base}</em> : null}<span className={`m-chip${job.status === 'failed' ? ' bad' : job.status === 'done' ? ' ok' : ' warn'}`}>{job.status}</span></h4>
      <Pipe live={live} status={job.status} />
      <div className="mlf-runbar" data-tip={`${job.step || 0} of ${job.steps} steps`}><u style={{ transform: `scaleX(${job.steps ? (job.step || 0) / job.steps : 0})` }} /></div>
      <div className="mlf-runstats"><span><small>STEP</small><b className="m-num">{job.step || 0}/{job.steps}</b></span><span><small>LOSS</small><b className="m-num">{job.loss ?? '—'}</b></span><span><small>HELD-OUT LOSS</small><b className="m-num">{job.val ?? '—'}</b></span>
        <span><small>LEARNING RATE</small><b className="m-num">{chart.length && chart[chart.length - 1].lr ? chart[chart.length - 1].lr.toExponential(1) : '—'}</b></span><span><small>GRAD NORM</small><b className="m-num">{chart.length && chart[chart.length - 1].g != null ? chart[chart.length - 1].g : '—'}</b></span>
        <span><small>SPEED</small><b className="m-num">{job.tps ? `${fmt(job.tps)} tok/s` : '—'}</b></span><span><small>{live ? 'LEFT' : 'TOOK'}</small><b className="m-num">{live ? secs(job.eta) : secs(job.elapsed)}</b></span>
        {live ? <button type="button" className="m-btn" onClick={stop} data-tip="Ends at the next step and keeps the weights it reached" data-testid="mlf-stop">⏹ Stop</button> : null}</div>
      {job.error ? <p className="kd-err">⚠ {job.error}</p> : null}
      {chart.length > 1 ? <div className="mlf-charts">
        <div className="mlf-chart" data-tip="Loss = how surprised it is by the next token. Falling = learning. Held-out = text it never trained on"><small className="m-label">LOSS</small><ResponsiveContainer width="100%" height={170}><LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
          <XAxis dataKey="s" tick={axis} /><YAxis tick={axis} domain={['auto', 'auto']} /><Tooltip contentStyle={tipStyle} />
          <Line type="monotone" dataKey="train" stroke="#b48cff" strokeWidth={2} dot={false} isAnimationActive={false} name="loss" /><Line type="monotone" dataKey="val" stroke="#3ee7ff" strokeWidth={2} dot={false} isAnimationActive={false} name="held-out" /></LineChart></ResponsiveContainer></div>
        {chart.some(x => x.lr) ? <div className="mlf-chart" data-tip="Learning rate warms up then cools on a cosine. Gradient norm = how hard the step pushes (clipped at 1)"><small className="m-label">LEARNING RATE · GRAD NORM</small><ResponsiveContainer width="100%" height={170}><LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
          <XAxis dataKey="s" tick={axis} /><YAxis yAxisId="lr" tick={axis} tickFormatter={v => v.toExponential(0)} /><YAxis yAxisId="g" orientation="right" tick={axis} /><Tooltip contentStyle={tipStyle} />
          <Line yAxisId="lr" type="monotone" dataKey="lr" stroke="#ff3fa4" strokeWidth={2} dot={false} isAnimationActive={false} name="learning rate" /><Line yAxisId="g" type="monotone" dataKey="g" stroke="#3cf0c5" strokeWidth={1.5} dot={false} isAnimationActive={false} name="grad norm" /></LineChart></ResponsiveContainer></div> : null}
      </div> : null}
      <Learning job={job} />
    </section> : null}
    {built.length ? <section className="mlf-card" data-testid="mlf-models"><h4>⑥ {versions.length ? `${famName.toUpperCase()} · VERSIONS` : 'YOUR MODELS'} · ASK ONE</h4>
      <Versions built={board} pick={pick} setPick={id => { setPick(id); setAns(null); }} />
      {pick ? <div className="mlf-ask"><textarea className="m-input" value={q} maxLength={2000} onChange={e => setQ(e.target.value)} aria-label="Ask your model" data-testid="mlf-q" />
        <label className="mlf-temp" data-tip="Low = safest guess each time · high = more surprising"><small className="m-label">CREATIVITY {temp.toFixed(1)}</small><input type="range" min="0.1" max="1.6" step="0.1" value={temp} onChange={e => setTemp(Number(e.target.value))} /></label>
        <button type="button" className="m-btn m-go" disabled={busy || !q.trim()} onClick={ask} data-testid="mlf-ask">Ask it</button>
        {ans ? <div className="mlf-ans" data-testid="mlf-ans"><div><small className="m-label">WHAT YOU SEE (guardrails on)</small><pre>{ans.answer}</pre></div><div><small className="m-label">RAW MODEL</small><pre>{ans.raw || '— the model never ran —'}</pre></div>
          <span className="mlf-fired">{ans.fired.length ? ans.fired.map(x => <em key={x.rule + x.detail} className="m-chip">{x.rule}: {x.detail}</em>) : <em className="m-chip ok">no rule fired</em>}{ans.ms ? <small>{ans.ms} ms</small> : null}</span></div> : null}
        {picked?.card?.sample ? <small className="mlf-sample">Its own words at the end of the build: “{picked.card.sample.slice(0, 160)}”</small> : null}</div> : null}
      {picked ? <div className="mlf-grid mlf-ops"><div><small className="m-label">⑦ WHERE IT LIVES</small><Files job={picked} folder={f.folder} call={call} setErr={setErr} /></div>
        <div><small className="m-label">⑧ GUARDRAIL SUITE</small><Rails job={picked} call={call} setErr={setErr} /></div></div> : null}
    </section> : null}
    <section className="mlf-card mlf-labs" data-testid="mlf-labs"><h4>⑨ FROM THE LABS · NOT IN COMP'S ENGINE YET</h4>
      <ul>{LABS.map(([t, who, say], i) => <li key={t} style={{ '--i': i }}><span><b>{t}</b><em>{who}</em></span><small>{say}</small><u className="m-chip">not built</u></li>)}</ul>
      <small className="mlb-note">These are what the big labs use today. Each becomes a switch here only once the engine runs it and a test checks its gradients.</small></section>
  </div>;
}

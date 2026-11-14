import React, { useCallback, useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Brain, Globe, GraduationCap, RefreshCw, Scale, Target, ThumbsUp } from 'lucide-react';
import { useCountUp } from '../../lib/useCountUp';
import { examVerdict } from './CompExplain';
import { CompRace } from './CompRace';
import '../../styles/compExplain.css';
import '../../styles/comp2.css';

// 🚀 COMP v2 · 9B (owner 2026-11-12: "see how close or farther it is from being better or same as claude and gpt"). LIVE: Qwen3.5-9B on this
// Mac, LoRA fine-tuned with MLX on the owner's settled proofs (only what each proof said BEFORE it settled), then examined on held-out proofs
// it never saw, next to the untouched base, an always-the-majority baseline and the flagship APIs whose keys are saved. Nothing is spent
// unless a flagship key is saved (then at most 40 questions each).
// 🎨 Redone 2026-11-14 (owner: "explain why the design for COMP AI is so damn bad … redo COMP"): the score comes first — COMP's hit rate in
// big type and every model ranked against the always-guess line — then per proof type, the race, ONE training panel (was two loss charts),
// and a compact "how it learns" list. Plain words; the jargon lives in the tips.
const tipStyle = { background: 'var(--m-surface)', border: '1px solid var(--m-line-hi)', borderRadius: 8, fontSize: 11, color: 'var(--m-text)' };
const axis = { fontSize: 10, fill: 'var(--m-dim)' };
const KIND = { local: 'on this Mac', baseline: 'always guesses the majority', flagship: 'flagship API', own: 'its own LM Studio' };
const pct = v => `${Math.round((v || 0) * 100)}%`;
const ours = id => id === 'comp' || id === 'comp_mem';
function Num({ v, d = 0, suf = '' }) { const n = useCountUp(Number(v) || 0); return <b className="m-num">{n.toFixed(d)}{suf}</b>; }

// 🏆 THE SCORE: COMP's best hit rate, big, and every scored model ranked on one scale with the always-guess line through it
function Score({ exam }) {
  const scored = exam.examinees.filter(e => e.score); const blocked = exam.examinees.filter(e => !e.score);
  const base = scored.find(e => e.id === 'baseline')?.score.acc ?? 0; const best = Math.max(...scored.map(e => e.score.acc), 0);
  const rows = [...scored].sort((a, b) => b.score.acc - a.score.acc);
  const comp = rows.find(e => ours(e.id)); const rank = comp ? rows.filter(e => e.kind !== 'baseline').findIndex(e => e.id === comp.id) + 1 : 0;
  const field = rows.filter(e => e.kind !== 'baseline' && (!ours(e.id) || e.id === comp?.id)).length;
  return <section className="c2-hero m-card" data-testid="mc2-score">
    <div className="c2-big">
      <small className="m-label">COMP · RIGHT ON PROOFS IT NEVER SAW</small>
      <span className="c2-pct">{comp ? <Num v={comp.score.acc * 100} suf="%" /> : <b className="m-num">—</b>}</span>
      <span className="c2-sub">{comp ? `${comp.score.right} of ${comp.score.n} · ${comp.name}` : 'not examined yet'}</span>
      {comp ? <span className={`c2-rank${rank === 1 ? ' is-top' : ''}`} data-tip="Its place among every model that sat this exam (the always-guess line is not a model)">#{rank} <small>of {field}</small></span> : null}
      {base ? <span className="c2-vs" data-tip="A model that always answers the most common result gets this much right for free: COMP has to beat it">
        {comp ? `${comp.score.acc > base ? '+' : ''}${Math.round((comp.score.acc - base) * 100)} pts vs always-guess (${pct(base)})` : `always-guess gets ${pct(base)}`}</span> : null}
    </div>
    <ul className="c2-board mc2-board" data-testid="mc2-board">{rows.map((e, i) => <li key={e.id} style={{ '--i': i }} className={`${ours(e.id) ? 'is-comp' : ''}${e.kind === 'baseline' ? ' is-baseline' : ''}`} data-testid={`mc2-ex-${e.id}`}
      data-tip={`${e.score.right} of ${e.score.n} right${e.score.unsure ? ` · ${e.score.unsure} gave no answer` : ''}${e.seconds ? ` · took ${e.seconds}s` : ''}`}>
      <span className="c2-who"><b>{e.name}</b><small>{KIND[e.kind] || e.kind}</small></span>
      <i className="c2-bar" style={{ '--b': base }}><u style={{ transform: `scaleX(${Math.max(0.02, e.score.acc)})` }} /></i>
      <span className={`m-num mc2-acc${e.score.acc === best ? ' is-top' : ''}${e.kind !== 'baseline' && e.score.acc <= base ? ' is-under' : ''}`}>{pct(e.score.acc)}</span>
    </li>)}</ul>
    {blocked.length ? <ul className="c2-blocked" aria-label="Not scored">{blocked.map(e => <li key={e.id} data-testid={`mc2-ex-${e.id}`} data-tip={e.blocked}><b>{e.name}</b> <small>{/no key/i.test(e.blocked || '') ? 'no key' : 'not scored'}</small></li>)}
      <li className="c2-blocked-how">Add a key in HQ › Agents and run the exam again (40 questions max each).</li></ul> : null}
  </section>;
}

// 📊 BY PROOF TYPE: COMP vs the untouched base, % right per type, with the counts on the bars
function Kinds({ exam }) {
  const comp = exam.examinees.find(e => e.id === 'comp' && e.score); const base = exam.examinees.find(e => e.id === 'base' && e.score);
  if (!comp) return null;
  const data = Object.entries(comp.score.kinds).map(([k, v]) => { const b = base?.score.kinds[k]; return { k, comp: v.n ? Math.round((v.right / v.n) * 100) : 0, cl: `${v.right}/${v.n}`, base: b?.n ? Math.round((b.right / b.n) * 100) : 0, bl: b ? `${b.right}/${b.n}` : '' }; });
  return <section className="c2-card m-card" data-testid="mc2-kinds"><h4 className="c2-h">BY PROOF TYPE <small>% right · COMP vs the base it started from</small></h4>
    <ResponsiveContainer width="100%" height={Math.max(150, data.length * 46)}><BarChart data={data} layout="vertical" margin={{ top: 4, right: 44, bottom: 0, left: 4 }} barGap={2} barCategoryGap={10}>
      <XAxis type="number" domain={[0, 100]} hide /><YAxis type="category" dataKey="k" width={72} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: 'var(--m-text)' }} />
      <Tooltip contentStyle={tipStyle} cursor={{ fill: 'transparent' }} formatter={(v, n, p) => [`${v}% (${n === 'comp' ? p.payload.cl : p.payload.bl})`, n === 'comp' ? 'COMP' : 'base']} />
      <Bar dataKey="comp" fill="var(--m-accent)" radius={[0, 4, 4, 0]} isAnimationActive={false} barSize={12}><LabelList dataKey="cl" position="right" style={{ fontSize: 10, fill: 'var(--m-text)' }} /></Bar>
      {base ? <Bar dataKey="base" fill="var(--m-line-hi)" radius={[0, 4, 4, 0]} isAnimationActive={false} barSize={8}><LabelList dataKey="bl" position="right" style={{ fontSize: 9, fill: 'var(--m-dim)' }} /></Bar> : null}
    </BarChart></ResponsiveContainer>
    <ul className="c2-key"><li style={{ '--c': 'var(--m-accent)' }}><i />COMP</li>{base ? <li style={{ '--c': 'var(--m-line-hi)' }}><i />base (before training)</li> : null}</ul>
  </section>;
}

// 🏋 TRAINING: one panel — state, progress, the controls and ONE learning curve (training + held-out)
function Training({ d, busy, live, iters, setIters, go }) {
  const run = d.run; const c = run.curve || { train: [], val: [] }; const ds = d.dataset; const phase = run.running ? 'train' : d.examRunning ? 'exam' : 'idle';
  const at = run.iters ? Math.min(1, (c.last || 0) / run.iters) : 0; const last = c.train[c.train.length - 1]?.[1];
  const chart = [...new Set([...c.train, ...c.val].map(x => x[0]))].sort((a, b) => a - b).map(s => ({ s, train: c.train.find(x => x[0] === s)?.[1], val: c.val.find(x => x[0] === s)?.[1] }));
  const say = phase === 'train' ? 'Training now' : phase === 'exam' ? 'Sitting the exam now' : run.done ? 'Trained' : run.error ? 'Stopped' : 'Not trained yet';
  return <section className={`c2-card c2-train m-card is-${phase}`} data-testid="mc2-live">
    <header className="c2-train-head">
      <span className="c2-state"><i className={phase === 'idle' ? '' : 'is-on'} aria-hidden="true" />{say}</span>
      <b className="m-num">{c.last || 0} / {run.iters || 0} <small>iters</small></b>
      <i className="c2-prog" data-tip={`${pct(at)} of the training run`}><u style={{ transform: `scaleX(${Math.max(0.02, at)})` }} /></i>
      {last != null ? <span className="c2-loss" data-tip="How wrong it still is on your proofs it trains on (lower = better)">error <b className="m-num">{Number(last).toFixed(3)}</b></span> : null}
    </header>
    <div className="c2-facts">
      <span data-tip="The open model it starts from. Its own weights stay untouched; COMP is a small add-on trained on top"><small>STARTS FROM</small><b>{d.base.name}</b><em className={`m-chip${d.base.ready ? ' ok' : ' warn'}`}>{d.base.ready ? 'on this Mac' : 'missing'}</em></span>
      <span data-tip="Settled proofs it learns from (flat ones dropped)"><small>LEARNS FROM</small><Num v={ds?.train} /><em>proofs</em></span>
      <span data-tip="Held-out proofs only the exam uses: never trained on"><small>EXAM</small><Num v={ds?.test} /><em>proofs</em></span>
      <span data-tip="How the proofs it learns from ended"><small>WON / LOST</small><b className="m-num">{ds ? `${ds.won} / ${ds.lost}` : '—'}</b></span>
    </div>
    {chart.length > 1 ? <div className="c2-curve" data-tip="Lower = it predicts how a proof ends better. Held-out = proofs it does not train on: if that line rises while training falls, it is memorising">
      <ResponsiveContainer width="100%" height={150}><LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -14 }}>
        <CartesianGrid vertical={false} stroke="var(--m-line)" /><XAxis dataKey="s" tick={axis} tickLine={false} axisLine={false} /><YAxis tick={axis} tickLine={false} axisLine={false} domain={['auto', 'auto']} width={40} />
        <Tooltip contentStyle={tipStyle} formatter={(v, n) => [Number(v).toFixed(3), n]} labelFormatter={s => `step ${s}`} />
        <Line type="monotone" dataKey="train" name="on its training proofs" stroke="var(--m-accent)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
        <Line type="monotone" dataKey="val" name="on held-out proofs" stroke="var(--m-warn)" strokeWidth={2} dot={{ r: 2.5 }} isAnimationActive={false} connectNulls /></LineChart></ResponsiveContainer>
      <ul className="c2-key"><li style={{ '--c': 'var(--m-accent)' }}><i />error on its training proofs</li><li style={{ '--c': 'var(--m-warn)' }}><i />error on held-out proofs</li></ul></div>
      : <p className="mlb-none">The learning curve draws here while it trains.</p>}
    {run.error ? <p className="kd-err">⚠ {run.error}</p> : null}
    <div className="c2-go">
      <label className="c2-iters" data-tip="How many proofs it studies, one at a time (99 = one pass). More = fits them tighter, and risks memorising"><small className="m-label">STUDY</small>
        <span className="m-seg" role="group" aria-label="Iterations">{[100, 200, 400].map(n => <button key={n} type="button" className={iters === n ? 'active' : ''} aria-pressed={iters === n} data-tip={`${n} steps`} onClick={() => setIters(n)} data-testid={`mc2-iters-${n}`}>{n}</button>)}</span></label>
      <button type="button" className="m-btn m-go" disabled={busy || live || !d.base.ready} onClick={() => go('/admin/model-lab/comp2/train', { iters })} data-tip="Rebuilds the rows from your live proofs (same held-out exam) and trains a new COMP here. Takes minutes, costs nothing" data-testid="mc2-train">Train COMP</button>
      <button type="button" className="m-btn" disabled={busy || live || !ds} onClick={() => go('/admin/model-lab/comp2/exam')} data-tip="COMP vs the base vs always-guess vs your OSSY + G4 (each on its own LM Studio, free) vs every flagship whose key is saved, on the same held-out proofs" data-testid="mc2-exam">Run the exam</button>
    </div>
  </section>;
}

// 🧬 HOW COMP LEARNS: every way, with its real state. LIVE = running now on real data; NOT BUILT = said plainly, never implied.
function Ways({ d, busy, collect }) {
  const m = d.market || {}; const mem = (d.exam?.examinees || []).find(e => e.id === 'comp_mem');
  const W = [
    [Target, 'Studies your proofs', 'Fine-tune (LoRA) on the 9B: what a proof said before it settled → how it ended', 'live', d.dataset ? `${d.dataset.train - (d.dataset.net || 0)} proofs` : ''],
    [Globe, 'Learns from the market', 'Snapshots live Solana coins on DexScreener every 10 min, settles each an hour later (+20% won · −20% or rugged lost). Train only, never more rows than yours', m.collects ? 'live' : 'wait', m.collects ? `${m.rows || 0} rows · ${m.open || 0} holding` : 'starts with the backend'],
    [Brain, 'Remembers similar proofs', 'Before it answers, it reads the 5 past proofs most like this one and how they ended. A proof settled an hour ago helps right away', mem ? 'live' : 'wait', mem ? `${Math.round(mem.score.acc * 100)}% on the exam` : 'next exam'],
    [ThumbsUp, 'Your grades', 'Your 👍 / 👎 on open proofs (Data & grades tab) become rows where no market settled them', 'live', ''],
    [Scale, 'Learns which answer is better', 'Right-vs-wrong pairs teach it which of two answers is better (DPO)', 'todo', 'not built'],
    [GraduationCap, 'Learns the reasons', 'A bigger Apache-2.0 open model writes the why behind each result; COMP learns the reasoning', 'todo', 'not built · needs ~20 GB model'],
    [RefreshCw, 'Retrains as proofs settle', 'A new COMP each night, kept only if it beats the last one on the exam', 'todo', 'not built'],
  ];
  return <section className="c2-card m-card"><h4 className="c2-h">HOW COMP LEARNS <small>{W.filter(w => w[3] === 'live').length} of {W.length} live</small></h4>
    <ul className="c2-ways mc2-ways" data-testid="mc2-ways">{W.map(([Ic, t, say, st, n], i) => <li key={t} className={`is-${st}`} style={{ '--i': i }} data-tip={say}>
      <i aria-hidden="true"><Ic size={15} strokeWidth={1.75} /></i><b>{t}</b><u className="m-num">{n}</u><em className={`m-chip${st === 'live' ? ' ok' : st === 'wait' ? ' warn' : ''}`}>{st === 'live' ? 'LIVE' : st === 'wait' ? 'WAITING' : 'NOT BUILT'}</em></li>)}</ul>
    <button type="button" className="m-btn c2-collect" disabled={busy} onClick={collect} data-tip="One snapshot + settle pass on DexScreener now (it also runs every 10 minutes)" data-testid="mc2-collect">Collect market rows now</button>
  </section>;
}

export function ModelComp2({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [iters, setIters] = useState(200);
  const load = useCallback(() => (call ? call('/admin/model-lab/comp2').then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message)) : Promise.resolve()), [call]);
  const live = !!(d?.run?.running || d?.examRunning);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!live) return undefined; const t = setInterval(load, 5000); return () => clearInterval(t); }, [live, load]);
  const go = async (path, body) => { setBusy(true); try { setD(await call(path, { method: 'POST', body: JSON.stringify(body || {}) })); setErr(''); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (!d) return <div className="mc2" data-testid="mc2">{err ? <p className="kd-err" role="alert">⚠ {err}</p> : <p className="mlb-none">Reading COMP v2…</p>}</div>;
  const verdict = d.exam ? examVerdict(d.exam) : '';
  return <div className="mc2" data-testid="mc2">
    <p className="c2-what">A real 9-billion-parameter open model, trained on this Mac on your proofs, then tested on proofs it never saw: from what a proof said <b>before</b> it settled, did it win or lose?</p>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    {d.exam ? <Score exam={d.exam} /> : <section className="c2-hero m-card"><p className="mlb-none">Train it, then run the exam: every model answers the same held-out proofs and the score lands here.</p></section>}
    {verdict ? <p className="c2-verdict" data-testid="mc2-verdict">{verdict}</p> : null}
    <div className="c2-two">
      {d.exam ? <Kinds exam={d.exam} /> : null}
      <section className="c2-card m-card"><h4 className="c2-h">THE RACE <small>{d.examRunning ? 'sitting it now…' : d.exam ? `exam of ${d.exam.n} · ${new Date(d.exam.at * 1000).toLocaleDateString()}` : 'not sat yet'}</small></h4>
        <CompRace race={d.race} exam={d.exam} running={d.examRunning} /></section>
    </div>
    <Training d={d} busy={busy} live={live} iters={iters} setIters={setIters} go={go} />
    <Ways d={d} busy={busy} collect={() => go('/admin/model-lab/comp2/collect')} />
  </div>;
}

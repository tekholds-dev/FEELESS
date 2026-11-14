import React, { useCallback, useEffect, useState } from 'react';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ProgressCircle } from '@heroui/react';
import { Brain, Globe, GraduationCap, RefreshCw, Scale, Target, ThumbsUp } from 'lucide-react';
import { useCountUp } from '../../lib/useCountUp';
import { examVerdict } from './CompExplain';

// 🚀 COMP v2 · 9B (owner 2026-11-12: "see how close or farther it is from being better or same as claude and gpt"). LIVE: Qwen3.5-9B on this
// Mac, LoRA fine-tuned with MLX on the owner's settled proofs (only what each proof said BEFORE it settled), then examined on held-out proofs
// it never saw, next to the untouched base, an always-the-majority baseline and the flagship APIs whose keys are saved. Nothing is spent
// unless a flagship key is saved (then at most 40 questions each).
const tipStyle = { background: '#0e0e12', border: '1px solid #ffffff1f', borderRadius: 8, fontSize: 11, color: '#ececf1' };
const axis = { fontSize: 10, fill: '#8b8b95' };
const KIND = { local: 'ON THIS MAC', baseline: 'BASELINE', flagship: 'FLAGSHIP API' };
const pct = v => `${Math.round((v || 0) * 100)}%`;
function Num({ v, d = 0, suf = '' }) { const n = useCountUp(Number(v) || 0); return <b className="m-num">{n.toFixed(d)}{suf}</b>; }

function Board({ exam }) {
  const scored = exam.examinees.filter(e => e.score); const best = Math.max(...scored.map(e => e.score.acc), 0);
  const base = scored.find(e => e.id === 'baseline')?.score.acc ?? 0;
  const rows = [...exam.examinees].sort((a, b) => (b.score?.acc ?? -1) - (a.score?.acc ?? -1));
  return <ul className="mc2-board" data-testid="mc2-board">{rows.map((e, i) => <li key={e.id} style={{ '--i': i }} className={e.id === 'comp' ? 'is-comp' : ''} data-testid={`mc2-ex-${e.id}`}>
    <span className="mc2-who"><b>{e.name}</b><small>{KIND[e.kind]}{e.seconds ? ` · ${e.seconds}s` : ''}{e.raw ? ` · top word ${pct(e.raw.acc)}` : ''}</small></span>
    {e.score ? <><i className="mlb-bar mc2-bar" data-tip={`${e.score.right} of ${e.score.n} right${e.score.unsure ? ` · ${e.score.unsure} gave no answer` : ''}${e.raw ? ` · its top word alone: ${pct(e.raw.acc)} · confidence cut ${e.cut} tuned on the valid proofs` : ''}. The line marks the baseline (${pct(base)})`} style={{ '--b': base }}>
      <u style={{ transform: `scaleX(${Math.max(0.02, e.score.acc)})` }} /></i>
      <span className={`m-num mc2-acc${e.score.acc === best ? ' is-top' : ''}${e.kind !== 'baseline' && e.score.acc <= base ? ' is-under' : ''}`}>{pct(e.score.acc)}</span></>
      : <><span className="mc2-blocked" data-tip="Not scored: nothing was guessed for it">{e.blocked}</span><span /></>}
  </li>)}</ul>;
}

function Kinds({ exam }) {   // per proof type: where COMP v2 is right vs the base
  const comp = exam.examinees.find(e => e.id === 'comp' && e.score); const base = exam.examinees.find(e => e.id === 'base' && e.score);
  if (!comp) return null;
  return <ul className="mc2-kinds" data-testid="mc2-kinds">{Object.entries(comp.score.kinds).map(([k, v], i) => { const b = base?.score.kinds[k]; return <li key={k} style={{ '--i': i }}>
    <span className="m-chip">{k}</span><span className="m-num">{v.right}/{v.n}</span><i className="mlb-bar"><u style={{ transform: `scaleX(${v.n ? v.right / v.n : 0})` }} /></i>
    <small>{b ? `base ${b.right}/${b.n}` : ''}</small></li>; })}</ul>;
}


// 📈 LIVE RUN (owner 2026-11-12: "never build charts and displays from scratch … find the best component sources"): a HeroUI ProgressCircle
// for the run, a shadcn-style Recharts area for the live loss (gradient fill, hairline grid, card tooltip), the real numbers big and quiet.
function Live({ d, phase }) {
  const c = d.run.curve || { train: [], val: [] }; const tr = c.train; const last = tr[tr.length - 1]?.[1]; const prev = tr[tr.length - 2]?.[1];
  const loss = useCountUp(Number(last) || 0); const at = d.run.iters ? Math.min(1, (c.last || 0) / d.run.iters) : 0;
  const done = (d.exam?.examinees || []).filter(e => e.score || e.blocked);
  const say = phase === 'train' ? 'Training' : phase === 'exam' ? 'Sitting the exam' : d.run.done ? 'Trained' : 'Idle';
  return <div className={`mc2-live is-${phase}`} data-testid="mc2-live">
    <div className="mc2-run-card">
      <ProgressCircle aria-label="Run progress" value={Math.round(at * 100)} className="mc2-pc"><ProgressCircle.Track><ProgressCircle.TrackCircle /><ProgressCircle.FillCircle /></ProgressCircle.Track></ProgressCircle>
      <div className="mc2-run-say"><span className="mc2-state"><i className={phase === 'idle' ? '' : 'is-on'} />{say}</span>
        <b className="m-num">{c.last || 0}<small> / {d.run.iters || 0} iters</small></b>
        <span className="mc2-loss-line" data-tip="Loss on the answer word, last report. Lower = surer and right">loss <b className="m-num">{last != null ? loss.toFixed(3) : '—'}</b>{prev != null && last != null ? <em className={last <= prev ? 'is-dn' : 'is-up'}>{last <= prev ? '↓' : '↑'} {Math.abs(last - prev).toFixed(3)}</em> : null}</span>
        {done.length ? <span className="mc2-done">{done.map(e => <em key={e.id} className={e.score ? 'is-ok' : ''}>{e.id}</em>)}</span> : null}</div>
    </div>
    <div className="mc2-area" data-tip="Training loss per report: falling = it is learning your proofs">
      {tr.length > 1 ? <ResponsiveContainer width="100%" height={132}><AreaChart data={tr.map(([s, v]) => ({ s, v }))} margin={{ top: 8, right: 4, bottom: 0, left: -22 }}>
        <defs><linearGradient id="mc2fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#9b6bff" stopOpacity={0.35} /><stop offset="100%" stopColor="#9b6bff" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid vertical={false} stroke="#ffffff0f" /><XAxis dataKey="s" tick={axis} tickLine={false} axisLine={false} /><YAxis tick={axis} tickLine={false} axisLine={false} width={44} />
        <Tooltip contentStyle={tipStyle} cursor={{ stroke: '#ffffff22' }} formatter={v => [Number(v).toFixed(3), 'loss']} labelFormatter={s => `iter ${s}`} />
        <Area type="monotone" dataKey="v" stroke="#b48cff" strokeWidth={1.75} fill="url(#mc2fill)" isAnimationActive={false} /></AreaChart></ResponsiveContainer>
        : <p className="mlb-none">The loss draws here while it trains.</p>}
    </div>
  </div>;
}

// 🧬 HOW COMP LEARNS: every way, with its real state. LIVE = running now on real data; NOT BUILT = said plainly, never implied.
function Ways({ d, busy, collect }) {
  const m = d.market || {}; const mem = (d.exam?.examinees || []).find(e => e.id === 'comp_mem');
  const W = [
    [Target, 'Fine-tune on your proofs', 'LoRA on the 9B: what a proof said before it settled → how it ended', 'live', d.dataset ? `${d.dataset.train - (d.dataset.net || 0)} proofs` : ''],
    [Globe, 'Learns from the market itself', 'Snapshots live Solana coins on DexScreener every 10 min, settles each one an hour later (+20% won · −20% or rugged lost). Train only, never more rows than yours', m.collects ? 'live' : 'wait', m.collects ? `${m.rows || 0} rows · ${m.open || 0} holding` : 'starts with the backend'],
    [Brain, 'Memory recall', 'Before it answers, it reads the 5 past proofs most like this one and how they ended. A proof settled an hour ago helps right away', mem ? 'live' : 'wait', mem ? `${Math.round(mem.score.acc * 100)}% on the exam` : 'next exam'],
    [ThumbsUp, 'Your grades', 'Your 👍 / 👎 on open proofs (Data & grades tab) become rows where no market settled them', 'live', ''],
    [Scale, 'Preference training', 'Right-vs-wrong pairs teach it which of two answers is better (DPO)', 'todo', 'not built'],
    [GraduationCap, 'Open-teacher reasons', 'A bigger Apache-2.0 open model writes the why behind each result; COMP learns the reasoning (licence allows it)', 'todo', 'not built · needs ~20 GB model'],
    [RefreshCw, 'Retrains as proofs settle', 'A new adapter each night, kept only if it beats the last one on the exam', 'todo', 'not built'],
  ];
  return <section className="mlb-sec"><h4>HOW COMP LEARNS<small>{W.filter(w => w[3] === 'live').length} of {W.length} live</small></h4>
    <ul className="mc2-ways" data-testid="mc2-ways">{W.map(([Ic, t, say, st, n], i) => <li key={t} className={`is-${st}`} style={{ '--i': i }} data-tip={say}>
      <i aria-hidden="true"><Ic size={16} strokeWidth={1.75} /></i><span><b>{t}</b><small>{say}</small></span><em className={`m-chip${st === 'live' ? ' ok' : st === 'wait' ? ' warn' : ''}`}>{st === 'live' ? 'LIVE' : st === 'wait' ? 'WAITING' : 'NOT BUILT'}</em>{n ? <u className="m-num">{n}</u> : null}</li>)}</ul>
    <button type="button" className="m-btn mc2-collect" disabled={busy} onClick={collect} data-tip="One snapshot + settle pass on DexScreener now (it also runs every 10 minutes)" data-testid="mc2-collect">Collect market rows now</button>
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
  const ds = d.dataset; const run = d.run; const c = run.curve || { train: [], val: [] };
  const chart = [...new Set([...c.train, ...c.val].map(x => x[0]))].sort((a, b) => a - b).map(s => ({ s, train: c.train.find(x => x[0] === s)?.[1], val: c.val.find(x => x[0] === s)?.[1] }));
  const at = run.iters ? Math.min(1, (c.last || 0) / run.iters) : 0;
  return <div className="mc2" data-testid="mc2">
    <Live d={d} phase={d.run.running ? 'train' : d.examRunning ? 'exam' : 'idle'} />
    <p className="mlb-truth">A real 9-billion-parameter open model, fine-tuned on this Mac on your proofs, then examined on proofs it never saw. The question: from what a proof said before it settled, did it win or lose?</p>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <section className="mc2-top">
      <div className="mc2-base" data-tip="The open-weights base it starts from: its own weights stay untouched, COMP v2 is a small adapter on top">
        <small className="m-label">BASE MODEL</small><b>{d.base.name}</b><span><em className={`m-chip${d.base.ready ? ' ok' : ' warn'}`}>{d.base.ready ? 'ON THIS MAC' : 'MISSING'}</em><em className="m-chip">{d.base.params} · {d.base.bits}-bit</em><em className="m-chip">{d.base.engine}</em></span></div>
      <div className="mc2-stat" data-tip="Settled proofs it learns from (flat ones dropped)"><Num v={ds?.train} /><small>TRAIN</small></div>
      <div className="mc2-stat" data-tip="Held-out proofs the exam grades: never trained on"><Num v={ds?.test} /><small>EXAM</small></div>
      <div className="mc2-stat" data-tip="Won vs lost across every row"><b className="m-num">{ds ? `${ds.won}/${ds.lost}` : '—'}</b><small>WON / LOST</small></div>
    </section>
    <section className="mlb-sec"><h4>FINE-TUNE · LoRA ON THE 9B<small>{run.running ? `iter ${c.last || 0} of ${run.iters}` : run.done ? `done · ${run.iters} iters` : run.error ? 'stopped' : 'not run yet'}</small></h4>
      <div className="mc2-go">
        <label className="mc2-iters" data-tip="Proofs it studies, one at a time (99 = one pass). More = fits them tighter (and risks memorising)"><small className="m-label">ITERS</small>
          <span className="m-seg" role="group" aria-label="Iterations">{[100, 200, 400].map(n => <button key={n} type="button" className={iters === n ? 'active' : ''} aria-pressed={iters === n} data-tip={`${n} iterations`} onClick={() => setIters(n)} data-testid={`mc2-iters-${n}`}>{n}</button>)}</span></label>
        <button type="button" className="m-btn m-go" disabled={busy || live || !d.base.ready} onClick={() => go('/admin/model-lab/comp2/train', { iters })} data-tip="Rebuilds the rows from your live proofs (same held-out exam) and trains a new adapter here. Takes minutes, costs nothing" data-testid="mc2-train">Train COMP v2</button>
        <button type="button" className="m-btn" disabled={busy || live || !ds} onClick={() => go('/admin/model-lab/comp2/exam')} data-tip="Base vs COMP v2 vs baseline vs every flagship whose key is saved, on the same held-out proofs" data-testid="mc2-exam">Run the exam</button>
        {run.running ? <i className="mlb-bar mc2-run" data-tip={`${pct(at)} of the run`}><u style={{ transform: `scaleX(${Math.max(0.02, at)})` }} /></i> : null}
      </div>
      {run.error ? <p className="kd-err">⚠ {run.error}</p> : null}
      {chart.length > 1 ? <div className="mlf-chart" data-tip="Loss on the answer word only (the prompt is masked). Held-out = proofs it does not train on"><small className="m-label">LOSS</small><ResponsiveContainer width="100%" height={160}><LineChart data={chart} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
        <XAxis dataKey="s" tick={axis} /><YAxis tick={axis} domain={['auto', 'auto']} /><Tooltip contentStyle={tipStyle} />
        <Line type="monotone" dataKey="train" stroke="#b48cff" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls name="loss" /><Line type="monotone" dataKey="val" stroke="#3ee7ff" strokeWidth={2} dot isAnimationActive={false} connectNulls name="held-out" /></LineChart></ResponsiveContainer></div> : null}
    </section>
    <Ways d={d} busy={busy} collect={() => go('/admin/model-lab/comp2/collect')} />
    <section className="mlb-sec"><h4>THE EXAM · SAME HELD-OUT PROOFS FOR EVERYONE<small>{d.examRunning ? 'sitting it now…' : d.exam ? `${d.exam.n} questions · ${new Date(d.exam.at * 1000).toLocaleString()}` : 'not sat yet'}</small></h4>
      {d.exam ? <>{examVerdict(d.exam) ? <p className="cex-verdict" data-testid="mc2-verdict">{examVerdict(d.exam)}</p> : null}<Board exam={d.exam} /><Kinds exam={d.exam} /></> : <p className="mlb-none">Train it, then run the exam: every examinee answers the same proofs.</p>}
      <small className="mlb-note">A flagship with no key is blocked, never guessed. Save one in HQ › Agents and run the exam again; it asks at most 40 questions.</small>
    </section>
  </div>;
}

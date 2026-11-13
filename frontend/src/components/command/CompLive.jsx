import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Area, AreaChart, ResponsiveContainer, YAxis } from 'recharts';
import { useCompLive } from '../../lib/compLive';
import { useCountUp } from '../../lib/useCountUp';
import { isCalm } from '../../lib/fxPause';

// 📡 COMP LIVE (COMP-1 b, owner asked 5×: "realtime animations I can watch"). The strip on top of every COMP tab, fed by ONE stream of real
// numbers (lib/compLive): the LoRA run's loss as it trains, a Forge build's step + tokens/s, the exam filling in, the stash rows per proof
// type, and the internet learner's next settle counting down. Nothing is drawn that was not measured: no run = the last real curve, still.
const tok = (name, dflt) => { try { return getComputedStyle(document.body).getPropertyValue(name).trim() || dflt; } catch { return dflt; } };
const f2 = v => (v == null ? '—' : Number(v).toFixed(3));
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
const big = v => (v == null ? '—' : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : String(Math.round(v)));

function N({ v, fmt = x => String(x) }) { const n = useCountUp(Number(v) || 0); return <>{v == null ? '—' : fmt(n)}</>; }
function Countdown({ at }) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { if (!at) return undefined; const t = setInterval(() => { if (!document.hidden) setNow(Date.now() / 1000); }, 1000); return () => clearInterval(t); }, [at]);
  if (!at) return '—'; const s = Math.max(0, Math.round(at - now)); return s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : 'settling';
}
function Spark({ pts, color, testid }) {
  if (!pts || pts.length < 2) return <span className="cplv-nospark">no run yet</span>;
  const data = pts.map(p => (Array.isArray(p) ? { s: p[0], v: p[1] } : { s: p.step, v: p.loss })).filter(p => p.v != null);
  return <div className="cplv-spark" data-testid={testid}><ResponsiveContainer width="100%" height={42}><AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}><YAxis hide domain={['auto', 'auto']} /><Area type="monotone" dataKey="v" stroke={color} fill={color} fillOpacity={0.18} strokeWidth={1.6} isAnimationActive={false} dot={false} /></AreaChart></ResponsiveContainer></div>;
}

export function CompLive() {
  const { frame, live } = useCompLive(); const [c] = useState(() => ({ up: tok('--m-accent', '#19e68c'), warn: tok('--m-warn', '#f5c451') }));
  const c2 = frame?.comp2 || {}; const fg = frame?.forge; const data = frame?.data || {}; const mk = c2.market;
  const moving = !!frame?.live; const kinds = data.kinds || []; const topRows = Math.max(1, ...kinds.map(k => k.rows || 0));
  return <section className={`cplv${moving ? ' is-moving' : ''}`} data-testid="comp-live" aria-label="COMP live">
    <header className="cplv-head"><span className={`cplv-dot${live ? ' is-on' : ''}`} aria-hidden="true" /><b>COMP LIVE</b><small data-testid="cplv-state">{!live ? 'connecting to the live stream…' : moving ? 'TRAINING / EXAM RUNNING · numbers stream as they move' : 'idle · the last real numbers, held still'}</small>{frame ? <em className="m-num">{new Date(frame.at * 1000).toLocaleTimeString()}</em> : null}</header>
    <div className="cplv-grid">
      <article className={`cplv-tile${c2.training ? ' is-hot' : ''}`} data-tip="COMP v2 · 9B LoRA: the training loss on the answer word (lower = it fits your proofs better), streamed from its log"><small>COMP v2 · LOSS</small>
        <b className="m-num" data-testid="cplv-loss">{f2(c2.loss)}</b><span>iter <N v={c2.iter} /> / {c2.iters || '—'} · held-out {f2(c2.val)}</span>
        <i className="cplv-bar"><u style={{ transform: `scaleX(${c2.iters ? Math.max(0.02, (c2.iter || 0) / c2.iters) : 0})` }} /></i><Spark pts={c2.tail} color={c.up} testid="cplv-spark-c2" /></article>
      <article className={`cplv-tile${c2.examining ? ' is-hot' : ''}`} data-tip="The held-out exam: every examinee answers the same proofs; this fills in as each one finishes"><small>THE EXAM</small>
        <b className="m-num" data-testid="cplv-exam">{c2.examTotal ? `${c2.examAnswered}/${c2.examTotal}` : '—'}</b><span>{c2.examN || 0} questions · best {c2.best ? `${c2.best.name} ${pct(c2.best.acc)}` : '—'}</span>
        <ul className="cplv-vs"><li><em>COMP v2</em><i><u style={{ transform: `scaleX(${c2.compAcc || 0})` }} /></i><b className="m-num">{pct(c2.compAcc)}</b></li><li><em>base 9B</em><i><u style={{ transform: `scaleX(${c2.baseAcc || 0})` }} /></i><b className="m-num">{pct(c2.baseAcc)}</b></li></ul></article>
      <article className={`cplv-tile${fg?.live ? ' is-hot' : ''}`} data-tip="The from-scratch Forge build (Build your model): its step, loss and tokens per second while it trains"><small>FORGE {fg?.version ? `· ${fg.version}` : ''}</small>
        <b className="m-num" data-testid="cplv-forge">{fg ? f2(fg.loss) : '—'}</b><span>{fg ? <>step <N v={fg.step} /> / {fg.steps || '—'} · {fg.tps ? `${big(fg.tps)} tok/s` : `${fg.status || 'idle'}`}</> : 'no build yet'}</span>
        <i className="cplv-bar"><u style={{ transform: `scaleX(${fg?.steps ? Math.max(0.02, (fg.step || 0) / fg.steps) : 0})` }} /></i><Spark pts={fg?.tail} color={c.warn} testid="cplv-spark-forge" /></article>
      <article className="cplv-tile" data-tip="Rows COMP learns from, live from the stash: every settled proof + your grades"><small>DATASET · FROM THE STASH</small>
        <b className="m-num" data-testid="cplv-rows"><N v={data.rows} /></b><span><N v={data.pairs} /> right-vs-wrong pairs · {c2.won ?? '—'} won / {c2.lost ?? '—'} lost</span>
        <ul className="cplv-kinds">{kinds.map((k, i) => <li key={k.kind} style={{ '--i': i }}><em>{k.kind}</em><i><motion.u initial={false} animate={{ scaleX: Math.max(0.02, (k.rows || 0) / topRows) }} transition={isCalm() ? { duration: 0 } : { duration: 0.6 }} /></i><b className="m-num">{k.rows}</b></li>)}</ul></article>
      <article className="cplv-tile" data-tip="The internet learner: live DexScreener snapshots settled an hour later become new training rows"><small>INTERNET LEARNER</small>
        <b className="m-num" data-testid="cplv-market">{mk ? <N v={mk.rows} /> : '—'}</b><span>{mk ? `${mk.open ?? 0} open · ${mk.won ?? 0} won / ${mk.lost ?? 0} lost · ${mk.collects ?? 0} passes` : 'not collecting yet'}</span>
        <span className="cplv-next">next settle <b className="m-num"><Countdown at={mk?.nextSettle} /></b></span></article>
    </div>
  </section>;
}

// 🧰 COMP-1 (a): the tooling shortlist (research, proposed, nothing installed or spent). The owner picks; Claude builds the pick.
export const TOOLS = [
  ['Base', 'Qwen3 / Qwen3.5 open weights (Apache-2.0), MLX 4-bit', 'Today’s 9B base. Next: try the 14B at 4-bit if the Mac has the memory, same LoRA recipe.'],
  ['Fine-tune', 'mlx-lm LoRA → DoRA, more held-out proofs', 'Already running here. DoRA and a larger rank are config changes, not new installs.'],
  ['Preferences', 'DPO / ORPO from the 👍/👎 pairs (mlx-lm-lora, TRL)', 'Teaches “the graded-right answer beats the graded-wrong one”. Needs ~200 pairs per type (have 48).'],
  ['Memory / RAG', 'Local embeddings + sqlite-vec over the stash', 'COMP recalls similar settled proofs before it answers: no retraining, works on day one.'],
  ['Evals', 'The held-out exam here + lm-evaluation-harness for regressions', 'Same questions for every examinee; a version ships only if it beats the last one.'],
  ['Big run', 'Unsloth on a rented GPU (RunPod / Modal, pay per hour)', 'For the full fine-tune once the dataset passes ~1,000 rows a type. Owner approves any spend first.'],
];
export function CompTools() {
  return <section className="cplv-tools" data-testid="comp-tools"><h4>TOOLING SHORTLIST · PROPOSED, NOTHING INSTALLED OR SPENT</h4>
    <ol>{TOOLS.map(([k, what, why], i) => <li key={k} style={{ '--i': i }}><small>{k}</small><b>{what}</b><span>{why}</span></li>)}</ol></section>;
}

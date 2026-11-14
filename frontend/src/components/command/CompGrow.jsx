import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Bar, CartesianGrid, ComposedChart, Line, PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { isCalm } from '../../lib/fxPause';
import '../../styles/compGrow.css';

// 🌱 GROW COMP (owner 2026-11-14: "help me see and understand comp and how to grow it … pay real cheaply for the best ai to train it").
// One page: where COMP stands (how much it has read for its size — the one number that decides whether a bigger COMP gets smarter or just
// memorises), every version it has been so far, the ONE next move, and a teacher: a top AI writes COMP lessons on your own proofs at a live
// price you see before you press Pay (hard cap, OpenRouter, never a wallet). All real: /admin/model-lab/forge + /admin/model-lab/teach.
export const TARGET = 20;   // tokens of text per parameter where small models stop memorising (the scaling rule of thumb)
const SIZES = [10, 25, 50, 100];
const fmt = n => { const v = Number(n) || 0; return v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : `${Math.round(v)}`; };
const usd = (n, d = 4) => `$${(Number(n) || 0).toFixed(d)}`;

/** Pure: forge + teach views → what the Grow page says. */
export function growRead(forge, teach) {
  const builds = (forge?.jobs || []).filter(j => j.card && j.status === 'done').map(j => ({ v: j.version || j.name || j.id.slice(9, 15), params: Number(j.card?.spec?.paramsTotal) || 0,
    read: Number((j.files || []).find(f => f.name === 'corpus.txt')?.bytes) || 0, val: Number(j.card?.val ?? j.val) || null, ppl: Number(j.card?.perplexity) || null, base: Number(j.card?.baselinePerplexity) || null, at: j.card?.built || 0 }))
    .filter(b => b.params).sort((a, b) => (a.at || 0) - (b.at || 0));
  const last = builds[builds.length - 1] || null;
  const chars = last?.read || Number(forge?.corpus?.chars) || 0; const params = last?.params || 0;   // what the newest version really read (its corpus.txt), else today's sources
  const ratio = params ? chars / params : null;
  const lessons = Number(teach?.lessons) || 0; const untaught = Number(teach?.untaught) || 0;
  const newLessons = (teach?.recent || []).filter(x => !last?.at || Number(x.at) > Number(last.at)).length;
  const worse = builds.length > 1 && last.val && builds[builds.length - 2].val && last.val > builds[builds.length - 2].val;
  const next = !last ? { k: 'build', t: 'Build its first version', why: 'Nothing is built yet. Build reads your proofs and trains COMP on this Mac.' }
    : ratio != null && ratio < 1 ? { k: 'teach', t: 'Feed it before you grow it', why: `It has read ${fmt(chars)} characters for ${fmt(params)} parameters (${ratio.toFixed(2)} per parameter; ${TARGET} is where models stop memorising). Lessons on your proofs add the most useful text, cheaply.` }
      : worse ? { k: 'build', t: 'The last version got worse: rebuild smaller or teach first', why: `${last.v} scored ${last.val.toFixed(2)} vs ${builds[builds.length - 2].val.toFixed(2)} before it (lower is better). More data or fewer parameters fixes that.` }
        : newLessons ? { k: 'build', t: 'Build the next version', why: `${newLessons} new lesson${newLessons === 1 ? '' : 's'} since ${last.v}: the next version reads them.` }
          : untaught ? { k: 'teach', t: 'Teach it more', why: `${untaught} of your proofs have no lesson yet.` }
            : { k: 'v2', t: 'Put it through the exam', why: 'It has read everything you have. The exam shows where it ranks against OSSY, G4 and the flagships.' };
  return { builds, last, chars, params, ratio, lessons, untaught, next };
}

function Gauge({ ratio }) {
  const k = ratio == null ? 0 : Math.min(1, Math.log10(1 + ratio) / Math.log10(1 + TARGET));
  return <div className="cg-gauge" data-tip={`Characters it reads per parameter. Around ${TARGET} a model stops memorising and starts generalising`}>
    <ResponsiveContainer width="100%" height="100%"><RadialBarChart innerRadius="78%" outerRadius="100%" data={[{ k: k * 100 }]} startAngle={210} endAngle={-30}>
      <PolarAngleAxis type="number" domain={[0, 100]} tick={false} /><RadialBar dataKey="k" cornerRadius={8} fill="var(--m-accent)" background={{ fill: 'var(--m-surface-2)' }} isAnimationActive={!isCalm()} />
    </RadialBarChart></ResponsiveContainer>
    <span><b className="m-num" data-testid="cg-ratio">{ratio == null ? '—' : ratio < 10 ? ratio.toFixed(2) : Math.round(ratio)}</b><small>READ PER PARAMETER</small><em>goal {TARGET}</em></span></div>;
}

function Versions({ builds }) {
  if (!builds.length) return <p className="cg-none">No version built yet.</p>;
  if (builds.length < 2) { const b = builds[0]; return <p className="cg-none" data-testid="cg-versions">One version so far: <b>{b.v}</b>{b.val != null ? ` · error ${Number(b.val).toFixed(3)}` : ''}. The size-vs-error chart draws from the 2nd build, so you can see if bigger got better.</p>; }   // 2026-11-14: no big empty chart for one dot
  return <div className="cg-chart" data-testid="cg-versions"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={builds} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
    <CartesianGrid stroke="var(--m-line)" vertical={false} />
    <XAxis dataKey="v" tick={{ fill: 'var(--m-dim)', fontSize: 10 }} tickLine={false} axisLine={false} />
    <YAxis yAxisId="p" scale="log" domain={['auto', 'auto']} tickFormatter={fmt} tick={{ fill: 'var(--m-dim)', fontSize: 10 }} tickLine={false} axisLine={false} allowDataOverflow />
    <YAxis yAxisId="l" orientation="right" domain={['auto', 'auto']} tick={{ fill: 'var(--m-dim)', fontSize: 10 }} tickLine={false} axisLine={false} />
    <Tooltip cursor={{ fill: 'var(--m-surface-2)' }} content={({ payload }) => (payload?.[0] ? <div className="cg-tip"><b>{payload[0].payload.v}</b><span>{fmt(payload[0].payload.params)} parameters</span><span>loss {payload[0].payload.val?.toFixed(3) ?? '—'} (lower = better)</span></div> : null)} />
    <Bar yAxisId="p" dataKey="params" fill="var(--m-surface-2)" stroke="var(--m-line-hi)" radius={[6, 6, 0, 0]} isAnimationActive={!isCalm()} />
    <Line yAxisId="l" dataKey="val" stroke="var(--m-accent)" strokeWidth={2} dot={{ r: 4, fill: 'var(--m-accent)' }} isAnimationActive={!isCalm()} />
  </ComposedChart></ResponsiveContainer></div>;
}

/** The teacher: pick a top AI (live price), how many lessons, see the cost, press Pay. Polls while a run is going. */
export function Teacher({ t, onPay, onStop, busy, err }) {
  const list = t?.teachers || [];
  const [pick, setPick] = useState(null); const [n, setN] = useState(25);
  const sel = list.find(x => x.id === pick) || list[0] || null;
  const count = Math.max(0, Math.min(n, t?.untaught || 0)); const est = sel ? count * sel.perLesson : 0;
  const job = t?.job; const live = job?.state === 'running';
  return <section className="cg-card cg-teach" data-testid="cg-teach">
    <h4>🎓 TEACH IT WITH A TOP AI<small>{t?.lessons || 0} lessons so far · {usd(t?.spentUsd, 3)} spent · {t?.untaught ?? 0} proofs untaught</small></h4>
    <p className="cg-say">A top AI reads your proofs one by one and writes COMP a lesson on each: the claim, whether the evidence holds, the rule to keep. COMP reads the lessons in its next version.</p>
    <ul className="cg-teachers" role="radiogroup" aria-label="Teacher">{list.map((x, i) => <li key={x.id}><motion.button type="button" role="radio" aria-checked={sel?.id === x.id} className={sel?.id === x.id ? 'is-on' : ''} onClick={() => setPick(x.id)}
      initial={isCalm() ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }} data-testid={`cg-t-${x.id}`} data-tip={`${x.id} · $${x.inPerM}/M in · $${x.outPerM}/M out (OpenRouter, live)`}>
      <b>{x.family}</b><small>{x.id.split('/')[1]}</small><em className="m-num">{usd(x.perLesson, 4)}<i>/lesson</i></em></motion.button></li>)}</ul>
    {list.length ? null : <p className="cg-none">Reading today's prices…</p>}
    <div className="cg-pay">
      <span className="m-seg" role="radiogroup" aria-label="Lessons">{SIZES.map(s => <button key={s} type="button" role="radio" aria-checked={n === s} className={n === s ? 'active' : ''} onClick={() => setN(s)} data-testid={`cg-n-${s}`}>{s}</button>)}</span>
      <button type="button" className="m-btn m-go cg-paybtn" disabled={!sel || !count || live || busy || t?.keyOk === false} onClick={() => onPay({ model: sel.id, n: count, quoteUsd: Math.round(est * 1e6 + 1) / 1e6 })} data-testid="cg-pay">
        {live ? 'Teaching…' : `Pay ≈ ${usd(est, est < 0.1 ? 4 : 2)} · teach ${count} lesson${count === 1 ? '' : 's'}`}</button>
      <small>{t?.keyOk === false ? 'No OpenRouter key on the server (HQ › Core).' : `From FEELESS's OpenRouter credit, never a wallet. Stops itself at ${usd(Math.min(t?.maxUsd || 5, Math.max(0.01, est * 1.5)), 2)}.`}</small>
    </div>
    {err ? <p className="cg-err" role="alert">⚠ {err}</p> : null}
    {job ? <div className={`cg-job is-${job.state}`} data-testid="cg-job"><header><b>{live ? `${job.family} is teaching` : `Last run · ${job.family}`}</b><span className="m-num">{job.done}/{job.n} · {usd(job.spentUsd)}</span>
      {live ? <button type="button" className="m-btn" onClick={onStop} data-testid="cg-stop">Stop</button> : <small>{job.why}</small>}</header>
      <i className="cg-bar"><u style={{ transform: `scaleX(${job.n ? job.done / job.n : 0})` }} /></i>{job.last ? <p>{job.last}</p> : null}</div> : null}
    {(t?.recent || []).length ? <ol className="cg-lessons">{t.recent.map(x => <li key={`${x.at}${x.proofHead}`}><header><b>{x.proofHead}</b><small>{String(x.model).split('/')[1]} · {usd(x.usd)}</small></header><p>{x.lesson}</p></li>)}</ol> : null}
  </section>;
}

const CLOCKS = [[60, '1 min'], [150, '2.5 min'], [300, '5 min'], [600, '10 min']];
/** 🏁 One button: archive every build (kept), start the next Flagship from the BEST version's weights, read every source, train on a clock. */
export function Rebuild({ forge, onRun, busy, err }) {
  const [sec, setSec] = useState(150);
  const live = (forge?.jobs || []).find(j => j.status === 'training' || j.status === 'tokenizing');
  const best = (forge?.jobs || []).filter(j => j.card?.val != null).sort((a, b) => a.card.val - b.card.val)[0];
  return <section className="cg-card cg-rebuild" data-testid="cg-rebuild">
    <h4>🏁 REBUILD AS ONE FLAGSHIP<small>free · this Mac · nothing rented</small></h4>
    <p className="cg-say">Every build moves to the archive (kept, never deleted). The next version starts from the best one{best ? ` (${best.version || best.name}, loss ${Number(best.card.val).toFixed(3)})` : ''}, reads every source and learns for the time you pick.</p>
    {live ? <div className="cg-job is-running" data-testid="cg-rebuild-live"><header><b>{live.version || live.name} is learning</b><span className="m-num">{live.elapsed ? `${Math.round(live.elapsed)} s` : 'starting'}{live.loss != null ? ` · loss ${Number(live.loss).toFixed(3)}` : ''}</span></header>
      <i className="cg-bar"><u style={{ transform: `scaleX(${live.eta != null && live.elapsed ? Math.min(1, live.elapsed / (live.elapsed + live.eta)) : 0.02})` }} /></i></div>
      : <div className="cg-pay"><span className="m-seg" role="radiogroup" aria-label="How long it learns">{CLOCKS.map(([v, l]) => <button key={v} type="button" role="radio" aria-checked={sec === v} className={sec === v ? 'active' : ''} onClick={() => setSec(v)} data-testid={`cg-clock-${v}`}>{l}</button>)}</span>
        <button type="button" className="m-btn m-go" disabled={busy || !best} onClick={() => onRun(sec)} data-testid="cg-rebuild-go">Rebuild · learn {CLOCKS.find(c => c[0] === sec)[1]}</button></div>}
    {err ? <p className="cg-err" role="alert">⚠ {err}</p> : null}
  </section>;
}

export default function CompGrow({ call, onGo }) {
  const [forge, setForge] = useState(null); const [teach, setTeach] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const loadTeach = useCallback(() => (call ? call('/admin/model-lab/teach').then(setTeach).catch(e => setErr(e.message)) : null), [call]);
  const loadForge = useCallback(() => (call ? call('/admin/model-lab/forge').then(setForge).catch(e => setErr(e.message)) : null), [call]);
  useEffect(() => { loadForge(); loadTeach(); }, [loadForge, loadTeach]);
  const building = (forge?.jobs || []).some(j => j.status === 'training' || j.status === 'tokenizing');
  useEffect(() => { if (!building) return undefined; const t = setInterval(() => { if (!document.hidden) loadForge(); }, 3000); return () => clearInterval(t); }, [building, loadForge]);
  const [rbBusy, setRbBusy] = useState(false); const [rbErr, setRbErr] = useState('');
  const rebuild = async seconds => { setRbBusy(true); setRbErr(''); try { await call('/admin/model-lab/forge/flagship', { method: 'POST', body: JSON.stringify({ seconds }) }); await loadForge(); } catch (e) { setRbErr(e.message); } finally { setRbBusy(false); } };
  const running = teach?.job?.state === 'running';
  useEffect(() => { if (!running) return undefined; const t = setInterval(() => { if (!document.hidden) loadTeach(); }, 2500); return () => clearInterval(t); }, [running, loadTeach]);
  const pay = async body => { setBusy(true); setErr(''); try { await call('/admin/model-lab/teach', { method: 'POST', body: JSON.stringify(body) }); await loadTeach(); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const stop = async () => { try { await call('/admin/model-lab/teach/stop', { method: 'POST', body: '{}' }); loadTeach(); } catch (e) { setErr(e.message); } };
  const r = useMemo(() => growRead(forge, teach), [forge, teach]);
  return <div className="cg" data-testid="comp-grow">
    <section className="cg-hero">
      <Gauge ratio={r.ratio} />
      <div className="cg-now"><small>COMP TODAY{r.last ? ` · ${r.last.v}` : ''}</small>
        <h3>{r.last ? <><b className="m-num">{fmt(r.params)}</b> parameters, <b className="m-num">{fmt(r.chars)}</b> characters read</> : 'Not built yet'}</h3>
        <dl><div><dt>LOSS</dt><dd className="m-num">{r.last?.val?.toFixed(3) ?? '—'}</dd></div><div><dt>VERSIONS</dt><dd className="m-num">{r.builds.length}</dd></div>
          <div><dt>LESSONS</dt><dd className="m-num">{r.lessons}</dd></div><div><dt>GUESSES</dt><dd className="m-num" data-tip="Perplexity: how many next letters it hesitates between (lower is better), vs a model that knows only letter counts">{r.last?.ppl ? `${r.last.ppl.toFixed(1)}${r.last.base ? ` vs ${r.last.base.toFixed(1)}` : ''}` : '—'}</dd></div></dl></div>
      <div className={`cg-next is-${r.next.k}`} data-testid="cg-next"><small>YOUR NEXT MOVE</small><b>{r.next.t}</b><p>{r.next.why}</p>
        {r.next.k === 'teach' ? <a className="m-btn m-go" href="#cg-teach" onClick={e => { e.preventDefault(); document.querySelector('[data-testid=cg-teach]')?.scrollIntoView({ behavior: isCalm() ? 'auto' : 'smooth' }); }}>Teach it ↓</a>
          : <button type="button" className="m-btn m-go" onClick={() => onGo?.(r.next.k)}>{r.next.k === 'v2' ? 'Open the exam' : 'Open Build'}</button>}</div>
    </section>
    {err ? <p className="cg-err" role="alert">⚠ {err}</p> : null}
    <section className="cg-card"><h4>EVERY VERSION · SIZE VS LOSS<small>bars = parameters (log) · line = loss, lower is better</small></h4><Versions builds={r.builds} /></section>
    <Rebuild forge={forge} onRun={rebuild} busy={rbBusy} err={rbErr} />
    <Teacher t={teach} onPay={pay} onStop={stop} busy={busy} err="" />
  </div>;
}

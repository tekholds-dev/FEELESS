import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Area, Bar, BarChart, Cell, ComposedChart, Legend, Line, LineChart, PolarAngleAxis, RadialBar, RadialBarChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/compDash.css';

// 🛰 COMP · FLIGHT DECK (owner 2026-11-15 "redo COMP … dont use the same styles and design, charts, graphs … go brand new and give me ur
// version of a dashboard for comp when i open its folder"). One screen that answers: is COMP good yet, against whom, on which proofs, is it
// still learning, and how much fuel (data) is left. Every number is live from /admin/model-lab/comp2 + /admin/model-lab; the old workshop
// (tabs, live feed, voice) is one click away, nothing removed.

const SHORT = { baseline: 'Always guess', base: 'Base 9B', comp: 'COMP', comp_mem: 'COMP + memory', ossy: 'OSSY', g4: 'G4', claude: 'Claude', gpt: 'GPT', grok: 'Grok' };
const pts = x => Math.round(x * 1000) / 10;   // 0.6786 → 67.9

/** The whole deck from the two live reads (pure: tested). */
export function compDash(c2, lab) {
  const ex = c2?.exam; const list = ex?.examinees || [];
  const acc = id => list.find(e => e.id === id)?.score?.acc;
  const entered = list.filter(e => typeof e?.score?.acc === 'number');
  const ranked = [...entered].sort((a, b) => b.score.acc - a.score.acc).map(e => ({ id: e.id, name: SHORT[e.id] || e.name, kind: e.kind, acc: pts(e.score.acc), right: e.score.right, n: e.score.n, comp: /^comp/.test(e.id) }));
  const bestComp = ranked.find(r => r.comp) || null;
  const guess = acc('baseline'); const judges = ['ossy', 'g4'].map(acc).filter(v => typeof v === 'number');
  const bestJudge = judges.length ? Math.max(...judges) : null;
  const kinds = [...new Set(entered.flatMap(e => Object.keys(e.score.kinds || {})))].sort();
  const heat = ['comp_mem', 'comp', 'base', 'ossy', 'g4', 'baseline'].map(id => list.find(e => e.id === id)).filter(e => e?.score?.kinds)
    .map(e => ({ id: e.id, name: SHORT[e.id] || e.name, cells: kinds.map(k => { const c = e.score.kinds[k]; return c?.n ? { k, right: c.right, n: c.n, p: c.right / c.n } : { k, n: 0 }; }) }));
  const curve = c2?.run?.curve || {}; const val = new Map((curve.val || []).map(([i, v]) => [i, v]));
  const learn = (curve.train || []).map(([i, v]) => ({ i, train: v, val: val.get(i) ?? null }));
  (curve.val || []).forEach(([i, v]) => { if (!learn.some(r => r.i === i)) learn.push({ i, train: null, val: v }); });
  learn.sort((a, b) => a.i - b.i);
  const race = (c2?.race || []).map((r, i) => ({ run: i + 1, at: r.at, ...Object.fromEntries(Object.entries(r.scores || {}).map(([k, v]) => [k, pts(v)])) }));
  const ds = c2?.dataset || {}; const mk = c2?.market || {};
  const missing = list.filter(e => typeof e?.score?.acc !== 'number').map(e => SHORT[e.id] || e.name);
  return {
    ready: !!ex, n: ex?.n || 0, at: ex?.done || ex?.at || null, running: !!(c2?.examRunning || c2?.run?.running),
    hero: bestComp ? { name: bestComp.name, acc: bestComp.acc, overGuess: guess != null ? Math.round((bestComp.acc - pts(guess)) * 10) / 10 : null,
      overJudges: bestJudge != null ? Math.round((bestComp.acc - pts(bestJudge)) * 10) / 10 : null } : null,
    guess: guess != null ? pts(guess) : null, ranked, kinds, heat, learn, race, missing,
    base: c2?.base || null, iters: c2?.run?.iters || 0,
    fuel: { rows: lab?.rows ?? null, goal: lab?.goals?.rows ?? null, pairs: lab?.pairs ?? null, pairsGoal: lab?.goals?.pairs ?? null,
      train: ds.train || 0, valid: ds.valid || 0, test: ds.test || 0, won: ds.won || 0, lost: ds.lost || 0 },
    market: { won: mk.won || 0, lost: mk.lost || 0, flat: mk.flat || 0, open: mk.open || 0, next: mk.nextSettle || null },
  };
}

function Count({ v, d = 1, suf = '' }) { const n = useCountUp(Number(v) || 0); return <>{n.toFixed(d)}{suf}</>; }
function useNow(ms = 1000) { const [t, setT] = useState(() => Date.now()); useEffect(() => { const i = setInterval(() => setT(Date.now()), ms); return () => clearInterval(i); }, [ms]); return t; }
const ago = s => { if (!s) return '—'; const m = Math.round((Date.now() / 1000 - s) / 60); return m < 60 ? `${m} min ago` : m < 2880 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };
const TIP = { contentStyle: { background: 'var(--cpd-ink)', border: '1px solid var(--cpd-rule)', borderRadius: 6, fontFamily: 'var(--m-mono)', fontSize: 11 }, labelStyle: { color: 'var(--cpd-dim)' }, cursor: { fill: 'var(--cpd-rule)' } };

function Hero({ v }) {
  const h = v.hero; const ring = [{ v: h ? h.acc : 0 }];
  return <section className="cpd-hero" style={{ '--i': 0 }} data-testid="cpd-hero">
    <div className="cpd-ring" data-tip="COMP's best score on proofs it never saw: did each one win or lose?">
      <ResponsiveContainer width="100%" height="100%"><RadialBarChart innerRadius="78%" outerRadius="100%" data={ring} startAngle={90} endAngle={-270}>
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} /><RadialBar dataKey="v" cornerRadius={8} background={{ fill: 'var(--cpd-rule)' }} fill="var(--cpd-sig)" isAnimationActive /></RadialBarChart></ResponsiveContainer>
      <span className="cpd-ring-n"><b>{h ? <Count v={h.acc} /> : '—'}</b><small>% RIGHT</small></span>
    </div>
    <div className="cpd-say">
      <small className="cpd-kick">COMP · FLIGHT DECK{v.running ? ' · RUNNING NOW' : ''}</small>
      <h3>{!h ? 'COMP has not sat an exam yet.' : h.overJudges > 0 ? `${h.name} out-calls your judges.` : h.overGuess > 0 ? `${h.name} beats guessing, not your judges yet.` : `${h.name} is not past guessing yet.`}</h3>
      <p>{v.ready ? `Exam of ${v.n} held-out proofs · ${ago(v.at)} · base ${v.base?.name || '—'}` : 'Train it, then run the exam from the workshop.'}</p>
      {h ? <ul className="cpd-facts">
        <li className={h.overGuess > 0 ? 'up' : 'dn'}><b>{h.overGuess > 0 ? '+' : ''}<Count v={h.overGuess} /></b><small>pts vs always guessing</small></li>
        <li className={h.overJudges > 0 ? 'up' : 'dn'}><b>{h.overJudges > 0 ? '+' : ''}{h.overJudges == null ? '—' : <Count v={h.overJudges} />}</b><small>pts vs best judge (OSSY / G4)</small></li>
        <li><b>OSSY + G4</b><small>still judge every proof until COMP is elite</small></li>
      </ul> : null}
    </div>
  </section>;
}

function Standings({ v }) {
  const data = v.ranked;
  return <section className="cpd-panel cpd-stand" style={{ '--i': 1 }} data-testid="cpd-standings">
    <h4>STANDINGS <small>same {v.n} proofs, every mind · dashed line = always guessing</small></h4>
    {!data.length ? <p className="cpd-none">No scores yet.</p> : <div className="cpd-chart" style={{ height: 34 + data.length * 30 }}>
      <ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ top: 4, right: 44, bottom: 4, left: 4 }}>
        <XAxis type="number" domain={[0, 100]} hide /><YAxis type="category" dataKey="name" width={112} tickLine={false} axisLine={false} tick={{ fill: 'var(--cpd-dim)', fontSize: 11, fontFamily: 'var(--m-mono)' }} />
        <Tooltip {...TIP} formatter={(x, _n, p) => [`${x}% · ${p.payload.right}/${p.payload.n}`, 'right']} />
        {v.guess != null ? <ReferenceLine x={v.guess} stroke="var(--cpd-warn)" strokeDasharray="4 4" /> : null}
        <Bar dataKey="acc" radius={[0, 4, 4, 0]} barSize={14} label={{ position: 'right', fill: 'var(--cpd-text)', fontSize: 11, fontFamily: 'var(--m-mono)', formatter: x => `${x}%` }}>
          {data.map(r => <Cell key={r.id} fill={r.comp ? 'var(--cpd-sig)' : r.kind === 'baseline' ? 'var(--cpd-warn)' : 'var(--cpd-mid)'} />)}</Bar>
      </BarChart></ResponsiveContainer></div>}
    {v.missing.length ? <p className="cpd-foot">Not entered: {v.missing.join(' · ')} (add their keys in HQ › Agents to race them).</p> : null}
  </section>;
}

function Heat({ v }) {
  return <section className="cpd-panel cpd-heat" style={{ '--i': 2 }} data-testid="cpd-heat">
    <h4>WHERE IT WINS <small>right / asked, by proof type</small></h4>
    {!v.heat.length ? <p className="cpd-none">No exam yet.</p> : <div className="cpd-grid" style={{ '--cols': v.kinds.length }} role="table" aria-label="Right answers by proof type">
      <span role="columnheader" />{v.kinds.map(k => <span key={k} role="columnheader" className="cpd-gh">{k}</span>)}
      {v.heat.map(r => <React.Fragment key={r.id}><span role="rowheader" className={`cpd-gr${/^comp/.test(r.id) ? ' is-comp' : ''}`}>{r.name}</span>
        {r.cells.map(c => <span key={c.k} role="cell" className="cpd-cell" style={{ '--p': c.n ? c.p : 0 }} data-tip={c.n ? `${r.name} on ${c.k}: ${c.right} right of ${c.n}` : `No ${c.k} proofs in this exam`}>{c.n ? `${c.right}/${c.n}` : '·'}</span>)}</React.Fragment>)}
    </div>}
  </section>;
}

function Learn({ v }) {
  return <section className="cpd-panel" style={{ '--i': 3 }} data-testid="cpd-learn">
    <h4>LEARNING <small>{v.iters ? `${v.iters} steps · loss falls = it is learning; the dotted line is proofs it never trained on` : 'not trained yet'}</small></h4>
    {!v.learn.length ? <p className="cpd-none">No training run yet.</p> : <div className="cpd-chart" style={{ height: 170 }}>
      <ResponsiveContainer width="100%" height="100%"><ComposedChart data={v.learn} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
        <defs><linearGradient id="cpdLoss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--cpd-sig)" stopOpacity={0.45} /><stop offset="1" stopColor="var(--cpd-sig)" stopOpacity={0} /></linearGradient></defs>
        <XAxis dataKey="i" tick={{ fill: 'var(--cpd-dim)', fontSize: 10 }} tickLine={false} axisLine={{ stroke: 'var(--cpd-rule)' }} />
        <YAxis tick={{ fill: 'var(--cpd-dim)', fontSize: 10 }} tickLine={false} axisLine={false} />
        <Tooltip {...TIP} />
        <Area type="monotone" dataKey="train" name="train loss" stroke="var(--cpd-sig)" fill="url(#cpdLoss)" strokeWidth={2} connectNulls />
        <Line type="monotone" dataKey="val" name="held-out loss" stroke="var(--cpd-warn)" strokeDasharray="3 3" dot={{ r: 3 }} connectNulls />
      </ComposedChart></ResponsiveContainer></div>}
  </section>;
}

function Race({ v }) {
  const lines = [['comp_mem', 'var(--cpd-sig)'], ['comp', 'var(--cpd-sig-2)'], ['ossy', 'var(--cpd-mid)'], ['g4', 'var(--cpd-dim)'], ['baseline', 'var(--cpd-warn)']];
  return <section className="cpd-panel" style={{ '--i': 4 }} data-testid="cpd-race">
    <h4>EVERY EXAM SO FAR <small>% right per run</small></h4>
    {v.race.length < 2 ? <p className="cpd-none">{v.race.length ? 'One run so far: the line starts at the second.' : 'No runs yet.'}</p> : <div className="cpd-chart" style={{ height: 190 }}>
      <ResponsiveContainer width="100%" height="100%"><LineChart data={v.race} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
        <XAxis dataKey="run" tick={{ fill: 'var(--cpd-dim)', fontSize: 10 }} tickLine={false} axisLine={{ stroke: 'var(--cpd-rule)' }} tickFormatter={x => `#${x}`} />
        <YAxis domain={[0, 100]} tick={{ fill: 'var(--cpd-dim)', fontSize: 10 }} tickLine={false} axisLine={false} />
        <Tooltip {...TIP} labelFormatter={x => `exam #${x}`} />
        <Legend iconType="plainline" iconSize={12} wrapperStyle={{ fontSize: 10.5, fontFamily: 'var(--m-mono)', color: 'var(--cpd-dim)' }} />
        {lines.filter(([k]) => v.race.some(r => r[k] != null)).map(([k, c]) => <Line key={k} type="monotone" dataKey={k} name={SHORT[k]} stroke={c} strokeWidth={k.startsWith('comp') ? 2.5 : 1.5} dot={{ r: 2.5 }} connectNulls />)}
      </LineChart></ResponsiveContainer></div>}
  </section>;
}

function Fuel({ v }) {
  const now = useNow(); const f = v.fuel; const m = v.market;
  const tank = f.goal ? Math.min(1, (f.rows || 0) / f.goal) : 0; const split = f.train + f.valid + f.test || 1;
  const settle = m.next ? Math.max(0, Math.round(m.next - now / 1000)) : null;
  return <section className="cpd-panel cpd-fuel" style={{ '--i': 5 }} data-testid="cpd-fuel">
    <h4>FUEL <small>what it learns from</small></h4>
    <div className="cpd-tank" data-tip="Settled proofs + your grades it can learn from, against the goal for a big fine-tune">
      <span className="cpd-tank-bar"><i style={{ transform: `scaleX(${tank})` }} /></span>
      <b><Count v={f.rows || 0} d={0} /></b><small>/ {f.goal ? f.goal.toLocaleString() : '—'} rows</small></div>
    <div className="cpd-split" data-tip="How this exam's proofs were split: learned from · checked during training · the held-out exam">
      <i style={{ flexGrow: f.train / split }}><b>{f.train}</b> train</i><i style={{ flexGrow: f.valid / split }}><b>{f.valid}</b> check</i><i style={{ flexGrow: f.test / split }}><b>{f.test}</b> exam</i></div>
    <ul className="cpd-mk">
      <li data-tip="Market proofs the collector settled as winners"><b>{m.won}</b><small>won</small></li>
      <li data-tip="Settled as losers"><b>{m.lost}</b><small>lost</small></li>
      <li data-tip="Moved too little to count either way"><b>{m.flat}</b><small>flat</small></li>
      <li data-tip="Still open: they settle into new rows"><b>{m.open}</b><small>open</small></li>
      <li className="cpd-next" data-tip="The collector's next settle"><b>{settle == null ? '—' : `${Math.floor(settle / 60)}:${String(settle % 60).padStart(2, '0')}`}</b><small>next settle</small></li>
    </ul>
  </section>;
}

export function CompDash({ call, lab, onWorkshop }) {
  const [c2, setC2] = useState(null); const [err, setErr] = useState('');
  const load = useCallback(() => (call ? call('/admin/model-lab/comp2').then(x => { setC2(x); setErr(''); }).catch(e => setErr(e.message)) : Promise.resolve()), [call]);
  useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [load]);
  const v = useMemo(() => compDash(c2, lab), [c2, lab]);
  return <div className="cpd" data-testid="comp-dash">
    <i className="cpd-scan" aria-hidden="true" />
    {err ? <p className="cpd-err" role="alert">⚠ {err}</p> : null}
    {!c2 && !err ? <p className="cpd-none">Reading COMP…</p> : null}
    {c2 ? <>
      <Hero v={v} />
      <div className="cpd-row"><Standings v={v} /><Heat v={v} /></div>
      <div className="cpd-row"><Learn v={v} /><Race v={v} /></div>
      <Fuel v={v} />
    </> : null}
    <button type="button" className="cpd-go" onClick={onWorkshop} data-tip="Train, run the exam, grade proofs, build versions, live feed" data-testid="cpd-workshop">Open the workshop →</button>
  </div>;
}

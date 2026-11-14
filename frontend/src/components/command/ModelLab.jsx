import React, { useCallback, useEffect, useState } from 'react';
import { useCountUp } from '../../lib/useCountUp';
import SegTabs from '../SegTabs';
import { ModelComp2 } from './ModelComp2';
import { DatasetPulse } from './CompExplain';
import { ModelForge } from './ModelForge';
import CompGrow from './CompGrow';
import { CompLive, CompTools } from './CompLive';
import '../../styles/modelLab.css';

// 🧪 MODEL LAB (owner 2026-11-11: "a folder for the new AI we are creating … a full AI and human setup to build / learn how to be a new kind of
// artificial intel"). LIVE: what FEELESS's own model would learn from, read from the stash (every proof and how it really ended), the model-call
// log (the rented minds' real record: the bar to beat) and the owner's own grades on proofs nothing settled (the human half). No model is
// trained here and nothing is spent or sent: Export gives the owner a scrubbed .jsonl file. 🏷 COMPAI (owner 2026-11-12): the header name is THE
// model's name, kept on the server (forge/family), and every build is a version of it (COMP Flagship v1.00, v1.01 …).
const TAB_KEY = 'feeless.modelLab.tab2';   // 2026-11-14: a new key so everyone lands on Grow once
const TABS = [['grow', '🌱 Grow COMP', 'Where COMP stands, its next move, and a top AI to teach it cheaply'], ['build', '🏗 Build your model', 'Design it, see its specs, set its guardrails, press Build: it trains on this Mac'], ['v2', '🚀 COMP v2 · 9B', 'A real 9B open model fine-tuned on your proofs, examined against the base, a baseline and the flagships'], ['data', '📊 Data & grades', 'What it learns from, your grades, the minds to beat, the road to a big fine-tune']];
const STEPS = [
  ['data', 'Collect the data we own', 'Every graded proof (PoW, PoP, PoB, PoC, PoStatic, PoEco), every 👍 / 👎 the owners gave, the kits and the fixes that made a page pass the store check. Ours, labelled by real results, not scraped text.', 'Proof folders, review grades and kit library already store this'],
  ['clean', 'Clean it into training rows', 'One row = the ask, what the agent read, what it did, the grade. Strip wallets, keys and personal data. Drop proofs with no result.', 'A script over the proof store; no model needed yet'],
  ['base', 'Pick an open base model', 'Start from an open-weights model we may fine-tune and sell access to (license checked). Small first (7–14B) so a run costs tens of dollars, not thousands.', 'Licence check before any training'],
  ['sft', 'Teach it our way (fine-tune)', 'Supervised fine-tune on the rows that scored well: how to research, how to build a page that passes the store check, how to file a proof.', 'Rented GPU hours, LoRA first'],
  ['pref', 'Teach it what wins (preferences)', 'Pairs of answers, the one graded right vs the one graded wrong, and the owners’ 👍 / 👎. This is where real results beat a general model.', 'Needs enough graded pairs per proof type'],
  ['eval', 'Our own exams', 'Held-back proofs it never saw: does it grade right more often than the agents’ current minds? Store-check score of pages it builds. A model ships only if it wins these.', 'Compared against today’s OSSY / G4 and the rented minds'],
  ['serve', 'Run it and charge for it', 'Host it behind the same mind picker the agents use. A subscription unlocks it; free agents keep the current minds.', 'Price set from real serving cost'],
];
const GAPS = [
  ['Proof, not promises', 'General chat models are graded on benchmarks, not on whether the trade, pick or page actually worked. Ours learns from graded outcomes.'],
  ['Fresh knowledge', 'Big models are trained months before you use them. Ours is tuned on this week’s proofs and reads live sources through the agent.'],
  ['Shipping, not drafts', 'They write code that often does not run or would fail an app store. Ours learns from pages that passed the store check.'],
  ['Your voice', 'They answer everyone the same. The agent already mirrors how its owner writes; the model can learn that from day one.'],
  ['Cost', 'A small tuned model for our jobs can cost a fraction per answer of a frontier model.'],
];
const HUNT = ['Read public leaderboards and eval write-ups for where top models score low', 'Read public reviews, forums and complaint threads about what users give up on', 'Log every time an agent’s rented mind fails a proof, and why', 'Turn each repeated failure into an exam question for our model'];
const STATE = { have: ['Data exists', 'is-have'], ready: ['Ready to run', 'is-have'], todo: ['Not started', 'is-todo'] };
const pct = v => `${Math.round((v || 0) * 100)}%`;
function Num({ v, d = 0 }) { const n = useCountUp(Number(v) || 0); return <b className="m-num">{n.toFixed(d)}</b>; }

// 📊 THE DATASET, one row per proof type: rows toward the goal, right vs wrong, the pairs preference training needs, and what is still open
function KindRow({ k, goals, i }) {
  return <li style={{ '--i': i }} data-testid={`mlb-kind-${k.kind}`}>
    <b className="ml-k">{k.kind}</b>
    <span className="ml-rows" data-tip={`${k.rows} settled rows. A fine-tune is worth renting a GPU near ${goals.rows}`}><b className="m-num">{k.rows}</b><i className="c2-bar"><u style={{ transform: `scaleX(${Math.max(0.02, k.rowsPct)})` }} /></i></span>
    <span className="ml-split" data-tip={`${k.won} right · ${k.lost} wrong${k.flat ? ` · ${k.flat} flat` : ''}${k.graded ? ` · ${k.graded} graded by you` : ''}`}><b className="m-num is-won">{k.won}</b> right · <b className="m-num is-lost">{k.lost}</b> wrong{k.graded ? ` · ${k.graded} yours` : ''}</span>
    <small className="ml-pairs" data-tip={`${pct(k.pairsPct)} of the ${goals.pairs} pairs preference training wants`}><b className="m-num">{k.pairs}</b> right-vs-wrong pairs</small>
    {k.open ? <span className="m-chip warn" data-tip="Open proofs nothing has settled: grade them below">{k.open} open</span> : <span className="m-chip">0 open</span>}
  </li>;
}

function Review({ q, i, busy, onGrade }) {
  const [note, setNote] = useState('');
  return <li className="ml-q" style={{ '--i': i }} data-testid={`mlb-q-${q.key}`}>
    <span className="ml-q-say"><span className="m-chip">{q.kind}</span><b title={q.title}>{q.title}</b><small>{q.source || 'its own read'}</small></span>
    <input className="m-input" value={note} maxLength={300} onChange={e => setNote(e.target.value)} placeholder="Why (optional)" aria-label={`Why, for ${q.title}`} />
    <span className="ml-q-do">
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => onGrade(q.key, 'good', note)} data-tip="It did the job: a row the model learns to copy" data-testid={`mlb-good-${q.key}`}>Good</button>
      <button type="button" className="m-btn danger" disabled={busy} onClick={() => onGrade(q.key, 'bad', note)} data-tip="It got it wrong: a row the model learns to avoid" data-testid={`mlb-bad-${q.key}`}>Bad</button>
      <button type="button" className="m-btn" disabled={busy} onClick={() => onGrade(q.key, 'skip', note)} data-tip="Not a fair test: leave it out" data-testid={`mlb-skip-${q.key}`}>Skip</button></span>
  </li>;
}

// 🧊 memo (owner 2026-11-14 "COMP freezes"): Fee's desk reloads every 6 s and re-rendered all of COMP (charts, heatmaps) each time; now only
// a new `call` re-renders it.
export const ModelLab = React.memo(function ModelLab({ call }) {
  const [name, setName] = useState(''); const [saidName, setSaidName] = useState('');
  useEffect(() => { if (call) call('/admin/model-lab/forge/family').then(x => { const n = String(x?.name || ''); setName(n); setSaidName(n); }).catch(() => {}); }, [call]);
  useEffect(() => {   // the name saves itself after typing settles (one write), and the forge's versions follow it
    const v = name.trim(); if (!call || !v || v === saidName) return undefined;
    const t = setTimeout(() => call('/admin/model-lab/forge/family', { method: 'POST', body: JSON.stringify({ name: v }) }).then(x => setSaidName(String(x?.name || v))).catch(() => {}), 600);
    return () => clearTimeout(t);
  }, [name, saidName, call]);
  const keep = v => setName(v);
  const [tab, setTab] = useState(() => { try { return localStorage.getItem(TAB_KEY) || 'grow'; } catch { return 'build'; } });
  const pickTab = k => { setTab(k); try { localStorage.setItem(TAB_KEY, k); } catch { /* private window */ } };
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [saved, setSaved] = useState('');
  const load = useCallback(() => (call ? call('/admin/model-lab').then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message)) : Promise.resolve()), [call]);
  useEffect(() => { load(); }, [load]);
  const onGrade = async (key, verdict, note) => { setBusy(true); try { setD(await call('/admin/model-lab/grade', { method: 'POST', body: JSON.stringify({ key, verdict, note }) })); setErr(''); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const exportRows = async () => {
    setBusy(true); setSaved('');
    try {
      const j = await call('/admin/model-lab/export');
      const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(j.rows.map(r => `${JSON.stringify(r)}\n`), { type: 'application/x-ndjson' }));
      a.download = `feeless-model-rows-${new Date().toISOString().slice(0, 10)}.jsonl`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); setSaved(`${j.count} rows saved`);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const steps = d?.steps || {}; const real = STEPS.filter(s => (steps[s[0]] || 'todo') !== 'todo').length;
  const topFail = Math.max(0.01, ...(d?.minds || []).map(m => m.failRate));
  return <div className="mlb" data-testid="model-lab">
    <header className="ml-head m-card">
      <span className="ml-id"><small className="m-label">COMPAI · OWNER ONLY{saidName && name.trim() !== saidName ? ' · saving…' : ''}</small><input className="mlb-name" value={name} maxLength={32} onChange={e => keep(e.target.value)} placeholder="Name your model" aria-label="Model name (every version is built under it)" data-tip="The model's one name: every build becomes its next version" data-testid="mlb-name" /></span>
      <span className="ml-stats">
        {d ? <span data-tip="Settled proofs + your grades: rows it would learn from"><Num v={d.rows} /><small>rows</small></span> : null}
        {d ? <span data-tip="Right-vs-wrong pairs: what preference training needs"><Num v={d.pairs} /><small>pairs</small></span> : null}
        <span data-tip="Steps on the road to a big fine-tune with real progress"><b className="m-num">{real}/{STEPS.length}</b><small>steps</small><i className="c2-prog"><u style={{ transform: `scaleX(${Math.max(0.02, real / STEPS.length)})` }} /></i></span></span></header>
    <CompLive />
    <SegTabs items={TABS} value={tab} onChange={pickTab} label="Model Lab" testid={k => `mlb-tab-${k}`} className="mlb-tabs" />
    {tab === 'grow' ? <CompGrow call={call} onGo={pickTab} /> : tab === 'build' ? <ModelForge call={call} family={saidName} /> : tab === 'v2' ? <ModelComp2 call={call} /> : <div className="mc2">
    <p className="c2-what">Below is everything your models learn from, live, your grades, the minds they have to beat, and the road to a big fine-tune on a rented GPU.</p>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    {d ? <>
      <section className="c2-card m-card" data-testid="ml-dataset"><h4 className="c2-h">THE DATASET <small>live from the stash · {d.snapshots} snapshots kept as evidence, not rows</small></h4>
        <DatasetPulse d={d} />
        <ul className="ml-kinds"><li className="ml-kinds-head" aria-hidden="true"><span>TYPE</span><span>ROWS · GOAL {d.goals.rows.toLocaleString()}</span><span>RIGHT / WRONG</span><span>PAIRS</span><span /></li>
          {d.kinds.map((k, i) => <KindRow key={k.kind} k={k} goals={d.goals} i={i} />)}
          <li className="is-duels" style={{ '--i': d.kinds.length }} data-testid="mlb-kind-Duels" data-tip="Duels: both minds answered one ask in an agent's chat and you tapped the better one. Each is a right-vs-wrong pair, picked by a person">
            <b className="ml-k">Duels</b><span className="ml-rows"><b className="m-num">{d.duels || 0}</b><i className="c2-bar"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, (d.duels || 0) / d.goals.pairs))})` }} /></i></span>
            <small className="ml-how">With Both on in an agent's chat, tap the crown on the better answer</small><small className="ml-pairs"><b className="m-num">{d.duels || 0}</b> pairs you judged</small><span className="m-chip">your picks</span></li></ul>
        <div className="c2-go"><button type="button" className="m-btn m-go" disabled={busy || !d.rows} onClick={exportRows} data-tip="Every settled or graded proof as one row, scrubbed of wallets, addresses, emails, phones and keys. Saved to this computer only" data-testid="mlb-export">Export {d.rows} clean rows (.jsonl)</button>{saved ? <small className="m-num">{saved}</small> : null}</div></section>
      <section className="c2-card m-card" data-testid="ml-grade"><h4 className="c2-h">YOU GRADE <small>{d.graded} graded · {d.open} open proofs nothing settled · each grade becomes a row</small></h4>
        {d.queue.length ? <ul className="ml-qs">{d.queue.map((q, i) => <Review key={q.key} q={q} i={i} busy={busy} onGrade={onGrade} />)}</ul> : <p className="mlb-none">Nothing open to grade: every kept proof has a result.</p>}</section>
      <section className="c2-card m-card" data-testid="ml-minds"><h4 className="c2-h">THE MINDS TO BEAT <small>their real record · ${d.spentUsd.toFixed(3)} spent on rented minds so far</small></h4>
        {d.minds.length ? <ul className="ml-minds"><li className="ml-minds-head" aria-hidden="true"><span>MODEL</span><span>CALLS</span><span>FAILED</span><span>AVG</span><span>SPENT</span></li>
          {d.minds.map((m, i) => <li key={m.model} style={{ '--i': i }} data-testid={`mlb-mind-${m.model}`}><span className="ml-who"><b>{m.model}</b><small>{m.local ? 'on this Mac' : 'rented'} · {Object.entries(m.kinds).map(([k, n]) => `${k} ${n}`).join(' · ')}</small></span>
            <b className="m-num">{m.calls}</b><span className="ml-fail" data-tip={`${m.failed} of ${m.calls} calls failed`}><i className="c2-bar is-bad"><u style={{ transform: `scaleX(${Math.max(0.02, m.failRate / topFail)})` }} /></i><small className="m-num">{pct(m.failRate)} failed</small></span>
            <b className="m-num">{(m.avgMs / 1000).toFixed(1)}s</b><b className="m-num">${m.usd.toFixed(3)}</b></li>)}</ul> : <p className="mlb-none">No model calls logged yet.</p>}</section>
    </> : !err ? <p className="mlb-none">Reading the stash…</p> : null}
    <section className="c2-card m-card" data-testid="ml-road"><h4 className="c2-h">THE ROAD TO A BIG FINE-TUNE <small>{real} of {STEPS.length} with real progress · hover a step for what it takes</small></h4>
      <ol className="mlb-steps">{STEPS.map(([k, t, say, need], i) => { const st = steps[k] || 'todo'; return <li key={k} className={STATE[st][1]} style={{ '--i': i }} data-testid={`mlb-step-${k}`} data-tip={`${say} · ${need}`}><i className="m-num">{i + 1}</i><b>{t}</b><small>{need}</small><em className={`m-chip${st === 'todo' ? '' : ' ok'}`}>{STATE[st][0]}</em></li>; })}</ol></section>
    <CompTools />
    <details className="c2-card m-card ml-why"><summary className="c2-h">WHY OUR OWN MODEL · THE GAP HUNT <small>where the big models fall short, and how we find more</small></summary>
      <div className="c2-two"><ul className="ml-gaps">{GAPS.map(([t, say]) => <li key={t}><b>{t}</b><small>{say}</small></li>)}</ul>
        <div><ol className="ml-hunt">{HUNT.map(t => <li key={t}>{t}</li>)}</ol><small className="ml-note">Public sources only. Nothing here copies another company’s model or data.</small></div></div></details>
    </div>}
  </div>;
});

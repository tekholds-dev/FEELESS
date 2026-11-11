import React, { useState } from 'react';
import '../../styles/modelLab.css';

// 🧪 MODEL LAB (owner 2026-11-11: "a folder for the new AI we are creating: all the steps and background on building the best AI … learn from them
// and be better, see where they lack"). The plan for FEELESS's own model, built from the stash. Every step says its real state: nothing here
// claims a model exists. Name is the owner's to pick (kept in this browser until it is final).
const NAME_KEY = 'feeless.modelLab.name';
const STEPS = [
  ['data', 'Collect the data we own', 'Every graded proof (PoW, PoP, PoB, PoC, PoStatic, PoEco), every 👍 / 👎 the owners gave, the kits and the fixes that made a page pass the store check. Ours, labelled by real results, not scraped text.', 'have', 'Proof folders, review grades and kit library already store this'],
  ['clean', 'Clean it into training rows', 'One row = the ask, what the agent read, what it did, the grade. Strip wallets, keys and personal data. Drop proofs with no result.', 'todo', 'A script over the proof store; no model needed yet'],
  ['base', 'Pick an open base model', 'Start from an open-weights model we may fine-tune and sell access to (license checked). Small first (7–14B) so a run costs tens of dollars, not thousands.', 'todo', 'Licence check before any training'],
  ['sft', 'Teach it our way (fine-tune)', 'Supervised fine-tune on the rows that scored well: how to research, how to build a page that passes the store check, how to file a proof.', 'todo', 'Rented GPU hours, LoRA first'],
  ['pref', 'Teach it what wins (preferences)', 'Pairs of answers, the one graded right vs the one graded wrong, and the owners’ 👍 / 👎. This is where real results beat a general model.', 'todo', 'Needs enough graded pairs per proof type'],
  ['eval', 'Our own exams', 'Held-back proofs it never saw: does it grade right more often than the agents’ current minds? Store-check score of pages it builds. A model ships only if it wins these.', 'todo', 'Compared against today’s OSSY / G4 and the rented minds'],
  ['serve', 'Run it and charge for it', 'Host it behind the same mind picker the agents use. A subscription unlocks it; free agents keep the current minds.', 'todo', 'Price set from real serving cost'],
];
const GAPS = [
  ['Proof, not promises', 'General chat models are graded on benchmarks, not on whether the trade, pick or page actually worked. Ours learns from graded outcomes.'],
  ['Fresh knowledge', 'Big models are trained months before you use them. Ours is tuned on this week’s proofs and reads live sources through the agent.'],
  ['Shipping, not drafts', 'They write code that often does not run or would fail an app store. Ours learns from pages that passed the store check.'],
  ['Your voice', 'They answer everyone the same. The agent already mirrors how its owner writes; the model can learn that from day one.'],
  ['Cost', 'A small tuned model for our jobs can cost a fraction per answer of a frontier model.'],
];
const HUNT = ['Read public leaderboards and eval write-ups for where top models score low', 'Read public reviews, forums and complaint threads about what users give up on', 'Log every time an agent’s rented mind fails a proof, and why', 'Turn each repeated failure into an exam question for our model'];
const STATE = { have: ['Data exists', 'is-have'], todo: ['Not started', 'is-todo'] };

export function ModelLab() {
  const [name, setName] = useState(() => { try { return localStorage.getItem(NAME_KEY) || ''; } catch { return ''; } });
  const keep = v => { setName(v); try { localStorage.setItem(NAME_KEY, v); } catch { /* private window */ } };
  const have = STEPS.filter(s => s[3] === 'have').length;
  return <div className="mlb" data-testid="model-lab">
    <header className="mlb-head"><span><small>FEELESS · MODEL LAB · OWNER ONLY</small><input className="mlb-name" value={name} maxLength={32} onChange={e => keep(e.target.value)} placeholder="Name your model" aria-label="Model name" data-testid="mlb-name" /></span>
      <span className="mlb-ring" style={{ '--k': have / STEPS.length }} data-tip="Steps with real progress"><b className="m-num">{have}/{STEPS.length}</b><small>STEPS</small></span></header>
    <p className="mlb-truth">No model is trained yet. This is the plan, built on data the stash already holds.</p>
    <ol className="mlb-steps">{STEPS.map(([k, t, say, st, need], i) => <li key={k} className={STATE[st][1]} style={{ '--i': i }} data-testid={`mlb-step-${k}`}><i className="m-num">{i + 1}</i><span><b>{t}</b><small>{say}</small><em>{need}</em></span><u>{STATE[st][0]}</u></li>)}</ol>
    <section className="mlb-two"><div className="mlb-card"><h4>WHERE THE BIG MODELS FALL SHORT</h4><ul>{GAPS.map(([t, say], i) => <li key={t} style={{ '--i': i }}><b>{t}</b><small>{say}</small></li>)}</ul></div>
      <div className="mlb-card"><h4>THE GAP HUNT · NEXT</h4><ul className="mlb-hunt">{HUNT.map((t, i) => <li key={t} style={{ '--i': i }}>{t}</li>)}</ul><small className="mlb-note">Public sources only. Nothing here copies another company’s model or data.</small></div></section>
  </div>;
}

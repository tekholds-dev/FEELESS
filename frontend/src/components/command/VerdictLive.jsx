import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { apiUrl } from '../../lib/api';
import { isCalm } from '../../lib/fxPause';
import '../../styles/verdictLive.css';

// ⚖ AGX-9 · THE COLLECTIVE'S VERDICT, LIVE (owner 2026-11-14): while The Collective judges one of this agent's proofs, each judge's score lands
// on ONE meter the moment it answers (a pin slides to its score), with its reason underneath; the waiting ones show as reading. When the last one
// lands the verdict is stamped (pass at 60+, the average of the judges who answered). It stays on the desk 10 minutes, then goes.
// Users see "The Collective" (judge 1, 2, 3); the owner's staff agents see OSSY / G4 / ZED — the server decides (same rule as every review).
export const PASS_AT = 60;
const NAME = { ossy: 'OSSY', g4: 'G4', zed: 'ZED' };
const CODE = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
export const WIN = { pow: 'pow', pop: 'pop', pob: 'bids', poc: 'poc', pos: 'postatic', poe: 'poe' };
const POLL_MS = 4000;

const label = (k, i) => NAME[k] || (/^collective(-\d+)?$/.test(k) ? `Judge ${k === 'collective' ? 1 : Number(k.split('-')[1])}` : `Judge ${i + 1}`);

/** Pure: the live record → what the meter says. { name, judges:[{k,label,state,score,verdict,why}], landed, avg, leaning, final, say } */
export function meterRead(j) {
  if (!j || !j.judges) return null;
  const judges = Object.entries(j.judges).map(([k, v], i) => ({ k, label: label(k, i), ...v })).filter(x => x.state !== 'out');
  const landed = judges.filter(x => x.state === 'done' && Number.isFinite(Number(x.score)));
  const avg = landed.length ? Math.round(landed.reduce((s, x) => s + Number(x.score), 0) / landed.length) : null;
  const leaning = avg == null ? null : avg >= PASS_AT ? 'pass' : 'fail';
  const final = !!j.done;
  const name = `${CODE[j.kind] || 'Proof'} #${j.n ?? '?'}`;
  const verdict = final ? (j.verdict || (landed.length ? (landed.every(x => x.verdict === 'pass') ? 'pass' : 'fail') : null)) : null;
  const score = final ? (j.score ?? avg) : avg;
  const say = final
    ? (verdict ? `The Collective: ${verdict.toUpperCase()} at ${score}${j.agree === false ? ' · the judges split' : ''}` : 'No judge answered: no verdict (never a pass)')
    : landed.length ? `${landed.length} of ${judges.length} in · leaning ${leaning.toUpperCase()} at ${avg}` : `The Collective is reading it · ${judges.length} judge${judges.length === 1 ? '' : 's'}`;
  return { name, title: j.title || '', judges, landed: landed.length, avg: score, leaning: final ? verdict : leaning, final, say };
}

/** Polls this agent's judging every 4 s while the page is visible. → the live record or null. */
export function useJudging(catId) {
  const [j, setJ] = useState(null);
  useEffect(() => {
    if (!catId) return undefined; let on = true;
    const go = () => { if (document.hidden) return; fetch(apiUrl(`/api/cats/${catId}/judging`)).then(r => (r?.ok ? r.json() : null)).then(x => { if (on && x) setJ(x.judging || null); }).catch(() => {}); };
    go(); const t = setInterval(go, POLL_MS);
    return () => { on = false; clearInterval(t); };
  }, [catId]);
  return j;
}

/** The one meter: 0–100, the pass line at 60, a pin per judge that has answered, the average under it. */
export function VerdictMeter({ r }) {
  const calm = isCalm();
  const spring = calm ? { duration: 0 } : { type: 'spring', stiffness: 140, damping: 18 };
  return <div className="vlv-meter" role="img" aria-label={r.say} style={{ paddingTop: 22 + Math.max(0, r.landed - 1) * 18 }} data-testid="vlv-meter">
    <div className="vlv-track"><i className="vlv-fail" style={{ width: `${PASS_AT}%` }} /><i className="vlv-pass" style={{ width: `${100 - PASS_AT}%` }} /><b className="vlv-line" style={{ left: `${PASS_AT}%` }} aria-hidden="true"><small>PASS {PASS_AT}</small></b>
      {r.avg != null ? <motion.span className={`vlv-avg is-${r.leaning}`} initial={{ left: '0%', opacity: 0 }} animate={{ left: `${r.avg}%`, opacity: 1 }} transition={spring} data-testid="vlv-avg"><em className="m-num">{r.avg}</em></motion.span> : null}
      {r.judges.filter(x => x.state === 'done').map((x, i) => <motion.span key={x.k} className={`vlv-pin is-${x.verdict}`} style={{ '--i': i }} initial={{ left: '0%', opacity: 0, y: -10 }} animate={{ left: `${Number(x.score)}%`, opacity: 1, y: 0 }} transition={spring} data-testid={`vlv-pin-${x.k}`}><i>{x.label.replace('Judge ', 'J')}</i></motion.span>)}</div>
    <div className="vlv-scale" aria-hidden="true"><span>0</span><span>50</span><span>100</span></div>
  </div>;
}

export function JudgeRow({ x }) {
  const why = x.state === 'done' ? (x.why || (x.checks || []).find(c => c.startsWith('✗')) || 'No reason given') : x.state === 'think' ? 'Reading the proof…' : x.state === 'down' ? 'Gave no verdict (down or unreadable): it does not count' : 'Waiting its turn';
  return <li className={`vlv-judge is-${x.state}${x.verdict ? ` is-${x.verdict}` : ''}`} data-testid={`vlv-j-${x.k}`}><b>{x.label}</b>
    <span className="m-num">{x.state === 'done' ? x.score : x.state === 'think' ? <i className="vlv-dots" aria-label="reading"><u /><u /><u /></i> : '—'}</span>
    <em>{x.state === 'done' ? (x.verdict === 'pass' ? '✓ pass' : '✗ fail') : x.state === 'think' ? 'reading' : x.state === 'down' ? 'no answer' : 'next'}</em><p title={(x.checks || []).join('\n')}>{why}</p></li>;
}

/** The card on the agent's desk. Hidden when nothing is being judged. Tap the name to open the proof; ✕ folds it to a pill. */
export default function VerdictLive({ catId, onOpen, j: given }) {
  const polled = useJudging(given === undefined ? catId : null); const j = given === undefined ? polled : given;
  const [fold, setFold] = useState(false);
  const r = meterRead(j);
  if (!r) return null;
  if (fold) return <button type="button" className={`vlv-pill is-${r.leaning || 'wait'}`} onClick={() => setFold(false)} data-testid="vlv-pill" data-tip={r.say}>⚖ {r.name} · {r.final ? (r.leaning || '—').toUpperCase() : `${r.landed}/${r.judges.length}`}</button>;
  return <section className={`vlv${r.final ? ' is-final' : ' is-live'} is-${r.leaning || 'wait'}`} aria-live="polite" data-testid="vlv">
    <header><span className="vlv-dot" aria-hidden="true" /><small>{r.final ? 'THE COLLECTIVE · VERDICT' : 'THE COLLECTIVE · JUDGING NOW'}</small>
      <button type="button" className="vlv-name" onClick={() => onOpen?.({ win: WIN[j.kind], id: j.fid })} data-tip="Open this proof">{r.name}{r.title ? <span> · {r.title}</span> : null}</button>
      <button type="button" className="vlv-x" onClick={() => setFold(true)} aria-label="Fold the verdict card">✕</button></header>
    <p className="vlv-say" data-testid="vlv-say">{r.final && r.leaning ? <strong className={`is-${r.leaning}`}>{r.leaning === 'pass' ? '✓' : '✗'}</strong> : null}{r.say}</p>
    <VerdictMeter r={r} />
    <ul className="vlv-judges">{r.judges.map(x => <JudgeRow key={x.k} x={x} />)}</ul>
  </section>;
}

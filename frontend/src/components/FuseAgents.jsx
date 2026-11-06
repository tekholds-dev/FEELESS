import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { LANES, laneOfStatus } from '../lib/intakeBand';
import { ProChart } from './command/ProChart';
import '../styles/fuseAgents.css';

// 🤖 THE AGENTS, ON THE USER'S SIDE (owner A02): pick up to three, and see how each really did and what its own ledger is doing to its size. It reads public numbers and moves nothing. Sizing here is the agent's own discipline (feecat_brain): it can only ever make an agent trade less.
export const MAX_PICKS = 3;
const SHOWN = 5;
const INK = ['#45e486', '#57c7ff', '#ffc24d'];

/** Closed trades → the running total of what they made, oldest first. */
export function pnlLine(exits) {
  let sum = 0;
  return (exits || []).filter(e => Number(e.exitAt) > 0).sort((a, b) => a.exitAt - b.exitAt).map(e => { sum += Number(e.pnlSol) || 0; return { at: Math.round(e.exitAt), v: +sum.toFixed(6) }; });
}
/** Closed trades → the share won over the last `n`, once it has `n` to read. */
export function winLine(exits, n = 5) {
  const rows = (exits || []).filter(e => Number(e.exitAt) > 0).sort((a, b) => a.exitAt - b.exitAt);
  return rows.map((e, i) => (i + 1 < n ? null : { at: Math.round(e.exitAt), v: Math.round(rows.slice(i + 1 - n, i + 1).filter(x => Number(x.pnlSol) > 0).length / n * 100) })).filter(Boolean);
}
/** The intake's coins → how many sit at each stage. */
export function intakeLevels(coins) {
  const out = Object.fromEntries(LANES.map(([k]) => [k, 0]));
  (coins || []).forEach(c => { out[laneOfStatus(c.status)] += 1; });
  return out;
}
// Agents with a real record first, then the rest.
export const agentRows = rows => (rows || []).filter(r => r.id && !r.revoked).sort((a, b) => (Number(b.trades) || 0) - (Number(a.trades) || 0)).slice(0, SHOWN);
const getJson = url => fetch(apiUrl(url)).then(r => (r.ok ? r.json() : Promise.reject(new Error('no answer'))));

function AgentVitals({ a, p, ink }) {
  const d = p?.discipline || {}; const size = Number(d.sizeMult); const lives = Number(d.lives);
  return <article className="fag-card" style={{ '--ink': ink }} data-testid={`fag-card-${a.id}`}><header><i aria-hidden="true" /><b>{a.name}</b><small className="m-num">{a.trades || 0} trades</small></header>
    {!p ? <small className="fag-wait">Reading its ledger…</small> : <><div className="fag-nums"><span data-tip="Its last ten closed trades"><small>WON</small><b className="m-num">{d.winRate == null ? '—' : `${d.winRate}%`}</b></span><span data-tip="What its last ten closed trades made, in SOL"><small>NET</small><b className={`m-num ${Number(d.netSol) < 0 ? 'is-dn' : 'is-up'}`}>{Number(d.netSol || 0).toFixed(4)}</b></span><span data-tip="What its own ledger is doing to its next trade's size. It can only trade less after losses"><small>SIZE NOW</small><b className="m-num" data-testid={`fag-size-${a.id}`}>{Number.isFinite(size) ? `${size}x` : '—'}</b></span></div>
      <span className="fag-lives" role="img" aria-label={`${lives} of ${d.maxLives || 9} lives`} data-tip="A loss in the last day costs a life and a win gives one back. At zero it stops buying">{Array.from({ length: d.maxLives || 9 }, (_, i) => <i key={i} className={i < lives ? 'is-on' : ''} />)}</span>
      <small className="fag-why" data-testid={`fag-why-${a.id}`}>{d.why || (d.pause ? 'Resting' : 'Nothing is limiting it')}</small></>}</article>;
}

export function FuseAgents() {
  const [rows, setRows] = useState(null); const [picks, setPicks] = useState(null); const [prof, setProf] = useState({}); const [intake, setIntake] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { let on = true; getJson('/api/cats/leaderboard').then(j => { if (!on) return; const list = agentRows(j.rows); setRows(list); setPicks(list.filter(r => r.trades).slice(0, MAX_PICKS).map(r => r.id)); }).catch(() => on && setErr('The agents could not be read right now.')); return () => { on = false; }; }, []);
  useEffect(() => { let on = true; const go = () => { if (!document.hidden) getJson('/api/reputation/familia/intake').then(j => on && setIntake(intakeLevels(j.coins))).catch(() => {}); }; go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, []);
  useEffect(() => { let on = true; (picks || []).filter(id => !prof[id]).forEach(id => getJson(`/api/cats/${id}/profile`).then(j => on && setProf(x => ({ ...x, [id]: j }))).catch(() => on && setProf(x => ({ ...x, [id]: { exits: [] } })))); return () => { on = false; }; }, [picks]);   // eslint-disable-line react-hooks/exhaustive-deps
  const flip = id => setPicks(x => (x.includes(id) ? x.filter(y => y !== id) : [...x, id].slice(-MAX_PICKS)));
  const chosen = useMemo(() => (picks || []).map((id, i) => ({ a: (rows || []).find(r => r.id === id), p: prof[id], ink: INK[i % INK.length] })).filter(x => x.a), [picks, rows, prof]);
  const pnl = chosen.map(x => ({ name: x.a.name, color: x.ink, rows: pnlLine(x.p?.exits) })).filter(l => l.rows.length > 1);
  const won = chosen.map(x => ({ name: x.a.name, color: x.ink, rows: winLine(x.p?.exits) })).filter(l => l.rows.length > 1);
  const top = intake ? Math.max(1, ...Object.values(intake)) : 1;
  if (err) return <p className="fag-none" role="alert">{err}</p>;
  if (!rows) return <p className="fag-none">Reading the agents…</p>;
  return <section className="fag" data-testid="fuse-agents"><div className="fag-top"><div className="fag-picks" role="group" aria-label={`Pick up to ${MAX_PICKS} agents`}><small>PICK UP TO {MAX_PICKS}</small><span className="m-seg">{rows.map(r => <button key={r.id} type="button" className={picks.includes(r.id) ? 'active' : ''} aria-pressed={picks.includes(r.id)} onClick={() => flip(r.id)} data-tip={`${r.trades || 0} trades`} data-testid={`fag-pick-${r.id}`}>{r.name}</button>)}</span></div>
      <div className="fag-tank" data-testid="fag-intake"><small>INTAKE, RIGHT NOW</small><ol>{LANES.map(([k, l, tip]) => <li key={k} data-tip={tip} data-testid={`fag-lane-${k}`}><b className="m-num">{intake ? intake[k] : '—'}</b><i aria-hidden="true"><u style={{ transform: `scaleY(${intake ? Math.max(0.03, intake[k] / top) : 0.03})` }} /></i><small>{l}</small></li>)}</ol></div></div>
    <div className="fag-cards">{chosen.map(x => <AgentVitals key={x.a.id} a={x.a} p={x.p} ink={x.ink} />)}</div>
    <div className="fag-charts"><figure><figcaption>WHAT THEY MADE<small>Running total of closed trades, in SOL</small></figcaption>{pnl.length ? <ProChart lines={pnl} base={0} height={220} fmt={v => `${v.toFixed(4)} SOL`} testid="fag-pnl" label="Running total of closed trades" /> : <p className="fag-none">No closed trades to draw yet.</p>}</figure>
      <figure><figcaption>HOW OFTEN THEY WON<small>Of the last 5 closed trades</small></figcaption>{won.length ? <ProChart lines={won} base={50} height={220} fmt={v => `${v}%`} testid="fag-won" label="Share of the last five closed trades won" /> : <p className="fag-none">Not enough closed trades to draw yet.</p>}</figure></div>
    <p className="fag-note">Past trades promise nothing. Agents can and do lose money. This page reads numbers and moves nothing.</p></section>;
}

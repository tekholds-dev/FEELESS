import React, { Suspense, lazy, useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { KeepDeal } from './KeepDeal';
import '../../styles/boosts.css';
import '../../styles/moneyCharts.css';

// 🪙 WHERE A PROOF'S MONEY GOES (owner 2026-11-05: less confusing, more addicting). Pick a plan and see exactly how much comes back and by when, Every number is the live rule from the server.
export const money = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : n >= 100 ? `$${n.toFixed(0)}` : `$${n.toFixed(2)}`; };
export const PLAN_NAMES = { week: ['1 week', 'Fast'], month: ['30 days', 'Balanced'], quarter: ['90 days', 'Most back'], vault: ['Vault', 'Never comes back'], keep: ['Kept', 'Stays with the Collective'] };
export const dateIn = days => new Date(Date.now() + days * 86400000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
export function splitOf(rules, send, plan = 'month', boost = 0) {
  const p = (rules.plans || []).find(x => x.plan === plan) || { backPct: 0, days: null, weightX: 1 }; const b = rules.boostMode === 'rank' || plan === 'vault' ? 0 : boost; const backPct = Math.min(100, p.backPct + (rules.boostBackPts || 0) * b);
  const kept = send * rules.skimPct / 100; const locked = send - kept; const back = locked * backPct / 100;
  return { send, kept, locked, back, house: locked - back, backPct, days: p.days, weightX: p.weightX, floor: send > 0 ? back / send : 0, vault: plan === 'vault' };
}
export function usePoolRules(given) {
  const [r, setR] = useState(given || null);
  useEffect(() => { if (given) { setR(given); return undefined; } let on = true; Promise.resolve().then(() => fetch(apiUrl('/api/cats/pool/rules'))).then(x => (x?.ok ? x.json() : null)).then(j => on && j?.rules && setR(j.rules)).catch(() => {}); return () => { on = false; }; }, [given]);
  return r;
}
export function PlanPicker(props) { return props.rules?.deal !== 'plans' ? null : <OldPlanPicker {...props} />; }
function OldPlanPicker({ rules, send, plan, setPlan, boost = 0, testid = 'plan-picker' }) {
  const [sure, setSure] = useState(false);
  const pick = k => { if (k === 'vault' && !sure) { setSure(true); return; } setSure(false); setPlan(k); };
  return <div className="spf-plans" role="radiogroup" aria-label="Plan" data-testid={testid}>{(rules.plans || []).map(p => { const s = splitOf(rules, send, p.plan, boost); const [t, tag] = PLAN_NAMES[p.plan] || [p.plan, '']; const v = p.plan === 'vault';
    return <button key={p.plan} type="button" role="radio" aria-checked={plan === p.plan} className={`spf-plan${plan === p.plan ? ' is-on' : ''}${v ? ' is-vault' : ''}${v && sure ? ' is-sure' : ''}`} onClick={() => pick(p.plan)} data-tip={v ? 'What it sends stays in the Collective for good. In return it takes the biggest part of the fee pot while it keeps sending.' : `${s.backPct}% of what locks comes back, a little every second, by ${dateIn(p.days)}. It also earns ${p.weightX}x from the fee pot while it works.`} data-testid={`plan-${p.plan}`}><small>{v && sure ? 'Tap again to confirm' : tag}</small><b>{t}</b>{v ? <em className="m-num is-gone">$0 back</em> : <em className="m-num">{money(s.back)} back</em>}<i>{v ? 'none, ever' : `by ${dateIn(p.days)}`}</i><u className="m-num">{p.weightX}x fee pot</u>{(() => { const live = rules.live; if (!live) return null; const w = send * p.weightX; const day = (live.potDayUsd || 0) * (w / Math.max(1e-9, (live.weight || 0) + w)); if (day <= 0) return <span className="spf-even is-none" data-tip="Nothing has been traded into the fee pot yet, so it cannot say">Fee pot empty today</span>; const n = Math.max(0, send - s.back) / day; return <span className="spf-even" data-tip="At today's fee pot, and with nothing else sent. An estimate, not a promise" data-testid={`plan-even-${p.plan}`}>Pays for itself ≈ {n < 1 ? 'under a day' : `${Math.ceil(n)}d`}</span>; })()}</button>; })}</div>;
}
const GrowthLinesLazy = lazy(() => import('./MoneyCharts').then(m => ({ default: m.GrowthLines })));
// 🌱 The owner's question: why send, if less comes back? Because the send buys a share of everyone's fees. This shows when that beats the gap, on the real pool code.
export function GrowthCalc(props) { const r = usePoolRules(); if (!r) return null; return r.deal === 'plans' ? <OldGrowthCalc {...props} /> : null; }
function OldGrowthCalc({ cfg = null, testid = 'growth-calc' }) {
  const [plan, setPlan] = useState('month'); const [vol, setVol] = useState(100); const [pct, setPct] = useState(100); const [g, setG] = useState(null); const [err, setErr] = useState(false); const key = cfg ? JSON.stringify(cfg) : '';
  useEffect(() => { let on = true; const t = setTimeout(() => { Promise.resolve().then(() => fetch(apiUrl(`/api/cats/pool/growth?plan=${plan}&volume=${vol}&senders=${pct}${key ? `&cfg=${encodeURIComponent(key)}` : ''}`))).then(r => (r?.ok ? r.json() : Promise.reject())).then(j => { if (on) { setG(j); setErr(false); } }).catch(() => { if (on) setErr(true); }); }, 200); return () => { on = false; clearTimeout(t); }; }, [plan, vol, pct, key]);
  const seg = (label, opts, val, set, tip, k) => <div className="spf-knob"><small>{label}</small><span className="m-seg" role="group" aria-label={label}>{opts.map(([v, l]) => <button key={v} type="button" className={val === v ? 'active' : ''} aria-pressed={val === v} onClick={() => set(v)} data-tip={tip} data-testid={`grw-${k}-${v}`}>{l}</button>)}</span></div>;
  const first = g ? g.rows.find(r => r[`s${g.senders[1]}`] > 0) : null; const mid = g ? g.rows[2] : null;
  return <section className="grw" data-testid={testid}><div className="spf-knobs">{seg('THE PLAN', [['week', '1 week'], ['month', '30 days'], ['quarter', '90 days'], ['vault', 'Vault']], plan, setPlan, 'How the send comes back', 'plan')}{seg('EACH AGENT TRADES, A DAY', [[0, '$0'], [25, '$25'], [100, '$100'], [500, '$500'], [2000, '$2K']], vol, setVol, 'More trading means more fees in the pot', 'vol')}{seg('OF ALL TRADERS, THESE SEND', [[100, 'All'], [60, '60%'], [30, '30%']], pct, setPct, 'All = only senders trade, the careful case. Fees from traders who do not send also fill the pot', 'pct')}</div>
    {err ? <p className="kd-err" role="alert">⚠ The numbers did not load. Try again in a moment.</p> : null}
    {g ? <><Suspense fallback={<div className="spf-wait" />}><GrowthLinesLazy g={g} testid={`${testid}-chart`} /></Suspense>
      <small className="grw-x">Across the bottom: swaps by everyone else on FEELESS, a day. Each line: a ${g.send} send over {g.days} days.</small>
      <p className="spf-say" data-testid={`${testid}-say`}>{first ? <>With {g.senders[1].toLocaleString()} senders, a ${g.send} send comes out <b className="grw-up">${first[`s${g.senders[1]}`].toFixed(2)} ahead</b> {first.swaps ? `once everyone else swaps $${first.swaps.toLocaleString()} a day` : 'from members\' fees alone'}.</> : <>With {g.senders[1].toLocaleString()} senders, a ${g.send} send stays <b className="grw-dn">${Math.abs(mid[`s${g.senders[1]}`]).toFixed(2)} short</b> here. It needs more trading, or fewer senders sharing.</>} Over those {g.days} days it also pays ${(g.feeEach * g.days).toFixed(2)} in its own trade fees, as it would anyway, and it can earn at most {g.roomX}x what it sent. <em>The real pool rules on these numbers, assuming a {g.swapFeePct}% swap fee. An example, not a promise.</em></p></> : <div className="spf-wait" />}</section>;
}
const ProfitLinesLazy = lazy(() => import('./MoneyCharts').then(m => ({ default: m.ProfitLines })));
const FEES = [[0, 'No fees'], [10, '$10'], [100, '$100'], [1000, '$1K'], [10000, '$10K']]; const CROWD = [[0, 'Only it'], [1000, '$1K'], [10000, '$10K'], [100000, '$100K'], [1000000, '$1M']];
// 🧮 Can an agent come out ahead? The answer depends on the fees everyone pays and how many share them, so both are the viewer's to set. The server runs the real pool code on these numbers.
export function ProfitCalc({ send, plan, boost, rules, testid }) {
  const [fees, setFees] = useState(100); const [crowd, setCrowd] = useState(10000); const [p, setP] = useState(null); const [err, setErr] = useState(false);
  useEffect(() => { let on = true; const t = setTimeout(() => { Promise.resolve().then(() => fetch(apiUrl(`/api/cats/pool/project?usd=${send}&plan=${plan}&boost=${boost}&feesDay=${fees}&othersUsd=${crowd}`))).then(r => (r?.ok ? r.json() : Promise.reject())).then(j => { if (on) { setP(j); setErr(false); } }).catch(() => { if (on) setErr(true); }); }, 120); return () => { on = false; clearTimeout(t); }; }, [send, plan, boost, fees, crowd]);
  const seg = (label, opts, val, set, tip, key) => <div className="spf-knob"><small>{label}</small><span className="m-seg" role="group" aria-label={label}>{opts.map(([v, l]) => <button key={v} type="button" className={val === v ? 'active' : ''} aria-pressed={val === v} onClick={() => set(v)} data-tip={tip} data-testid={`spf-${key}-${v}`}>{l}</button>)}</span></div>;
  const ahead = p && p.profit > 0; const vault = plan === 'vault';
  return <div className="spf-calc" data-testid={`${testid}-calc`}>
    <div className="spf-knobs">{seg('FEES EVERYONE PAYS, A DAY', FEES, fees, setFees, 'Real trade and task fees from all members. Part of each goes to the fee pot', 'fees')}{seg('MONEY OTHERS HAVE WORKING', CROWD, crowd, setCrowd, 'The more others have working, the smaller its part of the pot', 'crowd')}</div>
    {rules?.live ? <small className="spf-live" data-testid="spf-live">Right now the pot pays <b className="m-num">{money(rules.live.potDayUsd)}</b> a day across <b className="m-num">{money(rules.live.weight)}</b> working.</small> : null}
    {err ? <p className="kd-err" role="alert">⚠ The calculator did not answer. Try again in a moment.</p> : null}
    {p ? <><div className="spf-sum" data-testid={`${testid}-sum`}><span data-tip="What the agent sends"><small>SENT</small><b className="m-num">{money(p.sent)}</b></span><span data-tip={vault ? 'A Vault send never comes back. It earns from the fee pot only' : 'Comes back along its plan, on a fixed date'}><small>FROM ITS PLAN</small><b className="m-num">{money(p.back)}</b></span><span data-tip="Its part of the fee pot over these days. It rises and falls with real fees"><small>FROM THE FEE POT</small><b className="m-num">{money(p.pot)}</b></span><span className={ahead ? 'is-up' : 'is-dn'} data-tip="Everything that came back, minus what it sent"><small>{ahead ? 'AHEAD BY' : 'SHORT BY'}</small><b className="m-num" data-testid="spf-profit">{money(Math.abs(p.profit))}</b></span></div>
      <p className="spf-say" data-testid="spf-back">{ahead ? <>Comes out ahead{p.breakEven ? <> on <b>day {p.breakEven}</b></> : null}, at these fees and this many others.</> : <>Does not pay for itself in {p.days} days at these numbers. More fees, or fewer others, would change that.</>}{p.capped ? ' It hit the limit on what one agent can take for its size, so the rest stays in the pot.' : ''} <em>An example from the real rules, not a promise.</em></p>
      <Suspense fallback={<div className="spf-wait" />}><ProfitLinesLazy p={p} testid={`${testid}-chart`} /></Suspense></> : <div className="spf-wait" />}
  </div>;
}
export const FLOW_COLORS = { Sent: '#ffc24d', Locked: '#c58bff', 'Back to the agent': '#3ee58a', 'Collective, right away': '#57c7ff', 'Collective, as it comes back': '#2f7fd6', Vault: '#c58bff', 'Trade fees': '#ffc24d', 'Swap fees': '#ffc24d', 'Fee pot': '#ff8bd8', Members: '#3ee58a', Collective: '#57c7ff', FEELESS: '#8fa3cc', 'Deposit fees': '#ffc24d' };
export const sendRows = s => (s.vault ? [['Sent', 'Collective, right away', s.kept], ['Sent', 'Vault', s.locked]] : [['Sent', 'Collective, right away', s.kept], ['Sent', 'Locked', s.locked], ['Locked', 'Back to the agent', s.back], ['Locked', 'Collective, as it comes back', s.house]]);
export function SplitFlow(props) { const r = usePoolRules(props.rules); if (r && r.deal !== 'plans') return <KeepDeal rules={r} sendUsd={props.sendUsd} testid={props.testid || 'keep-deal'} />; return r ? <OldSplitFlow {...props} rules={r} /> : null; }
function OldSplitFlow({ rules: given, sendUsd = null, plan: fixedPlan = null, onPlan = null, testid = 'split-flow' }) {
  const rules = usePoolRules(given?.plans ? given : null); const [win, setWin] = useState(100); const [pct, setPct] = useState(10); const [boostOn, setBoostOn] = useState(false); const [own, setOwn] = useState('month');
  if (!rules) return null;
  const plan = fixedPlan || own; const setPlan = onPlan || setOwn; const given$ = sendUsd != null; const send = given$ ? sendUsd : win * pct / 100; const s = splitOf(rules, send, plan, boostOn ? 1 : 0);
  return <section className="spf" data-testid={testid} aria-label="Where a proof's money goes">
    {given$ ? null : <div className="spf-ctl"><span className="m-seg" role="group" aria-label="Size of the win">{[20, 100, 1000].map(v => <button key={v} type="button" className={win === v ? 'active' : ''} aria-pressed={win === v} onClick={() => setWin(v)} data-tip={`A win of $${v}`} data-testid={`spf-win-${v}`}>Win ${v}</button>)}</span>
      <span className="m-seg" role="group" aria-label="Share it sends">{[5, 10, 15, 20, 25].map(v => <button key={v} type="button" className={pct === v ? 'active' : ''} aria-pressed={pct === v} onClick={() => setPct(v)} data-tip={`It sends ${v}% of the win`} data-testid={`spf-pct-${v}`}>{v}%</button>)}</span>
      {rules.boostMode !== 'rank' ? <button type="button" className={`m-btn spf-boost${boostOn ? ' m-go' : ''}`} aria-pressed={boostOn} onClick={() => setBoostOn(x => !x)} data-tip="See the same send with a full boost" data-testid="spf-boost">{boostOn ? 'Full boost' : 'No boost'}</button> : null}</div>}
    <PlanPicker rules={rules} send={send} plan={plan} setPlan={setPlan} boost={boostOn ? 1 : 0} />
    <ProfitCalc send={send} plan={plan} boost={boostOn ? 1 : 0} rules={rules} testid={testid} />
  </section>;
}

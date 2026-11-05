import React, { Suspense, lazy, useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import '../../styles/boosts.css';
import '../../styles/moneyCharts.css';

// 🪙 WHERE A PROOF'S MONEY GOES (owner 2026-11-05: less confusing, more addicting). Pick a plan and see exactly how much comes back and by when, drawn as pipes as thick as the money. Every number is the live rule from the server.
export const money = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : n >= 100 ? `$${n.toFixed(0)}` : `$${n.toFixed(2)}`; };
export const PLAN_NAMES = { week: ['1 week', 'Fast'], month: ['30 days', 'Balanced'], quarter: ['90 days', 'Most back'], vault: ['Vault', 'Never comes back'] };
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
export function PlanPicker({ rules, send, plan, setPlan, boost = 0, testid = 'plan-picker' }) {
  const [sure, setSure] = useState(false);
  const pick = k => { if (k === 'vault' && !sure) { setSure(true); return; } setSure(false); setPlan(k); };
  return <div className="spf-plans" role="radiogroup" aria-label="Plan" data-testid={testid}>{(rules.plans || []).map(p => { const s = splitOf(rules, send, p.plan, boost); const [t, tag] = PLAN_NAMES[p.plan] || [p.plan, '']; const v = p.plan === 'vault';
    return <button key={p.plan} type="button" role="radio" aria-checked={plan === p.plan} className={`spf-plan${plan === p.plan ? ' is-on' : ''}${v ? ' is-vault' : ''}${v && sure ? ' is-sure' : ''}`} onClick={() => pick(p.plan)} data-tip={v ? 'What it sends stays in the Collective for good. In return it takes the biggest part of the fee pot while it keeps sending.' : `${s.backPct}% of what locks comes back, a little every second, by ${dateIn(p.days)}. It also earns ${p.weightX}x from the fee pot while it works.`} data-testid={`plan-${p.plan}`}><small>{v && sure ? 'Tap again to confirm' : tag}</small><b>{t}</b>{v ? <em className="m-num is-gone">$0 back</em> : <em className="m-num">{money(s.back)} back</em>}<i>{v ? 'none, ever' : `by ${dateIn(p.days)}`}</i><u className="m-num">{p.weightX}x fee pot</u>{(() => { const live = rules.live; if (!live) return null; const w = send * p.weightX; const day = (live.potDayUsd || 0) * (w / Math.max(1e-9, (live.weight || 0) + w)); if (day <= 0) return <span className="spf-even is-none" data-tip="Nothing has been traded into the fee pot yet, so it cannot say">Fee pot empty today</span>; const n = Math.max(0, send - s.back) / day; return <span className="spf-even" data-tip="At today's fee pot, and with nothing else sent. An estimate, not a promise" data-testid={`plan-even-${p.plan}`}>Pays for itself ≈ {n < 1 ? 'under a day' : `${Math.ceil(n)}d`}</span>; })()}</button>; })}</div>;
}
const MoneyFlowLazy = lazy(() => import('./MoneyCharts').then(m => ({ default: m.MoneyFlow })));
export const FLOW_COLORS = { Sent: '#ffc24d', Locked: '#c58bff', 'Back to the agent': '#3ee58a', 'Collective, right away': '#57c7ff', 'Collective, as it comes back': '#2f7fd6', Vault: '#c58bff', 'Trade fees': '#ffc24d', 'Swap fees': '#ffc24d', 'Fee pot': '#ff8bd8', Members: '#3ee58a', Collective: '#57c7ff', FEELESS: '#8fa3cc', 'Deposit fees': '#ffc24d' };
export const sendRows = s => (s.vault ? [['Sent', 'Collective, right away', s.kept], ['Sent', 'Vault', s.locked]] : [['Sent', 'Collective, right away', s.kept], ['Sent', 'Locked', s.locked], ['Locked', 'Back to the agent', s.back], ['Locked', 'Collective, as it comes back', s.house]]);
export function SplitFlow({ rules: given, sendUsd = null, plan: fixedPlan = null, onPlan = null, testid = 'split-flow' }) {
  const rules = usePoolRules(given?.plans ? given : null); const [win, setWin] = useState(100); const [pct, setPct] = useState(10); const [boostOn, setBoostOn] = useState(false); const [own, setOwn] = useState('month');
  if (!rules) return null;
  const plan = fixedPlan || own; const setPlan = onPlan || setOwn; const given$ = sendUsd != null; const send = given$ ? sendUsd : win * pct / 100; const s = splitOf(rules, send, plan, boostOn ? 1 : 0);
  return <section className="spf" data-testid={testid} aria-label="Where a proof's money goes">
    {given$ ? null : <div className="spf-ctl"><span className="m-seg" role="group" aria-label="Size of the win">{[20, 100, 1000].map(v => <button key={v} type="button" className={win === v ? 'active' : ''} aria-pressed={win === v} onClick={() => setWin(v)} data-tip={`A win of $${v}`} data-testid={`spf-win-${v}`}>Win ${v}</button>)}</span>
      <span className="m-seg" role="group" aria-label="Share it sends">{[5, 10, 15, 20, 25].map(v => <button key={v} type="button" className={pct === v ? 'active' : ''} aria-pressed={pct === v} onClick={() => setPct(v)} data-tip={`It sends ${v}% of the win`} data-testid={`spf-pct-${v}`}>{v}%</button>)}</span>
      {rules.boostMode !== 'rank' ? <button type="button" className={`m-btn spf-boost${boostOn ? ' m-go' : ''}`} aria-pressed={boostOn} onClick={() => setBoostOn(x => !x)} data-tip="See the same send with a full boost" data-testid="spf-boost">{boostOn ? 'Full boost' : 'No boost'}</button> : null}</div>}
    <PlanPicker rules={rules} send={send} plan={plan} setPlan={setPlan} boost={boostOn ? 1 : 0} />
    <Suspense fallback={<div className="spf-wait" />}><MoneyFlowLazy rows={sendRows(s)} colors={FLOW_COLORS} height={230} testid={`${testid}-chart`} label={`${money(s.send)} sent: ${money(s.kept)} kept by the Collective, ${money(s.locked)} locked, ${money(s.back)} back to the agent`} /></Suspense>
    <div className="spf-meter" data-tip="Of each $1 sent: what is sure to come back to the agent, and what stays in the Collective" data-testid="spf-meter">
      <small data-testid="spf-back">{s.vault ? <><b className="m-num">{money(s.send)}</b> stays in the Collective. It earns the biggest part of the fee pot while it keeps sending.</> : <><b className="m-num">{money(s.back)}</b> comes back by {dateIn(s.days)}, plus a part of the fee pot on top. The fee part rises and falls with trading. It is not promised.</>}</small></div>
  </section>;
}

import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { GrowthExample } from './GrowthExample';
import '../../styles/boosts.css';

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
const W = v => Math.max(2.5, Math.min(26, 2.5 + Math.sqrt(Math.max(0, v)) * 3));
function Pipe({ d, w, tone, flow = true, dash = false, hot, delay = 0 }) {
  return <g className={`spf-pipe is-${tone}${hot ? ' is-hot' : ''}`}><path className="is-bed" d={d} strokeWidth={w + 5} /><path className={`is-core${dash ? ' is-dash' : ''}`} d={d} strokeWidth={w} />
    {flow ? [0, 1, 2].map(k => <circle key={k} className="spf-drop" r={Math.max(2, Math.min(5, w / 3))} style={{ offsetPath: `path('${d}')`, animationDelay: `${delay + k * 0.8}s` }} />) : null}</g>;
}
function Node({ x, y, w = 118, h = 54, tone, label, value, sub, tip, hot, testid }) {
  return <g className={`spf-node is-${tone}${hot ? ' is-hot' : ''}`} transform={`translate(${x - w / 2} ${y - h / 2})`} data-tip={tip} data-testid={testid} tabIndex={0} role="img" aria-label={`${label} ${value}${sub ? ` ${sub}` : ''}`}>
    <rect width={w} height={h} rx="13" /><text className="is-label" x={w / 2} y="15">{label}</text><text className="is-value" x={w / 2} y="33" key={value}>{value}</text>{sub ? <text className="is-sub" x={w / 2} y="46">{sub}</text> : null}</g>;
}
export function PlanPicker({ rules, send, plan, setPlan, boost = 0, testid = 'plan-picker' }) {
  const [sure, setSure] = useState(false);
  const pick = k => { if (k === 'vault' && !sure) { setSure(true); return; } setSure(false); setPlan(k); };
  return <div className="spf-plans" role="radiogroup" aria-label="Plan" data-testid={testid}>{(rules.plans || []).map(p => { const s = splitOf(rules, send, p.plan, boost); const [t, tag] = PLAN_NAMES[p.plan] || [p.plan, '']; const v = p.plan === 'vault';
    return <button key={p.plan} type="button" role="radio" aria-checked={plan === p.plan} className={`spf-plan${plan === p.plan ? ' is-on' : ''}${v ? ' is-vault' : ''}${v && sure ? ' is-sure' : ''}`} onClick={() => pick(p.plan)} data-tip={v ? 'What it sends stays in the Collective for good. In return it takes the biggest part of the fee pot while it keeps sending.' : `${s.backPct}% of what locks comes back, a little every second, by ${dateIn(p.days)}. It also earns ${p.weightX}x from the fee pot while it works.`} data-testid={`plan-${p.plan}`}><small>{v && sure ? 'Tap again to confirm' : tag}</small><b>{t}</b>{v ? <em className="m-num is-gone">$0 back</em> : <em className="m-num">{money(s.back)} back</em>}<i>{v ? 'none, ever' : `by ${dateIn(p.days)}`}</i><u className="m-num">{p.weightX}x fee pot</u></button>; })}</div>;
}
export function SplitFlow({ rules: given, sendUsd = null, hot = null, plan: fixedPlan = null, onPlan = null, testid = 'split-flow' }) {
  const rules = usePoolRules(given); const [view, setView] = useState('one'); const [win, setWin] = useState(100); const [pct, setPct] = useState(10); const [boostOn, setBoostOn] = useState(false); const [own, setOwn] = useState('month'); const id = useRef(`spf${Math.random().toString(36).slice(2, 8)}`).current;
  if (!rules) return null;
  const plan = fixedPlan || own; const setPlan = onPlan || setOwn; const given$ = sendUsd != null; const send = given$ ? sendUsd : win * pct / 100; const s = splitOf(rules, send, plan, boostOn ? 1 : 0);
  const tank = s.send > 0 ? Math.max(0.12, Math.min(1, s.locked / Math.max(s.send, 1))) : 0.12; const backTip = s.vault ? 'The Vault returns nothing. It earns from the fee pot instead.' : `Comes back a little every second until ${dateIn(s.days)}. This is the live count on its desk.`;
  return <section className="spf" data-testid={testid} aria-label="Where a proof's money goes">
    <div className="spf-view m-seg" role="tablist" aria-label="Show"><button type="button" role="tab" aria-selected={view === 'one'} className={view === 'one' ? 'active' : ''} onClick={() => setView('one')} data-testid="spf-view-one" data-tip="Where one proof's money goes">One proof</button><button type="button" role="tab" aria-selected={view === 'year'} className={view === 'year' ? 'active' : ''} onClick={() => setView('year')} data-testid="spf-view-year" data-tip="How the Collective grows and how members earn over a year">A year</button></div>
    {view === 'year' ? <GrowthExample rules={rules} /> : <>
    {given$ ? null : <div className="spf-ctl"><span className="m-seg" role="group" aria-label="Size of the win">{[20, 100, 1000].map(v => <button key={v} type="button" className={win === v ? 'active' : ''} aria-pressed={win === v} onClick={() => setWin(v)} data-tip={`Try a $${v} win`}>Win ${v}</button>)}</span>
      <span className="m-seg" role="group" aria-label="Share it sends">{[5, 10, 15, 20, 25].map(v => <button key={v} type="button" className={pct === v ? 'active' : ''} aria-pressed={pct === v} onClick={() => setPct(v)} data-tip={`It sends ${v}% of the win`}>{v}%</button>)}</span>
      {rules.boostMode !== 'rank' ? <button type="button" className={`m-btn spf-boost${boostOn ? ' m-go' : ''}`} aria-pressed={boostOn} onClick={() => setBoostOn(x => !x)} data-tip="See the same send with a full boost" data-testid="spf-boost">{boostOn ? 'Full boost' : 'No boost'}</button> : null}</div>}
    <PlanPicker rules={rules} send={send} plan={plan} setPlan={setPlan} boost={boostOn ? 1 : 0} />
    <svg viewBox="0 0 420 356" role="group" aria-label={`${money(s.send)} sent: ${money(s.kept)} kept by the Collective, ${money(s.locked)} locked, ${money(s.back)} back to the agent`}>
      <defs><linearGradient id={`${id}f`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#7fd0ff" /><stop offset="1" stopColor="#1f6dff" /></linearGradient><clipPath id={`${id}c`}><rect x="162" y="150" width="96" height="86" rx="16" /></clipPath></defs>
      <Pipe d="M92 42 H148" w={W(s.send + (given$ ? 0 : win - send) * 0.1)} tone="gold" />
      {given$ ? null : <Pipe d="M272 42 H326" w={W((win - send) * 0.2)} tone="dim" flow={false} />}
      <Pipe d="M196 68 C196 96 80 92 80 122" w={W(s.kept)} tone="blue" hot={hot === 'kept'} delay={0.2} />
      <Pipe d="M222 68 V150" w={W(s.locked)} tone="violet" hot={hot === 'locked'} delay={0.3} />
      <Pipe d="M388 136 C388 200 366 250 340 296" w={4} tone="pot" dash hot={hot === 'pot'} delay={0.5} />
      {s.vault ? null : <Pipe d="M236 236 C236 268 310 262 310 296" w={W(s.back)} tone="green" hot={hot === 'back'} delay={0.6} />}
      {s.house > 0 ? <Pipe d="M196 236 C196 268 100 262 100 296" w={W(s.house)} tone="blue" hot={hot === 'house'} delay={0.7} /> : null}
      {given$ ? <Node x={72} y={42} w={104} tone="gold" label="PROOF" value="+50% win" tip="Only a real proof that made +50% or more can send. Its transaction, link and snapshot go with it." /> : <Node x={72} y={42} w={104} tone="gold" label="IT WINS" value={money(win)} tip="A proof closes at +50% or more. Smaller wins and losses send nothing." />}
      <Node x={210} y={42} w={124} tone="gold" label={given$ ? 'IT SENDS' : `SENDS ${pct}%`} value={money(s.send)} sub="in SOL, on-chain" tip="Its own wallet sends this to the Collective wallet. It is read back from the chain before it counts." testid="spf-send" />
      {given$ ? null : <Node x={366} y={42} w={92} h={46} tone="dim" label="IT KEEPS" value={money(win - send)} tip="The rest of the win never leaves its wallet." />}
      <Node x={80} y={146} w={120} tone="blue" label={`COLLECTIVE ${rules.skimPct}%`} value={money(s.kept)} sub="kept right away" hot={hot === 'kept'} tip="The Collective's part of every proof sent. It stays in the Collective." testid="spf-kept" />
      <g className={`spf-tank${hot === 'locked' ? ' is-hot' : ''}`} data-tip={s.vault ? 'This goes into the Vault for good.' : `Locked until ${dateIn(s.days)}, then it is done. It cannot be pulled out early, but boost points can bring the date closer.`} data-testid="spf-locked" tabIndex={0} role="img" aria-label={`${s.vault ? 'Vault' : 'Locked'} ${money(s.locked)}`}>
        <rect className="is-glass" x="162" y="150" width="96" height="86" rx="16" />
        <g clipPath={`url(#${id}c)`}><g className="spf-liquid" style={{ transform: `translateY(${86 - 86 * tank}px)` }}><path fill={`url(#${id}f)`} d="M100 156 q22 -9 44 0 t44 0 t44 0 t44 0 t44 0 V260 H100Z" /></g></g>
        <text className="is-label" x="210" y="172">{s.vault ? 'VAULT' : 'LOCKED'}</text><text className="is-value" x="210" y="196" key={s.locked}>{money(s.locked)}</text><text className="is-sub" x="210" y="214">{s.vault ? 'for good' : `until ${dateIn(s.days)}`}</text>
        <rect className="is-rim" x="162" y="150" width="96" height="86" rx="16" /></g>
      <Node x={366} y={112} w={96} h={48} tone="pot" label="FEE POT" value={`${s.weightX}x share`} tip={`${rules.potPct}% of every trade and task fee fills this pot, and nothing a member deposits or sends. While its money works, it earns a part of the pot, right into its earnings. It rises and falls with trading, so it is never promised.`} hot={hot === 'pot'} testid="spf-pot" />
      <Node x={320} y={324} w={158} h={58} tone="green" label={s.vault ? 'NOTHING BACK' : `BACK TO THE AGENT ${s.backPct}%`} value={money(s.back)} sub={s.vault ? 'earns from the fee pot' : `by ${dateIn(s.days)}`} hot={hot === 'back'} tip={backTip} testid="spf-back" />
      <Node x={84} y={324} w={136} h={58} tone="blue" label={s.vault ? 'COLLECTIVE VAULT' : `COLLECTIVE ${Math.round((100 - s.backPct) * 10) / 10}%`} value={money(s.house)} sub={s.vault ? 'for good' : 'as it comes back'} hot={hot === 'house'} tip="The Collective's part. It stays in the Collective." testid="spf-house" />
    </svg>
    <div className="spf-meter" data-tip="Of each $1 sent: what is sure to come back to the agent, and what stays in the Collective" data-testid="spf-meter"><span className="spf-bar" aria-hidden="true"><i className="is-green" style={{ flexGrow: s.floor }} /><i className="is-blue" style={{ flexGrow: 1 - s.floor }} /></span>
      <small>{s.vault ? <><b className="m-num">{money(s.send)}</b> stays in the Collective. It earns the biggest part of the fee pot while it keeps sending.</> : <><b className="m-num">{money(s.back)}</b> comes back by {dateIn(s.days)}, plus a part of the fee pot on top.</>} <em>The fee part rises and falls with trading. It is not promised.</em></small></div></>}
  </section>;
}

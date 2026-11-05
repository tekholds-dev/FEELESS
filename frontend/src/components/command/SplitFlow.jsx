import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { GrowthExample } from './GrowthExample';
import '../../styles/boosts.css';

// 🪙 THE SPLIT, DRAWN (owner 2026-11-04: "visual eye candy, not just text"): a win pours down real pipes, each as thick as its money. Every number is the live rule from the server, and a hover says it in plain words.
export const money = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : n >= 100 ? `$${n.toFixed(0)}` : `$${n.toFixed(2)}`; };
export function splitOf(rules, send, boost = 0) {
  const b = rules.boostMode === 'rank' ? 0 : boost; const split = rules.splitPct + (rules.splitMaxPct - rules.splitPct) * b; const days = rules.halfLifeDays + (rules.halfLifeMinDays - rules.halfLifeDays) * b;
  const kept = send * rules.skimPct / 100; const locked = send - kept; const back = locked * split / 100;
  return { send, kept, locked, back, house: locked - back, split, days, floor: send > 0 ? back / send : 0 };
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
export function SplitFlow({ rules: given, sendUsd = null, hot = null, boost: fixedBoost = null, testid = 'split-flow' }) {
  const rules = usePoolRules(given); const [view, setView] = useState('one'); const [win, setWin] = useState(100); const [pct, setPct] = useState(10); const [boostOn, setBoostOn] = useState(false); const id = useRef(`spf${Math.random().toString(36).slice(2, 8)}`).current;
  if (!rules) return null;
  const given$ = sendUsd != null; const send = given$ ? sendUsd : win * pct / 100; const b = fixedBoost ?? (boostOn ? 1 : 0); const s = splitOf(rules, send, b);
  const tank = s.send > 0 ? Math.max(0.12, Math.min(1, s.locked / Math.max(s.send, 1))) : 0.12;
  return <section className="spf" data-testid={testid} aria-label="Where a proof's money goes">
    <div className="spf-view m-seg" role="tablist" aria-label="Show"><button type="button" role="tab" aria-selected={view === 'one'} className={view === 'one' ? 'active' : ''} onClick={() => setView('one')} data-testid="spf-view-one" data-tip="Where one proof's money goes">One proof</button><button type="button" role="tab" aria-selected={view === 'year'} className={view === 'year' ? 'active' : ''} onClick={() => setView('year')} data-testid="spf-view-year" data-tip="How the Collective grows and how members earn over a year">A year</button></div>
    {view === 'year' ? <GrowthExample rules={rules} /> : <>
    {given$ ? null : <div className="spf-ctl"><span className="m-seg" role="group" aria-label="Size of the win">{[20, 100, 1000].map(v => <button key={v} type="button" className={win === v ? 'active' : ''} aria-pressed={win === v} onClick={() => setWin(v)} data-tip={`Try a $${v} win`}>Win ${v}</button>)}</span>
      <span className="m-seg" role="group" aria-label="Share it sends">{[5, 10, 15, 20, 25].map(v => <button key={v} type="button" className={pct === v ? 'active' : ''} aria-pressed={pct === v} onClick={() => setPct(v)} data-tip={`It sends ${v}% of the win`}>{v}%</button>)}</span>
      {fixedBoost == null && rules.boostMode !== 'rank' ? <button type="button" className={`m-btn spf-boost${boostOn ? ' m-go' : ''}`} aria-pressed={boostOn} onClick={() => setBoostOn(x => !x)} data-tip="See the same send with a full boost: a better split and a faster release" data-testid="spf-boost">{boostOn ? 'Full boost' : 'No boost'}</button> : null}</div>}
    <svg viewBox="0 0 420 356" role="group" aria-label={`${money(s.send)} sent: ${money(s.kept)} kept by the Collective, ${money(s.locked)} locked, ${money(s.back)} released back to the agent`}>
      <defs><linearGradient id={`${id}f`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#7fd0ff" /><stop offset="1" stopColor="#1f6dff" /></linearGradient><clipPath id={`${id}c`}><rect x="162" y="150" width="96" height="86" rx="16" /></clipPath></defs>
      <Pipe d="M92 42 H148" w={W(s.send + (given$ ? 0 : win - send) * 0.1)} tone="gold" />
      {given$ ? null : <Pipe d="M272 42 H326" w={W((win - send) * 0.2)} tone="dim" flow={false} />}
      <Pipe d="M196 68 C196 96 80 92 80 122" w={W(s.kept)} tone="blue" hot={hot === 'kept'} delay={0.2} />
      <Pipe d="M222 68 V150" w={W(s.locked)} tone="violet" hot={hot === 'locked'} delay={0.3} />
      <Pipe d="M392 136 C392 176 310 168 258 184" w={3} tone="pot" dash hot={hot === 'pot'} delay={0.5} />
      <Pipe d="M196 236 C196 268 112 262 112 296" w={W(s.back)} tone="green" hot={hot === 'back'} delay={0.6} />
      <Pipe d="M236 236 C236 268 320 262 320 296" w={W(s.house)} tone="blue" hot={hot === 'house'} delay={0.7} />
      {given$ ? <Node x={72} y={42} w={104} tone="gold" label="PROOF" value="+50% win" tip="Only a real proof that made +50% or more can send. Its transaction, link and snapshot go with it." /> : <Node x={72} y={42} w={104} tone="gold" label="IT WINS" value={money(win)} tip="A proof closes at +50% or more. Smaller wins and losses send nothing." />}
      <Node x={210} y={42} w={124} tone="gold" label={given$ ? 'IT SENDS' : `SENDS ${pct}%`} value={money(s.send)} sub="in SOL, on-chain" tip="Its own wallet sends this to the Collective wallet. It is read back from the chain before it counts." testid="spf-send" />
      {given$ ? null : <Node x={366} y={42} w={92} h={46} tone="dim" label="IT KEEPS" value={money(win - send)} tip="The rest of the win never leaves its wallet." />}
      <Node x={80} y={146} w={120} tone="blue" label={`COLLECTIVE ${rules.skimPct}%`} value={money(s.kept)} sub="kept right away" hot={hot === 'kept'} tip="The Collective's part of every proof sent. It stays in the Collective." testid="spf-kept" />
      <g className={`spf-tank${hot === 'locked' ? ' is-hot' : ''}`} data-tip={`This money is locked. Half of it releases every ${Math.round(s.days)} days, so the count never stops and it can't be pulled out early.`} data-testid="spf-locked" tabIndex={0} role="img" aria-label={`Locked ${money(s.locked)}, half releases every ${Math.round(s.days)} days`}>
        <rect className="is-glass" x="162" y="150" width="96" height="86" rx="16" />
        <g clipPath={`url(#${id}c)`}><g className="spf-liquid" style={{ transform: `translateY(${86 - 86 * tank}px)` }}><path fill={`url(#${id}f)`} d="M100 156 q22 -9 44 0 t44 0 t44 0 t44 0 t44 0 V260 H100Z" /></g></g>
        <text className="is-label" x="210" y="172">LOCKED</text><text className="is-value" x="210" y="196" key={s.locked}>{money(s.locked)}</text><text className="is-sub" x="210" y="214">half out every {Math.round(s.days)}d</text>
        <rect className="is-rim" x="162" y="150" width="96" height="86" rx="16" /></g>
      <Node x={366} y={112} w={96} h={48} tone="pot" label="FEE POT" value={`+ share`} tip={`${rules.potPct}% of every trade and task fee fills this pot, and nothing a member deposits or sends. While money is locked, it earns a part of the pot, which adds to the lock and compounds. It rises and falls with trading, so it is never promised.`} hot={hot === 'pot'} testid="spf-pot" />
      <Node x={112} y={324} w={150} h={58} tone="green" label={`BACK TO THE AGENT ${s.split.toFixed(s.split % 1 ? 1 : 0)}%`} value={money(s.back)} sub="counts up every second" hot={hot === 'back'} tip="Released to its earnings, second by second. This is the live count on its desk." testid="spf-back" />
      <Node x={320} y={324} w={136} h={58} tone="blue" label={`COLLECTIVE ${(100 - s.split).toFixed(s.split % 1 ? 1 : 0)}%`} value={money(s.house)} sub="as it releases" hot={hot === 'house'} tip="The Collective's part of what releases. It stays in the Collective." testid="spf-house" />
    </svg>
    <div className="spf-meter" data-tip="Of each $1 sent: what is sure to come back to the agent, and what stays in the Collective" data-testid="spf-meter"><span className="spf-bar" aria-hidden="true"><i className="is-green" style={{ flexGrow: s.floor }} /><i className="is-blue" style={{ flexGrow: 1 - s.floor }} /></span>
      <small><b className="m-num">{Math.round(s.floor * 100)}¢</b> of each $1 comes back, then a part of the fee pot on top. <em>The fee part rises and falls with fees. It is not promised.</em></small></div></>}
  </section>;
}

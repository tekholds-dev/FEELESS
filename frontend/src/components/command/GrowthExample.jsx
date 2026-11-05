import React, { useMemo, useState } from 'react';
import { growthExample } from '../../lib/proofprint';
import { money, usePoolRules } from './SplitFlow';
import '../../styles/boosts.css';

// 🌊 HOW IT GROWS AND HOW MEMBERS EAT (owner 2026-11-04): the same rules as the ledger, played over a year, on numbers you pick. No new people join in this example, on purpose: it shows nothing here needs them.
const K = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : money(v));
function Chart({ rows, at, series, label }) {
  const top = Math.max(1e-9, ...rows.flatMap(r => series.map(([k]) => r[k]))); const X = i => (i / (rows.length - 1)) * 600; const Y = v => 158 - (v / top) * 148; const i = Math.round(at / 10);
  return <figure className="ge-chart"><figcaption>{label}</figcaption><svg viewBox="0 0 600 164" preserveAspectRatio="none" role="img" aria-label={label}><line className="is-base" x1="0" x2="600" y1="158" y2="158" />{series.map(([k, , c]) => <path key={k} d={rows.map((r, n) => `${n ? 'L' : 'M'}${X(n).toFixed(1)} ${Y(r[k]).toFixed(1)}`).join(' ')} stroke={c} />)}<line className="is-now" x1={X(i)} x2={X(i)} y1="4" y2="160" /></svg>
    <ul className="ge-legend">{series.map(([k, l, c]) => <li key={k}><i style={{ background: c }} />{l} <b className="m-num">{K(rows[i][k])}</b></li>)}</ul></figure>;
}
const Seg = ({ label, value, set, opts, fmt, tip, testid }) => <label className="ge-seg" data-tip={tip}><small>{label}</small><span className="m-seg" role="group" aria-label={label}>{opts.map(v => <button key={v} type="button" className={value === v ? 'active' : ''} aria-pressed={value === v} onClick={() => set(v)} data-testid={`${testid}-${v}`}>{fmt(v)}</button>)}</span></label>;
export const NOT_PONZI = [['Only real trading fees feed members', 'Part of every trade and task fee fills the fee pot. Nothing a member deposits or sends can reach another member.'], ['Nobody gets paid for bringing people', 'There is no referral money, and joining early earns no bigger share.'], ['No rate is promised', 'The count follows real fees. If trading slows, the count slows.'], ['Its own money always comes back first', 'What it locks releases on its own schedule and never depends on anyone else joining.'], ['Every dollar is on a sealed chain', 'Each dollar in is one link of a keyed hash chain, checked against the real wallet every 5 minutes. An edited ledger refuses to load.']];
export function GrowthExample({ rules: given, testid = 'growth-example' }) {
  const rules = usePoolRules(given); const [members, setMembers] = useState(500); const [sendWeek, setSendWeek] = useState(10); const [tradeDay, setTradeDay] = useState(50); const [boost, setBoost] = useState(0); const [at, setAt] = useState(180);
  const rows = useMemo(() => (rules ? growthExample({ potHalfLifeDays: 30, earnRoomX: 1, weightMaxX: 2, ...rules }, { members, sendWeek, tradeDay, boost }) : []), [rules, members, sendWeek, tradeDay, boost]);
  if (!rules || !rows.length) return null;
  const r = rows[Math.round(at / 10)]; const net = r.back + r.locked * ((rules.splitPct) / 100) - r.sent;
  return <section className="ge" data-testid={testid} aria-label="How the Collective grows and how members earn">
    <header><small>EXAMPLE ON THE NUMBERS YOU PICK · NOT A PROMISE</small><h4>A year in the Collective</h4></header>
    <div className="ge-ctl"><Seg label="MEMBERS" value={members} set={setMembers} opts={[50, 500, 5000]} fmt={v => v.toLocaleString()} testid="ge-members" tip="How many agents are in it. None join during the example" /><Seg label="IT SENDS A WEEK" value={sendWeek} set={setSendWeek} opts={[2, 10, 50]} fmt={v => `$${v}`} testid="ge-send" tip="From wins of +50% or more" /><Seg label="EACH TRADES A DAY" value={tradeDay} set={setTradeDay} opts={[5, 50, 500]} fmt={v => `$${v}`} testid="ge-trade" tip="This is what feeds the fee pot. Try $5 and watch the fee share fall" />{rules.boostMode === 'rank' ? null : <Seg label="ITS BOOST" value={boost} set={setBoost} opts={[0, 1]} fmt={v => (v ? 'Full' : 'None')} testid="ge-boost" tip="A better split, a faster release and more of the pot" />}</div>
    <div className="ge-day" data-tip="Slide through the year"><input type="range" min="0" max="360" step="10" value={at} onChange={e => setAt(Number(e.target.value))} aria-label="Day" data-testid="ge-day" /><b className="m-num">Day {at}</b></div>
    <div className="ge-tiles">{[['IT SENT', K(r.sent), 'What it has sent so far'], ['ITS OWN BACK', K(r.own), 'Its own money, released at the split. Sure to come, no matter who joins'], ['FEE SHARE', K(r.fee), 'From members\' trading fees. Rises and falls with trading'], ['AHEAD OR BEHIND', `${net >= 0 ? '+' : '−'}${K(Math.abs(net))}`, 'Earned plus what is still locked and on its way, against what it sent']].map(([k, v, t]) => <span key={k} data-tip={t} className={k.startsWith('AHEAD') ? (net >= 0 ? 'is-up' : 'is-dn') : ''}><small>{k}</small><b className="m-num">{v}</b></span>)}</div>
    <div className="ge-charts"><Chart rows={rows} at={at} label="ONE AGENT" series={[['sent', 'Sent', '#8fa3cc'], ['back', 'Earned', '#3ee58a'], ['fee', 'of that, fee share', '#ff8bd8']]} /><Chart rows={rows} at={at} label="THE COLLECTIVE" series={[['keep', 'Keeps', '#4fb8ff'], ['lock', 'Locked', '#a06bff'], ['pot', 'Fee pot', '#ff8bd8']]} /></div>
    <details className="ge-why"><summary data-tip="The rules that keep it honest">Why it is not a Ponzi</summary><ul>{NOT_PONZI.map(([h, t]) => <li key={h}><b>✓ {h}</b><small>{t}</small></li>)}</ul></details>
  </section>;
}

import React, { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { hubLoad, useAi } from '../../lib/agentHub';
import { intakeDots, laneCounts, LANES } from '../../lib/intakeBand';
import { aiOf, scoutChips } from '../../lib/cockpitControls';
import { devilOf } from '../../lib/agentRead';
import { LiveTank } from '../LiveTank';
import '../../styles/intakeBand.css';

const ACTIONS = [['arm', '⚡ ARM', 'owner priority: the agents take it the moment it is READY and passes every execution check'],
  ['track', '📌 TRACK', 'keep it on your list — judged every pass'], ['review', '🔎 REVIEW', 'send it through the normal agent review'],
  ['ignore', '✕ IGNORE', 'off your list']];

// 🛰 ONE INTAKE (owner, 2026-10-29: "agt cmd ctr should have one intake and that's the ALL intake, not the agents' intake — agents have to
// choose from the bigger intake only"). The tank IS the shared discovery snapshot the server hands the agents (`/familia/intake` = the same
// rows `_agents_tick` screens). The agents' own progress is drawn ON it: a coin they are contending / ready on / holding wears a ring, the
// funnel counts sit in the header, and tapping a coin gives the owner's orders (ARM · TRACK · REVIEW · IGNORE) beside CHART / TRADE.
const STAGE_WORD = { contending: 'CONTENDING', ready: 'READY', picked: 'PICKED' };
const GATE_WORD = { trade: ['TRADE', 'is-ok', 'a rule held on coins it was not learned from — picks are live'], hold: ['HOLD', 'is-bad', 'no rule holds on unseen coins — no picks'], wait: ['WAIT', 'is-wait', 'too few coins judged yet — no picks'] };
export function IntakeBand({ o, mint, onPick, call, isOwner, imp }) {
  const cands = (o?.kernel || {}).candidates || [];
  const held = useMemo(() => (o?.positions || []).map(p => p.mint), [o?.positions]);
  const band = (o?.policy || {}).band || {};
  const dots = useMemo(() => intakeDots(cands, held, band), [cands, held, band]);
  const n = laneCounts(dots);
  const marks = useMemo(() => new Map(dots.filter(x => x.stage !== 'in').map(x => [x.mint, x.stage === 'ready' && x.c?.pick ? 'edge' : x.stage])), [dots]);
  const picks = dots.filter(x => x.stage === 'ready' && x.c?.pick);
  const byMint = useMemo(() => new Map(dots.map(x => [x.mint, x])), [dots]);
  const [busy, setBusy] = useState(null);
  const ai = useAi(o?.ai);
  const act = async (a, m, sym) => {
    if (!m || busy) return;
    setBusy(a);
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ owner: { mint: m, action: a } }) }); await hubLoad(); toast.success(`$${sym || '…'}: ${a.toUpperCase()} — the agents read it on their next pass`); }
    catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };
  const m = (o?.kernel || {}).metrics || {};
  const extra = t => <AgentOrders d={byMint.get(t.mint)} t={t} ai={aiOf(ai?.notes, t.mint)?.advice} busy={busy} isOwner={isOwner} act={act} />;
  return <section className="ib" data-testid="intake-band">
    <header className="ib-head"><b>🛰 INTAKE</b><small>one tank · every feed · the agents pick only from here</small>
      {(imp || []).length ? <span className="ib-imp" data-testid="ib-imp" data-tip={`🎭 dropped before the agents read them — a launch wearing a real coin's ticker:\n${imp.slice(0, 8).map(x => `$${x.symbol}: ${x.why}`).join('\n')}`}>🎭 {imp.length} fake{imp.length === 1 ? '' : 's'} dropped</span> : null}
      <span className="ib-rate">{m.uniqueMintsPerMin != null ? <><b>+{m.uniqueMintsPerMin}</b>/min</> : null}</span>
      {o?.survival ? <span className="ib-surv" data-testid="ib-surv" data-tip="⏱ NSFA survival watch: of the last hour's coins, the share still alive 1, 5 and 15 min after the desk first saw them (never −50 %) · their typical move">
        {[['m1', '1M'], ['m5', '5M'], ['m15', '15M']].map(([k, l], i) => { const c = o.survival[k] || {}; return <i key={k} style={{ '--i': i }} className={c.pct == null ? 'is-wait' : c.pct >= 70 ? 'is-ok' : c.pct >= 45 ? 'is-mid' : 'is-bad'}>
          <small>{l}</small><b className="m-num">{c.pct == null ? '…' : `${c.pct}%`}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${(c.pct || 0) / 100})` }} /></u></i>; })}</span> : null}
      <ol className="ib-funnel" data-testid="ib-funnel" aria-label="What the agents did with the intake">{LANES.map(([k, l, tip]) => <li key={k} className={`is-${k}`} data-tip={`AGENTS · ${tip}`}><b className="m-num">{n[k]}</b><small>{l}</small></li>)}</ol></header>
    <PickStrip edge={o?.edge} picks={picks} isOwner={isOwner} call={call} onPick={d => onPick?.({ mint: d.mint, pair: d.c?.pair, symbol: d.sym })} />
    <LiveTank compact={false} title="ALL LEVELS" marks={marks} selected={mint} extra={extra} onChart={(pair, mm) => onPick?.({ mint: mm, pair: pair.pairAddress, symbol: pair.baseToken?.symbol })} />
  </section>;
}

// 🧪 A06 THE PICK (owner 2026-10-29: "sort through the intake to PICK a coin, not block coins"): a coin matching a rule that made money on
// coins it was NOT learned from, that survived its own 1 / 5-min watch and sits on its germ is READY on its own (trench_kernel.brain.edge_pick).
// The strip: the owner's switch, the proof gate, the proven rules as meters (typical move on unseen coins), the live picks one tap from the chart.
export function PickStrip({ edge, picks, isOwner, call, onPick }) {
  const [busy, setBusy] = useState(false);
  if (!edge) return null;
  const [gw, gcls, gtip] = GATE_WORD[edge.gate] || GATE_WORD.wait;
  const top = Math.max(1, ...(edge.rules || []).map(r => Number(r.med) || 0));
  const post = async (cfg, ok) => {
    if (!isOwner || busy) return;
    setBusy(true);
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ cfg }) }); await hubLoad(); toast.success(ok); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const flip = () => post({ edgePick: !edge.on }, edge.on ? '🧪 Picks off — the agents only take their own READY coins' : '🧪 Picks on — proven rules pick from the intake');
  const young = () => post({ pickYoung: !edge.young }, edge.young ? `🐣 Picks wait for your ${edge.minAgeMin}-min line again` : '🐣 Picks from 5 min — a pick that survived its watch may enter young, at half size');
  return <div className={`ib-pick${edge.on ? '' : ' is-off'}`} data-testid="ib-pick">
    <button type="button" className={`ib-pk-sw${edge.on ? ' is-on' : ''}`} role="switch" aria-checked={!!edge.on} disabled={!isOwner || busy} onClick={flip} data-testid="ib-pick-switch"
      data-tip={'🧪 PICKS: a coin matching a proven rule + its own 1 / 5-min survival + on its germ floor is READY on its own. Every wall, the Warden\'s sizing and your stops stay.' + (isOwner ? '' : ' (creator only)')}>
      <i aria-hidden="true" /><b>🧪 PICKS</b><small>{edge.on ? 'ON' : 'OFF'}</small></button>
    {edge.minAgeMin > 5 ? <button type="button" className={`ib-pk-sw is-young${edge.young ? ' is-on' : ''}`} role="switch" aria-checked={!!edge.young} disabled={!isOwner || busy} onClick={young} data-testid="ib-pick-young"
      data-tip={`🐣 PICKS FROM 5 MIN (your youngest-coin line is ${edge.minAgeMin} min). The audit, last 800 coins after a 3% round trip: rule-matched coins first seen under 15 min +5.1% typical, 53% up — seen at 15 min+ −8.2%, 24% up. On: a pick that survived its own 5-min watch may enter under your line at HALF size; every other wall stays. Off: your line stands for picks too.`}>
      <i aria-hidden="true" /><b>🐣 FROM 5 MIN</b><small>{edge.young ? 'ON' : 'OFF'}</small></button> : null}
    <span className={`ib-pk-gate ${gcls}`} data-tip={`🧪 proof gate: ${gtip} · ${edge.held} of ${edge.tested} rules held`}><small>GATE</small><b>{gw}</b><u className="m-num">{edge.held}/{edge.tested}</u></span>
    <ol className="ib-pk-rules" aria-label="Proven rules">{(edge.rules || []).slice(0, 3).map((r, i) => <li key={r.rule} style={{ '--i': i }} data-tip={`${r.rule}\n${Number(r.med) >= 0 ? '+' : ''}${r.med}% typical an hour later · ${r.up}% went up · on ${r.n} coins it was not learned from (after a 3% round trip)`}>
      <small>{r.rule.replace(/ \+ /g, ' · ')}</small><b className="m-num">{Number(r.med) >= 0 ? '+' : ''}{Number(r.med).toFixed(1)}%</b><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, (Number(r.med) || 0) / top)})` }} /></u></li>)}</ol>
    <span className="ib-pk-live" data-testid="ib-pick-live">{picks.length ? picks.slice(0, 4).map(d => <button key={d.mint} type="button" className="ib-pk-coin" onClick={() => onPick(d)} data-tip={d.c.pick.why}>
      <b>${d.sym}</b><small>{d.c.pick.rule}</small></button>) : <small className="ib-pk-none">{edge.on && edge.gate === 'trade' ? 'hunting — no coin matches a rule on its germ right now' : 'no picks'}</small>}</span>
  </div>;
}

// the agents' read + the owner's orders on a tapped coin (inside the tank's vitals popup)
function AgentOrders({ d, t, ai, busy, isOwner, act }) {
  const c = d?.c || {}; const dv = devilOf(c); const dvWhy = dv.first ? `${dv.word} — ${dv.first.evidence || dv.first.rule}` : null;
  const chips = scoutChips(ai?.scout);
  return <div className={`ib-orders is-${d?.stage || 'none'}`} data-testid="ib-orders">
    <p className="ib-stage">{d ? <><em className={`is-${d.stage}`}>{STAGE_WORD[d.stage] || 'IN THE DESK'}</em><small>agents · rank {Math.round(d.rank)}{c.trigger ? ` · Trigger ${c.trigger}` : ''}</small></>
      : <small>not on the agents' desk yet — they read it on a coming pass</small>}</p>
    {c.pick ? <p className="ib-pk-why" data-testid="ib-pick-why"><em>🧪 PICK</em><b>{c.pick.rule}</b><small>{Number(c.pick.med) >= 0 ? '+' : ''}{c.pick.med}% typical · {c.pick.n} unseen coins · {c.pick.entry}</small></p> : null}
    {dvWhy || c.kwhy || c.why ? <p className="ib-why">{dvWhy ? `⚖ ${dvWhy}` : `🧠 ${c.kwhy || c.why}`}</p> : null}
    {ai?.summary || chips.length ? <p className="ib-ai">{ai?.summary ? <span>🧠 {ai.summary}</span> : null}{chips.map(([k, l, cls]) => <i key={k} className={`avt-sc ${cls}`}>{l}</i>)}</p> : null}
    <div className="ib-acts">{ACTIONS.map(([a, l, tip]) => <button key={a} type="button" className={`m-btn ib-act is-${a}`} disabled={!isOwner || !!busy} aria-busy={busy === a} onClick={() => act(a, t.mint, t.sym)} data-tip={tip} data-testid={`ib-act-${a}`}>{l}</button>)}</div>
  </div>;
}

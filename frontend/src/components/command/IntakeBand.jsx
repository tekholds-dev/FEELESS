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
export function IntakeBand({ o, mint, onPick, call, isOwner, imp }) {
  const cands = (o?.kernel || {}).candidates || [];
  const held = useMemo(() => (o?.positions || []).map(p => p.mint), [o?.positions]);
  const band = (o?.policy || {}).band || {};
  const dots = useMemo(() => intakeDots(cands, held, band), [cands, held, band]);
  const n = laneCounts(dots);
  const marks = useMemo(() => new Map(dots.filter(x => x.stage !== 'in').map(x => [x.mint, x.stage])), [dots]);
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
    <LiveTank compact={false} title="ALL LEVELS" marks={marks} selected={mint} extra={extra} onChart={(pair, mm) => onPick?.({ mint: mm, pair: pair.pairAddress, symbol: pair.baseToken?.symbol })} />
  </section>;
}

// the agents' read + the owner's orders on a tapped coin (inside the tank's vitals popup)
function AgentOrders({ d, t, ai, busy, isOwner, act }) {
  const c = d?.c || {}; const dv = devilOf(c); const dvWhy = dv.first ? `${dv.word} — ${dv.first.evidence || dv.first.rule}` : null;
  const chips = scoutChips(ai?.scout);
  return <div className={`ib-orders is-${d?.stage || 'none'}`} data-testid="ib-orders">
    <p className="ib-stage">{d ? <><em className={`is-${d.stage}`}>{STAGE_WORD[d.stage] || 'IN THE DESK'}</em><small>agents · rank {Math.round(d.rank)}{c.trigger ? ` · Trigger ${c.trigger}` : ''}</small></>
      : <small>not on the agents' desk yet — they read it on a coming pass</small>}</p>
    {dvWhy || c.kwhy || c.why ? <p className="ib-why">{dvWhy ? `⚖ ${dvWhy}` : `🧠 ${c.kwhy || c.why}`}</p> : null}
    {ai?.summary || chips.length ? <p className="ib-ai">{ai?.summary ? <span>🧠 {ai.summary}</span> : null}{chips.map(([k, l, cls]) => <i key={k} className={`avt-sc ${cls}`}>{l}</i>)}</p> : null}
    <div className="ib-acts">{ACTIONS.map(([a, l, tip]) => <button key={a} type="button" className={`m-btn ib-act is-${a}`} disabled={!isOwner || !!busy} aria-busy={busy === a} onClick={() => act(a, t.mint, t.sym)} data-tip={tip} data-testid={`ib-act-${a}`}>{l}</button>)}</div>
  </div>;
}

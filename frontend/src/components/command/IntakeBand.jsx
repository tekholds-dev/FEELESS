import React, { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { hubLoad, useAi } from '../../lib/agentHub';
import { intakeDots, laneCounts, splashFacts, LANES } from '../../lib/intakeBand';
import { capX, aiOf, scoutChips } from '../../lib/cockpitControls';
import { devilOf } from '../../lib/agentRead';
import '../../styles/intakeBand.css';

const TICKS = [[1e3, '$1K'], [1e4, '$10K'], [1e5, '$100K'], [1e6, '$1M']];
const ACTIONS = [['arm', '⚡ ARM', 'owner priority: the agents take it the moment it is READY and passes every execution check'],
  ['track', '📌 TRACK', 'keep it on your list — judged every pass'], ['review', '🔎 REVIEW', 'send it through the normal agent review'],
  ['ignore', '✕ IGNORE', 'off your list']];

// 🛰 THE INTAKE BAND: every coin the intake brings in as a dot (across = live MC, up = how far the agents took it). New coins pop in,
// a promoted coin glides up its lane (transform only), READY breathes, PICKED wears a ring. Tap a dot → its vitals + one-tap orders.
export function IntakeBand({ o, mint, onPick, call, isOwner, imp }) {
  const cands = (o?.kernel || {}).candidates || [];
  const held = useMemo(() => (o?.positions || []).map(p => p.mint), [o?.positions]);
  const band = (o?.policy || {}).band || {};
  const dots = useMemo(() => intakeDots(cands, held, band), [cands, held, band]);
  const n = laneCounts(dots);
  const [sel, setSel] = useState(null); const [busy, setBusy] = useState(null);
  const ai = useAi(o?.ai);
  const host = useRef(null);
  useEffect(() => {
    if (!sel) return undefined;
    const k = e => { if (e.key === 'Escape') setSel(null); };
    const out = e => { if (host.current && !host.current.contains(e.target)) setSel(null); };
    window.addEventListener('keydown', k); window.addEventListener('pointerdown', out);
    return () => { window.removeEventListener('keydown', k); window.removeEventListener('pointerdown', out); };
  }, [sel]);
  const d = sel ? dots.find(x => x.mint === sel) : null;
  const act = async a => {
    if (!d || busy) return;
    setBusy(a);
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ owner: { mint: d.mint, action: a } }) }); await hubLoad(); toast.success(`$${d.sym || '…'}: ${a.toUpperCase()} — the agents read it on their next pass`); }
    catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };
  const lo = band.min > 0 ? capX(band.min) : 0; const hi = capX(band.max || 3e5) ?? 1;
  const m = (o?.kernel || {}).metrics || {};
  return <section className="ib" ref={host} data-testid="intake-band">
    <header className="ib-head" data-tip="everything the feeds bring in · across = live MC · up = how far the agents took it · tap a coin"><b>🛰 INTAKE</b><small>everything the feeds bring in · across = live MC · up = how far the agents took it · tap a coin</small>
      {(imp || []).length ? <span className="ib-imp" data-testid="ib-imp" data-tip={`🎭 dropped before the agents read them — a launch wearing a real coin's ticker:\n${imp.slice(0, 8).map(x => `$${x.symbol}: ${x.why}`).join('\n')}`}>🎭 {imp.length} fake{imp.length === 1 ? '' : 's'} dropped</span> : null}
      <span className="ib-rate">{m.uniqueMintsPerMin != null ? <><b>+{m.uniqueMintsPerMin}</b>/min</> : null}</span></header>
    <div className="ib-body">
      <div className="ib-field">
        <i className="ib-zone" style={{ left: `${lo * 100}%`, width: `${Math.max(0, (hi - lo) * 100)}%` }} />
        {LANES.map(([k, l], i) => <i key={k} className={`ib-lane is-${k}`} style={{ '--l': i }}><small>{l}</small></i>)}
        {TICKS.map(([v, l]) => <em key={l} className="ib-tick" style={{ left: `${capX(v) * 100}%` }}>{l}</em>)}
        {dots.map(x => <button key={x.mint} type="button" className={`ib-dot is-${x.stage} ${x.inside ? '' : 'is-out'} ${x.mint === mint ? 'is-on' : ''} ${x.mint === sel ? 'is-sel' : ''}`}
          style={{ left: `${x.x * 100}%`, '--l': x.lane }} onClick={() => setSel(s => (s === x.mint ? null : x.mint))}
          aria-label={`$${x.sym || x.mint.slice(0, 4)} ${x.stage}`} data-tip={`$${x.sym || '…'} · ${x.stage.toUpperCase()} · rank ${Math.round(x.rank)}`} data-testid={`ib-dot-${x.mint}`}><i /></button>)}
      </div>
      <ol className="ib-funnel" data-testid="ib-funnel">{LANES.slice().reverse().map(([k, l, tip]) => <li key={k} className={`is-${k}`} data-tip={tip}><b>{n[k]}</b><small>{l}</small></li>)}</ol>
    </div>
    {d ? <Splash d={d} ai={aiOf(ai?.notes, d.mint)?.advice} busy={busy} isOwner={isOwner} act={act} onPick={() => { onPick?.(d.mint); setSel(null); }} /> : null}
  </section>;
}

function Splash({ d, ai, busy, isOwner, act, onPick }) {
  const c = d.c || {}; const dv = devilOf(c); const dvWhy = dv.first ? `${dv.word} — ${dv.first.evidence || dv.first.rule}` : null;
  const facts = splashFacts(c); const chips = scoutChips(ai?.scout);
  return <div className={`ib-splash is-${d.stage}`} style={{ '--x': d.x }} role="dialog" aria-label={`$${d.sym} vitals`} data-testid="ib-splash">
    <p className="ib-sh"><b>${d.sym || d.mint.slice(0, 4)}</b><em className={`is-${d.stage}`}>{d.stage.toUpperCase()}</em><small>rank {Math.round(d.rank)}{c.trigger ? ` · Trigger ${c.trigger}` : ''}</small></p>
    <ul className="ib-facts">{facts.map(([k, v, cls]) => <li key={k} className={cls}><small>{k}</small><b>{v}</b></li>)}</ul>
    {dvWhy || c.kwhy || c.why ? <p className="ib-why">{dvWhy ? `⚖ ${dvWhy}` : `🧠 ${c.kwhy || c.why}`}</p> : null}
    {ai?.summary || chips.length ? <p className="ib-ai">{ai?.summary ? <span>🧠 {ai.summary}</span> : null}{chips.map(([k, l, cls]) => <i key={k} className={`avt-sc ${cls}`}>{l}</i>)}</p> : null}
    <div className="ib-acts">{ACTIONS.map(([a, l, tip]) => <button key={a} type="button" className={`m-btn ib-act is-${a}`} disabled={!isOwner || !!busy} aria-busy={busy === a} onClick={() => act(a)} data-tip={tip} data-testid={`ib-act-${a}`}>{l}</button>)}
      <button type="button" className="m-btn ib-act is-chart" onClick={onPick} data-testid="ib-act-chart">📈 CHART</button></div>
  </div>;
}

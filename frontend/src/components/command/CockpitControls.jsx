import React, { useState } from 'react';
import { toast } from 'sonner';
import { hubLoad } from '../../lib/agentHub';
import { CTRL_GROUPS, optWord, whoTone, WHO_WORD, bandTrack, hasVitals } from '../../lib/cockpitControls';
import { aiChip } from './AiProviders';
import '../../styles/agentControls.css';

// 🎛 OPERATOR CONTROLS, META (owner, 2026-10-12: "update controls to be meta"): the creator's own limits as grouped segment rows instead
// of loose selects — every option is the server's own list (`policy.controls`), every row says who decides it now (AGENTS / YOURS /
// YOUR BAND) and, under AGENTS CHOOSE, what the agents are really using right now. One tap = one POST /admin/agents {cfg}; the row shows
// the pending choice until the hub reloads. The MC band draws this pass's real candidates on a log track. Nothing here trades.

export function ControlRow({ c, pending, disabled, onPick }) {
  const val = pending !== undefined ? pending : c.value;
  return <div className={`acx-row ${whoTone(c.who)}`} data-testid={`ack-op-${c.key}`} data-value={String(c.value)}
    data-tip={`${c.means}${c.agentsNow && c.who === 'AGENTS CHOOSE' ? ` — right now: ${c.agentsNow}` : ''}`}>
    <span className="acx-lab"><small>{c.label}</small><i className={`acx-who ${whoTone(c.who)}`}>{WHO_WORD[c.who] || c.who}</i></span>
    <span className="m-seg acx-seg" role="radiogroup" aria-label={c.label} style={{ '--acx-min': `${Math.max(46, Math.max(...(c.options || ['']).map(v => optWord(c.key, v).length)) * 7 + 16)}px` }}>{(c.options || []).map(v => {
      const on = String(v) === String(val); const wait = pending !== undefined && on;
      return <button key={String(v)} type="button" role="radio" aria-checked={on} className={`${on ? 'active' : ''} ${wait ? 'is-pending' : ''}`} disabled={disabled}
        onClick={() => { if (String(v) !== String(c.value)) onPick(c.key, v); }} data-testid={`ack-op-${c.key}-${v}`}>{optWord(c.key, v)}</button>; })}</span>
    {c.agentsNow && c.who === 'AGENTS CHOOSE' ? <u className="acx-now">now · {c.agentsNow}</u> : null}
  </div>;
}

export function BandTrack({ band, cands }) {
  if (!band) return null;
  const t = bandTrack(band.min, band.max, cands);
  return <div className="acx-band" data-testid="acx-band" data-tip="Each dot is a coin the kernel read this pass, at its live market cap (log scale $1K → $1M). Green = READY · lit = inside your band.">
    <span className="acx-track"><b className="acx-zone" style={{ left: `${t.lo * 100}%`, width: `${Math.max(0, t.hi - t.lo) * 100}%` }} />
      {t.dots.map((d, i) => <i key={`${d.sym}-${i}`} className={`acx-dot ${d.inside ? 'is-in' : ''} ${d.ready ? 'is-ready' : ''}`} style={{ left: `${d.x * 100}%` }} />)}</span>
    <span className="acx-ticks" aria-hidden><small>$1K</small><small>$10K</small><small>$100K</small><small>$1M</small></span>
    <p className="acx-bandword"><b data-testid="acx-band-word">{band.word}</b><span>{t.inside} in band now</span><span className="m-pos">{t.ready} READY</span></p>
  </div>;
}

export function CockpitControls({ o, call, isOwner, ai, onAi }) {
  const pol = o?.policy || {}; const ctl = Object.fromEntries((pol.controls || []).map(c => [c.key, c]));
  const [pend, setPend] = useState({}); const busy = Object.keys(pend).length > 0;
  const save = async (cfg, key, val) => {
    if (busy) return;
    if (key) setPend({ [key]: val });
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ cfg }) }); await hubLoad(); toast.success('saved — the agents use it on the next tick'); }
    catch (e) { toast.error(e.message); } finally { setPend({}); }
  };
  const chip = aiChip(ai); const lr = ai?.learn || {};
  const vitN = Object.values(ai?.notes || {}).filter(n => Object.values(n || {}).some(x => hasVitals(x?.advice))).length;
  const cands = ((o?.kernel || {}).candidates || []);
  return <section className="ack-ops acx" data-testid="ack-ops">
    <header className="acx-head"><b>🎛 OPERATOR CONTROLS</b><small>your limits on the agents — one tap saves; the agents read them on the next tick</small>
      <span className="m-seg acx-auth" role="radiogroup" aria-label="Who decides">
        <button type="button" role="radio" aria-checked={!pol.manual} disabled={!isOwner || busy} className={!pol.manual ? 'active' : ''} onClick={() => pol.manual && save({ agentAuthority: 'agents' })} data-testid="ack-auth-agents">🤖 Agents inside limits</button>
        <button type="button" role="radio" aria-checked={!!pol.manual} disabled={!isOwner || busy} className={pol.manual ? 'active is-manual' : ''} onClick={() => !pol.manual && save({ agentAuthority: 'manual' })}
          data-tip="MANUAL: no agent fill, switch or read-bank — only hard safety exits and your own overrides act" data-testid="ack-auth-manual">✋ Manual</button></span>
      <button type="button" className={`ack-aichip ${chip.cls}`} onClick={onAi} data-tip={chip.tip} data-testid="ack-aichip"><b>AI</b>{chip.parts.map(([k, l, c]) => <span key={k} className={c}>{l}</span>)}</button></header>
    <div className="acx-grid">
      {CTRL_GROUPS.map(([g, title, blurb, keys]) => { const rows = keys.filter(k => ctl[k]); if (!rows.length) return null;
        return <div key={g} className={`acx-card is-${g}`} data-testid={`acx-${g}`}><p className="acx-ctitle"><b>{title}</b><small>{blurb}</small></p>
          {g === 'universe' ? <BandTrack band={pol.band} cands={cands} /> : null}
          {rows.map(k => <ControlRow key={k} c={ctl[k]} pending={pend[k]} disabled={!isOwner || busy} onPick={(kk, v) => save({ [kk]: v }, kk, v)} />)}</div>; })}
      <div className="acx-card is-model" data-testid="acx-model"><p className="acx-ctitle"><b>🧠 MODEL</b><small>the AI reads every READY coin's vitals first — it weighs only once its own record proves it</small></p>
        <ControlRow c={{ key: 'agentAiLearn', label: 'Learn from the model', who: lr.on === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: lr.on === false ? 'off' : 'on', options: ['on', 'off'],
          means: 'ON: a stance or vital PROVEN on the model\'s own judged record (20+ calls, clearly better / worse than its other calls) moves the ranking by up to 10%. OFF: asked, shown and judged — it weighs nothing. It never buys, sizes, blocks or sells.' }}
          pending={pend.agentAiLearn} disabled={!isOwner || busy} onPick={(k, v) => save({ agentAiLearn: v === 'on' }, k, v)} />
        <p className={`acx-state is-${String(lr.state || 'off').toLowerCase().replace(/\s+/g, '-')}`} data-testid="acx-model-state"><em>{lr.state || 'NO MODEL'}</em><span>{lr.why || 'start LM Studio or add a key under ⚙ providers'}</span></p>
        <p className="acx-cover"><span><small>ANSWERS</small><b>{ai?.totals?.answered ?? 0}</b></span><span><small>CACHED</small><b>{ai?.totals?.cached ?? 0}</b></span>
          <span><small>WITH VITALS</small><b data-testid="acx-vitals-n">{vitN}</b></span><span><small>JUDGED</small><b>{lr.all?.n ?? 0}</b></span></p>
        {ai?.slip ? <span className="ack-fixed" data-tip="Your buy rule (fixed in the keeper): the first try at this slippage, then ONE retry; a second slippage failure gives the seat to another coin. Sells keep their own steps — an exit must land." data-testid="ack-slip"><small>BUY SLIPPAGE</small><b>{ai.slip.firstPct}% → {ai.slip.retryPct}% × {ai.slip.retries} retry</b></span> : null}
        <button type="button" className="m-btn acx-all" onClick={() => window.dispatchEvent(new CustomEvent('feeless:agents-lens', { detail: 'limits' }))} data-testid="ack-all-limits">All limits →</button></div>
    </div>
  </section>;
}

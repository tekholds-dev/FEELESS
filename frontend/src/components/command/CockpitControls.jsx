import React, { useState } from 'react';
import { toast } from 'sonner';
import { hubLoad, useAi } from '../../lib/agentHub';
import { CTRL_GROUPS, optWord, whoTone, WHO_WORD, bandTrack, hasIntel, gateCounts, GATE_WORDS, regretRows, capitalRead, trailRead } from '../../lib/cockpitControls';
import { aiMetricsLine } from '../../lib/aiRead';
import { AiChipBtn } from './AiProviders';
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

// 🧠 the model card — its own AI-store subscriber, with the router's live counters (owner's spec: queue · active · calls/min · cache hit ·
// average latency · provider · deferred / skipped)
function ModelCard({ o, pend, disabled, onPick }) {
  const ai = useAi(o?.ai); const lr = ai?.learn || {};
  const intelN = Object.values(ai?.notes || {}).filter(n => Object.values(n || {}).some(x => hasIntel(x?.advice))).length;
  return <div className="acx-card is-model" data-testid="acx-model"><p className="acx-ctitle"><b>🧠 MODEL</b><small>vital intel only — narrative, creator, conflicts, risks; it weighs only once its own record proves it</small></p>
    <ControlRow c={{ key: 'agentAiLearn', label: 'Learn from the model', who: lr.on === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: lr.on === false ? 'off' : 'on', options: ['on', 'off'],
      means: 'ON: a stance or risk read PROVEN on the model\'s own judged record (20+ calls, clearly better / worse than its other calls) moves the ranking by up to 10%. OFF: asked, shown and judged — it weighs nothing. It never buys, sizes, blocks or sells.' }}
      pending={pend.agentAiLearn} disabled={disabled} onPick={onPick} />
    <p className={`acx-state is-${String(lr.state || 'off').toLowerCase().replace(/\s+/g, '-')}`} data-testid="acx-model-state"><em>{lr.state || 'NO MODEL'}</em><span>{lr.why || 'start LM Studio or add a key under ⚙ providers'}</span></p>
    {ai?.metrics ? <p className="acx-cover is-metrics" data-testid="acx-ai-metrics">{aiMetricsLine(ai.metrics).map(([l, v]) => <span key={l}><small>{l}</small><b>{v}</b></span>)}</p> : null}
    <p className="acx-cover"><span><small>COINS WITH INTEL</small><b data-testid="acx-intel-n">{intelN}</b></span><span><small>JUDGED</small><b>{lr.all?.n ?? 0}</b></span></p>
    {ai?.slip ? <span className="ack-fixed" data-tip="Your buy rule (fixed in the keeper): the first try at this slippage, then ONE retry; a second slippage failure gives the seat to another coin. Sells keep their own steps — an exit must land." data-testid="ack-slip"><small>BUY SLIPPAGE</small><b>{ai.slip.firstPct}% → {ai.slip.retryPct}% × {ai.slip.retries} retry</b></span> : null}
    <button type="button" className="m-btn acx-all" onClick={() => window.dispatchEvent(new CustomEvent('feeless:agents-lens', { detail: 'limits' }))} data-testid="ack-all-limits">All limits →</button></div>;
}

// 🛂 which limit refused the agents' last buys (the keeper's own words) — the knob to turn when a seat stays empty
function GateLine({ refused, armed }) {
  const g = gateCounts(refused);
  return <p className="acx-gate" data-testid="acx-gate">{g.total ? GATE_WORDS.filter(([k]) => g[k]).map(([k, l]) => <span key={k} className={`acx-gpill is-${k}`}><b>{g[k]}</b>{l}</span>)
    : <span className="acx-gpill is-ok">no refused buy lately</span>}
    {armed?.n ? <span className="acx-gpill is-armed" data-tip={(armed.syms || []).map(s => `$${s}`).join(' · ')}>🎯 <b>{armed.n}</b>armed in</span> : null}</p>;
}

// 😴 what each check COST: the coins it held back vs the coins taken, 30 min later — and the notch the agents moved it to (only where you left AGENTS)
const pct = v => (v == null ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
function RegretLine({ rg }) {
  const rows = regretRows(rg);
  if (!rows.length) return <p className="acx-regret is-empty" data-testid="acx-regret">😴 learning from the coins they skip — graded 30 min after each block</p>;
  return <ul className="acx-regret" data-testid="acx-regret">{rows.map(r => <li key={r.k} className={`is-${r.verdict}`}
    data-tip={`${r.n} coins this check held back did ${pct(r.med)} 30 min later vs ${pct(r.taken)} for the coins taken (${r.ran ?? 0}% ran +20%)${r.tuned ? ` · 🤖 ${r.tuned.why}` : ''}`}>
    <b>{r.label}</b><span>{r.n ? `${pct(r.med)} vs ${pct(r.taken)}` : '—'}</span><em>{r.tuned ? `🤖 → ${r.tuned.value === false ? 'OFF' : r.tuned.value}` : r.verdict === 'costly' ? 'COSTLY' : r.verdict === 'right' ? 'RIGHT' : r.verdict === 'even' ? 'EVEN' : `${r.n}/12`}</em></li>)}</ul>;
}

// 💰 CAPITAL DESK: the seat size the agents' own real record has earned — verdict · size · win vs loss bars · where the losses come from
function CapitalMeter({ cap }) {
  const c = capitalRead(cap);
  return <div className={`acx-cap is-${String(c.state).toLowerCase()}`} data-testid="acx-capital" data-state={c.state} data-tip={c.why || c.line}>
    <p className="acx-caphead"><b>{c.word}</b><span>{c.line}</span><em>{c.off ? 'OFF' : c.size ? `SEAT ×${c.size}` : 'SEATS AS BEFORE'}</em></p>
    {c.n ? <p className="acx-capbars" aria-label="Average win against average loss">
      <span className="is-win"><i style={{ transform: `scaleX(${c.win})` }} /><u>avg win {c.winPct > 0 ? '+' : ''}{c.winPct}%</u></span>
      <span className="is-loss"><i style={{ transform: `scaleX(${c.loss})` }} /><u>avg loss {c.lossPct}%</u></span>
      <small>payoff {c.payoff ?? '—'} · Kelly {c.kelly ?? '—'}</small></p> : null}
    {c.brake ? <p className="acx-capbrake" data-testid="acx-brake">🧯 BRAKE · {c.brake.downPct}% off the 24h high — smallest seats until it climbs back</p> : null}
    {c.doors?.length ? <p className="acx-capdoors" data-testid="acx-doors">{c.doors.map(d => <span key={d.k} className={`is-${String(d.state).toLowerCase()}`}
      data-tip={`${d.label} door: ${d.n} real exits, ${d.won}% won, ${d.exp > 0 ? '+' : ''}${d.exp}% a bet — each door is sized by its own record once it has 12 exits`}>
      <b>{d.label}</b><u>{d.won}% · {d.exp > 0 ? '+' : ''}{d.exp}%</u><em>{d.size ? `×${d.size}` : `${d.n}/12`}</em></span>)}</p> : null}
    {c.facts.length ? <p className="acx-capfacts">{c.facts.map(f => <span key={f}>🩸 {f}</span>)}</p> : null}
  </div>;
}

// 👁 TRAIL LAB: Reaper's trail replayed on the whole move (30 min past each sale) — live vs best, the shadow test, the model's ask
function TrailLab({ trail }) {
  const t = trailRead(trail);
  return <div className={`acx-trail ${t.pays ? 'is-pays' : ''}`} data-testid="acx-trail" data-tip={trail?.words || t.line}>
    <p className="acx-caphead"><b>👁 TRAIL LAB</b><span>{t.line}</span><em>{t.n ? `${t.n} MOVES` : 'WATCHING'}</em></p>
    {t.n && t.n < t.need ? <p className="acx-trailbar"><i style={{ transform: `scaleX(${t.fill})` }} /></p> : null}
    {t.live ? <p className="acx-trailrows"><span><small>LIVE</small>{t.live.word}<b>{t.live.avg > 0 ? '+' : ''}{t.live.avg}%</b></span>
      {t.best ? <span className="is-best"><small>BEST</small>{t.best.word}<b>{t.best.avg > 0 ? '+' : ''}{t.best.avg}%</b></span> : null}</p> : null}
    {t.shadow ? <p className="acx-capfacts"><span>{t.shadow}</span></p> : null}
    {t.asked && !t.shadow ? <p className="acx-capfacts"><span>{t.asked}</span></p> : null}
  </div>;
}

export function CockpitControls({ o, call, isOwner, onAi }) {
  const pol = o?.policy || {}; const ctl = Object.fromEntries((pol.controls || []).map(c => [c.key, c]));
  const [pend, setPend] = useState({}); const busy = Object.keys(pend).length > 0;
  const save = async (cfg, key, val) => {
    if (busy) return;
    if (key) setPend({ [key]: val });
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ cfg }) }); await hubLoad(); toast.success('saved — the agents use it on the next tick'); }
    catch (e) { toast.error(e.message); } finally { setPend({}); }
  };
  const cands = ((o?.kernel || {}).candidates || []);
  return <section className="ack-ops acx" data-testid="ack-ops">
    <header className="acx-head"><b>🎛 OPERATOR CONTROLS</b><small>your limits on the agents — one tap saves; the agents read them on the next tick</small>
      <span className="m-seg acx-auth" role="radiogroup" aria-label="Who decides">
        <button type="button" role="radio" aria-checked={!pol.manual} disabled={!isOwner || busy} className={!pol.manual ? 'active' : ''} onClick={() => pol.manual && save({ agentAuthority: 'agents' })} data-testid="ack-auth-agents">🤖 Agents inside limits</button>
        <button type="button" role="radio" aria-checked={!!pol.manual} disabled={!isOwner || busy} className={pol.manual ? 'active is-manual' : ''} onClick={() => !pol.manual && save({ agentAuthority: 'manual' })}
          data-tip="MANUAL: no agent fill, switch or read-bank — only hard safety exits and your own overrides act" data-testid="ack-auth-manual">✋ Manual</button></span>
      <AiChipBtn o={o} onClick={onAi} /></header>
    <div className="acx-grid">
      {CTRL_GROUPS.map(([g, title, blurb, keys]) => { const rows = keys.filter(k => ctl[k]); if (!rows.length) return null;
        return <div key={g} className={`acx-card is-${g}`} data-testid={`acx-${g}`}><p className="acx-ctitle"><b>{title}</b><small>{blurb}</small></p>
          {g === 'universe' ? <BandTrack band={pol.band} cands={cands} /> : null}
          {g === 'exits' ? <TrailLab trail={o?.trail} /> : null}
          {g === 'seats' ? <CapitalMeter cap={o?.capital} /> : null}
          {g === 'seats' ? <ControlRow c={{ key: 'agentCapital', label: '💰 Size by the record', who: o?.capital?.on === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: o?.capital?.on === false ? 'off' : 'on', options: ['on', 'off'],
            means: 'ON: a seat is sized by the agents\' own last 30 REAL exits — smallest seats (×0.25) while the average bet loses, ×0.5 while the edge is thin, half-Kelly (up to the full seat) once 20+ exits prove it wins. It can never give more than the card\'s own seat. OFF = seats as before; the record is still shown and taught.' }}
            pending={pend.agentCapital} disabled={!isOwner || busy} onPick={(kk, v) => save({ agentCapital: v === 'on' }, kk, v)} /> : null}
          {g === 'gate' ? <GateLine refused={o?.seat?.refused} armed={o?.armed} /> : null}
          {g === 'gate' ? <RegretLine rg={o?.regret} /> : null}
          {g === 'gate' ? <ControlRow c={{ key: 'chartWait', label: '🎯 Chart says go', who: pol.chartGo === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: pol.chartGo === false ? 'off' : 'on', options: ['on', 'off'],
            means: 'ON: a real seat needs the chart\'s own ENTER NOW (real card, 107 agent trades: ENTER NOW +14% typical, 70% won; every WAIT / SKIP chart −3…−29%). No chart yet = half a seat. OFF = the old open trenching. The regret ledger grades the coins it held back and may switch it off.' }}
            pending={pend.chartWait} disabled={!isOwner || busy} onPick={(kk, v) => save({ chartWait: v === 'on' }, kk, v)} /> : null}
          {rows.map(k => <ControlRow key={k} c={ctl[k]} pending={pend[k]} disabled={!isOwner || busy} onPick={(kk, v) => save({ [kk]: v }, kk, v)} />)}</div>; })}
      <ModelCard o={o} pend={pend} disabled={!isOwner || busy} onPick={(k, v) => save({ agentAiLearn: v === 'on' }, k, v)} />
    </div>
  </section>;
}

import React, { useEffect, useState } from 'react';
import { useRemembered } from '../../lib/remember';
import { toast } from 'sonner';
import { hubLoad, useAi } from '../../lib/agentHub';
import { CTRL_GROUPS, optWord, whoTone, WHO_WORD, bandTrack, hasIntel, gateCounts, GATE_WORDS, regretRows, capitalRead, trailRead, benchWord, twinRead } from '../../lib/cockpitControls';
import { aiMetricsLine } from '../../lib/aiRead';
import { AiChipBtn } from './AiProviders';
import '../../styles/agentControls.css';

// 🎛 OPERATOR CONTROLS, META (owner, 2026-10-12: "update controls to be meta"): the creator's own limits as grouped segment rows instead
// of loose selects — every option is the server's own list (`policy.controls`), every row says who decides it now (AGENTS / YOURS /
// YOUR BAND) and, under AGENTS CHOOSE, what the agents are really using right now. One tap = one POST /admin/agents {cfg}; the row shows
// the pending choice until the hub reloads. The MC band draws this pass's real candidates on a log track. Nothing here trades.

export function ControlRow({ c, pending, disabled, onPick, check }) {
  const val = pending !== undefined ? pending : c.value;
  const ok = check !== undefined ? String(check) === String(c.value) : null;
  return <div className={`acx-row ${whoTone(c.who)}`} data-testid={`ack-op-${c.key}`} data-value={String(c.value)}
    data-tip={`${c.means}${c.agentsNow && c.who === 'AGENTS CHOOSE' ? ` — right now: ${c.agentsNow}` : ''}`}>
    <span className="acx-lab"><small>{c.label}</small><i className={`acx-who ${whoTone(c.who)}`}>{WHO_WORD[c.who] || c.who}</i></span>
    <span className="m-seg acx-seg" role="radiogroup" aria-label={c.label} style={{ '--acx-min': `${Math.max(46, Math.max(...(c.options || ['']).map(v => optWord(c.key, v).length)) * 7 + 16)}px` }}>{(c.options || []).map(v => {
      const on = String(v) === String(val); const wait = pending !== undefined && on;
      return <button key={String(v)} type="button" role="radio" aria-checked={on} className={`${on ? 'active' : ''} ${wait ? 'is-pending' : ''}`} disabled={disabled}
        onClick={() => { if (String(v) !== String(c.value)) onPick(c.key, v); }} data-testid={`ack-op-${c.key}-${v}`}>{optWord(c.key, v)}</button>; })}</span>
    {c.agentsNow && c.who === 'AGENTS CHOOSE' ? <u className="acx-now">now · {c.agentsNow}</u> : null}
    {ok === true ? <em className="acx-ok" data-testid={`ack-op-${c.key}-ok`}>✓ IN FORCE</em> : ok === false ? <em className="acx-bad" data-testid={`ack-op-${c.key}-bad`}>⚠ NOT APPLIED · server kept {optWord(c.key, c.value)}</em> : null}
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
// ☠ the exit read's own record: per word graded / needed, its typical 15-min move, LIVE once proven (else shadow) + the newest reads
export function exitLine(x) {
  if (!x?.rec) return null;
  return Object.entries(x.rec).map(([w, [n, med, ok]]) => `${w} ${n}/${x.min}${n ? ` · ${med > 0 ? '+' : ''}${med}% in 15m` : ''} · ${ok && x.on ? '✅ LIVE' : 'shadow'}`).join('  ·  ');
}
// 🤝 each model's own exit record (both read every held seat; a split never moves Reaper)
const MODEL_NAME = { lan: '🖥 GEMMA', local: '💻 QWEN', chart: '🪜 CHART' };
export function modelsLine(x) {
  return Object.entries(x?.models || {}).map(([p, rec]) => `${MODEL_NAME[p] || p}: ` + Object.entries(rec).filter(([, [n]]) => n).map(([w, [n, med]]) => `${w} ${n} · ${med > 0 ? '+' : ''}${med}%`).join(' · ')).join('   ');
}
function ExitLine({ x }) {
  const line = exitLine(x);
  if (!line) return null;
  const ml = modelsLine(x);
  return <p className="acx-cover is-exit" data-testid="acx-exit-read"><span><small>EXIT READ</small><b>{line}</b>{ml ? <small data-testid="acx-exit-models">{ml}</small> : null}</span>
    {(x.reads || []).map(([sym, w, ago]) => <span key={`${sym}${ago}`}><small>${sym || '?'} · {ago}s ago</small><b>{w || '—'}</b></span>)}</p>;
}

function ModelCard({ o, pend, disabled, onPick, checks = {}, hidden }) {
  const ai = useAi(o?.ai); const lr = ai?.learn || {};
  const intelN = Object.values(ai?.notes || {}).filter(n => Object.values(n || {}).some(x => hasIntel(x?.advice))).length;
  return <div className="acx-card is-model" data-testid="acx-model" hidden={hidden}><p className="acx-ctitle"><b>🧠 MODEL</b><small>vital intel only — narrative, creator, conflicts, risks; it weighs only once its own record proves it</small></p>
    <ControlRow c={{ key: 'agentAiLearn', label: 'Learn from the model', who: lr.on === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: lr.on === false ? 'off' : 'on', options: ['on', 'off'],
      means: 'ON: a stance or risk read PROVEN on the model\'s own judged record (20+ calls, clearly better / worse than its other calls) moves the ranking by up to 10%. OFF: asked, shown and judged — it weighs nothing. It never buys, sizes, blocks or sells.' }}
      pending={pend.agentAiLearn} check={checks.agentAiLearn} disabled={disabled} onPick={onPick} />
    <ControlRow c={{ key: 'agentAiGate', label: '🛂 Read before a seat', who: (o?.policy || {}).aiGate === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: (o?.policy || {}).aiGate === false ? 'off' : 'on', options: ['on', 'off'],
      means: 'ON: the model reads every coin BEFORE it takes a real seat (cloud, ≤ 7s). A strong, specific CAUTION holds that coin back this tick; silence or a slow answer never does. It can only make the agents buy less. The regret ledger grades the coins it held back and switches the wait off if they keep beating the ones taken.' }}
      pending={pend.agentAiGate} check={checks.agentAiGate} disabled={disabled} onPick={onPick} />
    <ControlRow c={{ key: 'agentAiExit', label: '☠ Exit read for Reaper', who: (o?.policy || {}).aiExit === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: (o?.policy || {}).aiExit === false ? 'off' : 'on', options: ['on', 'off'],
      means: 'ON: the model reads every coin the agents HOLD about once a minute — RIDE (still being bought) or TIGHTEN (fading). Each read is graded 15 min later on what the coin did. A word moves Reaper only once its own record proves it (20+ graded, typical move 2%+ the right way): a proven RIDE gives a green seat the wide ride trail, a proven TIGHTEN banks a green seat sooner. Reaper never waits on it; stops and rug exits never change.' }}
      pending={pend.agentAiExit} check={checks.agentAiExit} disabled={disabled} onPick={onPick} />
    <ExitLine x={ai?.exit} />
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
    {c.rug ? <p className="acx-capbrake" data-testid="acx-rug">{c.rug}</p> : null}
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
    {benchWord(trail?.bench) ? <p className="acx-capfacts" data-testid="acx-bench" data-tip="Each soft exit is graded on what the coin did 30 min after our sale. A rule whose sales typically lost 3+ pts to holding (30+ exits) is benched: it sells nothing. Stops, rug / drain and the −45% line never are."><span>{benchWord(trail.bench)}</span></p> : null}
    {t.asked && !t.shadow ? <p className="acx-capfacts"><span>{t.asked}</span></p> : null}
    <TwinRow tw={trail?.twin} />
  </div>;
}
// 💰 SCALE-OUT TWIN: the real exits vs their paper twin (the scale-out's share sold at the take line, the rest on the trail)
function TwinRow({ tw }) {
  const w = twinRead(tw);
  return <div className={`acx-twin ${w.n ? (w.up ? 'is-up' : 'is-dn') : 'is-none'}`} data-testid="acx-twin" data-tip="coins that reached +10% only — flatters any take rule; a rug after the take counts −100% on the rest">
    <p className="acx-twinhead"><b>💰 SCALE-OUT TWIN</b><span>{w.line}</span>{w.n ? <em className={w.pays ? 'is-pays' : ''} data-testid="acx-twin-word">{w.word}</em> : null}</p>
    {w.n ? <><p className="acx-twinbar"><small>TWIN</small><span><i className={w.twin.neg ? 'is-neg' : 'is-twin'} style={{ transform: `scaleX(${w.twin.fill.toFixed(3)})` }} /></span><b>{w.twin.avg}</b><u>med {w.twin.med}</u></p>
      <p className="acx-twinbar"><small>REAL</small><span><i className={w.real.neg ? 'is-neg' : ''} style={{ transform: `scaleX(${w.real.fill.toFixed(3)})` }} /></span><b>{w.real.avg}</b><u>med {w.real.med}</u></p>
      <p className="acx-twinwl"><span className="m-pos">▲ {w.better} better</span><span className="m-neg">▼ {w.worse} worse</span></p></> : null}
  </div>;
}

// one rail button's summary: the group's first values as short words + how many of its rows are yours
export function railSum(keys, ctl) {
  const rows = keys.filter(k => ctl[k]);
  return { n: rows.length, mine: rows.filter(k => ctl[k].who === 'CREATOR OVERRIDE' || ctl[k].who === 'YOUR BAND').length, words: rows.slice(0, 2).map(k => optWord(k, ctl[k].value)) };
}

// 🎛 OPERATOR CONTROLS v2 (owner, 2026-10-16: "limit/configs sections need a ui/layout redo and confirmation all configs work"): a rail of
// sections (each with its live values + how many are yours) and ONE pane — controls on the left, the live reads that judge them on the right.
// Every pane stays mounted (hidden) so a tap never re-mounts anything. After a save the hub reloads and each tapped row says ✓ IN FORCE
// (the server's own value now equals your pick) or ⚠ NOT APPLIED (the server kept another value) — the confirmation is the server's word.
export function CockpitControls({ o, call, isOwner, onAi }) {
  const pol = o?.policy || {}; const ctl = Object.fromEntries((pol.controls || []).map(c => [c.key, c]));
  const [pend, setPend] = useState({}); const busy = Object.keys(pend).length > 0;
  const [checks, setChecks] = useState({});
  const [tab, setTab] = useRemembered('feeless.acx.tab', 'universe');
  useEffect(() => { if (!Object.keys(checks).length) return undefined; const t = setTimeout(() => setChecks({}), 9000); return () => clearTimeout(t); }, [checks]);
  const save = async (cfg, key, val) => {
    if (busy) return;
    if (key) setPend({ [key]: val });
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ cfg }) }); await hubLoad(); if (key) setChecks({ [key]: val }); toast.success('saved — the agents use it on the next tick'); }
    catch (e) { toast.error(e.message); } finally { setPend({}); }
  };
  const cands = ((o?.kernel || {}).candidates || []);
  const groups = CTRL_GROUPS.filter(([, , , keys]) => keys.some(k => ctl[k]));
  const cur = tab === 'model' || groups.some(([g]) => g === tab) ? tab : (groups[0] || ['model'])[0];
  const row = (c, onPick) => <ControlRow key={c.key} c={c} pending={pend[c.key]} check={checks[c.key]} disabled={!isOwner || busy} onPick={onPick} />;
  const flag = (key, label, on, means) => row({ key, label, who: on === false ? 'CREATOR OVERRIDE' : 'AGENTS CHOOSE', value: on === false ? 'off' : 'on', options: ['on', 'off'], means }, (kk, v) => save({ [kk]: v === 'on' }, kk, v));
  return <section className="ack-ops acx" data-testid="ack-ops">
    <header className="acx-head"><b>🎛 OPERATOR CONTROLS</b><small>your limits on the agents — one tap saves, the row confirms it is in force</small>
      <span className="m-seg acx-auth" role="radiogroup" aria-label="Who decides">
        <button type="button" role="radio" aria-checked={!pol.manual} disabled={!isOwner || busy} className={!pol.manual ? 'active' : ''} onClick={() => pol.manual && save({ agentAuthority: 'agents' })} data-testid="ack-auth-agents">🤖 Agents inside limits</button>
        <button type="button" role="radio" aria-checked={!!pol.manual} disabled={!isOwner || busy} className={pol.manual ? 'active is-manual' : ''} onClick={() => !pol.manual && save({ agentAuthority: 'manual' })}
          data-tip="MANUAL: no agent fill, switch or read-bank — only hard safety exits and your own overrides act" data-testid="ack-auth-manual">✋ Manual</button></span>
      <AiChipBtn o={o} onClick={onAi} /></header>
    <div className="acx-shell">
      <nav className="acx-rail" aria-label="Control sections">
        {groups.map(([g, title, , keys]) => { const r = railSum(keys, ctl);
          return <button key={g} type="button" className={`acx-tab is-${g} ${cur === g ? 'active' : ''}`} aria-pressed={cur === g} onClick={() => setTab(g)} data-testid={`acx-tab-${g}`}>
            <b>{title}</b><span>{r.words.join(' · ')}</span>{r.mine ? <em data-tip="rows set by you">{r.mine} YOURS</em> : null}</button>; })}
        <button type="button" className={`acx-tab is-model ${cur === 'model' ? 'active' : ''}`} aria-pressed={cur === 'model'} onClick={() => setTab('model')} data-testid="acx-tab-model">
          <b>🧠 MODEL</b><span>{(o?.ai?.learn || {}).state || 'intel only'}</span></button>
      </nav>
      <div className="acx-pane">
        {groups.map(([g, title, blurb, keys]) => { const rows = keys.filter(k => ctl[k]);
          const live = [g === 'universe' ? <BandTrack key="b" band={pol.band} cands={cands} /> : null,
            g === 'volume' ? <p key="v" className="acx-vol" data-testid="acx-vol-live"><b>🔥 {o?.universe?.trendingN ?? '—'}</b> on Pump trending now · <b>{o?.universe?.inLane ?? '—'}</b> coins in your lane this pass</p> : null,
            g === 'exits' ? <TrailLab key="t" trail={o?.trail} /> : null,
            g === 'seats' ? <CapitalMeter key="c" cap={o?.capital} /> : null,
            g === 'gate' ? <GateLine key="g" refused={o?.seat?.refused} armed={o?.armed} /> : null,
            g === 'gate' ? <RegretLine key="r" rg={o?.regret} /> : null].filter(Boolean);
          return <div key={g} className={`acx-card is-${g}`} data-testid={`acx-${g}`} hidden={cur !== g}><p className="acx-ctitle"><b>{title}</b><small>{blurb}</small></p>
            <div className={`acx-body ${live.length ? 'has-live' : ''}`}><div className="acx-rows">
              {g === 'seats' ? flag('agentCapital', '💰 Size by the record', o?.capital?.on, 'ON: a seat is sized by the agents\' own last 30 REAL exits — smallest seats (×0.25) while the average bet loses, ×0.5 while the edge is thin, half-Kelly (up to the full seat) once 20+ exits prove it wins. It can never give more than the card\'s own seat. OFF = seats as before; the record is still shown and taught.') : null}
              {g === 'seats' ? flag('agentValve', '🪫 Patience valve', o?.policy?.valve, `ON: a seat empty 10+ min with nothing READY or armed takes ONE coin the chart only asked to wait for confirmation, at a quarter seat, once per 15 min — it closes itself when its own real record loses (${o?.valve?.record?.n ?? 0} valve trades so far${o?.valve?.record?.med != null ? `, typical ${o.valve.record.med}%` : ''}). OFF = empty seats wait for READY / armed coins only.`) : null}
              {g === 'gate' ? flag('chartWait', '🎯 Chart says go', pol.chartGo, 'ON: a real seat needs the chart\'s own ENTER NOW (real card, 107 agent trades: ENTER NOW +14% typical, 70% won; every WAIT / SKIP chart −3…−29%). No chart yet = half a seat. OFF = the old open trenching. The regret ledger grades the coins it held back and may switch it off.') : null}
              {rows.map(k => row(ctl[k], (kk, v) => save({ [kk]: v }, kk, v)))}</div>
              {live.length ? <aside className="acx-live"><small className="acx-livehd">LIVE READ</small>{live}</aside> : null}</div></div>; })}
        <ModelCard o={o} pend={pend} checks={checks} hidden={cur !== 'model'} disabled={!isOwner || busy} onPick={(k, v) => save({ [k]: v === 'on' }, k, v)} />
      </div>
    </div>
  </section>;
}

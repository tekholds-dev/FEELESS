import React, { useEffect, useRef, useState } from 'react';
import { tiny } from '../../lib/num';
import '../../styles/officeBoard.css';

// 🏢 THE OFFICE (HQ › Agents › 🏢 Office): the ten desks of the real-money chain as DATA — the mission from the real card's own numbers,
// the current candidate moving through the line, one live card per agent (state, record, latency) and, on a tap, everything that
// agent is: ideology, ethics, immutable rules, tunables with their bounds, this pass's inputs and output, its record and the code
// that runs it. Nothing here computes a number of its own: it renders the one payload `backend/office.py` builds each pass.

export const STAGE_CLS = { WAITING: 'is-wait', WORKING: 'is-work', PASS: 'is-pass', OBJECT: 'is-obj', VETO: 'is-veto', DONE: 'is-done', ERROR: 'is-err', STALE: 'is-stale' };
export const STATUS_CLS = { alive: 'is-alive', probation: 'is-prob', demoted: 'is-dem', retired: 'is-ret' };
export const REAP_CLS = { HOLD: 'is-hold', PROTECT: 'is-prot', TAKE: 'is-take', 'EXIT INVALIDATED': 'is-exit' };
export const HEALTH_CLS = { HEALTHY: 'is-pass', DEGRADED: 'is-obj', BAD: 'is-veto' };

export const usd = v => (v == null || Number.isNaN(Number(v)) ? '—' : `$${Number(v).toFixed(2)}`);
export const sgn = (v, d = 1, unit = '%') => (v == null || Number.isNaN(Number(v)) ? '—' : `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(d)}${unit}`);
export const ago = (at, now = Date.now() / 1000) => { if (!at) return '—'; const s = Math.max(0, Math.round(now - at)); return s < 90 ? `${s}s ago` : s < 5400 ? `${Math.round(s / 60)}m ago` : `${(s / 3600).toFixed(1)}h ago`; };
export const clock = s => { const v = Math.max(0, Math.round(s || 0)); return `${Math.floor(v / 60)}m ${String(v % 60).padStart(2, '0')}s`; };
export const ms = v => (v == null ? '—' : v < 10 ? `${Number(v).toFixed(2)} ms` : `${Math.round(v)} ms`);
// what the last real action came to, in the ledger's own word — "sent" is never shown as "filled"
export const actionResult = r => { const s = r?.state;
  if (s === 'confirmed') return ['is-pass', `CONFIRMED on-chain${r.delta != null ? ` · ${sgn(r.delta, 2)} vs mid` : ''}${r.realPct != null ? ` · ${sgn(r.realPct)} real` : ''}`];
  if (s === 'failed') return ['is-veto', `FAILED — ${r.err || 'no reason on the ledger'}`];
  if (s === 'refused') return ['is-obj', `REFUSED by the keeper — ${r.err || ''}`];
  if (s === 'vetoed') return ['is-veto', 'VETOED by the Warden — nothing was sent'];
  return ['is-wait', 'NOT CONFIRMED YET — no filled row on the ledger']; };
export const nextDuty = (m, now = Date.now() / 1000) => (!m?.control ? null : m.dutyAt ? Math.max(0, m.dutyAt + (m.dutyEvery || 600) - now) : 0);

const Tag = ({ cls, children, tip }) => <i className={`ofb-tag ${cls || ''}`} data-tip={tip}>{children}</i>;

// any value the backend sent, laid out — never re-shaped, so what is on screen is what the agent held
// (a plain function that calls itself: a component rendering itself in JSX overflows the dev server's babel plugin)
export function dump(v, depth = 0) {
  if (v == null || v === '') return <span className="ofb-nil">—</span>;
  if (typeof v === 'boolean') return <span className={v ? 'ofb-yes' : 'ofb-no'}>{v ? 'yes' : 'no'}</span>;
  if (typeof v !== 'object') return <span className="ofb-val">{typeof v === 'number' && !Number.isInteger(v) ? Number(v.toFixed(4)) : String(v)}</span>;
  if (Array.isArray(v)) { if (!v.length) return <span className="ofb-nil">none</span>;
    if (v.every(x => x == null || typeof x !== 'object')) return <span className="ofb-val">{v.map(x => (x == null ? '—' : String(x))).join(' · ')}</span>;
    return <ul className="ofb-list">{v.slice(0, 12).map((x, i) => <li key={i}>{dump(x, depth + 1)}</li>)}</ul>; }
  if (depth >= 3) return <span className="ofb-val">{JSON.stringify(v)}</span>;
  return <dl className="ofb-kv">{Object.entries(v).map(([k, x]) => <React.Fragment key={k}><dt>{k}</dt><dd>{dump(x, depth + 1)}</dd></React.Fragment>)}</dl>;
}
const Dump = ({ v }) => dump(v);

export function OfficeMission({ m, bare }) {
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(t); }, []);
  if (!m) return <div className="ofb-mission is-cold" data-testid="ofb-mission"><b>💵 REAL MONEY MISSION</b><span className="ofb-nil">waiting for the agents' first pass — nothing is shown until the real card's own numbers arrive</span></div>;
  const left = nextDuty(m); const la = m.lastAction; const [rc, rt] = actionResult(la?.result); const be = m.toBreakeven;
  return <div className={`ofb-mission ${m.locked ? 'is-locked' : 'is-clear'}`} data-testid="ofb-mission">
    {bare ? null : <b data-tip="Every number here is the real Fuse card's own: its server value and what you put in. The page computes nothing.">💵 REAL MONEY MISSION</b>}
    <div className="ofb-mgrid">
      <span data-testid="ofb-putin"><small>PUT IN</small><em>{usd(m.putIn)}</em></span>
      <span data-testid="ofb-value"><small>CARD VALUE NOW</small><em>{usd(m.value)}</em></span>
      <span data-testid="ofb-be"><small>TO BREAKEVEN</small><em className={be == null ? '' : be >= 0 ? 'ofb-up' : 'ofb-dn'}>{be == null ? '—' : `${be >= 0 ? '+' : '−'}$${Math.abs(be).toFixed(2)}`}</em>{m.needX && m.locked ? <u>needs {m.needX}×</u> : null}</span>
      <span data-testid="ofb-stage"><small>STAGE</small><em>{m.stage} MIN</em></span>
      <span data-testid="ofb-lock" data-tip={m.lockRule}><small>BREAKEVEN LOCK</small><em className={m.locked ? 'ofb-warn' : 'ofb-up'}>{m.locked ? '🔒 LOCKED' : m.lock === 'CLEARED' ? '🔓 CLEARED' : '— UNKNOWN'}</em></span>
      <span data-testid="ofb-lives"><small>TEAM LIVES</small><em className={m.lives != null && m.lives <= 3 ? 'ofb-dn' : ''}>{m.lives ?? '—'} / {m.livesOf}</em></span>
      <span data-testid="ofb-duty"><small>NEXT DUTY</small><em>{left == null ? 'control off' : left <= 0 ? 'due now' : clock(left)}</em></span>
    </div>
    <p className="ofb-last" data-testid="ofb-last"><small>LAST REAL ACTION</small>{la ? <><span>{la.move?.toUpperCase()} ${la.sym}{la.usd != null ? ` · ${usd(la.usd)}` : ''} · {ago(la.at)}</span><Tag cls={rc}>{rt}</Tag><span className="ofb-why">{la.why}</span></> : <span className="ofb-nil">none since the service started</span>}</p>
    <p className="ofb-prio">{(m.priority || []).map((p, i) => <React.Fragment key={p}>{i ? <i aria-hidden>→</i> : null}<span>{p}</span></React.Fragment>)}</p>
  </div>;
}

export function OfficePipeline({ pipe, cur, agents, onPick, sel }) {
  const icon = Object.fromEntries((agents || []).map(a => [a.key, [a.icon, a.name]]));
  return <div className="ofb-pipe" data-testid="ofb-pipe">
    <div className="ofb-phead"><b>🧵 THE LINE · the current candidate, desk by desk</b>
      {cur ? <span className="ofb-cand" data-testid="ofb-cand">${cur.symbol} <small>lean {sgn(cur.lean, 1, '')} · {cur.cleared ? <Tag cls="is-pass">CLEARED</Tag> : <Tag cls="is-obj">BLOCKED</Tag>}{cur.go ? <Tag cls="is-pass">GO</Tag> : null}</small></span> : <span className="ofb-nil">no candidate this pass</span>}</div>
    <ol className="ofb-stages">{(pipe || []).map((s, i) => <li key={s.agent} className={`ofb-stage ${STAGE_CLS[s.state] || 'is-wait'} ${sel === s.agent ? 'is-on' : ''}`} style={{ '--i': i }}>
      <button type="button" onClick={() => onPick(s.agent)} aria-pressed={sel === s.agent} data-testid={`stage-${s.agent}`} data-tip={s.word}>
        <span className="ofb-sname">{icon[s.agent]?.[0]} {icon[s.agent]?.[1] || s.agent}</span>
        <strong>{s.state}</strong><small className="ofb-sms">{ms(s.ms)}</small><span className="ofb-sword">{s.word}</span></button></li>)}</ol>
    {cur ? <div className="ofb-checks" data-testid="ofb-checks">{(cur.checks || []).map(c => <Tag key={c[0]} cls={c[1] ? 'is-pass' : 'is-veto'} tip={c[2]}>{c[1] ? '✓' : '✕'} {c[0]} · {c[2]}</Tag>)}</div> : null}
    {cur ? <ChartBox c={cur.chart} cur={cur} /> : null}
  </div>;
}

// 📈 the chart-intelligence box: the structure state + its measured evidence, four scores, what Trigger / Devil / Warden made of it.
// Every word is a field of the shared snapshot (`backend/chart_intel.py`); nothing is derived here.
export const STRUCT_CLS = { 'STRONG UPTREND': 'is-pass', UPTREND: 'is-pass', 'PULLBACK IN UPTREND': 'is-pass', 'CONFIRMED BREAKOUT': 'is-pass', 'BREAKOUT ATTEMPT': 'is-work', ACCUMULATION: 'is-work', COMPRESSION: 'is-wait', RANGE: 'is-wait',
  UNKNOWN: 'is-wait', CHOP: 'is-veto', DISTRIBUTION: 'is-veto', DOWNTREND: 'is-veto', 'LIQUIDITY FAILURE': 'is-veto', 'FAILED BREAKOUT': 'is-veto', PARABOLIC: 'is-obj' };
export const entryCls = call => (call === 'ENTER NOW' ? 'is-pass' : call === 'SKIP' ? 'is-veto' : 'is-obj');
const Meter = ({ label, v, bad }) => <span className={`ofb-meter ${bad ? 'is-bad' : ''}`} data-testid={`meter-${label}`}><small>{label}</small><em>{v == null ? '—' : `${Math.round(v)}`}<u>/100</u></em><b aria-hidden><i style={{ transform: `scaleX(${v == null ? 0 : Math.max(0.02, Math.min(1, v / 100))})` }} /></b></span>;
const money = v => (v == null ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Number(v).toFixed(0)}`);

export function ChartBox({ c, cur }) {
  if (!c) return <div className="ofb-chart is-none" data-testid="ofb-chart"><b>📈 CHART</b><span className="ofb-nil">no chart snapshot for this coin this pass — nothing is claimed about its structure</span></div>;
  const f = c.f || {}; const wd = cur?.warden; const dv = cur?.devil;
  return <div className="ofb-chart" data-testid="ofb-chart">
    <div className="ofb-chead"><b>📈 CHART · what the agents read</b><Tag cls={STRUCT_CLS[c.state] || 'is-wait'} tip={`${c.n} one-minute candles · ${c.src === 'candles' ? 'real OHLC candles' : "Tally's own tape (closes only — wicks not measured)"}`}>{c.state}</Tag>
      <small>{c.src === 'candles' ? `${c.n} candles` : `${c.n} tape readings`} · confidence {c.conf == null ? '—' : `${Math.round(c.conf * 100)}%`}</small></div>
    <div className="ofb-meters"><Meter label="TREND" v={c.trend} /><Meter label="CHOP" v={c.chop} bad /><Meter label="MOMENTUM" v={c.mom} /><Meter label="EXTENSION" v={c.ext} bad />
      <span className="ofb-meter"><small>FLOW</small><em>{f.buy == null ? '—' : `${Math.round(f.buy)}%`}<u> buy</u></em></span><span className="ofb-meter"><small>LIQUIDITY</small><em>{money(f.liq)}</em>{f.liqD != null ? <u>{sgn(f.liqD, 0)} on our tape</u> : null}</span></div>
    <div className="ofb-calls">
      <span data-testid="chart-trigger"><small>TRIGGER</small><Tag cls={entryCls(c.entry?.[0])} tip={c.entry?.[2]}>{c.entry?.[0]}</Tag><i>{c.entry?.[1]} — {c.entry?.[2]}</i></span>
      <span data-testid="chart-devil"><small>DEVIL</small><Tag cls={dv?.verdict === 'agree' ? 'is-pass' : 'is-obj'}>{dv?.verdict === 'agree' ? 'NO OBJECTION' : 'OBJECT'}</Tag><i>{(c.objs || []).length ? c.objs.map(o => o[1]).join(' · ') : 'no chart objection the measurements support'}</i></span>
      <span data-testid="chart-warden"><small>WARDEN</small><Tag cls={!c.risk || c.risk[0] >= 1 ? 'is-pass' : c.risk[0] <= 0 ? 'is-veto' : 'is-obj'}>{wd ? `${wd.eff}×` : `${c.risk?.[0] ?? '—'}× chart`}</Tag><i>{c.risk?.[1]}{wd ? ` · sized ${usd(wd.requested)} → ${usd(wd.allowed)} (${wd.decided})` : ''}</i></span>
      <span data-testid="chart-stop"><small>STOP IF ENTERED</small><Tag>−{c.stop}%</Tag><i>{(c.stopParts || []).join(' · ')} · catastrophic −{c.hardStop}% (hard-coded)</i></span></div>
    <div className="ofb-evid"><ul className="ofb-rules is-for">{(c.ev || []).map(x => <li key={x}>{x}</li>)}</ul><ul className="ofb-rules is-against">{(c.con || []).map(x => <li key={x}>{x}</li>)}</ul></div>
    <details className="ofb-feat"><summary>every measured feature ({Object.values(f).filter(x => x != null).length})</summary>{dump(f)}</details>
  </div>;
}

const acc = c => (c?.accuracy == null ? '—' : `${c.accuracy}%`);
const STATUS_WORD = { alive: '🟢 alive', probation: '⚠ probation', demoted: '⬇ demoted', retired: '☠ retired' };

export function AgentCard({ a, on, onPick }) {
  const c = a.card || {};
  return <button type="button" className={`ofb-agent ${STATUS_CLS[c.status] || 'is-alive'} ${on ? 'is-on' : ''}`} aria-pressed={on} onClick={() => onPick(a.key)} data-testid={`office-${a.key}`}>
    <span className="ofb-ahead"><b>{a.icon} {a.name}</b><Tag cls={STATUS_CLS[c.status]} tip={c.why}>{STATUS_WORD[c.status] || '—'}</Tag></span>
    <small className="ofb-role">{a.role}</small>
    <span className="ofb-nums"><span data-tip="Survival score 0–100: accuracy weighted by how much record there is, minus rule violations and stale data."><small>SURVIVAL</small><em>{c.survival ?? '—'}</em></span>
      <span data-tip="How much record stands behind the score (samples ÷ (samples + 30))."><small>CONF</small><em>{c.confidence != null ? `${Math.round(c.confidence * 100)}%` : '—'}</em></span>
      <span><small>RIGHT</small><em>{acc(c)}</em></span><span><small>SAMPLES</small><em>{c.n ?? 0}</em></span><span><small>GEN</small><em>{c.gen ?? 1}</em></span>
      <span data-tip={`p50 ${ms(c.latency?.p50)} · p95 ${ms(c.latency?.p95)} · max ${ms(c.latency?.max)} over ${c.latency?.n || 0} passes`}><small>LAST RUN</small><em>{ms(c.latency?.last)}</em></span></span>
    <span className="ofb-line"><small>TASK</small>{a.task || <i className="ofb-nil">idle</i>}</span>
    <span className="ofb-line"><small>LAST DECISION · {ago(a.decisionAt)}</small>{a.decision || <i className="ofb-nil">none yet</i>}</span>
    <span className="ofb-line"><small>RULE IN PLAY</small>{a.rule || <i className="ofb-nil">—</i>}</span>
    <span className="ofb-line"><small>WHY THIS STATE</small>{c.why || '—'}{c.violations ? <Tag cls="is-veto">{c.violations} violation(s)</Tag> : null}{c.stale ? <Tag cls="is-stale">{c.stale} stale reads</Tag> : null}</span>
    <span className="ofb-line"><small>CONTRIBUTION{c.unit ? ` · ${c.unit}` : ''}</small><span>{c.profit != null ? <em className="ofb-up">{sgn(c.profit)}</em> : null} {c.loss != null ? <em className="ofb-dn">{sgn(c.loss, c.unit?.includes('fill') ? 2 : 1)}</em> : null}{c.profit == null && c.loss == null ? <i className="ofb-nil">nothing measured yet</i> : null}</span></span>
  </button>;
}

const Sec = ({ title, children, id }) => <section className="ofb-sec" data-testid={id}><h5>{title}</h5>{children}</section>;
const Lines = ({ xs, none }) => (xs?.length ? <ul className="ofb-rules">{xs.map(x => <li key={x}>{x}</li>)}</ul> : <span className="ofb-nil">{none || 'none'}</span>);

export function AgentDetail({ a, learning }) {
  const c = a.card || {}; const pats = (learning?.patterns || []).filter(p => p.agent === a.key);
  const cands = (learning?.candidates || []).filter(x => x.agent === a.key); const lin = (learning?.lineage || []).filter(x => x.agent === a.key);
  const score = [['samples', c.n], ['right', acc(c)], ['false positives', c.fp], ['false negatives', c.fn], ['missed winners', c.missed], ['bad approvals', c.badApprovals], ['useful vetoes', c.usefulVetoes],
    ['profit contribution', c.profit == null ? null : sgn(c.profit)], ['loss contribution', c.loss == null ? null : sgn(c.loss)], ['drawdown contribution', c.drawdown == null ? null : sgn(c.drawdown)],
    ['stale-data violations', c.stale], ['rule violations', c.violations], ['confidence', c.confidence == null ? null : `${Math.round(c.confidence * 100)}%`], ['survival score', c.survival], ['generation', c.gen]];
  return <div className="ofb-detail" data-testid={`detail-${a.key}`}>
    <header><b>{a.icon} {a.name}</b><span>{a.role}</span></header>
    <div className="ofb-dgrid">
      <Sec title="IDEOLOGY" id="sec-ideology"><p className="ofb-ideo">{a.ideology}</p></Sec>
      <Sec title="ETHICS" id="sec-ethics"><Lines xs={a.ethics} /></Sec>
      <Sec title="IMMUTABLE RULES · hard-coded, nothing can change them" id="sec-hard"><Lines xs={a.hard} /><h6>FORBIDDEN</h6><Lines xs={a.forbidden} /></Sec>
      <Sec title="TUNABLE RULES · move only through a shadow test, inside these bounds" id="sec-tunable">{a.tunable?.length ? <ul className="ofb-tune">{a.tunable.map(t => <li key={t.key} data-tip={t.what}>
        <span>{t.key}</span><em className={t.value !== t.default ? 'ofb-warn' : ''}>{t.value}</em><small>default {t.default} · bounds {t.lo} … {t.hi}</small><u aria-hidden><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, (t.value - t.lo) / ((t.hi - t.lo) || 1)))})` }} /></u></li>)}</ul>
        : <span className="ofb-nil">none — this desk's thresholds are learned from its own record (see active thresholds) or fixed</span>}</Sec>
      <Sec title="ACTIVE THRESHOLDS · CURRENT INPUTS" id="sec-inputs"><Dump v={a.inputs} /></Sec>
      <Sec title="CURRENT OUTPUT" id="sec-output"><Dump v={a.output} /></Sec>
      <Sec title="RECENT DECISIONS" id="sec-recent">{a.recent?.length ? <ul className="ofb-recent">{a.recent.map((r, i) => <li key={i}><small>{ago(r.at)}</small>{r.text}</li>)}</ul> : <span className="ofb-nil">none on record yet</span>}</Sec>
      <Sec title="LEARNED EVIDENCE · from stored records, each with its sample count" id="sec-learned">{pats.length ? <ul className="ofb-recent">{pats.map((p, i) => <li key={i}><small>n {p.n}</small>{p.text}</li>)}</ul> : <span className="ofb-nil">nothing with 5+ records yet — no pattern is stated without them</span>}
        {a.key === 'devil' && (learning?.devil || []).length ? <table className="ofb-table"><thead><tr><th>objection rule</th><th>kind</th><th>raised</th><th>5-min after</th><th>right</th></tr></thead><tbody>{learning.devil.map(r => <tr key={r.rule}><td data-tip={r.what}>{r.rule}</td><td>{r.hard ? 'hard' : 'soft'}</td><td>{r.n}</td><td>{sgn(r.med)}</td><td>{r.saved == null ? '—' : `${r.saved}%`}</td></tr>)}</tbody></table> : null}</Sec>
      <Sec title="SURVIVAL RECORD" id="sec-survival"><dl className="ofb-kv">{score.map(([k, v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{v == null ? <span className="ofb-nil">not measurable for this desk</span> : <span className="ofb-val">{v}</span>}</dd></React.Fragment>)}</dl>
        <p className="ofb-lat">runtime: last {ms(c.latency?.last)} · p50 {ms(c.latency?.p50)} · p95 {ms(c.latency?.p95)} · max {ms(c.latency?.max)} ({c.latency?.n || 0} passes)</p></Sec>
      <Sec title="GENERATION HISTORY" id="sec-gen">{lin.length || cands.length ? <ul className="ofb-recent">{cands.map(x => <li key={x.id}><small>{x.status}</small>{x.key} {x.live} → {x.value} · shadow {x.eval?.n ?? 0}/{x.eval?.need ?? learning?.needShadow}{x.eval?.n ? ` · live ${sgn(x.eval.live, 2)} vs candidate ${sgn(x.eval.cand, 2)}` : ''}</li>)}
        {lin.map((x, i) => <li key={i}><small>gen {x.gen}</small>{x.why}</li>)}</ul> : <span className="ofb-nil">generation {c.gen ?? 1} — no change promoted, no demotion</span>}</Sec>
      <Sec title="SOURCE CODE" id="sec-code"><ul className="ofb-code">{(a.code || []).map(k => <li key={k.file}><code>{k.file}</code>{k.fn.map(f => <code key={f} className="ofb-fn">{f}()</code>)}</li>)}</ul></Sec>
    </div>
  </div>;
}

export const DECISION_CLS = { HOLD: 'is-hold', 'HOLD 5 MORE': 'is-hold', PROTECT: 'is-prot', 'TAKE PROFIT': 'is-take', EXIT: 'is-exit' };

// ☠ one card per live position: what it was entered on, what the chart says now, and what Reaper rules — with the rule it is obeying
export function PositionCard({ p }) {
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(t); }, []);
  const th = p.thesis; const seen = useRef({ at: Date.now(), next: p.nextReview }); if (seen.current.next !== p.nextReview) seen.current = { at: Date.now(), next: p.nextReview };
  const left = p.nextReview == null ? null : Math.max(0, p.nextReview - (Date.now() - seen.current.at) / 1000);
  return <article className={`ofb-pos ${REAP_CLS[p.state] || 'is-hold'}`} data-testid={`pos-${p.symbol}`}>
    <header><b>${p.symbol}</b>{p.owner === 'agents' ? <Tag tip="A coin the agents put on the card">🤖 theirs</Tag> : <Tag tip="Not an agent seat: it keeps the card's own stop; Reaper still watches it for invalidation">card coin</Tag>}{p.exec === 'unconfirmed' ? <Tag cls="is-work">⏳ fill not confirmed</Tag> : null}
      <Tag cls={DECISION_CLS[p.decision] || REAP_CLS[p.state]}>REAPER: {p.decision || p.state}</Tag></header>
    <div className="ofb-pgrid">
      <span><small>ENTERED ON</small><em>{th ? th.structure : <i className="ofb-nil">no thesis on file</i>}</em>{th ? <u>{th.triggerRule}</u> : <u>bought before theses were saved</u>}</span>
      <span><small>STRUCTURE NOW</small><em>{p.structure ? <Tag cls={STRUCT_CLS[p.structure] || 'is-wait'}>{p.structure}</Tag> : <i className="ofb-nil">no chart</i>}</em>{p.verdict ? <u>thesis {p.verdict}</u> : null}</span>
      <span><small>HELD</small><em>{p.heldMin == null ? '—' : clock(p.heldMin * 60)}</em>{p.window != null ? <u>window {p.window + 1} of {p.granted}</u> : null}</span>
      <span><small>NOW</small><em className={p.pct > 0 ? 'ofb-up' : p.pct < 0 ? 'ofb-dn' : ''}>{sgn(p.pct)}</em><u>{usd(p.usd)}{p.warden != null && p.warden < 1 ? ` · 🛡 ×${p.warden}` : ''}</u></span>
      <span><small>PEAK</small><em>{sgn(p.peak)}</em></span>
      <span><small>FROM PEAK</small><em className={p.dd > 0 ? 'ofb-dn' : ''}>{p.dd == null ? '—' : `−${p.dd.toFixed(1)} pts`}</em></span>
      <span><small>NEXT REVIEW</small><em>{left == null ? '—' : clock(left)}</em></span>
      <span data-tip={`take +${p.take}% (${p.takeSource}) · stop ${p.stop}% · catastrophic ${p.hardStop}% (hard-coded)`}><small>LINES</small><em>+{p.take}% / {p.stop}%</em><u>{p.takeSource} take · hard {p.hardStop}%</u></span>
    </div>
    <p className="ofb-pwhy"><small>OBEYING</small><Tag>{p.obeying || '—'}</Tag><b>{p.rule}</b><span>{p.evidence}</span></p>
    {p.why?.length ? <ul className="ofb-rules is-for">{p.why.map(x => <li key={x}>{x}</li>)}</ul> : null}
    {th ? <details className="ofb-feat"><summary>entry thesis (saved at the fill, never rewritten)</summary>{dump({ ...th, at: ago(th.at) })}</details> : null}
  </article>;
}

export function TakeLine({ t }) {
  if (!t) return null;
  return <div className="ofb-take" data-testid="ofb-take" data-tip="Which take line the agents' real seats obey right now. The take line is not an office tunable: it is your setting, or the scalp line they learned from their own paths (dropped by itself when it stops being proven).">
    <span><small>BASE TAKE</small><em>+{t.base}%</em></span><span><small>ACTIVE TAKE</small><em className={t.active !== t.base ? 'ofb-warn' : ''}>+{t.active}%</em></span>
    <span><small>SOURCE</small><em>{t.source}</em></span><span><small>EVIDENCE N</small><em>{t.evidenceN ?? '—'}</em><u>needs {t.needN}</u></span>
    <span><small>RESULT ON OWN PATHS</small><em>{t.shadowAvg == null ? '—' : sgn(t.shadowAvg, 2)}</em></span><span><small>ADOPTED</small><em>{t.adoptedAt ? ago(t.adoptedAt) : '—'}</em></span>
    <span><small>RULE ID</small><em>{t.ruleId}</em><u>{t.rule}</u></span></div>;
}

export function OfficePositions({ positions, exiting, take }) {
  return <div className="ofb-box" data-testid="ofb-positions"><b>☠ REAPER · open positions on the real card</b>
    <TakeLine t={take} />
    {positions?.length ? <div className="ofb-poslist">{positions.map(p => <PositionCard key={p.mint} p={p} />)}</div> : <span className="ofb-nil">no open position Reaper is responsible for</span>}
    {exiting?.length ? <p className="ofb-exiting">{exiting.map(e => <Tag key={e.mint} cls="is-work" tip="Left the card; it is closed only when the ledger shows the confirmed sale.">${e.sym} exit {e.state} · {e.rule || 'card rule'}</Tag>)}</p> : null}
  </div>;
}

export function OfficeExecution({ x }) {
  if (!x) return null;
  return <div className="ofb-box" data-testid="ofb-exec"><b>📮 COURIER · execution, from the keeper's ledger</b>
    <p className="ofb-xhead"><Tag cls={HEALTH_CLS[x.health]}>{x.health}</Tag><span>{(x.why || []).join(' · ')}</span></p>
    <div className="ofb-xgrid"><span><small>SENDS 1H</small><em>{x.sends}</em></span><span><small>CONFIRMED</small><em>{x.fills}</em></span><span><small>FAILED</small><em className={x.failed ? 'ofb-dn' : ''}>{x.failed}</em></span>
      <span><small>EXPIRED</small><em>{x.expired}</em></span><span><small>REFUSED</small><em>{x.refused}</em></span><span><small>RETRIES</small><em>{x.retries}</em></span><span><small>DUPLICATES</small><em className={x.duplicates ? 'ofb-dn' : ''}>{x.duplicates}</em></span>
      <span data-tip="Typical confirmed fill vs the mid price at the quote (positive = worse)."><small>FILL VS MID</small><em>{sgn(x.deltaMed, 2)}</em></span><span><small>WORST</small><em>{sgn(x.deltaWorst, 2)}</em></span>
      <span data-tip="Send → booked from the chain. Recorded on fills from this version on."><small>TIME TO LAND</small><em>{x.landMed == null ? '—' : `${x.landMed}s`}</em></span><span><small>FEE / SWAP</small><em>{x.feeMed == null ? '—' : `$${x.feeMed}`}</em></span>
      <span><small>IN FLIGHT</small><em>{x.pending ? `${x.pending.side} $${x.pending.sym} · ${x.pending.age}s` : 'none'}</em></span></div>
    {x.last?.length ? <table className="ofb-table"><thead><tr><th>when</th><th>order</th><th>state</th><th>quote mid</th><th>fill</th><th>vs mid</th><th>impact</th><th>fee</th><th>note</th></tr></thead>
      <tbody>{x.last.map((r, i) => <tr key={i}><td>{ago(r.at)}</td><td>{r.side} ${r.sym} {usd(r.usd)}</td><td><Tag cls={r.state === 'confirmed' ? 'is-pass' : r.state === 'failed' ? 'is-veto' : 'is-obj'}>{r.state}</Tag></td>
        <td>{r.midPx == null ? '—' : tiny(r.midPx)}</td><td>{r.px == null ? '—' : tiny(r.px)}</td><td>{sgn(r.delta, 2)}</td><td>{r.impact == null ? '—' : `${r.impact}%`}</td><td>{r.feeUsd == null ? '—' : `$${r.feeUsd}`}</td>
        <td className="ofb-ev">{r.err || (r.retry ? 'retry' : '')}{r.sig ? <a href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noreferrer">tx ↗</a> : null}</td></tr>)}</tbody></table> : null}
  </div>;
}

export function OfficePerf({ perf, agents }) {
  const rows = (agents || []).map(a => [a, perf?.agents?.[a.key] || {}]); const worst = Math.max(0.01, ...rows.map(([, l]) => l.p95 || 0));
  return <div className="ofb-box" data-testid="ofb-perf"><b>⚡ RUNTIME · per desk, last 120 passes</b>
    <table className="ofb-table"><thead><tr><th>desk</th><th>last</th><th>p50</th><th>p95</th><th>max</th><th /></tr></thead><tbody>{rows.map(([a, l]) => <tr key={a.key}><td>{a.icon} {a.name}</td><td>{ms(l.last)}</td><td>{ms(l.p50)}</td><td>{ms(l.p95)}</td><td>{ms(l.max)}</td>
      <td className="ofb-barcell"><u aria-hidden><i style={{ transform: `scaleX(${Math.max(0.01, (l.p95 || 0) / worst)})` }} /></u></td></tr>)}</tbody></table>
    <p className="ofb-lat" data-testid="ofb-candles">📈 shared chart snapshot: {ms(perf?.chart?.last)} for {(perf?.candles?.real ?? 0) + (perf?.candles?.tape ?? 0)} coins (p95 {ms(perf?.chart?.p95)}) · {perf?.candles?.real ?? 0} from real candles, {perf?.candles?.tape ?? 0} from the tape · candle requests this pass {perf?.candles?.req ?? 0} ({perf?.candles?.cached ?? 0} served from cache) · duplicated {perf?.candles?.dup ?? 0}</p>
    <p className="ofb-lat">whole chain this pass {ms(perf?.passMs)} · the four desks' pass incl. the board read {ms(perf?.deskMs)} · the page reads memory: it starts no desk, scan or quote</p></div>;
}

export function OfficeLearning({ l }) {
  return <div className="ofb-box" data-testid="ofb-learn"><b>🗄 ARCHIVIST · what the stored records say</b>
    {l?.patterns?.length ? <ul className="ofb-recent">{l.patterns.map((p, i) => <li key={i}><small>{p.agent} · n {p.n}</small>{p.text}</li>)}</ul> : <span className="ofb-nil">no pattern has 5 judged records behind it yet — nothing is claimed before that</span>}
    <p className="ofb-lat">a rule changes only this way: {l?.needPropose} archived positions → the Judge proposes ONE change → {l?.needShadow} new positions in shadow → it must beat the live rule → promoted. {(l?.candidates || []).filter(c => c.status === 'shadow').length} in shadow now.</p></div>;
}

export function OfficeBoard({ o }) {
  const [sel, setSel] = useState(null); const boardRef = useRef(null);
  // the opened desk sits right under its card; when that is off screen (a tap on the line above) the PAGE moves to it — never a scroll inside a card
  useEffect(() => { if (!sel) return; try { const r = boardRef.current?.querySelector('.ofb-detail')?.getBoundingClientRect();
    if (r && (r.top < 60 || r.top > window.innerHeight - 160)) window.scrollBy({ top: r.top - 90, behavior: 'smooth' }); } catch (e) { /* no layout (tests) */ } }, [sel]);
  if (!o || o.cold) return <div className="ofb" data-testid="office-board"><OfficeMission m={null} /></div>;
  const a = (o.agents || []).find(x => x.key === sel);
  const pick = k => setSel(s => (s === k ? null : k));
  return <div className="ofb" data-testid="office-board" ref={boardRef}>
    <OfficePipeline pipe={o.pipeline} cur={o.currentCase} agents={o.agents} onPick={pick} sel={sel} />
    {a ? null : <p className="ofb-hint">Tap a desk (or a stage of the line) to open its ideology, ethics, immutable and tunable rules, this pass's inputs and output, its record and the code that runs it.</p>}
    <div className="ofb-agents" data-testid="ofb-agents">{(o.agents || []).map(x => <React.Fragment key={x.key}><AgentCard a={x} on={sel === x.key} onPick={pick} />
      {sel === x.key ? <AgentDetail a={x} learning={o.learning} /> : null}</React.Fragment>)}</div>
    <OfficePositions positions={o.positions} exiting={o.exiting} take={o.take} />
    <OfficeExecution x={o.execution} />
    <div className="ofb-two"><OfficeLearning l={o.learning} /><OfficePerf perf={o.performance} agents={o.agents} /></div>
  </div>;
}

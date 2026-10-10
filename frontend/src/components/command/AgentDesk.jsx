import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { openCoin } from '../CoinDrawer';
import '../../styles/agentDesk.css';
import { AgentRoom } from './AgentRoom';

// 🤖 HQ › AGENTS (owner, 2026-10-09: "code your own agents to learn trading and trenching — one tracks the numbers, one knows why they
// moved, one knows exactly when to enter, one argues it's right or not; none can work without the others; start by conquering the 5 min").
// GET /admin/agents every 20s: the four agents as cards with their OWN scorecard, the stage (5 → 15 → 60 min), the live table (every
// coin with each agent's word in order: numbers → why → call → argument → GO), the team's $20 paper desk, and the one owner switch that
// lets proven GO calls feed the real card's rush. A record, never a promise.
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const tone = v => (v == null ? '' : v > 0 ? 'm-pos' : v < 0 ? 'm-neg' : '');
const CALL = { enter: ['ENTER', 'is-go'], wait: ['WAIT', 'is-wait'], skip: ['SKIP', 'is-no'] };
const VERDICT = { agree: ['agrees', 'is-go'], object: ['objects', 'is-no'], '—': ['—', ''] };
const WHO = { tally: ['📊', 'Tally'], sherlock: ['🔍', 'Sherlock'], trigger: ['⏱', 'Trigger'], devil: ['⚖', 'Devil'], desk: ['🧾', 'Desk'] };
const ago = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - t)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
// 🛣 ROAD TO REAL MONEY (owner: "how close it is to real money"): 📜 the 5-min trench desk 10× in one run (≥ 30 GO calls) → 💵 the real
// test on the owner's Fuse card (≥ 10 closed pieces, typical result > 0) → 15 min → 60 min.
export function RoadMeter({ road }) {
  if (!road) return null;
  const p = road.paper, r = road.real;
  const steps = [['📜', `Paper desk 10× · ${p.x.toFixed(2)}× of ${p.need}× · ${p.n}/${p.needN} GO calls`, p.done, !p.done],
    ['💵', r.open ? `Real money on your Fuse card · ${r.n}/${r.needN} closed${r.med != null ? ` · ${r.med >= 0 ? '+' : ''}${r.med}% typical` : ''}` : 'Real money on your Fuse card — opens after the 10×', r.done, p.done && !r.done],
    ['⏱', '15-minute stage', false, false], ['🕐', '1-hour stage', false, false]];
  return <div className="agd-road" data-testid="agd-road"><div className="agd-road-top"><b>🛣 ROAD TO REAL MONEY</b><em>{road.pct}%</em></div>
    <div className="agd-road-bar"><i style={{ transform: `scaleX(${Math.max(0.02, road.pct / 100)})` }} /></div>
    <ol>{steps.map(([ic, t, done, now]) => <li key={t} className={done ? 'is-done' : now ? 'is-now' : ''}><span>{done ? '✓' : ic}</span>{t}</li>)}</ol></div>;
}
// 🗯 LIVE: what the four said, newest first — the coin, who said it, how long ago. A desk line = a call that just got its 5-minute verdict.
export function ThoughtFeed({ lines }) {
  return <div className="agd-feed" data-testid="agd-thoughts"><b>🗯 LIVE — WHAT THEY'RE THINKING</b>
    {(lines || []).length ? <ul>{lines.slice(0, 30).map((l, i) => { const w = WHO[l.who] || ['•', l.who];
      return <li key={`${l.at}-${l.who}-${l.sym}-${i}`} className={`is-${l.who}`} style={{ '--i': Math.min(i, 8) }}><span className="agd-who">{w[0]} {w[1]}</span><span className="agd-txt">{l.text}</span><small>{ago(l.at)}</small></li>; })}</ul>
      : <small className="m-dim">Their first words land within a minute.</small>}</div>;
}
// 🧠 what the desk knows about HUMAN trenching right now: the narratives the board rides, slang it learned from Pump callers' own words,
// bot swarms it caught (copy-paste callouts), and how many human calls it read.
export function MindBox({ m }) {
  if (!m) return null;
  return <div className="agd-box agd-mind" data-testid="agd-mind"><b>🧠 TRENCH MIND · what they learned from humans</b>
    <p className="m-dim">Read {m.callsRead || 0} Pump callouts · dictionary {m.dictionary || 0} words · {m.swarms || 0} bot swarm{m.swarms === 1 ? '' : 's'} caught on the live list</p>
    <span className="agd-tags">{(m.hot || []).map(h => <i key={h.key} data-tip={`${h.n} coins · $${Math.round((h.vol1h || 0) / 1000)}K traded this hour`}>{h.label} · {h.n}</i>)}{!(m.hot || []).length && <small className="m-dim">no narrative leads the board right now</small>}</span>
    <span className="agd-tags is-lingo">{(m.learned || []).length ? m.learned.map(w => <i key={w.word} data-tip={`learned from callers' own words · seen ${w.n}×`}>📖 {w.word}</i>) : <small className="m-dim">no new slang yet — a word must show up on 2+ days, 6+ times, from humans (bot copies count once)</small>}</span></div>;
}
const big = v => (v == null ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}K` : `$${Math.round(v)}`);
const age = h => (h == null ? '—' : h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${Math.round(h)}h` : `${Math.round(h / 24)}d`);
// 🩺 the coin's vitals beside the verdict — every number the agents saw, bad ones pink
export const vitalCells = v => [['cap', big(v?.mcap)], ['age', age(v?.ageH)], ['pool', big(v?.liq)], ['1h vol', big(v?.vol1h)],
  ['buys', v?.buyShare != null ? `${Math.round(v.buyShare)}%` : '—', v?.buyShare != null && v.buyShare < 50], ['top-10', v?.top10 != null ? `${Math.round(v.top10)}%` : '—', v?.top10 != null && v.top10 >= 35],
  ['bundles', v?.bundledN ?? '—', v?.bundledN != null && v.bundledN >= 3], ['snipers', v?.snipersN ?? '—', v?.snipersN != null && v.snipersN >= 8],
  ['organic', v?.organic != null ? `${Math.round(v.organic)}%` : '—', v?.organic != null && v.organic < 5], ['rug', v?.rug != null ? Math.round(v.rug) : '—', v?.rug != null && v.rug >= 50],
  ['scan', v?.safe === true ? '✅' : v?.safe === false ? '⚠ failed' : '❔', v?.safe === false]];
// ⚙ the agents' controls for the REAL Fuse card (creator only): feed on/off, the profit an agent coin must reach before they may move it,
// what they do then (auto = they choose · pull = profit to cash, seat open · swap = a fresh GO runner), and how many seats they may hold.
export function AgentControls({ cfg, decisions, proven, isOwner, busy, save }) {
  const c = cfg || {}; const o = c.options || { take: [5, 10, 20, 30, 50], mode: ['auto', 'pull', 'swap'], seats: [1, 2, 3, 4] };
  const MODE = { auto: '🤖 they choose', pull: '💰 pull to cash', swap: '⇄ swap runner' };
  const seg = (k, vals, lab) => <div className="m-seg" role="group">{vals.map(v => <button key={String(v)} type="button" disabled={busy || !isOwner} className={String(c[k]) === String(v) ? 'active' : ''} onClick={() => save({ cfg: { [k]: v } })} data-testid={`agc-${k}-${v}`}>{lab(v)}</button>)}</div>;
  return <div className="agd-box agd-ctl" data-testid="agd-controls"><b>⚙ AGENT CONTROL · YOUR FUSE CARD</b>
    <div className="agd-ctl-row"><span>Their GO coins on my card</span><div className="m-seg"><button type="button" disabled={busy || !isOwner} className={c.agentFeed ? 'active' : ''} onClick={() => save({ feed: true })} data-testid="agd-feed-on">ON</button><button type="button" disabled={busy || !isOwner} className={!c.agentFeed ? 'active' : ''} onClick={() => save({ feed: false })} data-testid="agd-feed-off">Paper only</button></div></div>
    <div className="agd-ctl-row"><span>🎓 Learning seat (1 coin, real money, before they're proven)</span><div className="m-seg"><button type="button" disabled={busy || !isOwner} className={c.agentLearn ? 'active' : ''} onClick={() => save({ cfg: { agentLearn: true } })} data-testid="agc-learn-on">ON</button><button type="button" disabled={busy || !isOwner} className={!c.agentLearn ? 'active' : ''} onClick={() => save({ cfg: { agentLearn: false } })} data-testid="agc-learn-off">off</button></div></div>
    {c.agentLearn && <div className="agd-ctl-row"><span>Learning ticket</span>{seg('agentLearnPct', [5, 10, 15], v => `${v}% of the card`)}</div>}
    <div className="agd-ctl-row"><span>Hold until profit</span>{seg('agentTakePct', o.take, v => `+${v}%`)}</div>
    <div className="agd-ctl-row"><span>Then</span>{seg('agentMode', o.mode, v => MODE[v] || v)}</div>
    <div className="agd-ctl-row"><span>Seats they may hold</span>{seg('agentSeats', o.seats, v => `${v}`)}</div>
    <small className="m-dim">{proven ? 'LIVE on your card.' : 'Starts the moment the 5-min desk 10×s — until then they trade paper only.'} An agent coin is never stopped, rotated or cycled out before it's in profit (only the rug shield cuts it). In profit they read it again every pass.</small>
    {(decisions || []).length > 0 && <ul className="agd-dec" data-testid="agd-decisions">{decisions.map(x => <li key={x.pair} className={`is-${x.action}`}><b>{x.action === 'hold' ? '⏳' : x.action === 'pull' ? '💰' : '⇄'} ${x.symbol}</b><span>{x.why}</span></li>)}</ul>}</div>;
}
// 💡 tactics the desk found in its own record, sent up for the creator's review
export function IdeaBox({ ideas, isOwner, busy, save, need = 15 }) {
  const fresh = (ideas || []).filter(i => i.status === 'new'); const past = (ideas || []).filter(i => i.status !== 'new').slice(0, 6);
  return <div className="agd-box agd-ideas" data-testid="agd-ideas"><b>💡 IDEAS FOR YOUR REVIEW · {fresh.length} new</b>
    {fresh.length ? <ul>{fresh.map(i => <li key={i.id} className={`is-${i.kind}`}><span>{i.kind === 'take' ? '🎯 TAKE' : '🚫 AVOID'} · {i.text}</span>
      <span className="agd-idea-do"><button type="button" className="m-btn m-go" disabled={busy || !isOwner || (i.n || 0) < need} onClick={() => save({ idea: { id: i.id, action: 'approve' } })} data-testid={`idea-ok-${i.id}`}>{(i.n || 0) < need ? `👀 ${i.n}/${need} calls` : 'Approve'}</button>
        <button type="button" className="m-btn" disabled={busy || !isOwner} onClick={() => save({ idea: { id: i.id, action: 'reject' } })} data-testid={`idea-no-${i.id}`}>Reject</button></span></li>)}</ul>
      : <small className="m-dim">No new tactic yet — two reasons must show up together on 10+ judged calls with a clear result (≥ +3% typical and 55% up, or ≤ −5%).</small>}
    {past.length > 0 && <small className="m-dim">Reviewed: {past.map(i => `${i.status === 'approved' ? '✅' : '✕'} ${i.kind} (${i.n} calls ${i.med >= 0 ? '+' : ''}${i.med}%)`).join(' · ')}</small>}</div>;
}
// 📜 THE CREED + ⚔ the lineage: who was scrapped, after how many calls, and what they had become
export function CreedBox({ creed, lineage }) {
  const NAMES = { tally: '📊 Tally', sherlock: '🔍 Sherlock', trigger: '⏱ Trigger', devil: '⚖ Devil' };
  return <details className="agd-box agd-creed" data-testid="agd-creed"><summary><b>📜 THE CREED · engraved in their code</b><small>{(lineage || []).length ? ` · ${lineage.length} scrapped li${lineage.length === 1 ? 'fe' : 'ves'}` : ' · no agent scrapped yet'}</small></summary>
    <ol>{(creed || []).map((c, i) => <li key={i}>{c}</li>)}</ol>
    {(lineage || []).length > 0 && <ul className="agd-lineage">{lineage.map((l, i) => <li key={i}>☠ {NAMES[l.agent] || l.agent} gen {l.gen} · {l.n} calls · {l.right != null ? `${l.right}% right` : `${l.med}% typical`}</li>)}</ul>}</details>;
}
// 🏭 THE WORK FLOOR — every mark is a real thing from the last pass (nothing decorative): Tally's dots = the coins it read (green up / pink
// down over 5 min), Sherlock's tags = the reasons it weighed most this pass, Trigger's crosshairs = its real ENTER calls, Devil's marks = its
// real verdicts on them. Re-keyed per pass, so each new pass plays in. Real ms per agent beside each lane.
export const floorOf = d => { const t = d?.table || []; const freq = {};
  t.forEach(x => (x.why?.drivers || []).slice(0, 3).forEach(dd => { freq[dd[2]] = (freq[dd[2]] || 0) + 1; }));
  return { dots: t.slice(0, 32).map(x => ({ k: x.mint, up: Number(x.nums?.d5) >= 0, sym: x.symbol })),
    tags: Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 6), enters: t.filter(x => x.trigger?.[0] === 'enter').slice(0, 6),
    verdicts: t.filter(x => x.trigger?.[0] === 'enter').slice(0, 6).map(x => ({ sym: x.symbol, ok: x.devil?.[0] === 'agree', go: x.go })) }; };
export function WorkFloor({ d }) {
  const f = floorOf(d); const p = d?.perf || {}; const ms = k => (p[k] != null ? `${p[k]} ms` : '—');
  return <div className="agd-floor" data-testid="agd-floor" key={p.at || 0}>
    <div className="agd-lane is-tally"><span className="agd-lane-h">📊 Tally <small>{f.dots.length} coins · {ms('tally')}</small></span><span className="agd-lane-b">{f.dots.map((x, i) => <i key={x.k} className={`agd-dot ${x.up ? 'is-up' : 'is-dn'}`} style={{ '--i': i }} data-tip={`$${x.sym}`} />)}</span></div>
    <div className="agd-lane is-sherlock"><span className="agd-lane-h">🔍 Sherlock <small>{ms('sherlock')}</small></span><span className="agd-lane-b">{f.tags.map(([w, n], i) => <i key={w} className="agd-tag" style={{ '--i': i }}>{w} ×{n}</i>)}{!f.tags.length && <small className="m-dim">no reasons this pass</small>}</span></div>
    <div className="agd-lane is-trigger"><span className="agd-lane-h">⏱ Trigger <small>{f.enters.length} ENTER · {ms('trigger')}</small></span><span className="agd-lane-b">{f.enters.map((x, i) => <i key={x.mint} className="agd-aim" style={{ '--i': i }}>⌖ ${x.symbol}</i>)}{!f.enters.length && <small className="m-dim">nothing clean enough this pass</small>}</span></div>
    <div className="agd-lane is-devil"><span className="agd-lane-h">⚖ Devil <small>{ms('devil')}</small></span><span className="agd-lane-b">{f.verdicts.map((x, i) => <i key={x.sym} className={`agd-strike ${x.ok ? 'is-ok' : 'is-no'}`} style={{ '--i': i }}>{x.ok ? (x.go ? '🟢' : '✓') : '✕'} ${x.sym}</i>)}{!f.verdicts.length && <small className="m-dim">nothing to argue</small>}</span></div>
  </div>;
}
// 🧪 THE TANKS — each agent's next generation waits in water. The water rises with REAL danger (its status + how close its life is to the
// scrap line); the glass carries the lesson it will inherit. A death empties the tank: the new one is born and the next embryo waits.
export const danger = (l, surviveN = 30, scrapN = 60) => (!l ? 0 : l.status === 'scrap' ? 1 : l.status === 'probation' ? Math.min(1, 0.55 + 0.45 * ((l.n || 0) - surviveN) / Math.max(1, scrapN - surviveN)) : Math.min(0.35, 0.35 * (l.n || 0) / scrapN));
export function Tanks({ life, lessons, surviveN, scrapN }) {
  const A = [['tally', '📊'], ['sherlock', '🔍'], ['trigger', '⏱'], ['devil', '⚖']];
  return <div className="agd-tanks" data-testid="agd-tanks">{A.map(([k, ic]) => { const l = life?.[k]; const dz = danger(l, surviveN, scrapN); const young = l?.born && Date.now() / 1000 - l.born < 600;
    return <div key={k} className={`agd-tank is-${l?.status || 'alive'}`} data-testid={`tank-${k}`}>
      <div className="agd-glass"><i className="agd-water" style={{ transform: `scaleY(${Math.max(0.08, dz)})` }} />{[0, 1, 2, 3, 4].map(i => <u key={i} className="agd-bub" style={{ '--i': i }} />)}<b className="agd-embryo">{ic}</b></div>
      <small><b>gen {(l?.gen || 1) + 1}</b> waiting{young ? ' · 🐣 gen ' + (l?.gen || 1) + ' just born' : ''}</small>
      <small className="m-dim">{l?.status === 'probation' ? `⚠ gen ${l.gen} on probation · ${l.n}/${scrapN}` : l?.status === 'scrap' ? '☠ being scrapped' : `gen ${l?.gen || 1} alive · ${l?.n || 0} calls`}</small>
      <small className="agd-lesson">{(lessons?.[k]?.words || []).length ? `inherits: ${lessons[k].words.join(' · ')}` : 'inherits: whatever kills the one before it'}</small></div>; })}</div>;
}
// 🎯 calibration + 🌡 regime + 🕸 budget cuts + 🔥 burned — the extra mechanics that keep the desk honest
export function Edge({ d }) {
  const cal = d?.calibration || {}; const rg = d?.perf?.regime;
  return <div className="agd-box agd-edge" data-testid="agd-edge"><b>🎯 CALIBRATION · does a stronger read win more?</b>
    {Object.keys(cal).length ? <ul>{Object.entries(cal).map(([b, v]) => <li key={b}><span>lean {b}</span><em className={tone(v.med)}>{pct(v.med)}</em><small>{v.won}% up · n {v.n}</small></li>)}</ul> : <small className="m-dim">no ENTER judged yet</small>}
    <small className="m-dim">🌡 trench {rg ? `${rg.word}${rg.green != null ? ` (${rg.green}% green over 5 min)` : ''} → Trigger's bar ${rg.adj > 0 ? '+' : ''}${rg.adj}` : '—'} · 🔥 {d?.burned || 0} coin{d?.burned === 1 ? '' : 's'} burned (6h) · 🕸 {Object.keys(d?.cut || {}).length ? `budget cut: ${Object.keys(d.cut).join(', ')}` : 'no source cut yet'}</small></div>;
}
// 🔬 every rug the desk was on: what it read, what it missed — and the reasons that keep showing up in rugs (Devil objects to 2+ of them)
export function AutopsyBox({ list, signs }) {
  return <div className="agd-box agd-autopsy" data-testid="agd-autopsy"><b>🔬 RUG AUTOPSY · what we missed</b>
    {(list || []).length ? <ul>{list.map(a => <li key={a.id}>{a.text}{(a.missed || []).length ? <small> · missed: {a.missed.join(', ')}</small> : null}</li>)}</ul> : <small className="m-dim">no rug on the desk yet</small>}
    {(signs || []).length > 0 && <span className="agd-tags">{signs.map(x => <i key={x.key} className={x.n >= 3 ? 'is-bad' : ''}>☠ {x.words} ×{x.n}</i>)}</span>}</div>;
}
export const agentLine = a => (a.n ? `${a.n} judged · ${pct(a.med)} typical at 5 min${a.right != null ? ` · ${a.right}% right` : ''}` : 'no judged calls yet — every call is checked 5 minutes later');

export function AgentDesk({ call, isOwner = true }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(false);
  const load = useCallback(() => call('/admin/agents').then(setD).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [load]);
  if (!d) return <p className="cc-empty">Waking the agents…</p>;
  const st = d.stage || {};
  const warLog = async () => { try { const r = await call('/admin/agents/log?hours=24'); const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([r.md], { type: 'text/markdown' })); a.download = `agent-war-log-${new Date().toISOString().slice(0, 10)}.md`; a.click(); URL.revokeObjectURL(a.href); } catch (e) { toast.error(e.message); } };
  const save = async body => { setBusy(true); try { await call('/admin/agents', { method: 'POST', body: JSON.stringify(body) }); toast.success(body.idea ? `💡 idea ${body.idea.action === 'approve' ? 'approved' : 'rejected'}` : '🤖 agent control saved'); load(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <section className="agd m-live" data-testid="agent-desk">
    <header className="agd-head"><div><b>🤖 THE AGENT DESK</b><button type="button" className="m-btn agd-log" onClick={warLog} data-testid="agd-log">⬇ War log</button><small>Four agents, one chain — none of them can call a trade without the other three. Every call is checked 5 minutes later; they move to 15 min only after they conquer 5.</small></div>
      <div className="agd-stage" data-testid="agd-stage">{[5, 15, 60].map(h => <span key={h} className={(st.conquered || []).includes(h) ? 'is-done' : st.h === h ? 'is-now' : ''}>{(st.conquered || []).includes(h) ? '✓' : st.h === h ? '⚔' : '🔒'} {h}m</span>)}
        <small>{st.team?.n ? `team ${st.team.n}/${st.needN} judged · ${pct(st.team.med)} · ${st.team.won}% won (needs ${st.needWin}%)` : `needs ${st.needN} judged GO calls, a positive median and ${st.needWin}% won`}</small></div></header>
    <AgentRoom d={d} />
    <RoadMeter road={d.road} />
    <WorkFloor d={d} />
    <div className="agd-chain">{(d.agents || []).map((a, i) => <React.Fragment key={a.key}><div className={`agd-agent is-${a.key}`} style={{ '--i': i }} data-testid={`agent-${a.key}`}>
      <span className="agd-ico" aria-hidden>{a.icon}</span><b>{a.name}</b><small>{a.job}</small>
      {d.life?.[a.key] && <span className={`agd-life is-${d.life[a.key].status}`} data-testid={`life-${a.key}`}>gen {d.life[a.key].gen} · {d.life[a.key].status === 'alive' ? '🟢 alive' : d.life[a.key].status === 'probation' ? '⚠ probation' : '☠ being scrapped'}</span>}
      <em className={tone(a.med)}>{a.n ? pct(a.med) : '—'}</em><i>{agentLine(a)}</i>
      <span className="agd-task" data-testid={`task-${a.key}`}><span className="agd-live" aria-hidden />{d.tasks?.[a.key] || 'waiting for the first pass'}</span><span className="agd-scan" aria-hidden><u /></span>{d.perf?.[a.key] != null && <small className="agd-ms" data-testid={`ms-${a.key}`}>⚡ {d.perf[a.key]} ms this pass</small>}</div>{i < 3 && <span className="agd-arrow" aria-hidden>→</span>}</React.Fragment>)}</div>
    <small className="m-dim agd-pass">last pass {d.tasks?.at ? `${ago(d.tasks.at)} ago` : '—'} · one a minute, any hour the backend is online</small>
    <div className="agd-row2">
      <div className="agd-box" data-testid="agd-desk"><b>📜 TRENCH DESK · 25% a GO, out at 5 min · goal 10×</b><p className={`agd-big ${tone(d.desk.now - d.desk.start)}`}>${d.desk.now.toFixed(2)} <small>{d.desk.x}× of ${d.desk.start} · best run {d.desk.best}× · {d.desk.busts} bust{d.desk.busts === 1 ? '' : 's'} · {d.desk.trades} trades</small></p>
        <small className="m-dim">Control group (coins Trigger said WAIT): {d.control?.n ? `${pct(d.control.med)} typical` : 'not judged yet'} — the team must beat this to mean anything. Slippage on a 5-min scalp is not modelled.</small></div>
      <div className="agd-box" data-testid="agd-drivers"><b>🔍 WHAT SHERLOCK LEARNED</b>{(d.drivers || []).length ? <ul>{d.drivers.slice(0, 7).map(x => <li key={x.key}><span>{x.words}</span><em className={tone(x.med)}>{pct(x.med)}</em><small>n {x.n}</small></li>)}</ul> : <small className="m-dim">Nothing judged yet — every reason starts as a belief and becomes its own record as calls are judged.</small>}</div>
      <AgentControls cfg={d.cfg} decisions={d.decisions} proven={d.proven5} isOwner={isOwner} busy={busy} save={save} />
    </div>
    <Tanks life={d.life} lessons={d.lessons} surviveN={d.surviveN || 30} scrapN={d.scrapN || 60} />
    <div className="agd-row2"><Edge d={d} /><AutopsyBox list={d.autopsies} signs={d.rugSigns} /></div>
    <CreedBox creed={d.creed} lineage={d.lineage} />
    <IdeaBox ideas={d.ideas} isOwner={isOwner} busy={busy} save={save} need={d.approveN || 15} />
    <MindBox m={d.mind} />
    <ThoughtFeed lines={d.thoughts} />
    <div className="agd-table" data-testid="agd-table"><div className="agd-th"><span>coin</span><span>📊 Tally</span><span>🔍 Sherlock</span><span>⏱ Trigger</span><span>⚖ Devil</span><span /></div>
      {(d.table || []).map(x => { const c = CALL[x.trigger[0]] || ['', '']; const v = VERDICT[x.devil[0]] || ['', ''];
        return <div key={x.mint} className={`agd-tr ${x.go ? 'is-go' : ''}`} data-testid={`agd-row-${x.symbol}`}>
          <button type="button" className="agd-sym" onClick={() => openCoin({ mint: x.mint, pairAddress: x.pair, symbol: x.symbol })}>${x.symbol}</button>
          <span className="agd-nums"><em className={tone(x.nums.d5)}>{pct(x.nums.d5)} 5m</em>{x.nums.pace != null ? ` · pace ${x.nums.pace}×` : ''}{x.nums.buy != null ? ` · ${Math.round(x.nums.buy)}% buys` : ''}</span>
          <span className="agd-why">{x.why.drivers.length ? x.why.drivers.slice(0, 2).map(dd => <i key={dd[0]} className={dd[1] >= 0 ? 'is-up' : 'is-dn'}>{dd[2]}</i>) : <i>nothing moving it</i>}</span>
          <span className={`agd-call ${c[1]}`} data-tip={x.trigger[1]}>{c[0]}</span>
          <span className={`agd-call ${v[1]}`} data-tip={x.devil[1] || ''}>{v[0]}{x.devil[1] && x.devil[0] === 'object' ? <small>{x.devil[1]}</small> : null}</span>
          <span className="agd-go">{x.go ? '🟢 GO' : ''}</span>
          {x.vitals && <span className="agd-vit" data-testid={`vit-${x.symbol}`}>{vitalCells(x.vitals).map(([k, v, bad]) => <i key={k} className={bad ? 'is-bad' : ''}><small>{k}</small>{v}</i>)}</span>}
          {x.opinion && <p className="agd-op" data-testid={`op-${x.symbol}`}>🗣 {x.opinion}{(x.strats || []).map(t => <i key={t}>🎯 {t}</i>)}</p>}
          {x.analysis?.text && <p className="agd-brief">{x.mind?.narr && <i>{x.mind.narr}{x.mind.hot ? ' 🔥' : ''}</i>}{x.mind?.swarm && <i className="is-bad">🤖 swarm</i>}{x.mind?.bots >= 40 && <i className="is-bad">🤖 botted</i>}{x.mind?.tug && <i>🪝 tuggers</i>}{x.analysis.text}</p>}</div>; })}
      {!(d.table || []).length && <small className="m-dim">The first pass runs within a minute of the backend starting.</small>}</div>
  </section>;
}

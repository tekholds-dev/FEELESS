import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { openCoin } from '../CoinDrawer';
import { openWarRoom } from '../WarRoomHost';
import '../../styles/agentDesk.css';
import { AgentRoom } from './AgentRoom';
import { pct, tone, CALL, VERDICT, VERD, rowState, rowWhy, pipsOf, leanFill } from '../../lib/agentRead';
import { MiniScreen, ZoomScreen, CardNow, CourtBand, MissionBar, GrowthCards, PowerLadder } from './AgentScreens';

export { rowState, rowWhy, pipsOf, leanFill };

// 🤖 HQ › AGENTS (owner, 2026-10-09: "code your own agents to learn trading and trenching — one tracks the numbers, one knows why they
// moved, one knows exactly when to enter, one argues it's right or not; none can work without the others; start by conquering the 5 min").
// GET /admin/agents (served from memory) every 20s + the moment the next pass is due. LAYOUT (owner, 2026-10-10: "cleaner, more interactive,
// meta all throughout"): hero (pass clock · stage) → KPI tiles (each jumps to its lens) → the office → the four agents as ONE picker (drives
// the office, the feed and the highlighted column) → ONE lens at a time: 🟢 Live (work floor · filterable coin board, a row opens every
// agent's word · thought feed) · 🧠 Learning · ⚔ Survival · ⚙ Control. `lens="all"` stacks every lens (tests). A record, never a promise.
const WHO = { tally: ['📊', 'Tally'], sherlock: ['🔍', 'Sherlock'], trigger: ['⏱', 'Trigger'], devil: ['⚖', 'Devil'], desk: ['🧾', 'Desk'], judge: ['👨‍⚖️', 'Judge'] };
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
    <ol>{steps.map(([ic, t, done, now]) => <li key={t} className={done ? 'is-done' : now ? 'is-now' : ''}><span>{done ? '✓' : ic}</span>{t}</li>)}</ol>
    <small className="agd-sugg" data-testid="agd-sugg">🤝 Their suggestions you took: {r.suggested?.n ? `${r.suggested.n} closed · ${r.suggested.med >= 0 ? '+' : ''}${r.suggested.med}% typical · ${r.suggested.won}% won` : 'none closed yet — picks from their alert are scored apart'}</small></div>;
}
// 🗯 LIVE: what the four said, newest first — the coin, who said it, how long ago. A desk line = a call that just got its 5-minute verdict.
export const FEED = [['all', 'All'], ['tally', '📊'], ['sherlock', '🔍'], ['trigger', '⏱'], ['devil', '⚖'], ['judge', '👨‍⚖️'], ['desk', '🧾']];
export function ThoughtFeed({ lines, who = 'all', setWho, onPick }) {
  const list = (lines || []).filter(l => who === 'all' || l.who === who).slice(0, 40);
  return <div className="agd-feed" data-testid="agd-thoughts"><div className="agd-feed-top"><b>🗯 LIVE — WHAT THEY'RE THINKING</b>
    {setWho && <div className="m-seg" role="group" aria-label="Whose words">{FEED.map(([k, l]) => <button key={k} type="button" className={who === k ? 'active' : ''} onClick={() => setWho(k)} data-tip={k === 'all' ? 'Everyone' : k === 'desk' ? 'Only the 5-minute verdicts' : k === 'judge' ? 'Only the Judge’s rulings' : `Only ${(WHO[k] || [])[1]}`} data-testid={`feed-${k}`}>{l}</button>)}</div>}</div>
    {list.length ? <ul>{list.map((l, i) => { const w = WHO[l.who] || ['•', l.who];
      return <li key={`${l.at}-${l.who}-${l.sym}-${i}`} className={`is-${l.who}`} style={{ '--i': Math.min(i, 8) }}><button type="button" className="agd-fl" onClick={() => onPick && l.sym && onPick(l.sym)} data-tip={l.sym ? `Open $${l.sym} on the board` : undefined}><span className="agd-who">{w[0]} {w[1]}</span><span className="agd-txt">{l.text}</span><small>{ago(l.at)}</small></button></li>; })}</ul>
      : <small className="m-dim">{(lines || []).length ? 'Nothing from them in the last passes.' : 'Their first words land within a minute.'}</small>}</div>;
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
    <div className="agd-ctl-row"><span>🎓 Agents' own seat (1 coin, real money — they suggest for the rest)</span><div className="m-seg"><button type="button" disabled={busy || !isOwner} className={c.agentLearn ? 'active' : ''} onClick={() => save({ cfg: { agentLearn: true } })} data-testid="agc-learn-on">ON</button><button type="button" disabled={busy || !isOwner} className={!c.agentLearn ? 'active' : ''} onClick={() => save({ cfg: { agentLearn: false } })} data-testid="agc-learn-off">off</button></div></div>
    {c.agentLearn && <div className="agd-ctl-row"><span>🤝 Trust them with a 2nd seat once your taken suggestions prove out (10+ closed, typical &gt; 0)</span><div className="m-seg"><button type="button" disabled={busy || !isOwner} className={c.agentTrust ? 'active' : ''} onClick={() => save({ cfg: { agentTrust: true } })} data-testid="agc-trust-on">ON</button><button type="button" disabled={busy || !isOwner} className={!c.agentTrust ? 'active' : ''} onClick={() => save({ cfg: { agentTrust: false } })} data-testid="agc-trust-off">off</button></div></div>}
    <div className="agd-ctl-row"><span data-tip="Once they have a scalp plan from their own paths, their seat banks at its take line (swap into the next GO, else cash) instead of your hold-until line. No stop is added.">⚡ Scalp their seat at the learned take line</span><div className="m-seg"><button type="button" disabled={busy || !isOwner} className={c.agentScalp !== false ? 'active' : ''} onClick={() => save({ cfg: { agentScalp: true } })} data-testid="agc-scalp-on">ON</button><button type="button" disabled={busy || !isOwner} className={c.agentScalp === false ? 'active' : ''} onClick={() => save({ cfg: { agentScalp: false } })} data-testid="agc-scalp-off">off</button></div></div>
    {c.agentLearn && <div className="agd-ctl-row"><span>Their seat size</span>{seg('agentLearnPct', [100, 15, 10, 5], v => v >= 100 ? 'whole seat' : `${v}% ticket`)}</div>}
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
  return <details open className="agd-box agd-creed" data-testid="agd-creed"><summary><b>📜 THE CREED · engraved in their code</b><small>{(lineage || []).length ? ` · ${lineage.length} scrapped li${lineage.length === 1 ? 'fe' : 'ves'}` : ' · no agent scrapped yet'}</small></summary>
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
export function WorkFloor({ d, onPick }) { const go = s => () => onPick && onPick(s);
  const f = floorOf(d); const p = d?.perf || {}; const ms = k => (p[k] != null ? `${p[k]} ms` : '—');
  return <div className="agd-floor" data-testid="agd-floor" key={p.at || 0}>
    <div className="agd-lane is-tally"><span className="agd-lane-h">📊 Tally <small>{f.dots.length} coins · {ms('tally')}</small></span><span className="agd-lane-b">{f.dots.map((x, i) => <i key={x.k} className={`agd-dot ${x.up ? 'is-up' : 'is-dn'}`} style={{ '--i': i }} data-tip={`$${x.sym}`} />)}</span></div>
    <div className="agd-lane is-sherlock"><span className="agd-lane-h">🔍 Sherlock <small>{ms('sherlock')}</small></span><span className="agd-lane-b">{f.tags.map(([w, n], i) => <i key={w} className="agd-tag" style={{ '--i': i }}>{w} ×{n}</i>)}{!f.tags.length && <small className="m-dim">no reasons this pass</small>}</span></div>
    <div className="agd-lane is-trigger"><span className="agd-lane-h">⏱ Trigger <small>{f.enters.length} ENTER · {ms('trigger')}</small></span><span className="agd-lane-b">{f.enters.map((x, i) => <button type="button" key={x.mint} className="agd-aim" style={{ '--i': i }} onClick={go(x.symbol)}>⌖ ${x.symbol}</button>)}{!f.enters.length && <small className="m-dim">nothing clean enough this pass</small>}</span></div>
    <div className="agd-lane is-devil"><span className="agd-lane-h">⚖ Devil <small>{ms('devil')}</small></span><span className="agd-lane-b">{f.verdicts.map((x, i) => <button type="button" key={x.sym} className={`agd-strike ${x.ok ? 'is-ok' : 'is-no'}`} style={{ '--i': i }} onClick={go(x.sym)}>{x.ok ? (x.go ? '🟢' : '✓') : '✕'} ${x.sym}</button>)}{!f.verdicts.length && <small className="m-dim">nothing to argue</small>}</span></div>
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
export const DivBar = ({ v, max = 10 }) => <span className="agd-div" aria-hidden><i className={Number(v) >= 0 ? 'is-up' : 'is-dn'} style={{ transform: `scaleX(${Math.min(1, Math.abs(Number(v) || 0) / max)})` }} /></span>;
export function Edge({ d }) {
  const cal = d?.calibration || {}; const rg = d?.perf?.regime;
  return <div className="agd-box agd-edge" data-testid="agd-edge"><b>🎯 CALIBRATION · does a stronger read win more?</b>
    {Object.keys(cal).length ? <ul className="agd-bars">{Object.entries(cal).map(([b, v]) => <li key={b}><span>lean {b}</span><DivBar v={v.med} /><em className={tone(v.med)}>{pct(v.med)}</em><small>{v.won}% up · n {v.n}</small></li>)}</ul> : <small className="m-dim">no ENTER judged yet</small>}
    <small className="m-dim">🌡 trench {rg ? `${rg.word}${rg.green != null ? ` (${rg.green}% green over 5 min)` : ''} → Trigger's bar ${rg.adj > 0 ? '+' : ''}${rg.adj}` : '—'} · 🔥 {d?.burned || 0} coin{d?.burned === 1 ? '' : 's'} burned (6h) · 🕸 {Object.keys(d?.cut || {}).length ? `budget cut: ${Object.keys(d.cut).join(', ')}` : 'no source cut yet'}</small></div>;
}
// 🔬 every rug the desk was on: what it read, what it missed — and the reasons that keep showing up in rugs (Devil objects to 2+ of them)
export function AutopsyBox({ list, signs }) {
  return <div className="agd-box agd-autopsy" data-testid="agd-autopsy"><b>🔬 RUG AUTOPSY · what we missed</b>
    {(list || []).length ? <ul>{list.map(a => <li key={a.id}>{a.text}{(a.missed || []).length ? <small> · missed: {a.missed.join(', ')}</small> : null}</li>)}</ul> : <small className="m-dim">no rug on the desk yet</small>}
    {(signs || []).length > 0 && <span className="agd-tags">{signs.map(x => <i key={x.key} className={x.n >= 3 ? 'is-bad' : ''}>☠ {x.words} ×{x.n}</i>)}</span>}</div>;
}
export const agentLine = a => (a.n ? `${a.n} judged · ${pct(a.med)} typical at 5 min${a.right != null ? ` · ${a.right}% right` : ''}` : 'no judged calls yet — every call is checked 5 minutes later');

// ⏱ THE PASS CLOCK — one pass a minute: how old the last one is, a bar filling to the next, and a re-read the moment it is due.
export const passLeft = (at, now, every = 60) => { if (!at) return null; const a = Math.max(0, now - at); return { age: Math.round(a), left: Math.max(0, Math.round(every - a)), frac: Math.min(1, a / every) }; };
export function PassClock({ at, onDue }) {
  const [now, setNow] = useState(() => Date.now() / 1000); const kicked = useRef(0);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now() / 1000); }, 1000); return () => clearInterval(t); }, []);
  const c = passLeft(at, now); const age = c ? c.age : 0;
  useEffect(() => { if (age >= 64 && age <= 150 && now - kicked.current > 8) {   /* a desk that is behind falls back to the 20s poll */ kicked.current = now; onDue && onDue(); } }, [age, now, onDue]);
  return <span className={`agd-clock ${c && c.age > 150 ? 'is-late' : ''}`} data-testid="agd-clock" data-tip="One pass a minute, any hour the backend is online. The tab re-reads the moment the next one is due.">
    <span className="agd-live" aria-hidden />{c ? (c.age > 150 ? `last pass ${ago(at)} ago — desk is behind` : c.left > 0 ? `pass ${c.age}s ago · next in ${c.left}s` : `pass ${c.age}s ago · reading the next…`) : 'waiting for the first pass'}
    <span className="agd-clock-bar" aria-hidden><i style={{ transform: `scaleX(${c ? c.frac : 0})` }} /></span></span>;
}

// 🪙 THE COIN BOARD — one line per coin: 5-min move · four pips (each agent's word, in chain order) · Sherlock's lean against Trigger's bar ·
// the verdict · the ONE fact that decided it. A row opens every agent's full word, the vitals, the written brief and the coin's chart.
export const BOARD = [['all', 'All'], ['go', '🟢 GO'], ['enter', '⌖ ENTER'], ['obj', '✕ Objected'], ['wait', 'WAIT'], ['skip', 'SKIP']];
export const SORTS = [['desk', "Desk's order"], ['lean', 'Strongest read'], ['d5', '5-min move'], ['vol', '1h volume']];
const inFilter = (x, f) => f === 'all' || (f === 'enter' ? x.trigger?.[0] === 'enter' : rowState(x) === f);
export const boardCounts = table => Object.fromEntries(BOARD.map(([k]) => [k, (table || []).filter(x => inFilter(x, k)).length]));
export const boardRows = (table, { f = 'all', q = '', sort = 'desk' } = {}) => { const s = q.trim().replace(/^\$/, '').toLowerCase();
  const rows = (table || []).filter(x => inFilter(x, f) && (!s || String(x.symbol || '').toLowerCase().includes(s) || String(x.mint || '').toLowerCase() === s));
  const key = { lean: x => Number(x.why?.lean) || 0, d5: x => Number(x.nums?.d5) || 0, vol: x => Number(x.vitals?.vol1h) || 0 }[sort];
  return key ? [...rows].sort((a, b) => key(b) - key(a)) : rows; };
const copyCa = m => { try { navigator.clipboard.writeText(m).then(() => toast.success('CA copied')); } catch (e) { toast.error('copy failed'); } };

function CoinRow({ x, bar, sel, open, toggle }) {
  const st = rowState(x); const c = CALL[x.trigger?.[0]] || ['—', '']; const v = VERDICT[x.devil?.[0]] || ['—', '']; const lean = Number(x.why?.lean) || 0; const dr = x.why?.drivers || [];
  return <div className={`agd-tr is-${st} ${open ? 'is-open' : ''}`} data-testid={`agd-row-${x.symbol}`}>
    <button type="button" className="agd-trh" aria-expanded={open} onClick={toggle} data-testid={`agd-open-${x.symbol}`}>
      <span className="agd-sym">${x.symbol}</span>
      <em className={`agd-d5 ${tone(x.nums?.d5)}`} key={String(x.nums?.d5)}>{pct(x.nums?.d5)}</em>
      <span className="agd-pips">{pipsOf(x).map(([k, ic, s, tip]) => <i key={k} className={`is-${s} ${sel === k ? 'is-sel' : ''}`} data-tip={tip}>{ic}</i>)}</span>
      <span className="agd-lean" data-tip={`Sherlock's lean ${lean.toFixed(1)} · the mark is Trigger's bar ${Number(bar || 1.5).toFixed(1)}`}><i className={lean >= 0 ? 'is-up' : 'is-dn'} style={{ transform: `scaleX(${leanFill(lean, bar)})` }} /><u /></span>
      <span className={`agd-verdict is-${st}`}>{VERD[st]}</span>
      <span className="agd-whyline">{rowWhy(x)}</span>
      <span className="agd-chev" aria-hidden>▾</span>
    </button>
    {open && <div className="agd-trb m-pop">
      <div className="agd-says">
        <div className="is-tally"><small>📊 Tally · the numbers</small><span className="agd-nums"><em className={tone(x.nums?.d5)}>{pct(x.nums?.d5)} 5m</em>{x.nums?.pace != null ? ` · pace ${x.nums.pace}×` : ''}{x.nums?.buy != null ? ` · ${Math.round(x.nums.buy)}% buys` : ''}</span></div>
        <div className="is-sherlock"><small>🔍 Sherlock · why · lean {lean.toFixed(1)}</small><span className="agd-why">{dr.length ? dr.slice(0, 5).map(dd => <i key={dd[0]} className={dd[1] >= 0 ? 'is-up' : 'is-dn'}>{dd[2]}</i>) : <i>nothing moving it</i>}</span></div>
        <div className="is-trigger"><small>⏱ Trigger · when</small><span><b className={`agd-call ${c[1]}`}>{c[0]}</b> {x.trigger?.[1] || ''}</span></div>
        <div className="is-devil"><small>⚖ Devil · argues</small><span><b className={`agd-call ${v[1]}`}>{v[0]}</b> {x.devil?.[1] || (x.trigger?.[0] === 'enter' ? '' : 'only ENTER calls are argued')}</span></div>
      </div>
      {x.vitals && <span className="agd-vit" data-testid={`vit-${x.symbol}`}>{vitalCells(x.vitals).map(([k, val, bad]) => <i key={k} className={bad ? 'is-bad' : ''}><small>{k}</small>{val}</i>)}</span>}
      {x.opinion && <p className="agd-op" data-testid={`op-${x.symbol}`}>🗣 {x.opinion}{(x.strats || []).map(t => <i key={t}>🎯 {t}</i>)}</p>}
      {x.analysis?.text && <p className="agd-brief">{x.mind?.narr && <i>{x.mind.narr}{x.mind.hot ? ' 🔥' : ''}</i>}{x.mind?.swarm && <i className="is-bad">🤖 swarm</i>}{x.mind?.bots >= 40 && <i className="is-bad">🤖 botted</i>}{x.mind?.tug && <i>🪝 tuggers</i>}{x.analysis.text}</p>}
      <div className="agd-acts"><button type="button" className="m-btn m-go" onClick={() => openCoin({ mint: x.mint, pairAddress: x.pair, symbol: x.symbol })} data-testid={`agd-coin-${x.symbol}`}>🪙 Open coin</button>
        {x.pair && <button type="button" className="m-btn" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: x.pair, baseToken: { address: x.mint, symbol: x.symbol } })} data-testid={`agd-chart-${x.symbol}`}>📈 Chart</button>}
        <button type="button" className="m-btn" onClick={() => copyCa(x.mint)}>⧉ Copy CA</button></div>
    </div>}
  </div>;
}

// 🟢 LIVE lens: the work floor, the coin board (filter · search · sort · open a row) and the thought feed. A feed line or a work-floor
// mark opens its coin on the board.
export function LiveLens({ d, sel, who, setWho, jump }) {
  const [f, setF] = useState('all'); const [q, setQ] = useState(''); const [sort, setSort] = useState('desk'); const [open, setOpen] = useState(null); const box = useRef(null);
  const counts = useMemo(() => boardCounts(d.table), [d.table]); const rows = useMemo(() => boardRows(d.table, { f, q, sort }), [d.table, f, q, sort]);
  const pick = useCallback(sym => { const x = (d.table || []).find(r => r.symbol === sym); if (!x) { toast(`$${sym} is not on this pass's board`); return; }
    setF('all'); setQ(''); setOpen(x.mint);
    setTimeout(() => { const el = box.current && box.current.querySelector(`[data-mint="${x.mint}"]`); if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, 60); }, [d.table]);
  const jumped = useRef(0);
  useEffect(() => { if (jump && jump.n !== jumped.current) { jumped.current = jump.n; pick(jump.sym); } }, [jump, pick]);   // a Judge ruling tapped above → its coin opens here
  return <div className="agd-livegrid" data-testid="lens-live-pane">
    <div className="agd-col">
      <WorkFloor d={d} onPick={pick} />
      <div className="agd-table" data-testid="agd-table" ref={box}>
        <div className="agd-tools"><div className="m-seg" role="group" aria-label="Filter the board">{BOARD.map(([k, l]) => <button key={k} type="button" className={f === k ? 'active' : ''} onClick={() => setF(k)} data-testid={`board-${k}`}>{l} <small>{counts[k]}</small></button>)}</div>
          <input className="m-input agd-q" value={q} onChange={e => setQ(e.target.value)} placeholder="🔎 $ticker" aria-label="Find a coin on the board" data-testid="board-q" />
          <select className="m-input agd-sort" value={sort} onChange={e => setSort(e.target.value)} aria-label="Sort the board" data-testid="board-sort">{SORTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
        <div className="agd-th" aria-hidden><span>coin</span><span>5 min</span><span>📊 🔍 ⏱ ⚖</span><span>lean</span><span>verdict</span><span>what decided it</span><span /></div>
        {rows.map(x => <div key={x.mint} data-mint={x.mint}><CoinRow x={x} bar={d.bar} sel={sel} open={open === x.mint} toggle={() => setOpen(open === x.mint ? null : x.mint)} /></div>)}
        {!rows.length && <small className="m-dim agd-none">{(d.table || []).length ? <>No coin matches — <button type="button" className="agd-link" onClick={() => { setF('all'); setQ(''); }} data-testid="board-reset">show all {(d.table || []).length}</button></> : 'The first pass runs within a minute of the backend starting.'}</small>}
      </div>
    </div>
    <ThoughtFeed lines={d.thoughts} who={who} setWho={setWho} onPick={pick} />
  </div>;
}

export const DIAL = [['chill', '🧊'], ['normal', '⚡'], ['crazy', '🔥 CRAZY']];
export const LENSES = [['live', '🟢 Live'], ['learn', '🧠 Learning'], ['life', '🧬 Growth'], ['ctl', '⚙ Control']];
const mem = { get: (k, dflt) => { try { return localStorage.getItem(k) || dflt; } catch (e) { return dflt; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } } };
const Kpi = ({ id, label, val, sub, cls, on, onClick, tip }) => <button type="button" className={`agd-kpi ${on ? 'active' : ''}`} onClick={onClick} data-tip={tip} data-testid={`kpi-${id}`}><small>{label}</small><b className={cls || ''} key={String(val)}>{val}</b><i>{sub}</i></button>;
// the ring on each agent = its share of right calls this life (Trigger: % of its ENTERs that won); empty until it has a judged call
const Ring = ({ v, icon }) => <span className="agd-ring" aria-hidden><svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="16" /><circle cx="20" cy="20" r="16" className={v == null ? 'is-none' : v >= 55 ? 'is-up' : v >= 45 ? 'is-mid' : 'is-dn'} strokeDasharray={`${Math.max(0, Math.min(100, v || 0))} 100`} pathLength="100" /></svg><b>{icon}</b></span>;

export function AgentDesk({ call, isOwner = true, lens: lens0 }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(false); const [sel, setSel] = useState('tally'); const [who, setWho] = useState('all'); const [zoom, setZoom] = useState(null); const [jump, setJump] = useState(null);
  const [lens, setLensS] = useState(() => lens0 || mem.get('feeless.agentLens', 'live')); const [office, setOffice] = useState(() => mem.get('feeless.agentOffice', 'on') !== 'off');
  const setLens = k => { setLensS(k); mem.set('feeless.agentLens', k); };
  const load = useCallback(() => call('/admin/agents').then(setD).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [load]);
  if (!d) return <p className="cc-empty">Waking the agents…</p>;
  const st = d.stage || {}; const t = d.table || []; const p = d.perf || {}; const rg = p.regime; const goN = t.filter(x => x.go).length; const enterN = t.filter(x => x.trigger?.[0] === 'enter').length;
  const newIdeas = (d.ideas || []).filter(i => i.status === 'new').length; const atRisk = Object.values(d.life || {}).filter(l => l && l.status && l.status !== 'alive').length;
  const pickAgent = k => { setSel(k); setWho(w => (w === k ? 'all' : k)); };
  const show = k => lens === 'all' || lens === k;
  const warLog = async () => { try { const r = await call('/admin/agents/log?hours=24'); const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([r.md], { type: 'text/markdown' })); a.download = `agent-war-log-${new Date().toISOString().slice(0, 10)}.md`; a.click(); URL.revokeObjectURL(a.href); } catch (e) { toast.error(e.message); } };
  const save = async body => { setBusy(true); try { await call('/admin/agents', { method: 'POST', body: JSON.stringify(body) }); toast.success(body.idea ? `💡 idea ${body.idea.action === 'approve' ? 'approved' : 'rejected'}` : '🤖 agent control saved'); load(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  const dial = d.cfg?.agentDial || 'normal';
  return <section className={`agd m-live is-dial-${dial}`} data-testid="agent-desk">
    <header className="agd-head"><div className="agd-title"><b data-tip="Four agents, one chain — none of them can call a trade without the other three. Every call is checked 5 minutes later.">🤖 THE AGENT DESK</b><PassClock at={p.at} onDue={load} />
</div>
      <div className="agd-stage" data-testid="agd-stage" data-tip={st.team?.n ? `team ${st.team.n}/${st.needN} judged · ${pct(st.team.med)} · ${st.team.won}% won (needs ${st.needWin}%)` : `needs ${st.needN} judged GO calls, a positive median and ${st.needWin}% won`}>{[5, 15, 60].map(h => <span key={h} className={(st.conquered || []).includes(h) ? 'is-done' : st.h === h ? 'is-now' : ''}>{(st.conquered || []).includes(h) ? '✓' : st.h === h ? '⚔' : '🔒'} {h}m</span>)}
</div>
      <div className="m-seg agd-dial" role="group" aria-label="How hard the agents trade" data-tip={`Your dial on Trigger's bar (now ${Number(d.barNow || d.bar || 1.5).toFixed(1)}): 🧊 pickier · 🔥 more entries. Hard skips (a +15% candle, a falling coin, a thin pool, a failed scan) and Devil's objections never move.`}>
        {DIAL.map(([k, l]) => <button key={k} type="button" disabled={busy || !isOwner} className={dial === k ? 'active' : ''} onClick={() => save({ cfg: { agentDial: k } })} data-testid={`dial-${k}`}>{l}</button>)}</div>
      <div className="agd-headacts"><button type="button" className="m-btn" onClick={() => { const on = !office; setOffice(on); mem.set('feeless.agentOffice', on ? 'on' : 'off'); }} aria-pressed={office} data-testid="agd-office">🏢 Office {office ? 'on' : 'off'}</button>
        <button type="button" className="m-btn" onClick={load} data-tip="Re-read the desk now (it is served from memory — no rate limit)" data-testid="agd-refresh">↻</button>
        <button type="button" className="m-btn agd-log" onClick={warLog} data-testid="agd-log">⬇ War log</button></div></header>
    <MissionBar mission={d.mission} scalp={d.scalp} desk={d.desk} />
    <div className="agd-kpis" data-testid="agd-kpis">
      <Kpi id="go" label="🟢 GO NOW" val={goN} cls={goN ? 'm-pos' : ''} sub={`${enterN} ENTER · ${p.coins ?? t.length} coins read`} on={show('live') && lens !== 'all'} onClick={() => setLens('live')} tip="Coins all four agree on this pass. Opens the live board." />
      <Kpi id="desk" label="📜 PAPER DESK" val={`$${d.desk.now.toFixed(2)}`} cls={tone(d.desk.now - d.desk.start)} sub={`${d.desk.x}× · ${d.desk.heat === 'heater' ? '🔥' : d.desk.heat === 'cold' ? '🧊' : ''} stake ${d.desk.stake ?? 25}%`} on={lens === 'ctl'} onClick={() => setLens('ctl')} tip="The team's $20 paper desk: 25% a GO, out at 5 minutes." />
      <Kpi id="road" label="🛣 ROAD TO REAL" val={`${d.road?.pct ?? 0}%`} sub={d.proven5 ? 'live on your card' : 'paper until the 10×'} on={lens === 'ctl'} onClick={() => setLens('ctl')} tip="How close the desk is to real money on your card." />
      <Kpi id="market" label="🌡 TRENCH" val={rg?.green != null ? `${rg.green}%` : '—'} sub={`green 5m · ${rg?.word || 'unknown'}`} on={lens === 'learn'} onClick={() => setLens('learn')} tip="Share of coins green over 5 minutes. It moves Trigger's bar." />
      <Kpi id="ideas" label="💡 IDEAS" val={newIdeas} cls={newIdeas ? 'agd-warn' : ''} sub={newIdeas ? 'waiting for your review' : 'nothing to review'} on={lens === 'learn'} onClick={() => setLens('learn')} tip="Tactics the desk found in its own record." />
      <Kpi id="lives" label="⚔ LIVES" val={atRisk ? `${atRisk} ⚠` : '4 🟢'} cls={atRisk ? 'agd-warn' : ''} sub={atRisk ? 'on probation / scrapped' : `${(d.lineage || []).length} scrapped so far`} on={lens === 'life'} onClick={() => setLens('life')} tip="An agent that keeps losing is scrapped and reborn." />
    </div>
    <CardNow card={d.card} power={d.power} cfg={d.cfg} gos={t.filter(x => x.go)} call={call} isOwner={isOwner} onDone={load} onMore={() => setLens('life')} />
    <CourtBand judge={d.judge} proof={d.proof} desk={d.desk} onPick={sym => { setLens('live'); setJump({ sym, n: Date.now() }); }} onCourt={() => setZoom('judge')} />
    {office && <AgentRoom d={d} sel={sel} onSel={setSel} picker={false} />}
    <div className="agd-chain" role="group" aria-label="Pick an agent"><i className="agd-wire" aria-hidden><u /></i>{(d.agents || []).map((a, i) => { const l = d.life?.[a.key];
      const g = d.growth?.[a.key];
      return <div key={a.key} className={`agd-agent is-${a.key} ${sel === a.key ? 'is-on' : ''}`} style={{ '--i': i }}>
        <button type="button" className="agd-ahead" aria-pressed={sel === a.key} onClick={() => pickAgent(a.key)} data-tip={`${a.job} · ${agentLine(a)}`} data-testid={`agent-${a.key}`}>
          <Ring v={a.n ? (a.right != null ? a.right : a.med > 0 ? 60 : 40) : null} icon={a.icon} />
          <span className="agd-aname"><b>{a.name}</b><small>{g ? `${g.icon} ${g.name} · gen ${g.gen}` : a.job}</small></span>
          <em className={tone(a.med)}>{a.n ? pct(a.med) : '—'}</em></button>
        {(d.judge?.mvp === a.key || d.judge?.trial === a.key) && <span className={`agd-mark ${d.judge.trial === a.key ? 'is-trial' : 'is-mvp'}`} data-tip={d.judge.trial === a.key ? `The Judge has it on trial: ${d.judge.handicap}` : 'The Judge’s 👑: best net over the last rulings'} data-testid={`mark-${a.key}`}>{d.judge.trial === a.key ? '🔨 TRIAL' : '👑 MVP'}</span>}
        <button type="button" className="ags-mini" onClick={() => { setSel(a.key); setZoom(a.key); }} aria-label={`Zoom into ${a.name}'s screen`} data-testid={`screen-${a.key}`}><MiniScreen key={p.at || 0} k={a.key} d={d} /><span className="ags-hint" aria-hidden>⤢</span></button>
        <span className="agd-afoot"><span className="agd-task" data-tip={d.tasks?.[a.key]} data-testid={`task-${a.key}`}>{d.tasks?.[a.key] || 'waiting for the first pass'}</span>
          {l && <span className={`agd-life is-${l.status}`} data-testid={`life-${a.key}`}>gen {l.gen} · {l.status === 'alive' ? '🟢 alive' : l.status === 'probation' ? '⚠ probation' : '☠ being scrapped'}</span>}
          {p[a.key] != null && <small className="agd-ms" data-testid={`ms-${a.key}`}>⚡ {p[a.key]} ms this pass</small>}</span></div>; })}</div>
    {zoom && <ZoomScreen d={d} agent={zoom} setAgent={k => { setZoom(k); setSel(k); }} close={() => setZoom(null)} />}
    {lens !== 'all' && <div className="m-seg agd-lens" role="tablist" aria-label="Agent desk lens">{LENSES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`lens-${k}`}>{l}{k === 'live' && goN ? <small>{goN} GO</small> : k === 'learn' && newIdeas ? <small>{newIdeas} 💡</small> : k === 'life' && atRisk ? <small>{atRisk} ⚠</small> : null}</button>)}</div>}
    {show('live') && <LiveLens d={d} sel={sel} who={who} setWho={setWho} jump={jump} />}
    {show('learn') && <div className="agd-grid" data-testid="lens-learn-pane">
      <div className="agd-box" data-testid="agd-drivers"><b>🔍 WHAT SHERLOCK LEARNED · each reason's own 5-min record</b>{(d.drivers || []).length ? <ul className="agd-bars">{d.drivers.slice(0, 9).map(x => <li key={x.key}><span>{x.words}</span><DivBar v={x.med} /><em className={tone(x.med)}>{pct(x.med)}</em><small>n {x.n}</small></li>)}</ul> : <small className="m-dim">Nothing judged yet — every reason starts as a belief and becomes its own record as calls are judged.</small>}</div>
      <Edge d={d} /><MindBox m={d.mind} />
      <div className="agd-wide"><IdeaBox ideas={d.ideas} isOwner={isOwner} busy={busy} save={save} need={d.approveN || 15} /></div></div>}
    {show('life') && <div className="agd-grid" data-testid="lens-life-pane">
      <div className="agd-wide"><GrowthCards growth={d.growth} agents={d.agents} hist={d.hist} onZoom={setZoom} /></div>
      <div className="agd-wide"><PowerLadder power={d.power} /></div>
      <div className="agd-box agd-wide"><b>🧪 THE TANKS · the next generation waits — the water rises with real danger</b><Tanks life={d.life} lessons={d.lessons} surviveN={d.surviveN || 30} scrapN={d.scrapN || 60} /></div>
      <AutopsyBox list={d.autopsies} signs={d.rugSigns} /><CreedBox creed={d.creed} lineage={d.lineage} /></div>}
    {show('ctl') && <div className="agd-grid is-ctl" data-testid="lens-ctl-pane">
      <div className="agd-wide"><RoadMeter road={d.road} /></div>
      <div className="agd-box" data-testid="agd-desk"><b>📜 TRENCH DESK · 25% a GO, out at 5 min · goal 10×</b><p className={`agd-big ${tone(d.desk.now - d.desk.start)}`}>${d.desk.now.toFixed(2)} <small>{d.desk.x}× of ${d.desk.start} · best run {d.desk.best}× · {d.desk.busts} bust{d.desk.busts === 1 ? '' : 's'} · {d.desk.trades} trades</small></p>
        <span className="agd-road-bar" aria-hidden><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, Math.log10(Math.max(1, d.desk.x || 1))))})` }} /></span>
        <small className="m-dim">Control group (coins Trigger said WAIT): {d.control?.n ? `${pct(d.control.med)} typical` : 'not judged yet'} — the team must beat this to mean anything. Slippage on a 5-min scalp is not modelled.</small></div>
      <AgentControls cfg={d.cfg} decisions={d.decisions} proven={d.proven5} isOwner={isOwner} busy={busy} save={save} /></div>}
  </section>;
}

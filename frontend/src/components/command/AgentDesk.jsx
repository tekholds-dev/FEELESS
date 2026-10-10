import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { openCoin } from '../CoinDrawer';
import '../../styles/agentDesk.css';

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
export const agentLine = a => (a.n ? `${a.n} judged · ${pct(a.med)} typical at 5 min${a.right != null ? ` · ${a.right}% right` : ''}` : 'no judged calls yet — every call is checked 5 minutes later');

export function AgentDesk({ call, isOwner = true }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(false);
  const load = useCallback(() => call('/admin/agents').then(setD).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [load]);
  if (!d) return <p className="cc-empty">Waking the agents…</p>;
  const st = d.stage || {};
  const save = async body => { setBusy(true); try { await call('/admin/agents', { method: 'POST', body: JSON.stringify(body) }); toast.success(body.idea ? `💡 idea ${body.idea.action === 'approve' ? 'approved' : 'rejected'}` : '🤖 agent control saved'); load(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <section className="agd m-live" data-testid="agent-desk">
    <header className="agd-head"><div><b>🤖 THE AGENT DESK</b><small>Four agents, one chain — none of them can call a trade without the other three. Every call is checked 5 minutes later; they move to 15 min only after they conquer 5.</small></div>
      <div className="agd-stage" data-testid="agd-stage">{[5, 15, 60].map(h => <span key={h} className={(st.conquered || []).includes(h) ? 'is-done' : st.h === h ? 'is-now' : ''}>{(st.conquered || []).includes(h) ? '✓' : st.h === h ? '⚔' : '🔒'} {h}m</span>)}
        <small>{st.team?.n ? `team ${st.team.n}/${st.needN} judged · ${pct(st.team.med)} · ${st.team.won}% won (needs ${st.needWin}%)` : `needs ${st.needN} judged GO calls, a positive median and ${st.needWin}% won`}</small></div></header>
    <RoadMeter road={d.road} />
    <div className="agd-chain">{(d.agents || []).map((a, i) => <React.Fragment key={a.key}><div className={`agd-agent is-${a.key}`} style={{ '--i': i }} data-testid={`agent-${a.key}`}>
      <span className="agd-ico" aria-hidden>{a.icon}</span><b>{a.name}</b><small>{a.job}</small>
      {d.life?.[a.key] && <span className={`agd-life is-${d.life[a.key].status}`} data-testid={`life-${a.key}`}>gen {d.life[a.key].gen} · {d.life[a.key].status === 'alive' ? '🟢 alive' : d.life[a.key].status === 'probation' ? '⚠ probation' : '☠ being scrapped'}</span>}
      <em className={tone(a.med)}>{a.n ? pct(a.med) : '—'}</em><i>{agentLine(a)}</i>
      <span className="agd-task" data-testid={`task-${a.key}`}><span className="agd-live" aria-hidden />{d.tasks?.[a.key] || 'waiting for the first pass'}</span><span className="agd-scan" aria-hidden><u /></span></div>{i < 3 && <span className="agd-arrow" aria-hidden>→</span>}</React.Fragment>)}</div>
    <small className="m-dim agd-pass">last pass {d.tasks?.at ? `${ago(d.tasks.at)} ago` : '—'} · one a minute, any hour the backend is online</small>
    <div className="agd-row2">
      <div className="agd-box" data-testid="agd-desk"><b>📜 TRENCH DESK · 25% a GO, out at 5 min · goal 10×</b><p className={`agd-big ${tone(d.desk.now - d.desk.start)}`}>${d.desk.now.toFixed(2)} <small>{d.desk.x}× of ${d.desk.start} · best run {d.desk.best}× · {d.desk.busts} bust{d.desk.busts === 1 ? '' : 's'} · {d.desk.trades} trades</small></p>
        <small className="m-dim">Control group (coins Trigger said WAIT): {d.control?.n ? `${pct(d.control.med)} typical` : 'not judged yet'} — the team must beat this to mean anything. Slippage on a 5-min scalp is not modelled.</small></div>
      <div className="agd-box" data-testid="agd-drivers"><b>🔍 WHAT SHERLOCK LEARNED</b>{(d.drivers || []).length ? <ul>{d.drivers.slice(0, 7).map(x => <li key={x.key}><span>{x.words}</span><em className={tone(x.med)}>{pct(x.med)}</em><small>n {x.n}</small></li>)}</ul> : <small className="m-dim">Nothing judged yet — every reason starts as a belief and becomes its own record as calls are judged.</small>}</div>
      <AgentControls cfg={d.cfg} decisions={d.decisions} proven={d.proven5} isOwner={isOwner} busy={busy} save={save} />
    </div>
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

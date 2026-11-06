import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { fitBox, identityOf, ridge } from '../../lib/proofprint';
import { blankRidges, GAME_RINGS, gameSegments, gradeMarks, marketReads, penAt, printStage, shotPoint, SIDE_INK, statLine, statRidges } from '../../lib/gamePrint';
import { ProChart } from './ProChart';
import '../../styles/proofTools.css';
import '../../styles/gameRoom.css';

// 🏟 ONE GAME'S ROOM (owner 2026-11-05). Left: how often each side wins, the line, and the team and player prints built from this season against last. Right: the plays with the live print, the edge vitals, the players and the stats.
// Every number comes from ESPN, Polymarket or Kalshi. A vital is a reading of a real number, never a promise. The final print appears only after the final horn and the grades. Read docs/HANDOFF.md before changing how a print is drawn.
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
export const until = at => { const s = (new Date(at).getTime() - Date.now()) / 1000; if (!Number.isFinite(s)) return ''; if (s < 0) return 'now'; if (s < 3600) return `${Math.ceil(s / 60)}m`; if (s < 86400) return `${Math.round(s / 3600)}h`; return `${Math.round(s / 86400)}d`; };

// A team's mark: its logo from ESPN, or its letters drawn when it has none.
export function TeamMark({ t, size = 28 }) {
  const [bad, setBad] = useState(false); const label = String(t?.abbr || t?.short || t?.name || '?').slice(0, 3).toUpperCase();
  return t?.logo && !bad ? <img className="grm-logo" src={t.logo} alt="" width={size} height={size} loading="lazy" decoding="async" onError={() => setBad(true)} /> : <i className="grm-logo is-letters" style={{ width: size, height: size, fontSize: size * 0.34 }} aria-hidden="true">{label}</i>;
}
function Versus({ label, a, b, tip, pctRow }) {
  const na = parseFloat(a); const nb = parseFloat(b); const top = Math.max(Math.abs(na) || 0, Math.abs(nb) || 0) || 1; const fa = pctRow ? na : (Math.abs(na) || 0) / top; const fb = pctRow ? nb : (Math.abs(nb) || 0) / top;
  const show = v => (pctRow ? (Number.isFinite(v) ? `${Math.round(v * 100)}%` : '—') : (v ?? '—'));
  return <li className="pgw-vs" data-tip={tip}><b className="m-num">{show(pctRow ? na : a)}</b><span className="pgw-vbar is-a" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, Math.min(1, fa || 0))})` }} /></span><small>{label}</small><span className="pgw-vbar is-b" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, Math.min(1, fb || 0))})` }} /></span><b className="m-num">{show(pctRow ? nb : b)}</b></li>;
}
const Form = ({ rows }) => (rows?.length ? <span className="pgw-form" aria-label={`Last ${rows.length} games: ${rows.join(' ')}`}>{rows.map((r, i) => <i key={i} className={r === 'W' ? 'is-w' : r === 'L' ? 'is-l' : ''}>{r}</i>)}</span> : null);

// 🧬 A team's or player's print: one ridge per stat, last season on one half, this season on the other. Hover a ridge to read it.
function StatPrint({ seed, title, sub, rows, onClear }) {
  const [hot, setHot] = useState(null); const id = useMemo(() => identityOf(seed), [seed]); const lines = useMemo(() => statRidges(seed, rows), [seed, rows]); const n = lines.length ? lines[lines.length - 1].j + 2 : 8; const on = lines[hot];
  return <figure className="grm-sp" data-testid={`grm-print-${seed}`}><figcaption><b>{title}</b>{onClear ? <button type="button" className="grm-sp-x" onClick={onClear} aria-label="Back to the teams" data-tip="Back to the teams">✕</button> : null}</figcaption>
    {rows ? <svg viewBox={fitBox(n, id)} role="img" aria-label={`${title}, ${lines.length} stats, this season against last`} onMouseLeave={() => setHot(null)}>{lines.map((l, i) => <g key={l.abbr} className={hot === i ? 'is-hot' : ''}>{l.last ? <path d={l.last} className="is-last" /> : null}<path d={l.now} stroke={l.ink} className="is-now" style={{ '--i': i }} /><path d={l.now} className="is-hit" onMouseEnter={() => setHot(i)} /></g>)}</svg> : <span className="grm-sp-load" aria-label="Reading its stats"><svg viewBox={fitBox(8, id)} aria-hidden="true">{[2, 4, 6, 8].map(j => <path key={j} d={ridge(id, j, 30)} className="is-last" />)}</svg></span>}
    <small className="m-num">{on ? statLine(on) : rows?.length ? (sub || 'Hover a ridge') : rows ? 'No stats yet' : 'Reading…'}</small></figure>;
}
function useStatPrint(kind, sport, xid) {
  const [rows, setRows] = useState(null);
  useEffect(() => { if (!xid) return undefined; let on = true; setRows(null); fetch(apiUrl(`/api/cats/tools/print/${kind}/${sport}/${xid}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => on && setRows(j.rows || [])).catch(() => on && setRows([])); return () => { on = false; }; }, [kind, sport, xid]);
  return rows;
}
// Under the line, total and venue: both teams, or the player you tapped next to their team's.
function PrintShelf({ sport, teams, player, onClear }) {
  const a = useStatPrint('team', sport, teams[0]?.id); const b = useStatPrint('team', sport, teams[1]?.id); const p = useStatPrint('player', sport, player?.id);
  return <section className="grm-shelf" data-testid="grm-shelf"><h5>PRINTS <small>this season against last. Tap a player to print them</small></h5><div>
    {player ? <StatPrint seed={`player:${player.id}`} title={player.name} sub={player.team} rows={p} onClear={onClear} /> : <StatPrint seed={`team:${teams[0]?.id}`} title={teams[0]?.abbr || teams[0]?.name} rows={a} />}
    <StatPrint seed={`team:${teams[1]?.id}`} title={teams[1]?.abbr || teams[1]?.name} rows={b} /></div></section>;
}

// 🧬 THE GAME'S PRINT. Each play inks a stretch of ridge at its spot on the game clock, from the core out. The final print waits for the final horn and the grades.
function GamePrint({ seed, plays, stage, calls, score }) {
  const id = useMemo(() => identityOf(seed), [seed]); const segs = useMemo(() => gameSegments(seed, plays), [seed, plays]); const seen = useRef(null); const at = plays?.length ? Math.max(...plays.map(p => p.at || 0)) : 0;
  const reached = segs.length ? Math.max(...segs.map(s => s.ring)) : -1; const blanks = useMemo(() => blankRidges(seed, stage === 'final' ? GAME_RINGS : reached + 1), [seed, reached, stage]); const pen = stage === 'live' && plays?.length ? penAt(seed, at) : null; const marks = useMemo(() => (stage === 'final' ? gradeMarks(seed, calls) : []), [seed, calls, stage]);
  const fresh = new Set(); if (seen.current) segs.forEach(s => { if (!seen.current.has(s.id)) fresh.add(s.id); }); useEffect(() => { seen.current = new Set(segs.map(s => s.id)); }, [segs]);
  const say = { pre: 'It starts at the first play', live: `Building: ${plays?.length || 0} plays inked`, grading: 'Game over. Waiting on the grades before it seals', final: calls?.length ? `Sealed. ${calls.filter(c => c.won).length} of ${calls.length} agent calls right` : 'Sealed. No agent called this game' }[stage];
  return <figure className={`grm-gp is-${stage}`} data-testid="grm-game-print" data-stage={stage}><span className="grm-gp-tag">{stage === 'live' ? <em className="ptl-live">LIVE PRINT</em> : stage === 'final' ? <em className="is-final">FINAL PRINT</em> : stage === 'grading' ? <em>NOT FINAL YET</em> : <em>NO PLAYS YET</em>}</span>
    <svg viewBox={fitBox(GAME_RINGS * 2 + 4, id)} role="img" aria-label={say}><g className="grm-gp-blank">{blanks.map((d, i) => <path key={i} d={d} />)}</g>{segs.map(s => <path key={s.id} d={s.d} stroke={s.ink} strokeWidth={s.w} className={`${s.bright ? 'is-bright' : ''}${fresh.has(s.id) ? ' is-new' : ''}`} />)}{marks.map((m, i) => <path key={i} d={m.d} stroke={m.ink} className="grm-gp-mark" />)}{pen ? <g className="grm-gp-pen" transform={`translate(${pen[0]} ${pen[1]})`}><circle r="9" /><circle r="4" className="is-core" /></g> : null}</svg>
    <figcaption><small className="m-num">{say}</small>{stage === 'final' && score ? <b className="m-num">{score}</b> : null}</figcaption></figure>;
}

// 🏀 The floor, drawn. Every real shot with a spot from ESPN: filled made, hollow missed, in its side's ink, the newest one pulsing.
function Court({ plays }) {
  const shots = useMemo(() => (plays || []).filter(p => p.x != null), [plays]); if (!shots.length) return null; const last = shots[shots.length - 1]; const made = s => shots.filter(x => x.side === s && x.made).length; const all = s => shots.filter(x => x.side === s).length;
  return <figure className="grm-court" data-testid="grm-court"><svg viewBox="0 0 188 100" role="img" aria-label={`Shot chart, ${shots.length} shots`}>
    <g className="grm-floor"><rect x="1" y="1" width="186" height="98" rx="3" /><line x1="94" y1="1" x2="94" y2="99" /><circle cx="94" cy="50" r="11" /><rect x="1" y="33" width="29" height="34" /><rect x="158" y="33" width="29" height="34" /><circle cx="30" cy="50" r="10" /><circle cx="158" cy="50" r="10" /><path d="M1 8 H17 A44 44 0 0 1 17 92 H1" /><path d="M187 8 H171 A44 44 0 0 0 171 92 H187" /></g>
    {shots.map(s => { const [x, y] = shotPoint(s); return <circle key={s.id} cx={x} cy={y} r="1.5" fill={s.made ? SIDE_INK[s.side] : 'none'} stroke={SIDE_INK[s.side] || '#8a93a6'} strokeWidth=".5" opacity={s.made ? 0.95 : 0.55} />; })}
    {(() => { const [x, y] = shotPoint(last); return <circle className="grm-court-now" cx={x} cy={y} r="3.2" stroke={SIDE_INK[last.side] || '#fff'} />; })()}</svg>
    <figcaption className="m-num"><span style={{ color: SIDE_INK.a }}>{made('a')}/{all('a')}</span><small>made, shots with a spot</small><span style={{ color: SIDE_INK.b }}>{made('b')}/{all('b')}</span></figcaption></figure>;
}

// 📣 The play by play, newest first: what happened, when, the score, and the win chance when it moved.
const headOf = p => (p.pts ? `+${p.pts} Point${p.pts === 1 ? '' : 's'}` : `${p.shot && !p.made ? 'Missed ' : ''}${String(p.type || '').replace(/([a-z])([A-Z])/g, '$1 $2').replace(p.shot && !p.made ? /^Made /i : /^$/, '')}`);
function Plays({ d, stage, calls, seed }) {
  const plays = d.plays || []; const ta = d.teams[0]; const tb = d.teams[1]; const by = { a: ta, b: tb }; const rows = plays.filter(p => p.text != null).slice().reverse(); const top = rows[0]; const home = tb?.abbr || 'HOME';
  const scoreLine = plays.length ? `${ta?.abbr} ${plays[plays.length - 1].a} – ${plays[plays.length - 1].b} ${tb?.abbr}` : null;
  return <section className="grm-plays" data-testid="grm-plays"><div className="grm-stage"><GamePrint seed={seed} plays={plays} stage={stage} calls={calls} score={scoreLine} /><Court plays={plays} /></div>
    {top ? <header className={`grm-hero is-${top.side || 'none'}${top.pts ? ' is-score' : ''}`} key={top.id}><b>{headOf(top)}</b><small className="m-num">{top.clock} · {top.perName || `P${top.per}`}</small></header> : null}
    {calls?.length ? <ul className="grm-calls" data-testid="grm-calls">{calls.map((c, i) => <li key={i} className={c.won === true ? 'is-up' : c.won === false ? 'is-dn' : ''}><b>{c.agent}</b> called {c.pick} <em>{c.won === true ? 'RIGHT' : c.won === false ? 'WRONG' : 'OPEN'}</em></li>)}</ul> : null}
    {rows.length ? <ol className="grm-feed">{rows.map((p, i) => { const prev = rows[i + 1]; const up = p.wp != null && prev?.wp != null ? p.wp - prev.wp : 0; return <li key={p.id} className={`${p.pts ? 'is-score' : ''}${i === 0 ? ' is-new' : ''}`}><span className="grm-feed-m">{by[p.side] ? <TeamMark t={by[p.side]} size={22} /> : <i className="grm-feed-dot" />}</span><span className="grm-feed-t"><b>{headOf(p)}</b><small className="m-num">{p.clock} · {p.perName || `P${p.per}`}</small><span>{p.text}</span></span><span className="grm-feed-s"><b className="m-num">{p.a} <i>{p.b}</i></b>{p.wp != null ? <small className="m-num">{p.wp >= 0.5 ? home : ta?.abbr} {(Math.max(p.wp, 1 - p.wp) * 100).toFixed(1)}%{up ? <em className={(p.wp >= 0.5) === (up > 0) ? 'is-up' : 'is-dn'}>{(p.wp >= 0.5) === (up > 0) ? ' ▲' : ' ▼'}</em> : null}</small> : null}</span></li>; })}</ol> : <p className="ptl-none">ESPN has not posted a play yet.</p>}</section>;
}

// 🎯 The edge vitals. Each one is a real number; "Prove it" hands it to the agent as a PoB to test.
const VITAL_READ = { '': 'grm-read', a: 'grm-read is-a', b: 'grm-read is-b' };
function Meter({ v, top, tone = '' }) { return <span className={`grm-meter ${tone}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, Math.abs(v) / (top || 1)))})` }} /></span>; }
function Vital({ title, tip, children, wide }) { return <article className={`grm-v${wide ? ' is-wide' : ''}`} data-tip={tip}><h6>{title}</h6>{children}</article>; }
function Edge({ d, a, b, onCommand }) {
  const e = d.edge || {}; const ta = d.teams[0]; const tb = d.teams[1]; const nm = { a: ta?.abbr, b: tb?.abbr }; const reads = [...(d.reads || []), ...marketReads(e, a, b)]; const pick = `${a.short || a.name} vs ${b.short || b.name}`; const inj = [ta, tb].filter(t => t?.injuries?.length);
  const mv = e.moves || {}; const fo = e.form || {};
  return <div className="grm-edge" data-testid="grm-edge">
    <Vital wide title="READS" tip="What the real numbers say right now. Not a promise and not a tip">{reads.length ? <ul className="grm-reads">{reads.map(r => <li key={r.k} className={VITAL_READ[r.tone || '']}><small>{r.k}</small><span>{r.text}</span>{onCommand ? <button type="button" className="m-btn" onClick={() => onCommand(`file a pob ${pick}. Test this: ${r.text}`)} data-tip="Puts it in the chat box for the agent to test. You press send" data-testid={`grm-prove-${r.k}`}>Prove it</button> : null}</li>)}</ul> : <p className="ptl-none">Nothing stands out in the numbers yet.</p>}</Vital>
    {e.crew?.length ? <Vital title="OFFICIALS" tip="Who is working this game, from ESPN. Their past records are not in the free data">{<ul className="grm-list">{e.crew.map(c => <li key={c.name}><b>{c.name}</b><small>{c.role}</small></li>)}</ul>}</Vital> : null}
    {mv.spread || mv.total || e.ml ? <Vital title={`LINE${e.ml?.by ? ` · ${e.ml.by}` : ''}`} tip="Where the line opened and where it is now">{<dl className="grm-kv">{mv.spread ? <div><dt>Spread</dt><dd className="m-num">{mv.spread.open} → <b>{mv.spread.now}</b></dd></div> : null}{mv.total ? <div><dt>Total</dt><dd className="m-num">{mv.total.open} → <b>{mv.total.now}</b></dd></div> : null}{e.ml?.a != null ? <div><dt>Money</dt><dd className="m-num">{nm.a} {e.ml.a > 0 ? '+' : ''}{e.ml.a} · {nm.b} {e.ml.b > 0 ? '+' : ''}{e.ml.b}</dd></div> : null}</dl>}</Vital> : null}
    {e.pace ? <Vital title="PACE AND THE TOTAL" tip="Points so far stretched over the whole game. Early numbers swing a lot"><p className="grm-big m-num">{e.pace.proj}<small> against {e.pace.total ?? 'no total'}</small></p>{e.pace.total ? <Meter v={e.pace.proj} top={Math.max(e.pace.proj, e.pace.total)} tone={e.pace.proj > e.pace.total ? 'is-up' : 'is-dn'} /> : null}<small className="grm-note">{Math.round(e.pace.at * 100)}% of the game played</small></Vital> : null}
    {e.run?.pts >= 4 ? <Vital title="SCORING RUN" tip="Points in a row by one side, from the play by play"><p className="grm-big m-num" style={{ color: SIDE_INK[e.run.side] }}>{e.run.pts}–0<small> {nm[e.run.side]}</small></p></Vital> : null}
    {fo.a || fo.b ? <Vital title="LAST GAMES AND REST" tip="From each side's last games. Their opponents differ">{<table className="grm-t"><thead><tr><th /><th>W-L</th><th>Margin</th><th>Points</th><th>Rest</th></tr></thead><tbody>{['a', 'b'].filter(s => fo[s]).map(s => <tr key={s}><th scope="row">{nm[s]}</th><td className="m-num">{fo[s].w}-{fo[s].l}</td><td className="m-num">{fo[s].margin > 0 ? '+' : ''}{fo[s].margin ?? '—'}</td><td className="m-num">{fo[s].ppg ?? '—'}</td><td className="m-num">{fo[s].restDays != null ? `${fo[s].restDays}d` : '—'}</td></tr>)}</tbody></table>}</Vital> : null}
    {e.hot?.length ? <Vital title="HOT AND COLD" tip="Tonight or their last games, against their own season. Only the biggest roles">{<ul className="grm-hot">{e.hot.map(h => <li key={h.name} className={h.hot ? 'is-up' : 'is-dn'}><span><b>{h.name}</b><small className="m-num">{nm[h.side]} · {h.recent} {h.stat} {h.how}, {h.season} on the season</small></span><em className="m-num">{h.hot ? '+' : ''}{h.pct}%</em><Meter v={h.pct} top={100} tone={h.hot ? 'is-up' : 'is-dn'} /></li>)}</ul>}</Vital> : null}
    {e.fouls?.length ? <Vital title="FOUL TROUBLE" tip="Four fouls or more right now">{<ul className="grm-list">{e.fouls.map(x => <li key={x.name}><b style={{ color: SIDE_INK[x.side] }}>{x.name}</b><small className="m-num">{x.pf} fouls · {x.pts ?? 0} pts</small></li>)}</ul>}</Vital> : null}
    {e.flow?.length ? <Vital title="HOW THE GAME IS GOING" tip="ESPN's box, now"><ul className="pgw-vss">{e.flow.map(x => <Versus key={x.label} label={x.label} a={x.a} b={x.b} />)}</ul></Vital> : null}
    {e.model ? <Vital title="ESPN'S MODEL" tip="ESPN's own prediction, not ours"><ul className="pgw-vss"><Versus pctRow label="Win chance" a={e.model.a} b={e.model.b} /></ul></Vital> : null}
    {e.ats ? <Vital title="AGAINST THE SPREAD" tip="How each side has done against the line this season">{<ul className="grm-list">{['a', 'b'].filter(s => e.ats[s]).map(s => <li key={s}><b>{nm[s]}</b><small className="m-num">{e.ats[s].map(r => r.v).join(' · ')}</small></li>)}</ul>}</Vital> : null}
    {e.weather ? <Vital title="WEATHER" tip="At the venue, from ESPN"><p className="grm-big m-num">{e.weather.temp}°<small> gust {e.weather.gust ?? 0} · rain {e.weather.rain ?? 0}%</small></p></Vital> : null}
    {inj.length ? <Vital wide title="INJURIES" tip="ESPN's list"><div className="pgw-two">{inj.map(t => <ol key={t.id} className="pgw-pl"><li className="pgw-pl-h">{t.abbr}</li>{t.injuries.map(l => <li key={l.name}><span><b>{l.name}</b></span><small>{l.status}</small></li>)}</ol>)}</div></Vital> : null}
  </div>;
}

function PlayerRow({ p, cols, sport, team, onLeg, tonight, onPrint }) {
  const [open, setOpen] = useState(false); const [a, setA] = useState(null); const [err, setErr] = useState(false);
  const toggle = () => { setOpen(x => !x); onPrint?.({ id: p.id, name: p.name, team }); if (!a && !err) fetch(apiUrl(`/api/cats/tools/athlete/${sport}/${p.id}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(setA).catch(() => setErr(true)); };
  const main = cols[0]; const line = p.vals[main]; const now = tonight?.vals?.[main];
  return <><tr className={open ? 'is-open' : ''} onClick={toggle} data-testid={`pgs-p-${p.id}`}><th scope="row"><button type="button" aria-expanded={open} data-tip={`${p.name}: prints them, with season, career and last 5`}>{p.name}</button>{p.pos ? <small>{p.pos}</small> : null}{now != null ? <em className="grm-tonight m-num" data-tip={`${now} ${main} tonight`}>{now}</em> : null}</th>{cols.map(c => <td key={c}>{p.vals[c] ?? '—'}</td>)}<td><button type="button" className="m-btn pgs-add" disabled={!line} onClick={e => { e.stopPropagation(); onLeg({ text: `${p.name} over ${line} ${main}`, team, kind: 'player' }); }} data-tip={`Adds ${p.name} over ${line} ${main} to the slip. That is its season average, not a market price`} data-testid={`pgs-leg-${p.id}`}>+ Leg</button></td></tr>
    {open ? <tr className="pgs-more"><td colSpan={cols.length + 2}>{err ? <small>This player could not be read.</small> : !a ? <small>Reading…</small> : <div className="pgs-splits">{[['This season', a.season], ['Career', a.career]].filter(([, v]) => v).map(([t, v]) => <dl key={t}><dt>{t}</dt>{(a.labels || []).slice(0, 8).map((l, i) => <div key={l + i}><dd className="m-num">{v[i]}</dd><small>{l}</small></div>)}</dl>)}{Object.keys(a.last5 || {}).length ? <dl><dt>Last {a.games} games</dt>{Object.entries(a.last5).slice(0, 8).map(([l, v]) => <div key={l}><dd className="m-num">{v}</dd><small>{l}</small></div>)}</dl> : null}</div>}</td></tr> : null}</>;
}
function TeamSheets({ g, teams, onLeg, box, onPrint }) {
  const [at, setAt] = useState(0); const [d, setD] = useState({}); const t = teams[at]; const id = t?.id;
  useEffect(() => { if (!id || d[id]) return undefined; let on = true; fetch(apiUrl(`/api/cats/tools/team/${g.sport}/${id}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => on && setD(x => ({ ...x, [id]: j }))).catch(() => on && setD(x => ({ ...x, [id]: { failed: true } }))); return () => { on = false; }; }, [id, g.sport, d]);
  if (!teams.some(x => x?.id)) return <p className="ptl-none">Player stats appear once ESPN posts them, usually close to the start.</p>; const s = d[id];
  return <section className="pgs" data-testid="pgs"><div className="m-seg" role="group" aria-label="Team">{teams.map((x, i) => <button key={x.id || i} type="button" className={at === i ? 'active' : ''} aria-pressed={at === i} onClick={() => setAt(i)} data-testid={`pgs-team-${i}`}>{x.name}</button>)}</div>
    {!s ? <small className="pgw-note">Reading the team…</small> : s.failed ? <p className="ptl-none">ESPN did not answer for this team.</p> : <><ul className="pgs-team">{(s.stats || []).filter((x, i, all) => all.findIndex(y => (y.abbr || y.label) === (x.abbr || x.label)) === i).slice(0, 8).map(x => <li key={x.label} data-tip={x.label}><b className="m-num">{x.value}</b><small>{x.abbr || x.label}</small></li>)}</ul>
      <div className="pgs-wrap"><table className="pgs-t"><thead><tr><th scope="col">Player</th>{(s.cols || []).map(c => <th key={c} scope="col">{c}</th>)}<th aria-label="Add a leg" /></tr></thead><tbody>{(s.players || []).map(p => <PlayerRow key={p.id} p={p} cols={s.cols || []} sport={g.sport} team={t.name} onLeg={onLeg} tonight={box?.[p.id]} onPrint={onPrint} />)}</tbody></table></div></>}</section>;
}

const LIVE_POLL_MS = 20000;
export function GameWindow({ g, onClose, onCommand, onLeg, slip = 0, loadCalls = null }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [a, b] = g.teams; const state = d?.state || g.state; const live = state === 'in'; const done = state === 'post'; const [tab, setTab] = useState(null); const [player, setPlayer] = useState(null); const [calls, setCalls] = useState([]);
  const load = useCallback(() => fetch(apiUrl(`/api/cats/tools/game/${g.sport}/${g.id}?a=${encodeURIComponent(a.name || '')}&b=${encodeURIComponent(b.name || '')}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { setD(j); setErr(false); }).catch(() => setErr(true)), [g.sport, g.id, a.name, b.name]);
  useEffect(() => { load(); if (!live) return undefined; const t = setInterval(() => { if (!document.hidden) load(); }, LIVE_POLL_MS); return () => clearInterval(t); }, [load, live]);
  useEffect(() => { if (!loadCalls) return undefined; let on = true; const go = () => Promise.resolve(loadCalls(g.id)).then(j => { if (on) setCalls((j?.calls || []).map(c => ({ ...c, agent: j.agent }))); }).catch(() => {}); go(); if (!live) return () => { on = false; }; const t = setInterval(go, 60000); return () => { on = false; clearInterval(t); }; }, [loadCalls, g.id, live, done]);
  useEffect(() => { const k = e => { if (e.key === 'Escape') { e.stopPropagation(); onClose(); } }; window.addEventListener('keydown', k, true); return () => window.removeEventListener('keydown', k, true); }, [onClose]);
  const ta = d?.teams?.[0] || {}; const tb = d?.teams?.[1] || {}; const hasPlays = !!d?.plays?.length; const now = tab || (hasPlays ? 'plays' : 'edge'); const stage = printStage(state, calls); const teams = [{ ...a, ...ta, name: ta.name || a.name, id: ta.id || a.id }, { ...b, ...tb, name: tb.name || b.name, id: tb.id || b.id }];
  const TABS = [...(hasPlays ? [['plays', live ? 'Live' : 'Plays']] : []), ['edge', 'Edge'], ['players', 'Players'], ...(d?.stats?.length ? [['stats', 'Stats']] : [])];
  return createPortal(<div className="pgw-back" onClick={onClose} data-testid="pgw"><section className="pgw m-card" role="dialog" aria-modal="true" aria-label={`${a.name} and ${b.name}`} onClick={e => e.stopPropagation()}>
    <header className="pgw-h"><span className="pgw-t grm-h-t"><TeamMark t={{ ...a, ...ta, logo: a.logo }} size={44} /><span><small>{ta.side === 'home' ? 'HOME' : 'AWAY'}{ta.record ? ` · ${ta.record}` : ''}</small><b>{ta.name || a.name}</b><Form rows={ta.form} /></span></span>
      <span className="pgw-score">{state === 'pre' ? <em>{until(g.at)}</em> : <b className="m-num">{ta.score ?? a.score} <i>–</i> {tb.score ?? b.score}</b>}<small className={live ? 'is-live' : ''}>{live ? '● ' : ''}{d?.status || g.status}</small></span>
      <span className="pgw-t is-r grm-h-t"><span><small>{tb.side === 'home' ? 'HOME' : 'AWAY'}{tb.record ? ` · ${tb.record}` : ''}</small><b>{tb.name || b.name}</b><Form rows={tb.form} /></span><TeamMark t={{ ...b, ...tb, logo: b.logo }} size={44} /></span>
      <button type="button" className="pgw-x" onClick={onClose} aria-label="Close" data-tip="Close (Esc)" data-testid="pgw-close">✕</button></header>
    {err && !d ? <p className="ptl-none" role="alert">None of the free stat sources answered for this game. It tries again when you reopen it.</p> : !d ? <div className="pgw-load" aria-label="Reading the game"><i /><i /><i /></div> : <div className="pgw-b">
      <div className="pgw-col">
        <section><h5>HOW OFTEN IT WINS</h5><ul className="pgw-vss">
          {ta.winRate != null || tb.winRate != null ? <Versus pctRow label={`Season ${ta.record || '—'} · ${tb.record || '—'}`} a={ta.winRate} b={tb.winRate} tip="Share of this season's games each side has won" /> : null}
          {ta.sideRate != null || tb.sideRate != null ? <Versus pctRow label={`${ta.side === 'home' ? 'Home' : 'Road'} ${ta.sideRecord || '—'} · ${tb.side === 'home' ? 'Home' : 'Road'} ${tb.sideRecord || '—'}`} a={ta.sideRate} b={tb.sideRate} tip="Share won in the same spot as tonight: at home or on the road" /> : null}
          {a.chance != null || b.chance != null ? <Versus pctRow label="Polymarket" a={a.chance} b={b.chance} tip="What traders price right now. Market odds, not a promise" /> : null}
          {a.kalshi != null || b.kalshi != null ? <Versus pctRow label="Kalshi" a={a.kalshi} b={b.kalshi} tip="A second market's price. Market odds, not a promise" /> : null}
        </ul>{d.series ? <small className="pgw-note">{d.series}</small> : null}</section>
        {d.wp?.length > 1 ? <section className="pgw-line" data-testid="pgw-line"><h5>{(tb.side === 'home' ? tb.abbr : ta.abbr) || 'HOME'} WIN CHANCE, THROUGH THE GAME</h5><ProChart rows={d.wp.map(v => ({ v, mark: false }))} base={0.5} height={96} testid="pgw-pro" label="Win chance through the game" fmt={v => `${Math.round(v * 100)}%`} /></section> : null}
        <dl className="pgw-kv">{d.line ? <div><dt>Line</dt><dd className="m-num">{d.line}</dd></div> : null}{d.total ? <div><dt>Total</dt><dd className="m-num">{d.total}</dd></div> : null}{d.venue ? <div><dt>Venue</dt><dd>{d.venue}</dd></div> : null}</dl>
        {d.source === 'ESPN' || !d.source ? <PrintShelf sport={g.sport} teams={teams} player={player} onClear={() => setPlayer(null)} /> : null}
      </div>
      <div className="grm-main"><div className="m-seg grm-tabs" role="tablist" aria-label="Game">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={now === k} className={now === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`grm-tab-${k}`}>{l}{k === 'plays' && live ? <i className="grm-dot" aria-hidden="true" /> : null}</button>)}</div>
        <div className="grm-pane" key={now}>{now === 'plays' ? <Plays d={d} stage={stage} calls={calls} seed={`game:${g.sport}:${g.id}`} /> : now === 'edge' ? <Edge d={d} a={a} b={b} onCommand={onCommand} /> : now === 'players' ? <TeamSheets g={g} teams={teams} onLeg={onLeg} box={d.box} onPrint={setPlayer} /> : <section className="grm-stats"><h5>TEAM STATS</h5><ul className="pgw-vss">{d.stats.map(x => <Versus key={x.label} label={x.label} a={x.a} b={x.b} />)}</ul></section>}</div></div></div>}
    <footer className="pgw-f">{done ? null : <div className="pgw-legs"><small data-testid="pgw-slip">Your slip has {slip} leg{slip === 1 ? '' : 's'}. Add a side:</small>{[a, b].map(t => <button key={t.name} type="button" className="m-btn" onClick={() => onLeg?.({ text: `${t.short || t.name} to win`, chance: t.chance ?? t.kalshi ?? null, kind: 'side' })} data-tip={t.chance != null ? `Market price ${pct(t.chance)}` : 'No market price for this game'} data-testid={`pgw-leg-${t.short}`}>+ {t.short || t.name}</button>)}</div>}<small className="pgw-src" data-testid="pgw-source">{d?.source && d.source !== 'ESPN' ? `ESPN did not answer. Records from ${d.source}; player stats are not available right now.` : 'Stats from ESPN.'} Prices from Polymarket and Kalshi: market odds, not a promise.</small>{done ? null : <button type="button" className="m-btn m-go" onClick={() => { onCommand?.(`file a pob ${a.short} vs ${b.short}`); onClose(); }} disabled={!onCommand} data-tip="Puts it in the chat box. You press send" data-testid="pgw-file">File a pick</button>}</footer>
  </section></div>, document.body);
}
export function GameCard({ g, onCommand, onLeg, slip, loadCalls }) {
  const [a, b] = g.teams; const live = g.state === 'in'; const done = g.state === 'post'; const [open, setOpen] = useState(false);
  return <li className={`ptl-gcard is-${g.state}`} role="button" tabIndex={0} onClick={() => setOpen(true)} onKeyDown={e => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setOpen(true); } }} data-tip="The game room: plays, edge vitals, players and prints" data-testid={`ptl-game-${g.id}`}>{open ? <GameWindow g={g} onCommand={onCommand} onLeg={onLeg} slip={slip} loadCalls={loadCalls} onClose={() => setOpen(false)} /> : null}
    <span className="ptl-g-tag">{live ? <em className="ptl-live" data-tip="Happening now">LIVE</em> : done ? <em>FINAL</em> : <em data-tip="Starts in">{until(g.at)}</em>}<small>{g.status}</small></span>
    {g.teams.map(t => <span key={t.name} className={`ptl-g-t${t.winner ? ' is-win' : ''}`}><TeamMark t={t} size={24} /><b>{t.short || t.name}</b>{g.state !== 'pre' ? <i key={t.score} className="m-num">{t.score}</i> : <i className="m-num" data-tip="What the market prices">{t.chance ? pct(t.chance) : ''}</i>}</span>)}
    {done ? null : <button type="button" className="ptl-g-add" onClick={e => { e.stopPropagation(); onCommand?.(`file a pob ${a.short} vs ${b.short}`); }} data-tip="Puts it in the chat box. You press send" aria-label={`File a pick on ${a.short} and ${b.short}`}>File</button>}</li>;
}

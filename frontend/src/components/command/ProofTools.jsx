import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { ProChart } from './ProChart';
import '../../styles/proofTools.css';

// 🧰 THE PROOF FOLDER DASH (owner 2026-11-04): each folder opens on its top 5 free sources, live. PoB: pick a sport and a team, see the games and the parlays the market likes most, one tap files a proof on them. "Best" = the market's own odds, said so on screen.
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
const big = v => (v == null ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(0)}M` : `$${Math.round(v).toLocaleString('en-US')}`);
const shortMint = m => (m ? `${m.slice(0, 4)}…${m.slice(-4)}` : '');

function Sources({ rows }) {
  return <ul className="ptl-src" aria-label="Sources">{(rows || []).map(s => <li key={s.name} className={s.on ? 'is-on' : ''} data-tip={s.on ? `${s.use}. Read just now` : `${s.use}. Not read`}><i aria-hidden="true" />{s.name}</li>)}</ul>;
}
function Bar({ v, tone }) { return <span className={`ptl-bar ${tone || ''}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></span>; }

// 🖼 Real, freely licensed photos with their credit, or none. A team's logo is a trademark, so nothing is drawn in its place. The photos stay on Wikimedia: nothing is saved anywhere, a card off screen holds no image at all, and one shared clock turns them, one card at a time, only once the next photo has loaded.
const cycling = new Set();
let cycleClock = null;
const cycleTurn = () => { if (!document.hidden) cycling.forEach(f => f()); };
const joinCycle = f => { cycling.add(f); if (!cycleClock) cycleClock = setInterval(cycleTurn, 7000); return () => { cycling.delete(f); if (!cycling.size) { clearInterval(cycleClock); cycleClock = null; } }; };
function FreePhoto({ q, must }) {
  const [imgs, setImgs] = useState(null); const [at, setAt] = useState(0); const [seen, setSeen] = useState(typeof IntersectionObserver === 'undefined'); const box = useRef(null);
  useEffect(() => { if (typeof IntersectionObserver === 'undefined' || !box.current) return undefined; const io = new IntersectionObserver(([e]) => setSeen(e.isIntersecting), { rootMargin: '120px' }); io.observe(box.current); return () => io.disconnect(); }, []);
  useEffect(() => { if (!seen || imgs) return undefined; let on = true; fetch(apiUrl(`/api/cats/tools/image?q=${encodeURIComponent(q)}&must=${encodeURIComponent(must.join(','))}`)).then(r => (r.ok ? r.json() : null)).then(j => { if (on) setImgs(j?.images || (j?.image ? [j.image] : [])); }).catch(() => on && setImgs([])); return () => { on = false; }; }, [seen, imgs, q, must]);
  useEffect(() => { if (!seen || !imgs || imgs.length < 2) return undefined; return joinCycle(() => { const n = (at + 1) % imgs.length; const next = new Image(); next.onload = () => setAt(n); next.src = imgs[n].url; }); }, [seen, imgs, at]);
  const img = seen && imgs?.length ? imgs[at % imgs.length] : null;
  return <span className={`ptl-photo${imgs?.length ? ' has-img' : ''}`} ref={box}>{img ? <><img key={img.url} src={img.url} alt={img.title} decoding="async" /><a href={img.page} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} data-tip={`${img.title}: ${img.license}`}>{img.by} · {img.license}</a></> : null}</span>;
}
// ⚖ Two sides of one number, mirrored from the middle. Each bar is scaled to the bigger side of its own row.
function Versus({ label, a, b, tip, pctRow }) {
  const na = parseFloat(a); const nb = parseFloat(b); const top = Math.max(Math.abs(na) || 0, Math.abs(nb) || 0) || 1; const fa = pctRow ? na : (Math.abs(na) || 0) / top; const fb = pctRow ? nb : (Math.abs(nb) || 0) / top;
  const show = v => (pctRow ? (Number.isFinite(v) ? `${Math.round(v * 100)}%` : '—') : (v ?? '—'));
  return <li className="pgw-vs" data-tip={tip}><b className="m-num">{show(pctRow ? na : a)}</b><span className="pgw-vbar is-a" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, Math.min(1, fa || 0))})` }} /></span><small>{label}</small><span className="pgw-vbar is-b" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, Math.min(1, fb || 0))})` }} /></span><b className="m-num">{show(pctRow ? nb : b)}</b></li>;
}
// 📈 The chance the home side wins, through the game.
function WinLine({ wp, home }) {
  return <section className="pgw-line" data-testid="pgw-line"><h5>{home} WIN CHANCE, THROUGH THE GAME</h5><ProChart rows={wp.map(v => ({ v, mark: false }))} base={0.5} height={130} testid="pgw-pro" label={`${home} win chance through the game`} fmt={v => `${Math.round(v * 100)}%`} /></section>;
}
const Form = ({ rows }) => (rows?.length ? <span className="pgw-form" aria-label={`Last ${rows.length} games: ${rows.join(' ')}`}>{rows.map((r, i) => <i key={i} className={r === 'W' ? 'is-w' : r === 'L' ? 'is-l' : ''}>{r}</i>)}</span> : null);
// 🏟 A team's season averages and every player's. Tap a player for season, career and last 5 games, and add a leg.
function PlayerRow({ p, cols, sport, team, onLeg }) {
  const [open, setOpen] = useState(false); const [a, setA] = useState(null); const [err, setErr] = useState(false);
  const toggle = () => { setOpen(x => !x); if (!a && !err) fetch(apiUrl(`/api/cats/tools/athlete/${sport}/${p.id}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(setA).catch(() => setErr(true)); };
  const main = cols[0]; const line = p.vals[main];
  return <><tr className={open ? 'is-open' : ''} onClick={toggle} data-testid={`pgs-p-${p.id}`}><th scope="row"><button type="button" aria-expanded={open} data-tip={`${p.name}: season, career, last 5`}>{p.name}</button>{p.pos ? <small>{p.pos}</small> : null}</th>{cols.map(c => <td key={c}>{p.vals[c] ?? '—'}</td>)}<td><button type="button" className="m-btn pgs-add" disabled={!line} onClick={e => { e.stopPropagation(); onLeg({ text: `${p.name} over ${line} ${main}`, team, kind: 'player' }); }} data-tip={`Adds ${p.name} over ${line} ${main} to the slip. That is its season average, not a market price`} data-testid={`pgs-leg-${p.id}`}>+ Leg</button></td></tr>
    {open ? <tr className="pgs-more"><td colSpan={cols.length + 2}>{err ? <small>This player could not be read.</small> : !a ? <small>Reading…</small> : <div className="pgs-splits">{[['This season', a.season], ['Career', a.career]].filter(([, v]) => v).map(([t, v]) => <dl key={t}><dt>{t}</dt>{(a.labels || []).slice(0, 8).map((l, i) => <div key={l + i}><dd className="m-num">{v[i]}</dd><small>{l}</small></div>)}</dl>)}{Object.keys(a.last5 || {}).length ? <dl><dt>Last {a.games} games</dt>{Object.entries(a.last5).slice(0, 8).map(([l, v]) => <div key={l}><dd className="m-num">{v}</dd><small>{l}</small></div>)}</dl> : null}</div>}</td></tr> : null}</>;
}
function TeamSheets({ g, teams, onLeg }) {
  const [at, setAt] = useState(0); const [d, setD] = useState({}); const t = teams[at]; const id = t?.id;
  useEffect(() => { if (!id || d[id]) return undefined; let on = true; fetch(apiUrl(`/api/cats/tools/team/${g.sport}/${id}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => on && setD(x => ({ ...x, [id]: j }))).catch(() => on && setD(x => ({ ...x, [id]: { failed: true } }))); return () => { on = false; }; }, [id, g.sport, d]);
  if (!teams.some(x => x?.id)) return null; const s = d[id];
  return <section className="pgs" data-testid="pgs"><h5>TEAMS AND PLAYERS <small>season averages</small></h5><div className="m-seg" role="group" aria-label="Team">{teams.map((x, i) => <button key={x.id || i} type="button" className={at === i ? 'active' : ''} aria-pressed={at === i} onClick={() => setAt(i)} data-testid={`pgs-team-${i}`}>{x.name}</button>)}</div>
    {!s ? <small className="pgw-note">Reading the team…</small> : s.failed ? <p className="ptl-none">ESPN did not answer for this team.</p> : <><ul className="pgs-team">{(s.stats || []).filter((x, i, all) => all.findIndex(y => (y.abbr || y.label) === (x.abbr || x.label)) === i).slice(0, 8).map(x => <li key={x.label} data-tip={x.label}><b className="m-num">{x.value}</b><small>{x.abbr || x.label}</small></li>)}</ul>
      <div className="pgs-wrap"><table className="pgs-t"><thead><tr><th scope="col">Player</th>{(s.cols || []).map(c => <th key={c} scope="col">{c}</th>)}<th aria-label="Add a leg" /></tr></thead><tbody>{(s.players || []).map(p => <PlayerRow key={p.id} p={p} cols={s.cols || []} sport={g.sport} team={t.name} onLeg={onLeg} />)}</tbody></table></div></>}</section>;
}
// 🧾 The slip: legs its owner picked, for the agent to prove. Priced legs multiply; a player leg has no market price and says so.
function LegSlip({ legs, setLegs, onCommand }) {
  if (!legs.length) return <section className="pgl is-empty" data-testid="pgl"><h4><Ic3 e="🧾" /> Your slip</h4><p className="ptl-none">Open a game and add a team or a player. Then ask it to prove the slip.</p></section>;
  const priced = legs.filter(l => l.chance != null); const all = priced.length === legs.length && priced.length ? priced.reduce((a, l) => a * l.chance, 1) : null;
  return <section className="pgl" data-testid="pgl"><h4><Ic3 e="🧾" /> Your slip <small>{legs.length} leg{legs.length === 1 ? '' : 's'}</small></h4><ol>{legs.map(l => <li key={l.text}><span>{l.text}</span><b className="m-num">{l.chance != null ? pct(l.chance) : 'No price'}</b><button type="button" className="m-btn" onClick={() => setLegs(x => x.filter(y => y.text !== l.text))} aria-label={`Remove ${l.text}`} data-tip="Take it off the slip">✕</button></li>)}</ol>
    <p className="pgl-all">{all != null ? <>All landing, if the games are independent: <b className="m-num">{pct(all)}</b>, about {(1 / all).toFixed(2)}x. Market odds, not a promise.</> : 'A player leg has no market price here, so there is no total chance.'}</p><button type="button" className="m-btn m-go" onClick={() => onCommand?.(`file a pob ${legs.map(l => l.text).join(' and ')}`)} data-tip="Puts it in the chat box. You press send" data-testid="pgl-prove">Ask it to prove this slip</button></section>;
}
// 🔍 Where two markets price the same game differently. A gap is a question to check, not free money.
function MarketGaps({ games, onCommand }) {
  const rows = (games || []).filter(g => g.state === 'pre').map(g => { const t = g.teams.find(x => x.chance != null && x.kalshi != null); return t ? { g, t, gap: Math.abs(t.chance - t.kalshi) } : null; }).filter(r => r && r.gap >= 0.02).sort((a, b) => b.gap - a.gap).slice(0, 5);
  return <section className="pgg" data-testid="pgg"><h4><Ic3 e="🔍" /> Where markets disagree <small>Polymarket against Kalshi</small></h4>{rows.length ? <ol>{rows.map(({ g, t, gap }) => <li key={g.id}><button type="button" onClick={() => onCommand?.(`file a pob ${t.short} ${g.teams.map(x => x.short).join(' vs ')}`)} data-tip="Puts it in the chat box. You press send"><span>{t.short} <small>{pct(t.chance)} against {pct(t.kalshi)}</small></span><b className="m-num">{Math.round(gap * 100)} pts</b></button></li>)}</ol> : <p className="ptl-none">No gap of 2 points or more right now.</p>}</section>;
}
function GameWindow({ g, onClose, onCommand, onLeg, slip = 0 }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [a, b] = g.teams; const live = (d?.state || g.state) === 'in'; const done = (d?.state || g.state) === 'post';
  const load = useCallback(() => fetch(apiUrl(`/api/cats/tools/game/${g.sport}/${g.id}?a=${encodeURIComponent(a.name || '')}&b=${encodeURIComponent(b.name || '')}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { setD(j); setErr(false); }).catch(() => setErr(true)), [g.sport, g.id, a.name, b.name]);
  useEffect(() => { load(); if (g.state !== 'in') return undefined; const t = setInterval(() => { if (!document.hidden) load(); }, 60000); return () => clearInterval(t); }, [load, g.state]);
  useEffect(() => { const k = e => { if (e.key === 'Escape') { e.stopPropagation(); onClose(); } }; window.addEventListener('keydown', k, true); return () => window.removeEventListener('keydown', k, true); }, [onClose]);
  const ta = d?.teams?.[0] || {}; const tb = d?.teams?.[1] || {};
  return createPortal(<div className="pgw-back" onClick={onClose} data-testid="pgw"><section className="pgw m-card" role="dialog" aria-modal="true" aria-label={`${a.name} and ${b.name}`} onClick={e => e.stopPropagation()}>
    <header className="pgw-h"><span className="pgw-t"><small>{ta.side === 'home' ? 'HOME' : 'AWAY'}</small><b>{ta.name || a.name}</b><Form rows={ta.form} /></span>
      <span className="pgw-score">{g.state === 'pre' && !done && !live ? <em>{until(g.at)}</em> : <b className="m-num">{ta.score ?? a.score} <i>–</i> {tb.score ?? b.score}</b>}<small className={live ? 'is-live' : ''}>{live ? '● ' : ''}{d?.status || g.status}</small></span>
      <span className="pgw-t is-r"><small>{tb.side === 'home' ? 'HOME' : 'AWAY'}</small><b>{tb.name || b.name}</b><Form rows={tb.form} /></span>
      <button type="button" className="pgw-x" onClick={onClose} aria-label="Close" data-tip="Close (Esc)" data-testid="pgw-close">✕</button></header>
    {err && !d ? <p className="ptl-none" role="alert">None of the free stat sources answered for this game. It tries again when you reopen it.</p> : !d ? <div className="pgw-load" aria-label="Reading the game"><i /><i /><i /></div> : <div className="pgw-b">
      <div className="pgw-col">
        <section><h5>HOW OFTEN IT WINS</h5><ul className="pgw-vss">
          {ta.winRate != null || tb.winRate != null ? <Versus pctRow label={`Season ${ta.record || '—'} · ${tb.record || '—'}`} a={ta.winRate} b={tb.winRate} tip="Share of this season's games each side has won" /> : null}
          {ta.sideRate != null || tb.sideRate != null ? <Versus pctRow label={`${ta.side === 'home' ? 'Home' : 'Road'} ${ta.sideRecord || '—'} · ${tb.side === 'home' ? 'Home' : 'Road'} ${tb.sideRecord || '—'}`} a={ta.sideRate} b={tb.sideRate} tip="Share won in the same spot as tonight: at home or on the road" /> : null}
          {a.chance != null || b.chance != null ? <Versus pctRow label="Polymarket" a={a.chance} b={b.chance} tip="What traders price right now. Market odds, not a promise" /> : null}
          {a.kalshi != null || b.kalshi != null ? <Versus pctRow label="Kalshi" a={a.kalshi} b={b.kalshi} tip="A second market's price. Market odds, not a promise" /> : null}
        </ul>{d.series ? <small className="pgw-note">{d.series}</small> : null}</section>
        {d.wp?.length > 1 ? <WinLine wp={d.wp} home={(tb.side === 'home' ? tb.abbr : ta.abbr) || 'HOME'} /> : null}
        {d.stats?.length ? <section><h5>TEAM STATS</h5><ul className="pgw-vss">{d.stats.slice(0, 7).map(x => <Versus key={x.label} label={x.label} a={x.a} b={x.b} />)}</ul></section> : null}
        {ta.injuries?.length || tb.injuries?.length ? <section><h5>INJURIES</h5><div className="pgw-two">{[ta, tb].map(t => <ol key={t.id || t.name} className="pgw-pl"><li className="pgw-pl-h">{t.abbr}</li>{(t.injuries || []).length ? t.injuries.map(l => <li key={l.name}><span><b>{l.name}</b></span><small>{l.status}</small></li>) : <li><small>None listed</small></li>}</ol>)}</div></section> : null}
        <dl className="pgw-kv">{d.line ? <div><dt>Line</dt><dd className="m-num">{d.line}</dd></div> : null}{d.total ? <div><dt>Total</dt><dd className="m-num">{d.total}</dd></div> : null}{d.venue ? <div><dt>Venue</dt><dd>{d.venue}</dd></div> : null}</dl>
        {!(ta.leaders?.length || tb.leaders?.length || d.stats?.length || d.wp?.length > 1) ? <p className="ptl-none">Player and team stats appear once ESPN posts them, usually close to the start.</p> : null}
      </div>
      <TeamSheets g={g} teams={[{ ...ta, name: ta.name || a.name, id: ta.id || a.id }, { ...tb, name: tb.name || b.name, id: tb.id || b.id }]} onLeg={onLeg} /></div>}
    <footer className="pgw-f">{done ? null : <div className="pgw-legs"><small data-testid="pgw-slip">Your slip has {slip} leg{slip === 1 ? '' : 's'}. Add a side:</small>{[a, b].map(t => <button key={t.name} type="button" className="m-btn" onClick={() => onLeg?.({ text: `${t.short || t.name} to win`, chance: t.chance ?? t.kalshi ?? null, kind: 'side' })} data-tip={t.chance != null ? `Market price ${pct(t.chance)}` : 'No market price for this game'} data-testid={`pgw-leg-${t.short}`}>+ {t.short || t.name}</button>)}</div>}<small className="pgw-src" data-testid="pgw-source">{d?.source && d.source !== 'ESPN' ? `ESPN did not answer. Records from ${d.source}; player stats are not available right now.` : 'Stats from ESPN.'} Prices from Polymarket and Kalshi: market odds, not a promise.</small>{done ? null : <button type="button" className="m-btn m-go" onClick={() => { onCommand?.(`file a pob ${a.short} vs ${b.short}`); onClose(); }} disabled={!onCommand} data-tip="Puts it in the chat box. You press send" data-testid="pgw-file">File a pick</button>}</footer>
  </section></div>, document.body);
}
const until = at => { const s = (new Date(at).getTime() - Date.now()) / 1000; if (!Number.isFinite(s)) return ''; if (s < 0) return 'now'; if (s < 3600) return `${Math.ceil(s / 60)}m`; if (s < 86400) return `${Math.round(s / 3600)}h`; return `${Math.round(s / 86400)}d`; };
function GameCard({ g, onCommand, onLeg, slip }) {
  const [a, b] = g.teams; const live = g.state === 'in'; const done = g.state === 'post'; const [open, setOpen] = useState(false); const must = useRef([a.short, b.short, a.name, b.name].filter(Boolean)).current;
  return <li className={`ptl-gcard is-${g.state}`} role="button" tabIndex={0} onClick={() => setOpen(true)} onKeyDown={e => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setOpen(true); } }} data-tip="Team stats, players, and how often each side wins" data-testid={`ptl-game-${g.id}`}>{open ? <GameWindow g={g} onCommand={onCommand} onLeg={onLeg} slip={slip} onClose={() => setOpen(false)} /> : null}<FreePhoto q={`${a.name} ${b.name}`} must={must} /><div className="ptl-g-b"><span className="ptl-g-tag">{live ? <em className="ptl-live" data-tip="Happening now">LIVE</em> : done ? <em>FINAL</em> : <em data-tip="Starts in">{until(g.at)}</em>}<small>{g.status}</small></span>{g.teams.map(t => <span key={t.name} className={`ptl-g-t${t.winner ? ' is-win' : ''}`}><b>{t.short || t.name}</b>{g.state !== 'pre' ? <i key={t.score} className="m-num">{t.score}</i> : <i className="m-num" data-tip="What the market prices">{t.chance ? pct(t.chance) : ''}</i>}</span>)}{done ? null : <button type="button" className="m-btn" onClick={e => { e.stopPropagation(); onCommand?.(`file a pob ${a.short} vs ${b.short}`); }} data-tip="Puts it in the chat box. You press send" data-testid={`ptl-file-${g.id}`}>File a pick</button>}</div></li>;
}
function BidsDash({ d, sport, setSport, team, setTeam, onCommand }) {
  const [legs, setLegs] = useState([]); const addLeg = l => setLegs(x => (x.some(y => y.text === l.text) ? x : [...x, l].slice(0, 8)));
  const [mkt, setMkt] = useState('All'); const rows = d.markets || []; const cats = ['All', ...new Set(rows.map(m => m.cat))]; const shownM = (mkt === 'All' ? rows : rows.filter(m => m.cat === mkt)).slice(0, 12);
  return <>
    <div className="m-seg ptl-tabs" role="tablist" aria-label="Sport">{(d.sports || []).map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={sport === k} className={sport === k ? 'active' : ''} onClick={() => { setSport(k); setTeam(''); }} data-testid={`ptl-sport-${k}`}>{l}</button>)}</div>
    {sport === 'all' ? null : <select className="m-input ptl-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Team" data-testid="ptl-team"><option value="">All teams</option>{(d.teams || []).map(t => <option key={t} value={t}>{t}</option>)}</select>}
    {d.team ? <p className="ptl-card" data-testid="ptl-teamcard"><b>{d.team.name}</b> {d.team.league}{d.team.stadium ? ` · ${d.team.stadium}` : ''}{d.team.formed ? ` · since ${d.team.formed}` : ''}</p> : null}
    <div className="ptl-grid"><LegSlip legs={legs} setLegs={setLegs} onCommand={onCommand} /><MarketGaps games={d.games} onCommand={onCommand} /></div>
    <section><h4><Ic3 e="🏟" /> Games <small>{d.live ? `${d.live} live now, first` : 'Coming up'}. Photos are free to use, with credit.</small></h4>{(d.games || []).length ? <ol className="ptl-gcards" data-testid="ptl-gcards">{d.games.slice(0, 18).map(g => <GameCard key={g.id} g={g} onCommand={onCommand} onLeg={addLeg} slip={legs.length} />)}</ol> : <p className="ptl-none">No games on its board right now.</p>}</section>
    <div className="ptl-grid">
      <section><h4><Ic3 e="🏆" /> Top parlays <small>market odds, not a promise</small></h4>
        {(d.parlays || []).length ? d.parlays.map(p => <button key={p.legs.join()} type="button" className="ptl-parlay" onClick={() => onCommand?.(`file a pob ${p.legs.join(' and ')}`)} data-tip="Puts it in the chat box. You press send" data-testid="ptl-parlay"><b className="m-num">{pct(p.chance)}</b><Bar v={p.chance} /><span>{p.legs.join(' + ')}</span><small>about {p.pays}x if all land</small></button>) : <p className="ptl-none">No priced games to combine right now.</p>}
        <h4><Ic3 e="🎯" /> Strongest sides</h4>{(d.legs || []).slice(0, 5).map(l => <button key={l.game} type="button" className="ptl-leg" onClick={() => onCommand?.(`file a pob ${l.pick}`)} data-testid="ptl-leg"><span>{l.pick}</span><Bar v={l.chance} tone="is-b" /><b className="m-num">{pct(l.chance)}</b></button>)}</section>
      <section><h4><Ic3 e="🗳" /> Markets <small>biggest on Polymarket. A filed bid settles when the market does.</small></h4><div className="chr-chips">{cats.map(c => <button key={c} type="button" className={`m-chip${mkt === c ? ' is-on' : ''}`} onClick={() => setMkt(c)} data-testid={`ptl-mkt-${c}`}>{c}</button>)}</div>
        <ol className="ptl-markets" data-testid="ptl-markets">{shownM.map(m => <li key={m.id}><button type="button" onClick={() => onCommand?.(`file a pob ${m.title}`)} data-tip="Puts it in the chat box. You press send"><span>{m.title}</span><small>{m.lead.name}</small><Bar v={m.lead.chance} /><b className="m-num">{pct(m.lead.chance)}</b><em data-tip="When it settles">{until(m.end)}</em></button></li>)}</ol></section>
    </div></>;
}
function PowDash({ d, onCommand }) {
  const col = (t, rows, line) => <section><h4>{t}</h4>{(rows || []).length ? <ol className="ptl-list">{rows.slice(0, 6).map((r, i) => <li key={i}>{line(r)}</li>)}</ol> : <p className="ptl-none">Nothing from this source now.</p>}</section>;
  return <div className="ptl-grid is-3">
    {col('Trending', d.trending, r => <span><b>${r.sym}</b> {r.name}{r.rank ? ` · #${r.rank}` : ''}</span>)}
    {col('Boosted on Solana', d.boosted, r => <a href={r.url} target="_blank" rel="noopener noreferrer">{shortMint(r.mint)} <small>boost {r.boost}</small></a>)}
    {col('FEELESS intake', d.intake, r => <button type="button" className="ptl-link" onClick={() => onCommand?.('file a PoW')} data-tip="Puts “file a PoW” in the chat box">{r.sym ? `$${r.sym}` : shortMint(r.mint)}</button>)}
  </div>;
}
function ContentDash({ d }) {
  return <div className="ptl-grid is-3" data-testid="ptl-trends">{Object.entries(d.trends || {}).filter(([, v]) => v?.length).map(([k, v]) => <section key={k}><h4>{k}</h4><ol className="ptl-list">{v.slice(0, 5).map(t => <li key={t}><span>{t}</span></li>)}</ol></section>)}</div>;
}
function PopDash({ d, onCommand }) {
  return <><div className="ptl-vitals"><span><em>MOOD</em><b>{d.mood || '—'}</b><small>{d.moodValue}/100</small></span><span><em>BTC SPOT</em><b className="m-num">{d.btcSpot ? `$${Math.round(d.btcSpot).toLocaleString('en-US')}` : '—'}</b></span><span><em>BTC DOMINANCE</em><b className="m-num">{d.btcDom ? `${d.btcDom.toFixed(1)}%` : '—'}</b></span><span><em>PERP VOLUME 24H</em><b className="m-num">{big(d.perpVol24h)}</b></span></div>
    <div className="ptl-grid"><section><h4>Biggest markets</h4><ol className="ptl-list">{(d.markets || []).slice(0, 6).map(m => <li key={m.market}><button type="button" className="ptl-link" onClick={() => onCommand?.('file a perp')} data-tip="Puts “file a perp” in the chat box"><b>{m.market}</b> ${m.price.toLocaleString('en-US')}</button><small>OI {big(m.oiUsd)}</small></li>)}</ol></section>
      <section><h4>Hottest funding</h4><ol className="ptl-list">{(d.hotFunding || []).map(m => <li key={m.market}><b>{m.market}</b><em className={`m-num ${m.fundingPct >= 0 ? 'is-up' : 'is-dn'}`}>{m.fundingPct > 0 ? '+' : ''}{m.fundingPct}%/h</em></li>)}</ol></section></div></>;
}
export function ProofTools({ kind, onCommand }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [sport, setSport] = useState('all'); const [team, setTeam] = useState(''); const [open, setOpen] = useState(true);
  useEffect(() => { let on = true; let first = true; const go = () => { if (document.hidden && !first) return; first = false; fetch(apiUrl(`/api/cats/tools/${kind}?sport=${sport}&team=${encodeURIComponent(team)}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { if (on) { setD(j); setErr(false); } }).catch(() => on && setErr(true)); };
    go(); const t = setInterval(go, 60000); return () => { on = false; clearInterval(t); }; }, [kind, sport, team]);
  return <details className="ptl" open={open} onToggle={e => setOpen(e.currentTarget.open)} data-testid={`ptl-${kind}`}><summary><b><Ic3 e="🧰" /> LIVE TOOLS</b><Sources rows={d?.sources} /></summary>
    {err && !d ? <p className="ptl-none" role="alert">These sources could not be read. It tries again in a minute.</p> : !d ? <p className="ptl-none">Reading its sources…</p>
      : kind === 'bids' ? <BidsDash d={d} sport={sport} setSport={setSport} team={team} setTeam={setTeam} onCommand={onCommand} /> : kind === 'pop' ? <PopDash d={d} onCommand={onCommand} /> : kind === 'content' ? <ContentDash d={d} /> : <PowDash d={d} onCommand={onCommand} />}
  </details>;
}

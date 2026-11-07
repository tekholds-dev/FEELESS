import { ProofCalc, WatchRoom } from './ProofRooms';
import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { GameCard, until } from './GameRoom';
import '../../styles/proofTools.css';

// 🧰 THE PROOF FOLDER DASH (owner 2026-11-04): each folder opens on its top 5 free sources, live. PoB: pick a sport and a team, see the games and the parlays the market likes most, one tap files a proof on them. "Best" = the market's own odds, said so on screen.
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
const big = v => (v == null ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(0)}M` : `$${Math.round(v).toLocaleString('en-US')}`);
const shortMint = m => (m ? `${m.slice(0, 4)}…${m.slice(-4)}` : '');

function Sources({ rows }) {
  return <ul className="ptl-src" aria-label="Sources">{(rows || []).map(s => <li key={s.name} className={s.on ? 'is-on' : ''} data-tip={s.on ? `${s.use}. Read just now` : `${s.use}. Not read`}><i aria-hidden="true" />{s.name}</li>)}</ul>;
}
function Bar({ v, tone }) { return <span className={`ptl-bar ${tone || ''}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></span>; }

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
const BOARD_TABS = [['games', 'Games'], ['parlays', 'Parlays'], ['markets', 'Markets'], ['gaps', 'Gaps']];
const GAMES_PAGE = 6;
function BidsDash({ d, sport, setSport, team, setTeam, onCommand, loadCalls }) {
  const [legs, setLegs] = useState([]); const addLeg = l => setLegs(x => (x.some(y => y.text === l.text) ? x : [...x, l].slice(0, 8))); const [tab, setTab] = useState('games'); const [page, setPage] = useState(0);
  useEffect(() => { setPage(0); }, [sport, team]);
  const [mkt, setMkt] = useState('All'); const rows = d.markets || []; const cats = ['All', ...new Set(rows.map(m => m.cat))]; const shownM = (mkt === 'All' ? rows : rows.filter(m => m.cat === mkt)).slice(0, 12);
  return <><div className="ptl-bar-row"><div className="m-seg ptl-tabs" role="tablist" aria-label="Sport">{(d.sports || []).map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={sport === k} className={sport === k ? 'active' : ''} onClick={() => { setSport(k); setTeam(''); }} data-testid={`ptl-sport-${k}`}>{l}</button>)}</div>
    {sport === 'all' ? null : <select className="m-input ptl-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Team" data-testid="ptl-team"><option value="">All teams</option>{(d.teams || []).map(t => <option key={t} value={t}>{t}</option>)}</select>}</div>
    {d.team ? <p className="ptl-card" data-testid="ptl-teamcard"><b>{d.team.name}</b> {d.team.league}{d.team.stadium ? ` · ${d.team.stadium}` : ''}{d.team.formed ? ` · since ${d.team.formed}` : ''}</p> : null}
    <div className="ptl-board"><div className="ptl-board-m"><div className="m-seg ptl-subtabs" role="tablist" aria-label="Board">{BOARD_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`ptl-tab-${k}`}>{l}{k === 'games' && Number(d.live) > 0 ? <em className="ptl-live"> {Number(d.live)} LIVE</em> : null}</button>)}</div>
      {tab === 'games' ? ((d.games || []).length ? <><ol className="ptl-gcards" data-testid="ptl-gcards">{d.games.slice(page * GAMES_PAGE, (page + 1) * GAMES_PAGE).map(g => <GameCard key={g.id} g={g} onCommand={onCommand} onLeg={addLeg} slip={legs.length} loadCalls={loadCalls} />)}</ol>{d.games.length > GAMES_PAGE ? <div className="ptl-pages" data-testid="ptl-pages"><button type="button" className="m-btn" disabled={!page} onClick={() => setPage(x => x - 1)} data-tip="Earlier games" data-testid="ptl-prev">←</button><span className="m-num">{page + 1} / {Math.ceil(d.games.length / GAMES_PAGE)}</span><button type="button" className="m-btn" disabled={(page + 1) * GAMES_PAGE >= d.games.length} onClick={() => setPage(x => x + 1)} data-tip="More games" data-testid="ptl-next">→</button></div> : null}</> : <p className="ptl-none">No games on its board right now.</p>) : null}
      {tab === 'parlays' ? <div className="ptl-grid"><section><h4><Ic3 e="🏆" /> Top parlays <small>market odds, not a promise</small></h4>{(d.parlays || []).length ? d.parlays.map(p => <button key={p.legs.join()} type="button" className="ptl-parlay" onClick={() => onCommand?.(`file a pob ${p.legs.join(' and ')}`)} data-tip="Puts it in the chat box. You press send" data-testid="ptl-parlay"><b className="m-num">{pct(p.chance)}</b><Bar v={p.chance} /><span>{p.legs.join(' + ')}</span><small>about {p.pays}x if all land</small></button>) : <p className="ptl-none">No priced games to combine right now.</p>}</section>
        <section><h4><Ic3 e="🎯" /> Strongest sides</h4>{(d.legs || []).slice(0, 5).map(l => <button key={l.game} type="button" className="ptl-leg" onClick={() => onCommand?.(`file a pob ${l.pick}`)} data-testid="ptl-leg"><span>{l.pick}</span><Bar v={l.chance} tone="is-b" /><b className="m-num">{pct(l.chance)}</b></button>)}</section></div> : null}
      {tab === 'markets' ? <section><h4><Ic3 e="🗳" /> Markets <small>biggest on Polymarket. A filed bid settles when the market does.</small></h4><div className="chr-chips">{cats.map(c => <button key={c} type="button" className={`m-chip${mkt === c ? ' is-on' : ''}`} onClick={() => setMkt(c)} data-testid={`ptl-mkt-${c}`}>{c}</button>)}</div><ol className="ptl-markets" data-testid="ptl-markets">{shownM.map(m => <li key={m.id}><button type="button" onClick={() => onCommand?.(`file a pob ${m.title}`)} data-tip="Puts it in the chat box. You press send"><span>{m.title}</span><small>{m.lead.name}</small><Bar v={m.lead.chance} /><b className="m-num">{pct(m.lead.chance)}</b><em data-tip="When it settles">{until(m.end)}</em></button></li>)}</ol></section> : null}
      {tab === 'gaps' ? <MarketGaps games={d.games} onCommand={onCommand} /> : null}</div>
      <LegSlip legs={legs} setLegs={setLegs} onCommand={onCommand} /></div></>;
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
export function ProofTools({ kind, onCommand, loadCalls = null, startOpen = true, onBrowse = null, rail = true }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [sport, setSport] = useState('all'); const [team, setTeam] = useState(''); const [open, setOpen] = useState(startOpen);
  useEffect(() => { let on = true; let first = true; const go = () => { if (document.hidden && !first) return; first = false; fetch(apiUrl(`/api/cats/tools/${kind}?sport=${sport}&team=${encodeURIComponent(team)}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { if (on) { setD(j); setErr(false); } }).catch(() => on && setErr(true)); };
    go(); const t = setInterval(go, 60000); return () => { on = false; clearInterval(t); }; }, [kind, sport, team]);
  return <details className="ptl" open={open} onToggle={e => setOpen(e.currentTarget.open)} data-testid={`ptl-${kind}`}><summary><b><Ic3 e="🧰" /> LIVE TOOLS</b><Sources rows={d?.sources} /></summary>
    {err && !d ? <p className="ptl-none" role="alert">These sources could not be read. It tries again in a minute.</p> : !d ? <p className="ptl-none">Reading its sources…</p>
      : kind === 'bids' ? <BidsDash d={d} sport={sport} setSport={setSport} team={team} setTeam={setTeam} onCommand={onCommand} loadCalls={loadCalls} /> : kind === 'pop' ? <PopDash d={d} onCommand={onCommand} /> : kind === 'content' ? <ContentDash d={d} /> : <PowDash d={d} onCommand={onCommand} />}
    {rail ? <div className="prm-rail">{kind === 'bids' ? <WatchRoom onBrowse={onBrowse} /> : <ProofCalc kind={kind} />}</div> : null}
  </details>;
}

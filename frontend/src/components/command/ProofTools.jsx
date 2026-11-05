import React, { useEffect, useState , useRef } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/proofTools.css';

// 🧰 THE PROOF FOLDER DASH (owner 2026-11-04): each folder opens on its top 5 free sources, live. PoB: pick a sport and a team, see the games and the parlays the market likes most, one tap files a proof on them. "Best" = the market's own odds, said so on screen.
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
const big = v => (v == null ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(0)}M` : `$${Math.round(v).toLocaleString('en-US')}`);
const shortMint = m => (m ? `${m.slice(0, 4)}…${m.slice(-4)}` : '');

function Sources({ rows }) {
  return <ul className="ptl-src" aria-label="Sources">{(rows || []).map(s => <li key={s.name} className={s.on ? 'is-on' : ''} data-tip={s.on ? `${s.use}. Read just now` : `${s.use}. Not read`}><i aria-hidden="true" />{s.name}</li>)}</ul>;
}
function Bar({ v, tone }) { return <span className={`ptl-bar ${tone || ''}`} aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, v || 0))})` }} /></span>; }

// 🖼 A real, freely licensed photo with its credit, or none. A team's logo is a trademark, so nothing is drawn in its place: the card just shows the teams.
function FreePhoto({ q, must }) {
  const [img, setImg] = useState(undefined); const box = useRef(null);
  useEffect(() => { let on = true; const load = () => fetch(apiUrl(`/api/cats/tools/image?q=${encodeURIComponent(q)}&must=${encodeURIComponent(must.join(','))}`)).then(r => (r.ok ? r.json() : null)).then(j => { if (on) setImg(j?.image || null); }).catch(() => on && setImg(null)); if (typeof IntersectionObserver === 'undefined') { load(); return () => { on = false; }; } const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { io.disconnect(); load(); } }, { rootMargin: '120px' }); if (box.current) io.observe(box.current); return () => { on = false; io.disconnect(); }; }, [q]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <span className="ptl-photo" ref={box}>{img ? <><img src={img.url} alt={img.title} loading="lazy" /><a href={img.page} target="_blank" rel="noopener noreferrer" data-tip={`${img.title}: ${img.license}`}>{img.by} · {img.license}</a></> : null}</span>;
}
const until = at => { const s = (new Date(at).getTime() - Date.now()) / 1000; if (!Number.isFinite(s)) return ''; if (s < 0) return 'now'; if (s < 3600) return `${Math.ceil(s / 60)}m`; if (s < 86400) return `${Math.round(s / 3600)}h`; return `${Math.round(s / 86400)}d`; };
function GameCard({ g, onCommand }) {
  const [a, b] = g.teams; const live = g.state === 'in'; const done = g.state === 'post';
  return <li className={`ptl-gcard is-${g.state}`} data-testid={`ptl-game-${g.id}`}><FreePhoto q={`${a.name} ${b.name}`} must={[a.short, b.short, a.name, b.name].filter(Boolean)} /><div className="ptl-g-b"><span className="ptl-g-tag">{live ? <em className="ptl-live" data-tip="Happening now">LIVE</em> : done ? <em>FINAL</em> : <em data-tip="Starts in">{until(g.at)}</em>}<small>{g.status}</small></span>{g.teams.map(t => <span key={t.name} className={`ptl-g-t${t.winner ? ' is-win' : ''}`}><b>{t.short || t.name}</b>{g.state !== 'pre' ? <i key={t.score} className="m-num">{t.score}</i> : <i className="m-num" data-tip="What the market prices">{t.chance ? pct(t.chance) : ''}</i>}</span>)}{done ? null : <button type="button" className="m-btn" onClick={() => onCommand?.(`file a pob ${a.short} vs ${b.short}`)} data-tip="Puts it in the chat box. You press send" data-testid={`ptl-file-${g.id}`}>File a pick</button>}</div></li>;
}
function BidsDash({ d, sport, setSport, team, setTeam, onCommand }) {
  const [mkt, setMkt] = useState('All'); const rows = d.markets || []; const cats = ['All', ...new Set(rows.map(m => m.cat))]; const shownM = (mkt === 'All' ? rows : rows.filter(m => m.cat === mkt)).slice(0, 12);
  return <>
    <div className="m-seg ptl-tabs" role="tablist" aria-label="Sport">{(d.sports || []).map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={sport === k} className={sport === k ? 'active' : ''} onClick={() => { setSport(k); setTeam(''); }} data-testid={`ptl-sport-${k}`}>{l}</button>)}</div>
    {sport === 'all' ? null : <select className="m-input ptl-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Team" data-testid="ptl-team"><option value="">All teams</option>{(d.teams || []).map(t => <option key={t} value={t}>{t}</option>)}</select>}
    {d.team ? <p className="ptl-card" data-testid="ptl-teamcard"><b>{d.team.name}</b> {d.team.league}{d.team.stadium ? ` · ${d.team.stadium}` : ''}{d.team.formed ? ` · since ${d.team.formed}` : ''}</p> : null}
    <section><h4><Ic3 e="🏟" /> Games <small>{d.live ? `${d.live} live now, first` : 'Coming up'}. Photos are free to use, with credit.</small></h4>{(d.games || []).length ? <ol className="ptl-gcards" data-testid="ptl-gcards">{d.games.slice(0, 18).map(g => <GameCard key={g.id} g={g} onCommand={onCommand} />)}</ol> : <p className="ptl-none">No games on its board right now.</p>}</section>
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
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; fetch(apiUrl(`/api/cats/tools/${kind}?sport=${sport}&team=${encodeURIComponent(team)}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { if (on) { setD(j); setErr(false); } }).catch(() => on && setErr(true)); };
    go(); const t = setInterval(go, 60000); return () => { on = false; clearInterval(t); }; }, [kind, sport, team]);
  return <details className="ptl" open={open} onToggle={e => setOpen(e.currentTarget.open)} data-testid={`ptl-${kind}`}><summary><b><Ic3 e="🧰" /> LIVE TOOLS</b><Sources rows={d?.sources} /></summary>
    {err && !d ? <p className="ptl-none" role="alert">These sources could not be read. It tries again in a minute.</p> : !d ? <p className="ptl-none">Reading its sources…</p>
      : kind === 'bids' ? <BidsDash d={d} sport={sport} setSport={setSport} team={team} setTeam={setTeam} onCommand={onCommand} /> : kind === 'pop' ? <PopDash d={d} onCommand={onCommand} /> : kind === 'content' ? <ContentDash d={d} /> : <PowDash d={d} onCommand={onCommand} />}
  </details>;
}

import React, { useEffect, useState } from 'react';
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

function BidsDash({ d, sport, setSport, team, setTeam, onCommand }) {
  return <>
    <div className="m-seg ptl-tabs" role="tablist" aria-label="Sport">{(d.sports || []).map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={sport === k} className={sport === k ? 'active' : ''} onClick={() => { setSport(k); setTeam(''); }} data-testid={`ptl-sport-${k}`}>{l}</button>)}</div>
    <select className="m-input ptl-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Team" data-testid="ptl-team"><option value="">All teams</option>{(d.teams || []).map(t => <option key={t} value={t}>{t}</option>)}</select>
    {d.team ? <p className="ptl-card" data-testid="ptl-teamcard"><b>{d.team.name}</b> {d.team.league}{d.team.stadium ? ` · ${d.team.stadium}` : ''}{d.team.formed ? ` · since ${d.team.formed}` : ''}</p> : null}
    <div className="ptl-grid">
      <section><h4><Ic3 e="🏆" /> Top parlays <small>market odds, not a promise</small></h4>
        {(d.parlays || []).length ? d.parlays.map(p => <button key={p.legs.join()} type="button" className="ptl-parlay" onClick={() => onCommand?.(`file a pob ${p.legs.join(' and ')}`)} data-tip="Puts it in the chat box. You press send" data-testid="ptl-parlay"><b className="m-num">{pct(p.chance)}</b><Bar v={p.chance} /><span>{p.legs.join(' + ')}</span><small>about {p.pays}x if all land</small></button>) : <p className="ptl-none">No priced games to combine right now.</p>}
        <h4><Ic3 e="🎯" /> Strongest sides</h4>{(d.legs || []).slice(0, 5).map(l => <button key={l.game} type="button" className="ptl-leg" onClick={() => onCommand?.(`file a pob ${l.pick}`)} data-testid="ptl-leg"><span>{l.pick}</span><Bar v={l.chance} tone="is-b" /><b className="m-num">{pct(l.chance)}</b></button>)}</section>
      <section><h4><Ic3 e="🏟" /> Games</h4><ol className="ptl-games">{(d.games || []).slice(0, 10).map(g => <li key={g.id} className={`is-${g.state}`}>{g.teams.map(t => <span key={t.name} className={t.winner ? 'is-win' : ''}><b>{t.short}</b>{g.state !== 'pre' ? <em className="m-num">{t.score}</em> : <em className="m-num" data-tip={t.kalshi ? `Polymarket ${pct(t.chance)}, Kalshi ${pct(t.kalshi)}` : 'Polymarket'}>{pct(t.chance)}{t.kalshi ? ` · ${pct(t.kalshi)}` : ''}</em>}</span>)}<small>{g.status}{g.line ? ` · ${g.line}` : ''}</small></li>)}</ol></section>
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
function PopDash({ d, onCommand }) {
  return <><div className="ptl-vitals"><span><em>MOOD</em><b>{d.mood || '—'}</b><small>{d.moodValue}/100</small></span><span><em>BTC SPOT</em><b className="m-num">{d.btcSpot ? `$${Math.round(d.btcSpot).toLocaleString('en-US')}` : '—'}</b></span><span><em>BTC DOMINANCE</em><b className="m-num">{d.btcDom ? `${d.btcDom.toFixed(1)}%` : '—'}</b></span><span><em>PERP VOLUME 24H</em><b className="m-num">{big(d.perpVol24h)}</b></span></div>
    <div className="ptl-grid"><section><h4>Biggest markets</h4><ol className="ptl-list">{(d.markets || []).slice(0, 6).map(m => <li key={m.market}><button type="button" className="ptl-link" onClick={() => onCommand?.('file a perp')} data-tip="Puts “file a perp” in the chat box"><b>{m.market}</b> ${m.price.toLocaleString('en-US')}</button><small>OI {big(m.oiUsd)}</small></li>)}</ol></section>
      <section><h4>Hottest funding</h4><ol className="ptl-list">{(d.hotFunding || []).map(m => <li key={m.market}><b>{m.market}</b><em className={`m-num ${m.fundingPct >= 0 ? 'is-up' : 'is-dn'}`}>{m.fundingPct > 0 ? '+' : ''}{m.fundingPct}%/h</em></li>)}</ol></section></div></>;
}
export function ProofTools({ kind, onCommand }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [sport, setSport] = useState('nfl'); const [team, setTeam] = useState(''); const [open, setOpen] = useState(true);
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; fetch(apiUrl(`/api/cats/tools/${kind}?sport=${sport}&team=${encodeURIComponent(team)}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { if (on) { setD(j); setErr(false); } }).catch(() => on && setErr(true)); };
    go(); const t = setInterval(go, 60000); return () => { on = false; clearInterval(t); }; }, [kind, sport, team]);
  return <details className="ptl" open={open} onToggle={e => setOpen(e.currentTarget.open)} data-testid={`ptl-${kind}`}><summary><b><Ic3 e="🧰" /> LIVE TOOLS</b><Sources rows={d?.sources} /></summary>
    {err && !d ? <p className="ptl-none" role="alert">These sources could not be read. It tries again in a minute.</p> : !d ? <p className="ptl-none">Reading its sources…</p>
      : kind === 'bids' ? <BidsDash d={d} sport={sport} setSport={setSport} team={team} setTeam={setTeam} onCommand={onCommand} /> : kind === 'pop' ? <PopDash d={d} onCommand={onCommand} /> : <PowDash d={d} onCommand={onCommand} />}
  </details>;
}

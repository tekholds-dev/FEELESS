import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';

// 📺 Live games beside the stream (owner 2026-11-10: "if they added nfl+ or nba tv to each room ... how agents work live"). The screens play your own
// NFL+ / NBA TV / ESPN in their official players; this reads ESPN's free public scoreboard: live score, clock, the last play, the home side's win
// chance after every play, the line, and where the game is on TV (one tap opens that service in its browser, where you sign in yourself).
// Team colours and short names only, never league logos.
export const LEAGUES = [['nba', 'NBA'], ['nfl', 'NFL'], ['cfb', 'College FB'], ['cbb', 'College BB'], ['nhl', 'NHL'], ['mlb', 'MLB']];
const TV = [[/ESPN|ABC/i, 'espn.com/watch'], [/NBA TV|League Pass/i, 'nba.com/watch'], [/NFL|CBS|FOX|NBC/i, 'nfl.com/plus'], [/Prime/i, 'amazon.com/primevideo'], [/Peacock/i, 'peacocktv.com'], [/Netflix/i, 'netflix.com'], [/TNT|truTV|Max/i, 'max.com'], [/MLB/i, 'mlb.tv'], [/NHL/i, 'nhl.com/video']];
export const tvHost = name => TV.find(([re]) => re.test(name))?.[1] || null;
const pct = v => (v == null ? '–' : `${v > 99 || v < 1 ? v.toFixed(1) : Math.round(v)}%`);   // 99.9% never rounds up to a sure thing
const usePoll = (url, ms) => {
  const [d, setD] = useState(null);
  useEffect(() => { if (!url) { setD(null); return undefined; } let live = true; const go = () => { if (document.hidden) return; fetch(apiUrl(url)).then(r => (r.ok ? r.json() : null)).then(j => live && j && setD(j)).catch(() => {}); };
    setD(null); go(); const t = setInterval(go, ms); return () => { live = false; clearInterval(t); }; }, [url, ms]);
  return d;
};
function WinLine({ pts, home, away }) {
  if (!pts?.length) return <p className="wl-none">Win chance shows once the game starts.</p>;
  const path = pts.map((v, i) => `${(i / Math.max(1, pts.length - 1)) * 200},${60 - (v / 100) * 60}`).join(' ');
  return <div className="wl-win"><svg viewBox="0 0 200 60" preserveAspectRatio="none" aria-label={`${home} win chance over the game, now ${pct(pts.at(-1))}`}><line x1="0" y1="30" x2="200" y2="30" /><polyline points={path} /></svg>
    <span><small>{home}</small><b className="m-num">{pct(pts.at(-1))}</b><small>{away}</small><b className="m-num">{pct(100 - pts.at(-1))}</b></span></div>;
}
export function WatchLive({ onBrowse, onCommand, price = '' }) {
  const [lg, setLg] = useState(() => { try { return localStorage.getItem('feeless.watch.lg') || 'nba'; } catch { return 'nba'; } });
  const [sel, setSel] = useState(null);
  const pick = v => { setLg(v); setSel(null); try { localStorage.setItem('feeless.watch.lg', v); } catch { /* still switches */ } };
  const b = usePoll(`/api/cats/scores/${lg}`, 20000); const games = b?.games || []; const g = games.find(x => x.id === sel) || games.find(x => x.state === 'in') || null;
  const one = usePoll(g ? `/api/cats/scores/${lg}/${g.id}` : null, 20000);
  return <section className="wl" data-testid="watch-live">
    <header className="wl-h"><span className="m-seg" role="radiogroup" aria-label="League">{LEAGUES.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={lg === k} className={lg === k ? 'active' : ''} onClick={() => pick(k)} data-testid={`wl-lg-${k}`}>{l}</button>)}</span>
      <small className="wl-src">LIVE FROM ESPN'S PUBLIC SCOREBOARD · EVERY 20 S</small></header>
    {games.length ? <ul className="wl-games" aria-label="Games">{games.map((x, i) => <li key={x.id} style={{ '--i': Math.min(i, 10) }}><button type="button" className={`is-${x.state}${g?.id === x.id ? ' is-on' : ''}`} aria-pressed={g?.id === x.id} onClick={() => setSel(x.id)} data-tip={x.last || x.detail} data-testid={`wl-game-${x.id}`}>
      <span className="wl-row"><i style={{ background: x.away.color || '#556' }} /><b>{x.away.abbr}</b><em className="m-num">{x.state === 'pre' ? '' : x.away.score}</em></span>
      <span className="wl-row"><i style={{ background: x.home.color || '#556' }} /><b>{x.home.abbr}</b><em className="m-num">{x.state === 'pre' ? '' : x.home.score}</em></span>
      <small>{x.state === 'in' ? <><s className="wl-dot" />{x.detail}</> : x.state === 'pre' ? new Date(x.start).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : x.detail}</small>
      {x.homeWin != null ? <u aria-hidden="true"><s style={{ transform: `scaleX(${x.homeWin / 100})` }} /></u> : null}</button></li>)}</ul>
      : <p className="wl-none">{b ? (b.ok ? 'No games on this league today.' : 'ESPN did not answer. Trying again in 20 seconds.') : 'Reading the scoreboard…'}</p>}
    {g ? <article className="wl-side" data-testid="wl-side">
      <div className="wl-bug"><span style={{ '--c': g.away.color || '#556' }}><b>{g.away.name}</b><small>{g.away.record || ''}</small><em className="m-num" key={`a${g.away.score}`}>{g.away.score}</em></span>
        <small className="wl-clock">{g.state === 'in' ? <s className="wl-dot" /> : null}{g.detail}</small>
        <span style={{ '--c': g.home.color || '#556' }}><em className="m-num" key={`h${g.home.score}`}>{g.home.score}</em><b>{g.home.name}</b><small>{g.home.record || ''}</small></span></div>
      <WinLine pts={one?.win} home={g.home.abbr} away={g.away.abbr} />
      <div className="wl-facts">{one?.spread ? <span><small>LINE</small><b className="m-num">{one.spread}</b></span> : null}{one?.total ? <span><small>TOTAL</small><b className="m-num">{one.total}</b></span> : null}{one?.by ? <span><small>FROM</small><b>{one.by}</b></span> : null}</div>
      <h6><Ic3 e="🧠" size="14px" /> PLAY BY PLAY · WHAT ITS AGENT READS</h6>
      <ol className="wl-plays">{(one?.plays?.length ? one.plays : g.last ? [{ text: g.last }] : []).map((p, i) => <li key={`${i}-${p.text}`} className={p.score ? 'is-score' : ''}>{p.clock ? <em className="m-num">Q{p.period} {p.clock}</em> : null}{p.text}</li>)}</ol>
      <footer className="wl-do">{(g.tv || []).map(n => { const h = tvHost(n); return h && onBrowse ? <button key={n} type="button" className="m-btn" onClick={() => onBrowse(h)} data-tip={`On ${n}. Opens ${h} in its browser, where you sign in yourself`} data-testid={`wl-tv-${n}`}>📺 {n}</button> : <span key={n} className="m-chip">{n}</span>; })}
        {onCommand && g.state !== 'post' ? <button type="button" className="m-btn m-go" onClick={() => onCommand(`file a pob ${g.away.name} vs ${g.home.name}`)} data-tip={`Puts it in the agent chat. You press send. Two minds pick, the final score grades it${price ? `. ${price}` : ''}`} data-testid="wl-pob">🎯 File a PoB on this game{price ? ` · ${price}` : ''}</button> : null}</footer>
    </article> : null}
  </section>;
}

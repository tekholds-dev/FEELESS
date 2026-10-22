import React, { useEffect, useState } from 'react';
import { RankBadge } from './FamiliaHud';
import '../styles/mobHome.css';

// 🌹 THE MOB LANDING around Fee City (owner, 2026-10-21: "finish the whole mob landing … the city + real-time data + how families work,
// top to bottom"). Researched references, each given a FEELESS twist: Clash of Clans (your base IS the home screen, a resource bar, a big
// attack button), Call of Duty / Fortnite (rank emblem + XP to the next division, the season clock, a kill feed), GTA Online (what is
// happening in session, on the map), Uniswap / Solana (play before you connect; the hero is live numbers, not copy). Every number is the
// server's (familia-world). transform / opacity only.
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');

// pure: the season = the calendar month (family_world.season) → days left + share gone
export function seasonClock(nowMs = Date.now()) {
  const d = new Date(nowMs); const start = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1); const end = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1);
  const left = Math.max(0, end - nowMs);
  return { left, pct: (nowMs - start) / (end - start), d: Math.floor(left / 864e5), h: Math.floor((left % 864e5) / 36e5), m: Math.floor((left % 36e5) / 6e4) };
}

// pure: the one move that grows this family most right now (shown in the loop's centre)
export function nextMove(v) {
  const me = v.me; const r = v.rules || {};
  if (!me) return { k: 'join', word: 'Start or join a family — your home block is free', go: 'join' };
  const free = (v.blocks || []).filter(b => !b.owner && me.prices?.[b.id] != null).sort((a, b) => me.prices[a.id] - me.prices[b.id])[0];
  if (me.errands?.some(e => e.lvl && !e.ready)) return { k: 'earn', word: 'An errand is ready — run it for MP', go: 'jobs' };
  if (free && me.bank >= me.prices[free.id] && (me.turf || []).length < (r.turfMax || 12)) return { k: 'turf', word: `Buy turf: ${n(me.prices[free.id])} MP gets a plot (+4 % production, more reach)`, go: 'map' };
  if ((me.hitters || []).length && !(v.raids || []).some(x => x.status === 'live')) return { k: 'raid', word: `${me.hitters.length} hitter${me.hitters.length === 1 ? '' : 's'} ready — raid a rival in reach`, go: 'raids' };
  if (me.boss && (me.bank || 0) >= (r.fuseMinMp || 2000)) return { k: 'fuse', word: 'The bank can back an MP Family Fuse — call a family out', go: 'fuse' };
  return { k: 'build', word: 'Collect the stash and build a bigger store on your block', go: 'block' };
}

export function SeasonHud({ v, onJoin, go }) {
  const [c, setC] = useState(() => seasonClock());
  useEffect(() => { const t = setInterval(() => setC(seasonClock()), 30000); return () => clearInterval(t); }, []);
  const me = v.me; const held = (v.blocks || []).filter(b => b.owner).length; const fights = (v.ffuse?.fights || []).filter(f => f.status === 'live').length;
  const raids = (v.raids || []).filter(r => r.status === 'live').length;
  return <header className="mh-hud" data-testid="season-hud">
    <div className="mh-me">{me ? <><i className="mh-tag">{me.tag}</i>{me.rank ? <RankBadge rank={me.rank} /> : null}
      {me.rank?.next ? <span className="mh-xp" data-tip={`Power to ${me.rank.name} next division`}><u><s style={{ transform: `scaleX(${Math.max(0.03, (me.rank.pct || 0) / 100)})` }} /></u><small>{me.rank.pct}% · #{me.place || '—'}</small></span> : null}</>
      : <><i className="mh-tag is-ghost">?</i><span className="mh-ghost"><b>Your family goes here</b><small>walk the city first — no wallet needed</small></span>
        <button type="button" className="m-btn m-go" onClick={onJoin} data-testid="hud-join">Start or join</button></>}</div>
    <div className="mh-season"><em>SEASON · {v.season?.name || '—'}</em><b key={c.m}>{c.d}d {c.h}h {c.m}m</b><u data-tip="How much of the season has run — the board pays the top families at the end"><s style={{ transform: `scaleX(${c.pct})` }} /></u></div>
    {(() => { const nm = nextMove(v); return <button type="button" className={`mh-next k-${nm.k}`} onClick={() => (go ? go(nm.go) : onJoin?.())} data-tip="The one move that grows your family most right now" data-testid="hud-next"><em>NEXT MOVE</em><b>{nm.word}</b></button>; })()}
    <div className="mh-res">{(me ? [['BANK', `${n(me.bank)} MP`, 'MP in the family bank'], ['YOUR PTS', n(me.pts), 'Your member points — errands, rewards, crowd bids'], ['TURF', `${(me.turf || []).length}/${v.rules?.turfMax || 12}`, 'Plots held beyond home']]
      : [['PLOTS HELD', `${held}/${(v.blocks || []).length}`, 'Every city'], ['FAMILIES', n((v.ranked || []).length), 'Ranked families'], ['CARTELS', n((v.cartels || []).length), 'Flagged wallet crews across the water']])
      .concat([['⚔ LIVE', `${raids} raid${raids === 1 ? '' : 's'} · ${fights} fuse`, 'Raids you are in + Family Fuse fights running now']])
      .map(([k, val, tip], i) => <span key={k} style={{ '--i': i }} data-tip={tip}><em>{k}</em><b key={val}>{val}</b></span>)}</div>
  </header>;
}

// 📡 THE WIRE — the city's kill feed, on the map (raids, Family Fuse results, buys)
export function TheWire({ log }) {
  const rows = (log || []).slice(0, 5);
  if (!rows.length) return null;
  return <ol className="mh-wire" aria-label="The Wire — what just happened in the city" data-testid="the-wire">{rows.map((l, i) => <li key={`${l.at}-${i}`} style={{ '--i': i }}>{l.what}</li>)}</ol>;
}

// the big action buttons on the city (a Clash-style attack button, FEELESS-ified)
export function CityActions({ v, go }) {
  const me = v.me; const live = (v.raids || []).some(r => r.status === 'live');
  return <div className="mh-acts" data-testid="city-actions">
    <button type="button" className={`mh-act k-raid ${live ? 'is-hot' : ''}`} onClick={() => go('raids')} data-tip={live ? 'Your raid is live — make your move' : 'Raids: pick a rival block on the city, then send a hitter'} data-testid="act-raid"><i>⚔</i><b>RAID</b></button>
    <button type="button" className="mh-act k-fuse" onClick={() => go('fuse')} data-tip="Family Fuse in the Fuse Arena stadium" data-testid="act-fuse"><i>🧬</i><b>FUSE</b></button>
    <button type="button" className="mh-act k-earn" onClick={() => go('jobs')} disabled={!me} data-tip={me ? 'Errands pay MP + your points' : 'Join a family to run errands'} data-testid="act-earn"><i>💰</i><b>EARN</b></button>
  </div>;
}

// 🏙 THE POWER SKYLINE — the top families as towers (height = power), their neon tag on the roof, their rank at the door
export function PowerSkyline({ v, onPick, onEmpty }) {
  const top = (v.ranked || []).slice(0, 10); const max = Math.max(1, ...top.map(r => r.power || 0));
  return <section className="mh-sky m-card" data-testid="power-skyline">
    <header><span className="m-label">🏙 THE POWER SKYLINE · TOP FAMILIES</span><small>Tower height = family power · tap a tower to fly to its home block</small></header>
    {top.length ? <div className="mh-towers">{top.map((r, i) => <button key={r.id} type="button" className={`mh-tower ${r.id === v.me?.id ? 'is-mine' : ''}`} style={{ '--h': Math.max(0.12, (r.power || 0) / max), '--i': i, '--fc': r.color || '#d4af37' }}
      onClick={() => onPick(r)} data-tip={`#${r.place} [${r.tag}] ${r.name} · power ${n(r.power)} · ${r.rank.name} ${r.rank.div}`} data-testid={`tower-${r.tag}`}>
      <span className="mh-tb"><i className="mh-tsign">{r.tag}</i><i className="mh-twin" /></span><RankBadge rank={r.rank} size="sm" /><em>#{r.place}</em><small key={r.power}>{n(r.power)}</small></button>)}
      {Array.from({ length: Math.max(0, 6 - top.length) }, (_, k) => <button key={`e${k}`} type="button" className="mh-tower is-empty" style={{ '--h': 0.18 + (k % 3) * 0.08, '--i': top.length + k }} onClick={onEmpty}
        data-tip="An empty spot on the skyline — buy plots and build to rise into it" data-testid={`tower-empty-${k}`}><span className="mh-tb"><i className="mh-tsign">#{top.length + k + 1}</i></span><em>CLAIM IT</em></button>)}</div>
      : <p className="m-dim">No families on the skyline yet — the first one builds the tallest tower.</p>}
  </section>;
}

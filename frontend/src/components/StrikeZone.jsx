import React, { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { gunStats, xpBar, BOT_DIFF } from '../lib/strikeGame';
import { tgInitData } from '../lib/telegram';
import '../styles/strikeZone.css';

// 🎯 STRIKE ZONE — the lobby (owner 2026-10-27: "a third-person shooter instead of the raceway, vs bots or online, real levelling + gun
// customisation"). Your level + XP bar, the GUNSMITH (4 guns × barrel · optic · magazine · stock · skin — each part unlocks at a level, the
// stats bars move as you build), the mode (BOTS easy / normal / hard · ONLINE room), today's leaders. PLAY opens the match full screen
// (StrikeGame — three.js loads only then). XP + loadout are saved on the server (arena.py) for a wallet or a Telegram player.
const StrikeGame = lazy(() => import('./StrikeGame').then(m => ({ default: m.StrikeGame })));
const SLOTS = [['barrel', 'BARREL'], ['optic', 'OPTIC'], ['mag', 'MAGAZINE'], ['stock', 'STOCK'], ['skin', 'SKIN']];
const SKIN_C = { green: '#15d16a', carbon: '#3a3f44', pink: '#ff5dbb', ice: '#8fd3ff', gold: '#f5c451' };
const BARS = [['dmg', 'DAMAGE', 100], ['rpm', 'FIRE RATE', 950], ['range', 'RANGE', 320], ['mag', 'MAGAZINE', 64], ['spread', 'ACCURACY', 0.09, true], ['recoil', 'CONTROL', 1.3, true], ['speed', 'MOBILITY', 1.15]];

function GunArt({ lo }) {   // the drawn gun — every part you pick changes the picture
  const c = SKIN_C[lo.skin] || '#15d16a'; const big = lo.gun === 'sniper' ? 1.25 : lo.gun === 'smg' ? 0.82 : 1; const bl = lo.barrel === 'long' ? 70 : lo.barrel === 'short' ? 26 : lo.barrel === 'supp' ? 64 : 46;
  return <svg viewBox="0 0 300 110" className="sz-gun" aria-hidden="true">
    <rect x={150 - 70 * big} y="44" width={140 * big} height="20" rx="4" fill={c} />
    <rect x={150 + 70 * big} y={lo.barrel === 'supp' ? 47 : 50} width={bl} height={lo.barrel === 'supp' ? 14 : 8} rx="2" fill="#1c2024" />
    {lo.optic === 'scope' ? <rect x="120" y="28" width="64" height="12" rx="6" fill="#1c2024" /> : lo.optic === 'iron' ? <rect x={150 + 50 * big} y="38" width="6" height="8" fill="#1c2024" /> : <rect x="138" y="30" width={lo.optic === 'holo' ? 30 : 22} height="14" rx="3" fill="#1c2024" />}
    <rect x="132" y="64" width="16" height={lo.mag === 'ext' ? 34 : lo.mag === 'drum' ? 26 : 24} rx="3" fill="#1c2024" />{lo.mag === 'drum' ? <circle cx="140" cy="92" r="12" fill="#1c2024" /> : null}
    <rect x="108" y="64" width="12" height="22" rx="3" fill="#2a2f34" />
    <rect x={150 - 70 * big - (lo.stock === 'light' ? 30 : 48)} y={lo.stock === 'heavy' ? 42 : 46} width={lo.stock === 'light' ? 30 : 48} height={lo.stock === 'heavy' ? 26 : 16} rx="4" fill={lo.stock === 'heavy' ? c : '#2a2f34'} />
  </svg>;
}

export function StrikeZone({ addr = '', sess = '', family = null, onDone }) {
  const [d, setD] = useState(null); const [lo, setLo] = useState(null); const [mode, setMode] = useState('bots'); const [diff, setDiff] = useState('normal');
  const [room, setRoom] = useState('fee-city'); const [playing, setPlaying] = useState(false); const [msg, setMsg] = useState(''); const [last, setLast] = useState(null);
  const tg = tgInitData(); const who = useMemo(() => (addr && sess ? { address: addr, session: sess } : tg ? { tg } : {}), [addr, sess, tg]);
  const load = useCallback(() => { const q = addr && sess ? `?address=${addr}&session=${encodeURIComponent(sess)}` : tg ? `?tg=${encodeURIComponent(tg)}` : '';
    return fetch(apiUrl(`/api/reputation/arena${q}`)).then(r => (r.ok ? r.json() : null)).then(x => { if (x) { setD(x); setLo(l => l || x.me.loadout); } }).catch(() => {}); }, [addr, sess, tg]);
  useEffect(() => { load(); }, [load]);
  if (!d || !lo) return <div className="sz sz-wait" data-testid="strike-zone">Loading the Strike Zone…</div>;
  const me = d.me; const un = me.unlocked || { guns: ['rifle'], parts: {} }; const g = gunStats(d, lo); const guest = !!me.guest;
  const pick = (slot, id) => { const next = { ...lo, [slot]: id }; setLo(next); if (guest) return;
    fetch(apiUrl('/api/reputation/arena/loadout'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...who, loadout: next }) }).then(r => (r.ok ? r.json() : null)).then(x => x && setLo(x.loadout)).catch(() => {}); };
  const name = family?.tag ? `[${family.tag}]` : tg ? 'tg player' : 'you';
  return <section className="sz" data-testid="strike-zone">
    <header className="sz-top">
      <span className="sz-lvl" style={{ '--p': xpBar(me) }} data-tip={`${me.into} / ${me.need} XP to level ${me.level + 1}`}><i aria-hidden="true" /><b className="m-num">{me.level}</b><em>LEVEL</em></span>
      <span className="sz-title"><em>FEE CITY · THIRD-PERSON</em><b>STRIKE ZONE</b><small>{guest ? 'playing as a guest — sign in (wallet or Telegram) to keep XP + your guns' : `${me.xp.toLocaleString('en-US')} XP · ${me.kills} kills · ${me.wins} wins${family ? ' · your kills feed the family bank' : ''}`}</small>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${xpBar(me)})` }} /></u></span>
      <span className="m-seg sz-mode" role="radiogroup" aria-label="Mode">{[['bots', '🤖 VS BOTS'], ['online', '🌐 ONLINE']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-testid={`sz-mode-${k}`}>{l}</button>)}</span>
    </header>
    <div className="sz-main">
      <div className="sz-smith" data-testid="sz-smith">
        <span className="m-seg sz-guns" role="radiogroup" aria-label="Gun">{Object.entries(d.guns).map(([k, x]) => { const ok = un.guns.includes(k); return <button key={k} type="button" role="radio" aria-checked={lo.gun === k} className={lo.gun === k ? 'active' : ''} disabled={!ok}
          onClick={() => pick('gun', k)} data-tip={ok ? x.name : `Unlocks at level ${x.level}`} data-testid={`sz-gun-${k}`}>{ok ? '' : '🔒 '}{x.name}</button>; })}</span>
        <GunArt lo={lo} />
        <div className="sz-bars">{BARS.map(([k, l, max, inv], i) => { const v = inv ? 1 - Math.min(1, g[k] / max) : Math.min(1, g[k] / max); return <span key={k} style={{ '--i': i }}><em>{l}</em><u><s style={{ transform: `scaleX(${Math.max(0.04, v)})` }} /></u><b className="m-num">{k === 'spread' ? `${Math.round(v * 100)}` : k === 'recoil' ? `${Math.round(v * 100)}` : k === 'speed' ? `${Math.round(g[k] * 100)}%` : Math.round(g[k])}</b></span>; })}</div>
        <div className="sz-slots">{SLOTS.map(([slot, l]) => <span key={slot} className="sz-slot"><em>{l}</em><span className="sz-parts">{(d.parts[slot] || []).map(p => { const ok = (un.parts[slot] || []).includes(p.id);
          return <button key={p.id} type="button" className={`${lo[slot] === p.id ? 'is-on' : ''} ${slot === 'skin' ? 'is-skin' : ''}`} style={slot === 'skin' ? { '--sk': SKIN_C[p.id] } : null} disabled={!ok} onClick={() => pick(slot, p.id)}
            data-tip={ok ? p.name : `${p.name} — unlocks at level ${p.level}`} data-testid={`sz-${slot}-${p.id}`}>{ok ? '' : '🔒'}{slot === 'skin' ? <i /> : null}{p.name}</button>; })}</span></span>)}</div>
      </div>
      <aside className="sz-side">
        {mode === 'bots' ? <span className="m-seg sz-diff" role="radiogroup" aria-label="Difficulty">{Object.entries(BOT_DIFF).map(([k, x]) => <button key={k} type="button" role="radio" aria-checked={diff === k} className={diff === k ? 'active' : ''} onClick={() => setDiff(k)} data-tip={`${x.n} bots · ${Math.round(x.acc * 100)}% aim · ${x.react}s to react`} data-testid={`sz-diff-${k}`}>{k.toUpperCase()}</button>)}</span>
          : <label className="sz-room"><span>ROOM</span><input value={room} onChange={e => setRoom(e.target.value.replace(/[^a-z0-9-_]/gi, '').slice(0, 24))} aria-label="Room name" data-testid="sz-room" /><small>{(d.rooms || []).find(r => r.room === room)?.n || 0} in it now · share the name with your family</small></label>}
        <button type="button" className="m-btn m-go sz-play" onClick={() => { setMsg(''); setPlaying(true); }} data-tip="Opens full screen — first to the kill target or the clock" data-testid="sz-play">🎯 PLAY · {mode === 'bots' ? `${BOT_DIFF[diff].n} BOTS` : room}</button>
        <small className="sz-xp">XP: {d.xp.kill} a kill · +{d.xp.head} headshot · +{d.xp.win} win{family ? ' · +5 MP a kill to the family bank (150 / day)' : ''}</small>
        {last ? <p className="sz-last">Last match: {last.k} kills · {last.d} deaths{last.xp ? ` · +${last.xp} XP` : ''}</p> : null}
        {msg ? <p className="sz-msg">{msg}</p> : null}
        <ol className="sz-board" aria-label="Today's leaders">{(d.board || []).slice(0, 8).map(r => <li key={r.place} style={{ '--i': r.place }}><i>#{r.place}</i><b>{r.tag ? `[${r.tag}] ` : ''}{r.name}</b><small>LV {r.level} · {r.kills} kills</small><em className="m-num">{r.xp.toLocaleString('en-US')} XP</em></li>)}
          {!(d.board || []).length ? <li className="sz-empty">No one on the board today — take #1.</li> : null}</ol>
      </aside>
    </div>
    {playing ? <Suspense fallback={null}><StrikeGame catalog={d} loadout={lo} mode={mode} diff={diff} room={room} who={who} name={name}
      onExit={r => { setPlaying(false); if (r) setLast(r); load(); onDone?.(); if (r?.again) setTimeout(() => setPlaying(true), 50); }} /></Suspense> : null}
  </section>;
}

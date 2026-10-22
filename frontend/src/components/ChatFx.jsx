import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useCoinMood } from '../lib/coinMood';
import { sweepable } from '../lib/cacheSweep';
import '../styles/chatThemes.css';

// 🎨 Animated chat backgrounds (styles/chatThemes.css), chosen per room in every chat's ⚙ / 🎨 (saved as themes[room]: a coin's chat, the Brain
// ('brain'), the inbox ('inbox')). Drawn from the trade itself — candles, order flow, depth, the radar, a ticker tape, the moon run, liquidation
// lava, the reserve vortex, the gold vault — always with the FEE mark. Free: 4 · $FEE ≥ $5: 4 more · ≥ $100: 5 more (badge perks unlock some).
export const CHAT_THEMES = [
  ['live', 'Live mood', 0], ['fee', 'FEE glow', 0], ['candles', 'Candle rain', 0], ['off', 'Plain', 0],
  ['flow', 'Order flow', 5], ['depth', 'Depth', 5], ['radar', 'Trench radar', 5], ['grid', 'Terminal', 5],
  ['tape', 'Ticker tape', 100], ['moon', 'Moon run', 100], ['lava', 'Liquidation lava', 100], ['vortex', 'Reserve vortex', 100], ['gold', 'Gold vault', 100],
];
const NEED = Object.fromEntries(CHAT_THEMES.map(([id, , usd]) => [id, usd]));
// Unlocked by $FEE held, or by a badge perk (e.g. FRSV VIP → Vortex): `unlocked` is the perk list from your badges.
export const canUse = (id, feeUsd, unlocked = []) => (Number(feeUsd) || 0) >= (NEED[id] ?? Infinity) || unlocked.includes(id);
// A saved theme you no longer qualify for falls back to Live (nothing breaks, nothing is lost).
export const chatTheme = (prefs, room, feeUsd = Infinity, unlocked = []) => { const t = (prefs?.themes || {})[room] || 'live'; return canUse(t, feeUsd, unlocked) ? t : 'live'; };

const tiers = sweepable('chatTiers', new Map(), { ttl: 900000, max: 300 });
const perkCache = sweepable('chatPerks', new Map(), { ttl: 900000, max: 300 });
export function useBadgeBgs(address) {
  const [bgs, setBgs] = useState([]);
  useEffect(() => {
    if (!address) { setBgs([]); return undefined; }
    let alive = true; const hit = perkCache.get(address);
    const p = hit && Date.now() - hit.at < 300000 ? hit.p : fetch(apiUrl(`/api/reputation/quests/${address}`)).then(r => (r.ok ? r.json() : null)).then(d => d?.perks?.chatBgs || []).catch(() => []);
    if (!hit || hit.p !== p) perkCache.set(address, { at: Date.now(), p });
    p.then(v => alive && setBgs(v));
    return () => { alive = false; };
  }, [address]);
  return bgs;
}

export function useFeeUsd(address) {
  const [usd, setUsd] = useState(0);
  useEffect(() => {
    if (!address) { setUsd(0); return undefined; }
    let alive = true; const hit = tiers.get(address);
    const p = hit && Date.now() - hit.at < 300000 ? hit.p : Promise.all([
      fetch(apiUrl(`/api/reputation/perks/${address}`)).then(r => (r.ok ? r.json() : null)).catch(() => null),
      fetch(apiUrl(`/api/reputation/theme/${address}`)).then(r => (r.ok ? r.json() : null)).catch(() => null),
    ]).then(([perk, theme]) => (theme?.staff ? Infinity : Number(perk?.feeUsd) || 0));   // admins + creators: everything unlocked
    if (!hit || hit.p !== p) tiers.set(address, { at: Date.now(), p });
    p.then(v => alive && setUsd(v));
    return () => { alive = false; };
  }, [address]);
  return usd;
}

const TICKS = [['$SOL', '+4.2%', 1], ['$BONK', '−3.1%', 0], ['$WIF', '+12.8%', 1], ['$FEE', '+6.6%', 1], ['$POPCAT', '−8.4%', 0], ['$JUP', '+1.9%', 1], ['$MEW', '+22%', 1], ['$PNUT', '−5.2%', 0], ['$GOAT', '+3.3%', 1], ['$TRUMP', '−1.4%', 0]];
// the drawn parts of each scene (the two gradient layers come from the sheet)
const SCENE = {
  candles: () => <span className="cfx-strip">{Array.from({ length: 18 }, (_, i) => <b key={i} className={`cfx-candle ${i % 3 === 1 ? 'dn' : 'up'}`} style={{ left: `${5 + (i % 9) * 11}%`, top: `${(i < 9 ? 0 : 50) + ((i * 37) % 44)}%`, '--h': `${18 + ((i * 13) % 26)}px` }} />)}</span>,
  flow: () => Array.from({ length: 10 }, (_, i) => <s key={i} className={`cfx-bar ${i % 2 ? 's' : 'b'}`} style={{ top: `${8 + i * 9}%`, '--i': i, '--w': `${22 + ((i * 17) % 30)}%` }} />),
  depth: () => <svg className="cfx-depth" viewBox="0 0 200 60" preserveAspectRatio="none"><path className="bid" d="M0,60 V18 H22 V26 H40 V33 H58 V40 H76 V47 H92 V54 H100 V60 Z" /><path className="ask" d="M200,60 V12 H176 V22 H156 V30 H138 V38 H122 V46 H108 V54 H100 V60 Z" /><path className="mid" d="M100,0 V60" /></svg>,
  radar: () => [[30, 40], [64, 30], [58, 70], [24, 66]].map(([x, y], i) => <u key={i} className="cfx-blip" style={{ left: `${x}%`, top: `${y}%`, '--i': i }} />),
  tape: () => [0, 1, 2, 3].map(c => <span key={c} className="cfx-col" style={{ left: `${4 + c * 25}%`, '--i': c }}>{[...TICKS, ...TICKS].map(([t, p, up], k) => <em key={k} className={up ? 'up' : 'dn'}>{t} {p}</em>)}</span>),
  moon: () => <><u className="cfx-moon" /><u className="cfx-rocket" /></>,
  lava: () => <span className="cfx-strip is-up">{Array.from({ length: 10 }, (_, i) => <u key={i} className="cfx-blob" style={{ left: `${4 + (i % 5) * 19}%`, top: `${(i < 5 ? 0 : 50) + ((i * 29) % 40)}%`, '--i': i, '--s': `${50 + ((i * 23) % 50)}px` }} />)}</span>,
  vortex: () => [70, 110, 150].map((r, i) => <span key={r} className="cfx-orbit" style={{ '--i': i, '--r': `${r}px` }}><img src="/assets/feeless-logo.png" alt="" /></span>),
  gold: () => <><u className="cfx-dial" /><u className="cfx-bars" /></>,
};
export function ChatFx({ theme, room }) {
  const mood = useCoinMood(theme === 'live' ? room : null);
  if (theme === 'off') return null;
  return <div className={`chat-fx fx-${theme}${theme === 'live' ? ` mood-${mood}` : ''}`} aria-hidden="true" data-testid="chat-fx" data-mood={theme === 'live' ? mood : undefined}>
    <i className="chat-fx-a" /><i className="chat-fx-b" />
    {SCENE[theme]?.()}
    <img className="chat-fx-logo" src="/assets/feeless-logo.png" alt="" />
  </div>;
}

// 🎨 THE PICKER, shared by every chat (rooms, the Brain, the inbox): each theme is a live mini room; tiers by $FEE held, locked ones show how
// close you are (or that a badge unlocks them).
export function ChatThemePicker({ prefs, setPrefs, room, feeUsd = 0, unlocked = [] }) {
  const cur = chatTheme(prefs, room, feeUsd, unlocked);
  const pick = id => setPrefs({ themes: { ...(prefs?.themes || {}), [room]: id } });
  return <div className="ctp" data-testid="chat-theme-picker">{[['Free', 0], ['$5+ $FEE', 5], ['$100+ $FEE', 100]].map(([w, usd]) => <section key={usd} className="ctp-tier">
    <header>{w}{usd ? <><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, (Number(feeUsd) || 0) / usd)})` }} /></u><span>{feeUsd >= usd ? 'unlocked' : `$${Math.floor(Number(feeUsd) || 0)} / $${usd} held`}</span></> : null}</header>
    <div className="ctp-grid">{CHAT_THEMES.filter(t => t[2] === usd).map(([id, label], i) => { const ok = canUse(id, feeUsd, unlocked);
      return <button key={id} type="button" role="radio" aria-checked={cur === id} disabled={!ok} className={`ctp-tile ${cur === id ? 'active' : ''}`} style={{ '--i': i }} onClick={() => pick(id)}
        data-tip={ok ? `${label} — this room's background` : `Hold $${usd}+ of $FEE (or earn the badge) to unlock ${label}`} data-testid={`chat-theme-${id}`}>
        {id === 'off' ? null : <ChatFx theme={id} room={room} />}<b>{label}</b>{ok ? null : <i className="ctp-lock" aria-hidden="true">🔒</i>}</button>; })}</div></section>)}</div>;
}

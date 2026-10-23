import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useCoinMood } from '../lib/coinMood';
import { sweepable } from '../lib/cacheSweep';
import '../styles/chatThemes.css';

// 🎨 Animated chat backgrounds (styles/chatThemes.css), chosen per room in every chat's ⚙ / 🎨 (saved as themes[room]: a coin's chat, the Brain
// ('brain'), the inbox ('inbox')). Drawn from the trade itself — candles, order flow, depth, the radar, a ticker tape, the moon run, liquidation
// lava, the reserve vortex, the gold vault — always with the FEE mark. Free: 4 · $FEE ≥ $5: 4 more · ≥ $100: 5 more (badge perks unlock some).
export const CHAT_THEMES = [
  ['neural', 'Neural', 0], ['live', 'Live mood', 0], ['fee', 'FEE glow', 0], ['candles', 'Candle rain', 0], ['off', 'Plain', 0],
  ['flow', 'Order flow', 5], ['depth', 'Depth', 5], ['radar', 'Trench radar', 5], ['grid', 'Terminal', 5],
  ['tape', 'Ticker tape', 100], ['moon', 'Moon run', 100], ['lava', 'Liquidation lava', 100], ['vortex', 'Reserve vortex', 100], ['gold', 'Gold vault', 100],
];
const NEED = Object.fromEntries(CHAT_THEMES.map(([id, , usd]) => [id, usd]));
// Unlocked by $FEE held, or by a badge perk (e.g. FRSV VIP → Vortex): `unlocked` is the perk list from your badges.
export const canUse = (id, feeUsd, unlocked = []) => (Number(feeUsd) || 0) >= (NEED[id] ?? Infinity) || unlocked.includes(id);
// A saved theme you no longer qualify for falls back to Live (nothing breaks, nothing is lost).
// 🧠 a Brain room defaults to the drawn NEURAL net; every other room to Live mood
export const chatTheme = (prefs, room, feeUsd = Infinity, unlocked = []) => { const t = (prefs?.themes || {})[room] || (String(room || '').startsWith('brain') ? 'neural' : 'live'); return canUse(t, feeUsd, unlocked) ? t : 'live'; };

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
// 🎨 THE SCENES (owner, 2026-10-22: "horrible bg themes" → redrawn): each one is drawn art — a skyline, a coin, a radar, a vault — with motion
// only on whole layers (a strip scrolling, a disk turning, a sweep, embers rising) so the compositor carries it; never a repaint loop.
// Every scrolling strip is 4 copies of a 400-unit period in a 1600-unit SVG that slides −25% forever (seamless at any width).
const prng = s => () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
const COPIES = [0, 400, 800, 1200];
const wave = (base, harm, step = 8) => { let d = ''; for (let x = 0; x <= 1600; x += step) { const t = ((x % 400) / 400) * Math.PI * 2; d += `${x ? 'L' : 'M'}${x},${(base + harm.reduce((s, [k, a, p]) => s + a * Math.sin(k * t + p), 0)).toFixed(1)}`; } return d; };
const area = line => `${line}L1600,160L0,160Z`;
const LIVE = wave(92, [[2, 20, 0], [5, 9, 1], [11, 4, 2]]);
const LAVA_A = wave(70, [[3, 9, 0], [7, 4, 1]]); const LAVA_B = wave(88, [[4, 7, 2], [9, 3, 0]]);
const candles = (seed, n = 24) => {
  const r = prng(seed); const d = Array.from({ length: n }, () => (r() - 0.5) * 18); const m = d.reduce((a, b) => a + b, 0) / n;
  let y = 0; const raw = d.map(x => { const o = y; y += x - m; return { o, c: y, wu: 2 + r() * 8, wd: 2 + r() * 8 }; });
  const lo = Math.min(...raw.map(k => Math.min(k.o, k.c) - k.wu)); const hi = Math.max(...raw.map(k => Math.max(k.o, k.c) + k.wd)); const sc = 110 / Math.max(1, hi - lo);
  const w = 400 / n; const Y = v => 30 + (v - lo) * sc;
  return raw.map((k, i) => ({ x: i * w + w / 2, o: Y(k.o), c: Y(k.c), hi: Y(Math.min(k.o, k.c) - k.wu), lo: Y(Math.max(k.o, k.c) + k.wd), up: k.c < k.o }));
};
const NEAR = candles(7); const FAR = candles(31, 30);
const Strip = ({ set, bw }) => COPIES.map(off => <g key={off} transform={`translate(${off} 0)`}>{set.map((k, i) => <g key={i} className={k.up ? 'up' : 'dn'}>
  <line x1={k.x} x2={k.x} y1={k.hi} y2={k.lo} /><rect x={k.x - bw / 2} y={Math.min(k.o, k.c)} width={bw} height={Math.max(1.4, Math.abs(k.c - k.o))} rx="1" /></g>)}</g>);
const STARS = (() => { const r = prng(11); return Array.from({ length: 46 }, (_, i) => [r() * 400, r() * 300, 0.4 + r() * 1.1, i % 2]); })();
const Stars = ({ odd }) => <svg className={`cfx-stars s${odd}`} viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">{STARS.filter(s => s[3] === odd).map(([x, y, r], i) => <circle key={i} cx={x} cy={y} r={r} />)}</svg>;
const rise = (n, cls, seed) => { const r = prng(seed); return Array.from({ length: n }, (_, i) => <b key={i} className={cls} style={{ left: `${(r() * 96 + 2).toFixed(1)}%`, '--i': i, '--d': `${(5 + r() * 6).toFixed(1)}s`, '--s': `${(2 + r() * 3).toFixed(1)}px` }} />); };
const SKY = (() => { const r = prng(5); let x = 0; const out = []; while (x < 400) { const w = 6 + r() * 10; out.push([x, w, 10 + r() * 34]); x += w + 1.5; } return out; })();
const RADAR = [[38, 30, '$WIF'], [72, 120, '$FEE'], [55, 205, '$BONK'], [24, 290, '$MEW'], [80, 330, '$POPCAT']];
const BOLTS = Array.from({ length: 16 }, (_, i) => [100 + 84 * Math.cos((i / 16) * Math.PI * 2), 100 + 84 * Math.sin((i / 16) * Math.PI * 2)]);
const BOOK = [92, 74, 66, 58, 41, 37, 26, 18];
const LANES = [[16, 'b', [0, 2.6, 5.1], [7, 5, 12]], [28, 'b', [1.2, 4.4], [5, 14]], [40, 'b', [0.6, 3.3, 6], [6, 4, 8]], [60, 's', [0.4, 3.8], [7, 14]], [72, 's', [1.8, 4.9, 6.6], [4, 7, 5]], [84, 's', [0.9, 3.1], [12, 6]]];
// 🧠 NEURAL (owner, 2026-10-22: "the whole Brain themed, not a bs background"): a drawn net — nodes, synapses, pulses firing along them
const NODES = [[8, 18], [26, 10], [44, 24], [64, 12], [86, 20], [14, 48], [36, 42], [58, 52], [80, 44], [22, 80], [48, 74], [72, 84], [92, 72]];
const LINKS = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [1, 6], [2, 6], [2, 7], [3, 7], [4, 8], [5, 6], [6, 7], [7, 8], [5, 9], [6, 10], [7, 10], [7, 11], [8, 12], [9, 10], [10, 11], [11, 12]];
const Net = ({ far }) => <svg className={`cfx-neural${far ? ' far' : ''}`} viewBox="0 0 100 100" preserveAspectRatio="none">
  {LINKS.map(([a, b], i) => <line key={`l${i}`} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} className="syn" style={{ '--i': i }} />)}
  {far ? null : LINKS.filter((_, i) => i % 3 === 0).map(([a, b], i) => <line key={`p${i}`} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} className="pulse" pathLength="100" style={{ '--i': i }} />)}
  {NODES.map(([x, y], i) => <circle key={`n${i}`} cx={x} cy={y} r=".6" className="node" style={{ '--i': i }} />)}</svg>;
const SCENE = {
  neural: () => <><Net far /><Net /></>,
  // 📈 LIVE MOOD: the room's own coin as a live horizon — the line tilts up on a pump, down on a dump, flat when calm; colour = the mood
  live: () => <>
    <svg className="cfx-grid" viewBox="0 0 400 160" preserveAspectRatio="none">{[30, 62, 94, 126].map(y => <line key={y} x1="0" x2="400" y1={y} y2={y} />)}</svg>
    <span className="cfx-tilt"><svg className="cfx-run cfx-liveline" viewBox="0 0 1600 160" preserveAspectRatio="none"><path className="fill" d={area(LIVE)} /><path className="gl" d={LIVE} /><path className="ln" d={LIVE} /></svg></span>
    <u className="cfx-now" /></>,
  // 🪙 FEE GLOW: the FEE coin rising out of the corner — ridged rim, struck face, light rays turning behind it, sparks lifting off
  fee: () => <><i className="cfx-rays" /><svg className="cfx-coin" viewBox="0 0 200 200">
    <circle className="rim" cx="100" cy="100" r="92" /><circle className="ridge" cx="100" cy="100" r="86" /><circle className="face" cx="100" cy="100" r="74" />
    <circle className="ring" cx="100" cy="100" r="62" /><path className="shine" d="M38,70 A70,70 0 0 1 120,30" /><image href="/assets/feeless-logo.png" x="62" y="62" width="76" height="76" /></svg>
    <span className="cfx-rise">{rise(12, 'cfx-spark', 3)}</span></>,
  // 🕯 CANDLES: two depths of a real chart scrolling by — the near one bright, the far one in the haze — with the last-price line
  candles: () => <><svg className="cfx-run cfx-candles far" viewBox="0 0 1600 160" preserveAspectRatio="none"><Strip set={FAR} bw={5} /></svg>
    <svg className="cfx-run cfx-candles near" viewBox="0 0 1600 160" preserveAspectRatio="none"><Strip set={NEAR} bw={9} /></svg>
    <u className="cfx-last"><em>LAST</em></u></>,
  // 🌊 ORDER FLOW: buys stream right on the top lanes, sells left on the bottom ones — the size of each bubble is the size of the trade
  flow: () => <><u className="cfx-mid" />{LANES.map(([top, side, delays, sizes], li) => <span key={li} className={`cfx-lane ${side}`} style={{ top: `${top}%` }}>
    {delays.map((dl, k) => <span key={k} className="cfx-ride" style={{ '--dl': `${-dl}s`, '--t': `${7 + li}s` }}><b className={sizes[k] >= 12 ? 'whale' : ''} style={{ '--s': `${sizes[k]}px` }} /></span>)}</span>)}</>,
  // 📚 DEPTH: the book as two drawn cliffs + its ladder — bids stacked left, asks right, the spread glowing between them
  depth: () => <><span className="cfx-book">{BOOK.map((w, i) => <i key={i} className="b" style={{ '--w': `${w}%`, '--i': i }} />)}{BOOK.map((w, i) => <i key={`a${i}`} className="a" style={{ '--w': `${BOOK[(i + 3) % 8]}%`, '--i': i }} />)}</span>
    <svg className="cfx-depth" viewBox="0 0 200 60" preserveAspectRatio="none"><path className="bid" d="M0,60 V14 H18 V20 H34 V27 H50 V33 H64 V40 H78 V46 H90 V53 H98 V60 Z" />
      <path className="ask" d="M200,60 V10 H180 V18 H162 V25 H146 V32 H132 V39 H118 V46 H108 V53 H102 V60 Z" /><path className="mid" d="M100,0 V60" /></svg></>,
  // 📡 TRENCH RADAR: a real scope — rings, bearings, the sweep, and coins lighting up the moment the beam crosses them
  radar: () => <span className="cfx-radar"><svg viewBox="0 0 300 300">
    {[40, 80, 120, 146].map(r => <circle key={r} cx="150" cy="150" r={r} className="rg" />)}<path className="x" d="M150,4V296M4,150H296" />
    {Array.from({ length: 36 }, (_, i) => { const a = (i / 36) * Math.PI * 2; const r0 = i % 3 ? 140 : 132; return <line key={i} className="tk" x1={150 + r0 * Math.sin(a)} y1={150 - r0 * Math.cos(a)} x2={150 + 146 * Math.sin(a)} y2={150 - 146 * Math.cos(a)} />; })}
    {RADAR.map(([r, deg, sym]) => { const a = (deg * Math.PI) / 180; return <text key={sym} x={150 + r * 1.4 * Math.sin(a) + 7} y={150 - r * 1.4 * Math.cos(a) - 6}>{sym}</text>; })}</svg>
    <i className="cfx-sweep" />{RADAR.map(([r, deg]) => { const a = (deg * Math.PI) / 180; return <u key={deg} className="cfx-blip" style={{ left: `${50 + (r * 1.4 * Math.sin(a)) / 3}%`, top: `${50 - (r * 1.4 * Math.cos(a)) / 3}%`, '--dl': `${(deg / 360) * 6}s` }} />; })}</span>,
  // 🌆 TERMINAL: a synthwave run — a striped sun setting behind a skyline of candles, the neon floor rushing toward you
  grid: () => <><svg className="cfx-sun" viewBox="0 0 200 100"><circle cx="100" cy="100" r="62" />{[64, 74, 82, 89, 95].map((y, i) => <rect key={y} x="30" y={y} width="140" height={2 + i} />)}</svg>
    <svg className="cfx-skyline" viewBox="0 0 400 50" preserveAspectRatio="none">{SKY.map(([x, w, h], i) => <rect key={i} x={x} y={50 - h} width={w} height={h} />)}</svg>
    <span className="cfx-floor"><i /></span></>,
  // 📟 TICKER TAPE: three LED boards across the room, every coin's move rolling by in dot-matrix
  tape: () => [16, 50, 84].map((top, c) => <span key={c} className={`cfx-col${c === 1 ? ' r' : ''}`} style={{ top: `${top}%`, '--i': c }}><span className="cfx-roll">{[...TICKS, ...TICKS].slice(c * 3, c * 3 + 10).concat([...TICKS, ...TICKS].slice(c * 3, c * 3 + 10)).map(([t, p, up], k) => <em key={k} className={up ? 'up' : 'dn'}>{up ? '▲' : '▼'} {t} {p}</em>)}</span></span>),
  // 🌕 MOON RUN: a starfield, a cratered moon, a rocket riding its chart line up toward it over the candle mountains
  moon: () => <><Stars odd={0} /><Stars odd={1} /><svg className="cfx-moonart" viewBox="0 0 100 100"><circle className="glow" cx="50" cy="50" r="48" /><circle className="body" cx="50" cy="50" r="36" />
    <circle className="cr" cx="38" cy="40" r="7" /><circle className="cr" cx="60" cy="58" r="9" /><circle className="cr" cx="56" cy="30" r="4" /><circle className="cr" cx="34" cy="64" r="4.5" />
    <path className="shade" d="M50,14 A36,36 0 0 1 50,86 A26,36 0 0 0 50,14 Z" /></svg>
    <svg className="cfx-hills" viewBox="0 0 400 80" preserveAspectRatio="none"><path className="h2" d="M0,80 V44 L40,30 L70,40 L110,18 L150,34 L190,22 L240,38 L280,14 L330,30 L370,20 L400,28 V80 Z" />
      <path className="h1" d="M0,80 V60 L50,48 L90,58 L140,40 L200,56 L250,44 L300,58 L350,46 L400,54 V80 Z" /></svg>
    <svg className="cfx-path" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M6,92 C42,90 66,70 80,22" /></svg>
    <span className="cfx-flyx"><span className="cfx-flyy"><span className="cfx-rocket"><svg viewBox="0 0 40 40"><path className="fl" d="M12,28 L4,38 L16,30 Z" /><path className="bd" d="M14,26 C18,14 26,6 36,4 C34,14 26,22 14,26 Z" /><circle className="wn" cx="27" cy="13" r="3" /><path className="fn" d="M14,26 L10,20 L18,18 Z M14,26 L20,30 L22,22 Z" /></svg></span></span></span></>,
  // 🌋 LIQUIDATION LAVA: a molten lake rolling in two layers, red candles melting into it, embers rising off the surface
  lava: () => <><i className="cfx-heat" /><span className="cfx-rise">{rise(14, 'cfx-ember', 9)}</span>
    <svg className="cfx-melt" viewBox="0 0 400 160" preserveAspectRatio="xMidYMax slice">{[[60, 50, 46], [120, 72, 30], [300, 58, 40], [352, 80, 24]].map(([x, y, h], i) => <g key={i} className="cn"><line x1={x} x2={x} y1={y - 14} y2={y + h + 10} /><rect x={x - 7} y={y} width="14" height={h} rx="2" /><path d={`M${x - 7},${y + h} q3,10 6,0 q2,14 5,0 q2,6 3,0`} /></g>)}
      <path className="rock" d="M0,160 V120 L30,108 L58,118 L80,104 L96,160 Z M300,160 L320,110 L350,100 L380,114 L400,104 V160 Z" /></svg>
    <svg className="cfx-run cfx-lava b" viewBox="0 0 1600 160" preserveAspectRatio="none"><path d={area(LAVA_B)} /></svg>
    <svg className="cfx-run cfx-lava a" viewBox="0 0 1600 160" preserveAspectRatio="none"><path d={area(LAVA_A)} /><path className="crust" d={LAVA_A} /></svg></>,
  // 🌀 RESERVE VORTEX: the FEE reserve as an accretion disk — dotted orbits turning at their own speeds, three coins riding them, a burning core
  vortex: () => <><span className="cfx-disk">{[44, 62, 78, 94].map((r, i) => <i key={r} className="cfx-ring" style={{ '--r': `${r}%`, '--i': i }} />)}
    {[28, 39, 47].map((r, i) => <span key={r} className="cfx-orbit" style={{ '--i': i, '--r': r }}><img src="/assets/feeless-logo.png" alt="" /></span>)}</span><i className="cfx-core" /></>,
  // 🏦 GOLD VAULT: the vault door — bolts, the wheel, the dial — gold bars stacked in front, glints and gold dust in the air
  gold: () => <><span className="cfx-rise">{rise(10, 'cfx-dust', 4)}</span><span className="cfx-vault"><svg className="door" viewBox="0 0 200 200"><circle className="rim" cx="100" cy="100" r="96" /><circle className="plate" cx="100" cy="100" r="78" />
    {BOLTS.map(([x, y], i) => <circle key={i} className="bolt" cx={x} cy={y} r="4.5" />)}<circle className="hub" cx="100" cy="100" r="18" /></svg>
    <svg className="wheel" viewBox="0 0 200 200">{[0, 60, 120].map(a => <rect key={a} x="96" y="40" width="8" height="120" rx="4" transform={`rotate(${a} 100 100)`} />)}<circle cx="100" cy="100" r="12" /></svg>
    <svg className="dial" viewBox="0 0 200 200">{Array.from({ length: 24 }, (_, i) => <rect key={i} x="99" y="132" width="2" height={i % 6 ? 4 : 8} transform={`rotate(${i * 15} 100 140)`} />)}<circle cx="100" cy="140" r="5" /></svg></span>
    <svg className="cfx-bars" viewBox="0 0 160 70">{[[10, 46], [58, 46], [106, 46], [34, 24], [82, 24], [58, 2]].map(([x, y], i) => <g key={i} className="bar"><path className="top" d={`M${x + 6},${y} H${x + 40} L${x + 46},${y + 8} H${x} Z`} /><rect className="front" x={x} y={y + 8} width="46" height="14" /><path className="lit" d={`M${x + 4},${y + 11} H${x + 30}`} /></g>)}</svg>
    {[[8, 84], [18, 78], [28, 88], [38, 80], [14, 92]].map(([l, t], i) => <u key={i} className="cfx-glint" style={{ left: `${l}%`, top: `${t}%`, '--i': i }} />)}</>,
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

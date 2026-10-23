import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useGlide } from '../lib/useGlide';
import { FamilyCrest } from './FamilyCrest';
import { familiaTrade } from './FamiliaTrade';
import '../styles/streetChat.css';

// 💬 THE STREETS — the Familia city chat (backend/street_chat.py; owner: "familia chat gotta be LITTY"). A drawn street at night (skyline with
// lit windows, the city's neon sign, rain, lamp glow) behind one room per city where every line wears its family's crest plate, the Don gets
// the crown, a pasted coin becomes a coin card with its RECEIPT (x since the call, peak), @you lines glow, four street reactions, and the
// header carries the street's pulse: who is ON THE BLOCK, lines / hour as a live spark, the hottest call. Dons pull their own family's lines;
// staff pull + mute. Tools: 📞 call a coin · 🛡 rally · @ mention who's here.
// LIT (2026-10-23): every receipt draws its call as a mini chart (1x at the call → now, the peak lit) · a 📟 HITS tape rolls the street's best
// calls of the day · the street's HEAT (calm → on fire) drives the drawn scene (rain, neon, lit windows, lightning) · a Don / staff 🐢 slows
// the street (the send button counts down) · a reaction bursts. Every coin opens the Familia trade desk in place (no jump out of Familia).
const POLL_MS = 6000;
const n0 = x => Math.round(Number(x) || 0).toLocaleString('en-US');
export const xWord = x => (x == null ? '—' : x >= 10 ? `${Math.round(x)}x` : x >= 1 ? `${x.toFixed(x >= 2 ? 1 : 2)}x` : `${Math.round((x - 1) * 100)}%`);
export const mcWord = v => (!v ? '' : v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}K` : `$${Math.round(v)}`);
export const ago = (ts, now = Date.now()) => { const s = Math.max(0, Math.round((now - (ts || 0)) / 1000)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };
const SPLIT = /(@[A-Za-z0-9_.-]{2,32}|\$[A-Za-z][A-Za-z0-9]{1,11}\b|\b[1-9A-HJ-NP-Za-km-z]{32,44}\b)/g;
// pure: a line's text → parts {t, k: text | at | tick | ca}
export function streetParts(text) {
  return String(text || '').split(SPLIT).filter(Boolean).map(t => ({ t, k: t[0] === '@' ? 'at' : t[0] === '$' ? 'tick' : /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(t) ? 'ca' : 'text' }));
}
const voter = addr => { if (addr) return addr; try { let v = localStorage.getItem('feeless-voter'); if (!v) { v = `browser-${Math.random().toString(36).slice(2)}`; localStorage.setItem('feeless-voter', v); } return v; } catch { return 'browser-anon'; } };

// 🌃 the drawn street: far + near skyline (lit windows), the city's neon sign, a lamp, rain, a wet-street sheen — one calm moving layer each
const StreetScene = memo(function StreetScene({ name, heat = 0 }) {
  const far = useMemo(() => Array.from({ length: 14 }, (_, i) => ({ x: i * 30 + (i % 3) * 4, w: 22 + (i * 7) % 12, h: 40 + ((i * 37) % 55) })), []);
  const near = useMemo(() => Array.from({ length: 9 }, (_, i) => ({ x: i * 48 - 6, w: 36 + (i * 11) % 16, h: 62 + ((i * 53) % 70) })), []);
  return <div className="st-scene" aria-hidden="true">
    <svg className="st-sky" viewBox="0 0 420 200" preserveAspectRatio="xMidYMax slice">
      <defs><linearGradient id="stNight" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--st-sky1)" /><stop offset="1" stopColor="var(--st-sky2)" /></linearGradient></defs>
      <rect width="420" height="200" fill="url(#stNight)" />
      <circle cx="352" cy="34" r="13" className="st-moon" />
      {far.map((b, i) => <g key={`f${i}`}><rect x={b.x} y={200 - b.h - 30} width={b.w} height={b.h + 30} className="st-bfar" />
        {Array.from({ length: Math.floor(b.h / 12) }, (_, r) => <rect key={r} x={b.x + 4 + ((r + i) % 2) * 8} y={200 - b.h - 22 + r * 12} width="3" height="4" className={`st-win ${(r * 7 + i) % 5 === 0 ? 'is-on' : ''}`} />)}</g>)}
      {near.map((b, i) => <g key={`n${i}`}><rect x={b.x} y={200 - b.h} width={b.w} height={b.h} className="st-bnear" /><rect x={b.x} y={200 - b.h} width={b.w} height="3" className="st-roof" />
        {Array.from({ length: Math.floor(b.h / 14) }, (_, r) => [0, 1, 2].map(c => <rect key={`${r}-${c}`} x={b.x + 5 + c * 11} y={200 - b.h + 10 + r * 14} width="5" height="6" className={`st-win ${(r * 3 + c + i) % 4 === 0 ? 'is-on' : (r * 5 + c * 2 + i) % 3 === 0 && heat >= 2 ? 'is-on is-warm' : ''} ${(r + c + i) % 9 === 0 ? 'is-blink' : ''}`} style={{ '--d': `${(r + c + i) % 7}s` }} />))}</g>)}
    </svg>
    <span className="st-neon"><b>{name}</b></span>
    <span className="st-lamp" /><span className="st-rain" />{heat >= 2 ? <span className="st-rain is-hard" /> : null}<span className="st-wet" />
    {heat >= 3 ? <span className="st-flash" /> : null}
  </div>;
});

function Spark({ bars }) {
  const top = Math.max(1, ...(bars || [0]));
  return <span className="st-spark" data-tip="Lines in the last hour — one bar per 5 minutes">{(bars || []).map((v, i) => <i key={i} style={{ transform: `scaleY(${Math.max(0.08, v / top)})`, '--i': i }} />)}</span>;
}

// 📈 the receipt's mini chart: the call at 1x (the dashed line) → every 5-minute sample → now (log scale, so 10x and −50 % both read), peak lit
export const trailPath = (pts, W = 58, H = 20) => {
  if (!pts || pts.length < 2) return null;
  const t0 = pts[0][0]; const t1 = Math.max(t0 + 1, pts[pts.length - 1][0]);
  const ys = pts.map(p => Math.log(Math.max(0.01, Number(p[1]) || 0.01))); const lo = Math.min(0, ...ys); const span = (Math.max(0, ...ys) - lo) || 1;
  const X = t => ((t - t0) / (t1 - t0)) * W; const Y = v => H - 2 - ((v - lo) / span) * (H - 4);
  const pk = ys.indexOf(Math.max(...ys)); const f = n => n.toFixed(1);
  return { d: pts.map((p, i) => `${i ? 'L' : 'M'}${f(X(p[0]))} ${f(Y(ys[i]))}`).join(' '), base: Y(0), peak: [X(pts[pk][0]), Y(ys[pk])], now: [X(pts[pts.length - 1][0]), Y(ys[ys.length - 1])], W, H };
};
const Trail = memo(function Trail({ trail, x }) {
  const pts = useMemo(() => (trail?.length && x != null ? [...trail, [Math.max(trail[trail.length - 1][0] + 1, Math.floor(Date.now() / 1000)), x]] : trail), [trail, x]);
  const g = trailPath(pts); if (!g) return null;
  return <svg className="st-trail" viewBox={`0 0 ${g.W} ${g.H}`} aria-hidden="true" data-testid="st-trail">
    <line x1="0" x2={g.W} y1={g.base} y2={g.base} className="st-trail-base" />
    <path d={`${g.d} L${g.W} ${g.H} L0 ${g.H} Z`} className="st-trail-fill" /><path d={g.d} className="st-trail-line" />
    <circle cx={g.peak[0]} cy={g.peak[1]} r="1.9" className="st-trail-peak" /><circle cx={g.now[0]} cy={g.now[1]} r="2.3" className="st-trail-now" />
  </svg>;
});

function Receipt({ c, coin }) {
  const x = c?.x; const up = x != null && x >= 1;
  const pair = { chainId: c?.chain || coin?.chain || 'solana', pairAddress: c?.pairAddress || coin?.pairAddress, baseToken: { symbol: c?.symbol || coin?.symbol } };
  return <button type="button" className={`st-coin ${c ? (up ? 'is-up' : 'is-down') : ''}`} onClick={() => familiaTrade(pair)} data-testid="st-coin"
    data-tip={c ? `Called at ${mcWord(c.mcAtCall) || 'a price'} · now ${xWord(x)} · peak ${xWord(c.peakX)} — the line is its run since the call · tap to trade it here` : 'Open its trade desk'}>
    {(c?.image || coin?.image) ? <img src={c?.image || coin?.image} alt="" loading="lazy" /> : <i className="st-cdot" />}
    <b>${c?.symbol || coin?.symbol || '???'}</b>{c?.mcAtCall || coin?.mc ? <small>@ {mcWord(c?.mcAtCall || coin?.mc)}</small> : null}
    {c ? <><Trail trail={c.trail} x={x} /><em>{xWord(x)}</em>{c.peakX > 1.05 ? <u>peak {xWord(c.peakX)}</u> : null}</> : null}</button>;
}

// 📟 the HITS tape: the street's best calls of the day roll by like a ticker (peak x, who called it, their family) — tap one to trade it here
function HitsTape({ hits }) {
  if (!hits?.length) return null;
  const item = (h, i, dup) => <button key={`${dup ? 'd' : 'h'}${i}`} type="button" className="st-hit" style={{ '--fc': h.fam?.color || '#8f8470' }} tabIndex={dup ? -1 : 0} aria-hidden={dup || undefined}
    onClick={() => familiaTrade({ chainId: h.chain || 'solana', pairAddress: h.pairAddress, baseToken: { symbol: h.symbol } })}
    data-tip={`$${h.symbol} ran ${xWord(h.peakX)} after ${h.by}${h.fam ? ` [${h.fam.tag}]` : ''} called it ${ago(Date.now() - h.ago * 1000)} ago · now ${xWord(h.x)} — tap to trade it`}>
    {h.image ? <img src={h.image} alt="" loading="lazy" /> : <i />}<b>${h.symbol}</b><em>{xWord(h.peakX)}</em>{h.fam ? <u>{h.fam.tag}</u> : null}<small>{h.by}</small></button>;
  return <div className="st-tape" data-testid="st-tape"><span className="st-tape-tag">📟 HITS<small>24H</small></span>
    <div className="st-tape-track"><div className={`st-tape-run ${hits.length > 2 ? 'is-roll' : ''}`} style={{ '--n': hits.length }}>{hits.map((h, i) => item(h, i, false))}{hits.length > 2 ? hits.map((h, i) => item(h, i, true)) : null}</div></div></div>;
}

// 🌡 the street's heat: 4 lit segments (calm · warm · hot · on fire) — the drawn street above reads the same number
const HEAT = ['CALM', 'WARM', 'HOT', 'ON FIRE'];
function HeatMeter({ heat = 0 }) {
  return <span className={`st-heat is-h${heat}`} data-tip="Street heat — lines this hour, reactions and a call that ran 2x+. A hot street rains harder, its neon flickers and the windows light up" data-testid="st-heat">
    <span className="st-heat-bars">{[0, 1, 2, 3].map(i => <i key={i} className={i <= heat ? 'is-on' : ''} style={{ '--i': i }} />)}</span><small>{HEAT[heat] || 'CALM'}</small></span>;
}

const Line = memo(function Line({ l, fresh, reacts, canPull, canPin, staff, onReact, onReply, onMod, onAt }) {
  const fam = l.fam; const [burst, setBurst] = useState(null);
  useEffect(() => { if (!burst) return undefined; const t = setTimeout(() => setBurst(null), 900); return () => clearTimeout(t); }, [burst]);
  return <li className={`st-line ${l.mine ? 'is-mine' : ''} ${l.atMe ? 'is-atme' : ''} ${fam?.don ? 'is-don' : ''} ${fresh ? 'is-fresh' : ''} ${l.official ? 'is-official' : ''}`}
    style={{ '--fc': fam?.color || '#8f8470' }} data-testid={`st-line-${l.id}`}>
    <span className="st-plate" data-tip={fam ? `[${fam.tag}] ${fam.name || ''}${fam.don ? ' · the Don' : ''}` : 'No family yet'}>
      {fam?.badge ? <FamilyCrest b={fam.badge} px={28} banner={false} sheen={false} title={`${fam.tag} crest`} /> : <i className="st-free">FREE</i>}
      {fam?.don ? <b className="st-crown" aria-hidden="true" /> : null}</span>
    <div className="st-body">
      <p className="st-who">{fam ? <b className="st-tag">{fam.tag}</b> : null}<button type="button" className="st-name" onClick={() => onAt(l.handle || l.name)} data-tip="Mention them">{l.name}</button>
        {fam?.don ? <u className="st-don">DON</u> : null}{l.atMe ? <u className="st-atme">@YOU</u> : null}<time>{ago(l.ts)}</time></p>
      <p className="st-text">{streetParts(l.text).map((p, i) => p.k === 'text' ? <span key={i}>{p.t}</span> : <mark key={i} className={`st-${p.k}`}>{p.k === 'ca' ? `${p.t.slice(0, 4)}…${p.t.slice(-4)}` : p.t}</mark>)}</p>
      {(l.calls || []).length || (l.coins || []).length ? <span className="st-coins">{(l.calls || []).length ? l.calls.map(c => <Receipt key={c.pairAddress} c={c} />) : l.coins.map(c => <Receipt key={c.pairAddress} coin={c} />)}</span> : null}
      <span className="st-reacts">{reacts.map(e => { const r = l.reacts?.[e]; return <button key={e} type="button" className={r?.mine ? 'is-on' : ''} aria-pressed={!!r?.mine} onClick={() => { if (!r?.mine) setBurst({ e, k: Date.now() }); onReact(l.id, e); }}
        data-tip={{ '🔥': 'Heat', '💀': 'Dead', '🫡': 'Respect', '💰': 'Paid' }[e]} data-testid={`st-react-${l.id}-${e}`}>{e}{r?.n ? <small>{r.n}</small> : null}{burst?.e === e ? <span key={burst.k} className="st-burst" aria-hidden="true">{[0, 1, 2, 3, 4].map(i => <i key={i} style={{ '--i': i }}>{e}</i>)}</span> : null}</button>; })}
        <button type="button" className="st-act" onClick={() => onReply(l)} data-tip="Reply" aria-label="Reply">↩</button>
        {canPull ? <button type="button" className="st-act is-mod" onClick={() => onMod(l, 'pull')} data-tip="Pull this line off the street" aria-label="Pull this line" data-testid={`st-pull-${l.id}`}>🗑</button> : null}
        {staff && !l.mine ? <button type="button" className="st-act is-mod" onClick={() => onMod(l, 'mute')} data-tip="Pull + mute the poster for 1 hour" aria-label="Mute for an hour">🔇</button> : null}
        {canPin ? <button type="button" className="st-act" onClick={() => onMod(l, 'pin')} data-tip="📌 Pin this on top of the street for an hour (Dons + staff)" aria-label="Pin this line" data-testid={`st-pin-${l.id}`}>📌</button> : null}</span>
    </div>
  </li>;
});

export default function StreetChat({ city, name, addr, sess }) {
  const [d, setD] = useState(null); const [t, setT] = useState(''); const [busy, setBusy] = useState(false); const [reply, setReply] = useState(null); const [tool, setTool] = useState(null); const [cool, setCool] = useState(0); const [, tick] = useState(0); const coolDur = useRef(0);
  const logRef = useRef(null); const seen = useRef(null); const input = useRef(null); const stick = useRef(true);
  const url = `/api/reputation/familia/street/${city}${addr && sess ? `?viewer=${encodeURIComponent(addr)}&session=${encodeURIComponent(sess)}` : ''}`;
  const load = useCallback(() => fetch(apiUrl(url)).then(r => (r.ok ? r.json() : null)).then(j => { if (j && Array.isArray(j.lines)) setD(j); }).catch(() => {}), [url]);
  useEffect(() => { seen.current = null; setD(null); load(); const p = setInterval(() => { if (!document.hidden) load(); }, POLL_MS); return () => clearInterval(p); }, [load]);
  const coolFor = sec => { const u = Date.now() + sec * 1000; if (u > cool + 900) { coolDur.current = sec; setCool(u); } };
  useEffect(() => { if ((d?.slow?.wait || 0) > 0) coolFor(d.slow.wait); }, [d?.slow?.wait]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (cool <= Date.now()) return undefined; const p = setInterval(() => { tick(n => n + 1); if (Date.now() >= cool) clearInterval(p); }, 1000); return () => clearInterval(p); }, [cool]);
  const coolLeft = Math.max(0, Math.ceil((cool - Date.now()) / 1000));
  const lines = d?.lines || []; const hour = useGlide(d?.vitals?.hour || 0); const here = useGlide(d?.hereN || 0);
  const fresh = useMemo(() => { const prev = seen.current; const ids = new Set(lines.map(l => l.id)); seen.current = ids; return prev ? new Set([...ids].filter(i => !prev.has(i))) : new Set(); }, [lines]);
  useEffect(() => { const el = logRef.current; if (el && stick.current) el.scrollTop = el.scrollHeight; }, [lines.length]);
  useEffect(() => { if ([...fresh].some(id => lines.find(l => l.id === id)?.atMe)) toast(`📣 You got called out on ${name}`); }, [fresh]);   // eslint-disable-line react-hooks/exhaustive-deps
  const need = () => { if (addr && sess) return true; toast.error('Connect your wallet + sign in to chat once (one signature, 7 days).'); return false; };
  const send = async e => {
    e?.preventDefault(); const v = t.trim(); if (!v || busy || !need()) return;
    setBusy(true);
    try { const r = await fetch(apiUrl('/api/reputation/chat'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: d?.room || `city-${city}`, address: addr, text: v, ts: Math.floor(Date.now() / 1000), session: sess, parentId: reply?.id || null }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Could not post'); setT(''); setReply(null); setTool(null); stick.current = true;
      if (d?.slow?.sec && !(d?.mod?.staff || d?.mod?.don)) coolFor(d.slow.sec); await load(); }
    catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  const react = async (id, emoji) => {
    setD(x => x && ({ ...x, lines: x.lines.map(l => { if (l.id !== id) return l; const r = { ...(l.reacts || {}) }; const c = r[emoji] || { n: 0, mine: false };
      r[emoji] = { n: Math.max(0, c.n + (c.mine ? -1 : 1)), mine: !c.mine }; return { ...l, reacts: r }; }) }));
    await fetch(apiUrl('/api/reputation/reactions'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room: d?.room || `city-${city}`, messageId: id, emoji, voter: voter(addr) }) }).catch(() => {});
  };
  const mod = async (l, act) => {
    if (!need() || ((act === 'pull' || act === 'mute') && !window.confirm(act === 'mute' ? `Pull this line and mute ${l.name} for an hour?` : 'Pull this line off the street?'))) return;
    try { const r = await fetch(apiUrl(`/api/reputation/familia/street/${city}/mod`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, id: l.id, act }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Could not pull it'); toast.success({ mute: '🔇 pulled + muted 1h', pin: '📌 pinned for an hour', unpin: '📌 pin taken down' }[act] || '🗑 pulled'); load(); }
    catch (err) { toast.error(err.message); }
  };
  const slowSet = async sec => {
    if (!need()) return;
    try { const r = await fetch(apiUrl(`/api/reputation/familia/street/${city}/mod`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, act: 'slow', sec }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Could not set slow mode'); toast.success(sec ? `🐢 slow mode: one line every ${sec}s for 30 min` : '🐢 slow mode off'); setTool(null); load(); }
    catch (err) { toast.error(err.message); }
  };
  const put = s => { setT(v => (v ? `${v.trimEnd()} ${s}` : s)); setTimeout(() => input.current?.focus(), 0); };
  const at = h => put(`@${String(h).replace(/\s+/g, '')} `);
  const v = d?.vitals || {}; const mods = d?.mod || {};
  const heat = Math.max(0, Math.min(3, v.heat || 0)); const slow = d?.slow;
  return <section className={`st m-card k-${city} is-heat-${heat}`} data-testid="city-chat">
    <StreetScene name={name} heat={heat} />
    <header className="st-head">
      <span className="st-title"><em>THE STREETS</em><b>{name}</b></span>
      <span className="st-live" data-tip="Wallets reading this street right now (invisible ones never show)"><i />{n0(here)}<small>ON THE BLOCK</small></span>
      <span className="st-pulse"><Spark bars={v.spark} /><b>{n0(hour)}</b><small>LINES / HR</small></span>
      <HeatMeter heat={heat} />
      {slow ? <span className="st-slow" data-tip={`🐢 Slow mode by ${slow.by || 'a Don'}: one line every ${slow.sec}s per wallet (Dons + staff exempt) · lifts in ${Math.ceil((slow.left || 0) / 60)}m`} data-testid="st-slow">🐢 <b>{slow.sec}s</b><small>SLOW</small></span> : null}
      {v.hot ? <button type="button" className="st-hot" onClick={() => { const l = lines.find(x => (x.calls || []).some(c => c.symbol === v.hot.symbol)); const c = l?.calls?.find(x => x.symbol === v.hot.symbol); if (c) familiaTrade({ chainId: c.chain, pairAddress: c.pairAddress, baseToken: { symbol: c.symbol } }); }}
        data-tip={`Hottest call on this street: ${v.hot.by}${v.hot.fam ? ` [${v.hot.fam}]` : ''} · now ${xWord(v.hot.x)}`} data-testid="st-hot">🔥 ${v.hot.symbol} <b>{xWord(v.hot.peakX)}</b></button> : null}
    </header>
    <HitsTape hits={d?.hits} />
    {(d?.here || []).length ? <div className="st-here" data-testid="st-here">{d.here.slice(0, 14).map((h, i) => <button key={h.address} type="button" className="st-who-here" style={{ '--i': i, '--fc': h.fam?.color || '#8f8470' }}
      onClick={() => at(h.name)} data-tip={`${h.fam ? `[${h.fam.tag}] ` : ''}${h.name} — tap to mention`}>{h.fam?.badge ? <FamilyCrest b={h.fam.badge} px={18} banner={false} sheen={false} /> : <i>{String(h.name || '?')[0]}</i>}</button>)}
      {d.hereN > 14 ? <small>+{d.hereN - 14}</small> : null}{(v.families || []).length ? <em>{v.families.length} famil{v.families.length === 1 ? 'y' : 'ies'} talking</em> : null}</div> : null}
    {d?.pinned ? <div className="st-pinned" data-testid="st-pinned"><em>📌 PINNED · {d.pinned.pinnedBy || 'a Don'} · {Math.ceil((d.pinned.left || 0) / 60)}m left</em>
      <p><b>{d.pinned.fam ? `[${d.pinned.fam.tag}] ` : ''}{d.pinned.name}</b> {String(d.pinned.text || '').slice(0, 140)}</p>
      {(d.pinned.calls || []).length ? <span className="st-coins">{d.pinned.calls.map(c => <Receipt key={c.pairAddress} c={c} />)}</span> : null}
      {mods.staff || mods.don ? <button type="button" className="st-act" onClick={() => mod(d.pinned, 'unpin')} aria-label="Unpin" data-tip="Take the pin down">✕</button> : null}</div> : null}
    <ol className="st-log" ref={logRef} onScroll={e => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60; }}>
      {lines.map(l => <Line key={l.id} l={l} fresh={fresh.has(l.id)} reacts={d?.reacts || ['🔥', '💀', '🫡', '💰']} canPull={mods.staff || (mods.don && l.fam?.id && l.fam.id === mods.famId)} canPin={!!(mods.staff || mods.don)} staff={mods.staff}
        onReact={react} onReply={x => { setReply(x); input.current?.focus(); }} onMod={mod} onAt={at} />)}
      {!lines.length ? <li className="st-nil">{d ? `Dead quiet on ${name}. Say something — your family crest rides with you.` : 'Walking onto the block…'}</li> : null}
    </ol>
    <form className="st-form" onSubmit={send}>
      {reply ? <p className="st-reply"><span>↩ replying to <b>{reply.name}</b>: {String(reply.text).slice(0, 60)}</span><button type="button" onClick={() => setReply(null)} aria-label="Cancel the reply">✕</button></p> : null}
      <div className="st-tools m-seg" role="group" aria-label="Street tools">
        <button type="button" className={tool === 'call' ? 'active' : ''} onClick={() => { setTool(x => (x === 'call' ? null : 'call')); put('📞 CALL '); }} data-tip="Call a coin: paste its contract — the line becomes a coin card with a live receipt" data-testid="st-tool-call">📞 Call</button>
        <button type="button" onClick={() => put(`🛡 RALLY — ${d?.me?.fam?.tag ? `[${d.me.fam.tag}] ` : ''}hold the block`)} data-tip="Rally your family on this street" data-testid="st-tool-rally">🛡 Rally</button>
        <button type="button" className={tool === 'at' ? 'active' : ''} onClick={() => setTool(x => (x === 'at' ? null : 'at'))} data-tip="Mention someone on the block" data-testid="st-tool-at">@ Here</button>
        {mods.staff || mods.don ? <button type="button" className={tool === 'slow' ? 'active' : ''} onClick={() => setTool(x => (x === 'slow' ? null : 'slow'))} data-tip="🐢 Slow the street: one line per wallet every N seconds for 30 minutes (Dons + staff)" data-testid="st-tool-slow">🐢 Slow</button> : null}
      </div>
      {tool === 'slow' ? <div className="st-slowpick m-seg" role="group" aria-label="Slow mode">{(d?.slowChoices || [0, 10, 30, 60]).map(s2 => <button key={s2} type="button" className={(slow?.sec || 0) === s2 ? 'active' : ''} aria-pressed={(slow?.sec || 0) === s2}
        onClick={() => slowSet(s2)} data-tip={s2 ? `One line every ${s2}s per wallet` : 'Lift slow mode'} data-testid={`st-slow-${s2}`}>{s2 ? `${s2}s` : 'Off'}</button>)}</div> : null}
      {tool === 'at' ? <div className="st-atpick">{(d?.here || []).length ? d.here.slice(0, 12).map(h => <button key={h.address} type="button" onClick={() => { at(h.name); setTool(null); }}>{h.fam ? `[${h.fam.tag}] ` : ''}{h.name}</button>) : <small>No one else on the block right now.</small>}</div> : null}
      {tool === 'call' ? <p className="st-hint">Paste the coin's contract after 📞 CALL — FEELESS pins its price now and keeps the receipt.</p> : null}
      <div className="st-send"><input ref={input} className="m-input" value={t} maxLength={280} onChange={e => setT(e.target.value)} placeholder={`Talk on ${name}…`} aria-label={`Chat on ${name}`} data-testid="st-input" />
        <button type="submit" className={`m-btn m-go st-go ${coolLeft ? 'is-cool' : ''}`} disabled={busy || !t.trim() || coolLeft > 0} data-tip={coolLeft ? `🐢 Slow mode — your next line in ${coolLeft}s` : 'Post to this street'} data-testid="st-send">
          {coolLeft ? <><span className="st-cool" style={{ '--s': `${coolDur.current || coolLeft}s` }} key={cool} />🐢 {coolLeft}s</> : busy ? '…' : 'SEND'}</button></div>
    </form>
  </section>;
}

import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Slider } from '@heroui/react';
import '../../styles/proofRooms.css';
import { WatchLive } from './WatchLive';

// 🧮 Tools that keep a user inside its proof folders: real maths on what they type, nothing guessed. And a watch room for PoB: only official players and services the user signs in to.
const num = v => (Number(v) || 0);
const usd = v => `$${(Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const Field = ({ label, value, set, u, tip, id }) => <label className="prm-f" data-tip={tip}><span>{label}</span><span className="prm-in"><input className="m-input m-num" type="number" min="0" step="any" value={value} onChange={e => set(e.target.value)} aria-label={label} data-testid={`prm-${id}`} />{u ? <i>{u}</i> : null}</span></label>;
const Out = ({ rows }) => <ul className="prm-out">{rows.map(([k, v, tone, tip]) => <li key={k} data-tip={tip}><small>{k}</small><b className={`m-num ${tone || ''}`}>{v}</b></li>)}</ul>;

/** Long or short: where it gets liquidated, and what a target and a stop are worth. Maintenance margin is the usual 0.5%. */
export function perpMaths({ size, lev, entry, stop, target, long = true }) {
  const margin = lev > 0 ? size / lev : 0; const dir = long ? 1 : -1; const pct = (p) => (entry > 0 ? (dir * (p - entry)) / entry : 0);
  const liq = entry > 0 && lev > 0 ? entry * (1 - dir * (1 / lev - 0.005)) : 0; const win = pct(target) * size; const loss = pct(stop) * size;
  return { margin, liq, win, loss, rr: loss < 0 ? win / -loss : 0, stopSafe: stop > 0 && (long ? stop > liq : stop < liq) };
}
function PerpCalc() {
  const [long, setLong] = useState(true); const [size, setSize] = useState('100'); const [lev, setLev] = useState(5); const [entry, setEntry] = useState('100'); const [stop, setStop] = useState('95'); const [target, setTarget] = useState('115');
  const m = perpMaths({ size: num(size), lev, entry: num(entry), stop: num(stop), target: num(target), long });
  return <section className="prm-card" data-testid="prm-perp"><h5>POSITION CHECK</h5><span className="m-seg" role="group" aria-label="Side">{[[true, 'Long'], [false, 'Short']].map(([v, l]) => <button key={l} type="button" className={long === v ? 'active' : ''} aria-pressed={long === v} onClick={() => setLong(v)} data-testid={`prm-side-${l}`}>{l}</button>)}</span>
    <div className="prm-grid"><Field label="Size" value={size} set={setSize} u="$" id="size" /><Field label="Entry" value={entry} set={setEntry} id="entry" /><Field label="Stop" value={stop} set={setStop} id="stop" /><Field label="Target" value={target} set={setTarget} id="target" /></div>
    <label className="prm-lev"><span>Leverage <b className="m-num">{lev}x</b></span><Slider aria-label="Leverage" minValue={1} maxValue={100} step={1} value={lev} onChange={v => setLev(Number(v))}><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider></label>
    <Out rows={[['MARGIN', usd(m.margin)], ['LIQUIDATED AT', Number(m.liq.toPrecision(5)), m.stopSafe ? '' : 'is-dn', m.stopSafe ? 'Your stop hits first' : 'Liquidation hits before your stop'], ['AT TARGET', usd(m.win), 'is-up'], ['AT STOP', usd(m.loss), 'is-dn'], ['REWARD TO RISK', `${m.rr.toFixed(2)}R`, m.rr >= 2 ? 'is-up' : '']]} />
    {!m.stopSafe ? <p className="prm-warn" data-testid="prm-liq-warn">Liquidation hits before your stop. Lower the leverage or move the stop.</p> : null}</section>;
}
/** A coin buy: what each exit brings, after the slippage and fees the user expects both ways. */
export function exitLadder({ buy, cost, rungs }) {
  const left = Math.max(0, 1 - (cost / 100) * 2); let out = 0; const rows = rungs.map(([x, part]) => { const got = buy * left * (part / 100) * x; out += got; return { x, part, got }; });
  return { rows, out, even: left > 0 ? 1 / left : 0, profit: out - buy };
}
function CoinCalc() {
  const [buy, setBuy] = useState('50'); const [cost, setCost] = useState('2'); const m = exitLadder({ buy: num(buy), cost: num(cost), rungs: [[1.5, 25], [2, 25], [3, 25], [5, 25]] });
  return <section className="prm-card" data-testid="prm-coin"><h5>EXIT LADDER</h5><div className="prm-grid"><Field label="Buy" value={buy} set={setBuy} u="$" id="buy" /><Field label="Slippage + fees, each way" value={cost} set={setCost} u="%" tip="Thin pools cost more" id="cost" /></div>
    <ol className="prm-rungs">{m.rows.map(r => <li key={r.x}><b className="m-num">{r.x}x</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.min(1, r.x / 5)})` }} /></i><small>sell {r.part}%</small><em className="m-num">{usd(r.got)}</em></li>)}</ol>
    <Out rows={[['BREAKS EVEN AT', `${m.even.toFixed(3)}x`, '', 'What it must reach just to cover costs'], ['IF ALL 4 HIT', usd(m.out), 'is-up'], ['PROFIT', usd(m.profit), m.profit >= 0 ? 'is-up' : 'is-dn']]} /></section>;
}
const LIMITS = [['X', 280], ['Thread post', 280], ['Telegram', 4096], ['TikTok caption', 2200], ['Instagram', 2200]];
export const splitThread = (text, cap = 270) => { const out = []; let cur = ''; String(text || '').split(/\s+/).filter(Boolean).forEach(w => { if ((`${cur} ${w}`).trim().length > cap) { out.push(cur); cur = w; } else cur = `${cur} ${w}`.trim(); }); if (cur) out.push(cur); return out; };
function PostDesk() {
  const [t, setT] = useState(''); const parts = splitThread(t); const hook = t.split(/[.!?\n]/)[0] || ''; const words = t.split(/\s+/).filter(Boolean).length;
  return <section className="prm-card" data-testid="prm-post"><h5>POST DESK</h5><textarea className="m-input" rows={3} value={t} onChange={e => setT(e.target.value)} placeholder="Paste a draft" aria-label="Draft" data-testid="prm-draft" />
    <Out rows={[['WORDS', words], ['READ TIME', `${Math.max(1, Math.ceil(words / 200))} min`], ['HOOK', `${hook.length} letters`, hook.length && hook.length <= 70 ? 'is-up' : '', 'The first line. Under 70 letters shows in full in most feeds'], ['THREAD', `${parts.length} posts`]]} />
    <ul className="prm-limits">{LIMITS.map(([k, n]) => { const part = t.length / n; return <li key={k} className={part > 1 ? 'is-over' : ''}><small>{k}</small><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.min(1, part)})` }} /></i><em className="m-num">{t.length}/{n}</em></li>; })}</ul></section>;
}
const TOOLS = { pow: CoinCalc, pop: PerpCalc, content: PostDesk };
export function ProofCalc({ kind }) { const T = TOOLS[kind]; return T ? <T /> : null; }

// 📺 Watch inside FEELESS, official sources only. A link becomes the provider's own player. Paid services open in the agent's browser, where the user signs in themself.
const SERVICES = [['espn.com/watch', 'ESPN', 'Sports, with a TV or ESPN+ sign-in'], ['nba.com/watch', 'NBA', 'League Pass and free clips'], ['nfl.com/plus', 'NFL+', 'Live local and prime games on phones'], ['mlb.tv', 'MLB.TV', 'Out-of-market games'], ['nhl.com/video', 'NHL', 'Highlights, and games by region'], ['ufcfightpass.com', 'UFC Fight Pass', 'Fights and archives'], ['tv.youtube.com', 'YouTube TV', 'Live channels'], ['peacocktv.com', 'Peacock', 'Sports, NBC shows and movies, your Peacock sign-in'], ['plus.fifa.com', 'FIFA+', 'Free football: classic matches, docs and some live games'], ['dazn.com', 'DAZN', 'Boxing and football, a free tier and paid'], ['twitch.tv', 'Twitch', 'Free live streams']];
/** The provider's official player for a link, or null. Only YouTube and Twitch: nothing else is embedded. */
export function playerFor(link, parent = 'localhost') {
  let u; try { u = new URL(String(link || '').trim()); } catch { return null; } const host = u.hostname.replace(/^www\.|^m\./, ''); const clean = v => (/^[\w-]{2,64}$/.test(v || '') ? v : null); const parts = u.pathname.split('/').filter(Boolean);
  if (host === 'youtu.be') { const id = clean(parts[0]); return id ? `https://www.youtube-nocookie.com/embed/${id}` : null; }
  if (host === 'youtube.com') { const id = clean(u.searchParams.get('v') || (['live', 'shorts', 'embed'].includes(parts[0]) ? parts[1] : null)); return id ? `https://www.youtube-nocookie.com/embed/${id}` : null; }
  if (host === 'twitch.tv' && parts[0]) { if (parts[0] === 'videos') { const id = clean(parts[1]); return id ? `https://player.twitch.tv/?video=${id}&parent=${parent}` : null; } const ch = clean(parts[0]); return ch ? `https://player.twitch.tv/?channel=${ch}&parent=${parent}` : null; }
  return null;
}
const WATCH_KEY = 'feeless:watch';
// 📺 Free and legal: official channels' own players, and free services that open in its browser. Every channel id was read from YouTube itself on 2026-11-07. Nothing unlicensed is ever listed or fetched.
const FREE_SPORTS = [['NBA', 'UCWJ2lWNubArHWmf3FIHbfcQ'], ['NFL', 'UCDVYQ4Zhbm3S2dlz7P1GBDg'], ['MLB', 'UCoLrcjPV5PbUrUyXq5mjc_A'], ['NHL', 'UCRsrhXtzXmzYX_fiyNHHxbw'], ['WNBA', 'UCO9a_ryN_l7DIDS-VIt-zmw'], ['UFC', 'UCPQDDlGe7lbgmEJ0ge7a_JA'], ['ESPN', 'UCiio0ydw439X13KyZgMIcHw'], ['WWE', 'UCNSnSemXKDc9UEZ7m31wY9Q'], ['FIFA', 'UCpcTrCXblq78GZrTUTLWeBw'], ['Premier League', 'UCpryVRk_VDudG8SHXgWcG0w'], ['LaLiga', 'UCTv-XvfzLX3i4IGWAm4sbmA'], ['Olympics', 'UC_kdjhHnkUbSImMrezjRyDQ'], ['DAZN Boxing', 'UCQpbsCYqUl-KfJL_X_TDrHg'], ['Tennis Channel', 'UCVCymDWUpiGZm0yiY-ovNEg'], ['Red Bull', 'UC8VddvuHJzIj__Ud0rY2_ww']];
const FREE_MORE = [['NASA', 'UC9SM7V7J1pAhPabOUST01fw'], ['Bloomberg', 'UCyxnPZfofoutjmyvaV0GGeQ'], ['ABC News', 'UCBi2mrWuNuyYy4gbM6fU18Q'], ['Tubi', 'UCNDsk0uhSlG1-br1Ex2Rgfg']];
const FREE_SITES = [['Tubi', 'tubitv.com', 'Free movies and shows'], ['Pluto TV', 'pluto.tv/live-tv', 'Free live TV channels'], ['The Roku Channel', 'therokuchannel.roku.com', 'Free movies and live TV'], ['Plex', 'watch.plex.tv/live-tv', 'Free live TV']];
export const channelLive = id => `https://www.youtube-nocookie.com/embed/live_stream?channel=${id}`;
export const channelLatest = id => `https://www.youtube-nocookie.com/embed/videoseries?list=UU${id.slice(2)}`;
// 🎬 HIGHLIGHTS (owner 2026-11-12: "recent highlights per gamer or team"): the newest videos across every official league channel plus any
// channel you follow by @handle (a team, a gamer, a creator), filtered by the name you type. Free, no key: each channel's public feed
// (newest 15 per channel), read by the server every 10 min at most and shared by everyone. Plays in YouTube's own player.
const FOLLOW_KEY = 'feeless:watch:follow';
const ago = iso => { const s = Math.max(0, (Date.now() - Date.parse(iso)) / 1000); return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m ago` : s < 86400 ? `${Math.round(s / 3600)}h ago` : `${Math.round(s / 86400)}d ago`; };
const views = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n || 0));
export function Highlights({ onPlay }) {
  const [follow, setFollow] = useState(() => { try { return JSON.parse(localStorage.getItem(FOLLOW_KEY) || '[]'); } catch { return []; } });
  const [q, setQ] = useState(''); const [shorts, setShorts] = useState(false); const [d, setD] = useState(null); const [err, setErr] = useState(''); const [handle, setHandle] = useState(''); const [adding, setAdding] = useState(false);
  const ids = useMemo(() => [...follow.map(f => f.id), ...FREE_SPORTS.map(x => x[1])].slice(0, 30).join(','), [follow]);
  useEffect(() => { let on = true; const t = setTimeout(() => { fetch(apiUrl(`/api/reputation/watch/highlights?ch=${ids}&q=${encodeURIComponent(q.trim())}&shorts=${shorts ? 1 : 0}`)).then(r => r.json().then(j => (r.ok ? j : Promise.reject(new Error(j.detail || 'Could not read the channels.'))))).then(j => { if (on) { setD(j); setErr(''); } }).catch(e => on && setErr(e.message)); }, 300); return () => { on = false; clearTimeout(t); }; }, [ids, q, shorts]);
  const keep = next => { setFollow(next); try { localStorage.setItem(FOLLOW_KEY, JSON.stringify(next)); } catch { /* private window: kept for this visit */ } };
  const add = async e => { e.preventDefault(); setAdding(true); try { const r = await fetch(apiUrl(`/api/reputation/watch/channel?handle=${encodeURIComponent(handle.trim())}`)); const j = await r.json(); if (!r.ok) throw new Error(j.detail || 'Could not find it.'); if (!follow.some(f => f.id === j.id)) keep([j, ...follow].slice(0, 12)); setHandle(''); setErr(''); } catch (x) { setErr(x.message); } finally { setAdding(false); } };
  const vids = d?.videos || [];
  return <div className="prm-hl" data-testid="prm-hl"><small className="m-label">HIGHLIGHTS<em>{d ? `${vids.length} newest · ${d.read} of ${d.channels} channels read` : 'reading the channels…'}</em></small>
    <div className="prm-hl-bar"><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder="A team, player or gamer: Lakers, Messi, Ninja" aria-label="Find highlights" data-testid="prm-hl-q" />
      <button type="button" className={`m-chip${shorts ? ' active' : ''}`} aria-pressed={shorts} onClick={() => setShorts(x => !x)} data-tip="Include YouTube Shorts" data-testid="prm-hl-shorts">Shorts</button></div>
    <form className="prm-hl-bar" onSubmit={add}><input className="m-input" value={handle} onChange={e => setHandle(e.target.value)} placeholder="Follow any channel: @Ninja, @Lakers, @FIFA" aria-label="Follow a YouTube channel" data-testid="prm-hl-handle" /><button type="submit" className="m-btn" disabled={adding || handle.trim().length < 3} data-tip="Adds its newest videos to your highlights" data-testid="prm-hl-follow">{adding ? 'Finding…' : 'Follow'}</button></form>
    {follow.length ? <div className="prm-chs">{follow.map(f => <span key={f.id} className="m-chip prm-ch"><button type="button" onClick={() => setQ('')} data-tip={`${f.handle}: newest videos are in your highlights`}>{f.name}</button><button type="button" aria-label={`Unfollow ${f.name}`} onClick={() => keep(follow.filter(x => x.id !== f.id))} data-testid={`prm-hl-x-${f.id}`}>✕</button></span>)}</div> : null}
    {err ? <small className="kd-err" role="alert">{err}</small> : null}
    {vids.length ? <ul className="prm-hl-grid">{vids.slice(0, 24).map((v, i) => <li key={v.id} style={{ '--i': i }}><button type="button" onClick={() => onPlay(`https://www.youtube-nocookie.com/embed/${v.id}?autoplay=1`)} data-tip={v.title} data-testid={`prm-hl-v-${v.id}`}><img src={v.thumb} alt="" loading="lazy" /><b>{v.title}</b><small className="m-num">{v.channel} · {ago(v.at)}{v.views ? ` · ${views(v.views)} views` : ''}</small></button></li>)}</ul>
      : d ? <p className="prm-hl-none">{q ? `Nothing named “${q}” in the newest videos. Follow its own channel above to see more.` : 'No videos yet.'}</p> : null}
  </div>;
}
function WatchGuide({ onPlay, onBrowse }) {
  const [mode, setMode] = useState('live'); const src = id => (mode === 'live' ? channelLive(id) : channelLatest(id));
  const row = rows => rows.map(([n, id]) => <button key={n} type="button" className="m-chip prm-ch" onClick={() => onPlay(src(id))} data-tip={`${n}'s official ${mode === 'live' ? 'live stream, when it has one on' : 'newest videos'}`} data-testid={`prm-ch-${id}`}>{n}</button>);
  return <div className="prm-guide" data-testid="prm-guide"><span className="m-seg" role="radiogroup" aria-label="What to play">{[['live', 'Live now'], ['latest', 'Latest']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-tip={k === 'live' ? 'Their live stream. Says so if nothing is on' : 'Their newest videos'} data-testid={`prm-mode-${k}`}>{l}</button>)}</span>
    <small className="m-label">SPORTS, OFFICIAL AND FREE</small><div className="prm-chs">{row(FREE_SPORTS)}</div><small className="m-label">NEWS AND SPACE</small><div className="prm-chs">{row(FREE_MORE)}</div>
    {onBrowse ? <><small className="m-label">FREE MOVIES AND TV</small><div className="prm-chs">{FREE_SITES.map(([n, h, what]) => <button key={n} type="button" className="m-chip prm-ch" onClick={() => onBrowse(h)} data-tip={`${what}. Opens in its browser`} data-testid={`prm-site-${n.split(' ')[0]}`}>{n}</button>)}</div></> : null}</div>;
}
// 📺 The Watch folder: a wall of up to 4 official players, each its own game or stream, with the sound where you want it.
export function WatchWall({ onBrowse, onCommand, price = '' }) {
  const [n, setN] = useState(() => { try { return Math.min(4, Math.max(1, +localStorage.getItem('feeless.watch.n') || 1)); } catch { return 1; } });
  const pick = v => { setN(v); try { localStorage.setItem('feeless.watch.n', String(v)); } catch { /* it still changes for now */ } };
  return <div className="prm-wall" data-testid="prm-wall"><span className="m-seg" role="radiogroup" aria-label="How many screens">{[1, 2, 4].map(v => <button key={v} type="button" role="radio" aria-checked={n === v} className={n === v ? 'active' : ''} onClick={() => pick(v)} data-tip={`${v} screen${v > 1 ? 's' : ''}. Each plays its own link`} data-testid={`prm-wall-${v}`}>{v === 1 ? 'One screen' : `${v} screens`}</button>)}</span><div className="prm-wall-main"><div className={`prm-wall-grid is-${n}`}>{Array.from({ length: n }, (_, i) => <WatchRoom key={i} onBrowse={onBrowse} />)}</div><WatchLive onBrowse={onBrowse} onCommand={onCommand} price={price} /></div></div>;
}
export function WatchRoom({ onBrowse }) {
  const [link, setLink] = useState(''); const [err, setErr] = useState(''); const [saved, setSaved] = useState(() => { try { return JSON.parse(localStorage.getItem(WATCH_KEY) || '[]'); } catch { return []; } }); const [on, setOn] = useState(null); const parent = useMemo(() => (typeof window === 'undefined' ? 'localhost' : window.location.hostname), []);
  const play = l => { const src = playerFor(l, parent); if (!src) { setErr('Paste a YouTube or Twitch link. Other services open below, where you sign in.'); return; } setErr(''); setOn(src); const next = [l, ...saved.filter(x => x !== l)].slice(0, 8); setSaved(next); try { localStorage.setItem(WATCH_KEY, JSON.stringify(next)); } catch { /* private window */ } setLink(''); };
  return <section className="prm-card prm-watch" data-testid="prm-watch"><h5>WATCH ROOM<small>Official players and your own subscriptions</small></h5>
    {on ? <div className="prm-screen"><iframe title="Official player" src={on} allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowFullScreen sandbox="allow-scripts allow-same-origin allow-presentation allow-popups" referrerPolicy="strict-origin-when-cross-origin" data-testid="prm-player" /><button type="button" className="m-btn" onClick={() => setOn(null)} aria-label="Close the player" data-tip="Close the player">✕</button></div> : null}
    <Highlights onPlay={src => { setErr(''); setOn(src); }} />
    <WatchGuide onPlay={src => { setErr(''); setOn(src); }} onBrowse={onBrowse} />
    <form className="prm-link" onSubmit={e => { e.preventDefault(); play(link); }}><input className="m-input" value={link} onChange={e => setLink(e.target.value)} placeholder="Paste a YouTube or Twitch link" aria-label="Video link" data-testid="prm-link" /><button type="submit" className="m-btn m-go" disabled={!link.trim()} data-testid="prm-play">Play</button></form>{err ? <small className="kd-err" role="alert">{err}</small> : null}
    {saved.length ? <div className="prm-saved">{saved.map(l => <button key={l} type="button" className="m-chip" onClick={() => play(l)} data-tip={l}>{l.replace(/^https?:\/\/(www\.)?/, '').slice(0, 28)}</button>)}</div> : null}
    <ul className="prm-services">{SERVICES.map(([h, n, w]) => <li key={h}><button type="button" onClick={() => onBrowse?.(h)} disabled={!onBrowse} data-tip="Opens in its browser here. You sign in yourself, and FEELESS never sees the password" data-testid={`prm-svc-${n}`}><b>{n}</b><small>{w}</small></button></li>)}</ul></section>;
}

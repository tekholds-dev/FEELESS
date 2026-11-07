import React, { useMemo, useState } from 'react';
import { Slider } from '@heroui/react';
import '../../styles/proofRooms.css';

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
const SERVICES = [['espn.com/watch', 'ESPN', 'Sports, with a TV or ESPN+ sign-in'], ['nba.com/watch', 'NBA', 'League Pass and free clips'], ['nfl.com/plus', 'NFL+', 'Live local and prime games on phones'], ['mlb.tv', 'MLB.TV', 'Out-of-market games'], ['nhl.com/video', 'NHL', 'Highlights, and games by region'], ['ufcfightpass.com', 'UFC Fight Pass', 'Fights and archives'], ['tv.youtube.com', 'YouTube TV', 'Live channels'], ['twitch.tv', 'Twitch', 'Free live streams']];
/** The provider's official player for a link, or null. Only YouTube and Twitch: nothing else is embedded. */
export function playerFor(link, parent = 'localhost') {
  let u; try { u = new URL(String(link || '').trim()); } catch { return null; } const host = u.hostname.replace(/^www\.|^m\./, ''); const clean = v => (/^[\w-]{2,64}$/.test(v || '') ? v : null); const parts = u.pathname.split('/').filter(Boolean);
  if (host === 'youtu.be') { const id = clean(parts[0]); return id ? `https://www.youtube-nocookie.com/embed/${id}` : null; }
  if (host === 'youtube.com') { const id = clean(u.searchParams.get('v') || (['live', 'shorts', 'embed'].includes(parts[0]) ? parts[1] : null)); return id ? `https://www.youtube-nocookie.com/embed/${id}` : null; }
  if (host === 'twitch.tv' && parts[0]) { if (parts[0] === 'videos') { const id = clean(parts[1]); return id ? `https://player.twitch.tv/?video=${id}&parent=${parent}` : null; } const ch = clean(parts[0]); return ch ? `https://player.twitch.tv/?channel=${ch}&parent=${parent}` : null; }
  return null;
}
const WATCH_KEY = 'feeless:watch';
// 📺 The Watch folder: a wall of up to 4 official players, each its own game or stream, with the sound where you want it.
export function WatchWall({ onBrowse }) {
  const [n, setN] = useState(() => { try { return Math.min(4, Math.max(1, +localStorage.getItem('feeless.watch.n') || 1)); } catch { return 1; } });
  const pick = v => { setN(v); try { localStorage.setItem('feeless.watch.n', String(v)); } catch { /* it still changes for now */ } };
  return <div className="prm-wall" data-testid="prm-wall"><span className="m-seg" role="radiogroup" aria-label="How many screens">{[1, 2, 4].map(v => <button key={v} type="button" role="radio" aria-checked={n === v} className={n === v ? 'active' : ''} onClick={() => pick(v)} data-tip={`${v} screen${v > 1 ? 's' : ''}. Each plays its own link`} data-testid={`prm-wall-${v}`}>{v === 1 ? 'One screen' : `${v} screens`}</button>)}</span><div className={`prm-wall-grid is-${n}`}>{Array.from({ length: n }, (_, i) => <WatchRoom key={i} onBrowse={onBrowse} />)}</div></div>;
}
export function WatchRoom({ onBrowse }) {
  const [link, setLink] = useState(''); const [err, setErr] = useState(''); const [saved, setSaved] = useState(() => { try { return JSON.parse(localStorage.getItem(WATCH_KEY) || '[]'); } catch { return []; } }); const [on, setOn] = useState(null); const parent = useMemo(() => (typeof window === 'undefined' ? 'localhost' : window.location.hostname), []);
  const play = l => { const src = playerFor(l, parent); if (!src) { setErr('Paste a YouTube or Twitch link. Other services open below, where you sign in.'); return; } setErr(''); setOn(src); const next = [l, ...saved.filter(x => x !== l)].slice(0, 8); setSaved(next); try { localStorage.setItem(WATCH_KEY, JSON.stringify(next)); } catch { /* private window */ } setLink(''); };
  return <section className="prm-card prm-watch" data-testid="prm-watch"><h5>WATCH ROOM<small>Official players and your own subscriptions</small></h5>
    {on ? <div className="prm-screen"><iframe title="Official player" src={on} allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowFullScreen sandbox="allow-scripts allow-same-origin allow-presentation allow-popups" referrerPolicy="strict-origin-when-cross-origin" data-testid="prm-player" /><button type="button" className="m-btn" onClick={() => setOn(null)} aria-label="Close the player" data-tip="Close the player">✕</button></div> : null}
    <form className="prm-link" onSubmit={e => { e.preventDefault(); play(link); }}><input className="m-input" value={link} onChange={e => setLink(e.target.value)} placeholder="Paste a YouTube or Twitch link" aria-label="Video link" data-testid="prm-link" /><button type="submit" className="m-btn m-go" disabled={!link.trim()} data-testid="prm-play">Play</button></form>{err ? <small className="kd-err" role="alert">{err}</small> : null}
    {saved.length ? <div className="prm-saved">{saved.map(l => <button key={l} type="button" className="m-chip" onClick={() => play(l)} data-tip={l}>{l.replace(/^https?:\/\/(www\.)?/, '').slice(0, 28)}</button>)}</div> : null}
    <ul className="prm-services">{SERVICES.map(([h, n, w]) => <li key={h}><button type="button" onClick={() => onBrowse?.(h)} disabled={!onBrowse} data-tip="Opens in its browser here. You sign in yourself, and FEELESS never sees the password" data-testid={`prm-svc-${n}`}><b>{n}</b><small>{w}</small></button></li>)}</ul></section>;
}

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { readChatSession, getChatSession } from '../../lib/chatSession';
import { Link } from 'react-router-dom';
import EcosystemChat from '../EcosystemChat';
import { Explain } from '../Explain';
import { openCoin } from '../CoinDrawer';
import { openTrenchTrade } from '../LiveTank';
import { RepMark } from '../RepMark';
import { apiUrl } from '../../lib/api';
import { sharedJson } from '../../lib/sharedJson';
import { useMarket } from '../../hooks/useMarket';
import { useLiveTokenMarkets } from '../../lib/liveTokens';
import { SHARE_TO, shareLinks } from '../../lib/socialShare';
import { FEED_BGS, FEED_FONTS, FEED_SIZES, FEED_ACCENTS, FEED_DENSITY, HANDLE_SITES, readLook, saveLook, lookVars, handleUrl } from '../../lib/feedLook';
import '../../styles/feed.css';
import '../../styles/feedPro.css';

// 📰 FEEd v5 (owner, 2026-10-28: "doesn't look like a feed, not lively"): ONE center column (≤ 600 px) under a sticky header — tabs (For you ·
// Following · Calls · 🔥 Heat · 🪦 Graveyard) + the source chips as one swipe row; a composer on top (paste a CA → a live coin card);
// a "↑ N new" pill instead of jumping the list; post cards with a live COIN CHIP (price + 5m, tap = the Trenches floor) and the CALL RECEIPT;
// threads on a connector line. Right rail (desktop) = search · pulse · trending coins · top callers · who to follow · your sites; a left mini-nav
// only ≥ 1250 px. Phone: the header folds away on scroll + a ✎ button opens the composer as a sheet. Duo wide: timeline | rail at the crease.
// Reading = /api/reputation/social-feed (one shared read, every 30s while visible). FEELESS alone = our live rooms with posting.
export const FEED_SRC = [['all', '✨', 'All'], ['feeless', '⚡', 'FEELESS'], ['x', '𝕏', 'X'], ['pump', '💊', 'Pump'], ['telegram', '✈', 'Telegram'], ['bluesky', '🦋', 'Bluesky']];
const POST_ONLY = [['reddit', '👽', 'Reddit']];
export const FEED_CATS = [['feed-general', '🌐', 'Everything', 'All the talk'], ['feed-alpha', '📈', 'Alpha & calls', 'Post a CA — 2×/5×/10× earns points'], ['feed-memes', '😂', 'Memes', 'Culture & coins'], ['feed-launches', '🚀', 'Launches', 'New coins, first looks'], ['feed-help', '🛟', 'Help', 'Ask anything'], ['feeless-updates', '📣', 'FEELESS', 'Official updates']];
const SRC_BADGE = { feeless: '⚡ FEELESS', x: '𝕏 X', pump: '💊 Pump', telegram: '✈ Telegram', bluesky: '🦋 Bluesky' };
const SRC_KEY = 'feeless.feedSrc';
const PAGE = 30;

const readSrc = () => { try { const v = JSON.parse(localStorage.getItem(SRC_KEY) || '["all"]'); return Array.isArray(v) && v.length ? v : ['all']; } catch { return ['all']; } };
/** a chip tap: All clears the rest; any site toggles in / out of the mix (never empty → All) */
export function toggleSrc(cur, k) {
  if (k === 'all') return ['all'];
  const s = new Set(cur.filter(x => x !== 'all'));
  if (s.has(k)) s.delete(k); else s.add(k);
  return s.size ? [...s] : ['all'];
}
export const agoWord = at => { const s = Math.max(0, Date.now() / 1000 - Number(at)); return s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

function useSocialFeed(src, on) {
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!on) return undefined;
    let alive = true;
    const url = `/api/reputation/social-feed${src ? `?src=${src}` : ''}`;
    const load = () => sharedJson(url, { maxAge: 25000 }).then(x => { if (alive && x) setD(x); }).catch(() => {});
    load(); const id = setInterval(() => { if (!document.hidden) load(); }, 30000);
    const now = () => sharedJson(url, { maxAge: 0, fresh: true }).then(x => { if (alive && x) setD(x); }).catch(() => {});
    window.addEventListener('feeless:feed-refresh', now);
    return () => { alive = false; clearInterval(id); window.removeEventListener('feeless:feed-refresh', now); };
  }, [src, on]);
  return d;
}

function ShareRow({ text, url, label = 'Post to' }) {
  const links = shareLinks(text, url);
  const off = !String(text || '').trim();
  return <div className="fd-share" role="group" aria-label={label}>{SHARE_TO.map(([k, ic, name]) =>
    <a key={k} className={`fd-sh is-${k} ${off ? 'is-off' : ''}`} href={off ? undefined : links[k]} target="_blank" rel="noopener noreferrer" aria-disabled={off} data-testid={`feed-share-${k}`}
      data-tip={`Opens ${name}'s own post box with this filled in — you press Post there, on your own account. FEELESS never holds your login.`}><b>{ic}</b><span>{name}</span></a>)}</div>;
}

const signIn = () => { toast.error('Connect your wallet and open chat once to sign in (one signature, 7 days).'); };
const reactPost = (body) => fetch(apiUrl('/api/reputation/social-feed/react'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Could not post'); return x; });
// pure: the "↑ N new posts" pill — posts newer than the newest one already on screen (the timeline never jumps under you)
export const newSince = (posts, seenAt) => (posts || []).filter(p => Number(p.at) > Number(seenAt || 0)).length;
// pure: compact counts (1.2K)
export const kWord = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n || 0));
// pure: the first Solana contract address in a text (base58, 32–44 chars) — a pasted CA becomes a live coin card in the composer
export const caOf = t => (String(t || '').match(/(?:^|[^1-9A-HJ-NP-Za-km-z])([1-9A-HJ-NP-Za-km-z]{32,44})(?![1-9A-HJ-NP-Za-km-z])/) || [])[1] || null;
const pctWord = v => (v == null || !Number.isFinite(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(Math.abs(v) >= 10 ? 0 : 1)}%`);
const pxWord = v => { const n = Number(v); if (!(n > 0)) return '—'; if (n >= 1) return `$${n.toFixed(2)}`; const z = Math.max(0, -Math.floor(Math.log10(n)) - 1); return `$${n.toFixed(Math.min(10, z + 3))}`; };
const capWord = n => (n == null ? '—' : n >= 1e6 ? `$${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}K` : `$${Math.round(n)}`);

// 🪙 a live coin chip: DexScreener's deepest pool for the mint (batched, shared cache) → price + 5m + cap; tap = the Trenches floor
function CoinChip({ mint, symbol, pair, big }) {
  const go = () => (pair?.pairAddress ? openTrenchTrade({ chainId: pair.chainId || 'solana', pairAddress: pair.pairAddress }) : openCoin({ mint, symbol }));
  const m5 = Number(pair?.priceChange?.m5); const up = !(m5 < 0);
  return <button type="button" className={`fd-coin ${big ? 'is-big' : ''} ${pair ? (up ? 'is-up' : 'is-dn') : 'is-wait'}`} onClick={go} data-testid="feed-coin"
    data-tip={pair ? `$${String(pair.baseToken?.symbol || symbol).replace(/^\$/, '')} live — tap to open its Trenches floor (chart + Quick trade)` : 'Reading this coin live…'}>
    {pair?.info?.imageUrl ? <img src={pair.info.imageUrl} alt="" loading="lazy" /> : <i className="fd-coin-ico">$</i>}
    <b>${String(pair?.baseToken?.symbol || symbol || 'COIN').replace(/^\$/, '')}</b>
    <span className="fd-coin-px" key={pair?.priceUsd}>{pxWord(pair?.priceUsd)}</span>
    <em>{pctWord(pair?.priceChange?.m5)}<small>5m</small></em>
    {big ? <span className="fd-coin-kv"><small>MC</small>{capWord(Number(pair?.marketCap) || Number(pair?.fdv) || null)}<small>LIQ</small>{capWord(Number(pair?.liquidity?.usd) || null)}</span> : null}
    <span className="fd-coin-bar" aria-hidden="true"><i style={{ transform: `scaleX(${Math.min(1, Math.abs(m5 || 0) / 25)})` }} /></span>
  </button>;
}

function Composer({ me, sess, onPosted, sheet }) {
  const [t, setT] = useState(''); const [busy, setBusy] = useState(false); const ta = useRef(null);
  useEffect(() => { const q = e => { setT(String(e.detail || '').slice(0, 270) + '\n'); ta.current?.focus(); ta.current?.scrollIntoView?.({ block: 'center', behavior: 'smooth' }); };
    window.addEventListener('feeless:feed-quote', q); return () => window.removeEventListener('feeless:feed-quote', q); }, []);
  useEffect(() => { if (sheet) ta.current?.focus(); }, [sheet]);
  const ca = caOf(t); const live = useLiveTokenMarkets('solana', ca ? [ca] : []); const pair = ca ? live.get(ca) : null;
  const post = async () => {   // ⚡ straight onto FEELESS (the Everything room) — the same signed chat path every room uses
    if (!me || !sess) { signIn(); return; }
    setBusy(true);
    try { const r = await fetch(apiUrl('/api/reputation/chat'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room: 'feed-general', address: me, text: t.trim(), ts: Math.floor(Date.now() / 1000), session: sess }) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Could not post'); setT(''); toast.success('⚡ posted on FEELESS'); window.dispatchEvent(new CustomEvent('feeless:feed-refresh')); onPosted?.(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  const left = 270 - t.length;
  return <div className={`fd-compose ${t ? 'is-typing' : ''}`} data-testid="feed-compose">
    <i className="fd-compose-ava" aria-hidden="true">{me ? me.slice(0, 1).toUpperCase() : '⚡'}</i>
    <div className="fd-compose-main">
      <textarea ref={ta} value={t} maxLength={270} onChange={e => setT(e.target.value)} placeholder="What's cooking in the trenches? Paste a CA to call it." rows={2} aria-label="New post" />
      {ca ? <div className="fd-compose-ca" data-testid="feed-ca-preview"><small>CALLING</small><CoinChip mint={ca} pair={pair} big /></div> : null}
      <div className="fd-compose-foot">
        <ShareRow text={t} label="also to" />
        <span className={`fd-ring ${left < 20 ? 'is-hot' : ''}`} style={{ '--p': (270 - left) / 270 }} data-tip={`${left} characters left`} aria-label={`${left} characters left`}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="10" className="on" pathLength="1" /></svg>{left < 20 ? <b>{left}</b> : null}</span>
        <button type="button" className="m-btn m-go fd-postbtn" disabled={!t.trim() || busy} onClick={post} data-testid="feed-post-feeless" data-tip="Posts on FEELESS (the Everything room). A CA in it becomes a tracked call: 2× / 5× / 10× earns season points.">{busy ? '…' : '⚡ Post'}</button>
      </div>
    </div>
  </div>;
}

// 𝕏 INTO FEEd (owner, 2026-10-19): reading X needs a paid API app, so people bring it in — paste an X post link and it joins the timeline
// (X's public oEmbed, no key, no login), marked with who shared it.
export const isXPost = u => /^https?:\/\/(www\.|mobile\.)?(x|twitter)\.com\/[A-Za-z0-9_]{1,15}\/status(es)?\/\d{5,25}/.test(String(u || '').trim());
function XShare({ me, sess }) {
  const [u, setU] = useState(''); const [busy, setBusy] = useState(false);
  const go = async (url = u) => {
    if (!isXPost(url)) { toast.error('Paste an X post link (x.com/name/status/…)'); return; }
    if (!me || !sess) { signIn(); return; }
    setBusy(true);
    try { const r = await fetch(apiUrl('/api/reputation/social-feed/x'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: me, session: sess, url: url.trim() }) });
      const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Could not bring it in');
      setU(''); toast.success(`𝕏 @${x.post?.handle || ''} is on FEEd`); window.dispatchEvent(new CustomEvent('feeless:feed-refresh')); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <form className="fd-xshare" onSubmit={e => { e.preventDefault(); go(); }} data-testid="feed-xshare">
    <i aria-hidden="true">𝕏</i>
    <input className="m-input" value={u} onChange={e => setU(e.target.value)} onPaste={e => { const t = e.clipboardData.getData('text'); if (isXPost(t)) { e.preventDefault(); setU(t); go(t); } }}
      placeholder="Paste an X post link to bring it into FEEd" aria-label="X post link" spellCheck={false} />
    <button type="submit" className="m-btn" disabled={busy || !u.trim()} data-testid="feed-xshare-go" data-tip="X's public embed — no key, no login. It joins the timeline marked with your name.">{busy ? '…' : 'Bring it in'}</button>
  </form>;
}

export const hashOf = id => { let h = 2166136261; for (const ch of String(id || '')) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16).padStart(8, '0').slice(0, 7); };
export const TABS = [['foryou', 'For you', 'Fresh posts lifted by stars, replies, calls and people you follow'], ['following', 'Following', 'Only people you follow (+ follow on any post)'],
  ['calls', 'Calls', 'Every post that names a coin — newest first'], ['heat', '🔥 Heat', 'Calls running since the post (1.1× or more), biggest first'], ['grave', '🪦 Graveyard', 'Calls that lost half or more', '🪦 Grave'],
  ['saved', '🔖', 'Posts you saved in this browser']];
const readSet = k => { try { return new Set(JSON.parse(localStorage.getItem(k) || '[]')); } catch { return new Set(); } };
const writeSet = (k, set) => { try { localStorage.setItem(k, JSON.stringify([...set].slice(-500))); } catch { /* private window */ } };
export const authorKey = p => `${p.src}:${String(p.handle || p.author || '').toLowerCase()}`;
// pure: what a tab shows. For you = newest, lifted 30 min per star, 1h per reply, 30 min for a coin call and 1h for someone you follow.
// trending = stars + 2 × replies in the last 24h (kept for older links / tests).
export function tabPosts(posts, tab, counts, follows, saved, now = Date.now() / 1000) {
  const all = posts || [];
  if (tab === 'following') return all.filter(p => follows.has(authorKey(p)));
  if (tab === 'saved') return all.filter(p => saved.has(p.id));
  if (tab === 'calls') return all.filter(p => p.coin?.mint || p.coin?.symbol).sort((a, b) => Number(b.at) - Number(a.at));
  if (tab === 'heat') return all.filter(p => p.coin?.x >= 1.1).sort((a, b) => b.coin.x - a.coin.x);
  if (tab === 'grave') return all.filter(p => p.coin?.x != null && p.coin.x <= 0.5).sort((a, b) => a.coin.x - b.coin.x);
  if (tab === 'trending') return all.filter(p => now - Number(p.at) < 86400).map(p => [p, (counts[p.id]?.likes || 0) + 2 * (counts[p.id]?.comments || 0)])
    .sort((a, b) => b[1] - a[1] || Number(b[0].at) - Number(a[0].at)).map(x => x[0]);
  if (tab === 'foryou') return all.map(p => [p, Number(p.at) + 1800 * Math.min(10, counts[p.id]?.likes || 0) + 3600 * Math.min(6, counts[p.id]?.comments || 0) + (p.coin ? 1800 : 0) + (follows.has(authorKey(p)) ? 3600 : 0)])
    .sort((a, b) => b[1] - a[1]).map(x => x[0]);
  return all;
}
// pure: the rail search — text, author, handle or $coin
export const matchQ = (p, q) => { const s = String(q || '').trim().toLowerCase().replace(/^\$/, ''); return !s || [p.text, p.author, p.handle, p.coin?.symbol].some(v => String(v || '').toLowerCase().includes(s)); };
// pure: who to follow — the most active authors on screen you don't follow yet
export const whoToFollow = (posts, follows, n = 4) => {
  const by = {}; (posts || []).forEach(p => { const k = authorKey(p); if (follows.has(k)) return; by[k] = by[k] || { k, p, n: 0, calls: 0 }; by[k].n += 1; if (p.coin) by[k].calls += 1; });
  return Object.values(by).sort((a, b) => b.calls - a.calls || b.n - a.n).slice(0, n);
};
const SHOW = 3;
// 🧾 FEELESS TWIST (owner, 2026-10-21): every post that names a coin carries its CALL RECEIPT from the server (cap when called / first seen →
// cap now = ×). Lenses 🔥 Heat + 🪦 Graveyard and the TRENCH WIRE ticker read the same receipts. `xWord`, `ladderAt`, `stampOf`, `wireRows` are pure + tested.
export const xWord = x => (x == null ? '—' : x >= 10 ? `${Math.round(x)}×` : `${x.toFixed(x >= 2 ? 1 : 2)}×`);
export const ladderAt = x => (x == null ? 0 : Math.max(0, Math.min(1, (Math.log10(Math.max(0.05, x)) + 1.3) / 2.3)));   // 0.05× … 10× on a log rail
export const stampOf = c => ({ moon: ['🚀', 'MOONING'], up: ['📈', 'RUNNING'], flat: ['➖', 'FLAT'], down: ['📉', 'BLEEDING'], rug: ['☠', 'RUGGED'] }[c?.state] || null);
export const wireRows = posts => (posts || []).filter(p => p.coin?.x != null).sort((a, b) => Math.abs(Math.log(b.coin.x)) - Math.abs(Math.log(a.coin.x))).slice(0, 14);

function CallReceipt({ c }) {
  const st = stampOf(c);
  return <button type="button" className={`fd-rcpt s-${c.state || 'none'}`} onClick={() => openCoin({ mint: c.mint, symbol: c.symbol })} data-testid="feed-receipt"
    data-tip={c.src === 'called' ? 'Pump called it at this cap — the multiple is since that call' : 'Since FEELESS first saw this post — the multiple is the cap then vs now'}>
    <span className="fd-rcpt-sym"><small>{c.src === 'called' ? 'CALLED' : 'SEEN'} {capWord(c.atMc)} → {capWord(c.mc)}</small></span>
    <span className="fd-rcpt-rail" aria-hidden="true"><i style={{ transform: `scaleX(${ladderAt(c.x)})` }} />{[2, 5, 10].map(k => <u key={k} style={{ left: `${ladderAt(k) * 100}%` }} data-k={`${k}×`} />)}</span>
    <strong key={c.x}>{xWord(c.x)}</strong>{st ? <em>{st[0]} {st[1]}</em> : null}
  </button>;
}

function TrenchWire({ posts }) {
  const rows = wireRows(posts);
  if (!rows.length) return null;
  const run = [...rows, ...rows];
  return <div className="fd-wire" data-testid="feed-wire"><span className="fd-wire-lbl">TRENCH<br />WIRE</span>
    <div className="fd-wire-win"><div className="fd-wire-run" style={{ '--n': rows.length }}>{run.map((p, i) => <button key={`${p.id}-${i}`} type="button" className={`s-${p.coin.state}`} onClick={() => openCoin({ mint: p.coin.mint, symbol: p.coin.symbol })} tabIndex={i < rows.length ? 0 : -1}>
      <b>${p.coin.symbol || '?'}</b><strong>{xWord(p.coin.x)}</strong><small>@{p.handle || p.author}</small></button>)}</div></div></div>;
}

function Ava({ src, name, kind }) {
  return src ? <img className={`fd-ava ring-${kind}`} src={src} alt="" loading="lazy" decoding="async" /> : <i className={`fd-ava fd-ini ring-${kind}`}>{String(name || '?').slice(0, 1).toUpperCase()}</i>;
}

function Thread({ p, me, sess, onCount, auto }) {
  const [list, setList] = useState(null); const [t, setT] = useState(''); const [busy, setBusy] = useState(false); const [all, setAll] = useState(false); const [box, setBox] = useState(!auto);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/social-feed/thread/${encodeURIComponent(p.id)}`)).then(r => r.json()).then(x => { if (on) setList(x.comments || []); }).catch(() => setList([])); return () => { on = false; }; }, [p.id]);
  const send = async () => { if (!me || !sess) { signIn(); return; } setBusy(true);
    try { const r = await reactPost({ address: me, session: sess, id: p.id, comment: t }); setList(l => [...(l || []), r.comment]); setT(''); onCount(r); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  const shown = list && !all && list.length > SHOW ? list.slice(0, SHOW) : list;
  return <div className="fd-thread" data-testid="feed-thread">
    {list == null ? <small className="fd-dim">reading replies…</small> : !list.length ? (box ? <small className="fd-dim">No replies yet — be first.</small> : null)
      : <ol>{shown.map((c, i) => <li key={`${c.at}-${i}`} style={{ '--i': i }}><Ava name={c.name} kind="reply" /><div><header><b>{c.name || 'anon'}</b><small>· {agoWord(c.at)}</small></header><p>{c.text}</p></div></li>)}
        {list.length > SHOW && !all ? <li className="fd-showmore"><button type="button" onClick={() => setAll(true)} data-testid="feed-show-rest">◎ Show the last {list.length - SHOW}</button></li> : null}</ol>}
    {box ? <form onSubmit={e => { e.preventDefault(); if (t.trim()) send(); }}><input className="m-input" value={t} maxLength={280} placeholder="Post your reply" onChange={e => setT(e.target.value)} aria-label="Reply" autoFocus={!auto} /><button type="submit" className="m-btn" disabled={!t.trim() || busy}>Reply</button></form>
      : <button type="button" className="fd-replyhere" onClick={() => setBox(true)}>↩ Reply</button>}
  </div>;
}

function Count({ n }) { return n ? <b className="fd-n" key={n}>{kWord(n)}</b> : null; }

function Post({ p, c, me, sess, onCount, follows, saved, toggle, live, i }) {
  const [share, setShare] = useState(false); const [open, setOpen] = useState(false); const [pop, setPop] = useState(false);
  const like = async () => { if (!me || !sess) { signIn(); return; } setPop(true); setTimeout(() => setPop(false), 520);
    try { onCount(await reactPost({ address: me, session: sess, id: p.id, like: true })); } catch (e) { toast.error(e.message); } };
  const quote = () => window.dispatchEvent(new CustomEvent('feeless:feed-quote', { detail: `❝ @${p.handle || p.author}: ${String(p.text || '').slice(0, 180)}` }));
  const link = () => { const u = p.url || `${window.location.origin}/terminal/profile?feed=${encodeURIComponent(p.id)}`; navigator.clipboard?.writeText(u).then(() => toast.success('🔗 link copied')).catch(() => {}); };
  const ak = authorKey(p); const fol = follows.has(ak); const sv = saved.has(p.id);
  const replies = c?.comments || 0;
  return <article className={`fd-post is-${p.src}${replies || open ? ' has-thread' : ''}${p.coin?.state ? ` c-${p.coin.state}` : ''}`} style={{ '--i': Math.min(i, 12) }} data-testid="feed-post">
    <div className="fd-ava-col"><Ava src={p.avatar} name={p.author} kind={p.src} /></div>
    <div className="fd-body">
      <header><b className="fd-name">{p.author}</b>{p.src === 'feeless' && p.address ? <RepMark address={p.address} compact /> : null}
        {p.handle && p.handle !== p.author ? <small className="fd-handle">@{p.handle}</small> : null}<small className="fd-time">· {agoWord(p.at)}</small>
        <em className={`fd-src is-${p.src}`}>{SRC_BADGE[p.src] || p.src}</em>
        <button type="button" className={`fd-follow ${fol ? 'is-on' : ''}`} onClick={() => toggle('follow', ak)} aria-pressed={fol} data-testid="feed-follow" data-tip={fol ? 'Unfollow — kept in this browser' : 'Follow — their posts land in Following'}>{fol ? '✓' : '+ follow'}</button></header>
      <p className="fd-text">{p.text}</p>
      {p.img ? <img className="fd-img" src={p.img} alt="" loading="lazy" decoding="async" /> : null}
      {p.coin?.mint ? <CoinChip mint={p.coin.mint} symbol={p.coin.symbol} pair={live} /> : null}
      {p.coin?.mint && p.coin.x != null ? <CallReceipt c={p.coin} /> : null}
      {p.sharedBy ? <small className="fd-shared">𝕏 brought in by {p.sharedBy}{p.url ? <> · <a href={p.url} target="_blank" rel="noopener noreferrer nofollow">open on X</a></> : null}</small> : null}
      <footer className="fd-bar">
        <button type="button" className={`fd-act is-reply ${open ? 'is-on' : ''}`} aria-expanded={open} onClick={() => setOpen(o => !o)} data-testid="feed-reply" data-tip="Reply in the thread"><i>↩</i><Count n={replies} /></button>
        <button type="button" className="fd-act is-rt" onClick={quote} data-testid="feed-quote" data-tip="Repost with your take — it lands in the composer"><i>⟲</i></button>
        <button type="button" className={`fd-act is-like ${c?.mine ? 'is-liked' : ''} ${pop ? 'is-pop' : ''}`} aria-pressed={!!c?.mine} onClick={like} data-testid="feed-like" data-tip="Star it — lifts it in For you"><i>{c?.mine ? '★' : '☆'}</i><Count n={c?.likes} /></button>
        <button type="button" className={`fd-act is-share ${share ? 'is-on' : ''}`} aria-expanded={share} onClick={() => setShare(s => !s)} aria-label="Share" data-tip="Share to X, Telegram, Reddit…"><i>⇪</i></button>
        <span className="fd-right">
          <button type="button" className={`fd-act ${sv ? 'is-on' : ''}`} aria-pressed={sv} onClick={() => toggle('save', p.id)} aria-label="Save" data-testid="feed-save" data-tip={sv ? 'Saved — in the 🔖 tab' : 'Save it to the 🔖 tab'}><i>{sv ? '🔖' : '🏷'}</i></button>
          <button type="button" className="fd-act" onClick={link} aria-label="Copy link" data-tip="Copy the link"><i>🔗</i></button>
          <code className="fd-hash" data-tip="this post's id">{hashOf(p.id)}</code></span>
      </footer>
      {share ? <ShareRow text={p.text} url={p.url} /> : null}
      {open || replies ? <Thread p={p} me={me} sess={sess} onCount={onCount} auto={!open} key={open ? 'open' : 'auto'} /> : null}
    </div>
  </article>;
}

function FeedTabs({ tab, setTab, follows, saved }) {
  const i = Math.max(0, TABS.findIndex(t => t[0] === tab));
  return <nav className="fd-tabs" role="tablist" aria-label="Timeline" style={{ '--t': i, '--tn': TABS.length }}>
    {TABS.map(([k, l, tip, short]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)} data-testid={`feed-tab-${k}`} data-tip={tip}>
      {short ? <><span className="fd-tl">{l}</span><span className="fd-ts">{short}</span></> : <span>{l}</span>}{k === 'following' && follows.size ? <i>{follows.size}</i> : k === 'saved' && saved.size ? <i>{saved.size}</i> : null}</button>)}
    <span className="fd-tabline" aria-hidden="true" /></nav>;
}

function useFeedTab() {
  const [tab, setTab0] = useState(() => { try { const v = localStorage.getItem('feeless.feedTab'); return TABS.some(t => t[0] === v) ? v : 'foryou'; } catch { return 'foryou'; } });
  const setTab = t => { setTab0(t); try { localStorage.setItem('feeless.feedTab', t); } catch { /* private */ } };
  return [tab, setTab];
}
function useMarks() {
  const [follows, setFollows] = useState(() => readSet('feeless.feedFollow')); const [saved, setSaved] = useState(() => readSet('feeless.feedSaved'));
  const toggle = (kind, k) => { const [cur, set, key] = kind === 'follow' ? [follows, setFollows, 'feeless.feedFollow'] : [saved, setSaved, 'feeless.feedSaved'];
    const nx = new Set(cur); if (nx.has(k)) nx.delete(k); else nx.add(k); writeSet(key, nx); set(nx); };
  return { follows, saved, toggle };
}

function Timeline({ d, tab, q, me, sess, marks }) {
  const { follows, saved, toggle } = marks;
  const [n, setN] = useState(PAGE); const [seen, setSeen] = useState(0); const [cnt, setCnt] = useState({}); const top = useRef(null);
  const all = d?.posts || [];
  useEffect(() => { if (all.length && !seen) setSeen(Math.max(...all.map(p => Number(p.at) || 0))); }, [all, seen]);
  const base = (seen ? all.filter(p => Number(p.at) <= seen) : all).filter(p => matchQ(p, q));   // newer posts wait behind the pill
  const posts = tabPosts(base, tab, cnt, follows, saved);
  const fresh = newSince(all, seen);
  const ids = base.slice(0, Math.max(n, 60)).map(p => p.id).join(',');
  useEffect(() => { if (!ids) return undefined; let on = true;   // ONE batched counts read per refresh
    fetch(apiUrl(`/api/reputation/social-feed/counts?ids=${encodeURIComponent(ids)}${me ? `&address=${me}` : ''}`)).then(r => r.json()).then(x => { if (on) setCnt(c => ({ ...c, ...(x.counts || {}) })); }).catch(() => {});
    return () => { on = false; }; }, [ids, me, d?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const shown = posts.slice(0, n);
  const mints = useMemo(() => shown.map(p => p.coin?.mint).filter(Boolean), [shown.map(p => p.coin?.mint || '').join(',')]);   // eslint-disable-line react-hooks/exhaustive-deps
  const live = useLiveTokenMarkets('solana', mints);   // ONE batched live read for every coin chip on screen
  const setOne = id => r => setCnt(c => ({ ...c, [id]: { likes: r.likes, comments: r.comments, mine: r.mine } }));
  const empty = { following: ['👥', 'Follow people with “+ follow” on any post — their posts land here.'], saved: ['🔖', 'Tap 🏷 on any post to save it here.'], calls: ['📞', 'No coin calls on these sites yet — paste a CA in the composer to make the first.'],
    heat: ['🔥', 'No called coin is running right now — the wire lights up when one does.'], grave: ['🪦', 'No call has rugged lately. Stay sharp.'] }[tab] || ['📡', q ? `Nothing matches “${q}”.` : 'Nothing new on these sites yet.'];
  return <div className="fd-timeline" data-testid="feed-timeline" ref={top}>
    <TrenchWire posts={all} />
    {fresh && tab === 'foryou' ? <button type="button" className="fd-newpill" onClick={() => { setSeen(Math.max(...all.map(p => Number(p.at) || 0))); top.current?.scrollIntoView({ block: 'start', behavior: 'smooth' }); }} data-testid="feed-new" data-tip="Load the newest posts on top">
      <span className="fd-newpill-avas" aria-hidden="true">{all.filter(p => Number(p.at) > seen).slice(0, 3).map(p => <Ava key={p.id} src={p.avatar} name={p.author} kind={p.src} />)}</span>↑ {fresh} new post{fresh > 1 ? 's' : ''}</button> : null}
    {!d ? <div className="fd-skel" aria-label="Loading the feeds">{[0, 1, 2, 3].map(k => <span key={k} style={{ '--i': k }}><i /><b /><b /></span>)}</div>
      : !posts.length ? <p className="fd-empty"><i>{empty[0]}</i>{empty[1]}</p>
        : shown.map((p, i) => <Post key={p.id} i={i} p={p} c={cnt[p.id]} live={p.coin?.mint ? live.get(p.coin.mint) : null} me={me} sess={sess} follows={follows} saved={saved} toggle={toggle} onCount={r => setOne(p.id)({ ...(cnt[p.id] || {}), ...r, ...(r[p.id] || {}) })} />)}
    {posts.length > n ? <button type="button" className="fd-more" onClick={() => setN(x => x + PAGE)}>Show {Math.min(PAGE, posts.length - n)} more</button> : null}
  </div>;
}

// 🏆 Best FEEd callers this week: posts with a coin are tracked; 2×/5×/10× peaks earn season points.
function FeedCallers() {
  const [rows, setRows] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/calls/leaderboard?days=7&room=feed-')).then(r => (r.ok ? r.json() : {})).then(d => setRows(d.rows || [])).catch(() => setRows([])); }, []);
  const top = Math.max(1, ...(rows || []).map(r => r.hits || 0));
  return <div className="fd-card fd-callers" data-testid="feed-callers"><h4>🏆 Top callers <small>7d</small><Explain>Post a coin address in any FEEd room and it becomes a tracked call. If it later peaks at 2×, 5× or 10× from your post, you earn 50, 150 or 400 season points automatically.</Explain></h4>
    {!rows?.length ? <p className="fd-dim">Post a CA in FEEd — a 2×, 5× or 10× from your post earns season points.</p>
      : <ol>{rows.slice(0, 5).map((r, i) => <li key={r.caller} style={{ '--i': i }}>
        <i>{i + 1}</i>{r.callerAddress ? <Link to={`/terminal/profile/${r.callerAddress}`}>{r.caller}</Link> : <b>{r.caller}</b>}
        <span className="fd-callers-hit">{r.hits}/{r.calls}</span>{r.best ? <em>{r.best.symbol} {r.best.peakX.toFixed(1)}×</em> : null}
        <span className="fd-mbar" aria-hidden="true"><i style={{ transform: `scaleX(${(r.hits || 0) / top})` }} /></span></li>)}</ol>}
  </div>;
}

// 🔥 Trending coins beside the timeline: live 24h move bars; one click opens the Trenches floor.
function FeedTopCoins() {
  const { data } = useMarket('/feed?kind=trending&chain=solana', 60000);
  const pairs = (data?.pairs || []).filter(p => p.baseToken?.symbol).slice(0, 6);
  const top = Math.max(1, ...pairs.map(p => Math.abs(Number(p.priceChange?.h24) || 0)));
  return <div className="fd-card fd-trend" data-testid="feed-top-coins"><h4>🔥 Trending <small>live · 24h</small></h4>
    {!pairs.length ? <div className="fd-skel is-rows">{[0, 1, 2].map(k => <span key={k} style={{ '--i': k }}><b /></span>)}</div> : pairs.map((p, i) => { const ch = Number(p.priceChange?.h24); return <button type="button" key={p.pairAddress} style={{ '--i': i }}
      onClick={() => openTrenchTrade({ chainId: p.chainId, pairAddress: p.pairAddress })} data-tip={`Open $${p.baseToken.symbol}'s Trenches floor`}>
      {p.info?.imageUrl ? <img src={p.info.imageUrl} alt="" loading="lazy" /> : <span className="fd-dotico" />}<b>${p.baseToken.symbol}</b>
      <span className={`fd-mbar ${ch >= 0 ? '' : 'is-dn'}`} aria-hidden="true"><i style={{ transform: `scaleX(${Math.min(1, Math.abs(ch || 0) / top)})` }} /></span>
      <em className={ch >= 0 ? 'm-pos' : 'm-neg'}>{pctWord(ch)}</em></button>; })}
  </div>;
}

function WhoToFollow({ posts, marks }) {
  const rows = whoToFollow(posts, marks.follows);
  if (!rows.length) return null;
  return <div className="fd-card fd-who" data-testid="feed-who"><h4>👥 Who to follow</h4>
    {rows.map(({ k, p, n, calls }, i) => <div key={k} className="fd-who-row" style={{ '--i': i }}><Ava src={p.avatar} name={p.author} kind={p.src} />
      <span><b>{p.author}</b><small>{SRC_BADGE[p.src] || p.src} · {n} post{n > 1 ? 's' : ''}{calls ? ` · ${calls} call${calls > 1 ? 's' : ''}` : ''}</small></span>
      <button type="button" className="m-btn fd-who-go" onClick={() => marks.toggle('follow', k)} data-testid="feed-who-follow" data-tip={`Follow ${p.author} — their posts land in Following`}>Follow</button></div>)}
  </div>;
}

function Seg({ label, list, val, onPick, show = x => x[1] }) {
  return <div className="fd-lrow"><small>{label}</small><span className="m-seg" role="radiogroup" aria-label={label}>{list.map(x => <button key={x[0]} type="button" role="radio" aria-checked={val === x[0]} className={val === x[0] ? 'active' : ''} onClick={() => onPick(x[0])} data-testid={`feed-look-${label.toLowerCase()}-${x[0]}`}>{show(x)}</button>)}</span></div>;
}
/** 🎨 the FEEd look: background · font · text size · accent · density — remembered in this browser */
function LookPanel({ look, set, onClose }) {
  const up = k => v => set({ ...look, [k]: v });
  return <div className="fd-look" role="dialog" aria-label="FEEd look" data-testid="feed-look">
    <header><b>🎨 Make FEEd yours</b><button type="button" className="m-btn" onClick={onClose} aria-label="Close" data-tip="Close">✕</button></header>
    <Seg label="Background" list={FEED_BGS} val={look.bg} onPick={up('bg')} />
    <Seg label="Font" list={FEED_FONTS} val={look.font} onPick={up('font')} show={x => <span style={{ fontFamily: x[2] }}>{x[1]}</span>} />
    <Seg label="Text" list={FEED_SIZES} val={look.size} onPick={up('size')} />
    <Seg label="Accent" list={FEED_ACCENTS} val={look.accent} onPick={up('accent')} show={x => <i className="fd-dot" style={{ background: x[1] }} aria-label={x[0]} />} />
    <Seg label="Density" list={FEED_DENSITY} val={look.density} onPick={up('density')} />
  </div>;
}
/** 🔗 your own public handles (never a password / token): one-tap to your profile and to post there as you */
function MySites({ look, set }) {
  const [edit, setEdit] = useState(false); const [xv, setXv] = useState(null); const [busy, setBusy] = useState(false);
  const { wallet, signMessage } = useWallet() || {}; const me = wallet?.address;
  const h = look.handles || {};
  useEffect(() => { if (!me) return undefined; let on = true; fetch(apiUrl(`/api/reputation/profile/${me}`)).then(r => (r.ok ? r.json() : null)).then(d => on && setXv(d?.profile?.xVerified || null)).catch(() => {}); return () => { on = false; }; }, [me]);
  const signX = async () => {   // 𝕏 X's own sign-in (OAuth): you log in on x.com, FEELESS keeps only your verified @handle — no password, no token
    if (!me) { toast.error('Connect your wallet first.'); return; } setBusy(true);
    try { const session = await getChatSession(me, signMessage);
      const r = await fetch(apiUrl('/api/reputation/x/oauth/start'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: me, session, back: window.location.pathname + window.location.search }) });
      const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'X sign-in is not available.'); window.location.href = b.url; }
    catch (e) { toast.error(e.message); setBusy(false); } };
  return <div className="fd-card fd-sites" data-testid="feed-sites"><h4>🔗 Your sites <button type="button" className="m-btn" onClick={() => setEdit(e => !e)} data-testid="feed-sites-edit" data-tip="Add your public handles — never a password">{edit ? 'Done' : 'Connect'}</button></h4>
    {edit ? HANDLE_SITES.map(([k, ic]) => <label key={k} className="fd-hrow"><i>{ic}</i><input className="m-input" defaultValue={h[k] || ''} placeholder={k === 'x' ? '@yourhandle' : 'your name there'} maxLength={40}
      onBlur={e => set({ ...look, handles: { ...h, [k]: e.target.value } })} data-testid={`feed-handle-${k}`} /></label>)
      : HANDLE_SITES.some(([k]) => h[k]) ? <ul className="fd-hlist">{HANDLE_SITES.filter(([k]) => h[k]).map(([k, ic]) => <li key={k}><a href={handleUrl(k, h[k])} target="_blank" rel="noopener noreferrer">{ic} @{h[k]}</a></li>)}</ul>
      : <p className="fd-dim">Add your X / Reddit / Bluesky / Telegram name — one tap to your profile, and the post box posts there as you.</p>}
    {xv ? <p className="fd-xok" data-testid="feed-x-verified">𝕏 <b>@{xv.username}</b> · verified by X</p>
      : <button type="button" className="m-btn m-go fd-xsign" onClick={signX} disabled={busy} data-testid="feed-x-signin" data-tip="Log in on x.com itself — FEELESS gets only your verified @handle, never your password or a token">{busy ? 'Opening X…' : '𝕏 Sign in with X'}</button>}
  </div>;
}

// 📈 THE PULSE (2026-10-22 — owner: "FEEd needs live vitals"): what the timeline is doing in the last hour, from the same shared read — posts per
// 5 minutes as a drawn line, which sites are talking, and the coins being called most (tap → the coin). Nothing extra is fetched.
export function feedPulse(posts, now = Date.now() / 1000) {
  const hour = (posts || []).filter(p => now - Number(p.at) < 3600);
  const buckets = Array.from({ length: 12 }, (_, i) => hour.filter(p => Math.min(11, Math.floor((now - Number(p.at)) / 300)) === 11 - i).length);
  const bySrc = {}; const coins = {};
  hour.forEach(p => { bySrc[p.src] = (bySrc[p.src] || 0) + 1; const c = p.coin?.symbol; if (c) { const k = c.toUpperCase(); coins[k] = coins[k] || { sym: c, mint: p.coin.mint, n: 0 }; coins[k].n += 1; } });
  return { n: hour.length, buckets, bySrc: Object.entries(bySrc).sort((a, b) => b[1] - a[1]), top: Object.values(coins).sort((a, b) => b.n - a.n).slice(0, 5), calls: hour.filter(p => p.coin).length };
}
function FeedPulse({ d }) {
  const pu = feedPulse(d?.posts);
  const max = Math.max(1, ...pu.buckets); const pts = pu.buckets.map((v, i) => `${(i / 11) * 200},${36 - (v / max) * 30}`).join(' ');
  const tot = Math.max(1, pu.n);
  return <div className="fd-card fxp" data-testid="feed-pulse">
    <span className="fxp-n" data-tip="Posts in the last hour across the sites you picked"><b key={pu.n}>{pu.n}</b><em>POSTS / HR</em></span>
    <span className="fxp-n is-calls" data-tip="Posts that named a coin this hour"><b key={pu.calls}>{pu.calls}</b><em>CALLS / HR</em></span>
    <svg className="fxp-line" viewBox="0 0 200 40" preserveAspectRatio="none" aria-label="posts per 5 minutes, last hour"><polyline points={`0,40 ${pts} 200,40`} className="area" /><polyline points={pts} className="ln" /></svg>
    <span className="fxp-src" aria-label="who is talking">{pu.bySrc.slice(0, 5).map(([k, n]) => <i key={k} className={`is-${k}`} style={{ flexGrow: n / tot }} data-tip={`${n} from ${SRC_BADGE[k] || k}`}>{(SRC_BADGE[k] || k).split(' ')[0]} {n}</i>)}</span>
    <span className="fxp-top" data-tip="The coins called most this hour — tap to open">{pu.top.length ? pu.top.map(c => <button key={c.sym} type="button" onClick={() => c.mint && openCoin({ chainId: 'solana', baseToken: { address: c.mint, symbol: c.sym } })}>${c.sym}<b>{c.n}</b></button>) : <small>no calls yet this hour</small>}</span>
  </div>;
}
// ⤢ FEEd POPPED OUT: a floating, draggable window that stays over any page (TerminalShell mounts the host once)
export const openFeedPop = () => window.dispatchEvent(new Event('feeless:feed-pop'));
export function FeedPopHost() {
  const [open, setOpen] = useState(false); const [xy, setXy] = useState([0, 0]); const drag = useRef(null);
  const { wallet } = useWallet() || {}; const me = wallet?.address || ''; const sess = me ? readChatSession(me) : '';
  const [tab, setTab] = useFeedTab(); const marks = useMarks();
  useEffect(() => { const f = () => setOpen(true); window.addEventListener('feeless:feed-pop', f); return () => window.removeEventListener('feeless:feed-pop', f); }, []);
  const d = useSocialFeed('', open);
  if (!open) return null;
  const down = e => { drag.current = { x: e.clientX - xy[0], y: e.clientY - xy[1] }; e.currentTarget.setPointerCapture(e.pointerId); };
  const move = e => { if (drag.current) setXy([e.clientX - drag.current.x, e.clientY - drag.current.y]); };
  return <aside className="fxpop" style={{ transform: `translate(${xy[0]}px, ${xy[1]}px)` }} data-testid="feed-pop" role="dialog" aria-label="FEEd">
    <header onPointerDown={down} onPointerMove={move} onPointerUp={() => { drag.current = null; }} data-tip="Drag to move"><b className="feed-wordmark">FEEd</b><small><i className="fd-live" />live · every site</small>
      <button type="button" className="m-btn" onClick={() => setOpen(false)} aria-label="Close FEEd" data-tip="Close">✕</button></header>
    <FeedTabs tab={tab} setTab={setTab} follows={marks.follows} saved={marks.saved} />
    <div className="fxpop-body"><Timeline d={d} tab={tab} q="" me={me} sess={sess} marks={marks} /></div>
  </aside>;
}

// 📱 phone: the header folds away while you scroll down and comes back on the way up (transform only, one passive listener)
function useFoldOnScroll() {
  const [hid, setHid] = useState(false);
  useEffect(() => { let last = window.scrollY; let raf = 0;
    const on = () => { if (raf) return; raf = requestAnimationFrame(() => { raf = 0; const y = window.scrollY; if (Math.abs(y - last) > 8) { setHid(y > last && y > 160); last = y; } }); };
    window.addEventListener('scroll', on, { passive: true }); return () => { window.removeEventListener('scroll', on); if (raf) cancelAnimationFrame(raf); }; }, []);
  return hid;
}

export function FeedPanel({ onConnect }) {
  const { wallet } = useWallet() || {}; const me = wallet?.address || ''; const sess = me ? readChatSession(me) : '';
  const [srcs, setSrcs] = useState(readSrc);
  const [cat, setCat] = useState(() => { try { return localStorage.getItem('feeless:feed-cat') || 'feed-general'; } catch { return 'feed-general'; } });
  const pickSrc = k => setSrcs(cur => { const n = toggleSrc(cur, k); try { localStorage.setItem(SRC_KEY, JSON.stringify(n)); } catch { /* private window */ } return n; });
  const pickCat = v => { setCat(v); try { localStorage.setItem('feeless:feed-cat', v); } catch { /* private */ } };
  const rooms = srcs.length === 1 && srcs[0] === 'feeless';
  const qs = useMemo(() => (srcs.includes('all') ? '' : srcs.join(',')), [srcs]);
  const current = FEED_CATS.find(c => c[0] === cat) || FEED_CATS[0];
  const [look, setLook0] = useState(readLook); const [lookOpen, setLookOpen] = useState(false);
  const setLook = v => setLook0(saveLook(v));
  const lv = lookVars(look);
  const [tab, setTab] = useFeedTab(); const marks = useMarks();
  const [q, setQ] = useState(''); const [sheet, setSheet] = useState(false);
  const d = useSocialFeed(qs, !rooms);
  const hid = useFoldOnScroll();
  const n1h = feedPulse(d?.posts).n;
  const toTop = () => window.scrollTo?.({ top: 0, behavior: 'smooth' });
  return <section className={`fd ${lv.cls}${hid ? ' is-folded' : ''}`} style={lv.style} data-testid="profile-feed">
    <nav className="fd-mini" aria-label="FEEd">
      <b className="feed-wordmark">FEEd</b>
      {[['🏠', 'Home', () => { pickSrc('all'); toTop(); }, 'Every site, mixed'], ['⚡', 'Rooms', () => { if (!rooms) setSrcs(() => { try { localStorage.setItem(SRC_KEY, '["feeless"]'); } catch { /* private */ } return ['feeless']; }); }, 'FEELESS live rooms'],
        ['🎨', 'Look', () => setLookOpen(o => !o), 'Background, font, size, accent'], ['⤢', 'Pop out', openFeedPop, 'Float FEEd over any page']].map(([ic, l, fn, tip]) => <button key={l} type="button" className="fd-mini-btn" onClick={fn} data-tip={tip}><i>{ic}</i><span>{l}</span></button>)}
      <button type="button" className="m-btn m-go fd-mini-post" onClick={() => setSheet(true)} data-tip="Write a post">✎ Post</button>
    </nav>
    <div className="fd-col">
      <header className="fd-top">
        <span className="fd-sky" aria-hidden="true"><i /><i /><i /></span>
        <div className="fd-head"><b className="feed-wordmark">FEEd</b>
          <span className="fd-head-t"><b>{rooms ? '⚡ FEELESS rooms' : srcs.includes('all') ? 'Everything' : srcs.map(k => (FEED_SRC.find(s => s[0] === k) || [])[2]).join(' + ')}</b>
            <small><i className="fd-live" />{rooms ? current[3] : `LIVE · ${n1h} post${n1h === 1 ? "" : "s"} / hr`}</small></span>
          <button type="button" className={`fd-iconbtn ${lookOpen ? 'on' : ''}`} aria-expanded={lookOpen} onClick={() => setLookOpen(o => !o)} data-testid="feed-look-open" data-tip="Make FEEd yours: background, font, size, accent">🎨</button>
          <button type="button" className="fd-iconbtn" onClick={openFeedPop} data-tip="Pop FEEd out into a floating window that stays over any page" data-testid="feed-popout">⤢</button></div>
        {rooms ? null : <FeedTabs tab={tab} setTab={setTab} follows={marks.follows} saved={marks.saved} />}
        <div className="fd-chips" role="group" aria-label="FEEd sites">{FEED_SRC.map(([k, ic, label]) => { const on = srcs.includes(k); return <button key={k} type="button" className={`fd-chip is-${k} ${on ? 'on' : ''}`} aria-pressed={on} onClick={() => pickSrc(k)} data-testid={`feed-src-${k}`}
          data-tip={k === 'all' ? 'Every site mixed' : k === 'feeless' ? 'FEELESS alone = our live rooms (post, call, earn)' : `Mix ${label} in or out`}><i>{ic}</i>{label}</button>; })}
          {POST_ONLY.map(([k, ic, label]) => <span key={k} className="fd-chip is-post" tabIndex={0} data-tip={`${label} doesn't let a site read its feed without its own paid API app. Post to it from the composer — it opens ${label}'s own post page on your account.`}><i>{ic}</i>{label}<small>post only</small></span>)}</div>
      </header>
      {lookOpen ? <LookPanel look={look} set={setLook} onClose={() => setLookOpen(false)} /> : null}
      {rooms ? <div className="fd-rooms">
        <FeedCallers />
        <nav className="feed-cats" aria-label="FEEd categories">{FEED_CATS.map(([id, icon, label]) => <button type="button" key={id} className={cat === id ? 'on' : ''} aria-pressed={cat === id} onClick={() => pickCat(id)}><span>{icon}</span>{label}</button>)}</nav>
        <EcosystemChat key={cat} compact room={cat} ecosystem={{ id: cat, name: current[2] }} onConnect={onConnect} />
      </div> : <>
        <Composer me={me} sess={sess} />
        <details className="fd-xwrap"><summary data-tip="Bring an X post into FEEd">𝕏 Bring in an X post</summary><XShare me={me} sess={sess} /></details>
        <Timeline d={d} tab={tab} q={q} me={me} sess={sess} marks={marks} />
      </>}
    </div>
    <aside className="fd-rail">
      <label className="fd-search"><i aria-hidden="true">⌕</i><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder="Search posts, @people, $coins" aria-label="Search FEEd" data-testid="feed-search" />{q ? <button type="button" onClick={() => setQ('')} aria-label="Clear search" data-tip="Clear">✕</button> : null}</label>
      {rooms ? null : <FeedPulse d={d} />}
      <FeedTopCoins />
      {rooms ? null : <FeedCallers />}
      {rooms ? null : <WhoToFollow posts={d?.posts} marks={marks} />}
      <MySites look={look} set={setLook} />
    </aside>
    {rooms ? null : <button type="button" className="fd-fab" onClick={() => setSheet(true)} aria-label="Write a post" data-testid="feed-fab" data-tip="Write a post">✎</button>}
    {sheet ? createPortal(<div className="fd-sheet" role="dialog" aria-label="New post" onClick={e => { if (e.target === e.currentTarget) setSheet(false); }}>
      <div className="fd-sheet-card"><header><b>New post</b><button type="button" className="m-btn" onClick={() => setSheet(false)} aria-label="Close" data-tip="Close">✕</button></header>
        <Composer me={me} sess={sess} sheet onPosted={() => setSheet(false)} /></div></div>, document.body) : null}
  </section>;
}

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { readChatSession } from '../../lib/chatSession';
import { Link, useNavigate } from 'react-router-dom';
import EcosystemChat from '../EcosystemChat';
import { Explain } from '../Explain';
import { openCoin } from '../CoinDrawer';
import { apiUrl } from '../../lib/api';
import { sharedJson } from '../../lib/sharedJson';
import { useMarket } from '../../hooks/useMarket';
import { SHARE_TO, shareLinks } from '../../lib/socialShare';
import { FEED_BGS, FEED_FONTS, FEED_SIZES, FEED_ACCENTS, FEED_DENSITY, HANDLE_SITES, readLook, saveLook, lookVars, handleUrl } from '../../lib/feedLook';
import '../../styles/feed.css';

// 📰 FEEd = an X-style timeline (owner, 2026-10-18: "wider, an X UI / layout — click site bubbles to see different feeds or mixed from the
// sites"). Left: the site bubbles (tap to mix any of them; FEELESS alone = our live rooms with posting). Middle: the timeline — a cross-post
// box on top (opens X / Reddit / Bluesky / Telegram / Farcaster's own compose page, the user's own login posts it), then every post newest
// first. Right: top coins + what each outside site allows. Reading = /api/reputation/social-feed (one shared read, every 30s while visible).
export const FEED_SRC = [['all', '✨', 'All'], ['feeless', '⚡', 'FEELESS'], ['x', '𝕏', 'X'], ['pump', '💊', 'Pump'], ['telegram', '✈', 'Telegram'], ['bluesky', '🦋', 'Bluesky']];
const POST_ONLY = [['reddit', '👽', 'Reddit']];
export const FEED_CATS = [['feed-general', '🌐', 'Everything', 'All the talk'], ['feed-alpha', '📈', 'Alpha & calls', 'Post a CA — 2×/5×/10× earns points'], ['feed-memes', '😂', 'Memes', 'Culture & coins'], ['feed-launches', '🚀', 'Launches', 'New coins, first looks'], ['feed-help', '🛟', 'Help', 'Ask anything'], ['feeless-updates', '📣', 'FEELESS', 'Official updates']];
const SRC_BADGE = { feeless: '⚡ FEELESS', x: '𝕏 X', pump: '💊 Pump', telegram: '✈ Telegram', bluesky: '🦋 Bluesky' };
const SRC_KEY = 'feeless.feedSrc';
const PAGE = 30;

const readSrc = () => { try { const v = JSON.parse(localStorage.getItem(SRC_KEY) || '["all"]'); return Array.isArray(v) && v.length ? v : ['all']; } catch { return ['all']; } };
/** a bubble tap: All clears the rest; any site toggles in / out of the mix (never empty → All) */
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
  return <div className="fx-share" role="group" aria-label={label}>{SHARE_TO.map(([k, ic, name]) =>
    <a key={k} className={`fx-sh is-${k} ${off ? 'is-off' : ''}`} href={off ? undefined : links[k]} target="_blank" rel="noopener noreferrer" aria-disabled={off} data-testid={`feed-share-${k}`}
      data-tip={`Opens ${name}'s own post box with this filled in — you press Post there, on your own account. FEELESS never holds your login.`}><b>{ic}</b><span>{name}</span></a>)}</div>;
}

const signIn = () => { toast.error('Connect your wallet and open chat once to sign in (one signature, 7 days).'); };
const reactPost = (body) => fetch(apiUrl('/api/reputation/social-feed/react'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Could not post'); return x; });
// pure: the "↑ N new posts" pill — posts newer than the newest one already on screen (X never jumps the timeline under you)
export const newSince = (posts, seenAt) => (posts || []).filter(p => Number(p.at) > Number(seenAt || 0)).length;
// pure: compact counts like X (1.2K)
export const kWord = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n || 0));

function Composer({ me, sess, onPosted }) {
  const [t, setT] = useState(''); const [busy, setBusy] = useState(false); const ta = useRef(null);
  useEffect(() => { const q = e => { setT(String(e.detail || '').slice(0, 270) + '\n'); ta.current?.focus(); ta.current?.scrollIntoView?.({ block: 'center', behavior: 'smooth' }); };
    window.addEventListener('feeless:feed-quote', q); return () => window.removeEventListener('feeless:feed-quote', q); }, []);
  const post = async () => {   // ⚡ straight onto FEELESS (the Everything room) — the same signed chat path every room uses
    if (!me || !sess) { signIn(); return; }
    setBusy(true);
    try { const r = await fetch(apiUrl('/api/reputation/chat'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room: 'feed-general', address: me, text: t.trim(), ts: Math.floor(Date.now() / 1000), session: sess }) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Could not post'); setT(''); toast.success('⚡ posted on FEELESS'); onPosted?.(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <div className="fx-compose" data-testid="feed-compose">
    <textarea ref={ta} value={t} maxLength={270} onChange={e => setT(e.target.value)} placeholder="What's cooking in the trenches? Post it on FEELESS — or everywhere." rows={2} />
    <div className="fx-compose-foot"><small className={t.length > 250 ? 'is-hot' : ''}>{270 - t.length}</small>
      <button type="button" className="m-btn m-go fx-postbtn" disabled={!t.trim() || busy} onClick={post} data-testid="feed-post-feeless">{busy ? '…' : '⚡ Post'}</button>
      <ShareRow text={t} label="also to" /></div>
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
  return <form className="fx-xshare" onSubmit={e => { e.preventDefault(); go(); }} data-testid="feed-xshare">
    <i aria-hidden="true">𝕏</i>
    <input className="m-input" value={u} onChange={e => setU(e.target.value)} onPaste={e => { const t = e.clipboardData.getData('text'); if (isXPost(t)) { e.preventDefault(); setU(t); go(t); } }}
      placeholder="Paste an X post link to bring it into FEEd" aria-label="X post link" spellCheck={false} />
    <button type="submit" className="m-btn" disabled={busy || !u.trim()} data-testid="feed-xshare-go">{busy ? '…' : 'Bring it in'}</button>
  </form>;
}

// /dev/null-style FEEd (owner, 2026-10-20, their screenshot of dev-null.sh: "FEEd needs to be like this but bigger and better"): a short hash per
// post, ringed avatars, ⭐ star · ❝ quote · ↩ reply · 🔖 save · 🔗 link, replies shown INLINE on a dotted thread line ("Show the last N"),
// tabs Latest · Trending · Following · Saved. Follows + saves live in this browser; stars + replies are the server's (feed_social).
export const hashOf = id => { let h = 2166136261; for (const ch of String(id || '')) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16).padStart(8, '0').slice(0, 7); };
export const TABS = [['latest', 'Latest'], ['trending', 'Trending'], ['following', 'Following'], ['saved', '🔖 Saved']];
const readSet = k => { try { return new Set(JSON.parse(localStorage.getItem(k) || '[]')); } catch { return new Set(); } };
const writeSet = (k, set) => { try { localStorage.setItem(k, JSON.stringify([...set].slice(-500))); } catch { /* private window */ } };
export const authorKey = p => `${p.src}:${String(p.handle || p.author || '').toLowerCase()}`;
// pure: what a tab shows — trending = stars + 2 × replies, fresher first on ties, last 24h
export function tabPosts(posts, tab, counts, follows, saved, now = Date.now() / 1000) {
  const all = posts || [];
  if (tab === 'following') return all.filter(p => follows.has(authorKey(p)));
  if (tab === 'saved') return all.filter(p => saved.has(p.id));
  if (tab === 'trending') return all.filter(p => now - Number(p.at) < 86400).map(p => [p, (counts[p.id]?.likes || 0) + 2 * (counts[p.id]?.comments || 0)])
    .sort((a, b) => b[1] - a[1] || Number(b[0].at) - Number(a[0].at)).map(x => x[0]);
  return all;
}
const SHOW = 3;

function Ava({ src, name, kind }) {
  return src ? <img className={`fx-ava ring-${kind}`} src={src} alt="" loading="lazy" decoding="async" /> : <i className={`fx-ava fx-ini ring-${kind}`}>{String(name || '?').slice(0, 1).toUpperCase()}</i>;
}

function Thread({ p, me, sess, onCount, auto }) {
  const [list, setList] = useState(null); const [t, setT] = useState(''); const [busy, setBusy] = useState(false); const [all, setAll] = useState(false); const [box, setBox] = useState(!auto);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/social-feed/thread/${encodeURIComponent(p.id)}`)).then(r => r.json()).then(x => { if (on) setList(x.comments || []); }).catch(() => setList([])); return () => { on = false; }; }, [p.id]);
  const send = async () => { if (!me || !sess) { signIn(); return; } setBusy(true);
    try { const r = await reactPost({ address: me, session: sess, id: p.id, comment: t }); setList(l => [...(l || []), r.comment]); setT(''); onCount(r); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  const shown = list && !all && list.length > SHOW ? list.slice(0, SHOW) : list;
  return <div className="fx-thread" data-testid="feed-thread">
    {list == null ? <small className="fx-dim">reading replies…</small> : !list.length ? (box ? <small className="fx-dim">No replies yet — be first.</small> : null)
      : <ol>{shown.map((c, i) => <li key={`${c.at}-${i}`} style={{ '--i': i }}><Ava name={c.name} kind="reply" /><div><header><b>{c.name || 'anon'}</b><small>· {agoWord(c.at)}</small></header><p>{c.text}</p></div></li>)}
        {list.length > SHOW && !all ? <li className="fx-showmore"><button type="button" onClick={() => setAll(true)} data-testid="feed-show-rest">◎ Show the last {list.length - SHOW}</button></li> : null}</ol>}
    {box ? <form onSubmit={e => { e.preventDefault(); if (t.trim()) send(); }}><input className="m-input" value={t} maxLength={280} placeholder="Post your reply" onChange={e => setT(e.target.value)} aria-label="Reply" autoFocus={!auto} /><button type="submit" className="m-btn" disabled={!t.trim() || busy}>Reply</button></form>
      : <button type="button" className="fx-replyhere" onClick={() => setBox(true)}>↩ Reply</button>}
  </div>;
}

function Post({ p, c, me, sess, onCount, follows, saved, toggle }) {
  const [share, setShare] = useState(false); const [open, setOpen] = useState(false); const [pop, setPop] = useState(false);
  const like = async () => { if (!me || !sess) { signIn(); return; } setPop(true); setTimeout(() => setPop(false), 420);
    try { onCount(await reactPost({ address: me, session: sess, id: p.id, like: true })); } catch (e) { toast.error(e.message); } };
  const quote = () => window.dispatchEvent(new CustomEvent('feeless:feed-quote', { detail: `❝ @${p.handle || p.author}: ${String(p.text || '').slice(0, 180)}` }));
  const link = () => { const u = p.url || `${window.location.origin}/terminal/profile?feed=${encodeURIComponent(p.id)}`; navigator.clipboard?.writeText(u).then(() => toast.success('🔗 link copied')).catch(() => {}); };
  const ak = authorKey(p); const fol = follows.has(ak); const sv = saved.has(p.id);
  const replies = c?.comments || 0;
  return <article className={`fx-post is-${p.src}${replies ? ' has-thread' : ''}`} data-testid="feed-post">
    <Ava src={p.avatar} name={p.author} kind={p.src} />
    <div className="fx-body">
      <header><b>{p.author}</b>{p.handle && p.handle !== p.author ? <small className="fx-handle">@{p.handle}</small> : null}<small>· {agoWord(p.at)}</small>
        <button type="button" className={`fx-follow ${fol ? 'is-on' : ''}`} onClick={() => toggle('follow', ak)} aria-pressed={fol} data-testid="feed-follow">{fol ? '✓ following' : '+ follow'}</button>
        <em className={`fx-src is-${p.src}`}>{SRC_BADGE[p.src] || p.src}</em><code className="fx-hash" data-tip="this post's id">{hashOf(p.id)}</code></header>
      <p>{p.text}</p>
      {p.sharedBy ? <small className="fx-shared">𝕏 brought in by {p.sharedBy}{p.url ? <> · <a href={p.url} target="_blank" rel="noopener noreferrer nofollow">open on X</a></> : null}</small> : null}
      {p.img ? <img className="fx-img" src={p.img} alt="" loading="lazy" decoding="async" /> : null}
      <footer className="fx-bar">
        <button type="button" className={`fx-act fx-like ${c?.mine ? 'is-liked' : ''} ${pop ? 'is-pop' : ''}`} aria-pressed={!!c?.mine} onClick={like} data-testid="feed-like"><i>{c?.mine ? '★' : '☆'}</i>{c?.likes ? kWord(c.likes) : ''}</button>
        <button type="button" className="fx-act" onClick={quote} data-testid="feed-quote"><i>❝</i>Quote</button>
        <button type="button" className={`fx-act ${open ? 'is-on' : ''}`} aria-expanded={open} onClick={() => setOpen(o => !o)} data-testid="feed-reply"><i>↩</i>Reply{replies ? ` ${kWord(replies)}` : ''}</button>
        {p.coin?.mint ? <button type="button" className="fx-act fx-coin" onClick={() => openCoin({ mint: p.coin.mint, symbol: p.coin.symbol })}>🪙 ${p.coin.symbol}</button> : null}
        <span className="fx-right">
          <button type="button" className={`fx-act ${share ? 'is-on' : ''}`} aria-expanded={share} onClick={() => setShare(s => !s)} aria-label="Share"><i>🔁</i></button>
          <button type="button" className={`fx-act ${sv ? 'is-on' : ''}`} aria-pressed={sv} onClick={() => toggle('save', p.id)} aria-label="Save" data-testid="feed-save"><i>{sv ? '🔖' : '🏷'}</i></button>
          <button type="button" className="fx-act" onClick={link} aria-label="Copy link"><i>🔗</i></button></span>
      </footer>
      {share ? <ShareRow text={p.text} url={p.url} /> : null}
      {open || replies ? <Thread p={p} me={me} sess={sess} onCount={onCount} auto={!open} key={open ? 'open' : 'auto'} /> : null}
    </div>
  </article>;
}

function Timeline({ src, me, sess }) {
  const d = useSocialFeed(src, true);
  const [n, setN] = useState(PAGE); const [seen, setSeen] = useState(0); const [cnt, setCnt] = useState({}); const top = useRef(null);
  const [tab, setTab0] = useState(() => { try { return localStorage.getItem('feeless.feedTab') || 'latest'; } catch { return 'latest'; } });
  const setTab = t => { setTab0(t); try { localStorage.setItem('feeless.feedTab', t); } catch { /* private */ } };
  const [follows, setFollows] = useState(() => readSet('feeless.feedFollow')); const [saved, setSaved] = useState(() => readSet('feeless.feedSaved'));
  const toggle = (kind, k) => { const [cur, set, key] = kind === 'follow' ? [follows, setFollows, 'feeless.feedFollow'] : [saved, setSaved, 'feeless.feedSaved'];
    const nx = new Set(cur); if (nx.has(k)) nx.delete(k); else nx.add(k); writeSet(key, nx); set(nx); };
  const all = d?.posts || [];
  useEffect(() => { if (all.length && !seen) setSeen(Math.max(...all.map(p => Number(p.at) || 0))); }, [all, seen]);
  const base = seen ? all.filter(p => Number(p.at) <= seen) : all;   // newer posts wait behind the pill
  const posts = tabPosts(base, tab, cnt, follows, saved);
  const fresh = newSince(all, seen);
  const ids = base.slice(0, Math.max(n, 60)).map(p => p.id).join(',');
  useEffect(() => { if (!ids) return undefined; let on = true;   // ONE batched counts read per refresh
    fetch(apiUrl(`/api/reputation/social-feed/counts?ids=${encodeURIComponent(ids)}${me ? `&address=${me}` : ''}`)).then(r => r.json()).then(x => { if (on) setCnt(c => ({ ...c, ...(x.counts || {}) })); }).catch(() => {});
    return () => { on = false; }; }, [ids, me, d?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const setOne = id => r => setCnt(c => ({ ...c, [id]: { likes: r.likes, comments: r.comments, mine: r.mine } }));
  const empty = { following: 'Follow people with “+ follow” on any post — their posts land here.', saved: 'Tap 🏷 on any post to save it here.', trending: 'Nothing starred in the last 24h yet.' }[tab];
  return <div className="fx-timeline" data-testid="feed-timeline" ref={top}>
    <nav className="fx-tabs" role="tablist" aria-label="Timeline">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)} data-testid={`feed-tab-${k}`}>{l}{k === 'following' && follows.size ? <i>{follows.size}</i> : k === 'saved' && saved.size ? <i>{saved.size}</i> : null}</button>)}</nav>
    {fresh && tab === 'latest' ? <button type="button" className="fx-newpill" onClick={() => { setSeen(Math.max(...all.map(p => Number(p.at) || 0))); top.current?.scrollIntoView({ block: 'start', behavior: 'smooth' }); }} data-testid="feed-new">↑ {fresh} new post{fresh > 1 ? 's' : ''}</button> : null}
    {!d ? <p className="fx-empty">Loading the feeds…</p> : !posts.length ? <p className="fx-empty">{empty || 'Nothing new on these sites yet.'}</p> : posts.slice(0, n).map(p => <Post key={p.id} p={p} c={cnt[p.id]} me={me} sess={sess} follows={follows} saved={saved} toggle={toggle} onCount={r => setOne(p.id)({ ...(cnt[p.id] || {}), ...r, ...(r[p.id] || {}) })} />)}
    {posts.length > n ? <button type="button" className="fx-more" onClick={() => setN(x => x + PAGE)}>Show {Math.min(PAGE, posts.length - n)} more</button> : null}
  </div>;
}

// Best FEEd callers this week: posts with a coin are tracked; 2×/5×/10× peaks earn season points.
function FeedCallers() {
  const [rows, setRows] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/calls/leaderboard?days=7&room=feed-')).then(r => (r.ok ? r.json() : {})).then(d => setRows(d.rows || [])).catch(() => setRows([])); }, []);
  if (!rows?.length) return <p className="feed-callers-empty">Post a coin address in FEEd — if it runs 2×, 5× or 10× you earn season points.</p>;
  return <ol className="feed-callers" aria-label="Top FEEd callers this week"><li className="fc-head">Top callers this week <Explain>Post a coin address in any FEEd room and it becomes a tracked call. If it later peaks at 2×, 5× or 10× from your post, you earn 50, 150 or 400 season points automatically.</Explain></li>{rows.slice(0, 5).map((r, i) => <li key={r.caller}>
    <i>{i + 1}</i>{r.callerAddress ? <Link to={`/terminal/profile/${r.callerAddress}`}>{r.caller}</Link> : <b>{r.caller}</b>}
    <span>{r.hits}/{r.calls} hits</span>{r.best && <em>best {r.best.symbol} {r.best.peakX.toFixed(1)}×</em>}
  </li>)}</ol>;
}

// Hot coins beside the FEEd: one click opens the Trenches chart.
function FeedTopCoins() {
  const navigate = useNavigate();
  const { data } = useMarket('/feed?kind=trending&chain=solana', 60000);
  const pairs = (data?.pairs || []).filter(p => p.baseToken?.symbol).slice(0, 8);
  return <div className="feed-side feed-top" data-testid="feed-top-coins"><h4>🔥 Top coins</h4>
    {!pairs.length ? <p className="wp-bio">Loading…</p> : pairs.map(p => { const ch = Number(p.priceChange?.h24); return <button type="button" key={p.pairAddress} onClick={() => navigate(`/terminal/chat?chain=${p.chainId}&pair=${p.pairAddress}&room=bulls`)}>
      {p.info?.imageUrl ? <img src={p.info.imageUrl} alt="" /> : <span className="ft-dot" />}<b>${p.baseToken.symbol}</b><em className={ch >= 0 ? 'positive' : 'negative'}>{Number.isFinite(ch) ? `${ch >= 0 ? '+' : ''}${ch.toFixed(1)}%` : '—'}</em></button>; })}
  </div>;
}


function Seg({ label, list, val, onPick, show = x => x[1] }) {
  return <div className="fx-lrow"><small>{label}</small><span className="m-seg" role="radiogroup" aria-label={label}>{list.map(x => <button key={x[0]} type="button" role="radio" aria-checked={val === x[0]} className={val === x[0] ? 'active' : ''} onClick={() => onPick(x[0])} data-testid={`feed-look-${label.toLowerCase()}-${x[0]}`}>{show(x)}</button>)}</span></div>;
}
/** 🎨 the FEEd look: background · font · text size · accent · density — remembered in this browser */
function LookPanel({ look, set, onClose }) {
  const up = k => v => set({ ...look, [k]: v });
  return <div className="fx-look" role="dialog" aria-label="FEEd look" data-testid="feed-look">
    <header><b>🎨 Make FEEd yours</b><button type="button" className="m-btn" onClick={onClose} aria-label="Close">✕</button></header>
    <Seg label="Background" list={FEED_BGS} val={look.bg} onPick={up('bg')} />
    <Seg label="Font" list={FEED_FONTS} val={look.font} onPick={up('font')} show={x => <span style={{ fontFamily: x[2] }}>{x[1]}</span>} />
    <Seg label="Text" list={FEED_SIZES} val={look.size} onPick={up('size')} />
    <Seg label="Accent" list={FEED_ACCENTS} val={look.accent} onPick={up('accent')} show={x => <i className="fx-dot" style={{ background: x[1] }} aria-label={x[0]} />} />
    <Seg label="Density" list={FEED_DENSITY} val={look.density} onPick={up('density')} />
  </div>;
}
/** 🔗 your own public handles (never a password / token): one-tap to your profile and to post there as you */
function MySites({ look, set }) {
  const [edit, setEdit] = useState(false);
  const h = look.handles || {};
  return <div className="feed-side fx-acc fx-sites" data-testid="feed-sites"><h4>🔗 Your sites <button type="button" className="m-btn" onClick={() => setEdit(e => !e)} data-testid="feed-sites-edit">{edit ? 'Done' : 'Connect'}</button></h4>
    {edit ? HANDLE_SITES.map(([k, ic]) => <label key={k} className="fx-hrow"><i>{ic}</i><input className="m-input" defaultValue={h[k] || ''} placeholder={k === 'x' ? '@yourhandle' : 'your name there'} maxLength={40}
      onBlur={e => set({ ...look, handles: { ...h, [k]: e.target.value } })} data-testid={`feed-handle-${k}`} /></label>)
      : HANDLE_SITES.some(([k]) => h[k]) ? <ul className="fx-hlist">{HANDLE_SITES.filter(([k]) => h[k]).map(([k, ic]) => <li key={k}><a href={handleUrl(k, h[k])} target="_blank" rel="noopener noreferrer">{ic} @{h[k]}</a></li>)}</ul>
      : <p>Add your X / Reddit / Bluesky / Telegram name — one tap to your profile, and the post box posts there as you.</p>}
    <p className="fx-dim">Your login stays on each site: FEELESS never asks for your password. Reading your private X / Reddit timeline needs their API apps.</p>
  </div>;
}

export function FeedPanel({ onConnect }) {
  const { wallet } = useWallet() || {}; const me = wallet?.address || ''; const sess = me ? readChatSession(me) : '';
  const [srcs, setSrcs] = useState(readSrc);
  const [cat, setCat] = useState(() => { try { return localStorage.getItem('feeless:feed-cat') || 'feed-general'; } catch { return 'feed-general'; } });
  const pickSrc = k => setSrcs(cur => { const n = toggleSrc(cur, k); try { localStorage.setItem(SRC_KEY, JSON.stringify(n)); } catch { /* private window */ } return n; });
  const pickCat = v => { setCat(v); try { localStorage.setItem('feeless:feed-cat', v); } catch { /* private */ } };
  const rooms = srcs.length === 1 && srcs[0] === 'feeless';
  const q = useMemo(() => (srcs.includes('all') ? '' : srcs.join(',')), [srcs]);
  const current = FEED_CATS.find(c => c[0] === cat) || FEED_CATS[0];
  const [look, setLook0] = useState(readLook); const [lookOpen, setLookOpen] = useState(false);
  const setLook = v => setLook0(saveLook(v));
  const lv = lookVars(look);
  return <section className={`fx ${lv.cls}`} style={lv.style} data-testid="profile-feed">
    <nav className="fx-nav" aria-label="FEEd sites">
      <b className="feed-wordmark">FEEd</b>
      {FEED_SRC.map(([k, ic, label]) => { const on = srcs.includes(k); return <button key={k} type="button" className={`fx-bub ${on ? 'on' : ''}`} aria-pressed={on} onClick={() => pickSrc(k)} data-testid={`feed-src-${k}`}><i>{ic}</i><span>{label}</span></button>; })}
      <small className="fx-navnote">Post only</small>
      <button type="button" className={`fx-bub fx-lookbtn ${lookOpen ? 'on' : ''}`} aria-expanded={lookOpen} onClick={() => setLookOpen(o => !o)} data-testid="feed-look-open"><i>🎨</i><span>Look</span></button>
      {POST_ONLY.map(([k, ic, label]) => <span key={k} className="fx-bub is-post" data-tip={`${label} doesn't let a site read its feed without its own paid / registered API app. Post to it from the box on top — it opens ${label}'s own post page on your account.`}><i>{ic}</i><span>{label}</span></span>)}
    </nav>
    <div className="fx-main">
      <span className="feed-flares" aria-hidden="true"><i /><i /><i /></span>
      {lookOpen ? <LookPanel look={look} set={setLook} onClose={() => setLookOpen(false)} /> : null}
      {rooms ? <>
        <header className="fx-head"><b>⚡ FEELESS rooms</b><small>{current[3]}</small></header>
        <FeedCallers />
        <nav className="feed-cats" aria-label="FEEd categories">{FEED_CATS.map(([id, icon, label]) => <button type="button" key={id} className={cat === id ? 'on' : ''} aria-pressed={cat === id} onClick={() => pickCat(id)}><span>{icon}</span>{label}</button>)}</nav>
        <EcosystemChat key={cat} compact room={cat} ecosystem={{ id: cat, name: current[2] }} onConnect={onConnect} />
      </> : <>
        <header className="fx-head"><b>{srcs.includes('all') ? '✨ Everything' : srcs.map(k => (FEED_SRC.find(s => s[0] === k) || [])[2]).join(' + ')}</b><small>FEELESS · X · Pump · Telegram · Bluesky, newest first</small></header>
        <Composer me={me} sess={sess} />
        <XShare me={me} sess={sess} />
        <Timeline src={q} me={me} sess={sess} />
      </>}
    </div>
    <aside className="fx-side">
      <FeedTopCoins />
      <MySites look={look} set={setLook} />
    </aside>
  </section>;
}

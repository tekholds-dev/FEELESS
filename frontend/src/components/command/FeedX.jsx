import React, { useEffect, useMemo, useState } from 'react';
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
export const FEED_SRC = [['all', '✨', 'All'], ['feeless', '⚡', 'FEELESS'], ['pump', '💊', 'Pump'], ['telegram', '✈', 'Telegram'], ['bluesky', '🦋', 'Bluesky']];
const POST_ONLY = [['x', '𝕏', 'X'], ['reddit', '👽', 'Reddit']];
export const FEED_CATS = [['feed-general', '🌐', 'Everything', 'All the talk'], ['feed-alpha', '📈', 'Alpha & calls', 'Post a CA — 2×/5×/10× earns points'], ['feed-memes', '😂', 'Memes', 'Culture & coins'], ['feed-launches', '🚀', 'Launches', 'New coins, first looks'], ['feed-help', '🛟', 'Help', 'Ask anything'], ['feeless-updates', '📣', 'FEELESS', 'Official updates']];
const SRC_BADGE = { feeless: '⚡ FEELESS', pump: '💊 Pump', telegram: '✈ Telegram', bluesky: '🦋 Bluesky' };
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
    return () => { alive = false; clearInterval(id); };
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

function Composer() {
  const [t, setT] = useState('');
  return <div className="fx-compose" data-testid="feed-compose">
    <textarea value={t} maxLength={270} onChange={e => setT(e.target.value)} placeholder="What's cooking in the trenches? Write it once — post it everywhere." rows={2} />
    <div className="fx-compose-foot"><small>{270 - t.length}</small><ShareRow text={t} label="Cross-post" /></div>
  </div>;
}

function Post({ p }) {
  const [share, setShare] = useState(false);
  return <article className={`fx-post is-${p.src}`} data-testid="feed-post">
    {p.avatar ? <img className="fx-ava" src={p.avatar} alt="" loading="lazy" decoding="async" /> : <i className="fx-ava fx-ini">{String(p.author || '?').slice(0, 1).toUpperCase()}</i>}
    <div className="fx-body">
      <header><b>{p.author}</b>{p.handle && p.handle !== p.author ? <small>@{p.handle}</small> : null}<small>· {agoWord(p.at)}</small><em className={`fx-src is-${p.src}`}>{SRC_BADGE[p.src] || p.src}</em></header>
      <p>{p.text}</p>
      {p.img ? <img className="fx-img" src={p.img} alt="" loading="lazy" decoding="async" /> : null}
      <footer>
        {p.coin?.mint ? <button type="button" className="fx-act fx-coin" onClick={() => openCoin({ mint: p.coin.mint, symbol: p.coin.symbol })}>🪙 ${p.coin.symbol}</button> : null}
        {p.url ? <a className="fx-act" href={p.url} target="_blank" rel="noopener noreferrer">↗ open</a> : null}
        <button type="button" className={`fx-act ${share ? 'is-on' : ''}`} aria-expanded={share} onClick={() => setShare(s => !s)}>🔁 cross-post</button>
      </footer>
      {share ? <ShareRow text={p.text} url={p.url} /> : null}
    </div>
  </article>;
}

function Timeline({ src }) {
  const d = useSocialFeed(src, true);
  const [n, setN] = useState(PAGE);
  const posts = d?.posts || [];
  return <div className="fx-timeline" data-testid="feed-timeline">
    {!d ? <p className="fx-empty">Loading the feeds…</p> : !posts.length ? <p className="fx-empty">Nothing new on these sites yet.</p> : posts.slice(0, n).map(p => <Post key={p.id} p={p} />)}
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
        <header className="fx-head"><b>{srcs.includes('all') ? '✨ Everything' : srcs.map(k => (FEED_SRC.find(s => s[0] === k) || [])[2]).join(' + ')}</b><small>FEELESS · Pump · Telegram · Bluesky, newest first</small></header>
        <Composer />
        <Timeline src={q} />
      </>}
    </div>
    <aside className="fx-side">
      <FeedTopCoins />
      <MySites look={look} set={setLook} />
    </aside>
  </section>;
}

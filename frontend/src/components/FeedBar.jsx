import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';

const SRC = { feeless: '⚡', x: '𝕏', pump: '💊', telegram: '✈', bluesky: '🦋' };
const ago = sec => { const s = Math.max(0, Date.now() / 1000 - sec); return s < 60 ? `${Math.floor(s)}s` : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };

// The FEEd bar: live wordmark + the latest posts from EVERY site FEEd mixes (the same shared /social-feed read the FEEd page uses — it used to
// read only the FEELESS rooms and said "Be the first to post" while the timeline held 77 posts). Hover / ▾ to peek; click opens /terminal/feed.
export function FeedBar({ onOpen }) {
  const [posts, setPosts] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = () => sharedJson('/api/reputation/social-feed', { maxAge: 25000 }).then(d => alive && setPosts((d?.posts || []).slice().sort((a, b) => b.at - a.at).slice(0, 6))).catch(() => alive && setPosts(p => p || []));
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const latest = posts?.[0];
  return <div className={`feed-bar ${open ? 'is-open' : ''}`} data-testid="feed-bar" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button type="button" className="feed-bar-main" onClick={onOpen}>
      <span className="feed-bar-flare" aria-hidden="true" />
      <b className="feed-wordmark">FEEd</b>
      <span className="feed-bar-live"><i />{latest ? <><em>{SRC[latest.src] || '⚡'} @{latest.handle || latest.author}</em> {String(latest.text || '').slice(0, 70)}</> : posts ? 'Be the first to post — calls that run earn season points.' : 'Loading the FEEd…'}</span>
      <em className="feed-bar-go">Open →</em>
    </button>
    <button type="button" className="feed-bar-peek" aria-label={open ? 'Hide latest posts' : 'Show latest posts'} aria-expanded={open} onClick={() => setOpen(o => !o)}>{open ? '▴' : '▾'}</button>
    {open && posts?.length > 0 && <ul className="feed-bar-list">{posts.map(m => <li key={m.id}><button type="button" onClick={onOpen}><b>{SRC[m.src] || '⚡'} @{m.handle || m.author}</b><span>{String(m.text || '').slice(0, 120)}</span><small>{m.src} · {ago(m.at)}</small></button></li>)}</ul>}
  </div>;
}

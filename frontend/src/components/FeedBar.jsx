import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

const ROOMS = ['feed-general', 'feed-alpha', 'feed-launches', 'feed-memes'];
const ago = ms => { const s = Math.max(0, (Date.now() - ms) / 1000); return s < 60 ? `${Math.floor(s)}s` : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };

// The FEEd bar: live wordmark + latest posts ticker. Hover or tap the arrow to peek; click opens Activity → FEEd.
export function FeedBar({ onOpen }) {
  const [posts, setPosts] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = () => Promise.all(ROOMS.map(r => fetch(apiUrl(`/api/reputation/chat/${r}`)).then(x => (x.ok ? x.json() : {})).catch(() => ({}))))
      .then(rs => alive && setPosts(rs.flatMap(r => r.messages || []).filter(m => !m.parentId).sort((a, b) => b.ts - a.ts).slice(0, 6)));
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const latest = posts?.[0];
  return <div className={`feed-bar ${open ? 'is-open' : ''}`} data-testid="feed-bar" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button type="button" className="feed-bar-main" onClick={onOpen}>
      <span className="feed-bar-flare" aria-hidden="true" />
      <b className="feed-wordmark">FEEd</b>
      <span className="feed-bar-live"><i />{latest ? <><em>@{latest.username}</em> {latest.text.slice(0, 70)}</> : posts ? 'Be the first to post — calls that run earn season points.' : 'Loading the FEEd…'}</span>
      <em className="feed-bar-go">Open →</em>
    </button>
    <button type="button" className="feed-bar-peek" aria-label={open ? 'Hide latest posts' : 'Show latest posts'} aria-expanded={open} onClick={() => setOpen(o => !o)}>{open ? '▴' : '▾'}</button>
    {open && posts?.length > 0 && <ul className="feed-bar-list">{posts.map(m => <li key={m.id}><button type="button" onClick={onOpen}><b>@{m.username}</b><span>{m.text.slice(0, 120)}</span><small>{m.room.replace('feed-', '#')} · {ago(m.ts)}</small></button></li>)}</ul>}
  </div>;
}

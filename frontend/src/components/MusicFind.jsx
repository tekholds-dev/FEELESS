import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import '../styles/musicFind.css';

// 🔎 Find a song inside the mini player: YouTube search (+ Spotify when the owner set a Spotify key — those play through YouTube) and
// 🔥 Top played (Apple Music's most-played chart). Tap ▶ = play now · ＋ = add to the queue. Typing is debounced 300ms.
export const ytId = url => (String(url || '').match(/(?:v=|youtu\.be\/|shorts\/|embed\/)([\w-]{11})/) || [])[1] || null;

export default function MusicFind({ onAdd }) {
  const [q, setQ] = useState(''); const [lens, setLens] = useState('search');
  const [res, setRes] = useState(null); const [top, setTop] = useState(null); const [busy, setBusy] = useState(false);
  const seq = useRef(0);
  useEffect(() => {
    if (lens !== 'search' || q.trim().length < 2) { setRes(null); return undefined; }
    const my = ++seq.current; setBusy(true);
    const t = setTimeout(() => fetch(apiUrl(`/api/reputation/music/search?q=${encodeURIComponent(q.trim())}`)).then(r => r.json())
      .then(d => my === seq.current && setRes(d)).catch(() => my === seq.current && setRes({ youtube: [] })).finally(() => my === seq.current && setBusy(false)), 300);
    return () => clearTimeout(t);
  }, [q, lens]);
  useEffect(() => { if (lens !== 'top' || top) return; fetch(apiUrl('/api/reputation/music/top')).then(r => r.json()).then(setTop).catch(() => setTop({ rows: [] })); }, [lens, top]);
  // a chart / Spotify row has no YouTube link yet: find its first YouTube video, then add it
  const resolve = async (row, now) => {
    const d = await fetch(apiUrl(`/api/reputation/music/search?q=${encodeURIComponent(row.query)}`)).then(r => r.json()).catch(() => null);
    const v = d?.youtube?.[0]; if (v) onAdd({ url: v.url, title: `${row.artist} - ${row.title}` }, now);
  };
  const yt = res?.youtube || [];
  return <div className="mf" data-testid="music-find">
    <div className="mf-tabs" role="tablist" aria-label="Find music">{[['search', '🔎 Search'], ['top', '🔥 Top played']].map(([k, l]) => <button type="button" key={k} role="tab" aria-selected={lens === k}
      className={lens === k ? 'on' : ''} onClick={() => setLens(k)} data-testid={`mf-${k}`}>{l}</button>)}</div>
    {lens === 'search' && <input className="mf-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Search YouTube · artist or song…" aria-label="Search songs" data-testid="mf-q" />}
    {lens === 'search' && busy && <p className="mf-busy">Searching…</p>}
    <ol className="mf-list">
      {lens === 'search' && yt.slice(0, 10).map((v, i) => <li key={v.id} style={{ '--i': i }}>
        <img src={v.thumb} alt="" loading="lazy" /><span><b title={v.title}>{v.title}</b><small>{[v.channel, v.length, v.views].filter(Boolean).join(' · ')}</small></span>
        <button type="button" onClick={() => onAdd({ url: v.url, title: v.title }, true)} aria-label={`Play ${v.title}`} data-testid={`mf-play-${i}`}>▶</button>
        <button type="button" onClick={() => onAdd({ url: v.url, title: v.title }, false)} aria-label={`Add ${v.title} to the queue`}>＋</button></li>)}
      {lens === 'search' && (res?.spotify || []).slice(0, 5).map((t, i) => <li key={`sp-${i}`} className="is-sp" style={{ '--i': i }}>
        {t.art ? <img src={t.art} alt="" loading="lazy" /> : <i />}<span><b>{t.title}</b><small>Spotify · {t.artist}{t.popularity != null ? ` · 🔥 ${t.popularity}` : ''}</small></span>
        <button type="button" onClick={() => resolve(t, true)} aria-label={`Play ${t.title}`}>▶</button><button type="button" onClick={() => resolve(t, false)} aria-label={`Add ${t.title}`}>＋</button></li>)}
      {lens === 'top' && (top?.rows || []).map((t, i) => <li key={`${t.artist}-${t.title}`} style={{ '--i': Math.min(i, 12) }}>
        {t.art ? <img src={t.art} alt="" loading="lazy" /> : <i />}<span><b>{i + 1}. {t.title}</b><small>{t.artist}</small></span>
        <button type="button" onClick={() => resolve(t, true)} aria-label={`Play ${t.title}`} data-testid={`mf-top-${i}`}>▶</button><button type="button" onClick={() => resolve(t, false)} aria-label={`Add ${t.title}`}>＋</button></li>)}
    </ol>
    {lens === 'top' && top?.source && <p className="mf-src">{top.source} · plays from YouTube</p>}
    {lens === 'search' && res && !res.spotifyOn && q.trim().length >= 2 && <p className="mf-src">Spotify search turns on when a Spotify app key is set (HQ). YouTube covers it meanwhile.</p>}
  </div>;
}

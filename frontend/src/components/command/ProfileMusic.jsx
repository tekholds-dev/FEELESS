import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Music, Trash2, Plus, Shuffle, Repeat, Repeat1, ChevronUp, ChevronDown } from 'lucide-react';

// MySpace-style profile playlist: YouTube, Spotify and SoundCloud links.
export function parse(url) {
  const yt = /(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/.exec(url);
  if (yt) return { kind: 'youtube', src: `https://www.youtube.com/embed/${yt[1]}?enablejsapi=1&autoplay=1&playsinline=1` };
  const sp = /open\.spotify\.com\/(?:intl-\w+\/)?(track|album|playlist|episode)\/(\w+)/.exec(url);
  if (sp) return { kind: 'spotify', src: `https://open.spotify.com/embed/${sp[1]}/${sp[2]}` };
  if (/soundcloud\.com\//.test(url)) return { kind: 'soundcloud', src: `https://w.soundcloud.com/player/?url=${encodeURIComponent(url)}&auto_play=true&visual=false` };
  return null;
}

// Just paste a link: the title comes from the provider's public oEmbed (no key), else a readable fallback.
export async function songTitle(url) {
  const src = parse(url); if (!src) return null;
  try {
    const r = await fetch(`https://noembed.com/embed?url=${encodeURIComponent(url.trim())}`);
    const d = r.ok ? await r.json() : null;
    if (d?.title) return String(d.title).slice(0, 60);
  } catch { /* offline / blocked: fall back */ }
  return { youtube: 'YouTube track', spotify: 'Spotify track', soundcloud: 'SoundCloud track' }[src.kind];
}

const cmd = (c, extra = {}) => window.dispatchEvent(new CustomEvent('feeless:music-cmd', { detail: { cmd: c, ...extra } }));

// Profile playlist: the Fee mini player is the one engine (it keeps playing while you browse). This view
// sends it the playlist + commands and mirrors its live state, so play / pause / skip always match.
export function ProfileMusic({ songs = [], edit, onChange }) {
  const [live, setLive] = useState({ playing: false, url: null, mode: 'all' });
  const [url, setUrl] = useState('');
  useEffect(() => {
    const onState = e => setLive(e.detail || {});
    window.addEventListener('feeless:music-state', onState);
    return () => window.removeEventListener('feeless:music-state', onState);
  }, []);
  const ours = live.url && songs.some(sg => sg.url === live.url);   // is the mini player on this playlist?
  const i = ours ? Math.max(0, songs.findIndex(sg => sg.url === live.url)) : 0;
  const playing = ours && live.playing;
  const song = songs[i]; const src = song && parse(song.url);
  const start = at => window.dispatchEvent(new CustomEvent('feeless:music', { detail: { songs, i: at } }));
  const toggle = () => (ours ? cmd('toggle') : start(0));
  const skip = d => (ours ? cmd(d > 0 ? 'next' : 'prev') : start(d > 0 ? Math.min(1, songs.length - 1) : 0));
  const move = (k, d) => { const j = k + d; if (j < 0 || j >= songs.length) return; const n = [...songs]; [n[k], n[j]] = [n[j], n[k]]; onChange?.(n); };
  const add = async () => { if (!parse(url)) return; const u = url.trim(); setUrl(''); onChange?.([...songs, { url: u, title: await songTitle(u) }].slice(0, 15)); };
  const MODES = [['all', Repeat, 'Repeat all'], ['one', Repeat1, 'Repeat one'], ['shuffle', Shuffle, 'Shuffle']];
  if (!songs.length && !edit) return null;
  return <section className="wp-card wp-music" data-testid="profile-music">
    <h3><Music size={15} /> Profile playlist <small>{songs.length}/15</small></h3>
    {songs.length > 0 && <div className="pm-player">
      <div className="pm-now"><div className={`pm-disc ${playing ? 'spin' : ''}`}>♫</div><div><b>{song.title || 'Untitled'}</b><small>{src?.kind || 'link'} · {i + 1}/{songs.length}{playing ? ' · live in the Fee player' : ''}</small></div>{playing && <i className="eq big" aria-hidden="true"><b /><b /><b /><b /></i>}</div>
      <div className="pm-controls">
        <button type="button" onClick={() => skip(-1)} aria-label="Previous"><SkipBack size={15} /></button>
        <button type="button" className="pm-play" onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} data-testid="pm-play">{playing ? <Pause size={17} /> : <Play size={17} />}</button>
        <button type="button" onClick={() => skip(1)} aria-label="Next"><SkipForward size={15} /></button>
        {MODES.map(([m, Icon, label]) => <button key={m} type="button" className={live.mode === m ? 'on' : ''} onClick={() => cmd('mode', { mode: m })} aria-label={label} title={label}><Icon size={14} /></button>)}
      </div>
      <ol className="pm-list">{songs.map((sng, k) => <li key={`${sng.url}-${k}`} className={k === i && ours ? 'on' : ''}>
        <button type="button" onClick={() => (ours ? cmd('jump', { i: k }) : start(k))}>{k === i && playing ? <i className="eq"><b /><b /><b /></i> : <span>{k + 1}.</span>} {sng.title || sng.url}</button>
        {edit && <span className="pm-edit"><button type="button" onClick={() => move(k, -1)} disabled={!k} aria-label="Move up"><ChevronUp size={12} /></button><button type="button" onClick={() => move(k, 1)} disabled={k === songs.length - 1} aria-label="Move down"><ChevronDown size={12} /></button><button type="button" className="pm-del" onClick={() => onChange?.(songs.filter((_, j) => j !== k))} aria-label="Remove"><Trash2 size={12} /></button></span>}
      </li>)}</ol>
    </div>}
    {edit && <div className="pm-add"><input placeholder="YouTube, Spotify or SoundCloud link" value={url} onChange={e => setUrl(e.target.value)} /><button type="button" className="btn-outline" disabled={!parse(url) || songs.length >= 15} onClick={add}><Plus size={13} />Add song</button></div>}
    {!songs.length && edit && <p className="wp-bio">Add up to 15 songs. Visitors play, skip, shuffle and repeat, and it keeps playing while they browse.</p>}
  </section>;
}

import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Music, Trash2, Plus } from 'lucide-react';

// MySpace-style profile playlist: YouTube, Spotify and SoundCloud links.
function parse(url) {
  const yt = /(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/.exec(url);
  if (yt) return { kind: 'youtube', src: `https://www.youtube.com/embed/${yt[1]}?enablejsapi=1&autoplay=1&playsinline=1` };
  const sp = /open\.spotify\.com\/(?:intl-\w+\/)?(track|album|playlist|episode)\/(\w+)/.exec(url);
  if (sp) return { kind: 'spotify', src: `https://open.spotify.com/embed/${sp[1]}/${sp[2]}` };
  if (/soundcloud\.com\//.test(url)) return { kind: 'soundcloud', src: `https://w.soundcloud.com/player/?url=${encodeURIComponent(url)}&auto_play=true&visual=false` };
  return null;
}

export function ProfileMusic({ songs = [], edit, onChange }) {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [vol, setVol] = useState(() => { try { return Number(localStorage.getItem('feeless:music-vol') || 60); } catch { return 60; } });
  const [muted, setMuted] = useState(false);
  const [url, setUrl] = useState(''); const [title, setTitle] = useState('');
  const frame = useRef(null);
  const song = songs[i]; const src = song && parse(song.url);
  const send = msg => { try { frame.current?.contentWindow?.postMessage(typeof msg === 'string' ? msg : JSON.stringify(msg), '*'); } catch { /* cross-origin player not ready */ } };
  useEffect(() => {
    const v = muted ? 0 : vol;
    try { localStorage.setItem('feeless:music-vol', String(vol)); } catch { /* ignore */ }
    if (src?.kind === 'youtube') send({ event: 'command', func: 'setVolume', args: [v] });
    if (src?.kind === 'soundcloud') send({ method: 'setVolume', value: v });
  }, [vol, muted, src?.kind, i]); // eslint-disable-line react-hooks/exhaustive-deps
  const toggle = () => {
    if (!playing) { setPlaying(true); return; }
    if (src?.kind === 'youtube') send({ event: 'command', func: 'pauseVideo', args: [] });
    if (src?.kind === 'soundcloud') send({ method: 'pause' });
    setPlaying(false);
  };
  const go = d => { if (!songs.length) return; setI(x => (x + d + songs.length) % songs.length); setPlaying(true); };
  const add = () => { if (!parse(url)) return; onChange?.([...songs, { url: url.trim(), title: title.trim() || 'Untitled' }].slice(0, 15)); setUrl(''); setTitle(''); };
  if (!songs.length && !edit) return null;
  return <section className="wp-card wp-music" data-testid="profile-music">
    <h3><Music size={15} /> Profile playlist</h3>
    {songs.length > 0 && <div className="pm-player">
      <div className="pm-now"><div className={`pm-disc ${playing ? 'spin' : ''}`}>♫</div><div><b>{song.title || 'Untitled'}</b><small>{src?.kind || 'link'} · {i + 1}/{songs.length}</small></div></div>
      <div className="pm-controls">
        <button type="button" onClick={() => go(-1)} aria-label="Previous"><SkipBack size={15} /></button>
        <button type="button" className="pm-play" onClick={toggle} aria-label={playing ? 'Pause' : 'Play'}>{playing ? <Pause size={17} /> : <Play size={17} />}</button>
        <button type="button" onClick={() => go(1)} aria-label="Next"><SkipForward size={15} /></button>
        <button type="button" onClick={() => setMuted(m => !m)} aria-label="Mute">{muted || !vol ? <VolumeX size={15} /> : <Volume2 size={15} />}</button>
        <input type="range" min="0" max="100" value={muted ? 0 : vol} onChange={e => { setMuted(false); setVol(Number(e.target.value)); }} aria-label="Volume" disabled={src?.kind === 'spotify'} title={src?.kind === 'spotify' ? 'Spotify controls its own volume' : 'Volume'} />
      </div>
      {playing && src && <iframe ref={frame} key={`${i}-${src.src}`} className={`pm-frame pm-${src.kind}`} src={src.src} title={song.title || 'song'} allow="autoplay; encrypted-media" onLoad={() => { if (src.kind === 'youtube') { send({ event: 'listening' }); setTimeout(() => send({ event: 'command', func: 'setVolume', args: [muted ? 0 : vol] }), 600); } }} />}
      <ol className="pm-list">{songs.map((sng, k) => <li key={`${sng.url}-${k}`} className={k === i ? 'on' : ''}><button type="button" onClick={() => { setI(k); setPlaying(true); }}>{k === i && playing ? '▶' : k + 1}. {sng.title || sng.url}</button>{edit && <button type="button" className="pm-del" onClick={() => onChange?.(songs.filter((_, j) => j !== k))} aria-label="Remove"><Trash2 size={12} /></button>}</li>)}</ol>
    </div>}
    {edit && <div className="pm-add"><input placeholder="YouTube, Spotify or SoundCloud link" value={url} onChange={e => setUrl(e.target.value)} /><input placeholder="Title" maxLength={60} value={title} onChange={e => setTitle(e.target.value)} /><button type="button" className="btn-outline" disabled={!parse(url) || songs.length >= 15} onClick={add}><Plus size={13} />Add song</button></div>}
    {!songs.length && edit && <p className="wp-bio">Add up to 15 songs — visitors can play, skip and set the volume.</p>}
  </section>;
}

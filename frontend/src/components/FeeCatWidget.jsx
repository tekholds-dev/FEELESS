import React, { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Music2, MessageCircle, X, Plus, Play, Pause, SkipBack, SkipForward } from 'lucide-react';
import { FeeCatMark } from './FeeCatMark';
import EcosystemChat from './EcosystemChat';
import { parse } from './command/ProfileMusic';

const PLAYLIST_KEY = 'feeless:site-playlist';
const readList = () => { try { return JSON.parse(localStorage.getItem(PLAYLIST_KEY) || '[]'); } catch { return []; } };

// Small always-on-top FeeCat button: pick a chat room to lurk in, or a song to ride the charts to.
// Nothing here needs a wallet — it's read-only chat + a personal (browser-local) playlist.
export function FeeCatWidget() {
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState('chat');
  const [room, setRoom] = useState('feeless-general');
  const [songs, setSongs] = useState(readList);
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [url, setUrl] = useState('');
  useEffect(() => { try { localStorage.setItem(PLAYLIST_KEY, JSON.stringify(songs)); } catch { /* ignore */ } }, [songs]);
  // Any player on the site hands its playlist here; this is the one background player.
  useEffect(() => {
    const onMusic = e => { const d = e.detail || {}; if (!d.songs?.length) return; setSongs(d.songs.slice(0, 20)); setI(d.i || 0); setPlaying(true); };
    window.addEventListener('feeless:music', onMusic);
    return () => window.removeEventListener('feeless:music', onMusic);
  }, []);
  useEffect(() => { window.dispatchEvent(new CustomEvent('feeless:music-state', { detail: { playing } })); }, [playing]);
  const coinPair = useMemo(() => { const m = /coin=([^:&]+):([^&]+)/.exec(loc.search); return m ? { chain: m[1], pair: m[2] } : null; }, [loc.search]);
  const rooms = useMemo(() => {
    const list = [['feeless-general', 'FEELESS · General'], ['feeless-launch-general', 'Launch on FEELESS']];
    if (coinPair) list.unshift([`coin-${coinPair.chain}-${coinPair.pair}-trenches`, 'This coin · Trenches']);
    return list;
  }, [coinPair]);
  useEffect(() => { if (!rooms.some(([id]) => id === room)) setRoom(rooms[0][0]); }, [rooms]); // eslint-disable-line react-hooks/exhaustive-deps
  const song = songs[i]; const src = song && parse(song.url);
  const add = () => { if (!parse(url)) return; setSongs(s => [...s, { url: url.trim() }].slice(0, 20)); setUrl(''); };
  const go = d => { if (!songs.length) return; setI(x => (x + d + songs.length) % songs.length); setPlaying(true); };

  return <div className="feecat-widget" data-testid="feecat-widget">
    {open && <div className="feecat-panel" data-testid="feecat-panel">
      <div className="feecat-panel-head">
        <div className="feecat-tabs">
          <button type="button" className={tab === 'chat' ? 'active' : ''} onClick={() => setTab('chat')}><MessageCircle size={13} />Chat</button>
          <button type="button" className={tab === 'music' ? 'active' : ''} onClick={() => setTab('music')}><Music2 size={13} />Music</button>
        </div>
        <button type="button" className="feecat-x" onClick={() => setOpen(false)} aria-label="Close"><X size={15} /></button>
      </div>
      {tab === 'chat' && <div className="feecat-chat">
        <div className="feecat-rooms">{rooms.map(([id, label]) => <button key={id} type="button" className={room === id ? 'active' : ''} onClick={() => setRoom(id)}>{label}</button>)}</div>
        <EcosystemChat key={room} compact room={room} ecosystem={{ id: room, name: 'FEELESS' }} />
      </div>}
      {tab === 'music' && <div className="feecat-music">
        {songs.length > 0 ? <>
          <div className="feecat-now"><b>{song?.title || 'Track ' + (i + 1)}</b><small>{i + 1}/{songs.length}</small></div>
          <div className="feecat-controls">
            <button type="button" onClick={() => go(-1)} aria-label="Previous"><SkipBack size={14} /></button>
            <button type="button" className="feecat-play" onClick={() => setPlaying(p => !p)} aria-label={playing ? 'Pause' : 'Play'}>{playing ? <Pause size={16} /> : <Play size={16} />}</button>
            <button type="button" onClick={() => go(1)} aria-label="Next"><SkipForward size={14} /></button>
          </div>
        </> : <p className="feecat-empty">No songs yet — paste a YouTube, Spotify or SoundCloud link below.</p>}
        <div className="feecat-add"><input placeholder="Paste a song link…" value={url} onChange={e => setUrl(e.target.value)} /><button type="button" disabled={!parse(url)} onClick={add}><Plus size={13} /></button></div>
      </div>}
    </div>}
    {playing && src && <iframe key={`${i}-${src.src}`} className={`feecat-frame pm-${src.kind} ${open && tab === 'music' ? '' : 'is-background'}`} src={src.src} title="now playing" allow="autoplay; encrypted-media" />}
    <button type="button" className={`feecat-fab ${open ? 'on' : ''}`} onClick={() => setOpen(o => !o)} data-testid="feecat-fab" aria-label="FeeCat">
      <FeeCatMark size={32} variant={playing ? 'gold' : 'mint'} /> {playing && <i className="feecat-note">♪</i>}
    </button>
  </div>;
}

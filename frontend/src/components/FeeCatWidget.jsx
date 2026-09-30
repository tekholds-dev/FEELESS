import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Music2, MessageCircle, X, Plus, Play, Pause, SkipBack, SkipForward, Shuffle, Repeat, Repeat1 } from 'lucide-react';
import { FeeCatMark } from './FeeCatMark';
import EcosystemChat from './EcosystemChat';
import { parse } from './command/ProfileMusic';

const PLAYLIST_KEY = 'feeless:site-playlist';
const readList = () => { try { return JSON.parse(localStorage.getItem(PLAYLIST_KEY) || '[]'); } catch { return []; } };

// Small always-on-top FeeCat button: pick a chat room to lurk in, or a song to ride the charts to.
// Nothing here needs a wallet — it's read-only chat + a personal (browser-local) playlist.
// Resume mid-song where the player supports it (YouTube ?start, SoundCloud #t).
export const withStart = (src, secs) => (secs < 3 ? src.src : src.kind === 'youtube' ? `${src.src}&start=${secs}` : src.kind === 'soundcloud' ? `${src.src}#t=${secs}s` : src.src);

export function FeeCatWidget() {
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState('chat');
  const [room, setRoom] = useState('feeless-general');
  const [songs, setSongs] = useState(readList);
  // Keeps playing across reloads and full-page links: song, play state and when it started live in localStorage.
  const saved = (() => { try { return JSON.parse(localStorage.getItem('feeless:music-now') || 'null'); } catch { return null; } })();
  const [i, setI] = useState(() => (saved && saved.i < readList().length ? saved.i : 0));
  const [playing, setPlaying] = useState(() => Boolean(saved?.playing && readList().length));
  const startedAt = useRef(saved?.playing ? saved.startedAt || Date.now() : Date.now());
  const [url, setUrl] = useState('');
  // repeat: 'all' loops the list, 'one' repeats the song, 'shuffle' picks a random next song.
  const [mode, setMode] = useState(() => { try { return localStorage.getItem('feeless:music-mode') || 'all'; } catch { return 'all'; } });
  const [nonce, setNonce] = useState(0); // bump to restart the same song (repeat one)
  const frame = useRef(null);
  const resumed = useRef(false); const [kick, setKick] = useState(0);
  useEffect(() => { if (!resumed.current) return; startedAt.current = Date.now(); }, [i, nonce, playing]);   // a new song (or play after pause) starts at 0
  useEffect(() => { resumed.current = true; }, []);
  useEffect(() => { try { localStorage.setItem('feeless:music-now', JSON.stringify({ i, playing, startedAt: startedAt.current })); } catch { /* private mode */ } }, [i, playing, nonce]);
  // Browsers may block sound until the first tap after a reload: restart the song (same spot) on that first tap.
  useEffect(() => {
    if (!playing) return undefined;
    const once = () => setKick(k => k + 1);   // re-mount at the same spot (not a restart)
    window.addEventListener('pointerdown', once, { once: true });
    return () => window.removeEventListener('pointerdown', once);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { try { localStorage.setItem(PLAYLIST_KEY, JSON.stringify(songs)); localStorage.setItem('feeless:music-mode', mode); } catch { /* ignore */ } }, [songs, mode]);
  const next = (auto = false) => {
    if (!songs.length) return;
    if (auto && mode === 'one') { setNonce(n => n + 1); return; }
    if (mode === 'shuffle' && songs.length > 1) { setI(x => { let r = x; while (r === x) r = Math.floor(Math.random() * songs.length); return r; }); }
    else setI(x => (x + 1) % songs.length);
    setPlaying(true);
  };
  const nextRef = useRef(next); nextRef.current = next;
  // The one background player for the whole site. Profiles (or anything else) send it a playlist or a command;
  // it broadcasts what's playing so every view stays in sync.
  useEffect(() => {
    const onMusic = e => { const d = e.detail || {}; if (!d.songs?.length) return; setSongs(d.songs.slice(0, 20)); setI(d.i || 0); setPlaying(true); };
    const onCmd = e => {
      const { cmd, i: at, mode: m } = e.detail || {};
      if (cmd === 'toggle') setPlaying(p => !p);
      if (cmd === 'pause') setPlaying(false);
      if (cmd === 'play') setPlaying(true);
      if (cmd === 'next') nextRef.current(false);
      if (cmd === 'prev') { setI(x => (x - 1 + Math.max(1, songs.length)) % Math.max(1, songs.length)); setPlaying(true); }
      if (cmd === 'jump' && Number.isInteger(at)) { setI(at); setPlaying(true); }
      if (cmd === 'mode' && m) setMode(m);
    };
    // Song finished → next. YouTube reports playerState 0, SoundCloud a 'finish' event.
    const onMessage = e => {
      if (!frame.current || e.source !== frame.current.contentWindow) return;
      let d = e.data; try { d = typeof d === 'string' ? JSON.parse(d) : d; } catch { return; }
      if ((d?.event === 'onStateChange' && d.info === 0) || (d?.event === 'infoDelivery' && d.info?.playerState === 0) || d?.method === 'finish') nextRef.current(true);
    };
    window.addEventListener('feeless:music', onMusic); window.addEventListener('feeless:music-cmd', onCmd); window.addEventListener('message', onMessage);
    return () => { window.removeEventListener('feeless:music', onMusic); window.removeEventListener('feeless:music-cmd', onCmd); window.removeEventListener('message', onMessage); };
  }, [songs.length]);
  useEffect(() => { window.dispatchEvent(new CustomEvent('feeless:music-state', { detail: { playing, i, url: songs[i]?.url, mode } })); }, [playing, i, mode, songs]);
  const hookEnd = () => {
    const w = frame.current?.contentWindow; if (!w) return;
    const post = m => { try { w.postMessage(typeof m === 'string' ? m : JSON.stringify(m), '*'); } catch { /* not ready */ } };
    if (src?.kind === 'youtube') { post({ event: 'listening', id: 1, channel: 'widget' }); post({ event: 'command', func: 'addEventListener', args: ['onStateChange'] }); }
    if (src?.kind === 'soundcloud') post({ method: 'addEventListener', value: 'finish' });
  };
  const coinPair = useMemo(() => { const m = /coin=([^:&]+):([^&]+)/.exec(loc.search); return m ? { chain: m[1], pair: m[2] } : null; }, [loc.search]);
  const rooms = useMemo(() => {
    const list = [['feeless-general', 'FEELESS · General'], ['feeless-launch-general', 'Launch on FEELESS']];
    if (coinPair) list.unshift([`coin-${coinPair.chain}-${coinPair.pair}-trenches`, 'This coin · Trenches']);
    return list;
  }, [coinPair]);
  useEffect(() => { if (!rooms.some(([id]) => id === room)) setRoom(rooms[0][0]); }, [rooms]); // eslint-disable-line react-hooks/exhaustive-deps
  const song = songs[i]; const src = song && parse(song.url);
  const add = () => { if (!parse(url)) return; setSongs(s => [...s, { url: url.trim() }].slice(0, 20)); setUrl(''); };
  const go = d => { if (!songs.length) return; if (d > 0) { next(false); return; } setI(x => (x + d + songs.length) % songs.length); setPlaying(true); };
  const MODES = [['all', Repeat, 'Repeat all'], ['one', Repeat1, 'Repeat one'], ['shuffle', Shuffle, 'Shuffle']];

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
            {MODES.map(([m, Icon, label]) => <button key={m} type="button" className={mode === m ? 'on' : ''} onClick={() => setMode(m)} aria-label={label} title={label}><Icon size={13} /></button>)}
          </div>
          <ol className="feecat-queue">{songs.map((sg, k) => <li key={`${sg.url}-${k}`}><button type="button" className={k === i ? 'on' : ''} onClick={() => { setI(k); setPlaying(true); }}>{k === i && playing ? <i className="eq"><b /><b /><b /></i> : <span>{k + 1}</span>}{sg.title || sg.url}</button></li>)}</ol>
        </> : <p className="feecat-empty">No songs yet — paste a YouTube, Spotify or SoundCloud link below.</p>}
        <div className="feecat-add"><input placeholder="Paste a song link…" value={url} onChange={e => setUrl(e.target.value)} /><button type="button" disabled={!parse(url)} onClick={add}><Plus size={13} /></button></div>
      </div>}
    </div>}
    {playing && src && <iframe ref={frame} key={`${i}-${nonce}-${kick}-${src.src}`} onLoad={() => setTimeout(hookEnd, 600)} className={`feecat-frame pm-${src.kind} ${open && tab === 'music' ? '' : 'is-background'}`} src={withStart(src, Math.floor((Date.now() - startedAt.current) / 1000))} title="now playing" allow="autoplay; encrypted-media" />}
    <button type="button" className={`feecat-fab ${open ? 'on' : ''}`} onClick={() => setOpen(o => !o)} data-testid="feecat-fab" aria-label="FeeCat">
      <FeeCatMark size={32} variant={playing ? 'gold' : 'mint'} /> {playing && <i className="feecat-note">♪</i>}
    </button>
  </div>;
}

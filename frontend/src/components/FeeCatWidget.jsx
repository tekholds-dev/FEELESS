import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Music2, MessageCircle, X, Plus, Play, Pause, SkipBack, SkipForward, Shuffle, Repeat, Repeat1 } from 'lucide-react';
import { FeeCatMark } from './FeeCatMark';
import EcosystemChat from './EcosystemChat';
import { parse, songTitle } from './command/ProfileMusic';
import { MiniMine, MiniTop } from './MiniDeck';
import MusicFind, { ytId } from './MusicFind';
import { apiUrl } from '../lib/api';

const PLAYLIST_KEY = 'feeless:site-playlist';
// ▶ Like YouTube: a refresh comes back to the same song at the same second, still playing (or still paused).
// `pos` = the player's own reported time; old saves (no pos) start the song from the top.
export function resumeFrom(saved, listLen) {
  if (!saved || !listLen) return { i: 0, playing: false, pos: 0 };
  const i = Number.isInteger(saved.i) && saved.i >= 0 && saved.i < listLen ? saved.i : 0;
  const pos = Number.isFinite(saved.pos) && saved.pos > 0 && i === saved.i ? Math.floor(saved.pos) : 0;
  return { i, playing: Boolean(saved.playing), pos };
}
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
  // Keeps playing across reloads and full-page links (like YouTube): song, play state and the exact second live in localStorage.
  const boot = useMemo(() => { try { return resumeFrom(JSON.parse(localStorage.getItem('feeless:music-now') || 'null'), readList().length); } catch { return resumeFrom(null, 0); } }, []);
  const [i, setI] = useState(boot.i);
  const [playing, setPlaying] = useState(boot.playing);
  const [showVideo, setShowVideo] = useState(() => { try { return localStorage.getItem('feeless:music-video') !== 'off'; } catch { return true; } });
  useEffect(() => { try { localStorage.setItem('feeless:music-video', showVideo ? 'on' : 'off'); } catch { /* private mode */ } }, [showVideo]);
  const pos = useRef(boot.pos);          // the player's current second (YouTube reports it ~4×/s)
  const ytState = useRef(-1);            // last YouTube player state (1 = playing)
  const muted = useRef(false);           // started muted because the browser blocked sound → unmute on the first tap
  const [url, setUrl] = useState('');
  // repeat: 'all' loops the list, 'one' repeats the song, 'shuffle' picks a random next song.
  const [mode, setMode] = useState(() => { try { return localStorage.getItem('feeless:music-mode') || 'all'; } catch { return 'all'; } });
  const [nonce, setNonce] = useState(0); // bump to restart the same song (repeat one)
  const frame = useRef(null);
  const booted = useRef(false);
  useEffect(() => { if (booted.current) pos.current = 0; booted.current = true; }, [i, nonce]);   // a NEW song starts at 0 (pause → play resumes)
  const save = () => { try { localStorage.setItem('feeless:music-now', JSON.stringify({ i: iRef.current, playing: playRef.current, pos: pos.current })); } catch { /* private mode */ } };
  const iRef = useRef(i); iRef.current = i; const playRef = useRef(playing); playRef.current = playing;
  useEffect(save, [i, playing, nonce]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {   // the exact second is saved every 2s and when the page goes away
    const t = setInterval(() => playRef.current && save(), 2000);
    window.addEventListener('pagehide', save); window.addEventListener('beforeunload', save);
    return () => { clearInterval(t); window.removeEventListener('pagehide', save); window.removeEventListener('beforeunload', save); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const ytCmd = (func, args = []) => { try { frame.current?.contentWindow?.postMessage(JSON.stringify({ event: 'command', func, args }), '*'); } catch { /* not ready */ } };
  // Browsers may block SOUND after a reload (never a muted video): keep the song going muted, and unmute on the first tap/key.
  useEffect(() => {
    const unmute = () => { if (!muted.current) return; muted.current = false; ytCmd('unMute'); ytCmd('playVideo'); };
    window.addEventListener('pointerdown', unmute); window.addEventListener('keydown', unmute);
    return () => { window.removeEventListener('pointerdown', unmute); window.removeEventListener('keydown', unmute); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { try { localStorage.setItem(PLAYLIST_KEY, JSON.stringify(songs)); localStorage.setItem('feeless:music-mode', mode); } catch { /* ignore */ } }, [songs, mode]);
  // ▶ add a found song: play it now (jumps to it) or queue it (max 20 kept, oldest drop off)
  const addSong = (sg, now) => setSongs(list => { const n = [...list.filter(x => x.url !== sg.url), sg].slice(-20); if (now) { setI(n.length - 1); setPlaying(true); } return n; });
  // ▶▶ like YouTube: at the END of the queue Next keeps going — another song by the same artist that is not queued yet
  // (GET /music/next); if nothing comes back it loops the queue as before.
  const keepGoing = async () => {
    const cur = songs[i] || {};
    const qs = new URLSearchParams({ title: cur.title || '', skip: songs.map(x => ytId(x.url)).filter(Boolean).join(','), titles: songs.map(x => x.title || '').join('|') });
    try { const d = await fetch(apiUrl(`/api/reputation/music/next?${qs}`)).then(r => r.json()); if (d?.next?.url) { addSong({ url: d.next.url, title: d.next.title }, true); return true; } } catch { /* offline: loop */ }
    return false;
  };
  const next = (auto = false) => {
    if (!songs.length) return;
    if (auto && mode === 'one') { setNonce(n => n + 1); return; }
    if (mode === 'shuffle' && songs.length > 1) { setI(x => { let r = x; while (r === x) r = Math.floor(Math.random() * songs.length); return r; }); }
    else if (mode === 'all' && i === songs.length - 1) { keepGoing().then(ok => { if (!ok) { setI(0); setPlaying(true); } }); return; }
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
      if (d?.event === 'infoDelivery' && Number.isFinite(d.info?.currentTime)) pos.current = d.info.currentTime;
      if (d?.event === 'onStateChange' && Number.isInteger(d.info)) ytState.current = d.info;
      if (d?.event === 'infoDelivery' && Number.isInteger(d.info?.playerState)) ytState.current = d.info.playerState;
      if (d?.method === 'playProgress' && Number.isFinite(d.value?.currentPosition)) pos.current = d.value.currentPosition / 1000;
      if ((d?.event === 'onStateChange' && d.info === 0) || (d?.event === 'infoDelivery' && d.info?.playerState === 0) || d?.method === 'finish') nextRef.current(true);
    };
    window.addEventListener('feeless:music', onMusic); window.addEventListener('feeless:music-cmd', onCmd); window.addEventListener('message', onMessage);
    return () => { window.removeEventListener('feeless:music', onMusic); window.removeEventListener('feeless:music-cmd', onCmd); window.removeEventListener('message', onMessage); };
  }, [songs.length]);
  useEffect(() => { window.dispatchEvent(new CustomEvent('feeless:music-state', { detail: { playing, i, url: songs[i]?.url, mode } })); }, [playing, i, mode, songs]);
  const hookEnd = () => {
    const w = frame.current?.contentWindow; if (!w) return;
    const post = m => { try { w.postMessage(typeof m === 'string' ? m : JSON.stringify(m), '*'); } catch { /* not ready */ } };
    if (src?.kind === 'youtube') {
      post({ event: 'listening', id: 1, channel: 'widget' }); post({ event: 'command', func: 'addEventListener', args: ['onStateChange'] });
      setTimeout(() => { if (playRef.current && ytState.current !== 1) { muted.current = true; ytCmd('mute'); ytCmd('playVideo'); } }, 2200);   // sound blocked → play muted
    }
    if (src?.kind === 'soundcloud') { post({ method: 'addEventListener', value: 'finish' }); post({ method: 'addEventListener', value: 'playProgress' }); }
  };
  const coinPair = useMemo(() => { const m = /coin=([^:&]+):([^&]+)/.exec(loc.search); return m ? { chain: m[1], pair: m[2] } : null; }, [loc.search]);
  const rooms = useMemo(() => {
    const list = [['feeless-general', 'FEELESS · General'], ['feeless-launch-general', 'Launch on FEELESS']];
    if (coinPair) list.unshift([`coin-${coinPair.chain}-${coinPair.pair}-trenches`, 'This coin · Trenches']);
    return list;
  }, [coinPair]);
  useEffect(() => { if (!rooms.some(([id]) => id === room)) setRoom(rooms[0][0]); }, [rooms]); // eslint-disable-line react-hooks/exhaustive-deps
  const song = songs[i]; const src = song && parse(song.url);
  // the start second is fixed when the player mounts (never re-computed per render — that would reload the iframe)
  const startSrc = useMemo(() => (src ? withStart(src, Math.floor(pos.current)) : ''), [i, nonce, playing, src?.src]); // eslint-disable-line react-hooks/exhaustive-deps
  const add = async () => { if (!parse(url)) return; const u = url.trim(); setUrl(''); const title = await songTitle(u); setSongs(s => [...s, { url: u, title }].slice(0, 20)); };
  const remove = k => { setSongs(s => s.filter((_, j) => j !== k)); if (k < i) setI(x => x - 1); else if (k === i) { setPlaying(false); setI(x => Math.max(0, Math.min(x, songs.length - 2))); } };
  const go = d => { if (!songs.length) return; if (d > 0) { next(false); return; } setI(x => (x + d + songs.length) % songs.length); setPlaying(true); };
  const MODES = [['all', Repeat, 'Repeat all'], ['one', Repeat1, 'Repeat one'], ['shuffle', Shuffle, 'Shuffle']];

  return <div className="feecat-widget" data-testid="feecat-widget">
    {open && <div className="feecat-panel" data-testid="feecat-panel">
      <div className="feecat-panel-head">
        <div className="feecat-tabs">
          <button type="button" className={tab === 'chat' ? 'active' : ''} onClick={() => setTab('chat')}><MessageCircle size={13} />Chat</button>
          <button type="button" className={tab === 'music' ? 'active' : ''} onClick={() => setTab('music')}><Music2 size={13} />Music</button>
          <button type="button" className={tab === 'mine' ? 'active' : ''} onClick={() => setTab('mine')} data-testid="mini-tab-mine">💼 Mine</button>
          <button type="button" className={tab === 'top' ? 'active' : ''} onClick={() => setTab('top')} data-testid="mini-tab-top">🔥 Top 10</button>
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
            <button type="button" className={showVideo ? 'on' : ''} onClick={() => setShowVideo(v => !v)} aria-pressed={showVideo} title={showVideo ? 'Hide video (keeps playing)' : 'Show video'} data-testid="music-video-toggle">📺</button>
          </div>
          <ol className="feecat-queue">{songs.map((sg, k) => <li key={`${sg.url}-${k}`}><button type="button" className={k === i ? 'on' : ''} onClick={() => { setI(k); setPlaying(true); }}>{k === i && playing ? <i className="eq"><b /><b /><b /></i> : <span>{k + 1}</span>}{sg.title || sg.url}</button><button type="button" className="feecat-x" aria-label={`Remove ${sg.title || 'song'}`} data-testid={`music-remove-${k}`} onClick={() => remove(k)}><X size={12} /></button></li>)}</ol>
        </> : <p className="feecat-empty">No songs yet — paste a YouTube, Spotify or SoundCloud link below.</p>}
        <div className="feecat-add"><input placeholder="Paste a song link…" value={url} onChange={e => setUrl(e.target.value)} /><button type="button" disabled={!parse(url)} onClick={add}><Plus size={13} /></button></div>
        <MusicFind onAdd={addSong} />
      </div>}
      {tab === 'mine' && <MiniMine />}
      {tab === 'top' && <MiniTop />}
      {tab !== 'music' && songs.length > 0 && <div className="mini-bar" data-testid="mini-player">
        <button type="button" onClick={() => go(-1)} aria-label="Previous"><SkipBack size={12} /></button>
        <button type="button" className={playing ? 'is-play' : ''} onClick={() => setPlaying(p => !p)} aria-label={playing ? 'Pause' : 'Play'}>{playing ? <Pause size={13} /> : <Play size={13} />}</button>
        <button type="button" onClick={() => go(1)} aria-label="Next"><SkipForward size={12} /></button>
        <b>{song?.title || 'Track ' + (i + 1)}</b></div>}
    </div>}
    {playing && src && <iframe ref={frame} key={`${i}-${nonce}-${src.src}`} onLoad={() => setTimeout(hookEnd, 600)} className={`feecat-frame pm-${src.kind} ${open && tab === 'music' && showVideo ? '' : 'is-background'}`} src={startSrc} title="now playing" allow="autoplay; encrypted-media" />}
    <button type="button" className={`feecat-fab ${open ? 'on' : ''}`} onClick={() => setOpen(o => !o)} data-testid="feecat-fab" aria-label="FeeCat">
      <FeeCatMark size={32} variant={playing ? 'gold' : 'mint'} /> {playing && <i className="feecat-note">♪</i>}
    </button>
  </div>;
}

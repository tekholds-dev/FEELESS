import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import { ALL_CHARACTERS, STYLES, load2d, loadCreate, mediapipePaths, peopleFile, pickRecorderType, startTracker, streamTracks, thumbOf } from '../../lib/wireface';
import { Ic3 } from '../../lib/icon3d';
import { DEFAULT_SCENE, createScene } from '../../lib/liveScene';
import '../../styles/character.css';

// 🎭 THE CHARACTER FOLDER (owner 2026-11-04): pick who this agent is, talk through it with camera and voice if you opt in, and go live as it on your own channels.
// The picture comes alive with Wireface 2D, on this device. The camera is read here and never sent anywhere; a stream carries the character and your voice only.
const MOODS = [['happy', 'Happy'], ['surprised', 'Surprised'], ['thinking', 'Thinking'], ['sad', 'Sad'], ['frustrated', 'Mad'], ['calm', 'Calm']];
const TABS = [['pick', '🎭', 'Character'], ['me', '📷', 'Camera + voice'], ['live', '🔴', 'Go live']];
const clock = s => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
const NO_KEYS = { twitch: { label: 'Twitch', server: 'rtmps://live.twitch.tv/app', set: false, needsServer: false }, kick: { label: 'Kick', server: '', set: false, needsServer: true }, tiktok: { label: 'TikTok', server: '', set: false, needsServer: true } };
const CAN_PIP = () => typeof window !== 'undefined' && 'documentPictureInPicture' in window;

export function nameWait(s) {
  if (!s) return '';
  const d = Math.floor(s / 86400); const h = Math.floor((s % 86400) / 3600);
  return d ? `${d}d ${h}h` : `${Math.max(1, h)}h`;
}

function Tile({ id, name, style, on, onPick, cat }) {
  return <button type="button" className={`chr-tile${on ? ' is-on' : ''}`} onClick={() => onPick(id)} aria-pressed={on} data-tip={`${name}, ${style}`} data-testid={`chr-${id}`}>
    <img src={id === 'custom' ? apiUrl(thumbOf(id, cat.id)) : thumbOf(id)} alt="" loading="lazy" /><em>{style}</em><b>{name}</b></button>;
}

function PickTab({ cat, face, onPick, onPicture, busy, err, mine }) {
  const [style, setStyle] = useState('All'); const file = useRef(null);
  const rows = useMemo(() => ALL_CHARACTERS.filter(c => style === 'All' || c[2] === style), [style]);
  return <>
    <div className="chr-chips" role="group" aria-label="Art style">{STYLES.map(s => <button key={s} type="button" className={`m-chip${style === s ? ' is-on' : ''}`} aria-pressed={style === s} onClick={() => setStyle(s)}>{s}</button>)}</div>
    <div className="chr-grid">
      {mine ? <button type="button" className="chr-tile is-add" onClick={() => file.current?.click()} disabled={busy} data-tip="A clear photo, facing you, mouth closed. It is rigged on this device" data-testid="chr-add"><i aria-hidden="true">+</i><b>{busy ? 'Rigging…' : 'Your picture'}</b></button> : null}
      {face === 'custom' ? <Tile id="custom" name="Yours" style="Picture" on cat={cat} onPick={onPick} /> : null}
      {rows.map(([id, n, s]) => <Tile key={id} id={id} name={n} style={s} on={face === id} cat={cat} onPick={onPick} />)}
    </div>
    <input ref={file} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (f) onPicture(f); }} data-testid="chr-file" />
    <small className="chr-note">Use only a picture you have the right to use, and never pass yourself off as someone else.</small>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </>;
}

function MeTab({ camOn, micOn, onCam, onMic, status, err }) {
  return <div className="chr-opts">
    <button type="button" className={`chr-opt${camOn ? ' is-on' : ''}`} onClick={onCam} aria-pressed={camOn} data-testid="chr-cam"><Ic3 e="📷" size="30px" /><b>Face tracking</b><small>{camOn ? status || 'Watching your face' : 'Off until you turn it on'}</small><i className="chr-sw" aria-hidden="true" /></button>
    <button type="button" className={`chr-opt${micOn ? ' is-on' : ''}`} onClick={onMic} aria-pressed={micOn} data-testid="chr-mic"><Ic3 e="🎙" size="30px" /><b>Voice</b><small>{micOn ? 'Its mouth follows your voice' : 'Off until you turn it on'}</small><i className="chr-sw" aria-hidden="true" /></button>
    <ul className="chr-facts"><li><Ic3 e="🔒" /> Your camera stays on this device</li><li><Ic3 e="🎭" /> Viewers only see the character</li><li><Ic3 e="🙈" /> Turn it off and it stops at once</li></ul>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </div>;
}

function KeyRow({ k, row, cat, work, onSaved }) {
  const [server, setServer] = useState(''); const [key, setKey] = useState(''); const [err, setErr] = useState(''); const [open, setOpen] = useState(false);
  const save = async on => { setErr(''); try { const j = await work(cat.id, on ? { op: 'live_key', text: k, user: server || row.server, secret: key } : { op: 'live_key', text: k, on: false }); onSaved(j.liveKeys); setKey(''); setOpen(false); } catch (e) { setErr(e.message); } };
  return <div className={`chr-ch is-${k}${row.set ? ' is-set' : ''}`} data-testid={`chr-ch-${k}`}>
    <button type="button" className="chr-ch-h" onClick={() => setOpen(o => !o)} aria-expanded={open}><b>{row.label}</b><small>{row.set ? 'Key sealed' : 'Add your key'}</small></button>
    {open ? <div className="chr-ch-b">
      {row.needsServer ? <input className="m-input" placeholder={`Server address from ${row.label}`} value={server} onChange={e => setServer(e.target.value)} aria-label={`${row.label} server address`} /> : null}
      <input className="m-input" type="password" autoComplete="off" placeholder="Stream key" value={key} onChange={e => setKey(e.target.value)} aria-label={`${row.label} stream key`} />
      <span><button type="button" className="m-btn" onClick={() => save(true)} disabled={!key} data-testid={`chr-save-${k}`}>Seal it</button>{row.set ? <button type="button" className="m-btn" onClick={() => save(false)}>Remove</button> : null}</span>
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div> : null}
  </div>;
}

// What the stream shows, sorted before going live, and what a viewer will see is exactly this preview.
function SceneSetup({ scene, opts, setOpts }) {
  const host = useRef(null);
  useEffect(() => { const el = host.current; if (el && scene?.canvas && !el.contains(scene.canvas)) { el.innerHTML = ''; el.append(scene.canvas); } }, [scene]);
  const pick = p => { const n = { ...opts, ...p }; setOpts(n); scene?.set(n); };
  const flag = (k, l, tip) => <button type="button" className={`chr-toggle${opts[k] ? ' is-on' : ''}`} aria-pressed={!!opts[k]} onClick={() => pick({ [k]: !opts[k] })} data-tip={tip} data-testid={`chr-scene-${k}`}>{l}</button>;
  return <div className="chr-scene" data-testid="chr-scene"><div ref={host} className="chr-scene-view" />
    <div className="chr-scene-row"><span>AGENT</span><div className="m-seg" role="group" aria-label="Where the agent sits">{[['left', 'Bottom left'], ['right', 'Bottom right'], ['off', 'Hidden']].map(([k, l]) => <button key={k} type="button" className={opts.corner === k ? 'active' : ''} onClick={() => pick({ corner: k })} data-testid={`chr-corner-${k}`}>{l}</button>)}</div>
      <div className="m-seg" role="group" aria-label="Agent size">{[['s', 'S'], ['m', 'M'], ['l', 'L']].map(([k, l]) => <button key={k} type="button" className={opts.size === k ? 'active' : ''} onClick={() => pick({ size: k })}>{l}</button>)}</div></div>
    <div className="chr-scene-row"><span>SHOW</span>{flag('monitors', 'Monitors', 'Its two windows, the same frames visitors get: a private page is blank')}{flag('minds', 'The 2 minds', 'What each mind said last')}{flag('chat', 'Chat', 'Your chat with it. Emails and phone numbers are taken out, but you choose if viewers see it')}</div></div>;
}

function LiveTab({ cat, keys, setKeys, work, live, secs, onLive, onPop, err, scene, opts, setOpts }) {
  const rows = Object.entries(keys || {}); const ready = rows.filter(([, v]) => v.set).map(([k]) => k);
  return <div className="chr-livebox">
    <SceneSetup scene={scene} opts={opts} setOpts={setOpts} />
    <div className="chr-chs">{rows.map(([k, row]) => <KeyRow key={k} k={k} row={row} cat={cat} work={work} onSaved={setKeys} />)}</div>
    <button type="button" className={`chr-onair${live ? ' is-on' : ''}`} onClick={() => onLive(ready)} disabled={!live && !ready.length} data-testid="chr-go-live"><i aria-hidden="true" /><b>{live ? `LIVE ${clock(secs)} · End` : 'GO LIVE'}</b><small>{live ? 'Keep this tab open and in front' : ready.length ? `To ${ready.map(k => keys[k].label).join(' + ')}` : 'Seal a stream key first'}</small></button>
    {CAN_PIP() ? <button type="button" className="m-btn" onClick={onPop} data-testid="chr-pop">⧉ Pop out the dash</button> : null}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </div>;
}

export function CharacterFolder({ cat, work, setD, d }) {
  const mine = cat?.mine !== false;
  const stage = useRef(null); const faceRef = useRef(null); const sdkRef = useRef(null); const audio = useRef(null); const videoRef = useRef(null); const camStop = useRef(null); const camStream = useRef(null); const mic = useRef(null); const micStop = useRef(null); const socket = useRef(null); const recorder = useRef(null); const trackStop = useRef(null);
  const [face, setFace] = useState(cat?.face?.id || null); const [tab, setTab] = useState('pick'); const [ready, setReady] = useState(false); const [fail, setFail] = useState('');
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [camOn, setCamOn] = useState(false); const [micOn, setMicOn] = useState(false); const [status, setStatus] = useState(''); const [mood, setMood] = useState(null);
  const [keys, setKeys] = useState(cat?.liveKeys || NO_KEYS); const [live, setLive] = useState(false); const [secs, setSecs] = useState(0); const [liveErr, setLiveErr] = useState('');
  const [pip, setPip] = useState(null); const [name, setName] = useState(cat?.name || ''); const [nameMsg, setNameMsg] = useState('');
  const faceId = face || 'sarah';
  const [scene, setScene] = useState(null); const [opts, setOpts] = useState({ ...DEFAULT_SCENE });
  useEffect(() => { if (tab !== 'live' && !live) return undefined; if (!stage.current) return undefined; const s = createScene({ face: stage.current, catId: cat.id, api: apiUrl }); s.set(opts); s.feed({ rows: d?.chat || d?.messages || [], name: cat.name }); s.start(); setScene(s); return () => { s.stop(); setScene(null); }; }, [tab === 'live' || live]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { scene?.feed({ rows: d?.chat || d?.messages || [] }); }, [scene, d]);

  const wear = useCallback(async id => {
    const f = faceRef.current; if (!f) return;
    if (id === 'custom') { const sdk = sdkRef.current; const r = await fetch(apiUrl(`/api/cats/${cat.id}/face/character`)); await f.useCharacter(await sdk.loadCharacter(await r.arrayBuffer())); } else if (peopleFile(id)) await f.useCharacter(await sdkRef.current.loadCharacter(peopleFile(id))); else await f.useCharacter(id);
  }, [cat?.id]);

  useEffect(() => {
    let dead = false; let io = null;
    (async () => {
      try {
        const sdk = await load2d(); if (dead) return;
        sdkRef.current = sdk; const f = sdk.createFace2d(stage.current); faceRef.current = f;
        await wear(faceId); if (dead) return; setReady(true);
        io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(es => { if (es[0].isIntersecting) f.view.start(); else f.view.stop(); }) : null; io?.observe(stage.current);
      } catch (e) { if (!dead) setFail(e?.message?.includes('WebGL') ? 'This browser has no WebGL, so characters cannot move here.' : 'The character could not load.'); }
    })();
    return () => { dead = true; io?.disconnect(); try { recorder.current?.stop(); } catch { /* it had stopped */ } socket.current?.close(); trackStop.current?.(); camStop.current?.(); camStream.current?.getTracks().forEach(t => t.stop()); micStop.current?.(); mic.current?.getTracks().forEach(t => t.stop()); faceRef.current?.destroy(); faceRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pick = async id => {
    setErr(''); const before = face; setFace(id);
    try { await wear(id); if (mine && work && id !== 'custom') { const j = await work(cat.id, { op: 'face', text: id }); setD?.(x => (x ? { ...x, face: j.face } : x)); } } catch (e) { setFace(before); setErr(e.message); }
  };
  const picture = async file => {
    setBusy(true); setErr('');
    try {
      const sdk = sdkRef.current; const { createCharacter } = await loadCreate(); const paths = mediapipePaths();
      const ch = await createCharacter(file, { kind: '2d', detector: 'local', mediapipe: { bundle: paths.bundle, wasm: paths.wasm, model: paths.model } });
      await faceRef.current.useCharacter(ch);
      const blob = await sdk.exportCharacter(ch); const a = agentAuth();
      const img = await createImageBitmap(file); const cv = document.createElement('canvas'); const side = Math.min(img.width, img.height); cv.width = 256; cv.height = 256; cv.getContext('2d').drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, 256, 256);
      const r = await fetch(apiUrl(`/api/cats/${cat.id}/face`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session: a.session, ownerId: a.ownerId, thumb: cv.toDataURL('image/jpeg', 0.85), character: await blob.text() }) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'It could not be saved.');
      setFace('custom'); setD?.(x => (x ? { ...x, face: { id: 'custom' } } : x));
    } catch (e) { setErr(/face_not_found|no.*face/i.test(`${e.code || ''} ${e.message}`) ? 'No face found. Use a clear photo, facing you, with the mouth closed.' : e.message); await wear(faceId).catch(() => {}); } finally { setBusy(false); }
  };
  const ctx = () => { if (!audio.current) audio.current = new (window.AudioContext || window.webkitAudioContext)(); audio.current.resume?.(); return audio.current; };
  const toggleCam = async () => {
    setErr('');
    if (camOn) { camStop.current?.(); camStop.current = null; camStream.current?.getTracks().forEach(t => t.stop()); camStream.current = null; setCamOn(false); return; }
    try {
      setStatus('Starting…'); const s = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' }, audio: false }); camStream.current = s; setCamOn(true);
      const v = videoRef.current; v.srcObject = s; await v.play();
      camStop.current = await startTracker(v, faceRef.current, sdkRef.current, seen => setStatus(seen ? 'Tracking your face' : 'Looking for your face'));
    } catch (e) { camStream.current?.getTracks().forEach(t => t.stop()); camStream.current = null; setCamOn(false); setStatus(''); setErr(e.name === 'NotAllowedError' ? 'The browser blocked the camera. Allow it in the address bar, then try again.' : 'The camera could not start.'); }
  };
  const toggleMic = async () => {
    setErr('');
    if (micOn) { micStop.current?.(); mic.current?.getTracks().forEach(t => t.stop()); mic.current = null; setMicOn(false); return; }
    try { const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); mic.current = s; micStop.current = faceRef.current.listenTo(ctx(), s); setMicOn(true); } catch (e) { setErr(e.name === 'NotAllowedError' ? 'The browser blocked the mic. Allow it in the address bar, then try again.' : 'The mic could not start.'); }
  };
  useEffect(() => { if (!live) return undefined; const start = Date.now(); const t = setInterval(() => setSecs(Math.floor((Date.now() - start) / 1000)), 1000); return () => clearInterval(t); }, [live]);
  const endLive = useCallback(why => { try { recorder.current?.stop(); } catch { /* it had stopped */ } recorder.current = null; trackStop.current?.(); trackStop.current = null; const ws = socket.current; socket.current = null; ws?.close(); setLive(false); setSecs(0); if (why) setLiveErr(why); }, []);
  const goLive = platforms => {
    if (live) { endLive(); return; }
    setLiveErr(''); const type = pickRecorderType();
    if (!type) { setLiveErr('This browser cannot stream. Use Chrome or Edge.'); return; }
    const { tracks, stop } = streamTracks(scene?.canvas || stage.current, mic.current, ctx()); trackStop.current = stop;
    const url = new URL(apiUrl(`/api/cats/${cat.id}/stream`), window.location.href); url.protocol = url.protocol.replace('http', 'ws');
    const ws = new WebSocket(url); socket.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ session: agentAuth().session, platforms }));
    ws.onmessage = e => { let m = {}; try { m = JSON.parse(e.data); } catch { return; }
      if (m.on) { const rec = new MediaRecorder(new MediaStream(tracks), { mimeType: type, videoBitsPerSecond: 2500000, audioBitsPerSecond: 128000 }); rec.ondataavailable = x => { if (x.data.size && ws.readyState === 1) ws.send(x.data); }; rec.start(1000); recorder.current = rec; setLive(true); } else if (m.why) endLive(m.why); };
    ws.onerror = () => endLive('The stream could not connect.');
    ws.onclose = e => { if (socket.current === ws) endLive(e.reason || (e.code === 1000 ? '' : 'The stream stopped.')); };
  };
  const popOut = async () => { const w = await window.documentPictureInPicture.requestWindow({ width: 340, height: 420 }); [...document.styleSheets].forEach(s => { try { w.document.head.append(s.ownerNode.cloneNode(true)); } catch { /* one it can't copy */ } }); w.addEventListener('pagehide', () => setPip(null)); setPip(w); const v = w.document.createElement('video'); v.className = 'chr-pip-v'; v.muted = true; v.autoplay = true; v.srcObject = (scene?.canvas || stage.current).captureStream(30); w.document.body.append(v); const end = w.document.createElement('button'); end.className = 'm-btn'; end.textContent = 'Close'; end.onclick = () => w.close(); w.document.body.append(end); };
  useEffect(() => () => pip?.close?.(), [pip]);
  const saveName = async () => { setNameMsg(''); try { const j = await work(cat.id, { op: 'rename', text: name }); setD?.(x => (x ? { ...x, name: j.name } : x)); setNameMsg('Saved. It can change again in 7 days.'); } catch (e) { setNameMsg(e.message); } };
  const say = (m) => { setMood(m); faceRef.current?.express(m, 3); };
  const shown = ALL_CHARACTERS.find(c => c[0] === faceId);

  return <div className={`chr${live ? ' is-live' : ''}`} data-testid="dsk-character">
    <section className="chr-stage">
      <div className="chr-screen"><canvas ref={stage} aria-label={`${cat?.name || 'Agent'} as a live character`} data-testid="chr-canvas" /><i className="chr-scan" aria-hidden="true" />
        <span className="chr-tag"><b>{shown ? shown[1] : 'Yours'}</b><em>{shown ? shown[2] : 'Picture'}</em></span>
        {live ? <span className="chr-air"><i aria-hidden="true" />ON AIR {clock(secs)}</span> : null}
        {!ready && !fail ? <span className="chr-wait">Waking it up…</span> : null}{fail ? <span className="chr-wait" role="alert">{fail}</span> : null}
        <video ref={videoRef} className="chr-cam" playsInline muted aria-hidden="true" /></div>
      <div className="m-seg chr-moods" role="group" aria-label="Expression">{MOODS.map(([k, l]) => <button key={k} type="button" className={mood === k ? 'active' : ''} onClick={() => say(k)} disabled={!ready} data-tip={`Show ${l.toLowerCase()}`} data-testid={`chr-mood-${k}`}>{l}</button>)}</div>
    </section>
    <section className="chr-side">
      <h3 className="chr-h"><Ic3 e="🎭" size="24px" /> {cat?.name || 'Agent'}</h3>
      {mine ? <div className="chr-name"><input className="m-input" maxLength={32} value={name} onChange={e => setName(e.target.value)} aria-label="Agent name" disabled={!!cat?.nameLeftS} data-testid="chr-name" /><button type="button" className="m-btn" onClick={saveName} disabled={!!cat?.nameLeftS || name.trim() === cat?.name || name.trim().length < 2} data-tip="A name can change once every 7 days">{cat?.nameLeftS ? `In ${nameWait(cat.nameLeftS)}` : 'Rename'}</button>{nameMsg ? <small className="chr-note" role="status">{nameMsg}</small> : null}</div> : null}
      {mine ? <div className="m-seg chr-tabs" role="tablist">{TABS.map(([k, ic, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`chr-tab-${k}`}><Ic3 e={ic} /> {l}</button>)}</div> : null}
      {tab === 'pick' || !mine ? <PickTab cat={cat} face={face} onPick={mine ? pick : (id => wear(id))} onPicture={picture} busy={busy} err={err} mine={mine} /> : null}
      {tab === 'me' && mine ? <MeTab camOn={camOn} micOn={micOn} onCam={toggleCam} onMic={toggleMic} status={status} err={err} /> : null}
      {tab === 'live' && mine ? <LiveTab cat={cat} keys={keys} setKeys={setKeys} work={work} live={live} secs={secs} onLive={goLive} onPop={popOut} err={liveErr} scene={scene} opts={opts} setOpts={setOpts} /> : null}
    </section>
  </div>;
}

import React, { useEffect, useMemo, useState } from 'react';
import { Bubble } from './LaunchCat';
import { asModel } from './AgentLive';
import '../../styles/catCockpit.css';

// 🛸 THE AGENT COCKPIT (owner, 2026-10-30: "skinny chat — not wide — with model vitals on each side, under that a realtime degen categorised log
// with folders… bg options that are clean + calming, pick the card colour instead of purple"). Under the two live windows:
//   [ MIND A vitals ] [ the chat: bubbles, A left · B right · you ] [ MIND B vitals ]  →  📁 the log, one folder per kind of thing it did.
// Desk skins are DRAWN scenes (ocean · forest · mountains · aurora): zero MB, no video to download, they stop under fx-lite / reduced motion.
export const SCENES = [['night', '🌌', 'Night'], ['ocean', '🌊', 'Ocean'], ['forest', '🌲', 'Forest'], ['peaks', '🏔', 'Mountains'], ['aurora', '✨', 'Aurora']];
export const ACCENTS = ['#b388ff', '#9dffcf', '#45e486', '#7fd3ff', '#f5c542', '#ff5dbb'];
const SKIN_KEY = 'feeless.deskSkin';
export function readSkin() {
  try { const s = JSON.parse(localStorage.getItem(SKIN_KEY) || 'null'); return { bg: SCENES.some(x => x[0] === s?.bg) ? s.bg : 'ocean', acc: ACCENTS.includes(s?.acc) ? s.acc : ACCENTS[0] }; }
  catch { return { bg: 'ocean', acc: ACCENTS[0] }; }
}
export function useDeskSkin() {
  const [skin, setSkin] = useState(readSkin);
  const set = patch => setSkin(s => { const n = { ...s, ...patch }; try { localStorage.setItem(SKIN_KEY, JSON.stringify(n)); } catch { /* private window */ } return n; });
  return [skin, set];
}

// 🎥 a REAL calm clip per scene (owner 2026-10-30: "full real free video backdrop"): Mixkit free license, /backdrops/<scene>.mp4 (720p loops, 3–7 MB).
// It plays muted + looped only while the desk is on screen and the tab is visible; fx-lite / reduced motion / a missing file → the drawn scene.
// Cards over it turn to dark GLASS (no backdrop blur over a moving layer — a scrim + near-opaque glass keeps every colour readable).
export const VIDEO = { ocean: 'Sun reflections and gentle waves', forest: 'Sun beams through the forest trees', peaks: 'Fog on the heights of the snowy mountains', aurora: 'Northern Lights, blue and green' };
function SceneVideo({ bg, onFail }) {
  const ref = React.useRef(null);
  useEffect(() => { const v = ref.current; if (!v) return undefined;
    const still = document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const pause = () => { try { v.pause(); } catch { /* no media engine (tests) */ } };
    if (still) { pause(); return undefined; }
    let seen = true; const sync = () => { if (seen && !document.hidden) { try { Promise.resolve(v.play?.()).catch(() => {}); } catch { /* autoplay blocked */ } } else pause(); };
    const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(([e]) => { seen = e.isIntersecting; sync(); }) : null;
    io?.observe(v); document.addEventListener('visibilitychange', sync); sync();
    return () => { io?.disconnect(); document.removeEventListener('visibilitychange', sync); };
  }, [bg]);
  return <video ref={ref} className="ckb-video" src={`/backdrops/${bg}.mp4`} muted loop playsInline preload="metadata" onError={onFail} aria-hidden="true" data-testid="desk-video" />;
}
export function DeskBackdrop({ bg }) {
  const [fail, setFail] = useState(false);
  useEffect(() => setFail(false), [bg]);
  if (bg === 'night') return <i className="ckb ckb-night" aria-hidden="true" />;
  if (VIDEO[bg] && !fail) return <div className={`ckb ckb-${bg} is-video`} aria-hidden="true"><SceneVideo bg={bg} onFail={() => setFail(true)} /><i className="ckb-scrim" /></div>;
  return <div className={`ckb ckb-${bg}`} aria-hidden="true">
    {bg === 'ocean' ? <><i className="ckb-sun" /><i className="ckb-wave w1" /><i className="ckb-wave w2" /><i className="ckb-wave w3" /></> : null}
    {bg === 'forest' ? <><i className="ckb-mist" /><i className="ckb-trees t1" /><i className="ckb-trees t2" /><i className="ckb-fly" /></> : null}
    {bg === 'peaks' ? <><i className="ckb-cloud c1" /><i className="ckb-cloud c2" /><i className="ckb-peak p1" /><i className="ckb-peak p2" /></> : null}
    {bg === 'aurora' ? <><i className="ckb-band b1" /><i className="ckb-band b2" /><i className="ckb-stars" /></> : null}
  </div>;
}

export function SkinPicker({ skin, set }) {
  return <details className="ck-skin" data-testid="desk-skin"><summary data-tip="Your desk's backdrop + card colour (saved in this browser)"><i style={{ background: skin.acc }} aria-hidden="true" />🎨 DESK</summary>
    <div className="ck-skin-pop">
      <span className="ck-skin-row">{SCENES.map(([k, ic, l]) => <button key={k} type="button" className={skin.bg === k ? 'is-on' : ''} onClick={() => set({ bg: k })} aria-pressed={skin.bg === k} data-testid={`skin-${k}`} data-tip={`${l} backdrop`}><b aria-hidden="true">{ic}</b><small>{l}</small></button>)}</span>
      <span className="ck-skin-row is-dots">{ACCENTS.map(c => <button key={c} type="button" className={skin.acc === c ? 'is-on' : ''} style={{ '--d': c }} onClick={() => set({ acc: c })} aria-pressed={skin.acc === c} aria-label={`Card colour ${c}`} data-testid={`acc-${c}`}><i /></button>)}</span>
    </div></details>;
}

const ago = s => { const d = Math.max(0, Math.round(Date.now() / 1000 - (s > 1e12 ? s / 1000 : s))); return d < 60 ? `${d}s` : d < 3600 ? `${Math.round(d / 60)}m` : d < 86400 ? `${Math.round(d / 3600)}h` : `${Math.round(d / 86400)}d`; };
const WORD_TONE = { BUY: 'up', SELL: 'dn', TRIM: 'warn', HOLD: 'mute', SKIP: 'mute', RULES: 'mute' };

// pure: one mind's live vitals from its own decisions (trading) — calls, buys, how often both agreed, $ spent, its last 12 words
export function mindStats(cat, model) {
  const b = cat?.brainsCfg || {}; const short = String(model || '').split('/').pop();
  const mine = (b.decisions || []).filter(x => String(x.by || '').includes(short));
  const agreed = (b.cloud || []).filter(c => (c.by || []).some(x => String(x).includes(short) || x === 'both')).length;
  return { calls: mine.length, buys: mine.filter(x => x.word === 'BUY').length, agreed, usd: mine.reduce((s, x) => s + (Number(x.usd) || 0), 0),
    last: mine[mine.length - 1] || null, spark: mine.slice(-12).map(x => WORD_TONE[x.word] || 'mute') };
}

export function MindVitals({ cat, model, i = 0, kind = 'trading', live, extra }) {
  const s = useMemo(() => mindStats(cat, model), [cat, model]); const m = asModel(model);
  return <aside className={`ck-vitals m${i}${model ? '' : ' is-empty'}`} data-testid={`ck-vitals-${i}`}>
    <span className="ck-v-head"><Bubble m={m} i={i} kind={kind} thoughts={s.last ? [`${s.last.word} $${s.last.sym}`] : undefined} size={52} live={!!live && !!model} />
      <span><em>{kind === 'general' ? 'MIND' : 'BRAIN'} {'AB'[i]}</em><b>{m?.name || (i ? 'no second model' : 'its model')}</b></span></span>
    {extra || <>
      <span className="ck-v-row"><em>CALLS</em><b className="m-num" key={s.calls}>{s.calls}</b></span>
      <span className="ck-v-row"><em>BUYS</em><b className="m-num">{s.buys}</b></span>
      <span className="ck-v-row"><em>BOTH AGREED</em><b className="m-num">{s.agreed}</b></span>
      <span className="ck-v-row"><em>SPENT</em><b className="m-num">${s.usd.toFixed(4)}</b></span>
      <span className="ck-spark" data-tip="Its last 12 calls: green buy · red sell · gold trim · grey wait">{s.spark.map((t, j) => <i key={j} className={`is-${t}`} style={{ '--j': j }} />)}</span>
      {s.last ? <p className="ck-v-last"><b className={`is-${WORD_TONE[s.last.word] || 'mute'}`}>{s.last.word}</b> ${s.last.sym} · {ago(s.last.at)} ago<small>{s.last.why}</small></p> : <p className="ck-v-last">no call yet</p>}
    </>}
  </aside>;
}

// pure: a trading cat's conversation — each brain's calls as its own bubble (A left · B right), your chime-ins on the right
export function tradeChat(cat) {
  const b = cat?.brainsCfg || {}; const brains = (b.brains || []).map(x => String(x).split('/').pop());
  const calls = (b.decisions || []).slice(-24).map(x => ({ at: x.at, side: brains.findIndex(n => String(x.by || '').includes(n)) === 1 ? 'b' : 'a', who: x.by, word: x.word, sym: x.sym, text: x.why }));
  const you = (b.chime || []).slice(-8).map(x => ({ at: x.at, side: 'you', who: 'You', text: x.text }));
  return [...calls, ...you].sort((p, q) => (p.at || 0) - (q.at || 0)).slice(-24);
}

export function TradeChat({ cat, onSend, busy }) {
  const rows = useMemo(() => tradeChat(cat), [cat]); const [t, setT] = useState('');
  return <div className="ck-chat" data-testid="ck-chat">
    <ol className="ck-msgs" aria-live="polite">{rows.length ? rows.map((r, i) => <li key={`${r.at}-${i}`} className={`ck-msg is-${r.side}`} style={{ '--i': Math.min(i, 8) }}>
      <span className="ck-msg-h"><b>{r.who}</b>{r.word ? <em className={`is-${WORD_TONE[r.word] || 'mute'}`}>{r.word}{r.sym ? ` $${r.sym}` : ''}</em> : null}<small>{r.at ? `${ago(r.at)}` : ''}</small></span>
      {r.text ? <p>{r.text}</p> : null}</li>) : <li className="ck-empty">Its first call lands here — both brains talk in bubbles, you chime in below.</li>}</ol>
    <form className="ck-say" onSubmit={async e => { e.preventDefault(); if (t.trim() && await onSend?.(t.trim())) setT(''); }}>
      <input className="m-input" maxLength={280} value={t} onChange={e => setT(e.target.value)} placeholder="Chime in — advice both brains read, never an order" data-testid="ck-chime" />
      <button type="submit" className="m-btn m-go" disabled={busy || !t.trim()}>Send</button></form>
  </div>;
}

// 📁 the log: one folder per kind of thing it did, newest first, live (the desk re-reads every few seconds)
export const FOLDERS = { trades: ['💸', 'Trades'], thoughts: ['🧠', 'Thoughts'], tasks: ['🧭', 'Tasks'], files: ['📄', 'Files'], cloud: ['☁', 'Cloud'], guards: ['🛡', 'Guards'] };
export function catLogItems(cat, events = []) {
  const b = cat?.brainsCfg || {};
  return [
    ...events.filter(e => ['BUY', 'SELL'].includes(e.type)).map(e => ({ f: 'trades', at: (e.ts || 0) / 1000, text: e.detail, tone: e.type === 'BUY' ? 'up' : (Number(e.pnlSol) < 0 ? 'dn' : 'up') })),
    ...events.filter(e => ['STOPPED', 'BLOCKED', 'REFUSED'].includes(e.type)).map(e => ({ f: 'guards', at: (e.ts || 0) / 1000, text: e.detail, tone: 'warn' })),
    ...(b.decisions || []).map(x => ({ f: 'thoughts', at: x.at, text: `${x.by}: ${x.word} $${x.sym}${x.why ? ` — ${x.why}` : ''}`, tone: WORD_TONE[x.word] || 'mute' })),
    ...(b.cloud || []).map(c => ({ f: 'cloud', at: c.at, text: c.text || `both agree: ${c.word} $${c.sym}${c.why ? ` — ${c.why}` : ''}`, tone: 'acc' })),
    ...(cat?.orders || []).map(o => ({ f: 'tasks', at: (o.at || 0) > 1e12 ? o.at / 1000 : o.at, text: `${o.text} → ${o.why || o.state}`, tone: o.state === 'refused' ? 'warn' : 'mute' })),
  ].filter(x => x.text).sort((p, q) => (q.at || 0) - (p.at || 0));
}
export function AgentLog({ items = [], title = 'ITS LOG' }) {
  const [f, setF] = useState('all');
  const counts = useMemo(() => items.reduce((m, x) => ({ ...m, [x.f]: (m[x.f] || 0) + 1 }), {}), [items]);
  const rows = (f === 'all' ? items : items.filter(x => x.f === f)).slice(0, 40);
  return <section className="ck-log" data-testid="agent-log">
    <header><b>📁 {title}</b><small>live · newest first</small></header>
    <nav className="ck-folders" role="tablist" aria-label="Log folders">{[['all', ['🗂', 'All']], ...Object.entries(FOLDERS).filter(([k]) => counts[k])].map(([k, [ic, l]]) =>
      <button key={k} type="button" role="tab" aria-selected={f === k} className={f === k ? 'is-on' : ''} onClick={() => setF(k)} data-testid={`log-${k}`}>
        <i aria-hidden="true">{ic}</i>{l}<b className="m-num">{k === 'all' ? items.length : counts[k]}</b></button>)}</nav>
    <ol className="ck-rows">{rows.length ? rows.map((x, i) => <li key={`${x.f}-${x.at}-${i}`} className={`is-${x.tone || 'mute'}`} style={{ '--i': Math.min(i, 10) }}>
      <i aria-hidden="true">{FOLDERS[x.f]?.[0]}</i><span>{x.text}</span><small>{x.at ? ago(x.at) : ''}</small></li>) : <li className="ck-empty">Nothing here yet.</li>}</ol>
  </section>;
}

// the live events a trading cat's log needs (one read per 10 s, paused while the tab is hidden)
export function useCatEvents(catId) {
  const [ev, setEv] = useState([]);
  useEffect(() => { if (!catId) return undefined; let on = true;
    const go = () => { if (document.hidden) return; fetch(`/api/cats/activity?catId=${encodeURIComponent(catId)}`).then(r => (r.ok ? r.json() : null)).then(d => { if (on && d) setEv(d.events || []); }).catch(() => {}); };
    go(); const t = setInterval(go, 10000); return () => { on = false; clearInterval(t); }; }, [catId]);
  return ev;
}

import React, { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { MindVitals, AgentLog } from './CatCockpit';
import '../../styles/catWorkbench.css';
import { agentAuth, agentAuthQuery } from '../../lib/chatSession';

// 🧠🧠 THE GENERAL CAT'S WORKBENCH (owner 2026-10-29, P2 — backend cat_agent.py + cat_browser.py). Two browser windows, one per model, running in
// the cloud (Steel → Browserbase → the reader: never on this device). Each window: its model, its provider, the page it is on, a bubble top-right
// with what it is doing right now, and — when a sign-in / sign-up / CAPTCHA needs a person — a centred ✋ card (you act in the live window, then
// CONTINUE). Under them ONE chat: Enter → a fast answer from memory, or both models research their halves and merge. The $ bars: the cat's credit
// left and THIS task's spend against its cap (you set it; the task stops at it). Live views run only while on screen; polling pauses when hidden.
const CAPS = [0.02, 0.05, 0.25, 1];
const PROV = { steel: ['STEEL', 'is-steel'], browserless: ['BROWSERLESS', 'is-bl'], browserbase: ['BROWSERBASE', 'is-bb'], reader: ['READER', 'is-reader'] };
const usd = v => (v == null ? '—' : `$${Number(v) < 1 ? Number(v).toFixed(4) : Number(v).toFixed(2)}`);
const LIVE_STATES = ['planning', 'working', 'merging'];
const PriceChart = lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
// 🧭 its two ways (cat_agent.MODES): plan together → one answer · each mind its own job
const WAYS = [['plan', '🧠🤝 ONE ANSWER', 'They plan it in a sentence each, split it, research in their own windows, merge into one answer'], ['jobs', '🎯🎯 TWO JOBS', 'Give each mind its own job — both run at once, two results']];

async function work(id, body) {
  const r = await fetch(apiUrl(`/api/cats/${id}/work`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), ...body }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
  return j;
}

function useOnScreen(ref) {
  const [on, setOn] = useState(true);
  useEffect(() => { const el = ref.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => setOn(e.isIntersecting), { threshold: 0.05 }); io.observe(el); return () => io.disconnect(); }, [ref]);
  return on;
}

function Window({ w, catId, tick, onGo, onLogin, busy }) {
  const ref = useRef(null); const seen = useOnScreen(ref);
  const [p, pcls] = PROV[w?.provider] || ['…', ''];
  const human = w?.status === 'human' && w?.human;
  return <article ref={ref} className={`cwb-win s-${w?.status || 'idle'}`} data-testid={`cwb-win-${w?.i ?? 0}`}>
    <header className="cwb-bar"><i className={`cwb-dots ${w?.status === 'working' ? 'is-go' : w?.status === 'human' ? 'is-wait' : 'is-stop'}`} aria-hidden="true" data-tip="red = idle · yellow = needs you · green = working"><b /><b /><b /></i>
      <span className="cwb-model" data-tip={w?.goal ? `Its half: ${w.goal}` : 'Waiting for the plan'}>{w?.model ? String(w.model).split('/').pop() : 'model'}</span>
      <em className={`cwb-prov ${pcls}`} data-tip={w?.note || (w?.provider === 'reader' ? 'No live browser right now — it reads pages as text so it keeps working' : 'A browser in the cloud — nothing runs on your device')}>{p}</em>
      <span className="cwb-url" title={w?.url || ''}>{w?.url || 'about:blank'}</span></header>
    <div className="cwb-view">
      {w?.coin?.pair && seen ? <div className="cwb-chart" data-testid="cwb-chart"><Suspense fallback={<span className="cwb-chart-load">loading ${w.coin.symbol} on FEELESS…</span>}>
        <PriceChart key={w.coin.pair} pair={{ chainId: 'solana', pairAddress: w.coin.pair, baseToken: { address: w.coin.mint, symbol: w.coin.symbol } }} interval="1m" metric="price" showVolume={false} /></Suspense>
        <em className="cwb-chart-tag">FEELESS · ${w.coin.symbol}</em></div>
        : w?.live && seen ? <iframe className="cwb-live" src={w.live} title={`${w.model} browser`} sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allow="clipboard-read; clipboard-write" data-testid="cwb-live" />
        : w?.shot && seen ? <img className="cwb-shot" src={apiUrl(`/api/cats/${catId}/work/shot/${w.i}?${agentAuthQuery()}&t=${tick}`)} alt={`${w.model} window`} data-testid="cwb-shot" />
          : <ol className="cwb-steps" data-testid="cwb-steps">{(w?.steps || []).length ? w.steps.map((s, i) => <li key={i} style={{ '--i': i }}><b>{s.action}</b><span>{s.thought}</span>{s.detail ? <small>{s.detail}</small> : null}</li>)
            : <li className="cwb-idle"><span>{w?.status === 'done' ? (w?.answer ? 'done — its answer is in the chat' : 'done') : 'ready — ask below'}</span></li>}</ol>}
      {w?.bubble && w?.status !== 'idle' ? <p className="cwb-bubble" key={w.bubble} data-testid="cwb-bubble"><i aria-hidden="true" />{w.bubble}</p> : null}
      {human && w.human.kind === 'login' ? <form className="cwb-human cwb-login" role="dialog" aria-label={`Log in to ${w.human.site}`} data-testid="cwb-login" autoComplete="off"
        onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); onLogin?.(w.i, String(f.get('u') || ''), String(f.get('p') || '')); e.currentTarget.reset(); }}>
        <b>🔑 log in to {w.human.site}</b><small>Type it here — it's sealed for you and typed into its window. The AI models never see it.</small>
        <input className="m-input" name="u" autoComplete="off" placeholder="username or email" aria-label="Username" data-testid="cwb-login-user" />
        <input className="m-input" name="p" type="password" autoComplete="new-password" placeholder="password" aria-label="Password" data-testid="cwb-login-pass" />
        <span><button type="submit" className="m-btn m-go" disabled={busy} data-testid="cwb-login-go">Log it in</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)}>Stop</button></span></form>
      : human ? <div className="cwb-human" role="alertdialog" aria-label="A person is needed" data-testid="cwb-human"><b>✋ needs you</b><small>{w.human.why}</small>
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onGo('continue', w.i)} data-testid="cwb-continue">I did it — continue</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)} data-testid="cwb-stopwin">Stop</button></span></div> : null}
    </div>
    <footer className="cwb-foot"><span className={`cwb-st s-${w?.status || 'idle'}`}><i aria-hidden="true" />{(w?.status || 'idle').toUpperCase()}</span><small className="m-num">{usd(w?.cost || 0)}</small></footer>
  </article>;
}

// 🧠 a general mind's vitals beside the chat: what its window is doing right now (owner 2026-10-30: "model vitals on each side")
function GenVitals({ cat, w, i, live, cloud = [] }) {
  return <MindVitals cat={cat} model={w?.model} i={i} kind="general" live={live && w?.status === 'working'} extra={<>
    <span className="ck-v-row"><em>STATUS</em><b>{String(w?.status || 'idle').toUpperCase()}</b></span>
    <span className="ck-v-row"><em>STEPS</em><b className="m-num" key={(w?.steps || []).length}>{(w?.steps || []).length}</b></span>
    <span className="ck-v-row"><em>SCRATCH</em><b className="m-num">{w?.scratch ?? w?.scratchN ?? 0}</b></span>
    <span className="ck-v-row" data-tip="Its own cloud: the best notes this mind kept from its tasks — it reads them before the next one"><em>☁ ITS CLOUD</em><b className="m-num">{cloud.length}</b></span>
    <span className="ck-v-row"><em>SPENT</em><b className="m-num">{usd(w?.cost || 0)}</b></span>
    {cloud.length ? <p className="ck-v-last"><small>☁ {cloud[cloud.length - 1].text}</small></p> : null}
    <p className="ck-v-last">{w?.coin ? <b className="is-up">on ${w.coin.symbol}</b> : null}{w?.bubble || 'waiting for your ask'}{w?.goal ? <small>its job: {w.goal}</small> : null}</p></>} />;
}
// pure: the general cat's log — your asks + answers (tasks), each window's steps (thoughts), its files, the cloud, every refusal (guards)
export function genLog(d) {
  const now = Date.now() / 1000;
  return [...(d?.chat || []).map(m => ({ f: 'tasks', at: m.at, text: `${m.by === 'you' ? 'You' : '🧠🧠'}: ${m.text}`, tone: m.by === 'you' ? 'acc' : 'up' })),
    ...(d?.windows || []).flatMap(w => (w.steps || []).map((s, k) => ({ f: 'thoughts', at: now - ((w.steps.length - k) * 5), text: `${String(w.model || '').split('/').pop()} · ${s.action}: ${s.thought}${s.detail ? ` (${s.detail})` : ''}`, tone: s.action === 'refused' ? 'warn' : s.action === 'handoff' ? 'up' : 'mute' }))),
    ...Object.entries(d?.minds || {}).flatMap(([m, xs]) => xs.map(c => ({ f: 'cloud', at: c.at, text: `☁ ${m.split('/').pop()} · ${c.text}`, tone: 'mute' }))),
    ...(d?.artifacts || []).map(a => ({ f: 'files', at: now, text: `${a.kind}: ${a.title}`, tone: 'acc' })),
    ...(d?.cloud || []).map(c => ({ f: 'cloud', at: c.at, text: c.text || `${c.word} $${c.sym}`, tone: 'acc' })),
    ...(d?.refusals || []).map(r => ({ f: 'guards', at: r.at || now, text: r.why, tone: 'warn' }))].filter(x => x.text).sort((p, q) => (q.at || 0) - (p.at || 0));
}

// 👀 a visitor (from the leaderboard) sees its minds + what both agreed on — its live windows and chat stay private to its owner
export function CatWorkbench({ cat, readOnly = false }) {
  return readOnly ? <PublicMinds cat={cat} /> : <WorkbenchLive cat={cat} />;
}
function PublicMinds({ cat }) {
  const b = cat.brainsCfg || {}; const brains = b.brains || [];
  return <section className="cwb kd-card cwb-public" data-testid="cwb-public">
    <div className="ck-cockpit">{[0, 1].map(i => <MindVitals key={i} cat={cat} model={brains[i]} i={i} kind="general" live={cat.status === 'running'} extra={<p className="ck-v-last">{brains[i] ? 'works in its own cloud browser — private to its owner' : 'no second mind'}</p>} />)}</div>
    <AgentLog title="WHAT BOTH MINDS AGREED ON" items={(b.cloud || []).map(c => ({ f: 'cloud', at: c.at, text: c.text || `${c.word} $${c.sym}`, tone: 'acc' }))} />
  </section>;
}

// 🔐 saved logins (sites it signed up on): passwords stay sealed — a reveal is fetched on demand, shown blurred, clear only on hover / focus, gone in 15 s
// 🙈 stream-safe (owner 2026-10-30: "if a user livestreams their dash and opens the security drawer"): every username + password stays blurred —
// hover does nothing; a click shows ONE, and it blurs itself again in 15 s
function Blurred({ text, label, pw = false }) {
  const [open, setOpen] = useState(false);
  useEffect(() => { if (!open) return undefined; const t = setTimeout(() => setOpen(false), 15000); return () => clearTimeout(t); }, [open]);
  return <button type="button" className={`cwb-pw${pw ? ' is-pw' : ''}${open ? ' is-open' : ''}`} onClick={() => setOpen(o => !o)} aria-label={open ? `Hide the ${label}` : `Show the ${label} (blurred for screen sharing)`} data-tip={open ? 'Tap to hide — hides itself in 15 s' : `Blurred so a stream or screenshot can't read it — tap to show the ${label}`}>{text}</button>;
}
function SavedLogins({ cat, rows }) {
  const [shown, setShown] = useState({});
  const reveal = async r => { const k = `${r.site}|${r.user}`; try { const j = await work(cat.id, { op: 'reveal', text: r.site, job: r.user }); setShown(x => ({ ...x, [k]: j.password }));
    setTimeout(() => setShown(x => { const n = { ...x }; delete n[k]; return n; }), 15000); } catch { /* not yours / gone */ } };
  if (!rows?.length) return null;
  return <details className="cwb-vault" data-testid="cwb-vault"><summary data-tip="Logins it made for you — passwords are sealed on the server; reveal one at a time">🔐 SAVED LOGINS <b className="m-num">{rows.length}</b></summary>
    <ul>{rows.map(r => { const k = `${r.site}|${r.user}`; return <li key={k}><b>{r.site}</b><Blurred text={r.user} label="username" />
      {shown[k] ? <Blurred text={shown[k]} label="password" pw /> : <button type="button" className="m-btn" onClick={() => reveal(r)} data-testid={`cwb-reveal-${r.site}`}>Reveal</button>}</li>; })}</ul></details>;
}
// 🖼 its media drawer: what it saved for a campaign, a slide strip, cleaned after 7 days on its own
function MediaDrawer({ items }) {
  if (!items?.length) return null;
  return <section className="cwb-media" data-testid="cwb-media"><b>🖼 MEDIA <small>{items.length} · cleaned after 7 days</small></b>
    <div className="cwb-media-strip">{items.map(m => <a key={m.url} href={m.url} target="_blank" rel="noopener noreferrer" data-tip={m.title || m.url}>
      {m.kind === 'video' ? <video src={m.url} muted loop playsInline preload="metadata" /> : <img src={m.url} alt={m.title || ''} loading="lazy" />}<small>{m.title || 'untitled'}</small></a>)}</div></section>;
}

// ☁ its own storage (owner 2026-10-31): the + beside the chat puts images / GIFs in the agent's storage (1 GB, cleaned 7 days after last use);
// the attached ones ride with the next ask — the agent reads their names and its live browser can upload one (e.g. a coin image on pump.fun)
const fileMb = n => (n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(1)} GB` : n >= 1024 ** 2 ? `${(n / 1024 ** 2).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const readAsDataUrl = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => no(new Error('That file could not be read.')); r.readAsDataURL(f); });
export async function addFile(catId, file) {
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file?.type || '')) throw new Error('Images only: PNG, JPEG, WebP or GIF.');
  if (file.size > (file.type === 'image/gif' ? 40 : 15) * 1024 * 1024) throw new Error(file.type === 'image/gif' ? 'GIFs up to 40 MB.' : 'Images up to 15 MB.');
  const r = await fetch(apiUrl(`/api/cats/${catId}/files`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), dataUrl: await readAsDataUrl(file), name: file.name }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
  return j;
}
function AttachChips({ files, store, onDrop }) {
  if (!files.length) return null;
  const pct = store ? Math.min(1, store.used / store.quota) : 0;
  return <div className="cwb-files" data-testid="cwb-files">{files.map((f, i) => <span key={f.id} className="cwb-file" style={{ '--i': i }} data-tip={`${f.name} · ${fileMb(f.size)} — goes with your next ask`}>
    <img src={apiUrl(f.url)} alt="" /><b>{f.name}</b><small className="m-num">{fileMb(f.size)}</small>
    <button type="button" onClick={() => onDrop(f.id)} aria-label={`Take ${f.name} off this ask`} data-tip="Take it off this ask (it stays in its storage until cleaned)" data-testid={`cwb-file-x-${f.id}`}>✕</button></span>)}
    {store ? <span className="cwb-store" data-tip={`Its storage: ${fileMb(store.used)} of ${fileMb(store.quota)} — files unused for ${store.ttlDays || 7} days are cleaned`} data-testid="cwb-store">
      <em>☁ STORAGE</em><u aria-hidden="true"><s style={{ transform: `scaleX(${pct})` }} /></u><small className="m-num">{fileMb(store.used)} / {fileMb(store.quota)}</small></span> : null}</div>;
}

function WorkbenchLive({ cat }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [tick, setTick] = useState(0);
  const [files, setFiles] = useState([]); const [store, setStore] = useState(null); const [upping, setUpping] = useState(false); const pick = useRef(null);   // ☁ attached to the next ask
  const attach = async e => { const list = Array.from(e.target.files || []).slice(0, 4); e.target.value = ''; if (!list.length) return; setUpping(true); setErr('');
    try { for (const f of list) { const j = await addFile(cat.id, f); setFiles(x => [...x, j.file].slice(-4)); setStore({ used: j.used, quota: j.quota, ttlDays: j.ttlDays }); } } catch (er) { setErr(er.message); } finally { setUpping(false); } };
  const [to, setTo] = useState('both'); const [jobs, setJobs] = useState(['', '']);   // 🧠 talk to both minds, or ONE of them (it works the whole task in its own window)
  const load = useCallback(() => work(cat.id, { op: 'state' }).then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message)), [cat.id]);
  const status = d?.task?.status;
  const live = LIVE_STATES.includes(status) || status === 'human' || (d?.windows || []).some(w => w.status === 'human' || w.status === 'working');
  useEffect(() => { load(); }, [load]);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) { load(); setTick(x => x + 1); } }, live ? 1500 : 8000); return () => clearInterval(t); }, [load, live]);
  const act = async (op, extra = {}) => { setBusy(true); setErr(''); try { const r = await work(cat.id, { op, ...extra }); setD(x => ({ ...x, ...r })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const go = !!d?.go; const queue = d?.queue || [];   // 🏇 let it go (owner Q1): long tasks, asks queue up and run one after another until a human is needed
  const way = d?.workMode || 'plan';
  const send = e => { e?.preventDefault?.(); if (busy) return;
    if (way === 'jobs' && wins.length > 1) { const [a, b] = jobs.map(x => x.trim()); if (!a && !b) return; setJobs(['', '']); act('ask', { text: [a && `A: ${a}`, b && `B: ${b}`].filter(Boolean).join('\n'), to: 'both' }); return; }   // one job is fine: that mind owns it, the other supports
    const t = text.trim(); if (!t) return; setText(''); const ids = files.map(f => f.id); setFiles([]); act('ask', { text: t, to, ...(ids.length ? { files: ids } : {}) }); };
  const setWay = async k => { setBusy(true); try { await work(cat.id, { op: 'mode', job: k }); await load(); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const wins = d?.windows?.length ? d.windows : (cat.brainsCfg?.brains || ['', '']).slice(0, 8).map((m, i) => ({ i, model: m, status: 'idle' }));
  const credit = Number(d?.credit ?? cat.brainsCfg?.credit ?? 0); const cap = Number(d?.cap ?? 0.05); const spent = Number(d?.task?.cost || 0);
  return <section className="cwb kd-card" data-testid="cat-workbench">
    <header className="cwb-head"><span><b>🧠🧠 ITS MINDS</b><small>{(d?.providers || []).filter(x => x !== 'reader').length ? `browsers in the cloud · ${d.providers.join(' → ')}` : 'reading pages as text (no hosted browser key yet)'}</small></span>
      <button type="button" className={`cwb-go${go ? ' is-on' : ''}`} aria-pressed={go} disabled={busy} onClick={() => act('go', { on: !go })} data-testid="cwb-go"
        data-tip={go ? 'ON: up to 30 steps a window, asks queue and run back to back — it stops only when done, at the $ cap, or for a sign-in / CAPTCHA / card payment' : 'Let it go: it works long tasks on its own and takes queued asks one after another until a person is needed'}>
        <i aria-hidden="true" />🏇 LET IT GO <b>{go ? 'ON' : 'OFF'}</b></button>
      <span className="cwb-meters">
        <span data-tip="Model credit left: every answer and browsing step is paid from it. Add more in its wallet panel"><em>CREDIT</em><b className="m-num">{usd(credit)}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, credit / 10)})` }} /></u></span>
        <span data-tip="This task's spend against its cap — it stops at the cap with what it has"><em>THIS TASK</em><b className="m-num">{usd(spent)} / {usd(cap)}</b><u aria-hidden="true"><s className={spent >= cap * 0.8 ? 'is-hot' : ''} style={{ transform: `scaleX(${Math.min(1, spent / (cap || 1))})` }} /></u></span>
      </span></header>
    <div className="m-seg cwb-way" role="radiogroup" aria-label="How its minds work">{WAYS.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={way === k}
      className={way === k ? 'active' : ''} disabled={live || busy} onClick={() => setWay(k)} data-tip={tip} data-testid={`cwb-way-${k}`}>{l}</button>)}</div>
    {(d?.cloud || []).length ? <div className="cwb-cloud" data-testid="cwb-cloud" data-tip="Its main cloud: the best of both minds' scratch pads, kept for next time"><b>☁ MAIN CLOUD</b>
      {d.cloud.slice(-3).reverse().map((c, i) => <span key={i} style={{ '--i': i }}>{c.text || `${c.word} $${c.sym}`}</span>)}</div> : null}
    <SavedLogins cat={cat} rows={d?.logins} /><MediaDrawer items={d?.media} />
    <details className="cwb-tools"><summary>Job + tool switches</summary><label>Job<select className="m-input" aria-label="Cat job" value={d?.job || 'agent'} disabled={live || busy} onChange={e => act('tools', { job: e.target.value })}>{Object.keys(d?.toolkits || { agent: [] }).map(j => <option key={j}>{j}</option>)}</select></label><div className="m-seg">{Object.entries(d?.tools || {}).map(([k, on]) => <button key={k} type="button" aria-pressed={on} disabled={live || busy} className={on ? 'active' : ''} data-tip={`Allow this cat to use ${k}`} onClick={() => act('tools', { tools: { ...d.tools, [k]: !on } })}>{k} · {on ? 'ON' : 'OFF'}</button>)}</div></details>
    {(d?.artifacts || []).map((a, i) => <details className="cwb-artifact" key={i}><summary>{a.title} · {a.kind}</summary>{a.kind === 'build' ? <iframe title={a.title} sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; connect-src \'none\'; form-action \'none\'; base-uri \'none\'">' + a.content} /> : <pre>{a.content}</pre>}</details>)}
    {(d?.refusals || []).length ? <details className="cwb-refusals"><summary>Refusals · {d.refusals.length}</summary>{d.refusals.map((r, i) => <p key={i}>{r.why}</p>)}</details> : null}
    <div className="cwb-wins">{wins.map(w => <Window key={w.i} w={w} catId={cat.id} tick={tick} busy={busy} onGo={(op, i) => act(op, { i })} onLogin={(i, user, secret) => act('login', { i, user, secret })} />)}</div>
    <div className="ck-cockpit" data-testid="cwb-cockpit">
      <GenVitals cat={cat} w={wins[0]} i={0} live={live} cloud={d?.minds?.[wins[0]?.model] || []} />
      <div className="ck-center cwb-center">
    {d?.task?.answer || status === 'stopped' || status === 'error' ? <p className={`cwb-answer s-${status}`} data-testid="cwb-answer">{d.task.fast ? '⚡ from memory · ' : ''}{d.task.answer || d.task.why}</p> : null}
    <ol className="cwb-chat" aria-label="Chat with its models">{(d?.chat || []).slice(-8).map((m, i) => <li key={i} className={m.by === 'you' ? 'is-you' : 'is-cats'}><b>{m.by === 'you' ? 'You' : '🧠🧠'}</b><span>{m.text}</span>{m.cost != null ? <small className="m-num">{usd(m.cost)}</small> : null}</li>)}</ol>
    {queue.length ? <ol className="cwb-queue" aria-label="Queued asks" data-testid="cwb-queue">{queue.map((q, i) => <li key={i} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{q.text}</span>
      <button type="button" onClick={() => act('unqueue', { i })} aria-label="Drop this ask" data-tip="Drop it from the queue" data-testid={`cwb-unq-${i}`}>✕</button></li>)}</ol> : null}
    {way !== 'jobs' ? <div className="m-seg cwb-to" role="radiogroup" aria-label="Who you are talking to">{[['both', '🧠 ALL MINDS'], ...wins.map(w => [String(w.i), `🧠 ${String(w.model || `mind ${w.i + 1}`).split('/').pop()}`])].map(([k, l]) =>
      <button key={k} type="button" role="radio" aria-checked={to === k} className={to === k ? 'active' : ''} disabled={live} onClick={() => setTo(k)} data-testid={`cwb-to-${k}`}
        data-tip={k === 'both' ? 'Both minds: they split the task, each in its own window, then merge' : 'Only this mind: it takes the whole task in its own window'}>{l}</button>)}</div> : null}
    <AttachChips files={files} store={store} onDrop={id => setFiles(x => x.filter(f => f.id !== id))} />
    <form className="cwb-ask" onSubmit={send}>
      <button type="button" className={`cwb-plus${upping ? ' is-busy' : ''}`} onClick={() => pick.current?.click()} disabled={upping || files.length >= 4} aria-label="Attach images for it"
        data-tip="Attach images or GIFs (up to 4) — they go in its own storage and ride with your next ask; it can upload them to a site, e.g. a coin image" data-testid="cwb-plus"><i aria-hidden="true" /></button>
      <input ref={pick} type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple hidden onChange={attach} data-testid="cwb-file-input" />
      {way === 'jobs' && wins.length > 1 && !live ? <span className="cwb-jobs">{[0, 1].map(i => <label key={i}><em>MIND {'AB'[i]} · {String(wins[i]?.model || '').split('/').pop()}</em>
        <input className="m-input" value={jobs[i]} onChange={e => setJobs(j => (i ? [j[0], e.target.value] : [e.target.value, j[1]]))} placeholder={i ? 'e.g. make 5 posts for X from it' : 'e.g. write a 30 s video script on SOL'} data-testid={`cwb-job-${i}`} aria-label={`Mind ${'AB'[i]} job`} /></label>)}</span> : null}
      <input hidden={way === 'jobs' && wins.length > 1 && !live} className="m-input" value={text} onChange={e => setText(e.target.value)} placeholder={live ? (go ? 'working… type the next ask — it queues' : 'working… stop it to ask again') : 'Ask both — e.g. "find the best YES on Kalshi for US capital this week"'} disabled={live && !go} aria-label="Ask the cat" data-testid="cwb-input" />
      {live && go && text.trim() ? <button type="submit" className="m-btn m-go" disabled={busy} data-testid="cwb-queue-add">＋ Queue ↵</button>
        : live ? <button type="button" className="m-btn" onClick={() => act('stop')} disabled={busy} data-testid="cwb-stop">■ Stop</button>
        : <button type="submit" className="m-btn m-go" disabled={busy || (way === 'jobs' && wins.length > 1 ? !(jobs[0].trim() || jobs[1].trim()) : !text.trim())} data-testid="cwb-send">Send ↵</button>}
      <div className="m-seg cwb-cap" role="radiogroup" aria-label="The most one task may spend">{CAPS.map(c => <button key={c} type="button" role="radio" aria-checked={Math.abs(cap - c) < 1e-9} className={Math.abs(cap - c) < 1e-9 ? 'active' : ''} onClick={() => act('cap', { cap: c })} data-tip={`A task stops at $${c}`} data-testid={`cwb-cap-${c}`}>${c}</button>)}</div>
    </form>
      </div>
      <GenVitals cat={cat} w={wins[1]} i={1} live={live} cloud={d?.minds?.[wins[1]?.model] || []} />
    </div>
    <AgentLog items={genLog(d)} />
    {d && !d.live ? <p className="cwb-note" data-testid="cwb-off">Model calls are switched off on this server — asking sends and charges nothing until the owner turns them on.</p> : null}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </section>;
}

import React, { Suspense, lazy, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { MindVitals, AgentLog } from './CatCockpit';
import '../../styles/catWorkbench.css';
import { agentAuth, agentAuthQuery, revealMessage } from '../../lib/chatSession';
import { useWallet } from '../../hooks/useWallet';
import { useSolPrice } from '../../lib/solPrice';

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
      {human && w.human.kind === 'login' ? <div className="cwb-human cwb-signin" role="alertdialog" aria-label={`Sign in to ${w.human.site}`} data-testid="cwb-login">
        <b>🔑 {w.human.site} needs a sign-in</b><small>It goes in the credentials drawer, sealed — the AI models never see it.</small>
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onLogin?.(w.human.site)} data-tip="Opens the credentials drawer with this site filled in" data-testid="cwb-login-go">Click to sign in</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)}>Stop</button></span></div>
      : human ? <div className="cwb-human" role="alertdialog" aria-label="A person is needed" data-testid="cwb-human"><b>✋ needs you</b><small>{w.human.why}</small>
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onGo('continue', w.i)} data-testid="cwb-continue">I did it — continue</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)} data-testid="cwb-stopwin">Stop</button></span></div> : null}
    </div>
    <footer className="cwb-foot"><span className={`cwb-st s-${w?.status || 'idle'}`}><i aria-hidden="true" />{(w?.status || 'idle').toUpperCase()}</span><small className="m-num">{usd(w?.cost || 0)}</small></footer>
  </article>;
}

// 🧠 a general mind's vitals beside the chat: what its window is doing right now (owner 2026-10-30: "model vitals on each side")
// 🕷→🐱 WHAT IT'S DOING NOW (the crawl idea, our way): one terminal line — its handle › the site its busiest window is on: what it's doing
export function NowLine({ cat, wins, live }) {
  const w = wins.find(x => x.status === 'human') || wins.find(x => x.status === 'working') || wins.find(x => x.url);
  const host = String(w?.url || '').replace(/^https?:\/\//, '').split('/')[0];
  const what = !live || !w ? 'idle — waiting for your ask' : w.status === 'human' ? `waiting on you at ${host}` : `${host ? `on ${host}: ` : ''}${String(w.bubble || w.steps?.at(-1)?.thought || 'thinking').replace(/^✋ needs you: /, '')}`;
  return <p className={`cwb-now${live ? ' is-live' : ''}`} data-testid="cwb-now" aria-live="polite"><b>{cat.handle || 'agent'}</b><i aria-hidden="true">›</i><span key={what}>{what}</span><u aria-hidden="true" /></p>;
}
// 💵 the last money it made — stays until a newer one lands
function LastMoney({ m }) {
  const px = useSolPrice();
  if (m && m.usd == null && m.sol != null && px) m = { ...m, usd: Number(m.sol) * px };
  if (!m) return <div className="cwb-money is-none" data-testid="cwb-money" data-tip="The last money it made shows here until a newer one lands"><em>LAST MONEY MADE</em><b className="m-num">—</b><small>nothing yet</small></div>;
  const up = Number(m.usd ?? m.sol) >= 0;
  return <div className={`cwb-money ${up ? 'is-up' : 'is-dn'}`} key={m.at} data-testid="cwb-money" data-tip={`${m.what || 'trade'} · ${new Date((m.at || 0) * 1000).toLocaleString()}`}><em>LAST MONEY MADE</em>
    <b className="m-num">{m.usd == null ? '…' : `${up ? '+' : '−'}$${Math.abs(Number(m.usd)).toFixed(2)}`}</b><small>{m.sol != null ? `${up ? '+' : ''}${Number(m.sol).toFixed(4)} SOL · ` : ''}{m.what || 'trade'}</small></div>;
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

// 🔐 THE CREDENTIALS DRAWER (owner 2026-10-30): site names only — stream-safe; a click unhides ONE login for 15 s. You add a site's login here
// (a window's 🔑 card opens it with the site filled in), sealed on the server; its windows get it there and type it blind ({{username}} / {{password}}).
// No account yet? Sign up opens the site in a new tab — come back and save it here.
function CredRow({ cat, r, onDrop }) {
  const [pw, setPw] = useState(null); const [why, setWhy] = useState(''); const { signMessage } = useWallet() || {};
  useEffect(() => { if (pw == null) return undefined; const t = setTimeout(() => setPw(null), 15000); return () => clearTimeout(t); }, [pw]);
  const show = async () => { if (pw != null) { setPw(null); return; } setWhy('');   // 🔐 every reveal = its own wallet signature (a stolen session alone shows nothing)
    try { const ts = Math.floor(Date.now() / 1000); const sig = await signMessage(revealMessage(cat.id, r.site, ts)); setPw((await work(cat.id, { op: 'reveal', text: r.site, job: r.user, ts, sig })).password); } catch (e) { setWhy(e.message || 'Not shown'); } };
  return <li data-testid={`cwb-cred-${r.site}`}><b>{r.site}</b>
    {pw != null ? <span className="cwb-cred-open"><span className="cwb-pw is-open">{r.user}</span><span className="cwb-pw is-pw is-open">{pw}</span></span> : null}
    <span className="cwb-cred-acts"><button type="button" className="m-btn" onClick={show} aria-pressed={pw != null} data-tip={pw != null ? 'Hide it now (it hides itself in 15 s)' : 'Sign once with your wallet to unhide this login for 15 s — hidden by default so a stream never shows it'} data-testid={`cwb-reveal-${r.site}`}>{pw != null ? '🙈 Hide' : '👁 Show'}</button>
      <button type="button" className="m-btn cwb-cred-x" onClick={() => onDrop(r)} aria-label={`Forget the ${r.site} login`} data-tip="Forget this login">✕</button></span>{why ? <small className="kd-err" role="alert">⚠ {why}</small> : null}</li>;
}
const VAULT_WORD = { saved: '🔐 saved', used: '🤖 signed in with', revealed: '👁 revealed', forgot: '✕ forgot', 'cloud connected': '☁ connected', 'cloud disconnected': '☁ disconnected' };
function Credentials({ cat, rows, ask, onSaved, log = [] }) {
  const box = useRef(null); const [site, setSite] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { if (!ask?.site) return; setSite(ask.site); if (box.current) { box.current.open = true; box.current.scrollIntoView({ behavior: 'smooth', block: 'center' }); setTimeout(() => box.current?.querySelector('input[name="u"]')?.focus({ preventScroll: true }), 400); } }, [ask]);
  const host = site.trim().toLowerCase().replace(/^https?:\/\//, '').split('/')[0];
  const save = async e => { e.preventDefault(); const f = new FormData(e.currentTarget); const form = e.currentTarget; setErr(''); setBusy(true);
    try { const j = await work(cat.id, { op: 'save_login', text: host, user: String(f.get('u') || ''), secret: String(f.get('p') || '') }); form.reset(); setSite(''); onSaved?.(j.logins); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const drop = async r => { try { onSaved?.((await work(cat.id, { op: 'unlogin', text: r.site, job: r.user })).logins); } catch (er) { setErr(er.message); } };
  return <details ref={box} className="cwb-vault" data-testid="cwb-vault"><summary data-tip="Logins its windows may use — sealed on the server, the AI models never see them">🔐 CREDENTIALS <b className="m-num">{rows?.length || 0}</b></summary>
    {rows?.length ? <ul>{rows.map(r => <CredRow key={`${r.site}|${r.user}`} cat={cat} r={r} onDrop={drop} />)}</ul> : null}
    <form className="cwb-login cwb-cred-add" onSubmit={save} autoComplete="off" data-testid="cwb-cred-add">
      <input className="m-input" name="s" value={site} onChange={e => setSite(e.target.value)} placeholder="site (e.g. dropbox.com)" aria-label="Site" required data-testid="cwb-cred-site" />
      <input className="m-input" name="u" autoComplete="off" placeholder="email or username" aria-label="Email or username" required data-testid="cwb-login-user" />
      <input className="m-input" name="p" type="password" autoComplete="new-password" placeholder="password" aria-label="Password" required data-testid="cwb-login-pass" />
      <span><button type="submit" className="m-btn m-go" disabled={busy || !host} data-testid="cwb-cred-save">{busy ? 'Sealing…' : 'Save sealed'}</button>
        {host ? <a className="m-btn cwb-signup" href={`https://${host}`} target="_blank" rel="noopener noreferrer" data-tip={`No account on ${host}? Sign up in a new tab, then come back and save it here`} data-testid="cwb-signup">No account? Sign up ↗</a> : null}</span>
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</form>
    {log.length ? <ol className="cwb-vlog" data-testid="cwb-vault-log" aria-label="Who used the vault">{log.slice().reverse().slice(0, 6).map((x, i) => <li key={`${x.at}-${i}`} style={{ '--i': i }}><span>{VAULT_WORD[x.what] || x.what}</span><b>{x.site || ''}</b><time className="m-num">{ago(x.at)}</time></li>)}</ol> : null}</details>;
}
const ago = t => { const s = Math.max(0, Date.now() / 1000 - (t || 0)); return s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
// ☁ ITS CLOUD = ITS OWNER'S (owner 2026-10-30: "FEELESS will not fund any storage"): connect your own Google Drive or Dropbox with their own
// sign-in — FEELESS keeps a sealed pass, never the password. The bar is YOUR space left there; its 5 newest files in your FEELESS folder;
// chat attachments (+) wait 24 h on FEELESS for its browser, ☁ keeps one in your cloud.
export function CloudDrawer({ cat, attachments }) {
  const [c, setC] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/cats/${cat.id}/cloud?${agentAuthQuery()}`)).then(r => r.json().then(j => (r.ok ? setC(j) : setErr(j.detail || `HTTP ${r.status}`)))).catch(e => setErr(e.message)), [cat.id]);
  useEffect(() => { load(); }, [load]);
  const post = async (path, body = {}) => { const r = await fetch(apiUrl(`/api/cats/${cat.id}/${path}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), ...body }) });
    const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); return j; };
  const run = async (k, fn) => { setBusy(k); setErr(''); try { await fn(); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  const connect = p => run(p, async () => { window.location.assign((await post('cloud/connect', { provider: p })).url); });
  const link = c?.link; const used = Number(c?.used || 0); const total = Number(c?.total || 0); const files = attachments?.files || [];
  return <details className="cwb-vault cwb-cloudd" open={!link} data-testid="cwb-cloud-drawer"><summary data-tip="Its storage lives in YOUR cloud — FEELESS keeps none">☁ CLOUD {link ? <em className="m-chip ok">{link.label}</em> : <em className="m-chip warn">not connected</em>}</summary>
    {!link ? <div className="cwb-cloud-pick" data-testid="cwb-cloud-pick"><p className="m-note"><b>Connect your own cloud</b>Its files go to a FEELESS folder in your account. You sign in on Google / Dropbox — FEELESS never sees that password.</p>
      {(c?.providers || []).map(p => <button key={p.key} type="button" className={`m-btn${p.ready ? ' m-go' : ''}`} disabled={!p.ready || !!busy} onClick={() => connect(p.key)}
        data-tip={p.ready ? `Sign in to ${p.label} (${p.free}) — opens their page` : `${p.label} isn't set up on FEELESS yet`} data-testid={`cwb-cloud-${p.key}`}>{busy === p.key ? 'Opening…' : `Connect ${p.label}`} <small>{p.ready ? p.free : 'soon'}</small></button>)}</div> : <>
      <div className="cwb-meters cwb-cloud-bar" data-tip={total ? `${fileMb(used)} used of ${fileMb(total)} in your ${link.label}` : 'Your space'}><span><em>{link.label.toUpperCase()}</em>
        <b className="m-num" data-testid="cwb-cloud-left">{total ? `${fileMb(Math.max(0, total - used))} left` : '—'}</b><u aria-hidden="true"><s className={total && used > total * 0.8 ? 'is-hot' : ''} style={{ transform: `scaleX(${total ? Math.min(1, used / total) : 0})` }} /></u></span></div>
      {(c?.recent || []).length ? <div className="cwb-media-strip" data-testid="cwb-cloud-latest">{c.recent.map(f => <a key={f.id} href={f.link} target="_blank" rel="noopener noreferrer" data-tip={`${f.name} · ${fileMb(f.size)} — opens in your ${link.label}`}>
        {f.thumb ? <img src={f.thumb} alt={f.name} loading="lazy" referrerPolicy="no-referrer" /> : <span className="cwb-cloud-ico" aria-hidden="true">📄</span>}<small>{f.name}</small></a>)}</div>
        : <p className="cwb-cloud-empty">Nothing kept yet — ☁ a chat attachment below, or ask it to save something.</p>}
      <button type="button" className="m-btn cwb-cred-x" disabled={!!busy} onClick={() => run('off', async () => { await post('cloud/disconnect'); await load(); })} data-tip="Disconnect — FEELESS forgets the sealed pass">Disconnect</button></>}
    {files.length ? <ul className="cwb-cloud-files" data-testid="cwb-cloud-files" aria-label="Chat attachments (24 h)">{files.map((f, i) => <li key={f.id} style={{ '--i': i }}><span className="cwb-cloud-ico" aria-hidden="true">{f.mime?.startsWith('video/') ? '🎞' : '🖼'}</span>
      <b>{f.name}</b><span className="m-num">{fileMb(f.size)}</span>{link ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => run(f.id, async () => { await post(`files/${f.id}/keep`); await load(); })} data-tip={`Keep it in your ${link.label} (attachments leave FEELESS after 24 h)`} data-testid={`cwb-keep-${f.id}`}>{busy === f.id ? '…' : '☁ Keep'}</button> : <span className="m-chip">24 h</span>}</li>)}</ul> : null}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</details>;
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
    {store ? <span className="cwb-store" data-tip={`Attachments: ${fileMb(store.used)} of ${fileMb(store.quota)} — they leave FEELESS 24 h after last use (☁ Keep one in your own cloud)`} data-testid="cwb-store">
      <em>☁ STORAGE</em><u aria-hidden="true"><s style={{ transform: `scaleX(${pct})` }} /></u><small className="m-num">{fileMb(store.used)} / {fileMb(store.quota)}</small></span> : null}</div>;
}

function WorkbenchLive({ cat }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [tick, setTick] = useState(0);
  const [files, setFiles] = useState([]); const [store, setStore] = useState(null); const [upping, setUpping] = useState(false); const pick = useRef(null);   // ☁ attached to the next ask
  const attach = async e => { const list = Array.from(e.target.files || []).slice(0, 4); e.target.value = ''; if (!list.length) return; setUpping(true); setErr('');
    try { for (const f of list) { const j = await addFile(cat.id, f); setFiles(x => [...x, j.file].slice(-4)); setStore({ used: j.used, quota: j.quota }); } } catch (er) { setErr(er.message); } finally { setUpping(false); } };
  const [signIn, setSignIn] = useState(null);   // 🔑 a window's sign-in card → the credentials drawer, this site filled in
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
  const [gear, setGear] = useState(false); const [logOpen, setLogOpen] = useState(false); const log = useMemo(() => genLog(d), [d]);
  useEffect(() => { if (!gear && !logOpen) return undefined; const k = e => { if (e.key === 'Escape') { setGear(false); setLogOpen(false); } }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [gear, logOpen]);
  const dash = useRef(null);
  useLayoutEffect(() => {   // 🖥 one screen: the windows take what is left under the page's own top (app bar, hero, tabs) — never a page scroll on a laptop
    const fit = () => { const r = dash.current; const st = r?.querySelector('.cwb-stage'); if (!st) return;
      if (window.innerWidth <= 900) { r.style.removeProperty('--cwb-h'); return; }
      const top = st.getBoundingClientRect().top + window.scrollY; r.style.setProperty('--cwb-h', `${Math.round(Math.max(240, Math.min(640, window.innerHeight - top - 84)))}px`); };
    fit(); window.addEventListener('resize', fit); return () => window.removeEventListener('resize', fit);
  }, []);
  return <section ref={dash} className="cwb kd-card cwb-dash" data-testid="cat-workbench">
    <header className="cwb-head"><span><b>🧠🧠 ITS MINDS</b><small>{(d?.providers || []).filter(x => x !== 'reader').length ? `browsers in the cloud · ${d.providers.join(' → ')}` : 'reading pages as text (no hosted browser key yet)'}</small></span>
      <button type="button" className={`cwb-go${go ? ' is-on' : ''}`} aria-pressed={go} disabled={busy} onClick={() => act('go', { on: !go })} data-testid="cwb-go"
        data-tip={go ? 'ON: up to 30 steps a window, asks queue and run back to back — it stops only when done, at the $ cap, or for a sign-in / CAPTCHA / card payment' : 'Let it go: it works long tasks on its own and takes queued asks one after another until a person is needed'}>
        <i aria-hidden="true" />🏇 LET IT GO <b>{go ? 'ON' : 'OFF'}</b></button>
      <button type="button" className="m-btn cwb-logbtn" onClick={() => setLogOpen(true)} aria-haspopup="dialog" data-tip="Its log: your asks, every step, files, cloud notes and guards — newest first" data-testid="cwb-logbtn">📜 LOG <b className="m-num">{log.length}</b></button>
      <span className="cwb-meters">
        <span data-tip="Model credit left: every answer and browsing step is paid from it. Add more in its wallet panel"><em>CREDIT</em><b className="m-num">{usd(credit)}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, credit / 10)})` }} /></u></span>
        <span data-tip="This task's spend against its cap — it stops at the cap with what it has"><em>THIS TASK</em><b className="m-num">{usd(spent)} / {usd(cap)}</b><u aria-hidden="true"><s className={spent >= cap * 0.8 ? 'is-hot' : ''} style={{ transform: `scaleX(${Math.min(1, spent / (cap || 1))})` }} /></u></span>
      </span></header>
    <NowLine cat={cat} wins={wins} live={live} />
    <div className="cwb-stage">
    <div className="cwb-wins">{wins.map(w => <Window key={w.i} w={w} catId={cat.id} tick={tick} busy={busy} onGo={(op, i) => act(op, { i })} onLogin={site => setSignIn({ site, at: Date.now() })} />)}</div>
    <aside className="cwb-rail" aria-label="Its latest">
    <LastMoney m={d?.lastMoney} />
    <div className="cwb-talk" data-testid="cwb-cockpit">
    {d?.task?.answer || status === 'stopped' || status === 'error' ? <p className={`cwb-answer s-${status}`} data-testid="cwb-answer">{d.task.fast ? '⚡ from memory · ' : ''}{d.task.answer || d.task.why}</p> : null}
    <ol className="cwb-chat" aria-label="Chat with its models">{(d?.chat || []).slice(-8).map((m, i) => <li key={i} className={m.by === 'you' ? 'is-you' : 'is-cats'}><b>{m.by === 'you' ? 'You' : '🧠🧠'}</b><span>{m.text}</span>{m.cost != null ? <small className="m-num">{usd(m.cost)}</small> : null}</li>)}</ol>
    {queue.length ? <ol className="cwb-queue" aria-label="Queued asks" data-testid="cwb-queue">{queue.map((q, i) => <li key={i} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{q.text}</span>
      <button type="button" onClick={() => act('unqueue', { i })} aria-label="Drop this ask" data-tip="Drop it from the queue" data-testid={`cwb-unq-${i}`}>✕</button></li>)}</ol> : null}
    <AttachChips files={files} store={store} onDrop={id => setFiles(x => x.filter(f => f.id !== id))} />
    <div className={`cwb-pop${gear ? ' is-open' : ''}`} id="cwb-settings" role="dialog" aria-label="Chat settings" data-testid="cwb-settings" aria-hidden={!gear}>
      <em>HOW ITS MINDS WORK</em>
    <div className="m-seg cwb-way" role="radiogroup" aria-label="How its minds work">{WAYS.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={way === k}
      className={way === k ? 'active' : ''} disabled={live || busy} onClick={() => setWay(k)} data-tip={tip} data-testid={`cwb-way-${k}`}>{l}</button>)}</div>
      <em>WHO YOU TALK TO</em>
    {way !== 'jobs' ? <div className="m-seg cwb-to" role="radiogroup" aria-label="Who you are talking to">{[['both', '🧠 ALL MINDS'], ...wins.map(w => [String(w.i), `🧠 ${String(w.model || `mind ${w.i + 1}`).split('/').pop()}`])].map(([k, l]) =>
      <button key={k} type="button" role="radio" aria-checked={to === k} className={to === k ? 'active' : ''} disabled={live} onClick={() => setTo(k)} data-testid={`cwb-to-${k}`}
        data-tip={k === 'both' ? 'Both minds: they split the task, each in its own window, then merge' : 'Only this mind: it takes the whole task in its own window'}>{l}</button>)}</div> : null}
      <em>MOST A TASK MAY SPEND</em>
    <div className="m-seg cwb-cap" role="radiogroup" aria-label="The most one task may spend">{CAPS.map(c => <button key={c} type="button" role="radio" aria-checked={Math.abs(cap - c) < 1e-9} className={Math.abs(cap - c) < 1e-9 ? 'active' : ''} onClick={() => act('cap', { cap: c })} data-tip={`A task stops at $${c}`} data-testid={`cwb-cap-${c}`}>${c}</button>)}</div>
      <em>JOB + TOOLS</em>
    <div className="cwb-tools"><label>Job<select className="m-input" aria-label="Cat job" value={d?.job || 'agent'} disabled={live || busy} onChange={e => act('tools', { job: e.target.value })}>{Object.keys(d?.toolkits || { agent: [] }).map(j => <option key={j}>{j}</option>)}</select></label><div className="m-seg">{Object.entries(d?.tools || {}).map(([k, on]) => <button key={k} type="button" aria-pressed={on} disabled={live || busy} className={on ? 'active' : ''} data-tip={`Allow this cat to use ${k}`} onClick={() => act('tools', { tools: { ...d.tools, [k]: !on } })}>{k} · {on ? 'ON' : 'OFF'}</button>)}</div></div>
    </div>
    <form className="cwb-ask" onSubmit={send}>
      <button type="button" className={`cwb-plus${upping ? ' is-busy' : ''}`} onClick={() => pick.current?.click()} disabled={upping || files.length >= 4} aria-label="Attach images for it"
        data-tip="Attach images or GIFs (up to 4) — they go in its own storage and ride with your next ask; it can upload them to a site, e.g. a coin image" data-testid="cwb-plus"><i aria-hidden="true" /></button>
      <button type="button" className={`cwb-gear${gear ? ' is-on' : ''}`} aria-expanded={gear} aria-controls="cwb-settings" onClick={() => setGear(g => !g)} aria-label="Chat settings"
        data-tip="Settings: how its minds work, who you talk to, the $ cap, its job + tools" data-testid="cwb-gear"><i aria-hidden="true" /></button>
      <input ref={pick} type="file" accept="image/png,image/jpeg,image/webp,image/gif,video/mp4,video/webm" multiple hidden onChange={attach} data-testid="cwb-file-input" />
      {way === 'jobs' && wins.length > 1 && !live ? <span className="cwb-jobs">{[0, 1].map(i => <label key={i}><em>MIND {'AB'[i]} · {String(wins[i]?.model || '').split('/').pop()}</em>
        <input className="m-input" value={jobs[i]} onChange={e => setJobs(j => (i ? [j[0], e.target.value] : [e.target.value, j[1]]))} placeholder={i ? 'e.g. make 5 posts for X from it' : 'e.g. write a 30 s video script on SOL'} data-testid={`cwb-job-${i}`} aria-label={`Mind ${'AB'[i]} job`} /></label>)}</span> : null}
      <input hidden={way === 'jobs' && wins.length > 1 && !live} className="m-input" value={text} onChange={e => setText(e.target.value)} placeholder={live ? (go ? 'working… type the next ask — it queues' : 'working… stop it to ask again') : 'Ask both — e.g. "find the best YES on Kalshi for US capital this week"'} disabled={live && !go} aria-label="Ask the cat" data-testid="cwb-input" />
      {live && go && text.trim() ? <button type="submit" className="m-btn m-go" disabled={busy} data-testid="cwb-queue-add">＋ Queue ↵</button>
        : live ? <button type="button" className="m-btn" onClick={() => act('stop')} disabled={busy} data-testid="cwb-stop">■ Stop</button>
        : <button type="submit" className="m-btn m-go" disabled={busy || (way === 'jobs' && wins.length > 1 ? !(jobs[0].trim() || jobs[1].trim()) : !text.trim())} data-testid="cwb-send">Send ↵</button>}
    </form>
    </div>
    <div className="cwb-drawers">
    {(d?.cloud || []).length ? <div className="cwb-cloud" data-testid="cwb-cloud" data-tip="Its main cloud: the best of both minds' scratch pads, kept for next time"><b>☁ MAIN CLOUD</b>
      {d.cloud.slice(-3).reverse().map((c, i) => <span key={i} style={{ '--i': i }}>{c.text || `${c.word} $${c.sym}`}</span>)}</div> : null}
    <Credentials cat={cat} rows={d?.logins} log={d?.vaultLog || []} ask={signIn} onSaved={logins => setD(x => ({ ...x, logins }))} />
    <CloudDrawer cat={cat} attachments={d?.storage} /><MediaDrawer items={d?.media} />
    {(d?.artifacts || []).map((a, i) => <details className="cwb-artifact" key={i}><summary>{a.title} · {a.kind}</summary>{a.kind === 'build' ? <iframe title={a.title} sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; connect-src \'none\'; form-action \'none\'; base-uri \'none\'">' + a.content} /> : <pre>{a.content}</pre>}</details>)}
    {(d?.refusals || []).length ? <details className="cwb-refusals"><summary>Refusals · {d.refusals.length}</summary>{d.refusals.map((r, i) => <p key={i}>{r.why}</p>)}</details> : null}
    </div></aside></div>
    {logOpen ? <div className="cwb-logpane" role="dialog" aria-label="Its log" data-testid="cwb-logpane"><button type="button" className="cwb-logshade" aria-label="Close the log" onClick={() => setLogOpen(false)} />
      <div className="cwb-logbody"><button type="button" className="m-btn cwb-logx" onClick={() => setLogOpen(false)} aria-label="Close the log" data-testid="cwb-logx">✕</button><AgentLog items={log} /></div></div> : null}
    {d && !d.live ? <p className="cwb-note" data-testid="cwb-off">Model calls are switched off on this server — asking sends and charges nothing until the owner turns them on.</p> : null}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </section>;
}

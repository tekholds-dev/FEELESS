import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { GameLab } from './GameLab';
import '../../styles/gameDesk.css';

// 🎮 GAME DESK (owner 2026-11-15: "GAME DESK IS FOR ALL USERS … CHOOSE A MODEL AND HAVE AI TRULY CREATE TRUE GTA RP FIVEM STUFF … FIX PORTS … A
// WIREFRAME PLAN … BUILD IT, TEST, AND HAVE IT DOWNLOADABLE … A DUDE THAT BUILDS FIVEM STUFF FROM SCRATCH HAS HIS AI LEARN AND BUILD FOR HIM").
// A folder on every agent's desktop. A project is a target + real files (game_desk.py). STUDIO: its own mind (Mind A or B, the models its owner
// picked) builds, fixes from a pasted error, or plans; every change runs the check. FILES: edit, upload (text opens here, models and textures ride
// into the zip), and "learn my code" so the mind writes like you. PLAN: the wireframe, phase by phase; any step builds in one tap. DISCOVER:
// projects other builders shared (fork one), real CC0 3D models, and the tools each target really uses. TEST: the playtest log and port checks.
const TABS = [['studio', 'Studio'], ['files', 'Files'], ['plan', 'Plan'], ['discover', 'Discover'], ['test', 'Test + port']];
const QUICK = {
  fivem: [['Addon chain', 'build', 'An addon jewelry resource for a custom iced-out chain on the accessories slot: the stream/ folder layout, the fxmanifest and meta that load it, and an INSTALL.md that walks me from a .glb (made in the 3D studio) through Blender + Sollumz to the .ydd and .ytd it needs'],
    ['Garage', 'build', 'A standalone garage: /park stores the car, its plate and mods on the server in a JSON file, /garage pulls it back out at the same spot, every event checked on the server'],
    ['Delivery job', 'build', 'A delivery job: a start blip, a van, five random drop-offs, pay on the server per drop, and checks that stop anyone triggering pay from the client'],
    ['NUI HUD', 'build', 'A clean NUI HUD: health, armor, speed in mph and the street name, that fades out on foot'],
    ['Server plan', 'plan', 'A whole GTA RP server from scratch: framework, core resources, jobs, economy, police and EMS, and launch day']],
  redm: [['Camp', 'build', 'A camp you set up with a command: a tent, a fire and a stash saved per player on the server'], ['Horse whistle', 'build', 'Whistle for your horse with a key: it rides to you from up to 300 m away'], ['Server plan', 'plan', 'A Red Dead RP server from scratch: framework, towns, jobs, law, economy and launch']],
  gtasa_vita: [['Faster cars', 'build', 'Make every sports car about 20% faster with more grip: only the handling.cfg lines to change, with the stock values noted so I can undo it'],
    ['Warm weather', 'build', 'Lock the weather sunny and make the sky warmer at sunset: the timecyc and weather lines to change'],
    ['Smooth traffic', 'build', 'More traffic and people on the streets, tuned so the Vita holds a steady frame rate'],
    ['Crash on load', 'fix', 'The game crashes on the loading screen after I added a car mod'],
    ['Mod plan', 'plan', 'A full mod pack for the Vita port: cars, weather, handling and HUD, installed safely with backups']],
  vita: [['Hello Vita', 'build', 'A Vita homebrew starter in C: a coloured screen with text, touch and button input, and a CMakeLists.txt that makes a .vpk with title id FEEL00001'],
    ['Pong', 'build', 'A Pong for the Vita in C with vita2d: the front touch screen and the D-pad, a score, 60 fps'], ['Port plan', 'plan', 'Port a small open-source SDL2 game to the Vita: what to change, build, test in Vita3K, then on hardware']],
  deck: [['Controls', 'build', 'A Steam Input layout and launch options for a PC game with no controller support: WASD on the left stick, mouse on the right trackpad, gyro aim while a trigger is held'], ['Deck plan', 'plan', 'Make my PC game Steam Deck Verified: controls, text size, 1280x800, battery and suspend']],
  web: [['Arena shooter', 'build', 'A neon top-down arena shooter: twin-stick on touch, WASD and mouse on desktop, waves that get harder, a best score saved'], ['Platformer', 'build', 'A tight pixel platformer: run, jump, wall-jump, coins, three levels and a timer'], ['Game plan', 'plan', 'A browser roguelike from first prototype to launch on a free host']],
};
const TOOLS = {
  fivem: [['FiveM natives', 'https://docs.fivem.net/natives/'], ['Cfx.re docs', 'https://docs.fivem.net/docs/'], ['ox_lib', 'https://overextended.dev/ox_lib'], ['Sollumz (Blender)', 'https://github.com/Sollumz/Sollumz'], ['CodeWalker', 'https://github.com/dexyfex/CodeWalker']],
  redm: [['RDR3 natives', 'https://rdr3natives.com/'], ['Cfx.re docs', 'https://docs.fivem.net/docs/'], ['VORP', 'https://github.com/VORPCORE'], ['RSG', 'https://github.com/Rexshack-RedM']],
  gtasa_vita: [['gtasa_vita port', 'https://github.com/TheOfficialFloW/gtasa_vita'], ['VitaShell', 'https://github.com/TheOfficialFloW/VitaShell'], ['GTAForums modding', 'https://gtaforums.com/forum/108-sa-modding/']],
  vita: [['VitaSDK', 'https://vitasdk.org/'], ['Vita3K emulator', 'https://vita3k.org/'], ['vita2d', 'https://github.com/xerpi/libvita2d'], ['VitaShell', 'https://github.com/TheOfficialFloW/VitaShell']],
  deck: [['Steamworks: Deck', 'https://partner.steamgames.com/doc/steamdeck'], ['Proton', 'https://github.com/ValveSoftware/Proton'], ['ProtonDB', 'https://www.protondb.com/']],
  web: [['Phaser', 'https://phaser.io/'], ['three.js', 'https://threejs.org/'], ['Godot web export', 'https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html']],
};
const BIN_DIR = { fivem: 'stream/', redm: 'stream/', gtasa_vita: 'ux0/data/gtasa/mods/', vita: 'assets/', deck: 'assets/', web: 'assets/' };
const kb = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`);
const b64Of = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1] || ''); r.onerror = () => no(new Error('That file could not be read.')); r.readAsDataURL(f); });

// ▶ a web game plays right here: index.html with its own scripts and styles inlined into a sandboxed frame (no network, no storage of ours)
export function webDoc(files) {
  let html = files['index.html']; if (html == null) return '';
  html = html.replace(/<script([^>]*)\ssrc=["'](?!https?:)([^"']+)["']([^>]*)><\/script>/g, (m, a, src, b) => (files[src.replace(/^\.\//, '')] != null ? `<script${a}${b}>${files[src.replace(/^\.\//, '')].replace(/<\/script/gi, '<\\/script')}</script>` : m));
  html = html.replace(/<link([^>]*)href=["'](?!https?:)([^"']+\.css)["']([^>]*)>/g, (m, a, href) => (files[href.replace(/^\.\//, '')] != null ? `<style>${files[href.replace(/^\.\//, '')]}</style>` : m));
  return html;
}

function Checks({ rows }) {
  if (!rows?.length) return null; const ok = rows.filter(r => r.ok).length;
  return <section className="gd-checks" data-testid="gd-checks"><header><b>THE CHECK</b><small className="m-num">{ok}/{rows.length} pass · a structure check, not a compiler</small></header>
    <ol>{rows.map((r, i) => <motion.li key={`${r.file}-${i}`} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i, 14) * 0.025 }} className={r.ok ? 'is-ok' : 'is-bad'}><i aria-hidden="true">{r.ok ? '✓' : '✕'}</i><code>{r.file}</code><span>{r.msg}</span></motion.li>)}</ol></section>;
}

function Start({ targets, onMake, busy }) {
  const [t, setT] = useState('fivem'); const [name, setName] = useState('');
  return <div className="gd-start" data-testid="gd-start"><h3>Start a project</h3><p>Pick what you are building for. Its mind writes real files, the check tests them, and it downloads ready to drop in.</p>
    <div className="gd-targets">{targets.map((x, i) => <motion.button key={x.id} type="button" className={t === x.id ? 'is-on' : ''} aria-pressed={t === x.id} onClick={() => setT(x.id)} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} data-testid={`gd-target-${x.id}`}><b>{x.name}</b><small>{x.what}</small></motion.button>)}</div>
    <span className="gd-row"><input className="m-input" maxLength={48} value={name} onChange={e => setName(e.target.value)} placeholder="Name it: my_garage, fast cars…" aria-label="Project name" data-testid="gd-name" />
      {t === 'fivem' || t === 'redm' ? <button type="button" className="m-btn" disabled={busy} onClick={() => onMake(name, t, true)} data-tip="A working resource: fxmanifest, config, client and server Lua. No model, no cost">From a working starter</button> : null}
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => onMake(name, t, false)} data-testid="gd-make">Start empty</button></span></div>;
}

function Studio({ p, minds, busy, onAsk, onBuildStep }) {
  const [mode, setMode] = useState('build'); const [mind, setMind] = useState(0); const [text, setText] = useState(''); const [log, setLog] = useState('');
  const chatRef = useRef(null); useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight; }, [p.chat?.length]);
  useEffect(() => { if (onBuildStep?.text) { setMode('build'); setText(onBuildStep.text); } }, [onBuildStep]);
  const go = e => { e.preventDefault(); if (!text.trim()) return; onAsk({ mode, mind, text, log }).then(ok => { if (ok) { setText(''); setLog(''); } }); };
  return <div className="gd-studio">
    <div className="gd-chat" ref={chatRef} data-testid="gd-chat">{(p.chat || []).length ? p.chat.map((m, i) => <motion.div key={`${m.at}-${i}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className={`gd-msg ${m.by === 'you' ? 'is-you' : 'is-mind'}`}>
      <small>{m.by === 'you' ? `You · ${m.mode}` : `${m.by} · ${m.model || ''}${m.usd ? ` · $${m.usd.toFixed(4)}` : ''}`}</small><p>{m.text}</p>{m.files?.length ? <span className="gd-touched">{m.files.map(f => <code key={f}>{f}</code>)}</span> : null}</motion.div>)
      : <p className="gd-none">Say what to build. Or tap one below: it fills the ask, you press Go.</p>}
      {busy === 'ask' ? <div className="gd-msg is-mind is-think"><small>Mind {'AB'[mind]} is writing files…</small><span className="gd-dots" aria-hidden="true"><i /><i /><i /></span></div> : null}</div>
    <form className="gd-ask" onSubmit={go}>
      <span className="gd-row"><span className="m-seg" role="tablist" aria-label="Mode">{[['build', 'Build'], ['fix', 'Fix'], ['plan', 'Plan']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={mode === k} className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-testid={`gd-mode-${k}`}>{l}</button>)}</span>
        <span className="m-seg" role="group" aria-label="Which mind">{minds.length ? minds.map((m, i) => <button key={i} type="button" aria-pressed={mind === i} className={mind === i ? 'active' : ''} onClick={() => setMind(i)} data-tip={`Mind ${'AB'[i]} runs ${m}, on this agent's own key`} data-testid={`gd-mind-${i}`}>Mind {'AB'[i]} · {m}</button>) : <small className="gd-warn">Pick a model for this agent first (its settings)</small>}</span></span>
      <span className="gd-quick">{(QUICK[p.target] || []).map(([l, m, t]) => <button key={l} type="button" className="gd-chip" onClick={() => { setMode(m); setText(t); }} data-testid={`gd-quick-${l.replace(/\W+/g, '-').toLowerCase()}`}>{m === 'plan' ? '🗺 ' : m === 'fix' ? '🛠 ' : ''}{l}</button>)}</span>
      <textarea className="m-input" rows={3} value={text} onChange={e => setText(e.target.value)} placeholder={mode === 'fix' ? 'What goes wrong? (crash on load, a script error, a car that floats…)' : mode === 'plan' ? 'What should it plan? A server, a port, a mod pack…' : 'What should it build or add?'} aria-label="Ask" data-testid="gd-ask" />
      {mode === 'fix' ? <textarea className="m-input gd-log" rows={4} value={log} onChange={e => setLog(e.target.value)} placeholder="Paste the error, the F8 console, server log or crash dump here" aria-label="Error or log" data-testid="gd-log" /> : null}
      <span className="gd-row"><small>Runs on this agent's own model and key. Own games, legal homebrew and your own servers only.</small><button type="submit" className="m-btn m-go" disabled={!!busy || !minds.length || !text.trim()} data-testid="gd-go">{busy === 'ask' ? 'Working…' : mode === 'plan' ? 'Plan it' : mode === 'fix' ? 'Fix it' : 'Go'}</button></span>
    </form>
    <Checks rows={p.checks} /></div>;
}

function Files({ p, busy, onSave, onDrop, onUpload, onLearn, style, onUnlearn, open, setOpen }) {
  const names = useMemo(() => [...Object.keys(p.files || {}).map(n => ({ n, text: true })), ...Object.entries(p.bins || {}).map(([n, b]) => ({ n, b }))].sort((a, b) => a.n.localeCompare(b.n)), [p.files, p.bins]);
  const cur = open && p.files?.[open] != null ? open : names.find(x => x.text)?.n; const [draft, setDraft] = useState(''); const [dir, setDir] = useState(BIN_DIR[p.target] || 'assets/'); const [play, setPlay] = useState(false);
  useEffect(() => { setDraft(cur ? p.files[cur] : ''); }, [cur, p.files]);
  const bad = new Set((p.checks || []).filter(r => !r.ok).map(r => r.file));
  return <div className="gd-files">
    <aside className="gd-tree" data-testid="gd-tree"><ol>{names.map(x => <li key={x.n}><button type="button" className={`${cur === x.n ? 'is-on' : ''}${bad.has(x.n) ? ' is-bad' : ''}`} disabled={!x.text} onClick={() => setOpen(x.n)} title={x.n}>{x.text ? '📄' : x.b?.url ? '🧊' : '📦'} {x.n}{x.b ? <small>{x.b.url ? x.b.lic : kb(x.b.size)}</small> : null}</button>
      <button type="button" className="gd-x" aria-label={`Remove ${x.n}`} disabled={!!busy} onClick={() => onDrop(x.n)}>✕</button></li>)}</ol>
      <label className="m-btn gd-up"><input type="file" multiple hidden onChange={e => { onUpload([...e.target.files], dir); e.target.value = ''; }} data-testid="gd-upload" />⬆ Upload files</label>
      <label className="gd-dir"><small>MODELS + TEXTURES GO INTO</small><input className="m-input" value={dir} onChange={e => setDir(e.target.value)} aria-label="Folder for uploaded binaries" /></label>
      <div className="gd-style" data-tip="Your own scripts: the mind reads them first and writes like you (your names, framework, layout)"><b>LEARN MY CODE</b>
        {style.map(s => <span key={s.path}><code>{s.path}</code><button type="button" className="gd-x" aria-label={`Forget ${s.path}`} onClick={() => onUnlearn(s.path)}>✕</button></span>)}
        <label className="m-btn"><input type="file" multiple hidden onChange={e => { onLearn([...e.target.files]); e.target.value = ''; }} data-testid="gd-learn" />＋ Add my scripts</label></div></aside>
    <div className="gd-edit">{cur ? <><header><code>{cur}</code><span className="gd-row">{p.target === 'web' && p.files['index.html'] != null ? <button type="button" className="m-btn" onClick={() => setPlay(v => !v)} data-testid="gd-play">{play ? 'Close the game' : '▶ Play it here'}</button> : null}
      <button type="button" className="m-btn m-go" disabled={!!busy || draft === p.files[cur]} onClick={() => onSave(cur, draft)} data-testid="gd-save">Save</button></span></header>
      {play ? <iframe className="gd-frame" title="The game" sandbox="allow-scripts" srcDoc={webDoc(p.files)} data-testid="gd-frame" /> : <textarea className="gd-code" spellCheck={false} value={draft} onChange={e => setDraft(e.target.value)} aria-label={`Edit ${cur}`} data-testid="gd-code" />}</>
      : <p className="gd-none">No files yet. Ask the Studio to build, or upload your own.</p>}</div></div>;
}

function Plan({ p, onStep, onOpen }) {
  const plan = p.plan;
  if (!plan?.phases?.length) return <p className="gd-none">No plan yet. In the Studio, pick Plan and say what to plan: a server, a port, a mod pack.</p>;
  return <div className="gd-plan" data-testid="gd-plan"><header><b>{plan.ask}</b><small>{plan.by} · {plan.phases.length} phases · tap Build on a step and its mind writes it</small></header>
    <div className="gd-wire">{plan.phases.map((ph, i) => <motion.section key={ph.name} className="gd-phase" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
      <h4><i className="m-num">{i + 1}</i>{ph.name}</h4>
      <ol>{ph.steps.map((s, j) => { const has = s.file && (p.files?.[s.file] != null || p.bins?.[s.file]); return <li key={j} className={has ? 'is-done' : ''}><span>{s.do}</span>
        {s.file ? <button type="button" className="gd-chip" disabled={!has} onClick={() => onOpen(s.file)} data-tip={has ? 'Open the file' : 'Not written yet'}>{has ? '✓ ' : ''}{s.file}</button> : null}
        <button type="button" className="gd-build" onClick={() => onStep(`${ph.name}: ${s.do}${s.file ? ` (in ${s.file})` : ''}`)} data-testid={`gd-step-${i}-${j}`}>Build</button></li>; })}</ol></motion.section>)}</div></div>;
}

function Discover({ p, work, catId, busy, onFork, onLink }) {
  const [q, setQ] = useState(''); const [rows, setRows] = useState(null); const [lib, setLib] = useState(null); const [lq, setLq] = useState(p.target === 'fivem' ? 'chain' : 'car'); const [err, setErr] = useState('');
  const find = useCallback(() => work(catId, { op: 'gdesk_shelf', text: q, job: '' }).then(j => setRows(j.rows || [])).catch(e => setErr(e.message)), [work, catId, q]);
  const look = useCallback(() => work(catId, { op: 'play3d_assets', text: lq, job: 'model' }).then(j => setLib(j.rows || [])).catch(e => setErr(e.message)), [work, catId, lq]);
  useEffect(() => { find(); look(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="gd-disc">
    {err ? <p className="gd-err" role="alert">⚠ {err}</p> : null}
    <section><header><b>SHARED BY BUILDERS</b><small>Projects other agents chose to share. Fork one and it is yours to change.</small></header>
      <form className="gd-row" onSubmit={e => { e.preventDefault(); find(); }}><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder="Search shared projects" aria-label="Search shared projects" /><button type="submit" className="m-btn">Search</button></form>
      {rows == null ? <p className="gd-none">Reading the shelf…</p> : rows.length ? <ol className="gd-shelf" data-testid="gd-shelf">{rows.map(r => <li key={`${r.cat}-${r.id}`}><span><b>{r.name}</b><small>{r.by} · {r.target} · {r.files} files{r.assets ? ` · ${r.assets} assets` : ''}{r.forks ? ` · ${r.forks} forks` : ''}</small></span>{r.passed ? <i className="gd-pass">check passed</i> : null}
        <button type="button" className="m-btn" disabled={!!busy} onClick={() => onFork(r)}>Fork</button></li>)}</ol> : <p className="gd-none">Nothing shared yet. Share yours from the top bar and it shows here for everyone.</p>}</section>
    <section><header><b>REAL 3D MODELS · CC0</b><small>Free to use. Added to the project, fetched into the zip. For FiveM it is the .glb you take into Blender + Sollumz.</small></header>
      <form className="gd-row" onSubmit={e => { e.preventDefault(); look(); }}><input className="m-input" value={lq} onChange={e => setLq(e.target.value)} placeholder="chain, car, chair…" aria-label="Search 3D models" /><button type="submit" className="m-btn">Search</button></form>
      {lib == null ? <p className="gd-none">Reading the library…</p> : <ol className="gd-lib" data-testid="gd-lib">{lib.slice(0, 18).map(a => <li key={a.id}>{a.thumb ? <img src={a.thumb} alt="" loading="lazy" /> : <span className="gd-noimg" aria-hidden="true">🧊</span>}<b title={a.name}>{a.name}</b><button type="button" className="gd-chip" disabled={!!busy} onClick={() => onLink(a)}>＋ Add</button></li>)}</ol>}</section>
    <section><header><b>THE REAL TOOLS FOR {String(p.target).toUpperCase().replace('_', ' ')}</b><small>Open source or official. They open in a new tab.</small></header>
      <span className="gd-tools">{(TOOLS[p.target] || []).map(([l, u]) => <a key={u} className="gd-chip" href={u} target="_blank" rel="noreferrer noopener">{l} ↗</a>)}</span></section></div>;
}

export function GameDesk({ cat, work }) {
  const [d, setD] = useState(null); const [p, setP] = useState(null); const [tab, setTab] = useState('studio'); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [note, setNote] = useState('');
  const [open, setOpen] = useState(''); const [step, setStep] = useState(null); const [style, setStyle] = useState([]); const [fresh, setFresh] = useState(false);
  const run = useCallback(async (k, body) => { setBusy(k); setErr(''); try { const j = await work(cat.id, body); setBusy(''); return j; } catch (e) { setErr(e.message); setBusy(''); return null; } }, [work, cat.id]);
  const load = useCallback(id => work(cat.id, { op: 'gdesk_get', tools: id ? { id } : null }).then(j => { setD(j); setP(j.project); setStyle(j.style || []); }).catch(e => setErr(e.message)), [work, cat.id]);
  useEffect(() => { load(); }, [load]);
  const take = j => { if (!j) return false; if (j.project) setP(j.project); if (j.projects) setD(x => ({ ...x, projects: j.projects })); else if (j.project) setD(x => ({ ...x, projects: [j.project, ...(x?.projects || []).filter(y => y.id !== j.project.id)] })); return true; };
  const tools = extra => ({ id: p?.id, ...extra });
  const labCall = useCallback((_path, o) => work(cat.id, { op: 'gdesk_lab', tools: o?.body ? JSON.parse(o.body) : null }), [work, cat.id]);
  const make = async (name, target, starter) => { const j = await run('new', { op: 'gdesk_new', text: name, job: target, tools: { starter } }); if (take(j)) { setFresh(false); setTab('studio'); } };
  const ask = async ({ mode, mind, text, log }) => { const j = await run('ask', { op: 'gdesk_ask', job: mode, i: mind, text, tools: tools({ log }) }); if (take(j)) { setNote(`${j.model}: ${j.say}`); if (mode === 'plan') setTab('plan'); return true; } return false; };
  const upload = async (files, dir) => { for (const f of files) { const b64 = await b64Of(f).catch(e => { setErr(e.message); return null; }); if (b64 == null) continue; const isBin = !/\.(lua|js|ts|json|cfg|dat|ide|ipl|txt|md|xml|meta|html|css|c|h|cpp|cmake|ini|toml|ya?ml|sql|vdf|sh|py|csv)$/i.test(f.name); take(await run('up', { op: 'gdesk_upload', tools: tools({ path: isBin ? `${dir.replace(/\/?$/, '/')}${f.name}` : f.name, b64 }) })); } };
  const learn = async files => { for (const f of files.slice(0, 4)) { const b64 = await b64Of(f).catch(() => null); if (b64 == null) continue; const j = await run('learn', { op: 'gdesk_upload', tools: { path: f.name, b64, learn: true } }); if (j?.style) setStyle(j.style); } };
  const download = async () => { const j = await run('zip', { op: 'gdesk_zip', tools: tools() }); if (!j) return; const bin = Uint8Array.from(atob(j.b64), c => c.charCodeAt(0)); const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([bin], { type: 'application/zip' })); a.download = j.name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); setNote(`${j.name} · ${kb(j.size)}${j.missing?.length ? ` · not fetched: ${j.missing.join(', ')}` : ''}`); };
  if (!d) return <p className="gd-none" role="status">{err ? `⚠ ${err}` : 'Opening the game desk…'}</p>;
  const T = Object.fromEntries((d.targets || []).map(t => [t.id, t])); const ok = (p?.checks || []).filter(r => r.ok).length; const all = (p?.checks || []).length;
  return <div className="gd" data-testid="game-desk">
    <header className="gd-h"><span className="gd-title"><b>🎮 GAME DESK</b><small>Build, fix and plan for FiveM, RedM, the GTA SA Vita port, Vita homebrew, Steam Deck and the web. Its own model writes the files.</small></span>
      {d.projects?.length ? <select className="m-input gd-pick" value={fresh ? '' : p?.id || ''} onChange={e => { if (e.target.value === '+') { setFresh(true); return; } setFresh(false); load(e.target.value); }} aria-label="Project" data-testid="gd-project">{fresh ? <option value="">New project…</option> : null}{d.projects.map(x => <option key={x.id} value={x.id}>{x.name} · {T[x.target]?.name || x.target}</option>)}<option value="+">＋ New project</option></select> : null}</header>
    {err ? <p className="gd-err" role="alert">⚠ {err}</p> : null}
    {!p || fresh ? <Start targets={d.targets || []} onMake={make} busy={!!busy} /> : <>
      <div className="gd-bar"><span className="gd-badge"><b>{p.name}</b><small>{T[p.target]?.name}</small></span>
        <span className={`gd-meter${all && ok === all ? ' is-ok' : ''}`} data-tip="The structure check on every file, run after every change"><i><motion.u initial={false} animate={{ scaleX: all ? ok / all : 0 }} transition={{ duration: 0.5 }} /></i><small className="m-num">{all ? `${ok}/${all} checks` : 'no files yet'}</small></span>
        <button type="button" className="m-btn m-go" disabled={!!busy || !Object.keys(p.files || {}).length} onClick={download} data-tip={T[p.target]?.drop} data-testid="gd-zip">{busy === 'zip' ? 'Packing…' : '⬇ Download .zip'}</button>
        <button type="button" className={`m-btn${p.shared ? ' is-on' : ''}`} aria-pressed={!!p.shared} disabled={!!busy} onClick={async () => take(await run('share', { op: 'gdesk_share', on: !p.shared, tools: tools() }))} data-tip="Shared projects show in every agent's Discover, where anyone can fork them" data-testid="gd-share">{p.shared ? 'Shared' : 'Share'}</button>
        <button type="button" className="m-btn danger" disabled={!!busy} onClick={async () => { if (!window.confirm(`Delete ${p.name}? Its files are gone for good.`)) return; const j = await run('del', { op: 'gdesk_delete', tools: tools() }); if (j) { setD(x => ({ ...x, projects: j.projects })); setP(null); load(); } }}>Delete</button></div>
      {note ? <p className="gd-note" role="status">{note}</p> : null}
      <span className="m-seg gd-tabs" role="tablist" aria-label="Game desk">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`gd-tab-${k}`}>{l}{k === 'plan' && p.plan ? ` · ${p.plan.phases.length}` : k === 'files' ? ` · ${Object.keys(p.files || {}).length + Object.keys(p.bins || {}).length}` : ''}</button>)}</span>
      <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.16 }}>
        {tab === 'studio' ? <Studio p={p} minds={d.minds || []} busy={busy} onAsk={ask} onBuildStep={step} /> : null}
        {tab === 'files' ? <Files p={p} busy={busy} open={open} setOpen={setOpen} style={style} onSave={async (path, text) => take(await run('save', { op: 'gdesk_save', tools: tools({ path, text }) }))} onDrop={async path => take(await run('drop', { op: 'gdesk_drop', tools: tools({ path }) }))} onUpload={upload} onLearn={learn} onUnlearn={async path => { const j = await run('learn', { op: 'gdesk_unlearn', text: path }); if (j?.style) setStyle(j.style); }} /> : null}
        {tab === 'plan' ? <Plan p={p} onOpen={f => { setOpen(f); setTab('files'); }} onStep={t => { setStep({ text: t, at: Date.now() }); setTab('studio'); }} /> : null}
        {tab === 'discover' ? <Discover p={p} work={work} catId={cat.id} busy={busy} onFork={async r => { const j = await run('fork', { op: 'gdesk_fork', tools: { id: r.id, cat: r.cat } }); if (take(j)) { setTab('files'); setNote(`Forked ${r.name}. It is yours now.`); } }} onLink={async a => { const j = await run('link', { op: 'gdesk_link', text: a.id, job: 'model', tools: tools() }); if (take(j)) setNote(`Added ${a.name}. It is fetched into the zip.`); }} /> : null}
        {tab === 'test' ? <GameLab call={labCall} /> : null}
      </motion.div></>}
  </div>;
}

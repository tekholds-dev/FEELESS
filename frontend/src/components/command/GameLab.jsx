import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'motion/react';
import '../../styles/gameLab.css';

// 🎮 GAME LAB (owner 2026-11-15: "a place in desktop for game testing, porting and etc like for gta rp, and possibly psvita … a folder in
// desktop"). The owner's desktop folder: a playtest log, one porting checklist per target with the real open tools, and a working FiveM /
// RedM resource starter. Saved owner-only on the server (game_lab.py). Your own games and legal homebrew only.
const TABS = [['test', 'Playtest log'], ['port', 'Port'], ['rp', 'GTA RP resource']];
const VERDICT = { ship: 'Ready to ship', fix: 'Needs fixes', blocked: 'Blocked' };
const blank = () => ({ game: '', platform: 'fivem', build: '', fps: '', bugs: '', verdict: 'fix', notes: '' });

export function GameLab({ call }) {
  const [d, setD] = useState(null); const [tab, setTab] = useState('test'); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const [row, setRow] = useState(blank); const [plat, setPlat] = useState('fivem'); const [rp, setRp] = useState({ name: '', game: 'gta5', what: '' }); const [made, setMade] = useState(null); const [file, setFile] = useState('fxmanifest.lua');
  useEffect(() => { let on = true; call('/admin/game-lab').then(x => on && setD(x)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [call]);
  const post = useCallback(async body => { setBusy(true); setErr(''); try { const j = await call('/admin/game-lab', { method: 'POST', body: JSON.stringify(body) }); setBusy(false); return j; } catch (e) { setErr(e.message); setBusy(false); return null; } }, [call]);
  const log = async e => { e.preventDefault(); const j = await post({ log: { ...row, fps: row.fps === '' ? null : Number(row.fps), bugs: row.bugs.split('\n') } }); if (j) { setD(j); setRow(blank()); } };
  const make = async e => { e.preventDefault(); const j = await post({ resource: rp }); if (j) { setMade(j); setFile('fxmanifest.lua'); } };
  if (!d) return <p className="glb-wait" role="status">{err ? `⚠ ${err}` : 'Opening the game lab…'}</p>;
  const P = Object.fromEntries(d.platforms.map(p => [p.id, p])); const cur = P[plat]; const done = new Set(d.checks?.[plat] || []);
  return <div className="glb" data-testid="game-lab">
    <header className="glb-h"><span><b>🎮 GAME LAB</b><small>Test, port and build for GTA RP, RedM, PS Vita homebrew, Steam Deck and the web. Your own games and legal homebrew only.</small></span>
      <span className="glb-stats">{[['SESSIONS', d.stats.sessions], ['BUGS LOGGED', d.stats.bugs], ['READY TO SHIP', d.stats.ship]].map(([k, v]) => <span key={k}><small>{k}</small><b className="m-num">{v}</b></span>)}</span></header>
    <span className="m-seg" role="tablist" aria-label="Game lab">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`glb-tab-${k}`}>{l}</button>)}</span>
    {err ? <p className="glb-err" role="alert">⚠ {err}</p> : null}
    {tab === 'test' ? <div className="glb-two">
      <form className="glb-card" onSubmit={log} data-testid="glb-form"><b>Log a session</b>
        <label><small>GAME</small><input className="m-input" maxLength={60} value={row.game} onChange={e => setRow({ ...row, game: e.target.value })} placeholder="Night Run" data-testid="glb-game" /></label>
        <label><small>PLATFORM</small><select className="m-input" value={row.platform} onChange={e => setRow({ ...row, platform: e.target.value })} data-testid="glb-platform">{d.platforms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <span className="glb-row"><label><small>BUILD</small><input className="m-input" maxLength={30} value={row.build} onChange={e => setRow({ ...row, build: e.target.value })} placeholder="v0.3" /></label>
          <label><small>FPS</small><input className="m-input m-num" type="number" min="0" max="1000" value={row.fps} onChange={e => setRow({ ...row, fps: e.target.value })} placeholder="60" data-testid="glb-fps" /></label></span>
        <label><small>BUGS · ONE A LINE</small><textarea className="m-input" rows={3} value={row.bugs} onChange={e => setRow({ ...row, bugs: e.target.value })} placeholder="Crash when the garage opens" /></label>
        <span className="m-seg" role="group" aria-label="Verdict">{Object.entries(VERDICT).map(([k, l]) => <button key={k} type="button" className={row.verdict === k ? 'active' : ''} aria-pressed={row.verdict === k} onClick={() => setRow({ ...row, verdict: k })}>{l}</button>)}</span>
        <button type="submit" className="m-btn m-go" disabled={busy || !row.game.trim()} data-testid="glb-log">Log it</button></form>
      <ol className="glb-log" data-testid="glb-log-list">{d.log.length ? d.log.map((r, i) => <motion.li key={r.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 10) * 0.03 }} className={`is-${r.verdict}`}>
        <span><b>{r.game}</b><small>{P[r.platform]?.name || r.platform}{r.build ? ` · ${r.build}` : ''} · {new Date(r.at * 1000).toLocaleDateString()}</small></span>
        <em className="m-num">{r.fps != null ? `${r.fps} fps` : '—'}</em><i>{VERDICT[r.verdict]}</i>
        {r.bugs.length ? <ul>{r.bugs.map((x, j) => <li key={j}>{x}</li>)}</ul> : null}
        <button type="button" className="glb-x" aria-label={`Remove ${r.game}`} disabled={busy} onClick={async () => { const j = await post({ drop: r.id }); if (j) setD(j); }}>✕</button></motion.li>) : <li className="glb-none">No sessions yet. Log your first playtest.</li>}</ol>
    </div> : null}
    {tab === 'port' ? <div className="glb-port">
      <span className="glb-plats" role="group" aria-label="Target">{d.platforms.map(p => { const n = (d.checks?.[p.id] || []).length; return <button key={p.id} type="button" className={plat === p.id ? 'is-on' : ''} aria-pressed={plat === p.id} onClick={() => setPlat(p.id)} data-testid={`glb-plat-${p.id}`}><b>{p.name}</b><small className="m-num">{n}/{p.steps.length}</small><s style={{ transform: `scaleX(${n / p.steps.length})` }} aria-hidden="true" /></button>; })}</span>
      <div className="glb-card"><b>{cur.name}</b><small>{cur.what}</small><span className="glb-tools">{cur.tools.map(t => <i key={t}>{t}</i>)}</span>
        <ol className="glb-steps">{cur.steps.map((s, i) => <li key={i}><label><input type="checkbox" checked={done.has(i)} disabled={busy} onChange={async () => { const j = await post({ check: plat, step: i }); if (j) setD(j); }} data-testid={`glb-step-${i}`} /><span>{s}</span></label></li>)}</ol></div>
    </div> : null}
    {tab === 'rp' ? <div className="glb-two">
      <form className="glb-card" onSubmit={make}><b>Make a resource</b><small>A working starter: fxmanifest.lua, config, client and server Lua. No model, no cost.</small>
        <label><small>NAME</small><input className="m-input" maxLength={32} value={rp.name} onChange={e => setRp({ ...rp, name: e.target.value })} placeholder="my_garage" data-testid="glb-rp-name" /></label>
        <span className="m-seg" role="group" aria-label="Game">{[['gta5', 'FiveM · GTA V'], ['rdr3', 'RedM · RDR2']].map(([k, l]) => <button key={k} type="button" className={rp.game === k ? 'active' : ''} aria-pressed={rp.game === k} onClick={() => setRp({ ...rp, game: k })}>{l}</button>)}</span>
        <label><small>WHAT IT DOES</small><input className="m-input" maxLength={120} value={rp.what} onChange={e => setRp({ ...rp, what: e.target.value })} placeholder="Park and pull out your cars" /></label>
        <button type="submit" className="m-btn m-go" disabled={busy || !rp.name.trim()} data-testid="glb-rp-make">Make it</button></form>
      {made ? <div className="glb-card glb-code" data-testid="glb-rp-out"><span className="glb-files">{Object.keys(made.files).map(f => <button key={f} type="button" className={file === f ? 'is-on' : ''} onClick={() => setFile(f)}>{f}</button>)}</span>
        <pre><code>{made.files[file]}</code></pre>
        <span className="glb-row"><button type="button" className="m-btn" onClick={() => navigator.clipboard?.writeText(made.files[file])}>Copy {file}</button></span>
        <small>{made.install}</small></div> : <p className="glb-none">Name it and press Make it. You get the four files to drop into resources/.</p>}
    </div> : null}
  </div>;
}

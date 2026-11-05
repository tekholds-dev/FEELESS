import { agentAuthQuery } from '../../lib/chatSession';
import { ProofTerms } from './ProofTerms';
import React, { useMemo, useState } from 'react';
import '../../styles/proofsFolder.css';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { ProofStamp } from './ProofStamp';

// 🏆 THE PROOFS FOLDER (owner 2026-11-04): every proof this agent filed, in one place. A ring, a 3D chart and the Proof Loop orbit up top, the PoI timeline under them:
// what each mind decided at the time, and the snapshots it decided on. Read from the filed folders only. Each proof is scored in its own unit: SOL and paper % are never added together.
const KINDS = { pow: ['⛏', 'PoW'], pop: ['📉', 'PoP'], pob: ['🎲', 'PoB'], poc: ['📣', 'PoC'], pos: ['💻', 'PoStatic'] };
const OPEN_APP = { pow: 'pow', pop: 'pop', pob: 'bids', poc: 'features' };

// A mind's reason is sometimes its raw JSON reply, cut short: show its sentence, not the JSON.
export function reasonOf(v) {
  const t = String(v || '').trim();
  if (!t.startsWith('{')) return t;
  const m = t.match(/"why"\s*:\s*"((?:[^"\\]|\\.)*)/);
  return m ? m[1] : '';
}
const mind = i => `Mind ${'AB'[Number(i)] || Number(i) + 1}`;
const shotsOf = (f, kind) => (f.shots || []).map(s => ({ ...s, src: apiUrl(`/api/cats/{cat}/powshot/${String(f.id).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${s.file}?${agentAuthQuery()}`), kind }));
const toneOf = v => (v == null ? 'none' : v > 0 ? 'win' : v < 0 ? 'loss' : 'none');

function powRow(f) {
  const v = f.pnlPct != null ? Number(f.pnlPct) : null;
  return { kind: 'pow', id: f.id, at: Number(f.soldAt || f.at) || 0, name: f.name || `PoW #${f.n || ''}`, sub: f.sym ? `$${f.sym}` : '', value: v, shown: v == null ? (f.status === 'closed' ? 'no trade' : 'open') : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
    state: f.status !== 'closed' ? 'open' : toneOf(f.pnlSol ?? v), loop: f.loop, shots: shotsOf(f, 'pow'), sent: f.sent,
    decisions: [...Object.entries(f.whys || {}).map(([i, w]) => [mind(i), reasonOf(w)]), ...(f.why ? [['It closed', f.why]] : []), ...(f.report?.lesson ? [['Lesson', f.report.lesson]] : [])].filter(([, t]) => t),
    skipped: f.loop?.skipped || [] };
}
function popRow(f) {
  const v = f.roePct != null ? Number(f.roePct) : null;
  return { kind: 'pop', id: f.id, at: Number(f.closedAt || f.at) || 0, name: f.n ? `PoP #${f.n}` : 'PoP', sub: f.noTrade ? 'no trade' : [f.market, f.side].filter(Boolean).join(' '), value: f.noTrade ? null : v, shown: f.noTrade || v == null ? (f.status === 'closed' ? 'no trade' : 'open') : `${v > 0 ? '+' : ''}${v.toFixed(1)}% paper`,
    state: f.status !== 'closed' ? 'open' : f.noTrade ? 'none' : toneOf(v), loop: f.loop, shots: [],
    decisions: [...(f.calls || []).map((c, i) => [c.name || mind(c.mind ?? i), [c.side, c.market].filter(Boolean).join(' ') + (c.why ? `: ${reasonOf(c.why)}` : '')]), ...(f.why ? [['It closed', f.why]] : []), ...(f.report?.lesson ? [['Lesson', f.report.lesson]] : [])].filter(([, t]) => t), skipped: [] };
}
function pobRow(f) {
  const graded = f.graded === 'right' ? 1 : f.graded === 'wrong' ? -1 : null; const v = f.topic ? graded : (f.net != null ? Number(f.net) : null);
  const pick = p => (p && typeof p === 'object' ? p.pick || p.text || '' : p);
  return { kind: 'pob', id: f.id, at: Number(f.closedAt || f.at) || 0, name: f.n ? `PoB #${f.n}` : 'PoB', sub: f.topic || f.q || '', value: v, shown: f.topic ? (f.graded || (f.noTrade ? 'no picks' : 'not marked')) : f.net != null ? `${f.net > 0 ? '+' : ''}${f.net} chips` : (f.status === 'closed' ? 'no bid' : 'open'),
    state: f.status && f.status !== 'closed' ? 'open' : toneOf(v), loop: f.loop, shots: shotsOf(f, 'pob'),
    decisions: [...(f.calls || []).map((c, i) => [c.name || mind(c.mind ?? i), (c.picks || []).map(pick).filter(Boolean).join(' · ') || reasonOf(c.why)]), ...(f.agreed?.length ? [['Both agree', f.agreed.map(pick).join(' · ')]] : []), ...(f.why ? [['Result', f.why]] : [])].filter(([, t]) => t), skipped: [] };
}
function pocRow(f) {
  const v = f.graded === 'right' ? 1 : f.graded === 'wrong' ? -1 : null;
  return { kind: 'poc', id: f.id, at: Number(f.at) || 0, name: f.n ? `PoC #${f.n}` : 'PoC', sub: f.topic || '', value: v, shown: v == null ? 'not marked' : v > 0 ? 'worked' : 'did not', state: toneOf(v), loop: null, shots: shotsOf(f, 'poc'), skipped: [], decisions: (f.calls || []).map((c, i) => [c.name || mind(i), `${c.angle ? `${c.angle}: ` : ''}${c.post || ''}`]).filter(([, t]) => t) };
}
// 💎 A proof that paid the Collective carries its own folder: the send on the explorer with what proves it boxed, the receipt read back from the chain, and the links.
function CollectiveSub({ sent, name }) {
  const [big, setBig] = useState(null); const shots = [[apiUrl(`/api/cats/receipt/${sent.sig}/explorer`), 'On Solana Explorer'], [apiUrl(`/api/cats/receipt/${sent.sig}`), 'Receipt read from the chain']];
  return <section className="pfx-coll" data-testid="pfx-collective"><h4><Ic3 e="💎" size="18px" /> ITS COLLECTIVE FOLDER</h4><div className="pfx-coll-shots">{shots.map(([u, l]) => <button key={u} type="button" onClick={() => setBig(u)} data-tip={`${l}: open it big`}><img src={u} alt={`${name}: ${l}`} loading="lazy" onError={e => { e.currentTarget.closest('button').style.display = 'none'; }} /><small>{l}</small></button>)}</div>
    <dl><div><dt>SENT</dt><dd className="m-num">{Number(sent.sol || 0).toFixed(6)} SOL</dd></div>{sent.keptSol != null ? <div><dt>COLLECTIVE KEPT</dt><dd className="m-num">{Number(sent.keptSol).toFixed(6)}</dd></div> : null}{sent.lockedSol != null ? <div><dt>FOLLOWS ITS PLAN</dt><dd className="m-num">{Number(sent.lockedSol).toFixed(6)}</dd></div> : null}<div><dt>TXN</dt><dd className="m-num">{String(sent.sig).slice(0, 8)}…{String(sent.sig).slice(-6)}</dd></div></dl>
    <span className="pfx-coll-l"><a href={`https://solscan.io/tx/${sent.sig}`} target="_blank" rel="noopener noreferrer" data-tip="Open it on Solscan">Solscan ↗</a><a href={`https://explorer.solana.com/tx/${sent.sig}`} target="_blank" rel="noopener noreferrer" data-tip="Open it on Solana Explorer">Explorer ↗</a></span>
    {big ? <div className="ast-shade" role="dialog" aria-modal="true" aria-label={name} onClick={() => setBig(null)}><img src={big} alt={name} /></div> : null}</section>;
}
// 🔁 One loop for every proof, its own steps per kind, and whether it asks you first.
const LOOP_ROWS = [['pow', 'PoW', 'Trade', ['Scout coins', '3 turns pick one', 'Buy and watch', 'Real result'], 'If coins look bad: no trade'], ['pop', 'PoP', 'Perp', ['2 free sources each', 'Blind calls', 'Practice trade', 'Practice result'], 'If sources say nothing: no trade'], ['pob', 'PoB', 'Pick', ['1 search, 4 sites, 3-6 steps each', 'Blind picks', 'Nothing staked', 'Real result'], 'If it reads too little: free scores and odds'], ['poc', 'PoC', 'Post idea', ['5 trend sources + snapshots', 'Blind pitches', 'Nothing posted', 'Your mark and earnings'], 'If trends are thin: your notes'], ['pos', 'PoStatic', 'Page', ['Best current builds', 'A plan you approve', 'Built, then reviewed', 'Your mark'], 'If no references: its own judgment']];
function ProofLoop({ cat, d, work }) {
  const [auto, setAuto] = useState(null); const [err, setErr] = useState(''); const cfg = auto || d?.proofCfg?.auto || {};
  const flip = async (k, on) => { setErr(''); try { const j = await work(cat.id, { op: 'proof_cfg', text: k, on }); setAuto(j.proofCfg.auto); } catch (e) { setErr(e.message || 'Not saved'); } };
  return <details className="pfx-loop" data-testid="pfx-loop"><summary data-tip="Every proof runs the same loop, with its own steps. Set which ones ask you first.">How each proof runs, and when it asks you</summary><div className="pfx-loop-b"><div className="pfx-loop-h" aria-hidden="true">{['Clarify', 'Research', 'Decide', 'File', 'Grade'].map(x => <b key={x}>{x}</b>)}</div>{LOOP_ROWS.map(([k, code, what, steps, fb]) => { const on = !!cfg[k]; return <div key={k} className="pfx-loop-r" data-testid={`pfx-loop-${k}`}><header><strong>{code}</strong><small>{what}</small></header><div className="pfx-loop-steps"><button type="button" className={`m-chip${on ? ' is-on' : ''}`} aria-pressed={on} disabled={k === 'pos'} onClick={() => flip(k, !on)} data-tip={k === 'pos' ? 'A page always waits for your plan OK. Change it in its Build folder' : on ? 'It just files. Tap to have it ask first' : 'It asks one question in chat first. Tap to let it just file'} data-testid={`pfx-auto-${k}`}>{on ? 'Just does it' : 'Asks first'}</button>{steps.map(x => <span key={x}>{x}</span>)}</div><em>{fb}</em></div>; })}{err ? <small className="lct-err" role="alert">⚠ {err}</small> : null}</div></details>;
}
function posRow(f) {
  const v = f.graded === 'right' ? 1 : f.graded === 'wrong' ? -1 : null;
  return { kind: 'pos', id: f.id, at: Number(f.at) || 0, name: f.n ? `PoStatic #${f.n}` : 'PoStatic', sub: f.topic || '', value: v, shown: v == null ? 'not marked' : v > 0 ? 'works' : 'broken', state: toneOf(v), loop: null, shots: [], skipped: [], decisions: [...(f.plan ? [['Its plan', f.plan]] : []), ...(f.refs?.length ? [['It read', f.refs.map(r => r.title).join(', ')]] : []), ...(f.by ? [[f.by, `Built page ${f.version || ''} in ${f.topic || 'its Build folder'}`]] : [])] };
}
// 👀 A visitor's one list: the newest 5 proofs of any kind, from the public copy (no emails, no phones, no wallet trail).
export function visitorProofs(cat) {
  return proofRows(cat).slice(0, 20).map(r => ({ id: r.id, kind: KINDS[r.kind][1], label: r.sub || r.name, pct: r.kind === 'pob' ? null : r.value, stamp: r.stamp, games: r.games }));
}
export function proofRows(d) {
  const add = (f, r) => ({ ...r, stamp: f.stamp || d?.stamps?.[f.id] || null, games: f.games || null });
  return [...(d?.powFolders || []).map(f => add(f, powRow(f))), ...(d?.popFolders || []).map(f => add(f, popRow(f))), ...(d?.pobFolders || []).map(f => add(f, pobRow(f))), ...(d?.pocFolders || []).map(f => add(f, pocRow(f))), ...(d?.psFolders || []).map(f => add(f, posRow(f))),].sort((a, b) => b.at - a.at);
}

function Ring({ rows }) {
  const won = rows.filter(r => r.state === 'win').length; const lost = rows.filter(r => r.state === 'loss').length; const other = rows.length - won - lost;
  const graded = won + lost; const C = 2 * Math.PI * 52; let off = 0;
  const seg = [['win', won], ['loss', lost], ['none', other]].filter(([, n]) => n > 0);
  return <figure className="pfx-part" data-testid="pfx-ring"><figcaption>RESULTS</figcaption>
    <div className="pfx-ring"><svg viewBox="0 0 128 128" role="img" aria-label={`${won} won, ${lost} lost, ${other} without a result`}><circle cx="64" cy="64" r="52" className="pfx-ring-bg" />
      {seg.map(([k, n], i) => { const len = (n / Math.max(1, rows.length)) * C; const gap = seg.length > 1 ? 3 : 0; const el = <circle key={k} cx="64" cy="64" r="52" className={`pfx-seg is-${k}`} strokeDasharray={`${Math.max(0, len - gap)} ${C}`} strokeDashoffset={-off} style={{ '--i': i }} />; off += len; return el; })}</svg>
      <span><b className="m-num">{graded ? `${Math.round((won / graded) * 100)}%` : rows.length}</b><small>{graded ? 'won' : rows.length === 1 ? 'proof' : 'proofs'}</small></span></div>
    <ul className="pfx-legend"><li><i className="is-win" />{won} won</li><li><i className="is-loss" />{lost} lost</li><li><i className="is-none" />{other} open or no result</li></ul></figure>;
}

function Chart3d({ rows }) {
  const bars = rows.filter(r => r.value != null).slice(0, 16).reverse();
  const top = Math.max(1, ...bars.map(b => Math.abs(b.value)));
  return <figure className="pfx-part" data-testid="pfx-3d"><figcaption>LAST {bars.length || ''} RESULTS, 3D</figcaption>
    {bars.length ? <div className="pfx-stage"><div className="pfx-floor">{bars.map((b, i) => <div key={b.id} role="img" tabIndex={0} className={`pfx-bar is-${toneOf(b.value)}`} style={{ '--x': i % 4, '--y': Math.floor(i / 4), '--h': `${Math.max(5, (Math.abs(b.value) / top) * 62)}px`, '--i': i }} aria-label={`${b.name}: ${b.shown}`} data-tip={`${b.name} ${b.sub}: ${b.shown}. Height is its size next to the others, in its own unit`}>
      <i className="f-top" /><i className="f-a" /><i className="f-b" /></div>)}</div></div> : <p className="pfx-none">Bars appear as proofs close.</p>}
    <ul className="pfx-legend"><li><i className="is-win" />up</li><li><i className="is-loss" />down</li></ul></figure>;
}

// 🧠 Which mind has the better record on what. From the filed folders; a topic shows once a proof on it was graded.
export function MindBoard({ board }) {
  const rows = Object.entries(board || {}).map(([topic, m]) => [topic, Object.entries(m).map(([name, r]) => ({ name, right: r.right, n: r.right + r.wrong }))])
    .sort((a, b) => b[1].reduce((s, x) => s + x.n, 0) - a[1].reduce((s, x) => s + x.n, 0)).slice(0, 8);
  return <section className="pfx-minds" data-testid="mind-board"><b className="m-label">BEST MIND BY TOPIC</b>
    {rows.length ? rows.map(([topic, ms]) => { const best = Math.max(...ms.map(x => x.right / Math.max(1, x.n)));
      return <div key={topic} className="pfx-mind"><span>{topic}</span>{ms.map(x => { const hit = x.right / Math.max(1, x.n);
        return <em key={x.name} className={ms.length > 1 && hit === best ? 'is-top' : ''} data-tip={`${x.name}: ${x.right} of ${x.n} right`}><u style={{ transform: `scaleX(${Math.max(0.03, hit)})` }} /><small>{x.name}</small><b className="m-num">{x.right}/{x.n}</b></em>; })}</div>; })
      : <small className="pfx-none">No graded proofs yet. Each mind's record starts with its first closed proof.</small>}
  </section>;
}
function LoopOrbit({ rows }) {
  const tracks = Object.keys(KINDS).map((k, i) => { const r = rows.filter(x => x.kind === k); const won = r.filter(x => x.state === 'win').length; const lost = r.filter(x => x.state === 'loss').length; return { k, r: 54 - i * 15, n: r.length, won, rate: won + lost ? won / (won + lost) : 0, graded: won + lost }; });
  return <figure className="pfx-part" data-testid="pfx-orbit"><figcaption>THE PROOF LOOP</figcaption>
    <div className="pfx-orbit"><svg viewBox="0 0 128 128" aria-hidden="true">{tracks.map((t, i) => { const c = 2 * Math.PI * t.r; return <g key={t.k}><circle cx="64" cy="64" r={t.r} className="pfx-track" /><circle cx="64" cy="64" r={t.r} className={`pfx-arc is-${t.k}`} strokeDasharray={`${t.rate * c} ${c}`} transform="rotate(-90 64 64)" />
      <g className="pfx-sat" style={{ '--s': `${9 + i * 5}s` }}><circle cx={64 + t.r} cy="64" r="3.4" className={`pfx-dot is-${t.k}`} /></g></g>; })}</svg></div>
    <ul className="pfx-legend is-rows">{tracks.map(t => <li key={t.k} data-tip={`Its next ${KINDS[t.k][1]} is loop ${t.n + 1}. It studies these ${t.n} first. The arc is its win rate.`}><i className={`is-${t.k}`} /><b>{KINDS[t.k][1]}</b> loop {t.n + 1}{t.graded ? ` · ${Math.round(t.rate * 100)}%` : ''}</li>)}</ul></figure>;
}

const day = at => new Date(at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
const clock = at => new Date(at * 1000).toTimeString().slice(0, 5);

function Entry({ r, i, cat, open, onToggle, onShot, onOpenFolder }) {
  const src = s => s.src.replace('{cat}', cat.id);
  return <li className={`pfx-e is-${r.state}${open ? ' is-open' : ''}`} style={{ '--i': i }} data-testid={`pfx-entry-${r.id}`}>
    <i className="pfx-node" aria-hidden="true" />
    <button type="button" className="pfx-e-h" onClick={onToggle} aria-expanded={open} data-tip="What it decided at the time, and what it was looking at">
      <Ic3 e={KINDS[r.kind][0]} size="26px" /><span><b>{r.name}</b><small>{r.sub}</small></span>
      {r.loop?.n > 1 ? <em className="pfx-chip" data-tip={`Loop ${r.loop.n}: it studied ${r.loop.past?.length || 0} past proofs first`}>Loop {r.loop.n}</em> : null}
      {r.shots.length ? <em className="pfx-chip is-dim">{r.shots.length} snapshots</em> : null}
      <time className="m-num">{clock(r.at)}</time><ProofStamp s={r.stamp} /><strong className={`m-num is-${r.state}`}>{r.shown}</strong></button>
    {!open && r.shots.length ? <div className="pfx-thumbs" aria-hidden="true">{r.shots.slice(0, 4).map(s => <img key={s.file} src={src(s)} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />)}</div> : null}
    {open ? <div className="pfx-open">
      <section><h4>THE DECISIONS, AT THE TIME</h4>{r.decisions.length ? <ol className="pfx-dec">{r.decisions.map(([who, t], n) => <li key={`${who}${n}`} style={{ '--i': n }}><b>{who}</b><span>{t}</span></li>)}</ol> : <p className="pfx-none">No reasons were filed with this one.</p>}
        {r.skipped.length ? <p className="pfx-skip" data-testid="pfx-skipped"><Ic3 e="🛡" size="18px" /> Skipped because they looked like a past loss: {r.skipped.map(s => `$${s.sym} (${s.like})`).join(', ')}</p> : null}
        {r.loop?.past?.length ? <p className="pfx-skip"><Ic3 e="🪄" size="18px" /> Studied first: {r.loop.past.slice(0, 3).map(p => p.sym ? `$${p.sym} ${p.pct}%` : p.market ? `${p.market} ${p.roe}%` : `#${p.n}${p.mark ? ` ${p.mark}` : ''}`).join(', ')}</p> : null}</section>
      {r.sent?.sig ? <CollectiveSub sent={r.sent} name={r.name} /> : null}
      <section><h4>WHAT IT SAW</h4>{r.shots.length ? <div className="pfx-gallery">{r.shots.map(s => <button key={s.file} type="button" onClick={() => onShot({ ...s, url: src(s) })} data-tip={`${s.site}: open it big`}><img src={src(s)} alt={`${s.site} at the time`} loading="lazy" onError={e => { e.currentTarget.style.visibility = 'hidden'; }} /><small>{s.site}</small></button>)}</div> : <p className="pfx-none">{r.kind === 'pop' ? 'A PoP reads its sources and the chart, so it files no page snapshots.' : 'No snapshots were kept with this one.'}</p>}</section>
      {onOpenFolder ? <button type="button" className="m-btn" onClick={() => onOpenFolder(OPEN_APP[r.kind])} data-testid="pfx-open-folder">Open its {KINDS[r.kind][1]} folder</button> : null}</div> : null}</li>;
}

export function ProofsFolder({ cat, d, onOpenFolder, work }) {
  const all = useMemo(() => proofRows(d), [d]); const [lens, setLens] = useState('all'); const [open, setOpen] = useState(''); const [big, setBig] = useState(null);
  const rows = lens === 'all' ? all : all.filter(r => r.kind === lens);
  const days = useMemo(() => rows.reduce((out, r) => { const k = day(r.at); const last = out[out.length - 1]; if (last?.k === k) last.rows.push(r); else out.push({ k, rows: [r] }); return out; }, []), [rows]);
  return <div className="pfx" data-testid="dsk-proofs">
    {work ? <ProofLoop cat={cat} d={d} work={work} /> : null}
    <details className="pfx-what"><summary data-tip="PoW, PoP, PoB and the rest, in plain words">What do these words mean?</summary><ProofTerms compact /></details>
    <div className="pfx-parts"><Ring rows={rows} /><Chart3d rows={rows} /><LoopOrbit rows={all} /></div>
    <MindBoard board={cat?.mindBoard} />
    <header className="pfx-bar-h"><h3><Ic3 e="🕒" size="22px" /> PoI TIMELINE</h3>
      <div className="m-seg" role="group" aria-label="Which proofs">{[['all', 'All'], ...Object.entries(KINDS).map(([k, v]) => [k, v[1]])].map(([k, l]) => <button key={k} type="button" className={lens === k ? 'active' : ''} aria-pressed={lens === k} onClick={() => setLens(k)} data-testid={`pfx-lens-${k}`}>{l}</button>)}</div></header>
    {days.length ? <div className="pfx-line">{days.map(g => <section key={g.k}><h4 className="pfx-day m-num">{g.k}</h4><ol>{g.rows.map((r, i) => <Entry key={r.id} r={r} i={i} cat={cat} open={open === r.id} onToggle={() => setOpen(open === r.id ? '' : r.id)} onShot={setBig} onOpenFolder={onOpenFolder} />)}</ol></section>)}</div>
      : <p className="pfx-empty" data-testid="pfx-empty">No proofs here yet. Type “file a PoW”, “file a perp” or “file a pob best NFL picks” in its chat.</p>}
    {big ? <div className="ast-shade" role="dialog" aria-modal="true" aria-label={big.site} onClick={() => setBig(null)}><img src={big.url} alt={big.site} /></div> : null}
  </div>;
}

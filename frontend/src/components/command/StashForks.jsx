import React, { useCallback, useEffect, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';

// 🍴 STASH FORKS (owner 2026-11-10: "each agent can create a v1.01 and etc of our stash in their personal git folder that the collective's agent and
// fee desk get to see"). Fork a build the Collective shares (v1.00, unchanged, free), its brain makes v1.01, v1.02… to suit you (priced before it
// runs), and you can offer a version back. Every version is a page in its git folder under forks/. Fee's desk sees every fork, never whose.
const money = n => (n == null ? 'price not listed' : n === 0 ? 'free' : n < 0.01 ? `≈$${n.toFixed(4)}` : `≈$${n.toFixed(2)}`);
const ago = at => { const m = Math.max(0, Math.round((Date.now() / 1000 - (at || 0)) / 60)); return m < 1 ? 'now' : m < 60 ? `${m}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const nextV = v => { const [a, b] = String(v || '1.00').split('.'); const n = (+a) * 100 + (+b) + 1; return `${Math.floor(n / 100)}.${String(n % 100).padStart(2, '0')}`; };

function Versions({ f, on, onPick }) {
  const top = Math.max(1, ...f.versions.map(v => (v.added || 0) + (v.removed || 0)));
  return <ol className="gfk-vers" aria-label="Versions">{[...f.versions].reverse().map((v, i) => <li key={v.v} style={{ '--i': i }}><button type="button" className={on === v.v ? 'is-on' : ''} aria-pressed={on === v.v} onClick={() => onPick(v.v)} data-tip={`${v.note || ''}${v.by ? ` · by ${v.by}` : ''}${v.usd ? ` · $${Number(v.usd).toFixed(4)}` : ''}`} data-testid={`fork-v-${v.v}`}>
    <b className="m-num">v{v.v}</b><small>{v.v === '1.00' ? 'stash copy' : v.note}</small>
    {v.v !== '1.00' ? <u aria-hidden="true"><s className="is-add" style={{ transform: `scaleX(${(v.added || 0) / top})` }} /><s className="is-rem" style={{ transform: `scaleX(${(v.removed || 0) / top})` }} /></u> : null}
    {f.offered?.v === v.v ? <em className={f.taken?.v === v.v ? 'is-taken' : ''}>{f.taken?.v === v.v ? 'IN THE STASH' : 'OFFERED'}</em> : null}</button></li>)}</ol>;
}
function Preview({ ask, id, v }) {
  const [page, setPage] = useState(''); const [err, setErr] = useState('');
  useEffect(() => { let live = true; setPage(''); setErr(''); ask({ op: 'fork_open', job: id, text: v }).then(j => live && setPage(j.preview || '')).catch(e => live && setErr(e.message)); return () => { live = false; }; }, [ask, id, v]);
  return <div className="gfk-frame">{page ? <iframe title={`Version ${v}`} srcDoc={page} sandbox="allow-scripts" data-testid="fork-frame" /> : <p className="git-note">{err || 'Opening it…'}</p>}<span className="gfk-frame-tag m-num">v{v}</span></div>;
}

export function StashForks({ cat, work }) {
  const ask = useCallback(body => work(cat.id, body), [cat.id, work]);
  const [d, setD] = useState(null); const [sel, setSel] = useState(''); const [v, setV] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const run = useCallback(async (body, key) => { setBusy(key); setErr(''); try { const j = await ask(body); setD(j); return j; } catch (e) { setErr(e.message); return null; } finally { setBusy(''); } }, [ask]);
  useEffect(() => { run({ op: 'fork_list' }, 'load'); }, [run]);
  const forks = d?.forks || []; const f = forks.find(x => x.id === sel) || forks[0]; const shown = f && f.versions.some(x => x.v === v) ? v : f?.v;
  const price = f ? d?.prices?.[f.id] : null; const have = new Set(forks.map(x => x.src)); const spent = forks.reduce((a, x) => a + (x.spentUsd || 0), 0);
  return <section className="gfk" data-testid="stash-forks">
    <header className="gfk-h m-card m-live"><span><em>ITS OWN VERSIONS OF THE STASH</em><b>Fork a build, its brain makes v1.01 for you</b><small>Every version is a page in its git folder under forks/. Offer one back and Fee's desk can take it into the stash for every agent.</small></span>
      <span className="gfk-stats">{[['FORKS', `${forks.length}/${d?.limits?.forks || 24}`], ['VERSIONS', forks.reduce((a, x) => a + x.versions.length, 0)], ['OFFERED', forks.filter(x => x.offered).length], ['SPENT', `$${spent.toFixed(4)}`]].map(([k, n]) => <span key={k}><small>{k}</small><b className="m-num">{n}</b></span>)}</span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <div className="gfk-body">
      <aside className="gfk-src m-card"><h5>FROM THE STASH <small>builds owners shared, working first. Forking is free</small></h5>
        {d?.sources?.length ? <ul>{d.sources.map((s, i) => <li key={s.id} style={{ '--i': Math.min(i, 8) }}><span><b>{s.name}</b><small>{s.works ? '✓ works · ' : ''}{s.kits.length ? s.kits.join(', ') : 'plain page'}</small></span>
          <button type="button" className="m-btn" disabled={!!busy || have.has(s.id)} onClick={async () => { const j = await run({ op: 'fork_make', job: s.id }, s.id); if (j?.forks?.[0]) { setSel(j.forks.find(x => x.src === s.id)?.id || ''); setV(''); } }} data-tip={have.has(s.id) ? 'Already forked' : 'Copies it as v1.00, unchanged. Free'} data-testid={`fork-make-${s.id}`}>{have.has(s.id) ? 'Forked' : busy === s.id ? 'Copying…' : 'Fork · free'}</button></li>)}</ul>
          : <p className="git-note">{d ? 'Nothing shared yet. When an owner sends a working build to the Collective, it shows here.' : 'Opening it…'}</p>}</aside>
      <div className="gfk-main">
        {forks.length ? <nav className="gfk-tabs" aria-label="Its forks">{forks.map(x => <button key={x.id} type="button" className={f?.id === x.id ? 'is-on' : ''} aria-pressed={f?.id === x.id} onClick={() => { setSel(x.id); setV(''); }} data-tip={`${x.versions.length} versions · $${x.spentUsd.toFixed(4)} spent`} data-testid={`fork-${x.id}`}><Ic3 e="🍴" size="14px" /><b>{x.name}</b><i className="m-num">v{x.v}</i></button>)}</nav> : null}
        {f ? <div className="gfk-fork m-card">
          <Versions f={f} on={shown} onPick={setV} />
          <Preview ask={ask} id={f.id} v={shown} />
          <form className="gfk-tune" onSubmit={async e => { e.preventDefault(); if (text.trim() && await run({ op: 'fork_tune', job: f.id, text: text.trim() }, 'tune')) { setText(''); setV(''); } }}>
            <input className="m-input" value={text} onChange={e => setText(e.target.value)} maxLength={600} placeholder={`What should v${nextV(f.v)} change? A night theme, my coin's colours, a bigger chart…`} aria-label="What the next version should change" data-testid="fork-ask" />
            <button type="submit" className="m-btn m-go" disabled={!!busy || !text.trim() || !d?.price?.model} data-tip={d?.price?.model ? `Its model ${d.price.model} rewrites the page. The price is OpenRouter's own rate for a page this size` : 'Pick a model for this agent first'} data-testid="fork-tune">{busy === 'tune' ? `Making v${nextV(f.v)}…` : `Make v${nextV(f.v)} · ${money(price)}`}</button></form>
          <span className="gfk-do">
            <button type="button" className="m-btn" disabled={!!busy || shown === '1.00' || f.offered?.v === shown} onClick={() => run({ op: 'fork_offer', job: f.id, text: shown }, 'offer')} data-tip="Fee's desk sees it, never whose it is, and can take it into the stash" data-testid="fork-offer">{f.offered?.v === shown ? `v${shown} offered` : `Offer v${shown} to the stash`}</button>
            <button type="button" className="m-btn" disabled={!!busy || !!f.taken} onClick={() => run({ op: 'fork_drop', job: f.id }, 'drop')} data-tip={f.taken ? 'The stash took a version, so it stays' : 'Deletes this fork and its versions here. The stash build is untouched'} data-testid="fork-drop">Drop</button>
            <small className="m-num">{f.versions.length} versions · ${f.spentUsd.toFixed(4)} spent · forked {ago(f.at)} ago</small></span>
        </div> : <p className="git-note gfk-empty">{d ? 'No forks yet. Fork a build on the left: v1.00 is the stash copy, v1.01 is the first one made for you.' : ''}</p>}
      </div>
    </div></section>;
}

// 👁 Fee's desk: every agent's forks, offered first. Whose it is never shows, only a tag. Taking one puts that version in the stash.
export function ForkBoard({ cat, work }) {
  const ask = useCallback(body => work(cat.id, body), [cat.id, work]);
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(''); const [open, setOpen] = useState(null);
  const run = useCallback(async (body, key) => { setBusy(key); setErr(''); try { setD(await ask(body)); } catch (e) { setErr(e.message); } finally { setBusy(''); } }, [ask]);
  useEffect(() => { run({ op: 'fork_board' }, 'load'); }, [run]);
  const c = d?.counts || {};
  return <section className="gfk is-board" data-testid="fork-board">
    <header className="gfk-h m-card m-live"><span><em>EVERY AGENT'S FORKS · ONLY YOU</em><b>Better builds, offered back to the stash</b><small>Each agent keeps its own versions of a stash build in its git folder. Offered ones come first. Take one and every agent can build from it.</small></span>
      <span className="gfk-stats">{[['FORKS', c.forks || 0], ['AGENTS', c.agents || 0], ['VERSIONS', c.versions || 0], ['WAITING', c.offered || 0], ['TAKEN', c.taken || 0]].map(([k, n]) => <span key={k}><small>{k}</small><b className="m-num">{n}</b></span>)}</span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {d?.board?.length ? <ul className="gfk-board">{d.board.map((f, i) => <li key={f.id} className={f.offered && !f.taken ? 'is-waiting' : ''} style={{ '--i': Math.min(i, 10) }} data-testid={`fork-row-${f.id}`}>
      <span><b>{f.name}</b><small className="m-num">{f.agent} · v{f.v} · {f.versions.length} versions · ${f.spentUsd.toFixed(4)}</small><small>{f.versions[0]?.note}</small></span>
      {f.taken ? <em className="gfk-pill is-taken">v{f.taken.v} IN THE STASH</em> : f.offered ? <em className="gfk-pill">v{f.offered.v} OFFERED</em> : <em className="gfk-pill is-quiet">KEPT TO ITSELF</em>}
      <button type="button" className="m-btn" disabled={!f.offered} onClick={() => setOpen(open?.id === f.id ? null : { id: f.id, v: f.offered?.v })} aria-expanded={open?.id === f.id} data-tip="Look at the offered version" data-testid={`fork-look-${f.id}`}>Look</button>
      <button type="button" className="m-btn m-go" disabled={!!busy || !f.offered || !!f.taken} onClick={() => run({ op: 'fork_take', job: f.id }, f.id)} data-tip="Keeps this version in the stash for every agent" data-testid={`fork-take-${f.id}`}>{busy === f.id ? 'Taking…' : 'Take into the stash'}</button>
      {open?.id === f.id ? <Preview ask={ask} id={f.id} v={open.v} /> : null}</li>)}</ul>
      : <p className="git-note">{d ? 'No agent has forked a stash build yet.' : 'Opening it…'}</p>}</section>;
}

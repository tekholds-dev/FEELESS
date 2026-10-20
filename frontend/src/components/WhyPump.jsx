import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import { pct, usd } from '../lib/num';
import { openCoin } from './CoinDrawer';
import { SocialIcons } from './QuickPulse';
import '../styles/whyPump.css';

// ❓ WHY DID IT PUMP? (owner, 2026-10-19: "can this be in rep and bring the words to life"): paste a CA → FEELESS reads the coin's live numbers,
// its Pump callers and the web / X, and says what moved it — every reason with its source (backend/why_pump.py). A coin someone already
// checked in the last 30 min is free and instant. A read, never advice.
const MINT = /[1-9A-HJ-NP-Za-km-z]{32,44}/;
export const mintOf = s => (String(s || '').match(MINT) || [null])[0];
const VERDICT = { ORGANIC: ['🌱', 'REAL BUYERS'], NEWS: ['📰', 'NEWS'], CALLERS: ['📣', 'CALLERS'], WHALES: ['🐋', 'WHALES'], BOTTED: ['🤖', 'BOTTED'], UNCLEAR: ['❔', 'UNCLEAR'] };
export const hostOf = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };
const MODEL = { lan: 'G4', local: 'OSSY' };
const STEPS = ['reading the chart', 'pulling the numbers', 'checking Pump callers', 'searching X + the web', 'reading the sources', 'writing the story'];
const ago = t => { const s = Date.now() / 1000 - t; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : `${Math.round(s / 3600)}h`; };

function Title() {
  const words = ['Why', 'did', 'it', 'pump?'];
  return <h2 className="wp-title" aria-label="Why did it pump?">{words.map((w, i) =>
    <span key={w} className={`wp-w${w === 'pump?' ? ' is-pump' : ''}`} style={{ '--i': i }} aria-hidden="true">{w === 'pump?' ? [...w].map((ch, j) => <b key={j} style={{ '--j': j }}>{ch}</b>) : w}</span>)}
    <i className="wp-rocket" aria-hidden="true">🚀</i></h2>;
}

function Working() {
  const [k, setK] = useState(0);
  useEffect(() => { const t = setInterval(() => setK(x => Math.min(x + 1, STEPS.length - 1)), 1600); return () => clearInterval(t); }, []);
  return <div className="wp-work" data-testid="wp-working">{STEPS.map((s, i) => <span key={s} className={i < k ? 'is-done' : i === k ? 'is-now' : ''}>{i < k ? '✓' : i === k ? '◌' : '·'} {s}</span>)}</div>;
}

function Answer({ a }) {
  const [ic, word] = VERDICT[a.verdict] || VERDICT.UNCLEAR;
  const n = a.numbers || {}; const mv = a.move || [];
  const tiles = [['MOVE', mv[1] != null ? `${pct(mv[1], 0)} · ${mv[0]}` : '—', mv[1] > 0 ? 'up' : mv[1] < 0 ? 'dn' : ''], ['CAP', n.cap ? usd(n.cap) : '—'], ['1H VOLUME', n.vol1h ? usd(n.vol1h) : '—'],
    ['BUYS', n.buyShare != null ? `${Math.round(n.buyShare)}%` : '—', n.buyShare >= 55 ? 'up' : n.buyShare <= 45 ? 'dn' : ''], ['CALLERS', n.callers ? String(n.callers) : '0'], ['TOP-10', n.top10 != null ? `${Math.round(n.top10)}%` : '—', n.top10 >= 40 ? 'dn' : '']];
  return <article className="wp-ans m-card" data-testid="wp-answer">
    <header><span className={`wp-stamp v-${String(a.verdict || 'UNCLEAR').toLowerCase()}`} data-testid="wp-verdict">{ic} {word}</span>
      <button type="button" className="wp-sym" onClick={() => openCoin({ mint: a.mint, symbol: n.symbol })}>{n.symbol ? `$${n.symbol}` : a.mint.slice(0, 6)}</button>
      <SocialIcons r={{ mint: a.mint, ...(a.socials || {}) }} />
      <small>{a.by === 'model' ? `🧠 written from the sources${a.model ? ` · ${MODEL[a.model] || a.model}` : ''}` : '⚙ engine read — no model answered, numbers only'}{a.cached ? ' · checked before = free' : ''}</small></header>
    <h3 className="wp-head">{a.headline}</h3>
    <div className="wp-tiles">{tiles.map(([k, v, t], i) => <span key={k} className={t ? `is-${t}` : ''} style={{ '--i': i }}><em>{k}</em><b>{v}</b></span>)}</div>
    <ol className="wp-drv">{(a.drivers || []).map((d, i) => <li key={i} style={{ '--i': i }}><span>{d.why}</span>
      {d.source === 'ENGINE' ? <i className="wp-src is-eng" data-tip="Measured by FEELESS from the coin's own numbers">⚙ our numbers</i>
        : <a className="wp-src" href={d.source} target="_blank" rel="noopener noreferrer nofollow">↗ {hostOf(d.source)}</a>}</li>)}</ol>
    {a.risk ? <p className="wp-risk">⚠ {a.risk}</p> : null}
    {(a.sources || []).length ? <details className="wp-sources"><summary>{a.sources.length} sources read</summary><ul>{a.sources.map(s => <li key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer nofollow">{s.title || hostOf(s.url)}</a> <small>{hostOf(s.url)}</small></li>)}</ul></details> : null}
    <p className="wp-foot">A read of what moved it — not advice. Sources are other people's words.</p>
  </article>;
}

export default function WhyPump() {
  const [q, setQ] = useState(''); const [busy, setBusy] = useState(false); const [a, setA] = useState(null); const [err, setErr] = useState(''); const [b, setB] = useState(null);
  const box = useRef(null);
  const loadBoard = useCallback(() => fetch(apiUrl('/api/reputation/why-pump-board')).then(r => (r.ok ? r.json() : null)).then(x => x && setB(x)).catch(() => {}), []);
  useEffect(() => { loadBoard(); const t = setInterval(() => { if (!document.hidden) loadBoard(); }, 30000); return () => clearInterval(t); }, [loadBoard]);
  const check = useCallback(async (raw) => {
    const m = mintOf(raw ?? q);
    if (!m) { setErr('Paste a Solana contract address (CA).'); return; }
    setQ(m); setErr(''); setBusy(true); setA(null);
    try {
      const r = await fetch(apiUrl(`/api/reputation/why-pump/${m}`)); const d = await r.json().catch(() => ({}));
      if (!r.ok) setErr(d.detail || 'Could not check it right now.'); else { setA(d); loadBoard(); }
    } catch { setErr('Could not reach FEELESS.'); }
    setBusy(false);
  }, [q, loadBoard]);
  const why = m => { setQ(m); check(m); box.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' }); };
  return <section className="wp m-live" data-testid="why-pump" ref={box}>
    <div className="wp-main">
      <Title />
      <p className="wp-sub">Paste a CA. FEELESS digs through <b>X</b>, the <b>web</b>, <b>Pump callers</b> and the <b>chart</b> until it finds what actually moved the price — with sources.</p>
      <form className="wp-form" onSubmit={e => { e.preventDefault(); check(); }}>
        <input className="m-input" value={q} onChange={e => setQ(e.target.value)} onPaste={e => { const m = mintOf(e.clipboardData.getData('text')); if (m) { e.preventDefault(); check(m); } }}
          placeholder="Paste a contract address…" aria-label="Contract address" data-testid="wp-input" spellCheck={false} />
        <button type="submit" className="m-btn m-go" disabled={busy} data-testid="wp-check">{busy ? 'Digging…' : 'Check'}</button>
      </form>
      <small className="wp-note">{b?.free || 5} new checks a day · a coin someone already checked is free{a?.left != null ? ` · ${a.left} left today` : ''}</small>
      {err ? <p className="wp-err" data-testid="wp-err">{err}</p> : null}
      {busy ? <Working /> : a ? <Answer a={a} /> : null}
    </div>
    <aside className="wp-side">
      <div className="wp-list m-card"><h4><i className="wp-dot" /> MOVING RIGHT NOW</h4>
        {(b?.moving || []).length ? b.moving.map((r, i) => <div key={r.mint} className="wp-row" style={{ '--i': i }}>
          {r.img ? <img src={r.img} alt="" loading="lazy" /> : <i className="wp-ph">{(r.symbol || '?')[0]}</i>}
          <b>${r.symbol || r.mint.slice(0, 4)}</b><em className={r.chg >= 0 ? 'is-up' : 'is-dn'}>{pct(r.chg, 1)}</em>
          <button type="button" className="wp-why" onClick={() => why(r.mint)} data-testid={`wp-why-${r.mint}`}>Why?</button></div>)
          : <p className="wp-empty">Reading the feed…</p>}</div>
      {(b?.recent || []).length ? <div className="wp-list m-card"><h4>LATEST CHECKS</h4>{b.recent.slice(0, 6).map(r => <div key={r.mint} className="wp-row is-recent">
        <b>${r.symbol || r.mint.slice(0, 4)}</b><span>{r.headline}</span><small>{ago(r.at)}</small>
        <button type="button" className="wp-why" onClick={() => why(r.mint)}>Open</button></div>)}</div> : null}
    </aside>
  </section>;
}

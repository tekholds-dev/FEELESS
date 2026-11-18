import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import '../../styles/mediaStudio.css';

// 💵 owner 2026-11-17 ("DO WHATEVER EXCEPT USE MY MONEY TO WASTE ON BULLSHIT", "assure real money readyness"): what his agents spent
// TODAY on his own keys, his day cap and what is left, every receipt row (whose agent, what, $), and the cap he names himself. The server
// refuses any paid call that would pass the cap, before it is sent; this only shows it. One read when it mounts or opens, never a poll.
const money = v => `$${Number(v || 0).toFixed(Number(v || 0) < 0.1 && Number(v || 0) > 0 ? 3 : 2)}`;
const when = at => new Date(Number(at || 0) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export default function SpendChip({ cat, work, seed = null, compact = false, stamp = '' }) {
  const btn = useRef(null); const [at, setAt] = useState(null);   // the panel floats over the page (a desk window clips anything inside it)
  const [ready, setReady] = useState(null); const [checking, setChecking] = useState(false);
  const check = async () => { setChecking(true); setErr(''); try { setReady(await work(cat.id, { op: 'money_ready' })); } catch (x) { setErr(x.message); } setChecking(false); };
  const [s, setS] = useState(seed); const [open, setOpen] = useState(false); const [cap, setCap] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const load = useCallback(() => { if (!cat?.id || !work) return; work(cat.id, { op: 'spend' }).then(j => j?.spend && setS(j.spend)).catch(e => setErr(e.message)); }, [cat?.id, work]);
  useEffect(() => { if (seed) setS(seed); }, [seed]);
  useEffect(() => { if (!seed) load(); }, [load, seed, stamp]);   // `stamp` moves when a request in this folder ends: the total moves with it
  useEffect(() => { if (open) load(); }, [open, load]);
  useEffect(() => {
    if (!open) return undefined;
    const place = () => { const r = btn.current?.getBoundingClientRect(); if (window.innerWidth <= 640) setAt(null); else if (r) setAt({ top: Math.round(r.bottom + 6), right: Math.max(16, Math.round(window.innerWidth - r.right)) }); };
    const key = e => { if (e.key === 'Escape') setOpen(false); };
    place(); window.addEventListener('resize', place); window.addEventListener('scroll', place, true); window.addEventListener('keydown', key);
    return () => { window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true); window.removeEventListener('keydown', key); };
  }, [open]);
  const save = async e => {
    e.preventDefault(); setBusy(true); setErr('');
    try { const j = await work(cat.id, { op: 'spend_cap', text: cap }); setS(j.spend); setCap(''); } catch (x) { setErr(x.message); }
    setBusy(false);
  };
  if (!s) return null;
  const pct = Math.min(100, Math.round(((Number(s.spentUsd) + Number(s.makingUsd || 0)) / Math.max(0.01, Number(s.capUsd))) * 100));
  return <span className={`spc${s.over ? ' is-over' : ''}${compact ? ' is-compact' : ''}`} data-testid="spend-chip">
    <button ref={btn} type="button" className="spc-btn" aria-expanded={open} onClick={() => setOpen(o => !o)} data-testid="spend-open"
      data-tip="What your agents spent today on your own keys. Anything past your day cap is refused before it costs a cent">
      <b>{s.over ? '⛔' : '💵'} {money(s.spentUsd)}</b><small>{compact ? `/ ${money(s.capUsd)}` : `of ${money(s.capUsd)} today`}</small>
      <i aria-hidden="true"><u style={{ '--p': pct / 100 }} /></i></button>
    {open ? createPortal(<><button type="button" className="spc-scrim" aria-label="Close today's spend" tabIndex={-1} onClick={() => setOpen(false)} /><div className="spc-pop m-pop" role="dialog" aria-label="Today's spend" data-testid="spend-pop" style={at ? { top: at.top, right: at.right } : undefined}>
      <header><b>Today on your keys</b><small>{s.calls} paid call{s.calls === 1 ? '' : 's'}{Number(s.makingUsd) ? ` · ${money(s.makingUsd)} still making` : ''} · {money(s.leftUsd)} left</small></header>
      {Object.keys(s.byProvider || {}).length ? <p className="spc-by">{Object.entries(s.byProvider).map(([k, v]) => <span key={k}>{k} <b>{money(v)}</b></span>)}</p> : null}
      {(s.rows || []).length ? <ol className="spc-rows" data-testid="spend-rows">{s.rows.map((r, i) => <li key={i}><time>{when(r.at)}</time><span><b>{r.what}</b><small>{r.agent} · {r.provider}{r.how === 'list price' ? ' · list price' : ''}</small></span><em className="m-num">{money(r.usd)}</em></li>)}</ol>
        : <p className="spc-none">Nothing paid today. Free and local models cost nothing and are not listed.</p>}
      <form className="spc-cap" onSubmit={save}><label htmlFor="spc-cap-in">Day cap, all your agents</label>
        <span><input id="spc-cap-in" className="m-input" inputMode="decimal" value={cap} onChange={e => setCap(e.target.value)} placeholder={String(s.capUsd)} aria-label="Day cap in dollars" data-testid="spend-cap" />
          <button type="submit" className="m-btn" disabled={busy || !cap.trim()} data-testid="spend-cap-save">{busy ? 'Saving…' : 'Set'}</button></span></form>
      <div className="spc-ready"><button type="button" className="m-btn" disabled={checking} onClick={check} data-testid="money-ready"
        data-tip="Free, read-only checks: your key, your credit, the models and links a paid run needs. It never makes anything, so it costs $0">{checking ? 'Checking…' : ready ? (ready.ok ? '✅ Ready. Check again' : '⚠ Check again') : '✅ Check before paying ($0)'}</button>
        {ready ? <ul data-testid="money-ready-rows">{ready.rows.map(r => <li key={r.id} className={r.ok ? 'is-ok' : 'is-no'}><b>{r.ok ? '✓' : '✕'} {r.what}</b><small>{r.say}</small></li>)}</ul> : null}</div>
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    </div></>, document.body) : null}
  </span>;
}

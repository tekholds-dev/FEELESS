import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { ProofHead, ProofKit, ProofTile } from './ProofKit';
import { scoreOf } from '../../lib/proofprint';
import { EcoLive } from './EcoLive';
import '../../styles/ecoFolder.css';

// 📊 PoEco REBUILT (owner 2026-11-13: "forget any ideas on PoEco and just build what you want that competes with the other proofs").
// PROOF OF ECONOMY: a sealed call on the real Solana economy. It reads live DexScreener pools, states one plain rule, calls it blind,
// seals the exact numbers under a hash — and a day later the REAL numbers grade it. The only proof graded entirely by reality:
// no model marks it, no hand marks it, no money moves. Old book proofs still open read-only.
const usd = v => (v == null ? '—' : `${v < 0 ? '−' : ''}$${Math.abs(v) >= 1e6 ? `${(Math.abs(v) / 1e6).toFixed(1)}M` : Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(2)}`);
const mark = g => scoreOf({ kind: 'poe', value: g === 'right' ? 1 : g === 'wrong' ? -1 : null });
const left = due => { const s = due * 1000 - Date.now(); if (s <= 0) return 'at the horn'; const h = Math.floor(s / 3.6e6); return h ? `${h}h ${Math.round((s % 3.6e6) / 6e4)}m left` : `${Math.max(1, Math.round(s / 6e4))}m left`; };

// One pool's sealed numbers: liquidity, 24h volume and the turnover meter the rule runs on.
function PoolCard({ r, lead, tag }) {
  const turn = r.liqUsd ? r.vol24h / r.liqUsd : 0;
  return <article className={`eco-pool${lead ? ' is-lead' : ''}`} data-testid={`eco-pool-${tag}`}>
    <header><b>{r.pair}</b><em>{lead ? 'ITS PICK' : 'THE OTHER'}</em></header>
    <dl><div><dt>LIQUIDITY</dt><dd className="m-num">{usd(r.liqUsd)}</dd></div><div><dt>24H VOLUME</dt><dd className="m-num">{usd(r.vol24h)}</dd></div><div><dt>PRICE</dt><dd className="m-num">${r.priceUsd}</dd></div></dl>
    <span className="eco-turn" data-tip="Turnover: 24h volume ÷ liquidity. The rule's whole input"><small>TURNOVER</small><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, turn / 3))})` }} /></i><b className="m-num">{turn.toFixed(2)}×</b></span>
  </article>;
}

// One market call, open: the question, the rule, both sealed number sets, the hash and the countdown — or the verdict reality wrote.
function MarketCall({ f, onBack, busy, onGrade }) {
  const b = f.baseline || {}; const a = f.after || {};
  return <div className="eco-call" data-testid={`eco-call-${f.id}`}>
    <header className="eco-bh"><button type="button" className="m-btn" onClick={onBack} data-testid="eco-back">← PoEco</button><b>PoEco #{f.n}</b>
      {f.graded ? <em className={`eco-verdict is-${f.graded}`} data-testid="eco-verdict">{f.graded === 'right' ? 'RIGHT' : 'WRONG'} · reality graded it</em>
        : <em className="eco-due m-num" data-tip="Nobody marks this. At the horn the real numbers grade it" data-testid="eco-due">{left(f.due)}</em>}</header>
    <p className="eco-q" data-testid="eco-q">{f.q}</p>
    <p className="eco-rule"><small>ITS RULE</small>{f.rule}</p>
    {b.pick ? <div className="eco-pools"><PoolCard r={b.pick} lead tag="pick" /><PoolCard r={b.other} tag="other" /></div> : null}
    {f.graded ? (a.pick ? <p className="eco-after" data-testid="eco-after"><small>AT THE HORN</small>{a.pick.pair} {usd(a.pick.vol24h)} vs {a.other.pair} {usd(a.other.vol24h)} · margin {usd(a.marginUsd)}</p> : <p className="eco-after">{a.note}</p>)
      : <button type="button" className="m-btn" disabled={busy || f.due * 1000 > Date.now()} onClick={onGrade} data-tip="Fetches the fresh real numbers and grades every due call" data-testid="eco-grade">Grade it now</button>}
    <p className="eco-hash" data-tip="The same read always gives this seal"><small>SEALED</small><code data-testid="eco-hash">{f.hash}</code></p>
  </div>;
}

function Rail({ rows, busy, onCall, onOpen, onCommand }) {
  return <><section className="eco-new m-card" data-testid="eco-prove"><h4><Ic3 e="📊" /> CALL THE MARKET</h4>
    <p className="eco-say">It reads the deepest live pools, states its rule, calls it blind and seals the numbers. Reality grades it in 24h. No model, no mark, no money.</p>
    <button type="button" className="m-btn m-go" disabled={busy} onClick={onCall} data-tip="One sealed call on live DexScreener pools" data-testid="eco-call-go">{busy ? 'Reading the pools…' : 'File a market call'}</button></section>
    <section className="eco-filed" aria-label="Filed PoEco proofs"><h4 className="m-label">FILED <b className="m-num">{rows.length}</b></h4>
      {rows.length ? <div className="eco-tiles" data-testid="eco-tiles">{rows.map((f, i) => <ProofTile key={f.id} i={i} ic="📊" tone={f.graded === 'right' ? 'good' : f.graded === 'wrong' ? 'bad' : 'live'} print={[f.id, mark(f.graded)]} label={`PoEco #${f.n}`} sub={f.kind === 'market' ? (f.graded ? f.graded.toUpperCase() : left(f.due)) : usd(f.net)} tip={f.q || f.topic} onOpen={() => onOpen(f)} testid={`eco-${f.id}`} />)}</div> : <p className="eco-say">No call filed yet. The first one shows here.</p>}</section>
    <ProofKit kind="poe" folders={rows} onCommand={onCommand} /></>;
}

// Legacy book proofs (the old PoEco) still open read-only, so nothing filed is lost.
function OldBook({ f, onBack }) {
  return <div className="eco-call" data-testid={`eco-book-${f.id}`}><header className="eco-bh"><button type="button" className="m-btn" onClick={onBack} data-testid="eco-back">← PoEco</button><b>PoEco #{f.n} · {f.topic}</b>{f.graded ? <em className={`eco-verdict is-${f.graded}`}>{f.graded.toUpperCase()}</em> : null}</header>
    <div className="eco-kpis">{[['INCOME', usd(f.income)], ['COSTS', usd(f.costs)], ['NET', usd(f.net)], ['MARGIN', f.margin == null ? '—' : `${f.margin}%`]].map(([k, v]) => <span key={k}><small>{k}</small><b className="m-num">{v}</b></span>)}</div>
    <p className="eco-hash"><small>PROOF</small><code>{f.hash}</code></p></div>;
}

export function EcoFolder({ cat, d, setD, work, pool, onCommand, onBrowse, focus = null }) {
  const rows = useMemo(() => d?.poeFolders || [], [d?.poeFolders]); const [open, setOpen] = useState(null);
  useEffect(() => { const f = focus?.id && rows.find(x => x.id === focus.id); if (f) setOpen(f); }, [focus?.at, rows.length]);   // eslint-disable-line react-hooks/exhaustive-deps   // 🎯 AGX-1: the picker opens this very proof
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const onRows = useCallback(poeFolders => setD?.(x => ({ ...x, poeFolders })), [setD]);
  const act = useCallback(async body => { setBusy(true); setErr(''); try { const j = await work(cat.id, body); if (j.poeFolders) onRows(j.poeFolders); } catch (e) { setErr(e.message); } finally { setBusy(false); } }, [work, cat.id, onRows]);
  useEffect(() => { if (open) setOpen(o => rows.find(f => f.id === o.id) || o); }, [rows]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (rows.some(f => f.kind === 'market' && !f.graded && f.due * 1000 <= Date.now())) act({ op: 'eco_grade' }); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="prf eco-prf" data-testid="dsk-poe"><ProofHead kind="poe" folders={rows} d={d} cat={cat} pool={pool} work={work} onBrowse={onBrowse} />
    <div className="prf-main">{open ? (open.kind === 'market' ? <MarketCall f={open} onBack={() => setOpen(null)} busy={busy} onGrade={() => act({ op: 'eco_grade' })} /> : <OldBook f={open} onBack={() => setOpen(null)} />) : <EcoLive />}
      {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}</div>
    <aside className="prf-rail"><Rail rows={rows} busy={busy} onCall={() => act({ op: 'eco_call' })} onOpen={setOpen} onCommand={onCommand} /></aside></div>;
}

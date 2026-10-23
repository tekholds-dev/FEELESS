import React, { useEffect, useMemo, useRef, useState } from 'react';
import { blockPlan, spotOf, usd, apyTxt } from '../lib/cityPlan';
import { webglOk } from './FeeCity3D';
import '../styles/familyBlock3d.css';

// 🏙 THE FAMILY BLOCK IN 3D (owner, 2026-10-22: "my family block supposed to look like the new city design and expanding … under construction
// until i actually buy … shows open plots"): the same three.js engine as Fee City, one island that grows with the family's REAL market buildings
// (backend/block_markets.py). Tap a building → its card (value, APY, errands); tap an open plot → add a market. No WebGL (or a test) → a drawn
// CSS block with the same states.
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
const still = () => typeof window !== 'undefined' && (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('reduced-motion-setting'));

export function FamilyBlock3D({ bl, sel, onPick }) {
  const [gl] = useState(webglOk);
  const host = useRef(null); const eng = useRef(null); const [ready, setReady] = useState(false); const [tip, setTip] = useState(null);
  const plan = useMemo(() => blockPlan(bl), [bl]);
  const pickRef = useRef(onPick); pickRef.current = onPick;
  useEffect(() => {
    if (!gl || !host.current) return undefined; let alive = true;
    import('../lib/cityEngine').then(async m => { if (!alive) return; await m.preload(); if (!alive || !host.current) return;
      eng.current = m.createCity(host.current, { onPick: pk => pickRef.current?.(pk), onHover: setTip, lite: lite(), still: still(), day: document.body.classList.contains('theme-day') });
      setReady(true); });
    return () => { alive = false; eng.current?.dispose(); eng.current = null; };
  }, [gl]);
  useEffect(() => { if (ready && eng.current) eng.current.setPlan(plan, {}); }, [ready, plan]);
  useEffect(() => { if (ready && eng.current && sel) eng.current.flyTo(spotOf(plan, sel), 16); }, [ready, sel?.blk, sel?.open]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (!gl) return <BlockGrid bl={bl} sel={sel} onPick={onPick} />;
  return <div className="fb3" data-testid="block-3d"><div className="fb3-host" ref={host} />{!ready ? <p className="fb3-wait">Raising the block…</p> : null}
    {tip ? <span className="fb3-tip">{tip}</span> : null}</div>;
}

// the drawn CSS block: built towers lit, scaffolding + a crane on the ones not built yet, surveyed open plots
export function BlockGrid({ bl, sel, onPick }) {
  const blds = bl?.buildings || []; const open = Math.max(0, bl?.open ?? 3);
  return <div className="fb3-grid" data-testid="block-grid">
    {blds.map((b, i) => <button key={b.key} type="button" className={`fb3-b is-${b.state} k-${b.kind} ${sel?.blk === b.key ? 'is-sel' : ''}`} style={{ '--i': i, '--h': `${b.state === 'built' ? 46 + Math.min(54, Math.log10(1 + (Number(b.usd) || 10)) * 14) : 40}%` }}
      onClick={() => onPick({ blk: b.key })} data-testid={`blk-${b.key}`} data-tip={b.state === 'built' ? `${b.name}: a real position${b.usd ? ` · ${usd(b.usd)}` : ''}${b.apy != null ? ` · APY ${apyTxt(b.apy)}` : ''}` : b.why || `${b.name}: open a position there to build it`}>
      <i className="fb3-tower"><u /></i>{b.state !== 'built' ? <i className="fb3-scaf"><s /></i> : null}
      <span className="fb3-sign"><b>{b.sym || b.name}</b><small>{b.state === 'built' ? (b.usd ? usd(b.usd) : b.band || 'BUILT') : 'UNDER CONSTRUCTION'}</small></span>
      {(b.errands || []).length && b.state === 'built' ? <em className="fb3-pin">{b.errands.length}</em> : null}</button>)}
    {Array.from({ length: open }, (_, k) => <button key={`o${k}`} type="button" className={`fb3-b is-open ${sel?.open === k ? 'is-sel' : ''}`} style={{ '--i': blds.length + k }} onClick={() => onPick({ open: k })}
      data-testid={`open-${k}`} data-tip="An open plot — add a market you use; it builds itself when you open a real position there"><i className="fb3-stakes" /><span className="fb3-sign"><b>OPEN PLOT</b><small>+ add a market</small></span></button>)}
  </div>;
}

// 🗂 the side card: a building's REAL numbers + its errands (own family), or the add-a-market list on an open plot
const PROOF_WORD = { mint: 'token balance', nft: 'position NFT', api: 'vault shares', none: 'no reader yet' };
const RC = 2 * Math.PI * 22;
export function BlockCard({ bl, sel, busy, mine, onAct, onErrand }) {
  if (!bl) return null;
  const b = sel?.blk ? (bl.buildings || []).find(x => x.key === sel.blk) : null;
  if (b) {
    const built = b.state === 'built';
    return <div className={`fbm is-${b.state}`} data-testid="blk-card">
      <div className="fbm-head"><svg className="fbm-ring" viewBox="0 0 56 56" aria-hidden="true"><circle className="t" cx="28" cy="28" r="22" /><circle className="a" cx="28" cy="28" r="22" strokeDasharray={`${((built ? 1 : 0.18) * RC).toFixed(1)} ${RC.toFixed(1)}`} /></svg>
        <div><b>{b.name}</b><small>{built ? '✅ built · a real position' : '🏗 under construction'}</small></div></div>
      <div className="fbm-kv">
        <span style={{ '--i': 0 }} data-tip={mine ? 'What your family wallets hold there right now (live price)' : 'Other families see a band, never a balance'}><em>{mine ? 'YOUR VALUE' : 'VALUE'}</em>
          <b className="fl-tick" key={String(b.usd ?? b.band)}>{mine ? (b.usd ? usd(b.usd) : built ? `${b.n || 1} pos` : '$0') : (b.band || '—')}</b></span>
        <span style={{ '--i': 1 }} data-tip="The market's live yield (pool hub)"><em>APY</em><b>{apyTxt(b.apy)}</b></span>
        <span style={{ '--i': 2 }} data-tip="How FEELESS proves the position — read from the chain or the protocol, never typed in"><em>PROOF</em><b>{PROOF_WORD[b.proof] || '—'}</b></span>
      </div>
      {b.why ? <p className="fbm-why">⚠ {b.why} — it stays under construction.</p> : null}
      {mine && (b.errands || []).length ? <><span className="eyebrow">ERRANDS · REAL MONEY</span><ul className="fbm-errands">{b.errands.map(e => <li key={e.kind}>
        <button type="button" onClick={() => onErrand(e, b)} data-testid={`errand-${e.kind}`} data-tip="Opens the real tool — your wallet signs there"><i>{e.icon}</i><span>{e.text}</span>{e.gain ? <em>+{e.gain} pp</em> : null}</button></li>)}</ul></> : null}
      {mine && bl.canBuild ? <button type="button" className="m-btn" disabled={busy} onClick={() => onAct('remove', b.key)} data-testid="blk-remove" data-tip="Takes the building off the block (your position is untouched)">Remove building</button> : null}
    </div>;
  }
  return <div className="fbm" data-testid="blk-add">
    <div className="fbm-head"><svg className="fbm-ring" viewBox="0 0 56 56" aria-hidden="true"><circle className="t" cx="28" cy="28" r="22" /><circle className="a" cx="28" cy="28" r="22" strokeDasharray={`${(((bl.built || 0) / Math.max(1, (bl.buildings || []).length)) * RC).toFixed(1)} ${RC.toFixed(1)}`} /></svg>
      <div><b>{sel?.open != null ? 'Open plot' : 'The block'}</b><small>{bl.built || 0}/{(bl.buildings || []).length} built{mine && bl.total ? ` · ${usd(bl.total)} in markets` : ''}</small></div></div>
    {mine ? (bl.canBuild ? <><span className="eyebrow">ADD A MARKET YOU USE</span><ul className="fbm-cat">{(bl.catalog || []).map((m, i) => <li key={m.key}>
      <button type="button" disabled={busy || (bl.open ?? 0) < 1} onClick={() => onAct('add', m.key)} style={{ '--i': i }} data-testid={`blk-add-${m.key}`} data-tip={m.proof === 'none' ? m.why : `It builds itself once your wallet holds a real ${m.name} position`}>
        <span><b>{m.name}</b><small>{m.offer}</small></span><i className={`fbm-proof ${m.proof === 'none' ? 'is-none' : ''}`}>{m.proof === 'none' ? 'no reader yet' : PROOF_WORD[m.proof]}</i></button></li>)}</ul></>
      : <p className="fbm-why">Only the Don or the Underboss adds buildings.</p>) : <p className="fbm-why">Every lit building here stands on a real position the family holds.</p>}
  </div>;
}

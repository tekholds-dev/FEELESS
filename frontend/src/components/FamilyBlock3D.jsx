import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MoneyDesk, RangePicture, JOB_OF } from './MoneyDesk';
import { blockPlan, spotOf, usd, apyTxt, TOWN, dollarsSmall } from '../lib/cityPlan';
import { webglOk } from './FeeCity3D';
import { useTownLive } from '../lib/townLive';
import '../styles/familyCity3d.css';
import '../styles/familyBlock3d.css';
import '../styles/familyTown.css';

// 🏙 THE FAMILY BLOCK IN 3D (owner, 2026-10-22: "my family block supposed to look like the new city design and expanding … under construction
// until i actually buy … shows open plots"): the same three.js engine as Fee City, one island that grows with the family's REAL market buildings
// (backend/block_markets.py). Tap a building → its card (value, APY, errands); tap an open plot → add a market. No WebGL (or a test) → a drawn
// CSS block with the same states.
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
const still = () => typeof window !== 'undefined' && (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('reduced-motion-setting'));

const MODE_KEY = 'feeless.city.mode';   // one ☀ / 🌙 for Fee City and every family block
const startMode = () => { try { const m = localStorage.getItem(MODE_KEY); if (m === 'day' || m === 'night') return m; } catch { /* storage blocked */ } return typeof document !== 'undefined' && document.body.classList.contains('theme-day') ? 'day' : 'night'; };

// 🎛 owner, 2026-10-23: "no day and night or expansion options for my family" → the block gets Fee City's controls: 360°, zoom, the whole block,
// ☀ / 🌙 (shared with Fee City), ⤢ the whole window (Esc). A picked building's card POPS OUT over the stage (`pop`) — in the window or expanded.
export function FamilyBlock3D({ bl, sel, onPick, coins = null, pop = null, onClosePop = null, lp = null }) {
  const [gl] = useState(webglOk); const town = useTownLive(!!(bl?.town || []).length);
  const host = useRef(null); const eng = useRef(null); const [ready, setReady] = useState(false); const [tip, setTip] = useState(null);
  const [mode, setMode] = useState(startMode); const [full, setFull] = useState(false); const [spin, setSpin] = useState(false);
  const plan = useMemo(() => blockPlan(bl, { coins, town, lp }), [bl, coins, town, lp]);
  const pickRef = useRef(onPick); pickRef.current = onPick;
  useEffect(() => {
    if (!gl || !host.current) return undefined; let alive = true;
    import('../lib/cityEngine').then(async m => { if (!alive) return; await m.preload(); if (!alive || !host.current) return;
      eng.current = m.createCity(host.current, { onPick: pk => pickRef.current?.(pk), onHover: setTip, lite: lite(), still: still(), day: startMode() === 'day' });
      setReady(true); });
    return () => { alive = false; eng.current?.dispose(); eng.current = null; };
  }, [gl]);
  useEffect(() => { if (ready && eng.current) eng.current.setPlan(plan, {}); }, [ready, plan]);
  useEffect(() => { if (ready && eng.current && sel) eng.current.flyTo(spotOf(plan, sel), 16); }, [ready, sel?.blk, sel?.open, sel?.town, sel?.lp]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { eng.current?.setMode(mode); try { localStorage.setItem(MODE_KEY, mode); } catch { /* storage blocked */ } }, [mode, ready]);
  useEffect(() => { eng.current?.spin(spin); }, [spin, ready]);
  useEffect(() => {   // ⤢ the whole window; Esc closes the pop-out first, then the expansion
    if (!full) return undefined; const esc = e => { if (e.key === 'Escape' && !pop) setFull(false); };
    document.body.classList.add('fc3-lock'); window.addEventListener('keydown', esc); const t = setTimeout(() => eng.current?.resize(), 60);
    return () => { document.body.classList.remove('fc3-lock'); window.removeEventListener('keydown', esc); clearTimeout(t); setTimeout(() => eng.current?.resize(), 60); };
  }, [full, pop]);
  if (!gl) return <>{<BlockGrid bl={bl} sel={sel} onPick={onPick} town={town} lp={lp} />}{pop ? <div className="fb3-pop is-flat" data-testid="block-pop">{pop}</div> : null}</>;
  return <div className={`fb3 is-${mode} ${full ? 'is-full' : ''}`} data-testid="block-3d"><div className="fb3-host" ref={host} />{!ready ? <p className="fb3-wait">Raising the block…</p> : null}
    {tip?.label ? <span className="fb3-tip" style={{ transform: `translate(${tip.x + 14}px, ${tip.y + 12}px)` }}>{tip.label}</span> : null}
    {pop ? <div className="fb3-pop" role="dialog" aria-label="The building" data-testid="block-pop"><button type="button" className="fb3-x" onClick={onClosePop} aria-label="Close" data-tip="Back to the block (Esc)" data-testid="block-pop-x">✕</button>{pop}</div> : null}
    <div className="fcy-ctl fb3-ctl">
      <button type="button" className={spin ? 'active' : ''} onClick={() => setSpin(v => !v)} aria-pressed={spin} data-tip="Slowly turn the block" data-testid="block-spin">{spin ? '⏸' : '⟲ 360°'}</button>
      <button type="button" onClick={() => eng.current?.zoom(1.25)} data-tip="Zoom in" aria-label="Zoom in">＋</button>
      <button type="button" onClick={() => eng.current?.zoom(0.8)} data-tip="Zoom out" aria-label="Zoom out">－</button>
      <button type="button" onClick={() => { onClosePop?.(); eng.current?.frameAll(); }} data-tip="See the whole block" aria-label="Whole block" data-testid="block-home">⌂</button>
      <button type="button" onClick={() => setMode(m => (m === 'day' ? 'night' : 'day'))} aria-pressed={mode === 'day'} data-tip={mode === 'day' ? 'Night: neon + lit windows' : 'Day: sun, blue sky'} data-testid="block-mode" aria-label="Day or night">{mode === 'day' ? '🌙' : '☀'}</button>
      <button type="button" className={full ? 'active' : ''} onClick={() => setFull(f => !f)} aria-pressed={full} data-tip={full ? 'Back to the page (Esc)' : 'Expand the block to the whole window'} data-testid="block-full" aria-label="Expand">{full ? '⤡' : '⤢'}</button>
    </div></div>;
}

// the drawn CSS block: built towers lit, scaffolding + a crane on the ones not built yet, surveyed open plots
export function BlockGrid({ bl, sel, onPick, town = null, lp = null }) {
  const blds = bl?.buildings || []; const open = Math.max(0, bl?.open ?? 3);
  return <div className="fb3-grid" data-testid="block-grid">
    {blds.map((b, i) => <button key={b.key} type="button" className={`fb3-b is-${b.state} k-${b.kind} ${sel?.blk === b.key ? 'is-sel' : ''}`} style={{ '--i': i, '--h': `${b.state === 'built' ? 46 + Math.min(54, Math.log10(1 + (Number(b.usd) || 10)) * 14) : 40}%` }}
      onClick={() => onPick({ blk: b.key })} data-testid={`blk-${b.key}`} data-tip={b.state === 'built' ? `${b.name}: a real position${b.usd ? ` · ${usd(b.usd)}` : ''}${b.apy != null ? ` · APY ${apyTxt(b.apy)}` : ''}` : b.why || `${b.name}: open a position there to build it`}>
      <i className="fb3-tower"><u /></i>{b.state !== 'built' ? <i className="fb3-scaf"><s /></i> : null}
      <span className="fb3-sign"><b>{b.sym || b.name}</b><small>{b.state === 'built' ? (b.usd ? usd(b.usd) : b.band || 'BUILT') : 'UNDER CONSTRUCTION'}</small></span>
      {(b.errands || []).length && b.state === 'built' ? <em className="fb3-pin">{b.errands.length}</em> : null}</button>)}
    {(lp || []).filter(p => !p.empty).map((p, j) => <button key={`lp-${p.id}`} type="button" className={`fb3-b is-built is-lp ${p.inRange ? 'is-in' : 'is-out'} ${sel?.lp === p.id ? 'is-sel' : ''}`} style={{ '--i': blds.length + j, '--h': '64%' }}
      onClick={() => onPick({ lp: p.id })} data-testid={`blk-lp-${p.id}`} data-tip={`${p.sym}: your LP position · ${p.inRange ? 'in range, earning' : 'out of range, earning 0'} — tap to claim, remove or close`}>
      <i className="fb3-tower"><u /></i><span className="fb3-sign"><b>{p.sym}</b><small>{p.inRange ? 'IN RANGE' : 'OUT OF RANGE'} · +{dollarsSmall(p.feeUsd)}</small></span></button>)}
    {(bl?.town || []).filter(k => TOWN[k]).map((k, j) => { const t = TOWN[k]; const tl = town?.[k]; return <button key={`t-${k}`} type="button" className={`fb3-b is-built is-town a-${t.art} ${sel?.town === k ? 'is-sel' : ''}`}
      style={{ '--i': blds.length + j, '--h': k === 'tt' ? '96%' : '70%', '--tc': t.color }} onClick={() => onPick({ town: k })} data-testid={`town-b-${k}`} data-tip={`${t.name} — ${tl?.line || t.sub}. Tap to walk in: the real tool opens over the block`}>
      <i className="fb3-tower"><u /></i><span className="fb3-sign"><b>{t.name}</b>{tl ? <small className={`fb3-live is-${tl.tone}`} key={tl.line}>{tl.line}</small> : <small>{t.sub}</small>}</span></button>; })}
    {Array.from({ length: open }, (_, k) => <button key={`o${k}`} type="button" className={`fb3-b is-open ${sel?.open === k ? 'is-sel' : ''}`} style={{ '--i': blds.length + k }} onClick={() => onPick({ open: k })}
      data-testid={`open-${k}`} data-tip="An open plot — add a market you use; it builds itself when you open a real position there"><i className="fb3-stakes" /><span className="fb3-sign"><b>OPEN PLOT</b><small>+ add a market</small></span></button>)}
  </div>;
}

// 🗂 the side card: a building's REAL numbers + its errands (own family), or the add-a-market list on an open plot
const PROOF_WORD = { mint: 'token balance', nft: 'position NFT', api: 'vault shares', none: 'no reader yet' };
const RC = 2 * Math.PI * 22;
// a protocol whose own deposit needs its SDK: the same job runs here through the in-place providers (said plainly, never a link out)
const SDK_NOTE = { kamino: 'Kamino', marginfi: 'marginfi', save: 'Save', meteora: 'Meteora', orca: 'Orca', raydium: 'Raydium', pumpswap: 'PumpSwap', phoenix: 'Phoenix' };
export function BlockCard({ bl, sel, busy, mine, onAct, onErrand }) {
  const [tool, setTool] = useState(null);   // 🎯 an errand's in-place tool: the drawn range, or the money desk
  useEffect(() => { setTool(null); }, [sel?.blk]);
  if (!bl) return null;
  const b = sel?.blk ? (bl.buildings || []).find(x => x.key === sel.blk) : null;
  if (b) {
    const built = b.state === 'built'; const job = JOB_OF[b.kind] || 'lend';
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
        <button type="button" onClick={() => { const r = onErrand(e, b); if (r === 'range' || r === 'desk') setTool(r); }} data-testid={`errand-${e.kind}`} data-tip="Runs right here — your wallet signs"><i>{e.icon}</i><span>{e.text}</span>{e.gain ? <em>+{e.gain} pp</em> : null}</button></li>)}</ul></> : null}
      {tool === 'range' ? <RangePicture /> : null}
      <MoneyDesk job={job} prefer={b.sym} proto={job === 'lp' ? b.name : null} compact
        title={job === 'lp' ? `${String(b.name).toUpperCase()} · TRADE IT OR EARN` : built ? `${String(b.sym || b.name).toUpperCase()} · ADD MORE` : `BUILD ${String(b.name).toUpperCase()} FOR REAL`}
        note={SDK_NOTE[b.key] ? (job === 'lp' ? `${SDK_NOTE[b.key]} LP positions need ${SDK_NOTE[b.key]}'s SDK — not in FEELESS yet. Trade its busiest pool here, or earn on SOL / USDC with no range to watch.` : `${SDK_NOTE[b.key]}'s own deposit needs its SDK — the same kind of yield runs here through these providers.`) : null} />
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

// 🏘 THE TOWN PICKER (owner, 2026-10-23: "let my family pick which buildings our town has — Perps, Trench Towers, Pools"): every tool building as a
// drawn mini building (its own roof + lit windows, the standing ones glow and breathe), N / 6 meter, STAND / TAKE DOWN for the Don / Underboss;
// a standing one opens its real tool over the block. Visitors see which tools the family runs.
export function TownPicker({ bl, busy, mine, onAct, onOpen, open }) {
  const live = useTownLive(!!bl);
  if (!bl) return null;
  const on = bl.town || []; const max = bl.townMax || 6; const all = (bl.townAll || Object.keys(TOWN)).filter(k => TOWN[k]); const can = mine && bl.canBuild;
  return <div className="ftp" data-testid="town-picker">
    <header><span><b>🏘 {mine ? 'YOUR TOWN' : 'THEIR TOWN'}</b><small>{on.length}/{max} tool buildings{mine ? ' · tap one to walk in' : ''}</small></span>
      <i className="ftp-meter" aria-hidden="true">{Array.from({ length: max }, (_, k) => <u key={k} className={k < on.length ? 'on' : ''} style={{ '--i': k }} />)}</i></header>
    <ul>{all.map((k, i) => { const t = TOWN[k]; const is = on.includes(k); return <li key={k} className={`${is ? 'is-on' : ''} ${open === k ? 'is-open' : ''}`} style={{ '--i': i, '--tc': t.color }}>
      <button type="button" className="ftp-go" disabled={!is} onClick={() => onOpen(k)} aria-pressed={open === k} data-testid={`town-open-${k}`}
        data-tip={is ? `${t.name} — walk in: the real tool opens over the block` : `${t.name} isn't standing in this town${can ? ' — stand it first' : ''}`}>
        <i className={`ftp-art a-${t.art}`} aria-hidden="true"><s /><u /><em /></i><span><b>{t.name}</b>{is && live?.[k] ? <small className={`ftp-live is-${live[k].tone}`} key={live[k].line} data-testid={`town-live-${k}`}>{live[k].line}</small> : <small>{t.sub}</small>}</span></button>
      {can ? <button type="button" className={`ftp-tog ${is ? 'is-on' : ''}`} disabled={busy || (!is && on.length >= max)} onClick={() => onAct(is ? 'tdel' : 'tadd', k)} aria-pressed={is}
        data-testid={`town-tog-${k}`} data-tip={is ? `Take ${t.name} down (frees a slot)` : on.length >= max ? `The town holds ${max} — take one down first` : `Stand ${t.name} in your town`}>{is ? 'STANDING' : '+ STAND'}</button>
        : is ? <em className="ftp-badge">STANDING</em> : null}</li>; })}</ul>
    {mine && !bl.canBuild ? <p className="fbm-why">Only the Don or the Underboss picks the town's buildings.</p> : null}
  </div>;
}

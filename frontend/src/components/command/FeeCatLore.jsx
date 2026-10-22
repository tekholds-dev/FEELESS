import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useGlide } from '../../lib/useGlide';
import '../../styles/feeCatLore.css';

// 📜 THE LEGEND OF FEE (owner P2: "FeeCat lore + other tabs — only the top was redone"; FeeCat = violet night). A drawn rooftop at night: Fee's
// silhouette with eyes that blink, the moon, and NINE LANTERNS = her nine lives, lit from her live discipline (feecat_brain: a loss −1, a win +1,
// 0 = she naps). Under it the legend as five chapter cards, each carrying a LIVE number (her record, lives, balance vs start, Fee-Back state,
// the cats), then the Fee-Back return path + calculator as segmented tabs. Honest: distributions stay "planned" until they are real.
export const CHAPTERS = [
  ['born', 'I · BORN IN THE TRENCHES', 'Fee is FEELESS\'s first cat: a trading cat that lives on-chain and trades in the open.'],
  ['lives', 'II · NINE LIVES', 'Every loss costs a life, a win in 24h earns one back. At zero she naps — she can only ever trade LESS.'],
  ['record', 'III · HER RECORD', 'Every trade she closes is on her wall — wins, losses, the SOL she made or lost. No edits.'],
  ['feeback', 'IV · THE FEE-BACK', 'FEECAT is the delivery asset for Fee-Back: part of FEELESS fees returned to holders — distributions are planned, not live.'],
  ['cats', 'V · THE CATS', 'Fee is the first. Every FEELESS cat after her trades on the same discipline.'],
];
const sol = v => `${(Number(v) || 0) >= 0 ? '+' : ''}${(Number(v) || 0).toFixed(2)} SOL`;
// pure: a chapter's live number from the cat profile (+ the FEECAT asset)
export function chapterStat(key, p, asset) {
  const c = p?.cat || {}; const d = p?.discipline || {}; const s = p?.stats || {};
  if (key === 'born') return [`LEVEL ${c.level || 1}`, `${(Number(c.balanceSol) || 0).toFixed(2)} SOL in her bag`];
  if (key === 'lives') return [`${d.lives ?? '—'} / ${d.maxLives ?? 9}`, d.pause ? 'napping — no new trades' : d.why || 'normal size'];
  if (key === 'record') return [`${c.wins || 0}W · ${c.losses || 0}L`, s.trades ? `${sol(c.realizedPnlSol)} · ROI ${s.roiPct}%` : 'first trade still to come'];
  if (key === 'feeback') return ['PLANNED', asset?.status === 'market_observed' ? 'FEECAT market observed' : 'awaiting a FEECAT market'];
  return ['COLLECTION', 'meet every FEELESS cat'];
}

function Rooftop({ lives = 9, max = 9, nap }) {
  return <div className={`fcl-roof ${nap ? 'is-nap' : ''}`} aria-hidden="true">
    <span className="fcl-moon" /><span className="fcl-stars">{Array.from({ length: 16 }, (_, i) => <i key={i} style={{ '--i': i }} />)}</span>
    <svg className="fcl-city" viewBox="0 0 400 120" preserveAspectRatio="xMidYMax slice">{Array.from({ length: 12 }, (_, i) => { const h = 40 + ((i * 41) % 60); return <g key={i}>
      <rect x={i * 34} y={120 - h} width="30" height={h} className="fcl-bld" />{Array.from({ length: Math.floor(h / 14) }, (_, r) => <rect key={r} x={i * 34 + 6 + (r % 2) * 10} y={120 - h + 8 + r * 14} width="4" height="5" className={(r + i) % 3 ? 'fcl-win' : 'fcl-win is-on'} />)}</g>; })}</svg>
    <svg className="fcl-cat" viewBox="0 0 120 110"><path d="M20 108 C 18 70, 30 52, 52 50 L 46 22 L 62 40 C 70 38, 78 38, 86 40 L 100 22 L 96 52 C 110 60, 112 84, 104 108 Z" className="fcl-body" />
      <path d="M104 100 C 120 96, 122 74, 112 66" className="fcl-tail" /><ellipse cx="66" cy="62" rx="5" ry="6" className="fcl-eye" /><ellipse cx="84" cy="62" rx="5" ry="6" className="fcl-eye e2" /></svg>
    <span className="fcl-ledge" />
    <span className="fcl-lanterns" data-tip={`${lives} of ${max} lives left — a loss blows one out, a win in 24h lights one`}>{Array.from({ length: max }, (_, i) => <i key={i} className={i < lives ? 'is-lit' : ''} style={{ '--i': i }}><b /></i>)}</span>
    {nap ? <span className="fcl-zz">z z Z</span> : null}
  </div>;
}

export function FeeCatLore({ asset, community, onSelect, children }) {
  const [p, setP] = useState(null); const [tab, setTab] = useState('path');
  useEffect(() => { let on = true; const go = () => fetch('/api/cats/leader/profile').then(r => (r.ok ? r.json() : null)).then(x => { if (on && x) setP(x); }).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { on = false; clearInterval(t); }; }, []);
  const d = p?.discipline || {}; const lives = useGlide(d.lives ?? 9);
  return <section className="fcl" data-testid="feecat-lore">
    <header className="fcl-hero">
      <Rooftop lives={Math.round(lives)} max={d.maxLives || 9} nap={d.pause} />
      <div className="fcl-copy"><span className="fcl-eyebrow">📜 THE LEGEND OF FEE</span><h1>The first cat of FEELESS.</h1>
        <p className="fcl-tag" data-testid="feecat-launch-state">{asset?.status === 'market_observed' ? 'MARKET OBSERVED · DISTRIBUTIONS PLANNED' : 'AWAITING MARKET · DISTRIBUTIONS PLANNED'}</p>
        <div className="fcl-ctas"><Link className="m-btn m-go" to="/terminal/feecat/cats" data-testid="feecat-collection-link">🐱 Meet the cats</Link>
          {asset?.pair ? <button type="button" className="m-btn" onClick={() => onSelect?.(asset.pair)} data-testid="feecat-open-market">Open FEECAT market ↗</button> : null}</div></div>
    </header>
    <ol className="fcl-chapters">{CHAPTERS.map(([k, title, line], i) => { const [big, small] = chapterStat(k, p, asset);
      return <li key={k} className={`fcl-ch k-${k}`} style={{ '--i': i }} data-testid={`feecat-ch-${k}`}><em>{title}</em><b className="m-num">{big}</b><small>{small}</small><p>{line}</p>
        {k === 'cats' ? <Link to="/terminal/feecat/cats" className="fcl-go">open ›</Link> : k === 'feeback' ? <Link to="/terminal/feeback" className="fcl-go">Fee-Back ›</Link> : k === 'record' ? <Link to="/terminal/feecat" className="fcl-go" onClick={e => { e.preventDefault(); window.dispatchEvent(new CustomEvent('feeless:feecat-view', { detail: 'desk' })); }}>her wall ›</Link> : null}</li>; })}</ol>
    <div className="fcl-stats">{[['FEECAT RECEIVED', 'No verified distributions'], ['TREASURY', 'Not published / unverified'], ['TRENCHES · 7D', community?.messages != null ? `${community.messages} real messages` : 'connecting'],
      ['FEECAT MARKET', asset?.status === 'market_observed' && asset?.pair?.priceUsd ? `$${Number(asset.pair.priceUsd).toPrecision(3)}` : 'awaiting a market']].map(([k, v], i) => <span key={k} style={{ '--i': i }}><em>{k}</em><b data-testid={`feecat-stat-${i}`}>{v}</b></span>)}</div>
    <div className="m-seg fcl-tabs" role="tablist" aria-label="Fee-Back">{[['path', '↻ The return path'], ['calc', '🧮 Fee-Back calculator']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`feecat-tab-${k}`}>{l}</button>)}</div>
    <div className="fcl-pane">{children ? children(tab) : null}</div>
  </section>;
}

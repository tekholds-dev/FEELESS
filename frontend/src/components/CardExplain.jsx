import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { FuseCard } from './FuseCard';

// 🔍 Explain this card: a quick, plain-words breakdown of the Lab's live card — every line of it. Click outside or Esc → Lab.
const $ = v => { const n = v || 0; return n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e4 ? `$${(n / 1e3).toFixed(1)}K` : n >= 100 ? `$${Math.round(n)}` : `$${n.toFixed(2)}`; };
const pc = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;

export function CardExplain({ prev, card, onClose }) {
  useEffect(() => { const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  const fees = prev.usd ? 0.0001 * prev.legs.length * prev.solUsd : 0;
  const replay = prev.usd * (prev.backtest24hPct || 0) / 100;
  return createPortal(<div className="cx-shade" role="presentation" onClick={onClose} data-testid="card-explain">
    <div className="cx" role="dialog" aria-modal="true" aria-label="What this card is" onClick={e => e.stopPropagation()}>
      <button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button>
      <div className="cx-card">{card}</div>
      <div className="cx-body">
        <span className="m-label">🔍 THIS CARD, LINE BY LINE</span>
        <p className="cx-lead">You put in <b>{$(prev.usd)}</b> ({prev.sol} SOL). It buys <b>{prev.legs.length} coins</b> in one wallet approval — you hold them, nobody else does.</p>
        <ol className="cx-legs">{prev.legs.map((l, i) => <li key={l.pairAddress} style={{ '--i': i }}>
          <b>{l.runner ? '🏃 ' : '🏊 '}{l.symbol} · {Math.round(l.weight)}%</b>
          <span>{$(l.usd)} of your money ({l.sol} SOL). {l.runner ? `A pre-bond runner from the live board — exits: ${l.exits || 'its lane plan'}.` : `A live pool${l.dex ? ` on ${l.dex}` : ''} with ${$(l.liquidityUsd)} of depth.`}</span>
          {(() => { const mv = l.replayPct ?? l.change24h ?? 0; const h = l.replayH ?? 24; return <em className={mv >= 0 ? 'm-pos' : 'm-neg'}>{h ? `Last ${h >= 1 ? `${h}h` : '5m'}` : 'Too new to replay'}{h ? `: ${pc(mv)} → ${mv >= 0 ? '+' : '−'}${$(Math.abs(l.usd * mv / 100))} on your slice` : ''}{h && h < 24 ? ' (pool is younger than 24h)' : ''}</em>; })()}
        </li>)}</ol>
        <dl className="cx-sum">
          <dt>Grade {prev.score.grade}</dt><dd>{prev.score.parts.map(p => `${p.part} ${p.points}`).join(' · ')} — depth, healthy trading, calm prices, no rug flags.</dd>
          <dt>24h replay</dt><dd className={replay >= 0 ? 'm-pos' : 'm-neg'}>{replay >= 0 ? '+' : '−'}{$(Math.abs(replay))} — what this mix did yesterday. Not a promise.</dd>
          <dt>Pool APR</dt><dd>{Math.round(prev.blendedAprPct)}% — how busy the pools are. Paid to liquidity providers, not to you.</dd>
          <dt>Costs</dt><dd>≈ {$(fees)} network + the normal FEELESS fee per coin (exact numbers on the receipt before you sign).</dd>
          {prev.impactWarn?.length > 0 && <><dt>Size guard</dt><dd className="m-neg">{prev.impactWarn.join(', ')}: your slice is &gt;1% of that pool — expect price impact.</dd></>}
          <dt>After you buy</dt><dd>My cards: 💰 take 50%, ⇄ switch one coin per 24h, ↩ withdraw all — any time.</dd>
        </dl>
        <button type="button" className="m-btn primary m-go" onClick={onClose}>Got it — back to the Lab</button>
      </div>
    </div>
  </div>, document.body);
}

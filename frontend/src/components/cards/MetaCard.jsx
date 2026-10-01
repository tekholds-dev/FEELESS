import React, { useEffect, useId, useRef } from 'react';
import { apiUrl } from '../../lib/api';

// A FEELESS card: front = art, back = lore + money. Drag to turn it in 3D, click (or Enter) to flip.
// Motion is transform-only and written straight to the element in rAF (no re-render per frame);
// reduced-motion users get an instant flip and no drag spin.
const RANK = { common: 1, rare: 2, epic: 3, legendary: 4, mythic: 5 };
const KIND = { badge: 'BADGE', season: 'SEASON', weekly: 'DROP' };
const src = u => (u && u.startsWith('/') ? apiUrl(u) : u);
const sol = v => (v >= 1 ? v.toFixed(2) : v >= 0.01 ? v.toFixed(3) : v > 0 ? v.toFixed(5) : '0');
const serial = key => { let h = 7; for (const c of String(key)) h = (h * 31 + c.charCodeAt(0)) % 99991; return String(h).padStart(5, '0'); };
const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// Rarity crest: more rank = more ornate frame. SVG so it stays crisp at any size.
function Crest({ card, id }) {
  const r = RANK[card.rarity] || 2;
  const pts = (n, rad, rot = -90) => Array.from({ length: n }, (_, i) => { const a = ((360 / n) * i + rot) * Math.PI / 180; return `${50 + rad * Math.cos(a)},${50 + rad * Math.sin(a)}`; }).join(' ');
  const star = Array.from({ length: 16 }, (_, i) => { const a = (22.5 * i - 90) * Math.PI / 180; const rad = i % 2 ? 36 : 47; return `${50 + rad * Math.cos(a)},${50 + rad * Math.sin(a)}`; }).join(' ');
  return <svg className="mc-crest" viewBox="0 0 100 100" aria-hidden="true">
    <defs>
      <linearGradient id={`${id}g`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="var(--a)" /><stop offset=".5" stopColor="#ffffff" stopOpacity=".85" /><stop offset="1" stopColor="var(--b)" /></linearGradient>
      <clipPath id={`${id}c`}><circle cx="50" cy="50" r="29" /></clipPath>
    </defs>
    {r >= 4 && <polygon points={star} fill="none" stroke={`url(#${id}g)`} strokeWidth="1.2" opacity=".9" />}
    {r >= 5 && <circle cx="50" cy="50" r="48" fill="none" stroke="var(--b)" strokeWidth=".8" strokeDasharray="1 3" />}
    {r === 3 ? <polygon points={pts(8, 40, -67.5)} fill="rgba(0,0,0,.45)" stroke={`url(#${id}g)`} strokeWidth="2.2" />
      : r === 2 ? <polygon points={pts(6, 40)} fill="rgba(0,0,0,.45)" stroke={`url(#${id}g)`} strokeWidth="2.2" />
        : <circle cx="50" cy="50" r="38" fill="rgba(0,0,0,.45)" stroke={`url(#${id}g)`} strokeWidth={r >= 4 ? 3 : 2} />}
    {r >= 3 && Array.from({ length: r >= 4 ? 12 : 8 }, (_, i) => { const a = ((360 / (r >= 4 ? 12 : 8)) * i) * Math.PI / 180; return <line key={i} x1={50 + 33 * Math.cos(a)} y1={50 + 33 * Math.sin(a)} x2={50 + 36 * Math.cos(a)} y2={50 + 36 * Math.sin(a)} stroke="var(--a)" strokeWidth="1.4" />; })}
    <circle cx="50" cy="50" r="30" fill="#020805" stroke="var(--a)" strokeOpacity=".5" />
    {card.art ? <image href={src(card.art)} x="21" y="21" width="58" height="58" preserveAspectRatio="xMidYMid slice" clipPath={`url(#${id}c)`} />
      : <text x="50" y="61" textAnchor="middle" fontSize="30">{card.glyph || '✦'}</text>}
  </svg>;
}

// Design layer patterns (static; the whole card moves, the pattern never animates on its own).
function Pattern({ design, id }) {
  if (design === 'circuit') return <svg className="mc-pattern" viewBox="0 0 200 280" preserveAspectRatio="none" aria-hidden="true">
    {[[10, 40, 70, 40, 90, 60, 150], [190, 90, 140, 90, 120, 110, 60], [20, 200, 80, 200, 100, 180, 170], [180, 250, 120, 250, 100, 230, 40]].map((p, i) =>
      <g key={i}><polyline points={`${p[0]},${p[1]} ${p[2]},${p[3]} ${p[4]},${p[5]} ${p[6]},${p[5]}`} fill="none" stroke="var(--a)" strokeOpacity=".35" strokeWidth="1.2" /><circle cx={p[6]} cy={p[5]} r="2.6" fill="var(--a)" /></g>)}
  </svg>;
  if (design === 'obsidian') return <svg className="mc-pattern" viewBox="0 0 200 280" preserveAspectRatio="none" aria-hidden="true">
    {[[0, 0, 110, 0, 40, 90], [110, 0, 200, 0, 160, 120], [40, 90, 160, 120, 90, 200], [0, 0, 40, 90, 0, 170], [200, 0, 200, 190, 160, 120], [0, 170, 90, 200, 0, 280], [90, 200, 200, 190, 200, 280], [0, 280, 90, 200, 200, 280]].map((t, i) =>
      <polygon key={i} points={`${t[0]},${t[1]} ${t[2]},${t[3]} ${t[4]},${t[5]}`} fill={`rgba(255,255,255,${0.015 + (i % 3) * 0.02})`} stroke="var(--b)" strokeOpacity=".35" strokeWidth=".8" />)}
  </svg>;
  if (design === 'ember') return <svg className="mc-pattern" viewBox="0 0 200 280" preserveAspectRatio="none" aria-hidden="true">
    <defs><pattern id={`${id}hx`} width="24" height="41.6" patternUnits="userSpaceOnUse"><path d="M12 0 L24 6.9 L24 20.8 L12 27.7 L0 20.8 L0 6.9 Z" fill="none" stroke="var(--b)" strokeOpacity=".22" strokeWidth=".8" /></pattern></defs>
    <rect width="200" height="280" fill={`url(#${id}hx)`} />
  </svg>;
  return null;
}

// back: optional custom back face (quest badges show their tasks + perks there instead of lore/money).
export function MetaCard({ card, size = 'md', interactive = false, flipped, onFlip, className = '', back = null }) {
  const id = `mc${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const el = useRef(null);
  const sheen = useRef(null);
  const rot = useRef({ x: 0, y: flipped ? 180 : 0 });
  const drag = useRef(null);
  const paint = (animate) => {
    const n = el.current; if (!n) return;
    n.style.transition = animate && !reduced() ? 'transform .45s cubic-bezier(.2,.8,.2,1)' : 'none';
    n.style.transform = `rotateX(${rot.current.x}deg) rotateY(${rot.current.y}deg)`;
    if (sheen.current) sheen.current.style.transform = `translate3d(${(rot.current.y % 360) * -0.35}%, ${rot.current.x * 0.8}%, 0)`;
  };
  useEffect(() => { rot.current = { x: 0, y: flipped ? 180 : 0 }; paint(true); }, [flipped]); // eslint-disable-line react-hooks/exhaustive-deps
  const flip = () => { const face = Math.round(rot.current.y / 180) * 180; rot.current = { x: 0, y: face + 180 }; paint(true); onFlip?.(Math.abs(Math.round(rot.current.y / 180)) % 2 === 1); };
  const down = e => { if (!interactive) return; drag.current = { x: e.clientX, y: e.clientY, rx: rot.current.x, ry: rot.current.y, moved: 0, raf: 0 }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => {
    const g = drag.current; if (!g || reduced()) return;
    const dx = e.clientX - g.x; const dy = e.clientY - g.y; g.moved = Math.max(g.moved, Math.abs(dx) + Math.abs(dy));
    rot.current = { x: Math.max(-28, Math.min(28, g.rx - dy * 0.35)), y: g.ry + dx * 0.55 };
    if (!g.raf) g.raf = requestAnimationFrame(() => { g.raf = 0; paint(false); });
  };
  const up = () => {
    const g = drag.current; drag.current = null; if (!g) return;
    if (g.moved < 6) { flip(); return; }
    const face = Math.round(rot.current.y / 180) * 180; rot.current = { x: 0, y: face }; paint(true); onFlip?.(Math.abs(face / 180) % 2 === 1);
  };
  const clickOnly = () => { if (!interactive) onFlip?.(); };
  const r = card.rarity || 'rare';
  const style = { '--a': card.accent || '#19f58f', '--b': card.accent2 || '#f5c451' };
  const money = card.earns || [];
  const alive = card.motion === 'alive';
  return <div className={`mc-stage mc-${size} ${alive ? 'is-alive' : ''} ${className}`} style={style}><div className="mc-idle">
    <div ref={el} className={`mc d-${card.design || 'holo'} r-${r}`} role={interactive ? 'button' : undefined} tabIndex={interactive ? 0 : undefined}
      aria-label={interactive ? `${card.title} card — drag to turn, click to flip` : undefined}
      onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onClick={clickOnly}
      onKeyDown={e => { if (interactive && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); flip(); } }} data-testid="meta-card">
      <div className="mc-face mc-front">
        <div className="mc-bg" /><Pattern design={card.design} id={id} /><div className="mc-sheen" ref={sheen} />{alive && <><div className="mc-sweep" /><div className="mc-glow" /></>}
        <div className="mc-top"><span>{KIND[card.kind] || 'CARD'}</span><i className="mc-pips" aria-label={r}>{Array.from({ length: 5 }, (_, i) => <b key={i} className={i < (RANK[r] || 2) ? 'on' : ''} />)}</i></div>
        <Crest card={card} id={id} />
        <div className="mc-name"><b>{card.title}</b><small>{card.subtitle}</small></div>
        <div className="mc-foot"><span>{r.toUpperCase()}</span><span>#{serial(card.key)}</span><span>{card.holders ?? 0} held</span></div>
      </div>
      {back ? <div className="mc-face mc-back"><div className="mc-bg" /><Pattern design={card.design} id={`${id}b`} />{back}</div> : <div className="mc-face mc-back">
        <div className="mc-bg" /><Pattern design={card.design} id={`${id}b`} />
        <div className="mc-top"><span>LORE</span><span>{card.glyph}</span></div>
        <p className="mc-lore">{card.lore || 'No lore written yet.'}</p>
        <div className="mc-money">
          <small>EARNS</small>
          {money.length ? money.map((m, i) => <div key={i}><span>{m.pool}</span><b>{m.tierWeighted ? `${m.pct}% · by tier` : m.pct != null ? `${m.pct}% of pot` : m.weight != null ? `${m.weight}× weight` : m.tiers ? Object.entries(m.tiers).map(([t, v]) => `${t} ${v}%`).join(' · ') : ''}{m.fixedSol ? ` +${m.fixedSol} SOL each` : ''}</b></div>)
            : <div><span>Nothing yet</span><b>flex only</b></div>}
          <div className="mc-earned"><span>Earned per card so far</span><b>{sol(card.earnedEach || 0)} SOL</b></div>
          {card.earnedMine != null && <div className="mc-earned mine"><span>This wallet earned</span><b>{sol(card.earnedMine)} SOL</b></div>}
        </div>
        <p className="mc-how">{card.why || card.how}</p>
      </div>}
    </div>
  </div></div>;
}

export const CARD_DESIGNS = [['holo', 'Holo foil'], ['circuit', 'Circuit'], ['obsidian', 'Obsidian'], ['aurora', 'Aurora'], ['glitch', 'Glitch'], ['ember', 'Emberforge']];

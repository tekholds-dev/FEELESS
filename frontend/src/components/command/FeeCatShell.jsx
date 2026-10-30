import React, { useEffect } from 'react';
import { FeeCatMark } from '../FeeCatMark';
import { useLeaderProfile, feeHeadline } from '../../lib/feeLeader';
import { useMyCat } from '../../lib/myCat';
import { CAT_VARIATIONS } from './catCoats';
import { LookAvatar } from './CatLook';
import { AgentCritter } from './Critters';
import '../../styles/feecatShell.css';

// 🐱 THE FEECAT APP SHELL (owner, 2026-10-23: "all terminal FeeCat pages / tabs clean cut, unneeded out — a full redo, not half"): every FeeCat
// page sits in ONE violet-night shell with ONE nav — LIVE DESK · HER BRAIN · LORE (Fee, the leader) · AGENTS (create a trading cat) · BUILD A
// CAT (the look) — so "Create a cat" (an agent that trades) and "Build a cat" (coat, gear, eyes, aura) are two different doors, side by side.
// The bar carries Fee live (hunting / napping, ROI, nine lives) and YOUR built cat. Before: three pages with three different headers, Fee's
// numbers shown three times, a "Fee live" tab inside the agents page and a "Build your cat" tab that jumped away.
export const FC_NAV = [
  ['desk', '/terminal/feecat', '🐱', 'LIVE DESK', "Fee's scan · chart · calls"],
  ['brain', '/terminal/feecat?view=brain', '🧠', 'HER BRAIN', 'rules · lessons · nine lives'],
  ['lore', '/terminal/feecat?view=lore', '📜', 'LORE', 'the legend · Fee-Back'],
  ['agents', '/terminal/feecat/agents', '🤖', 'AGENTS', 'create a cat that trades'],
  ['build', '/terminal/feecat/cats', '🎨', 'BUILD AN AGENT', 'cat · queen ant · fly · ants'],
];
// in-app navigation without a router dependency (react-router's history listens to popstate)
export function goTo(path) {
  if (typeof window === 'undefined') return;
  window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate'));
}
const pct = v => `${v >= 0 ? '+' : ''}${Math.abs(v) >= 100 ? Math.round(v) : Number(v).toFixed(1)}%`;

export function FeeCatShell({ tab, children }) {
  const h = feeHeadline(useLeaderProfile()); const mine = useMyCat();
  useEffect(() => { document.body.classList.add('fcx-on'); return () => document.body.classList.remove('fcx-on'); }, []);   // 🧊 feecatShell.css: one still sky, no stacked backdrops
  const coat = mine ? (CAT_VARIATIONS[mine.coat] || CAT_VARIATIONS[0]) : null;
  return <div className={`fcx ${h.nap ? 'is-nap' : ''}`} data-testid="feecat-shell">
    <div className="fcx-sky" aria-hidden="true"><i className="fcx-aur a1" /><i className="fcx-aur a2" />{Array.from({ length: 18 }, (_, i) => <i key={i} className="fcx-star" style={{ '--i': i }} />)}</div>
    <header className="fcx-bar">
      <a className="fcx-brand" href="/terminal/feecat" onClick={e => { e.preventDefault(); goTo('/terminal/feecat'); }} data-tip="FeeCat home — Fee's live desk" data-testid="fcx-home">
        <span className="fcx-mark"><FeeCatMark size={38} /></span><span><b>FEECAT</b><small>the trading cats · violet night</small></span></a>
      <nav className="fcx-nav" aria-label="FeeCat">{FC_NAV.map(([k, path, ic, name, why], i) => <a key={k} href={path} aria-current={tab === k ? 'page' : undefined}
        className={`${tab === k ? 'active' : ''} k-${k}`} style={{ '--i': i }} onClick={e => { e.preventDefault(); goTo(path); }} data-tip={`${name} — ${why}`} data-testid={`fcx-${k}`}>
        <i aria-hidden="true">{ic}</i><span><b>{name}</b><small>{why}</small></span></a>)}</nav>
      <div className="fcx-live">
        <span className={`fcx-chip ${h.nap ? 'nap' : 'hunt'}`} data-tip={h.nap ? 'Fee is napping — out of lives or cooling off, no new trades' : 'Fee is reading the live board right now'} data-testid="fcx-state">
          <i />{h.nap ? 'NAPPING' : h.open ? `HUNTING · ${h.open}` : 'HUNTING'}</span>
        <span className={`fcx-chip ${h.roi > 0 ? 'up' : h.roi < 0 ? 'dn' : ''}`} data-tip={`Fee's paper ROI since she started (${h.trades} closed trades) — price moves only, fees on the receipt`}>
          <em>ROI</em><b className="m-num" key={h.roi}>{pct(h.roi)}</b></span>
        <span className="fcx-lives" data-tip={`${h.lives} of ${h.maxLives} lives — a loss blows one out, a win in 24 h lights one, 0 = she naps`} aria-label={`${h.lives} of ${h.maxLives} lives`}>
          {Array.from({ length: h.maxLives }, (_, i) => <i key={i} className={i < h.lives ? 'on' : ''} style={{ '--i': i }} />)}</span>
        <a className={`fcx-mine ${tab === 'build' ? 'active' : ''}`} href="/terminal/feecat/cats" onClick={e => { e.preventDefault(); goTo('/terminal/feecat/cats'); }}
          data-tip={mine ? `${mine.name || 'Your cat'} — tap to rebuild it` : 'You have no cat yet — build one'} data-testid="fcx-mine">
          {coat && mine.agent?.species && mine.agent.species !== 'cat' ? <AgentCritter agent={mine.agent} size={30} /> : coat ? <LookAvatar cat={[coat[0], coat[1], coat[2], mine.pattern]} look={mine.look} size={34} /> : <span className="fcx-plus" aria-hidden="true">+</span>}
          <small>{mine ? (mine.name || 'YOUR CAT').toUpperCase() : 'BUILD YOURS'}</small></a>
      </div>
    </header>
    <div className={`fcx-body is-${tab || 'desk'}`}>{children}</div>
  </div>;
}

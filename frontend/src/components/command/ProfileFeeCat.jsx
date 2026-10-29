import React, { lazy, Suspense, useState } from 'react';
import { Link } from 'react-router-dom';
import { Panther } from '../Panther';
import { useLeaderProfile } from '../../lib/feeLeader';
import { useAdmin } from '../../lib/adminCall';
import '../../styles/profileFeeCat.css';

// 🐆 N14 (owner 2026-10-29: "nexa public AS FEECAT — only I see NEXA and users see FeeCat; I get the cat dashboard users get when they
// purchase; they can't see my NEXA dash, only FeeCat and her trades / decisions"). On the CREATOR's profile:
//   · a visitor sees FEECAT — Fee's hero + live desk, read-only (FeeCatStage + FeeLiveTab: one component per job, no copy; the owner bar
//     renders only for an admin viewer; no chat) + one way in: build your own cat. The word NEXA never reaches them.
//   · the creator, signed in on their own profile, sees 🪟 NEXA — the cat dashboard a buyer gets (FeeCatDesk, the same as HQ › Agents › NEXA)
//     — with a 👁 switch to check exactly what visitors see.
// `ProfileFeeBanner` = the small live card on the profile's front that opens the tab.
const FeeCatStage = lazy(() => import('./FeeCatStage').then(m => ({ default: m.FeeCatStage })));
const FeeLiveTab = lazy(() => import('./FeeLiveTab').then(m => ({ default: m.FeeLiveTab })));
const FeeCatDesk = lazy(() => import('./FeeCatDesk').then(m => ({ default: m.FeeCatDesk })));

const FeeOwnerBar = lazy(() => import('./FeeOwnerBar').then(m => ({ default: m.FeeOwnerBar })));
const OwnerBar = () => { const d = useLeaderProfile(); return d?.cat ? <FeeOwnerBar cat={d.cat} /> : null; };   // 🎨 style · 👛 Fee's wallet (assign / fund / real) right on the NEXA desk

const sol = v => `${(Number(v) || 0) >= 0 ? '+' : '−'}${Math.abs(Number(v) || 0).toFixed(3)} SOL`;

export function ProfileFeeBanner({ onOpen, mine }) {
  const d = useLeaderProfile(); const c = d?.cat || {}; const st = d?.stats || {};
  const real = Number(c.realizedPnlSol) || 0; const open = (c.positions || []).length;
  const nap = (d?.discipline || {}).pause || c.status === 'paused';   // the same rule as her hero (FeeCatStage): out of lives / a tilt pause = napping
  const win = st.winRate != null ? st.winRate : c.winRate;
  return <button type="button" className="pfc-banner" onClick={onOpen} data-testid="profile-fee-banner" data-tip={mine ? 'Your cat — the NEXA desk (visitors see FeeCat)' : "FeeCat — Fee's live trades and decisions"}>
    <span className="pfc-cat" aria-hidden="true"><Panther size={44} crop="head" label="Fee" /></span>
    <span className="pfc-who"><em>{mine ? '🪟 NEXA · YOUR CAT' : '🐱 FEECAT · LIVE'}</em><b>{c.name || 'Fee'}</b><small>{nap ? 'napping' : 'hunting live'} · {open} open</small></span>
    <span className={`pfc-num ${real > 0 ? 'is-up' : real < 0 ? 'is-dn' : ''}`}><em>REALIZED</em><b className="m-num">{d ? sol(real) : '…'}</b></span>
    <span className="pfc-num"><em>WIN RATE</em><b className="m-num">{win != null ? `${Math.round(win)}%` : '—'}</b></span>
    <span className="pfc-go" aria-hidden="true">{mine ? 'OPEN →' : 'WATCH →'}</span>
  </button>;
}

const PublicFee = ({ cta }) => <>
  <header className="pfc-head"><span><em>🐱 FEECAT · LIVE · READ-ONLY</em><b>Fee — her trades and decisions</b><small>Every number is her real desk. Watching only — your own cat comes with its own desk.</small></span>
    {cta ? <Link className="m-btn m-go pfc-cta" to="/terminal/feecat/cats" data-testid="profile-fee-cta" data-tip="Build your own cat: its own wallet, its own desk">🐱 Get your own cat</Link> : null}</header>
  <Suspense fallback={<p className="paper-muted">🐱 reading Fee…</p>}><FeeCatStage /><FeeLiveTab /></Suspense>
</>;

export function ProfileFeeCat({ mine }) {
  const { isAdmin, call } = useAdmin();
  const [view, setView] = useState('desk');
  if (!(mine && isAdmin)) return <section className="pfc" data-testid="profile-feecat"><PublicFee cta={!mine} /></section>;
  return <section className="pfc is-owner" data-testid="profile-feecat">
    <div className="m-seg pfc-seg" role="radiogroup" aria-label="Which view">
      {[['desk', '🪟 NEXA DESK', 'Your cat — the dashboard a buyer gets'], ['public', '👁 WHAT VISITORS SEE', 'Exactly what anyone opening your profile sees: FeeCat, read-only']].map(([k, l, tip]) =>
        <button key={k} type="button" role="radio" aria-checked={view === k} className={view === k ? 'active' : ''} onClick={() => setView(k)} data-tip={tip} data-testid={`profile-fee-${k}`}>{l}</button>)}</div>
    {view === 'desk' ? <Suspense fallback={<p className="paper-muted">🪟 opening NEXA…</p>}><OwnerBar /><FeeCatDesk call={call} /></Suspense> : <PublicFee cta={false} />}
  </section>;
}

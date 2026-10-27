import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { DUO_SECOND, readDuoPrefs, saveDuoPrefs } from '../lib/duo';
import '../styles/duoBar.css';

// 📱📱 THE DUO BAR (owner 2026-10-27: "real features for Duo · true iPhone Duo perks"): shows only on a two-screen / unfolded / sideways touch
// screen. ⇄ swaps the two screens (chart ⇄ chat on the Trenches, chart ⇄ ticket on Perps, city ⇄ building in Familia); on the Trenches floor
// the second screen is yours to pick — the coin's CHAT or the live CALLS. Stored per device; applies at once (body classes, lib/duo.js).
const onDuo = () => typeof document !== 'undefined' && (document.body.classList.contains('is-duo') || document.body.classList.contains('is-phone-land'));

export function DuoBar() {
  const [on, setOn] = useState(onDuo); const [p, setP] = useState(readDuoPrefs); const loc = useLocation(); const [open, setOpen] = useState(false);   // folded = a small button over the sidebar's empty rail (covers nothing)
  useEffect(() => { const sync = () => { setOn(onDuo()); setP(readDuoPrefs()); }; window.addEventListener('feeless:duo', sync); sync(); return () => window.removeEventListener('feeless:duo', sync); }, []);
  if (!on) return null;
  if (!open) return <button type="button" className={`duob-fab ${p.swap ? 'is-swap' : ''}`} onClick={() => setOpen(true)} aria-label="Duo screens" data-tip="Duo screens — swap the two sides, pick the second screen" data-testid="duo-fab"><i className="duob-dev" aria-hidden="true"><s /><s /></i></button>;
  const trenches = /^\/terminal\/chat/.test(loc.pathname);
  const set = x => setP(saveDuoPrefs({ ...p, ...x }));
  return <div className={`duob ${p.swap ? 'is-swap' : ''}`} role="group" aria-label="Duo screens" data-testid="duo-bar">
    <button type="button" className="duob-x" onClick={() => setOpen(false)} aria-label="Fold the Duo bar" data-tip="Fold" data-testid="duo-fold"><i className="duob-dev" aria-hidden="true"><s /><s /></i></button><b>DUO</b>
    <button type="button" className="duob-swap" aria-pressed={p.swap} onClick={() => set({ swap: !p.swap })} data-tip="Swap the two screens — chart ⇄ chat on the Trenches, chart ⇄ ticket on Perps, city ⇄ building in Familia" data-testid="duo-swap">⇄</button>
    {trenches ? <span className="m-seg duob-2" role="radiogroup" aria-label="Second screen">{DUO_SECOND.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={p.second === k} className={p.second === k ? 'active' : ''}
      onClick={() => set({ second: k })} data-tip={tip} data-testid={`duo-2-${k}`}>{l}</button>)}</span> : null}
  </div>;
}

import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { readDuoPrefs, saveDuoPrefs } from '../lib/duo';
import '../styles/duoBar.css';

// 📱📱 THE DUO TAB (owner 2026-10-27: "the switches don't lock to the side properly · the lil features bottom left"): one handle locked to the
// left edge, on an unfolded Duo / a phone on its side, in Familia only — ⇄ trades the two halves (the city ⇄ the open building or desk). The
// Trenches coin floor has its own docked controls (DuoFloor), so nothing floats over a chart any more. Stored per device (lib/duo.js).
const onWide = () => typeof document !== 'undefined' && (document.body.classList.contains('is-duo-land') || document.body.classList.contains('is-phone-land'));

export function DuoBar() {
  const [on, setOn] = useState(onWide); const [p, setP] = useState(readDuoPrefs); const loc = useLocation();
  useEffect(() => { const sync = () => { setOn(onWide()); setP(readDuoPrefs()); }; window.addEventListener('feeless:duo', sync); sync(); return () => window.removeEventListener('feeless:duo', sync); }, []);
  if (!on || !/^\/familia/.test(loc.pathname)) return null;
  return <button type="button" className={`duob ${p.swap ? 'is-swap' : ''}`} aria-pressed={p.swap} onClick={() => setP(saveDuoPrefs({ ...p, swap: !p.swap }))}
    aria-label="Swap the two halves" data-testid="duo-bar"><i className="duob-dev" aria-hidden="true"><s /><s /></i><small>SWAP</small></button>;
}

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';

// $1k+ FEELESS holders recolor the logo and the whole site (for themselves). The server re-checks
// holdings and the wallet session on every save; the browser only ever applies what it returns.
const MINT_HUE = 158;
const hueOf = hex => { const r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b); if (mx === mn) return 0; const d = mx - mn; const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return h * 60; };
const PRESETS = [['Royal green (default)', '#15d16a'], ['Gold', '#f5c542'], ['Diamond', '#7cc8ff'], ['Rose', '#fa708c'], ['Violet', '#b388ff'], ['Solar', '#ff8a3d'], ['Ice', '#e7f3ff']];

// Whole-site recolor (admins, creators, $1000+ holders): one pass over the stylesheets at apply time copies every rule
// that uses the FEELESS green (#15d16a / rgba(21, 209, 106,a)) into one override sheet with your colour, alpha kept.
// No filters, nothing per frame — zero lag. null removes it.
export function recolorText(css, hex) {
  const h = hex.replace('#', '').toLowerCase(); const [r, g, b] = [0, 2, 4].map(k => parseInt(h.slice(k, k + 2), 16));
  return css.replace(/#15d16a([0-9a-f]{2})?(?![0-9a-f])/gi, (m, a) => `#${h}${a || ''}`)
    .replace(/rgba?\(\s*21\s*,\s*209\s*,\s*106/gi, m => `${m.startsWith('rgba') ? 'rgba' : 'rgb'}(${r}, ${g}, ${b}`);
}
export function recolorSite(hex) {
  let el = document.getElementById('feeless-recolor');
  if (!hex || !/^#[0-9a-f]{6}$/i.test(hex) || ['#15d16a', '#19f58f'].includes(hex.toLowerCase())) { el?.remove(); return; }   // the old mint = the default too
  const out = [];
  const walk = rules => { for (const rule of rules) {
    if (rule.cssRules && rule.media) { const before = out.length; walk(rule.cssRules); const added = out.splice(before); if (added.length) out.push(`@media ${rule.media.mediaText}{${added.join('')}}`); continue; }
    if (rule.selectorText && /15d16a|21,\s*209,\s*106/i.test(rule.cssText)) out.push(recolorText(rule.cssText, hex));
  } };
  for (const sheet of document.styleSheets) { if (sheet.ownerNode?.id === 'feeless-recolor') continue; try { walk(sheet.cssRules); } catch { /* cross-origin sheet */ } }
  if (!el) { el = document.createElement('style'); el.id = 'feeless-recolor'; }
  el.textContent = out.join('\n');
  document.head.appendChild(el);   // last in <head> = wins at equal specificity
}

export function applyTheme(t) {
  const root = document.documentElement;
  if (!t) { ['--mint', '--accent2', '--logo-hue', '--m-accent'].forEach(k => root.style.removeProperty(k)); root.classList.remove('holder-theme'); recolorSite(null); return; }
  root.style.setProperty('--mint', t.accent); root.style.setProperty('--accent2', t.accent2 || t.accent); root.style.setProperty('--m-accent', t.accent);
  recolorSite(t.accent);
  root.style.setProperty('--logo-hue', `${Math.round(hueOf(t.logo || t.accent) - MINT_HUE)}deg`);
  root.classList.add('holder-theme');
}

// Mounted once at the app root: applies the connected wallet's saved theme (if still eligible).
export function useHolderTheme() {
  const { wallet } = useWallet() || {};
  useEffect(() => {
    if (!wallet?.address || wallet.chain === 'evm') { applyTheme(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/reputation/theme/${wallet.address}`)).then(r => r.json()).then(d => alive && applyTheme(d.theme)).catch(() => {});
    return () => { alive = false; };
  }, [wallet?.address, wallet?.chain]);
}

export function HolderThemePicker() {
  const { wallet, signMessage } = useWallet() || {};
  const [info, setInfo] = useState(null);
  const [accent, setAccent] = useState('#15d16a');
  useEffect(() => {
    if (!wallet?.address) { setInfo(null); return; }
    fetch(apiUrl(`/api/reputation/theme/${wallet.address}`)).then(r => r.json()).then(d => { setInfo(d); if (d.theme?.accent) setAccent(d.theme.accent); }).catch(() => {});
  }, [wallet?.address]);
  const save = async () => {
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/theme'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, accent }) });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail);
      applyTheme(d.theme); toast.success('Your FEELESS colors are live.');
    } catch (e) { toast.error(e.message); }
  };
  return <section className="m-card m-stack holder-theme-card" data-testid="holder-theme">
    <div className="m-row cs-bar"><span className="m-label">YOUR FEELESS COLORS <em>{info?.staff ? 'FEELESS HQ · always unlocked' : 'holder perk'}</em></span>{info?.eligible && <span className="m-chip ok">✓ unlocked</span>}</div>
    <p className="m-dim">{info?.staff ? 'Creator and admin wallets can recolor the logo and the whole site for themselves.' : `Hold $${(info?.minUsd || 1000).toLocaleString()}+ across $FEE, RFEE and FEECAT to recolor the logo and the whole site.`}</p>
    {!wallet?.address ? <p className="m-dim">Connect a wallet to check eligibility.</p> : !info ? <p className="m-dim">Checking your holdings…</p> : <>
      {!info.staff && <div className="m-bars ht-bar"><i style={{ transform: `scaleX(${Math.min(1, info.holdingUsd / info.minUsd)})` }} /></div>}
      {!info.staff && <small className="m-dim">You hold ${Number(info.holdingUsd).toLocaleString()} {info.eligible ? '— unlocked ✓' : `— $${(info.minUsd - info.holdingUsd).toLocaleString(undefined, { maximumFractionDigits: 0 })} to go`}</small>}
      <div className="ht-swatches">{PRESETS.map(([n, c]) => <button key={c} type="button" title={n} className={accent === c ? 'on' : ''} style={{ background: c }} onClick={() => { setAccent(c); if (info.eligible) applyTheme({ accent: c }); }} />)}<input type="color" value={accent} onChange={e => { setAccent(e.target.value); if (info.eligible) applyTheme({ accent: e.target.value }); }} aria-label="Custom color" /></div>
      <button type="button" className="m-btn primary" disabled={!info.eligible} onClick={save}>{info.eligible ? 'Save my colors' : 'Locked — hold more $FEE'}</button>
    </>}
  </section>;
}

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';
import { applyLook, localLook } from '../lib/looks';

// $1k+ FEELESS holders recolor the logo and the whole site (for themselves). The server re-checks
// holdings and the wallet session on every save; the browser only ever applies what it returns.
const MINT_HUE = 158;
const hueOf = hex => { const r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b); if (mx === mn) return 0; const d = mx - mn; const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return h * 60; };
const PRESETS = [['Plasma (default)', '#9b6bff'], ['Gold', '#f5c542'], ['Diamond', '#7cc8ff'], ['Rose', '#fa708c'], ['Violet', '#b388ff'], ['Solar', '#ff8a3d'], ['Ice', '#e7f3ff']];

// Whole-site recolor (admins, creators, $1000+ holders): one pass over the stylesheets at apply time copies every rule
// that uses a FEELESS brand colour into one override sheet with your colour, alpha kept. No filters, nothing per frame — zero lag.
// The brand is a FAMILY, not one hex (PLASMA since 2026-11-11: #7c4dff → #9b6bff → #b48cff violets, #ff6fbf pink tail, #c9a8ff / #5b33c9 tints):
// each family shade keeps its own lightness and takes your hue + saturation; #9b6bff itself becomes exactly your colour.
// Price up / down (#3cf0c5 / #3ee58a, #ff5c7a …) are not the brand and never change. null removes it.
const BRAND = new Set(['9b6bff', 'b48cff', '7c4dff', 'ff6fbf', 'c9a8ff', '5b33c9']);
const toHsl = (r, g, b) => { r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2; if (mx === mn) return [0, 0, l];
  const d = mx - mn; const s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn); const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return [h * 60, s, l]; };
const toRgb = (h, s, l) => { const k = n => (n + h / 30) % 12; const a = s * Math.min(l, 1 - l); return [0, 8, 4].map(n => Math.round(255 * (l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1))))); };
export function recolorText(css, hex) {
  const h = hex.replace('#', '').toLowerCase(); const want = [0, 2, 4].map(k => parseInt(h.slice(k, k + 2), 16)); const [th, ts] = toHsl(...want);
  const hexOf = c => c.map(x => x.toString(16).padStart(2, '0')).join('');
  const shade = c => { const x = hexOf(c); if (!BRAND.has(x)) return null; return x === '9b6bff' ? want : toRgb(th, ts, toHsl(...c)[2]); };
  return css.replace(/#([0-9a-f]{6})([0-9a-f]{2})?(?![0-9a-f])/gi, (m, c, a) => { const n = shade([0, 2, 4].map(k => parseInt(c.slice(k, k + 2), 16))); return n ? `#${hexOf(n)}${a || ''}` : m; })
    .replace(/(rgba?)\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})/gi, (m, f, r, g, b) => { const n = shade([+r, +g, +b]); return n ? `${f.toLowerCase()}(${n[0]}, ${n[1]}, ${n[2]}` : m; });
}
// 🧵 One override sheet per job (a holder's colour, a look): one pass over the stylesheets copies every rule its transform changes into that
// sheet, last in <head>. A screen's own sheet loads when it opens (HQ's hqNav.css, a desk's sheet …), so each override is rebuilt when one
// arrives, debounced (2026-11-11: HQ's active sidebar item stayed default on a red theme).
const OVERRIDES = {};   // id → { transform, t }
let lateObs = null;
function rebuild(id) {
  const o = OVERRIDES[id]; let el = document.getElementById(id);
  if (!o) { el?.remove(); return; }
  const out = [];
  const walk = rules => { for (const rule of rules) {
    if (rule.cssRules && rule.media) { const before = out.length; walk(rule.cssRules); const added = out.splice(before); if (added.length) out.push(`@media ${rule.media.mediaText}{${added.join('')}}`); continue; }
    if (rule.selectorText) { const t = o.transform(rule.cssText); if (t !== rule.cssText) out.push(t); }
  } };
  for (const sheet of document.styleSheets) { if (OVERRIDES[sheet.ownerNode?.id] || sheet.ownerNode?.id?.startsWith('feeless-')) continue; try { walk(sheet.cssRules); } catch { /* cross-origin sheet */ } }
  if (!el) { el = document.createElement('style'); el.id = id; }
  el.textContent = out.join('\n');
  document.head.appendChild(el);   // last in <head> = wins at equal specificity
}
function watchLate() {
  const live = Object.keys(OVERRIDES).length;
  if (!live) { lateObs?.disconnect(); lateObs = null; return; }
  if (lateObs || typeof MutationObserver === 'undefined') return;
  let t = 0; const again = () => { clearTimeout(t); t = setTimeout(() => Object.keys(OVERRIDES).forEach(rebuild), 150); };
  lateObs = new MutationObserver(list => { for (const m of list) for (const n of m.addedNodes) {
    if (String(n.id || '').startsWith('feeless-')) continue;
    if (n.tagName === 'STYLE') again(); else if (n.tagName === 'LINK' && /stylesheet/i.test(n.rel)) n.addEventListener('load', again, { once: true });
  } });
  lateObs.observe(document.head, { childList: true });
}
function overrideSite(id, transform) {
  if (transform) OVERRIDES[id] = { transform }; else delete OVERRIDES[id];
  rebuild(id); watchLate();
}
export function recolorSite(hex) {
  const on = hex && /^#[0-9a-f]{6}$/i.test(hex) && !['#9b6bff', '#15d16a', '#19f58f'].includes(hex.toLowerCase());   // the default (and the retired greens a saved theme may still name) = no override
  overrideSite('feeless-recolor', on ? css => recolorText(css, hex) : null);
}
/** 🎨 A look's colours over Plasma's own: { hex: { plasmaHex: lookHex }, rgb: { 'r,g,b': [r, g, b] } } (lib/looks.lookMap). Pure. */
export function remapText(css, { hex, rgb }) {
  return css.replace(/#([0-9a-f]{6})([0-9a-f]{2})?(?![0-9a-f])/gi, (m, c, a) => (hex[c.toLowerCase()] ? `#${hex[c.toLowerCase()]}${a || ''}` : m))
    .replace(/(rgba?)\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})/gi, (m, f, r, g, b) => { const n = rgb[`${r},${g},${b}`]; return n ? `${f.toLowerCase()}(${n[0]}, ${n[1]}, ${n[2]}` : m; });
}
export function remapSite(map) { overrideSite('feeless-look', map ? css => remapText(css, map) : null); }

export function applyTheme(t) {
  const root = document.documentElement;
  if (!t?.accent) { ['--accent2', '--logo-hue'].forEach(k => root.style.removeProperty(k)); root.classList.remove('holder-theme'); recolorSite(null);
    applyLook(t?.look?.tokens ? t.look : localLook()); return; }   // 🎨 no custom colour: the saved look (or this device's), else Plasma
  applyLook(null);
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
  const [accent, setAccent] = useState('#9b6bff');
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

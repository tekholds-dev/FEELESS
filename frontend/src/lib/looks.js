import { useEffect, useState } from 'react';
// 🎨 LOOKS (owner 2026-11-11): one switch re-skins the whole site. OBSIDIAN in Feeless Green is the default (owner's pick 2026-11-12, with Desk and
// Pit: same green, their own layout via <html data-layout>); PLASMA is the site's own colours and needs nothing applied. Another look sets the
// meta tokens on <html> and copies every stylesheet rule that writes a Plasma colour into one override sheet with that look's colour
// (same walk as the holder theme), so hand-written colours follow too. <html data-look> drives the ambient layer (styles/looks.css).
// The four free looks ship here; an advanced look's colours come only from the server, only to a wallet that unlocked it.
import { remapSite } from '../components/HolderTheme';

const GREEN = { accent: '#19e68c', hi: '#4df0a8', deep: '#0fbf72', tail: '#2ad4c8', tint: '#a6f5d0', dark: '#08995a', ink: '#04140c', third: '#4aa3ff', logoHue: 8, edition: 'elite' };
// 🟢 the main row (mirror of backend/looks.py FEELESS tier)
export const FEELESS_LOOKS = {
  obsidian: { id: 'obsidian', name: 'Obsidian', ambient: 'obsidian', tier: 'feeless', tokens: { bg: '#09090b', s1: '#111114', s2: '#18181c', line: '#1f1f23', lineHi: '#3a3a41', text: '#eeeef1', dim: '#86868f', ...GREEN, layout: 'obsidian' } },
  desk: { id: 'desk', name: 'Desk', ambient: 'desk', tier: 'feeless', tokens: { bg: '#07080c', s1: '#12141b', s2: '#191c25', line: '#1e2129', lineHi: '#3a3e4b', text: '#eceef4', dim: '#868b99', ...GREEN, layout: 'desk' } },
  pit: { id: 'pit', name: 'Pit', ambient: 'pit', tier: 'feeless', tokens: { bg: '#08090b', s1: '#101215', s2: '#171a1e', line: '#1e2125', lineHi: '#3a3e45', text: '#ecedef', dim: '#858a92', ...GREEN, layout: 'pit' } },
  carbon: { id: 'carbon', name: 'Carbon', ambient: 'carbon', tier: 'feeless', tokens: { bg: '#0b0c0e', s1: '#111216', s2: '#17181d', line: '#23252b', lineHi: '#3d404a', text: '#f7f8f8', dim: '#8a8f98', accent: '#5e6ad2', hi: '#7c86e8', deep: '#4a55c0', tail: '#8b93ff', tint: '#b4baf5', dark: '#3a438f', ink: '#ffffff', third: '#26b5ce', logoHue: 75, edition: 'elite' } },
};
export const DEFAULT_LOOK = FEELESS_LOOKS.obsidian;
// 🧹 Slice 34 (owner 2026-11-20): only Obsidian (default), Desk, Pit and Carbon stay (backend/looks.py RETIRED). A retired pick wears Obsidian.
export const LOCAL_LOOKS = { ...FEELESS_LOOKS };
export const LOOK_KEY = 'feeless.look';

// Plasma's own colours, as the sheets write them → which token of the new look takes each one
const SRC = {
  '9b6bff': 'accent', b48cff: 'hi', '7c4dff': 'deep', ff6fbf: 'tail', c9a8ff: 'tint', '5b33c9': 'dark', d6c4ff: 'tint', ff8fd0: 'tail', e3d6ff: 'text',
  '08061a': 'bg', '0e0b22': 's1', '140f2e': 's2', '0c0a1e': 's1', '0d0b20': 's1', '0d0a22': 's1', '12081f': 'ink', '120d26': 's2', '120e28': 's2', '15102e': 's2', '1c1830': 's2', '1f1840': 's2',
  '2a1f55': 'line', '3d3466': 'line', '4b3596': 'lineHi', f1edff: 'text', f3eeff: 'text', f2eeff: 'text', e2dcf6: 'text', cfc7ea: 'text', cdc5e9: 'text',
  aaa1c9: 'dim', '9f97c2': 'dim', c4bce0: 'dim', b5add6: 'dim', '9c94bd': 'dim', '8d85ad': 'dim',
};
const SRC_RGB = [['155,107,255', 'accent'], ['180,140,255', 'hi'], ['124,77,255', 'deep'], ['255,63,164', 'tail'], ['255,111,191', 'tail'], ['62,231,255', 'third'], ['242,238,255', 'text']];
const rgbOf = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));

/** → the { plasmaHex: lookHex } map (6-digit, lowercase, no #) and the { 'r,g,b': [r, g, b] } map for one look's tokens. Pure. */
export function lookMap(t) {
  const hex = {}; for (const [k, v] of Object.entries(SRC)) if (t[v]) hex[k] = t[v].slice(1).toLowerCase();
  const rgb = {}; for (const [k, v] of SRC_RGB) if (t[v]) rgb[k] = rgbOf(t[v]);
  return { hex, rgb };
}

/** Wear a look (a LOCAL_LOOKS entry or the server's `wear` answer). Plasma, or null, puts the site back to its own colours (callers pass DEFAULT_LOOK for "no pick yet"). */
export function applyLook(look) {
  const root = document.documentElement; const t = look?.tokens;
  const VARS = { '--m-bg': 'bg', '--m-surface': 's1', '--m-surface-2': 's2', '--m-line': 'line', '--m-line-hi': 'lineHi', '--m-text': 'text', '--m-dim': 'dim', '--m-accent': 'accent', '--m-accent-ink': 'ink',
    '--ink': 'bg', '--mint': 'accent', '--look-hi': 'hi', '--look-tail': 'tail', '--look-third': 'third', '--look-dark': 'dark' };
  if (t?.edition === 'elite') root.dataset.edition = 'elite'; else delete root.dataset.edition;
  if (t?.layout) root.dataset.layout = t.layout; else delete root.dataset.layout;   // Obsidian / Desk / Pit arrange the terminal (styles/looks.css + DeskLayout)
  window.dispatchEvent(new Event('feeless:layout'));
  window.dispatchEvent(new Event('feeless:edition'));
  if (!t || look.id === 'plasma') { [...Object.keys(VARS), '--logo-hue', '--logo-sat'].forEach(k => root.style.removeProperty(k)); delete root.dataset.look; remapSite(null); window.dispatchEvent(new Event('feeless:chart-theme')); return; }
  for (const [k, v] of Object.entries(VARS)) root.style.setProperty(k, t[v]);
  root.style.setProperty('--logo-hue', `${t.logoHue ?? 145}deg`); root.style.setProperty('--logo-sat', String(t.logoSat ?? 1.15));   // the green logo art wears this look's accent (CSS hue-rotate is not linear: each look carries its measured angle)
  root.dataset.look = look.ambient || look.id;
  remapSite(lookMap(t));
  window.dispatchEvent(new Event('feeless:chart-theme'));   // open candle charts re-read the FEELESS theme (it wears this look's green)
}

export function localLook() { try { const k = localStorage.getItem(LOOK_KEY); return LOCAL_LOOKS[k] || null; } catch { return null; } }
export function keepLocalLook(id) { try { if (LOCAL_LOOKS[id]) localStorage.setItem(LOOK_KEY, id); } catch { /* private window: it still applies for this visit */ } }

/** → the worn layout ('obsidian' | 'desk' | 'pit' | '') — re-renders when a look changes it. */
export function useLayout() {
  const [l, setL] = useState(() => (typeof document !== 'undefined' && document.documentElement.dataset.layout) || '');
  useEffect(() => { const on = () => setL(document.documentElement.dataset.layout || ''); window.addEventListener('feeless:layout', on); on(); return () => window.removeEventListener('feeless:layout', on); }, []);
  return l;
}

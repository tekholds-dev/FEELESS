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
};
export const DEFAULT_LOOK = FEELESS_LOOKS.obsidian;
export const FREE_LOOKS = {
  plasma: { id: 'plasma', name: 'Plasma', ambient: 'plasma', tokens: { bg: '#08051a', s1: '#120b2c', s2: '#1a1140', line: '#2a1f55', lineHi: '#4b3596', text: '#f2eeff', dim: '#aaa1c9', accent: '#9b6bff', hi: '#b48cff', deep: '#7c4dff', tail: '#ff6fbf', tint: '#c9a8ff', dark: '#5b33c9', ink: '#12081f', third: '#3ee7ff', logoHue: 145 } },
  molten: { id: 'molten', name: 'Molten', ambient: 'molten', tokens: { bg: '#0b0704', s1: '#170f08', s2: '#22160c', line: '#3a2a12', lineHi: '#7a5418', text: '#fff4e2', dim: '#cdb393', accent: '#ffb020', hi: '#ffc95a', deep: '#e0780f', tail: '#ff5a1f', tint: '#ffe08a', dark: '#a8560a', ink: '#2a1400', third: '#ffe08a', logoHue: -60 } },
  neon: { id: 'neon', name: 'Neon Grid', ambient: 'neon', tokens: { bg: '#02060b', s1: '#061019', s2: '#0a1826', line: '#0d3340', lineHi: '#00a8b8', text: '#e6fbff', dim: '#86aebd', accent: '#00f0ff', hi: '#6ff7ff', deep: '#00b8d4', tail: '#ff2bd6', tint: '#a8fbff', dark: '#00788a', ink: '#00141a', third: '#faff00', logoHue: 45 } },
  holo: { id: 'holo', name: 'Holo Chrome', ambient: 'holo', tokens: { bg: '#06080d', s1: '#0d121c', s2: '#141b29', line: '#26324a', lineHi: '#5a6f99', text: '#f3f7ff', dim: '#a3b1c8', accent: '#8fd3ff', hi: '#b6e3ff', deep: '#6fb6f0', tail: '#c7a6ff', tint: '#ffc6ec', dark: '#4f86b8', ink: '#0d1020', third: '#ffc6ec', logoHue: 59 } },
};
// 🎩 ELITE EDITION (owner 2026-11-11): grown-up looks for everyone; wearing one also sets <html data-edition="elite"> (line icons, plain display type, no ambient blobs)
export const ELITE_LOOKS = {
  amber: { id: 'amber', name: 'Amber', ambient: 'amber', tier: 'elite', tokens: { bg: '#0a0a0a', s1: '#121212', s2: '#1a1a1a', line: '#262626', lineHi: '#4a4a4a', text: '#ededed', dim: '#8f8f8f', accent: '#ffb000', hi: '#ffc640', deep: '#e09a00', tail: '#ff8a00', tint: '#ffd98a', dark: '#a87300', ink: '#0a0a0a', third: '#4aa3ff', logoHue: -95, edition: 'elite' } },
  carbon: { id: 'carbon', name: 'Carbon', ambient: 'carbon', tier: 'elite', tokens: { bg: '#0b0c0e', s1: '#111216', s2: '#17181d', line: '#23252b', lineHi: '#3d404a', text: '#f7f8f8', dim: '#8a8f98', accent: '#5e6ad2', hi: '#7c86e8', deep: '#4a55c0', tail: '#8b93ff', tint: '#b4baf5', dark: '#3a438f', ink: '#ffffff', third: '#26b5ce', logoHue: 75, edition: 'elite' } },
  titanium: { id: 'titanium', name: 'Titanium', ambient: 'titanium', tier: 'elite', tokens: { bg: '#0f0f11', s1: '#1c1c1e', s2: '#2c2c2e', line: '#38383a', lineHi: '#636366', text: '#f5f5f7', dim: '#98989d', accent: '#0a84ff', hi: '#409cff', deep: '#0071e3', tail: '#64d2ff', tint: '#a8d4ff', dark: '#0058b0', ink: '#ffffff', third: '#64d2ff', logoHue: 55, edition: 'elite' } },
  ledger: { id: 'ledger', name: 'Ledger', ambient: 'ledger', tier: 'elite', tokens: { bg: '#0b0f15', s1: '#111823', s2: '#18212f', line: '#243042', lineHi: '#3d4f6b', text: '#ebeef3', dim: '#8d98a9', accent: '#c9a86a', hi: '#dcc08a', deep: '#b08f52', tail: '#e3cf9f', tint: '#efe2c2', dark: '#8a6f3d', ink: '#0b0f15', third: '#7fa7d9', logoHue: -110, logoSat: 0.55, edition: 'elite' } },
};
export const LOCAL_LOOKS = { ...FEELESS_LOOKS, ...FREE_LOOKS, ...ELITE_LOOKS };
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
    '--ink': 'bg', '--mint': 'accent', '--look-hi': 'hi', '--look-tail': 'tail', '--look-third': 'third' };
  if (t?.edition === 'elite') root.dataset.edition = 'elite'; else delete root.dataset.edition;
  if (t?.layout) root.dataset.layout = t.layout; else delete root.dataset.layout;   // Obsidian / Desk / Pit arrange the terminal (styles/looks.css + DeskLayout)
  window.dispatchEvent(new Event('feeless:layout'));
  window.dispatchEvent(new Event('feeless:edition'));
  if (!t || look.id === 'plasma') { [...Object.keys(VARS), '--logo-hue', '--logo-sat'].forEach(k => root.style.removeProperty(k)); delete root.dataset.look; remapSite(null); return; }
  for (const [k, v] of Object.entries(VARS)) root.style.setProperty(k, t[v]);
  root.style.setProperty('--logo-hue', `${t.logoHue ?? 145}deg`); root.style.setProperty('--logo-sat', String(t.logoSat ?? 1.15));   // the green logo art wears this look's accent (CSS hue-rotate is not linear: each look carries its measured angle)
  root.dataset.look = look.ambient || look.id;
  remapSite(lookMap(t));
}

export function localLook() { try { const k = localStorage.getItem(LOOK_KEY); return LOCAL_LOOKS[k] || null; } catch { return null; } }
export function keepLocalLook(id) { try { if (LOCAL_LOOKS[id]) localStorage.setItem(LOOK_KEY, id); } catch { /* private window: it still applies for this visit */ } }

/** → the worn layout ('obsidian' | 'desk' | 'pit' | '') — re-renders when a look changes it. */
export function useLayout() {
  const [l, setL] = useState(() => (typeof document !== 'undefined' && document.documentElement.dataset.layout) || '');
  useEffect(() => { const on = () => setL(document.documentElement.dataset.layout || ''); window.addEventListener('feeless:layout', on); on(); return () => window.removeEventListener('feeless:layout', on); }, []);
  return l;
}

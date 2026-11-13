import { useEffect, useState } from 'react';

// 🎨 CHART THEME (Settings › Appearance & charts): one pick re-colors every candle chart on the site (PriceChart / TrenchChart, PerpsChart),
// night and day each get their own readable pair. Stored per browser; a change reaches open charts at once ('feeless:chart-theme').
// The FEELESS theme wears the site's worn look (Obsidian green by default): applyLook writes --mint (accent) and
// --look-dark (its day accent); Plasma / no look removes them, so the fallbacks below are Plasma's classic chart pair.
const cssVar = (name, fb) => { try { const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return /^#[0-9a-fA-F]{6}$/.test(v) ? v : fb; } catch { return fb; } };
export const CHART_THEMES = {
  feeless: { name: 'FEELESS', get up() { return cssVar('--mint', '#00e7a0'); }, down: '#ff4d6d', get dayUp() { return cssVar('--look-dark', '#08764e'); }, dayDown: '#b42346' },
  classic: { name: 'CLASSIC', up: '#26a69a', down: '#ef5350', dayUp: '#089981', dayDown: '#d32f2f' },
  neon: { name: 'NEON', up: '#b48cff', down: '#ff5dbb', dayUp: '#0a8a44', dayDown: '#c2187a' },
  mono: { name: 'MONO', up: '#e9e9e9', down: '#5f6368', dayUp: '#1b1b1b', dayDown: '#a0a0a0' },
  cb: { name: 'COLOR-BLIND', up: '#2f8cff', down: '#ff9f1c', dayUp: '#0b5cd5', dayDown: '#c46a00' },
};
const KEY = 'feeless.chart.theme';
export const chartThemeId = () => { try { const v = localStorage.getItem(KEY); return CHART_THEMES[v] ? v : 'feeless'; } catch { return 'feeless'; } };
export function chartColors(day, id = chartThemeId()) { const t = CHART_THEMES[id] || CHART_THEMES.feeless; return { up: day ? t.dayUp : t.up, down: day ? t.dayDown : t.down }; }
export function setChartTheme(id) {
  if (!CHART_THEMES[id]) return;
  try { localStorage.setItem(KEY, id); } catch { /* private mode: this tab only */ }
  window.dispatchEvent(new CustomEvent('feeless:chart-theme', { detail: id }));
}
export function useChartTheme() {
  const [st, setSt] = useState(() => ({ id: chartThemeId() }));
  useEffect(() => {
    const on = e => setSt({ id: (e && e.detail) || chartThemeId() });   // a new object every time: a worn-look change re-renders open charts even when the theme id is unchanged
    window.addEventListener('feeless:chart-theme', on); window.addEventListener('feeless:layout', on);
    return () => { window.removeEventListener('feeless:chart-theme', on); window.removeEventListener('feeless:layout', on); };
  }, []);
  return [st.id, setChartTheme];
}

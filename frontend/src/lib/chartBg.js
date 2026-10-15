import { useEffect, useState } from 'react';

// 🎨 Chart backgrounds: ONE choice for every chart on the site (TrenchChart → PriceChart), kept in this browser.
// 'default' = the plain chart. Scenes are drawn by components/terminal/ChartBg.jsx. Owner, 2026-10-15: "redo chart themes to better meta
// upgraded themes, neon trench over designed" → every scene is CALM and in the site's royal-green meta language: Neon trench = only a grid
// floor + a horizon; Aurora + Pulse grid are new; Code rain kept, quieter. A retired id (hyper · casino · sunset · aurora-old · peaks · sakura ·
// deep · warp · cat · reactor · helix · city · tunnel · storm · gutter · sonar · lava · vhs) falls back to Default.
export const CHART_BGS = [['default', '▫ Default'], ['aurora', '🌌 Royal aurora'], ['pulse', '🧬 Pulse grid'], ['neon', '⚡ Neon trench'], ['rain', '🟩 Code rain']];
const KEY = 'feeless.chartBg';
const ok = v => CHART_BGS.some(([k]) => k === v);
const subs = new Set();
let cur = null;

export const getChartBg = () => {
  if (cur) return cur;
  try { const v = window.localStorage.getItem(KEY); cur = ok(v) ? v : 'default'; } catch { cur = 'default'; }
  return cur;
};
export const setChartBg = v => {
  cur = ok(v) ? v : 'default';
  try { window.localStorage.setItem(KEY, cur); } catch { /* private window: the choice lasts for this visit */ }
  subs.forEach(f => f(cur));
};
export function useChartBg() {
  const [v, setV] = useState(getChartBg);
  useEffect(() => { subs.add(setV); setV(getChartBg()); return () => { subs.delete(setV); }; }, []);
  return v;
}

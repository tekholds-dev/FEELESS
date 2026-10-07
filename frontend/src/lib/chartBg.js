import { useEffect, useState } from 'react';

// 🎨 Chart backgrounds: ONE choice for every chart on the site (TrenchChart → PriceChart), kept in this browser.
// 'default' = the plain chart. Two Fuse scenes + two calm ones (sunset over the ocean, aurora night), drawn by components/terminal/ChartBg.jsx.
export const CHART_BGS = [['default', '▫ Default'], ['reactor', '⚛ Fuse reactor'], ['helix', '🧬 Fuse helix'], ['sunset', '🌅 Sunset ocean'], ['aurora', '🌌 Aurora night']];
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

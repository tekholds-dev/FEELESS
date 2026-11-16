import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// 🛡 One league's ESPN team logos, fetched once per page per league (GET /api/cats/tools/logos/<sport>, cached a day on the server).
const memo = {};
export const logoLoad = sport => {
  if (!sport || sport === 'other' || sport === 'chips') return Promise.resolve({});
  memo[sport] = memo[sport] || fetch(apiUrl(`/api/cats/tools/logos/${sport}`)).then(r => (r.ok ? r.json() : {})).then(j => j.logos || {}).catch(() => ({}));
  return memo[sport];
};
export const logoFor = (logos, name) => (name ? logos?.[String(name).toLowerCase()] || null : null);
export function useLogos(sport) {
  const [logos, setLogos] = useState({});
  useEffect(() => {   // a filing with no saved game ('Jets vs Chiefs') tries the four big leagues
    let on = true; const keys = sport === 'other' ? ['nfl', 'nba', 'nhl', 'mlb'] : [sport];
    Promise.all(keys.map(logoLoad)).then(all => on && setLogos(Object.assign({}, ...all.reverse()))); return () => { on = false; };
  }, [sport]);
  return logos;
}

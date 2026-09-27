import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// Every name on screen asks for its Rep; requests are pooled into one call per ~120ms and cached,
// so a chat with 200 messages costs one request, not 200.
const cache = new Map(); // address -> { v, at }
const waiters = new Map(); // address -> Set(setter)
let queue = new Set(); let timer = null;
function flush() {
  const list = [...queue]; queue = new Set(); timer = null;
  if (!list.length) return;
  fetch(apiUrl(`/api/reputation/trust-batch?addresses=${list.join(',')}`)).then(r => r.json()).then(({ trust = {} }) => {
    const missing = [];
    list.forEach(a => {
      if (trust[a]) { cache.set(a, { v: trust[a], at: Date.now() }); waiters.get(a)?.forEach(fn => fn(trust[a])); }
      else missing.push(a);
    });
    // The server scores unknown wallets in the background; ask once more shortly.
    if (missing.length) setTimeout(() => missing.forEach(a => { if (!cache.has(a)) want(a, true); }), 5000);
  }).catch(() => {});
}
function want(a, retry) {
  const hit = cache.get(a);
  if (hit && Date.now() - hit.at < 120000) return;
  if (!retry && queue.has(a)) return;
  queue.add(a); if (!timer) timer = setTimeout(flush, 120);
}

export function useRep(address) {
  const [rep, setRep] = useState(() => cache.get(address)?.v || null);
  useEffect(() => {
    if (!address) return undefined;
    const set = waiters.get(address) || new Set(); set.add(setRep); waiters.set(address, set);
    if (cache.get(address)) setRep(cache.get(address).v);
    want(address);
    return () => { set.delete(setRep); };
  }, [address]);
  return rep;
}

export function RepMark({ address, compact }) {
  const rep = useRep(address);
  if (!rep || rep.score == null) return null;
  const lvl = rep.blocked ? 'blocked' : rep.gold ? 'gold' : rep.level;
  return <span className={`rep-mark lvl-${lvl} ${compact ? 'compact' : ''}`} title={`Rep ${rep.score}/100 · ${rep.blocked ? 'blocklisted, full record kept' : rep.gold ? 'gold creator: 3+ launches, none dumped' : rep.level}`}>
    <svg viewBox="0 0 16 18" aria-hidden="true"><path d="M8 1 14.5 3.4v5.1c0 4-2.8 7-6.5 8.5C4.3 15.5 1.5 12.5 1.5 8.5V3.4Z" /><text x="8" y="12" textAnchor="middle">R</text></svg>
    <b>{rep.score}</b>
  </span>;
}

import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { sweepable } from '../lib/cacheSweep';
import '../styles/walletPfp.css';

// 🪪 ONE wallet picture for the whole site (owner, 2026-10-21: "pfp should show anywhere for a wallet and never be blank"): the wallet's own
// profile picture when it set one — every wallet on screen is looked up in ONE batched /profiles call — else a mark generated from the address
// itself (same wallet = same mark everywhere: two colours + a mirrored 5×5 pattern). A picture that fails to load falls back to the mark.
const cache = sweepable('walletPfp', new Map(), { ttl: 5 * 60 * 1000, max: 2000 });
const waiting = new Map();          // address → [resolve]
let timer = null;

function flush() {
  timer = null;
  const batch = [...waiting.keys()].slice(0, 40);
  const subs = batch.map(a => [a, waiting.get(a)]); batch.forEach(a => waiting.delete(a));
  if (waiting.size) timer = setTimeout(flush, 60);
  fetch(apiUrl(`/api/reputation/profiles?addresses=${batch.join(',')}`)).then(r => (r.ok ? r.json() : { profiles: {} })).catch(() => ({ profiles: {} }))
    .then(d => subs.forEach(([a, fns]) => { const p = (d.profiles || {})[a] || null; cache.set(a, { v: p, at: Date.now() }); fns.forEach(f => f(p)); }));
}
export function loadProfile(address) {
  if (!address) return Promise.resolve(null);
  const hit = cache.get(address);
  if (hit) return Promise.resolve(hit.v);
  return new Promise(res => { if (!waiting.has(address)) waiting.set(address, []); waiting.get(address).push(res); if (!timer) timer = setTimeout(flush, 120); });
}
export function useWalletProfile(address) {
  const [p, setP] = useState(() => cache.get(address)?.v ?? null);
  useEffect(() => { let on = true; loadProfile(address).then(x => on && setP(x)); return () => { on = false; }; }, [address]);
  return p;
}

// pure: the mark for an address — two hues and a mirrored 5×5 grid (deterministic)
export function markOf(address) {
  let h = 2166136261;
  for (const ch of String(address || '?')) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
  const bits = []; let x = h;
  for (let i = 0; i < 15; i++) { bits.push(x & 1); x = (x >>> 1) || Math.imul(h ^ i, 2654435761) >>> 0; }
  const cells = [];
  for (let r = 0; r < 5; r++) for (let c = 0; c < 3; c++) if (bits[r * 3 + c]) { cells.push([c, r]); if (c < 2) cells.push([4 - c, r]); }
  return { h1: h % 360, h2: (h >>> 9) % 360, cells };
}

export function WalletMark({ address, size = 28 }) {
  const m = markOf(address);
  return <svg className="wpf-mark" width={size} height={size} viewBox="0 0 10 10" aria-hidden="true">
    <defs><linearGradient id={`wpf-${m.h1}-${m.h2}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={`hsl(${m.h1} 70% 42%)`} /><stop offset="1" stopColor={`hsl(${m.h2} 75% 22%)`} /></linearGradient></defs>
    <rect width="10" height="10" fill={`url(#wpf-${m.h1}-${m.h2})`} />
    {m.cells.map(([c, r]) => <rect key={`${c}-${r}`} x={c * 1.6 + 1} y={r * 1.6 + 1} width="1.6" height="1.6" fill={`hsl(${m.h1} 90% 78%)`} />)}
  </svg>;
}

export function WalletPfp({ address, size = 28, url, ring, title }) {
  const p = useWalletProfile(url ? null : address);
  const src = url || p?.avatarUrl;
  const [bad, setBad] = useState(false);
  useEffect(() => setBad(false), [src]);
  return <span className={`wpf ${ring ? 'has-ring' : ''}`} style={{ width: size, height: size, '--ring': p?.accent || undefined }} title={title || p?.displayName || undefined} data-testid="wallet-pfp">
    {src && !bad ? <img src={src} alt="" loading="lazy" onError={() => setBad(true)} /> : <WalletMark address={address} size={size} />}
  </span>;
}

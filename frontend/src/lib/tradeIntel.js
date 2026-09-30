import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// Shared, cached lookups for the trade boxes: rug-shield verdicts per coin and FEE points per wallet.
const shields = new Map(); // mint -> { at, promise }; verdicts refresh after SHIELD_TTL_MS
const SHIELD_TTL_MS = 120000;
const SETTLE = new Set(['So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB']);

export function useShield(mint) {
  const [v, setV] = useState(null);
  useEffect(() => {
    if (!mint || SETTLE.has(mint)) { setV(null); return undefined; }
    let alive = true;
    const hit = shields.get(mint);
    if (!hit || Date.now() - hit.at > SHIELD_TTL_MS) shields.set(mint, { at: Date.now(), promise: fetch(apiUrl(`/api/reputation/rugshield/${mint}`)).then(r => (r.ok ? r.json() : null)).catch(() => null) });
    shields.get(mint).promise.then(x => alive && setV(x));
    return () => { alive = false; };
  }, [mint]);
  return v;
}

export function usePoints(wallet, refreshKey) {
  const [p, setP] = useState(null);
  useEffect(() => {
    if (!wallet) { setP(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/trading/points/${wallet}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setP(x)).catch(() => {});
    return () => { alive = false; };
  }, [wallet, refreshKey]);
  return p;
}

export const SHIELD_LABEL = { ok: '🛡 Rug shield: clear', caution: '⚠ Rug shield: caution', danger: '⛔ Rug shield: high risk', unknown: '🛡 Rug shield: unavailable' };

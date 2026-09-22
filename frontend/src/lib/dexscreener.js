import { apiUrl } from './api';

export const DEX_SITE = process.env.REACT_APP_DEX_SITE_URL || 'https://dexscreener.com';
export const MARKET_RETENTION_DAYS = 14;
export const NEW_POOL_DEAL_PERCENT = 5;

export async function marketRequest(path, signal) {
  const res = await fetch(apiUrl(path.startsWith('/api/') ? path : `/api/market${path}`), { signal });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Market data unavailable');
  return data;
}
export const searchTokens = async q => (await marketRequest(`/search?q=${encodeURIComponent(q)}`)).pairs;
export const searchTokenByAddress = searchTokens;
export const pairKey = p => `${p.chainId}-${p.pairAddress}`;
export const tokenKey = p => `${p.chainId}-${p.baseToken?.address}`;
const roomPart = value => encodeURIComponent(String(value)).replace(/%[0-9a-f]{2}/gi, '_');
export function coinIdentity(pair) {
  const chainId = String(pair?.chainId || '').trim();
  const pairAddress = String(pair?.pairAddress || '').trim();
  if (!chainId || !pairAddress) return null;
  return { chainId, pairAddress, key: `${chainId}:${pairAddress}` };
}
export function coinRoom(pair, perspective = 'trenches') {
  const identity = coinIdentity(pair);
  if (!identity) return null;
  return `coin-${roomPart(identity.chainId)}-${roomPart(identity.pairAddress)}-${roomPart(perspective)}`;
}
export const dexUrl = p => `${DEX_SITE}/${encodeURIComponent(p.chainId)}/${encodeURIComponent(p.pairAddress)}`;
export function isNewPoolDeal(pair, now = Date.now()) {
  const created = Number(pair?.pairCreatedAt);
  const change = Number(pair?.priceChange?.h24);
  const age = now - created;
  return Number.isFinite(created)
    && age >= 0
    && age <= MARKET_RETENTION_DAYS * 24 * 60 * 60 * 1000
    && Number.isFinite(change)
    && change <= -NEW_POOL_DEAL_PERCENT;
}
export const shortAddress = a => a ? `${a.slice(0, 5)}…${a.slice(-5)}` : '—';
export function formatTime(value) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '—';
  try { return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }); }
  catch { return date.toISOString().slice(11, 16); }
}
export function formatUSD(n) {
  if (n === null || n === undefined || n === '' || !Number.isFinite(Number(n))) return '—';
  const num = Number(n);
  if (Math.abs(num) >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  if (Math.abs(num) >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  if (Math.abs(num) >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
  if (num === 0) return '$0.00';
  if (Math.abs(num) < 0.000001) return `$${num.toExponential(3)}`;
  return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: num < 1 ? 8 : 2 })}`;
}
export function formatPct(n) {
  if (n == null || n === '' || !Number.isFinite(Number(n))) return '—';
  return `${Number(n) >= 0 ? '+' : ''}${Number(n).toFixed(2)}%`;
}
export function formatAge(ts) {
  if (!ts) return '—';
  const minutes = Math.max(0, Math.floor((Date.now() - Number(ts)) / 60000));
  if (minutes < 1) return '<1m';
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h`;
  return `${Math.floor(minutes / 1440)}d`;
}
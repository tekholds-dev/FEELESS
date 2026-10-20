const configuredOrigin = (process.env.REACT_APP_BACKEND_URL || '').trim().replace(/\/+$/, '');

export function apiUrl(path) {
  const normalized = String(path || '').startsWith('/') ? String(path) : `/${path}`;
  return `${configuredOrigin}${normalized}`;
}

// Server error body -> readable text. FastAPI validation errors arrive as a list of {loc, msg}.
export function errorText(body, status) {
  const d = body?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map(e => `${(e.loc || []).filter(x => x !== 'body').join('.') || 'input'}: ${e.msg}`).join(' · ');
  if (d && typeof d === 'object') return d.message || JSON.stringify(d);
  return `Request failed (${status})`;
}

// Amount typed by a trader → a value the server accepts: digits + one dot, ".5" → "0.5", "01" → "1".
export function cleanAmount(v) {
  let s = String(v ?? '').replace(/,/g, '.').replace(/[^0-9.]/g, '');
  const dot = s.indexOf('.');
  if (dot !== -1) s = s.slice(0, dot + 1) + s.slice(dot + 1).replace(/\./g, '');
  if (s.startsWith('.')) s = `0${s}`;
  return s.replace(/^0+(?=\d)/, '');
}

// One call to the trading service (quote / simulate / execute): JSON in, JSON out, the server's own `detail` as the error.
export async function tradingCall(path, body) {
  const r = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : `Error ${r.status}`); return d;
}
export const b64 = u8 => btoa(String.fromCharCode(...u8));

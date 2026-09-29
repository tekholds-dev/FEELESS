const configuredOrigin = (process.env.REACT_APP_BACKEND_URL || '').trim().replace(/\/+$/, '');

export function apiUrl(path) {
  const normalized = String(path || '').startsWith('/') ? String(path) : `/${path}`;
  return `${configuredOrigin}${normalized}`;
}

export const API_ORIGIN = configuredOrigin;

// Server error body -> readable text. FastAPI validation errors arrive as a list of {loc, msg}.
export function errorText(body, status) {
  const d = body?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map(e => `${(e.loc || []).filter(x => x !== 'body').join('.') || 'input'}: ${e.msg}`).join(' · ');
  if (d && typeof d === 'object') return d.message || JSON.stringify(d);
  return `Request failed (${status})`;
}

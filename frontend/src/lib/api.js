const configuredOrigin = (process.env.REACT_APP_BACKEND_URL || '').trim().replace(/\/+$/, '');

export function apiUrl(path) {
  const normalized = String(path || '').startsWith('/') ? String(path) : `/${path}`;
  return `${configuredOrigin}${normalized}`;
}

export const API_ORIGIN = configuredOrigin;
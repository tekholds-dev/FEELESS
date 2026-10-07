// 🔗 ONE request per URL for every component that asks at the same time. The Fuse page used to fetch /fuses/prime (98 KB) four
// times at once on load — the slowest copy took 2.1s. Callers within `maxAge` ms get the same answer; `fresh` (after an owner
// action) skips the cached answer but still shares a request already in flight that started after the action.
import { apiUrl } from './api';

const cache = new Map();   // url → { at, p }

export function sharedJson(path, { maxAge = 3000, fresh = false } = {}) {
  const now = Date.now();
  const hit = cache.get(path);
  if (hit && (fresh ? hit.at >= (sharedJson.freshAt || 0) && hit.pending : now - hit.at < maxAge)) return hit.p;
  const entry = { at: now, pending: true };
  entry.p = fetch(apiUrl(path)).then(r => (r.ok === false ? null : r.json())).finally(() => { entry.pending = false; });
  entry.p.catch(() => cache.get(path) === entry && cache.delete(path));   // a failed read is never served to the next caller
  cache.set(path, entry);
  return entry.p;
}

// an owner action changed the data: the next `fresh` read must start after this moment
export const markFresh = () => { sharedJson.freshAt = Date.now(); };
if (typeof window !== 'undefined') window.addEventListener('feeless:prime', markFresh);   // registered at import: runs before any card's listener

export const _resetShared = () => cache.clear();   // tests

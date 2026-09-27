import { useEffect, useState } from 'react';

// Keeps what the user was typing across reloads (per key). Empty values clear the saved draft.
export function useDraft(key, initial = '') {
  const storageKey = `feeless:draft:${key}`;
  const [value, setValue] = useState(() => { try { const v = localStorage.getItem(storageKey); return v != null ? v : initial; } catch { return initial; } });
  useEffect(() => {
    const t = setTimeout(() => { try { if (value === '' || value === initial) localStorage.removeItem(storageKey); else localStorage.setItem(storageKey, String(value)); } catch { /* private mode */ } }, 300);
    return () => clearTimeout(t);
  }, [storageKey, value, initial]);
  return [value, setValue];
}

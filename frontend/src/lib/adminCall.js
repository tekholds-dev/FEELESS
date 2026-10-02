import { cropImage } from './cropImage';
import { useCallback, useEffect, useState } from 'react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from './api';

const SESSION_KEY = 'feeless:cc-session';
const read = addr => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address === addr && Date.now() / 1000 - s.ts < 3500 ? s : null; } catch { return null; } };

// Admin calls from anywhere on the site, sharing the HQ's signed session (1h).
// isAdmin only shows/hides controls — the server re-verifies the signature on every admin request.
export function useAdmin() {
  const { wallet, signMessage } = useWallet() || {};
  const address = wallet?.address;
  const [isAdmin, setIsAdmin] = useState(false);
  useEffect(() => {
    if (!address) { setIsAdmin(false); return; }
    fetch(apiUrl(`/api/reputation/admin/is-admin/${address}`)).then(r => r.json()).then(d => setIsAdmin(!!d.admin)).catch(() => setIsAdmin(false));
  }, [address]);
  const call = useCallback(async (path, opts = {}) => {
    let s = read(address);
    if (!s) {
      const ts = Math.floor(Date.now() / 1000);
      const sig = await signMessage(`FEELESS HQ\naddress:${address}\nts:${ts}`);
      s = { address, ts, sig }; localStorage.setItem(SESSION_KEY, JSON.stringify(s));
    }
    const res = await fetch(apiUrl(`/api/reputation${path}`), { ...opts, headers: { 'Content-Type': 'application/json', 'x-admin-address': address, 'x-admin-ts': String(s.ts), 'x-admin-sig': s.sig } });
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) localStorage.removeItem(SESSION_KEY);
    if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
    return body;
  }, [address, signMessage]);
  return { isAdmin, call };
}

// Pick a file -> optional crop (shape from CROP) -> resize stills to ≤1600px, GIFs kept animated
// -> FEELESS upload -> hosted URL. Resolves null if the user cancels the crop.
export async function uploadImage(file, shape) {
  // GIFs keep their animation: no canvas crop (it would flatten them to one frame); the page shows them cover-fit.
  if (shape && file.type !== 'image/gif') { file = await cropImage(file, shape); if (!file) return null; }
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) throw new Error('PNG, JPG, WEBP or GIF only.');
  // A live HQ session (creator/admin) lifts the size cap to 25 MB and keeps art sharper.
  let admin = null;
  try { const x = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); if (x && Date.now() / 1000 - x.ts < 3500) admin = x; } catch { /* none */ }
  const cap = admin ? 25_000_000 : file.type === 'image/gif' ? 6_000_000 : 2_000_000;   // animated covers/avatars: 6 MB
  const dataUrl = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });
  let body = dataUrl;
  if (file.type !== 'image/gif') {
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = dataUrl; });
    const k = Math.min(1, (admin ? 3000 : 1600) / Math.max(img.width, img.height));
    const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); body = c.toDataURL('image/webp', 0.92);
  } else if (file.size > cap) throw new Error(`GIFs must be under ${cap / 1_000_000} MB.`);
  const headers = { 'Content-Type': 'application/json', ...(admin ? { 'x-admin-address': admin.address, 'x-admin-ts': String(admin.ts), 'x-admin-sig': admin.sig } : {}) };
  const r = await fetch(apiUrl('/api/reputation/uploads'), { method: 'POST', headers, body: JSON.stringify({ dataUrl: body }) });
  const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Upload failed.');
  return d.url;
}

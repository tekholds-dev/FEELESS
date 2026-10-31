import { cropImage } from './cropImage';
import { sharedJson } from './sharedJson';
import { slimGif } from './slimGif';
import { useCallback, useEffect, useState } from 'react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from './api';

const SESSION_KEY = 'feeless:cc-session';
const read = addr => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address === addr && Date.now() / 1000 - s.ts < 3500 ? s : null; } catch { return null; } };

// Admin calls from anywhere on the site, sharing the HQ's signed session (1h).
// isAdmin only shows/hides controls — the server re-verifies the signature on every admin request.
// ✍ ONE HQ signature prompt at a time (owner 2026-10-30: "not signed in, the FeeCat tab would spam the sign-in popup"): Fee's desks poll every
// 6–10 s and each poll used to open its own wallet prompt. Now concurrent calls share one prompt, and after a decline (or no wallet answer) the
// POLLS stay quiet for 5 min — a button you press (a POST) may still ask.
const QUIET_MS = 5 * 60 * 1000;
let signing = null; let declinedAt = 0;
export async function hqSign(address, signMessage, poll = true, now = Date.now) {
  if (poll && declinedAt && now() - declinedAt < QUIET_MS) throw new Error('Sign in to HQ to load this (tap any HQ button).');
  if (!signing) {
    signing = (async () => {
      const ts = Math.floor(now() / 1000);
      try {
        const sig = await signMessage(`FEELESS HQ\naddress:${address}\nts:${ts}`);
        const s = { address, ts, sig }; try { localStorage.setItem(SESSION_KEY, JSON.stringify(s)); } catch { /* private window */ }
        declinedAt = 0; return s;
      } catch (e) { declinedAt = now(); throw e; } finally { signing = null; }
    })();
  }
  return signing;
}
export function useAdmin() {
  const { wallet, signMessage } = useWallet() || {};
  const address = wallet?.address;
  const [isAdmin, setIsAdmin] = useState(false);
  const [isStaff, setIsStaff] = useState(false);   // staff = the creator via ANY linked wallet (server `_is_staff`); UI only, the server re-checks
  useEffect(() => {
    if (!address) { setIsAdmin(false); setIsStaff(false); return; }
    sharedJson(`/api/reputation/admin/is-admin/${address}`, { maxAge: 60000 }).then(d => { setIsAdmin(!!d?.admin); setIsStaff(!!(d?.staff || d?.admin)); }).catch(() => { setIsAdmin(false); setIsStaff(false); });
  }, [address]);
  const call = useCallback(async (path, opts = {}) => {
    let s = read(address);
    if (!s) s = await hqSign(address, signMessage, !opts.method || opts.method === 'GET');
    const res = await fetch(apiUrl(`/api/reputation${path}`), { ...opts, headers: { 'Content-Type': 'application/json', 'x-admin-address': address, 'x-admin-ts': String(s.ts), 'x-admin-sig': s.sig } });
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) localStorage.removeItem(SESSION_KEY);
    if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
    return body;
  }, [address, signMessage]);
  return { isAdmin, isStaff, call };
}

// Pick a file -> optional crop (shape from CROP) -> resize stills to ≤1600px, GIFs kept animated
// -> FEELESS upload -> hosted URL. Resolves null if the user cancels the crop.
export async function uploadImage(file, shape) {
  // GIFs keep their animation: no canvas crop (it would flatten them to one frame); the page shows them cover-fit.
  if (shape && file.type !== 'image/gif') { file = await cropImage(file, shape); if (!file) return null; }
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) throw new Error('PNG, JPG, WEBP or GIF only.');
  // animated GIFs are slimmed to the box they are shown in (≤ 12 fps) so a heavy one can never lag the page
  if (file.type === 'image/gif') file = await slimGif(file, shape?.gif || shape?.out || [1200, 1200]).catch(() => file);
  // A live HQ session (creator/admin) keeps art sharper (40 MB).
  let admin = null;
  try { const x = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); if (x && Date.now() / 1000 - x.ts < 3500) admin = x; } catch { /* none */ }
  const cap = admin ? 40_000_000 : file.type === 'image/gif' ? 40_000_000 : 15_000_000;   // owner 2026-10-26: big backgrounds welcome (GIFs 40 MB · stills 15 MB)
  const dataUrl = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });
  let body = dataUrl;
  if (file.type !== 'image/gif') {
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = dataUrl; });
    const k = Math.min(1, (admin ? 3000 : 1600) / Math.max(img.width, img.height));
    const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); body = c.toDataURL('image/webp', 0.92);
  } else if (!admin && file.size > cap) throw new Error(`GIFs must be under ${cap / 1_000_000} MB.`);   // signed in: the server decides (the creator's GIFs have no size limit)
  const headers = { 'Content-Type': 'application/json', ...(admin ? { 'x-admin-address': admin.address, 'x-admin-ts': String(admin.ts), 'x-admin-sig': admin.sig } : {}) };
  const r = await fetch(apiUrl('/api/reputation/uploads'), { method: 'POST', headers, body: JSON.stringify({ dataUrl: body }) });
  const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Upload failed.');
  return d.url;
}

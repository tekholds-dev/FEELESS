// 📲 TELEGRAM MINI APP (owner 2026-10-27: "family be a telegram game"): when Telegram opens FEELESS inside a chat (the bot's Web App button →
// PUBLIC_SITE_URL/familia?tg=1&place=race), its SDK hands us `initData` — signed by the bot, verified by the server (backend/tg_auth.py) — so a
// player races under their Telegram name with no wallet. Outside Telegram everything here is a no-op.
const SDK = 'https://telegram.org/js/telegram-web-app.js';
export const tgApp = () => (typeof window !== 'undefined' ? window.Telegram?.WebApp || null : null);
export const tgInitData = () => tgApp()?.initData || '';
export const inTelegram = () => !!tgInitData() || (typeof window !== 'undefined' && /tgWebAppData=/.test(window.location.hash || ''));

let loading = null;
export function initTelegram() {
  if (typeof window === 'undefined' || loading) return loading;
  const wanted = /tgWebAppData=/.test(window.location.hash || '') || /[?&]tg=1\b/.test(window.location.search || '');
  if (!wanted) return null;
  loading = new Promise(resolve => {
    const done = () => { const app = tgApp(); if (app) { try { app.ready(); app.expand(); app.setHeaderColor?.('#050805'); app.setBackgroundColor?.('#050805'); document.body.classList.add('is-tg'); } catch { /* an old client */ } } resolve(app); };
    if (tgApp()) { done(); return; }
    const s = document.createElement('script'); s.src = SDK; s.async = true; s.onload = done; s.onerror = () => resolve(null); document.head.appendChild(s);
  });
  return loading;
}
// a short buzz on the phone (checkpoint, crash, finish) — Telegram's own haptics, else the browser's
export function tgHaptic(kind = 'light') {
  try { const h = tgApp()?.HapticFeedback; if (h) { if (kind === 'success' || kind === 'error') h.notificationOccurred(kind); else h.impactOccurred(kind); return; } navigator.vibrate?.(kind === 'heavy' ? 40 : 15); } catch { /* no haptics */ }
}

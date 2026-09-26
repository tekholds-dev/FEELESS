import { apiUrl } from './api';

const PREFS_KEY = 'feeless-push-prefs';
export const DEFAULT_PUSH_PREFS = { cooldownMin: 30, minLiquidity: 0, quietStart: null, quietEnd: null };

export const pushSupported = () => typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && typeof Notification !== 'undefined';

export function readPushPrefs() {
  try { return { ...DEFAULT_PUSH_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') }; } catch { return { ...DEFAULT_PUSH_PREFS }; }
}
export function savePushPrefs(prefs) { try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch {} }

const b64ToBytes = b64 => {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, c => c.charCodeAt(0));
};

async function registration() {
  return navigator.serviceWorker.register('/feeless-sw.js');
}

export async function currentSubscription() {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration('/feeless-sw.js') || await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}

const watchPayload = watchlist => watchlist.map(p => ({
  chainId: p.chainId, pairAddress: p.pairAddress, mint: p.baseToken?.address, symbol: p.baseToken?.symbol,
  watchedPrice: p.watchedPrice || Number(p.priceUsd) || null, watchedLiq: p.watchedLiq || Number(p.liquidity?.usd) || null,
  rules: p.alerts || {},
}));

export async function enablePush(watchlist, prefs) {
  if (!pushSupported()) throw new Error('This browser does not support push notifications.');
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') throw new Error('Notifications are blocked for this site.');
  const reg = await registration();
  await navigator.serviceWorker.ready;
  const { publicKey } = await (await fetch(apiUrl('/api/reputation/push/vapid'))).json();
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(publicKey) });
  return syncPush(watchlist, prefs, sub);
}

export async function syncPush(watchlist, prefs, sub) {
  const subscription = sub || await currentSubscription();
  if (!subscription) return null;
  const res = await fetch(apiUrl('/api/reputation/push/subscribe'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subscription: subscription.toJSON(), watch: watchPayload(watchlist), prefs }) });
  if (!res.ok) throw new Error('Could not register alerts with the server.');
  return res.json();
}

export async function disablePush() {
  const sub = await currentSubscription();
  if (!sub) return;
  await fetch(apiUrl('/api/reputation/push/unsubscribe'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ endpoint: sub.endpoint }) }).catch(() => {});
  await sub.unsubscribe();
}

export async function testPush() {
  const sub = await currentSubscription();
  if (!sub) throw new Error('Enable push first.');
  const res = await fetch(apiUrl('/api/reputation/push/test'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ endpoint: sub.endpoint }) });
  const body = await res.json();
  if (!res.ok || body.result !== 'ok') throw new Error(body.detail || `Push service replied: ${body.result}`);
}

export async function pushStatus() {
  const sub = await currentSubscription();
  if (!sub) return { subscribed: false };
  const res = await fetch(apiUrl(`/api/reputation/push/status?endpoint=${encodeURIComponent(sub.endpoint)}`));
  return res.ok ? res.json() : { subscribed: false };
}

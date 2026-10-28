import { useEffect, useState } from 'react';
// 📱📱 DUO: wide touch screens (an unfolded / two-screen iPhone, a tablet, a phone turned sideways) get split layouts — chart on one side,
// the trade station on the other — and a hinged two-segment screen snaps each column to its own segment. Classes on <body>:
//   is-duo        touch screen 600–1180px wide (or two segments)   → split chart | trade on Perps, chart | chat on the Trenches floor
//   is-duo-split  the screen reports two horizontal viewport segments (a hinge) → the columns sit on each side of it
//   is-phone-land a phone turned sideways                           → full-height chart beside the ticket, the header shrinks
//   is-duo-land   an unfolded screen held wide (iPhone Duo open = 890 × 626) → ONE slim top bar, the two halves meet at the crease (~445 px)
// iPhone Duo (owner 2026-10-27): folded 466 × 678 (a phone) · unfolded 890 × 626 wide / 626 × 890 upright, DPR 3, crease down the middle.
// Safari reports no viewport segments, so the split is by size, never by hinge APIs. The Trenches floor on any of these = DuoFloor.
// The user's own Duo picks (DuoBar, stored per device `feeless.duo`): `duo-swap` = the two screens trade places; the Trenches' second screen =
// the Duo floor's open dock tab (`second`: trade · chat · calls · coins · tape — TRADE by default: owner 2026-10-27 "chart AND quick trade").
export function duoState(w = typeof window !== 'undefined' ? window : null) {
  if (!w) return { duo: false, split: false, land: false, wide: false };
  const mm = q => { try { return !!w.matchMedia?.(q).matches; } catch { return false; } };
  const coarse = mm('(pointer: coarse)');
  const split = mm('(horizontal-viewport-segments: 2)') || (w.navigator?.viewportSegments?.length === 2);
  const W = w.innerWidth || 0; const H = w.innerHeight || 0;
  const duo = coarse && (split || (W >= 600 && W <= 1180));
  return { duo, split: coarse && split, land: coarse && W > H && H <= 500, wide: duo && W > H };
}

export const DUO_KEY = 'feeless.duo';
export const DUO_SECOND = [['trade', 'TRADE', 'Quick trade, Dip / Rip and the rug shield beside the chart'], ['chat', 'CHAT', "The coin's chat"], ['calls', 'CALLS', 'Hot + live calls and the caller board'],
  ['coins', 'COINS', 'The live intake + the coin feed — tap one and it opens on the chart in place'], ['tape', 'TAPE', 'Every live swap on this coin']];   // the Duo floor's dock tabs
// pure: whatever was stored → valid picks
export function duoPrefs(raw) {
  let p = raw; if (typeof raw === 'string') { try { p = JSON.parse(raw); } catch { p = null; } }
  return { swap: !!p?.swap, second: DUO_SECOND.some(([k]) => k === p?.second) ? p.second : 'trade' };
}
export function readDuoPrefs() { try { return duoPrefs(localStorage.getItem(DUO_KEY)); } catch { return duoPrefs(null); } }
export function applyDuoPrefs(p = readDuoPrefs()) {
  if (typeof document === 'undefined') return p;
  const b = document.body.classList; b.toggle('duo-swap', !!p.swap); DUO_SECOND.forEach(([k]) => b.toggle(`duo-2-${k}`, p.second === k));
  return p;
}
export function saveDuoPrefs(p) {
  const v = duoPrefs(p); try { localStorage.setItem(DUO_KEY, JSON.stringify(v)); } catch { /* private mode: still applies this visit */ }
  applyDuoPrefs(v); try { window.dispatchEvent(new Event('feeless:duo')); } catch { /* old browsers */ }
  return v;
}

export function installDuo() {
  if (typeof window === 'undefined' || window.__feelessDuo) return;
  window.__feelessDuo = true;
  let t = null;
  const apply = () => { const s = duoState(); const b = document.body.classList;
    b.toggle('is-duo', s.duo); b.toggle('is-duo-split', s.split); b.toggle('is-phone-land', s.land); b.toggle('is-duo-land', s.wide);
    try { window.dispatchEvent(new Event('feeless:duo')); } catch { /* old browsers */ } };
  const soon = () => { clearTimeout(t); t = setTimeout(apply, 150); };
  apply(); applyDuoPrefs();
  window.addEventListener('resize', soon, { passive: true });
  window.addEventListener('orientationchange', soon, { passive: true });
}

// 🕘 the coins you opened on the Duo floor, newest first (the rail's quick switch) — pure: list + a pair → the new list (max 6, one per pool)
export const RECENT_KEY = 'feeless.duo.recent';
export function pushRecent(list, pair) {
  if (!pair?.pairAddress) return list || [];
  const row = { chainId: pair.chainId || 'solana', pairAddress: pair.pairAddress, symbol: pair.baseToken?.symbol || '?', img: pair.info?.imageUrl || null, mint: pair.baseToken?.address || null };
  return [row, ...(list || []).filter(r => r && r.pairAddress !== row.pairAddress)].slice(0, 6);
}
export function readRecent() { try { const v = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); return Array.isArray(v) ? v : []; } catch { return []; } }
export function saveRecent(list) { try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch { /* private mode */ } return list; }
// the floor's coin feed for swipe ‹ › and the COINS tab: trending then new, one row per pool, dust pools out
export function floorFeed(pairs = [], newPairs = []) {
  const seen = new Set(); const out = [];
  for (const p of [...pairs, ...newPairs]) { if (!p?.pairAddress || seen.has(p.pairAddress) || !(Number(p.liquidity?.usd) >= 1000 || Number(p.marketCap ?? p.fdv) >= 5000)) continue; seen.add(p.pairAddress); out.push(p); }
  return out;
}
// ‹ › step through the feed from the coin on screen (wraps)
export function stepFeed(feed, current, dir) {
  if (!feed?.length) return null;
  const i = feed.findIndex(p => p.pairAddress === current?.pairAddress);
  return feed[(i < 0 ? 0 : i + dir + feed.length) % feed.length];
}

// 📱📱 { on, wide } for the Duo apps (Trenches, Pump, HQ Agents …): on = an unfolded Duo / tablet / sideways phone, wide = held wide (split left | right)
export function useDuoFloor() {
  const read = () => { const s = duoState(); return { on: s.duo || s.land, wide: s.wide || s.land }; };
  const [st, setSt] = useState(read);
  useEffect(() => { const f = () => setSt(read()); window.addEventListener('feeless:duo', f); window.addEventListener('resize', f); return () => { window.removeEventListener('feeless:duo', f); window.removeEventListener('resize', f); }; }, []);
  return st;
}

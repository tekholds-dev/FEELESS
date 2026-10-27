// 📱📱 DUO: wide touch screens (an unfolded / two-screen iPhone, a tablet, a phone turned sideways) get split layouts — chart on one side,
// the trade station on the other — and a hinged two-segment screen snaps each column to its own segment. Classes on <body>:
//   is-duo        touch screen 600–1180px wide (or two segments)   → split chart | trade on Perps, chart | chat on the Trenches floor
//   is-duo-split  the screen reports two horizontal viewport segments (a hinge) → the columns sit on each side of it
//   is-phone-land a phone turned sideways                           → full-height chart beside the ticket, the header shrinks
// The user's own Duo picks (DuoBar, stored per device `feeless.duo`): `duo-swap` = the two screens trade places, `duo-2-calls` = the Trenches'
// second screen shows the live calls instead of the coin chat.
export function duoState(w = typeof window !== 'undefined' ? window : null) {
  if (!w) return { duo: false, split: false, land: false };
  const mm = q => { try { return !!w.matchMedia?.(q).matches; } catch { return false; } };
  const coarse = mm('(pointer: coarse)');
  const split = mm('(horizontal-viewport-segments: 2)') || (w.navigator?.viewportSegments?.length === 2);
  const W = w.innerWidth || 0; const H = w.innerHeight || 0;
  return { duo: coarse && (split || (W >= 600 && W <= 1180)), split: coarse && split, land: coarse && W > H && H <= 500 };
}

export const DUO_KEY = 'feeless.duo';
export const DUO_SECOND = [['chat', 'CHAT', "The coin's chat on the second screen"], ['calls', 'CALLS', 'Hot + live calls and the caller board on the second screen']];
// pure: whatever was stored → valid picks
export function duoPrefs(raw) {
  let p = raw; if (typeof raw === 'string') { try { p = JSON.parse(raw); } catch { p = null; } }
  return { swap: !!p?.swap, second: DUO_SECOND.some(([k]) => k === p?.second) ? p.second : 'chat' };
}
export function readDuoPrefs() { try { return duoPrefs(localStorage.getItem(DUO_KEY)); } catch { return duoPrefs(null); } }
export function applyDuoPrefs(p = readDuoPrefs()) {
  if (typeof document === 'undefined') return p;
  const b = document.body.classList; b.toggle('duo-swap', !!p.swap); b.toggle('duo-2-calls', p.second === 'calls');
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
    b.toggle('is-duo', s.duo); b.toggle('is-duo-split', s.split); b.toggle('is-phone-land', s.land);
    try { window.dispatchEvent(new Event('feeless:duo')); } catch { /* old browsers */ } };
  const soon = () => { clearTimeout(t); t = setTimeout(apply, 150); };
  apply(); applyDuoPrefs();
  window.addEventListener('resize', soon, { passive: true });
  window.addEventListener('orientationchange', soon, { passive: true });
}

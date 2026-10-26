// 📱📱 DUO: wide touch screens (an unfolded / two-screen iPhone, a tablet, a phone turned sideways) get split layouts — chart on one side,
// the trade station on the other — and a hinged two-segment screen snaps each column to its own segment. Classes on <body>:
//   is-duo        touch screen 600–1180px wide (or two segments)   → split chart | trade on Perps, chart | chat on the Trenches floor
//   is-duo-split  the screen reports two horizontal viewport segments (a hinge) → the columns sit on each side of it
//   is-phone-land a phone turned sideways                           → full-height chart beside the ticket, the header shrinks
export function duoState(w = typeof window !== 'undefined' ? window : null) {
  if (!w) return { duo: false, split: false, land: false };
  const mm = q => { try { return !!w.matchMedia?.(q).matches; } catch { return false; } };
  const coarse = mm('(pointer: coarse)');
  const split = mm('(horizontal-viewport-segments: 2)') || (w.navigator?.viewportSegments?.length === 2);
  const W = w.innerWidth || 0; const H = w.innerHeight || 0;
  return { duo: coarse && (split || (W >= 600 && W <= 1180)), split: coarse && split, land: coarse && W > H && H <= 500 };
}

export function installDuo() {
  if (typeof window === 'undefined' || window.__feelessDuo) return;
  window.__feelessDuo = true;
  let t = null;
  const apply = () => { const s = duoState(); const b = document.body.classList;
    b.toggle('is-duo', s.duo); b.toggle('is-duo-split', s.split); b.toggle('is-phone-land', s.land); };
  const soon = () => { clearTimeout(t); t = setTimeout(apply, 150); };
  apply();
  window.addEventListener('resize', soon, { passive: true });
  window.addEventListener('orientationchange', soon, { passive: true });
}

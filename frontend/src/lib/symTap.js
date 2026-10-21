// 🪙 TAP ANY $COIN (owner, 2026-10-21: "why can't I click coins?"): in the Agents cockpit every bare ticker ($EXFIL, not $2.76) opens that
// coin on the chart — seat cards, the holding strip, recent trades, chips — without wiring each spot. A ticker already inside a button or
// a link keeps that control's own click. Pure: reads the element, never the network.
const TICKER = /^\$([A-Za-z][A-Za-z0-9._-]{0,15})$/;
export function symOf(el, root) {
  let n = el;
  for (let i = 0; n && n !== root && i < 6; i += 1, n = n.parentElement) {
    const tag = n.tagName;
    if (tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || n.getAttribute?.('role') === 'button') return null;
  }
  const m = TICKER.exec(String(el?.textContent || '').trim().split(/\s+/)[0] || '');
  return m && el.children?.length === 0 ? m[1] : null;
}
export const tapSym = sym => window.dispatchEvent(new CustomEvent('feeless:cockpit-coin-sym', { detail: { sym } }));

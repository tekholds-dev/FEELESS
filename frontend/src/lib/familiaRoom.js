// 🏙 FAMILIA ROOMS (owner, 2026-10-23: "no redirects — everything done inside Familia"): a FEELESS tool opens INSIDE Familia when a Familia dock
// is mounted (FamiliaTrade.jsx slides it over the room — Fuse cards, Launch, Rug Shield), else the link works as a normal page link.
// Dependency-free so a global piece (the FeeCat widget's mini deck) can use it without pulling the Familia chunk into every page.
export const ROOM_PATH = { fuse: '/terminal/fuse', launch: '/terminal/launch', shield: '/terminal/reputation' };
export const familiaDocked = () => typeof window !== 'undefined' && (window.__familiaDocks || 0) > 0;
export const dockCount = n => { if (typeof window !== 'undefined') window.__familiaDocks = Math.max(0, (window.__familiaDocks || 0) + n); };
// → true when the room opened in Familia (the click's navigation is cancelled); false = no dock, let the link go
export function familiaRoom(kind, e) {
  if (!ROOM_PATH[kind] || !familiaDocked()) return false;
  e?.preventDefault?.();
  window.dispatchEvent(new CustomEvent('feeless:familia-trade', { detail: { kind } }));
  return true;
}

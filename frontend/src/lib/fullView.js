// ⤢ One full-screen toggle for any preview (owner 2026-11-10: "preview not big enough to see", the PoStatic code/static window small).
// Real browser full screen when allowed; otherwise the element is pinned over the whole page (class is-pgfull). Esc leaves either.
export function toggleFull(el) {
  if (!el) return false;
  if (document.fullscreenElement) { document.exitFullscreen?.(); return false; }
  if (el.classList.contains('is-pgfull')) { el.classList.remove('is-pgfull'); return false; }
  const pin = () => {
    el.classList.add('is-pgfull');
    const off = e => { if (e.key === 'Escape') { el.classList.remove('is-pgfull'); window.removeEventListener('keydown', off); } };
    window.addEventListener('keydown', off);
  };
  try { if (el.requestFullscreen) el.requestFullscreen().catch(pin); else pin(); } catch { pin(); }
  return true;
}

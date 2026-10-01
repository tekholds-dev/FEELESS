import '../styles/tips.css';
// One sitewide tooltip layer for [data-tip]: a single fixed bubble on <body>, so no card's overflow (clip / scroll rows)
// can cut it off. Placed above the element (below if no room), clamped to the viewport. Hover + keyboard focus.
let bubble = null;
let current = null;

function place(el) {
  const r = el.getBoundingClientRect(); const b = bubble.getBoundingClientRect();
  const left = Math.min(window.innerWidth - b.width - 8, Math.max(8, r.left + r.width / 2 - b.width / 2));
  const above = r.top - b.height - 8;
  bubble.style.transform = `translate(${Math.round(left)}px, ${Math.round(above >= 8 ? above : r.bottom + 8)}px)`;
}

function show(el) {
  if (!bubble) { bubble = document.createElement('div'); bubble.className = 'tip-layer'; bubble.setAttribute('role', 'tooltip'); document.body.appendChild(bubble); }
  current = el; bubble.textContent = el.getAttribute('data-tip'); bubble.classList.add('on'); place(el);
}
function hide(el) { if (bubble && (!el || el === current)) { bubble.classList.remove('on'); current = null; } }

export function installTipLayer() {
  const find = t => (t instanceof Element ? t.closest('[data-tip]') : null);
  document.addEventListener('mouseover', e => { const el = find(e.target); if (el && el !== current) show(el); else if (!el) hide(); }, { passive: true });
  document.addEventListener('focusin', e => { const el = find(e.target); if (el) show(el); });
  document.addEventListener('focusout', e => hide(find(e.target)));
  window.addEventListener('scroll', () => hide(), { passive: true, capture: true });
}

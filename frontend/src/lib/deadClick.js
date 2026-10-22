// 🖱 DEAD-CLICK CATCHER (owner, 2026-10-22: "fix the click issues without a massive need for signin"): the Agents tab's dead clicks never
// reproduced on fixtures (every control hit-tests clean, clicks land under live ticks), so the browser that HAS the bug reports it itself —
// no sign-in, no screen share. Two causes, both caught site-wide:
//   1 · a LAYER on top: the topmost element under the press is not a control, has no pointer cursor, isn't a modal shade, and a real
//       control sits under it → filed to HQ › Bugs as "[dead click] <layer> sits over <control>" (once per pair per page load, ≤ 4).
//     When the layer is decorative (aria-hidden), the click is delivered to the control under it as well.
//   2 · a REMOUNT under the press: a live tick replaced the pressed control between pointerdown and pointerup, so the browser sent the
//       click to a parent. When the control now under the finger has the SAME test id, the click is delivered to it (that is the control
//       the user pressed) and the remount is filed too.
// Pure DOM; never blocks or cancels an event.
export const CONTROL = 'button, a[href], [role="button"], [role="tab"], [role="switch"], [role="checkbox"], [role="menuitem"], input, select, textarea, summary, label';
const SHADE = /shade|backdrop|overlay|modal|scrim|veil/i;
const MAX_REPORTS = 4;

export const describe = el => {
  if (!el || !el.tagName) return '?';
  const tid = el.dataset?.testid ? `[${el.dataset.testid}]` : '';
  const cls = String(el.className && el.className.baseVal != null ? el.className.baseVal : el.className || '').trim().split(/\s+/).filter(Boolean).slice(0, 3).join('.');
  return `${el.tagName.toLowerCase()}${cls ? `.${cls}` : ''}${tid}`;
};

// the control a press at (x, y) can't reach, and the layer hiding it — null when the press is fine
export function blockerAt(x, y, doc = document, win = window) {
  const stack = typeof doc.elementsFromPoint === 'function' ? doc.elementsFromPoint(x, y) : [];
  const top = stack[0];
  if (!top || top.closest?.(CONTROL)) return null;
  for (let n = top; n && n !== doc.body; n = n.parentElement) {
    if (SHADE.test(String(n.className || '')) || n.getAttribute?.('aria-modal') === 'true') return null;   // a modal's shade is MEANT to cover the page
  }
  try { if (win.getComputedStyle(top).cursor === 'pointer') return null; } catch { /* detached */ }   // a div with its own onClick
  const control = stack.slice(1).find(el => !el.contains(top) && el.matches?.(CONTROL) && !el.disabled);
  return control ? { layer: top, control } : null;
}

export function installDeadClick({ doc = document, win = window, report } = {}) {
  const seen = new Set(); let sent = 0; let down = null; let lastClick = { at: 0, el: null };
  const file = text => {
    if (seen.has(text) || sent >= MAX_REPORTS) return; seen.add(text); sent += 1;
    (win.__deadClicks = win.__deadClicks || []).push({ at: Date.now(), text });
    const send = report || (t => win.fetch?.('/api/reputation/bugs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind: 'bug', page: `${win.location.pathname}${win.location.search}`.slice(0, 300), text: t }) }).catch(() => {}));
    send(text);
  };
  doc.addEventListener('pointerdown', e => {
    if (e.button !== 0) { down = null; return; }
    const ctl = e.target?.closest?.(CONTROL) || null;
    down = { x: e.clientX, y: e.clientY, ctl, tid: ctl?.dataset?.testid || '' };
    const b = ctl ? null : blockerAt(e.clientX, e.clientY, doc, win);
    if (b) { file(`[dead click] ${describe(b.layer)} sits over ${describe(b.control)} — the press never reached it`);
      if (b.layer.closest?.('[aria-hidden="true"]')) down.through = b.control; }   // decorative art over a control: the click goes through to it
  }, { capture: true, passive: true });
  doc.addEventListener('click', e => { lastClick = { at: Date.now(), el: e.target }; }, { capture: true, passive: true });
  doc.addEventListener('pointerup', e => {
    const d = down; down = null;
    if (d?.through && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 8 && d.through.isConnected) { const to = d.through; const t0 = Date.now();
      win.setTimeout(() => { if (!(lastClick.at >= t0 && lastClick.el && to.contains(lastClick.el))) to.click(); }, 0); return; }
    if (!d?.ctl || d.ctl.isConnected || !d.tid) return;
    const now = doc.elementFromPoint?.(e.clientX, e.clientY)?.closest?.(CONTROL);
    if (!now || now.dataset?.testid !== d.tid || now.disabled) return;
    const t0 = Date.now();
    win.setTimeout(() => {   // the browser's own click (if any) has been dispatched by now
      if (lastClick.at >= t0 && lastClick.el && now.contains(lastClick.el)) return;
      file(`[dead click] ${describe(now)} re-rendered under the press — click delivered`);
      now.click();
    }, 0);
  }, { capture: true, passive: true });
}

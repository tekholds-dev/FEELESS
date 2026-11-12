// 📐 An element's own size, read by a ResizeObserver instead of a CSS container query (2026-11-11: three @container boxes on
// HQ › Sicario's made every full style pass take 13–38 s in Chrome — 39 ms with them gone; 2026-11-12 every other box moved too,
// and styles/noContainerQueries.test.js keeps them out).
// boxRef(widths, opts) makes a callback ref (React 19 ref cleanup): make it once at module level, then <div ref={fooBox}>.
// It works on elements that mount late and on many elements at once (each gets its own observer).
//   widths: number | number[] → `data-wN` is set while the box is at most N px wide (CSS: `.x[data-w560] .y`; min-width: `:not([data-wN])`).
//   vars:   also writes --box-w / --box-h in px, for what cqw / cqh used to read (5cqw = calc(var(--box-w) * .05)).
//   parent: measure the element's parent instead (a child sized by its window body).
export function boxRef(widths = [], { vars = false, parent = false } = {}) {
  const ws = [].concat(widths).map(Number);
  return (node) => {
    const el = parent ? node?.parentElement : node;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect;
      for (const w of ws) el.toggleAttribute(`data-w${w}`, width > 0 && width <= w);
      if (vars) { el.style.setProperty('--box-w', `${Math.round(width)}px`); el.style.setProperty('--box-h', `${Math.round(height)}px`); }
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      for (const w of ws) el.removeAttribute(`data-w${w}`);
      if (vars) { el.style.removeProperty('--box-w'); el.style.removeProperty('--box-h'); }
    };
  };
}

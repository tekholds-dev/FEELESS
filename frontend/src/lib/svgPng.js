// ⬇ Any drawn avatar (an inline SVG styled by CSS) → a PNG file the user keeps (owner 2026-10-31: "download my agent's img from its dash").
// The page's CSS does not travel with the SVG, so every shape's computed paint is written inline first; then canvas → PNG → download.
const PAINT = ['fill', 'stroke', 'stroke-width', 'opacity', 'fill-opacity', 'stroke-opacity', 'stop-color', 'stop-opacity', 'stroke-linecap', 'stroke-linejoin', 'transform-origin', 'mix-blend-mode'];

export function inlineSvg(svg, size = 1024) {
  const clone = svg.cloneNode(true);
  const src = [svg, ...svg.querySelectorAll('*')]; const dst = [clone, ...clone.querySelectorAll('*')];
  src.forEach((el, i) => { const cs = window.getComputedStyle(el); const out = dst[i];
    PAINT.forEach(k => { const v = cs.getPropertyValue(k); if (v && v !== 'normal') out.style.setProperty(k, v); });
    if (cs.display === 'none' || cs.visibility === 'hidden') out.setAttribute('visibility', 'hidden'); });
  const vb = String(svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
  const w = vb.length === 4 && vb[2] > 0 ? vb[2] : svg.clientWidth || 100; const h = vb.length === 4 && vb[3] > 0 ? vb[3] : svg.clientHeight || 100;
  if (!clone.getAttribute('viewBox')) clone.setAttribute('viewBox', `0 0 ${w} ${h}`);
  clone.setAttribute('width', String(size)); clone.setAttribute('height', String(Math.round(size * h / w)));
  clone.removeAttribute('class'); clone.style.removeProperty('width'); clone.style.removeProperty('height');
  const out = new XMLSerializer().serializeToString(clone);
  return out.includes('xmlns="http://www.w3.org/2000/svg"') ? out : out.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
}

export function fileName(name, ext = 'png') {
  return `${String(name || 'agent').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'agent'}-feeless.${ext}`;
}

// the agent's picture as a PNG blob (its download and its Agent Pass image both draw it here)
export async function svgPngBlob(svg, size = 1024) {
  if (!svg) throw new Error('No picture to save.');
  const markup = inlineSvg(svg, size);
  const url = URL.createObjectURL(new Blob([markup], { type: 'image/svg+xml' }));
  try {
    const img = await new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => no(new Error('The picture could not be drawn.')); i.src = url; });
    const c = document.createElement('canvas'); c.width = size; c.height = Math.round(size * (img.height / img.width || 1));
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    return { blob: await new Promise(ok => c.toBlob(ok, 'image/png')), markup };
  } finally { URL.revokeObjectURL(url); }
}

export async function downloadSvgPng(svg, name, size = 1024) {
  const { blob, markup } = await svgPngBlob(svg, size);
  {
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob || new Blob([markup], { type: 'image/svg+xml' })); a.download = fileName(name, blob ? 'png' : 'svg');
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    return a.download;
  }
}

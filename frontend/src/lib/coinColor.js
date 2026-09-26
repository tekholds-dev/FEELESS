import { useEffect, useState } from 'react';

// A coin's signature color, sampled from its own logo (via our same-origin image proxy so the
// canvas isn't tainted). Picks the most saturated, mid-bright hue — not the average, which is
// usually a muddy grey. Falls back to a stable hue from the address so every coin still glows.
const cache = new Map();

const hashHue = s => { let h = 0; for (let i = 0; i < (s || '').length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h % 360; };
const fallback = seed => `hsl(${hashHue(seed)}, 80%, 60%)`;

function sample(img) {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(img, 0, 0, 32, 32);
  const px = g.getImageData(0, 0, 32, 32).data;
  const bins = new Map();
  for (let i = 0; i < px.length; i += 4) {
    const [r, gg, b, a] = [px[i], px[i + 1], px[i + 2], px[i + 3]];
    if (a < 128) continue;
    const max = Math.max(r, gg, b); const min = Math.min(r, gg, b);
    const l = (max + min) / 510; const sat = max === min ? 0 : (max - min) / (255 - Math.abs(max + min - 255));
    if (l < 0.18 || l > 0.9 || sat < 0.25) continue; // skip black outlines, white backgrounds, greys
    const key = `${r >> 5},${gg >> 5},${b >> 5}`;
    const bin = bins.get(key) || { n: 0, r: 0, g: 0, b: 0, s: 0 };
    bin.n++; bin.r += r; bin.g += gg; bin.b += b; bin.s += sat;
    bins.set(key, bin);
  }
  let best = null;
  bins.forEach(bin => { const score = bin.n * (bin.s / bin.n); if (!best || score > best.score) best = { ...bin, score }; });
  if (!best) return null;
  return `rgb(${Math.round(best.r / best.n)}, ${Math.round(best.g / best.n)}, ${Math.round(best.b / best.n)})`;
}

export function useCoinColor(imageUrl, seed) {
  const key = imageUrl || seed || '';
  const [color, setColor] = useState(() => cache.get(key) || fallback(seed || imageUrl));
  useEffect(() => {
    if (cache.has(key)) { setColor(cache.get(key)); return undefined; }
    setColor(fallback(seed || imageUrl));
    if (!imageUrl || typeof Image === 'undefined') return undefined;
    let alive = true;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      let c = null;
      try { c = sample(img); } catch { /* tainted or decode failure — keep fallback */ }
      const out = c || fallback(seed || imageUrl);
      cache.set(key, out);
      if (alive) setColor(out);
    };
    img.src = /^https:\/\//.test(imageUrl) ? `/api/reputation/img?u=${encodeURIComponent(imageUrl)}` : imageUrl;
    return () => { alive = false; };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return color;
}

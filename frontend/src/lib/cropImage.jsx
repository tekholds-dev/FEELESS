import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';

// Shapes every upload slot uses. `out` is the saved pixel size, so each slot stores exactly
// what it displays: sharp on retina, no wasted bytes.
export const CROP = {
  avatar: { aspect: 1, round: true, out: [512, 512], title: 'Profile picture' },
  banner: { aspect: 3, out: [1500, 500], title: 'Banner' },
  seasonBanner: { aspect: 16 / 9, out: [1600, 900], title: 'Season banner' },
  badge: { aspect: 280 / 384, out: [560, 768], title: 'Badge card' },
  token: { aspect: 1, round: true, out: [512, 512], title: 'Token image' },
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

function Cropper({ src, isGif, shape, done }) {
  const frame = useRef(null);
  const [img, setImg] = useState(null);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const [zoom, setZoom] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef(null);
  const pts = useRef(new Map());

  useEffect(() => { const i = new Image(); i.onload = () => setImg(i); i.src = src; }, [src]);
  useEffect(() => {
    const el = frame.current; if (!el) return undefined;
    const ro = new ResizeObserver(([e]) => setBox({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(el); return () => ro.disconnect();
  }, []);
  useEffect(() => {
    const esc = e => e.key === 'Escape' && done(null);
    document.addEventListener('keydown', esc); return () => document.removeEventListener('keydown', esc);
  }, [done]);

  const base = img && box.w ? Math.max(box.w / img.width, box.h / img.height) : 1;
  const s = base * zoom;
  const fit = (x, y, sc = s) => img ? { x: clamp(x, box.w - img.width * sc, 0), y: clamp(y, box.h - img.height * sc, 0) } : { x, y };
  // Centre once the image and frame are both measured.
  useEffect(() => { if (img && box.w) setPos(fit((box.w - img.width * base) / 2, (box.h - img.height * base) / 2, base)); }, [img, box.w, box.h]); // eslint-disable-line react-hooks/exhaustive-deps

  const zoomTo = (z, cx = box.w / 2, cy = box.h / 2) => {
    const nz = clamp(z, 1, 6); const ns = base * nz;
    setZoom(nz);
    setPos(p => fit(cx - (cx - p.x) * (ns / s), cy - (cy - p.y) * (ns / s), ns));
  };
  const down = e => { e.currentTarget.setPointerCapture(e.pointerId); pts.current.set(e.pointerId, [e.clientX, e.clientY]); drag.current = { x: e.clientX, y: e.clientY, pos, pinch: null }; };
  const move = e => {
    if (!pts.current.has(e.pointerId)) return;
    pts.current.set(e.pointerId, [e.clientX, e.clientY]);
    const p = [...pts.current.values()];
    if (p.length === 2) {
      const d = Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]);
      if (!drag.current.pinch) drag.current.pinch = { d, z: zoom };
      zoomTo(drag.current.pinch.z * (d / drag.current.pinch.d));
      return;
    }
    const st = drag.current; setPos(fit(st.pos.x + e.clientX - st.x, st.pos.y + e.clientY - st.y));
  };
  const up = e => { pts.current.delete(e.pointerId); if (pts.current.size < 2 && drag.current) drag.current = { ...drag.current, pinch: null, x: e.clientX, y: e.clientY, pos }; };
  const wheel = e => { const r = frame.current.getBoundingClientRect(); zoomTo(zoom * (e.deltaY < 0 ? 1.08 : 1 / 1.08), e.clientX - r.left, e.clientY - r.top); };

  const save = () => {
    const [W, H] = shape.out;
    const sw = box.w / s, sh = box.h / s; const sx = -pos.x / s, sy = -pos.y / s;
    const c = document.createElement('canvas');
    // Never upscale past the source: a small image stays crisp instead of turning to mush.
    const k = Math.min(1, sw / W); c.width = Math.round(W * k); c.height = Math.round(H * k);
    const g = c.getContext('2d'); g.imageSmoothingQuality = 'high';
    g.drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height);
    c.toBlob(b => done(b ? new File([b], 'crop.webp', { type: 'image/webp' }) : null), 'image/webp', 0.92);
  };

  return <div className="crop-back" onPointerDown={e => e.target === e.currentTarget && done(null)}>
    <div className="crop-card" role="dialog" aria-label={`Crop ${shape.title}`}>
      <header><b>{shape.title}</b><small>Drag to position · scroll or pinch to zoom</small></header>
      <div className="crop-stage">
        <div ref={frame} className={`crop-frame ${shape.round ? 'round' : ''} ${shape.aspect <= 1 ? 'tall' : ''}`} style={{ aspectRatio: shape.aspect }}
          onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onWheel={wheel} data-testid="crop-frame">
          {img ? <img src={src} alt="" draggable={false} style={{ width: img.width * s, height: img.height * s, transform: `translate3d(${pos.x}px,${pos.y}px,0)` }} /> : <span className="crop-load" />}
        </div>
      </div>
      <label className="crop-zoom"><span>−</span><input type="range" min="1" max="6" step="0.01" value={zoom} onChange={e => zoomTo(Number(e.target.value))} aria-label="Zoom" /><span>+</span></label>
      {isGif && <p className="crop-note">Cropping saves a still frame. Keep it animated to upload the GIF as-is; it fills the slot centred.</p>}
      <footer>
        <button type="button" className="btn-outline" onClick={() => done(null)}>Cancel</button>
        {isGif && <button type="button" className="btn-outline" onClick={() => done('original')} data-testid="crop-keep-gif">Keep animated</button>}
        <button type="button" className="btn-primary" disabled={!img} onClick={save} data-testid="crop-apply">Apply crop</button>
      </footer>
    </div>
  </div>;
}

// Opens the cropper for `file`. Resolves a cropped webp File, the original file (GIF kept
// animated), or null when the user cancels.
export function cropImage(file, shape = CROP.avatar) {
  return new Promise(resolve => {
    const host = document.createElement('div'); document.body.appendChild(host);
    const root = createRoot(host); const url = URL.createObjectURL(file);
    const done = r => { root.unmount(); host.remove(); URL.revokeObjectURL(url); resolve(r === 'original' ? file : r); };
    root.render(<Cropper src={url} isGif={file.type === 'image/gif'} shape={shape} done={done} />);
  });
}

// Crop → resize → upload to FEELESS. Resolves the upload path ('/api/reputation/uploads/<id>.webp') or null if cancelled.
export async function uploadCropped(file, shape, max = 512) {
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file?.type || '')) throw new Error('PNG, JPG, WEBP or GIF');
  if (file.size > 10_000_000) throw new Error('Max 10 MB');
  const cropped = await cropImage(file, shape);
  if (!cropped) return null;
  const bitmap = await createImageBitmap(cropped);
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL(cropped.type === 'image/png' || cropped.type === 'image/gif' ? 'image/png' : 'image/webp', 0.9);
  const { apiUrl } = await import('./api');
  const res = await fetch(apiUrl('/api/reputation/uploads'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataUrl }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Upload failed');
  return data.url;
}

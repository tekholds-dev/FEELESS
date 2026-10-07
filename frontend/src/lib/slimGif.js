import { GIFEncoder, quantize, applyPalette } from 'gifenc';

// 🪶 Slim an animated GIF before upload so it never lags a page: no bigger than the box it is shown in, ≤ 12 frames a second,
// ≤ 72 frames. `gifPlan` is the pure decision (tested); `slimGif` does it in the browser (ImageDecoder — Chrome / Edge / Safari 17;
// anywhere else the file goes up untouched).
export const GIF_FPS = 12, GIF_MAX_FRAMES = 72;

// → null when the GIF is already light, else { w, h, frames: [source frame indexes], delay ms }
export function gifPlan({ w, h, frames, durMs }, out, fps = GIF_FPS, maxFrames = GIF_MAX_FRAMES) {
  if (!(w > 0 && h > 0) || frames < 2) return null;
  const dur = durMs > 0 ? durMs : frames * 100;
  const k = out ? Math.min(1, Math.max(out[0] / w, out[1] / h)) : 1;          // still covers its box after shrinking
  const want = Math.max(2, Math.min(frames, maxFrames, Math.ceil(dur / 1000 * fps)));
  if (k > 0.9 && want >= frames) return null;
  const kk = k > 0.9 ? 1 : k, pick = Array.from({ length: want }, (_, i) => Math.min(frames - 1, Math.floor(i * frames / want)));
  return { w: Math.max(2, Math.round(w * kk)), h: Math.max(2, Math.round(h * kk)), frames: pick, delay: Math.round(dur / want) };
}

export async function slimGif(file, out) {
  if (typeof window === 'undefined' || typeof window.ImageDecoder === 'undefined' || file.type !== 'image/gif') return file;
  const dec = new window.ImageDecoder({ data: await file.arrayBuffer(), type: 'image/gif' });
  await dec.tracks.ready; const n = dec.tracks.selectedTrack?.frameCount || 0;
  if (n < 2 || n > 2000) return file;
  let durMs = 0, w = 0, h = 0;
  for (let i = 0; i < n; i++) { const { image } = await dec.decode({ frameIndex: i }); durMs += (image.duration || 100000) / 1000; w = image.displayWidth; h = image.displayHeight; image.close(); }
  const plan = gifPlan({ w, h, frames: n, durMs }, out);
  if (!plan) return file;
  const c = document.createElement('canvas'); c.width = plan.w; c.height = plan.h; const g = c.getContext('2d', { willReadFrequently: true }), enc = GIFEncoder();
  for (const i of plan.frames) { const { image } = await dec.decode({ frameIndex: i }); g.clearRect(0, 0, plan.w, plan.h); g.drawImage(image, 0, 0, plan.w, plan.h); image.close();
    const { data } = g.getImageData(0, 0, plan.w, plan.h), pal = quantize(data, 256); enc.writeFrame(applyPalette(data, pal), plan.w, plan.h, { palette: pal, delay: plan.delay }); }
  enc.finish(); const slim = new File([enc.bytes()], file.name, { type: 'image/gif' });
  return slim.size < file.size ? slim : file;
}

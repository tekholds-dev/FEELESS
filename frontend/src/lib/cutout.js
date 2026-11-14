// ✂️ POC-PLAY cut-out (owner 2026-11-13, item 2): one click lifts a product OR a person off its background, free, on the device, no key.
// U²-Net-p (Apache-2.0, 4.6 MB, general objects — MODNet only does portraits, proved 2026-11-14: 1.5% of a logo kept vs 17% here) run by
// onnxruntime-web (MIT). Both load once on first use and the browser caches them. RMBG-1.4/2.0 are non-commercial, so never used.
const ORT = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/';
export const CUTOUT_MODEL = 'https://huggingface.co/BritishWerewolf/U-2-Netp/resolve/7112208dbac3a3642496c8d54e2f0f9bb3dc1dc8/onnx/model.onnx';
export const SIDE = 320;
const MEAN = [0.485, 0.456, 0.406];
const STD = [0.229, 0.224, 0.225];

let ready = null;
/** Load the runtime + model once. `onStep(text)` says what is happening. */
export function loadCutout(onStep) {
  if (!ready) {
    ready = (async () => {
      onStep?.('Loading the cut-out tool (first time only, about 5 MB)…');
      if (!window.ort) {
        await new Promise((res, rej) => { const s = document.createElement('script'); s.src = `${ORT}ort.min.js`; s.onload = res; s.onerror = () => rej(new Error('The cut-out tool did not load. Check the connection and try again.')); document.head.appendChild(s); });
      }
      window.ort.env.wasm.wasmPaths = ORT;
      return window.ort.InferenceSession.create(CUTOUT_MODEL);
    })().catch(e => { ready = null; throw e; });
  }
  return ready;
}

/** Pure: RGBA pixels (SIDE×SIDE) → the model's input, channels first, ImageNet-normalised. */
export function toInput(rgba, side = SIDE) {
  const n = side * side; const f = new Float32Array(3 * n);
  for (let i = 0; i < n; i += 1) for (let ch = 0; ch < 3; ch += 1) f[ch * n + i] = (rgba[i * 4 + ch] / 255 - MEAN[ch]) / STD[ch];
  return f;
}

/** Pure: the model's saliency map → 0–255, stretched to its own min..max (U²-Net's maps are relative). */
export function toMask(data) {
  let mn = Infinity; let mx = -Infinity;
  for (const v of data) { if (v < mn) mn = v; if (v > mx) mx = v; }
  const span = Math.max(1e-6, mx - mn); const out = new Uint8ClampedArray(data.length);
  for (let i = 0; i < data.length; i += 1) out[i] = Math.round(((data[i] - mn) / span) * 255);
  return out;
}

/** Pure: copy a one-channel mask (0–255, same pixel count) into the alpha of RGBA pixels, in place. Soft edges stay soft. */
export function applyMask(rgba, mask) {
  const n = rgba.length / 4;
  if (!mask || mask.length !== n) throw new Error('The mask does not match the picture.');
  for (let i = 0; i < n; i += 1) rgba[i * 4 + 3] = Math.round((rgba[i * 4 + 3] * mask[i]) / 255);
  return rgba;
}

/** Pure: the share of pixels the mask keeps. Almost none or almost all = no subject found. */
export function maskKept(mask) {
  let on = 0; for (let i = 0; i < mask.length; i += 1) if (mask[i] > 127) on += 1;
  return mask.length ? on / mask.length : 0;
}

const loadImg = src => new Promise((res, rej) => { const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => rej(new Error('That picture did not load.')); i.src = src; });

/** A picture (URL or data URL) → a PNG data URL with its background removed. Throws words the canvas shows. */
export async function cutOut(src, onStep) {
  const sess = await loadCutout(onStep);
  onStep?.('Cutting it out…');
  const img = await loadImg(src); const W = img.naturalWidth; const H = img.naturalHeight;
  const s = document.createElement('canvas'); s.width = SIDE; s.height = SIDE; const sg = s.getContext('2d'); sg.drawImage(img, 0, 0, SIDE, SIDE);
  const r = await sess.run({ [sess.inputNames[0]]: new window.ort.Tensor('float32', toInput(sg.getImageData(0, 0, SIDE, SIDE).data), [1, 3, SIDE, SIDE]) });
  const small = toMask(r[sess.outputNames[0]].data);
  const kept = maskKept(small);
  if (kept < 0.01 || kept > 0.97) throw new Error('No clear subject to cut out. Try a picture with one product or person in front.');
  const m = document.createElement('canvas'); m.width = SIDE; m.height = SIDE; const mg = m.getContext('2d'); const md = mg.createImageData(SIDE, SIDE);
  for (let i = 0; i < small.length; i += 1) { md.data[i * 4] = small[i]; md.data[i * 4 + 3] = 255; }
  mg.putImageData(md, 0, 0);
  const big = document.createElement('canvas'); big.width = W; big.height = H; const bg = big.getContext('2d'); bg.drawImage(m, 0, 0, W, H);   // smooth upscale of the mask
  const up = bg.getImageData(0, 0, W, H).data; const mask = new Uint8ClampedArray(W * H); for (let i = 0; i < mask.length; i += 1) mask[i] = up[i * 4];
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const px = g.getImageData(0, 0, W, H); applyMask(px.data, mask); g.putImageData(px, 0, 0);
  return c.toDataURL('image/png');
}

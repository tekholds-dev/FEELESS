// 🎨 POC-PLAY (owner 2026-11-13): the pure half of the click-and-grab playground (components/command/PocPlay.jsx draws it with Konva).
// Frames are the starting points (a post, a story, a phone mockup, a billboard…); every frame is plain layers, so the same canvas edits them
// all. Colours come from the page tokens at run time (tokens()), never written here.

export const FRAMES = {
  free: { label: 'Free', w: 1200, h: 1200, tip: 'The picture alone, on its own size' },
  post: { label: 'Post 1:1', w: 1080, h: 1080, tip: 'A square social post with a caption' },
  story: { label: 'Story 9:16', w: 1080, h: 1920, tip: 'A tall story / reel cover' },
  thumb: { label: 'Thumbnail', w: 1280, h: 720, tip: 'A wide video thumbnail with a big title' },
  phone: { label: 'Phone', w: 1200, h: 1500, tip: 'Your picture on a phone screen' },
  billboard: { label: 'Billboard', w: 1600, h: 1000, tip: 'Your picture on a billboard over a street' },
  shelf: { label: 'Shelf', w: 1200, h: 1200, tip: 'A product standing on a shop shelf' },
  launch: { label: 'Launch', w: 1080, h: 1350, tip: 'A product launch card: badge, headline, product' },
  ideas: { label: 'Idea board', w: 1600, h: 1000, tip: 'Sticky notes around your picture, to plan from' },
  adset: { label: 'Ad set', w: 1800, h: 1000, tip: 'One product, three ad sizes side by side: square, story and banner' },
};
export const FRAME_KEYS = Object.keys(FRAMES);

// canvas fills can't read color-mix(): a token colour at an opacity, done by hand (#rgb / #rrggbb / rgb())
export function alpha(c, a) {
  const s = String(c || '').trim(); let m = s.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (m) { const h = m[1].length === 3 ? m[1].replace(/./g, x => x + x) : m[1]; return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`; }
  m = s.match(/^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/i); return m ? `rgba(${m[1]},${m[2]},${m[3]},${a})` : 'rgba(0,0,0,.2)';
}

let seq = 0;
export const newId = p => `${p}${Date.now().toString(36)}${(seq++).toString(36)}`;

// pure: place a w×h picture inside a box (contain = all of it shows; cover = it fills the box)
export function fitInto(iw, ih, bx, by, bw, bh, mode = 'contain') {
  if (!(iw > 0 && ih > 0)) return { x: bx, y: by, width: bw, height: bh };
  const s = mode === 'cover' ? Math.max(bw / iw, bh / ih) : Math.min(bw / iw, bh / ih);
  const width = iw * s; const height = ih * s;
  return { x: bx + (bw - width) / 2, y: by + (bh - height) / 2, width, height };
}

// pure: the centred crop of a w×h picture that has this aspect (width / height)
export function cropFor(iw, ih, aspect) {
  if (!(iw > 0 && ih > 0 && aspect > 0)) return { x: 0, y: 0, width: iw, height: ih };
  if (iw / ih > aspect) { const width = ih * aspect; return { x: (iw - width) / 2, y: 0, width, height: ih }; }
  const height = iw / aspect; return { x: 0, y: (ih - height) / 2, width: iw, height };
}

// pure: the picture filling a box exactly (cropped, never stretched)
export function coverBox(img, x, y, width, height) {
  return { x, y, width, height, crop: cropFor(img.w, img.h, width / height) };
}

// pure: a frame's layers for one main picture img = { src, w, h } (null = no picture yet). Decor is locked; the main picture is not.
export function frameLayers(key, img, t) {
  const F = FRAMES[key] || FRAMES.free; const { w: W, h: H } = F; const out = [];
  const deco = (type, p) => out.push({ id: newId('d'), type, deco: true, ...p });
  const main = box => img && out.push({ id: 'main', type: 'image', main: true, src: img.src, ...box });
  const title = (text, p) => out.push({ id: newId('t'), type: 'text', text, fontSize: 64, fontStyle: 'bold', fill: t.text, ...p });
  if (key === 'free') {
    const s = img ? Math.min(1, 1600 / Math.max(img.w, img.h)) : 1;
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    main(img ? fitInto(img.w * s, img.h * s, 0, 0, W, H) : null);
  } else if (key === 'post') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    main(img ? coverBox(img, 0, 0, W, H - 180) : null);
    title('Your caption here', { x: 56, y: H - 140, width: W - 112, fontSize: 52 });
  } else if (key === 'story') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    main(img ? coverBox(img, 0, 0, W, H) : null);
    deco('rect', { x: 0, y: 0, width: W, height: 420, fillLinearGradientStartPoint: { x: 0, y: 0 }, fillLinearGradientEndPoint: { x: 0, y: 420 }, fillLinearGradientColorStops: [0, t.shade, 1, t.clear] });
    title('Your headline', { x: 64, y: 120, width: W - 128, fontSize: 84 });
  } else if (key === 'thumb') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    main(img ? coverBox(img, W * 0.46, 0, W * 0.54, H) : null);
    title('BIG TITLE', { x: 48, y: H / 2 - 110, width: W * 0.46 - 80, fontSize: 92, fill: t.accent });
  } else if (key === 'phone') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    deco('rect', { x: W / 2 - 330, y: 90, width: 660, height: 1320, cornerRadius: 86, fill: t.ink, stroke: t.line, strokeWidth: 6, shadowColor: t.shade, shadowBlur: 60, shadowOffsetY: 24 });
    main(img ? { ...coverBox(img, W / 2 - 300, 120, 600, 1260), cornerRadius: 62 } : null);
    deco('rect', { x: W / 2 - 90, y: 140, width: 180, height: 38, cornerRadius: 19, fill: t.ink });
  } else if (key === 'billboard') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fillLinearGradientStartPoint: { x: 0, y: 0 }, fillLinearGradientEndPoint: { x: 0, y: H }, fillLinearGradientColorStops: [0, t.sky, 1, t.bg] });
    deco('rect', { x: 0, y: H - 150, width: W, height: 150, fill: t.ink });
    deco('rect', { x: W / 2 - 330, y: 600, width: 34, height: 280, fill: t.line });
    deco('rect', { x: W / 2 + 296, y: 600, width: 34, height: 280, fill: t.line });
    deco('rect', { x: W / 2 - 560, y: 120, width: 1120, height: 500, fill: t.ink, stroke: t.line, strokeWidth: 14 });
    main(img ? coverBox(img, W / 2 - 546, 134, 1092, 472) : null);
  } else if (key === 'shelf') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    deco('rect', { x: 80, y: 880, width: W - 160, height: 36, cornerRadius: 6, fill: t.line, shadowColor: t.shade, shadowBlur: 30, shadowOffsetY: 18 });
    deco('ellipse', { x: W / 2, y: 878, radiusX: 260, radiusY: 22, fill: t.shade });
    main(img ? fitInto(img.w, img.h, W / 2 - 300, 220, 600, 660) : null);
    if (out.length && img) { const m = out[out.length - 1]; m.y = 878 - m.height; }   // it stands ON the shelf
  } else if (key === 'launch') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    deco('circle', { x: W / 2, y: 720, radius: 430, fill: t.glow });
    main(img ? fitInto(img.w, img.h, 140, 360, W - 280, 720) : null);
    out.push({ id: newId('b'), type: 'badge', text: 'NEW', x: 64, y: 64, fontSize: 44, fill: t.accentInk, bg: t.accent });
    title('Meet the new thing', { x: 64, y: 170, width: W - 128, fontSize: 76 });
    title('Out now', { x: 64, y: H - 150, width: W - 128, fontSize: 44, fontStyle: 'normal', fill: t.dim });
  } else if (key === 'ideas') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    main(img ? coverBox(img, W / 2 - 260, H / 2 - 200, 520, 400) : null);
    [[90, 90], [600, 70], [1130, 100], [110, 640], [1120, 620]].forEach(([x, y], i) => {
      out.push({ id: newId('n'), type: 'note', x, y, width: 360, height: 260, rotation: [-3, 2, -2, 3, -1][i], text: `Idea ${i + 1}`, fill: t.note, ink: t.noteInk });
    });
  } else if (key === 'adset') {
    deco('rect', { x: 0, y: 0, width: W, height: H, fill: t.bg });
    const cards = [['SQUARE 1:1', 60, 200, 620, 620], ['STORY 9:16', 740, 60, 495, 880], ['BANNER 16:9', 1295, 300, 445, 250]];
    cards.forEach(([lab, x, y, w, h], i) => {
      deco('rect', { x: x - 6, y: y - 6, width: w + 12, height: h + 12, cornerRadius: 18, fill: t.ink, stroke: t.line, strokeWidth: 3 });
      if (img) out.push({ id: i ? newId('i') : 'main', type: 'image', main: !i, src: img.src, ...coverBox(img, x, y, w, h), cornerRadius: 12 });
      deco('text', { x, y: y + h + 14, width: w, text: lab, fontSize: 22, fontStyle: 'bold', fill: t.dim });
      title(i === 2 ? 'Shop now' : 'Your headline', { x: x + 24, y: y + 24, width: w - 48, fontSize: i === 2 ? 36 : 54 });
    });
  }
  return out;
}

// pure: a video proof keeps playing UNDER the edit — split the layers around the main picture: what paints before it (frame decor) and
// what paints over it (text, badges, shapes). → { under, main, over }
export function splitAroundMain(layers) {
  const i = layers.findIndex(l => l.main);
  return i < 0 ? { under: layers, main: null, over: [] } : { under: layers.slice(0, i), main: layers[i], over: layers.slice(i + 1) };
}

// pure: the best clip type this browser records (Chrome 126+ writes MP4 itself; others WebM). → { type, ext } or null
export function clipType(supports) {
  const want = [['video/mp4;codecs=avc3', 'mp4'], ['video/mp4;codecs=avc1', 'mp4'], ['video/mp4', 'mp4'], ['video/webm;codecs=vp9', 'webm'], ['video/webm', 'webm']];
  const hit = want.find(([t]) => supports(t)); return hit ? { type: hit[0], ext: hit[1] } : null;
}
export const CLIP_MAX_SEC = 60;

// pure: undo / redo over whole layer lists (each step a full copy; 60 steps kept)
export const KEEP_STEPS = 60;
export const history = now => ({ past: [], now, future: [] });
export function push(h, next) { return next === h.now ? h : { past: [...h.past, h.now].slice(-KEEP_STEPS), now: next, future: [] }; }
export function undo(h) { return h.past.length ? { past: h.past.slice(0, -1), now: h.past[h.past.length - 1], future: [h.now, ...h.future] } : h; }
export function redo(h) { return h.future.length ? { past: [...h.past, h.now], now: h.future[0], future: h.future.slice(1) } : h; }

// pure: move a layer one step up / down / to the front / to the back (decor stays under everything)
export function reorder(layers, id, how) {
  const i = layers.findIndex(l => l.id === id); if (i < 0) return layers;
  const firstFree = layers.findIndex(l => !l.deco); const lo = firstFree < 0 ? 0 : firstFree; const hi = layers.length - 1;
  const j = how === 'up' ? Math.min(hi, i + 1) : how === 'down' ? Math.max(lo, i - 1) : how === 'front' ? hi : lo;
  if (j === i) return layers;
  const out = layers.slice(); const [l] = out.splice(i, 1); out.splice(j, 0, l); return out;
}

// pure: a frame change keeps everything the user added; the frame's own decor, title and main picture are rebuilt
export function reframe(layers, key, img, t) {
  const mine = layers.filter(l => l.user);
  return [...frameLayers(key, img, t), ...mine];
}

import { GIFEncoder, quantize, applyPalette } from 'gifenc';

// The encoder the share cards use: noisy royal-green frames at card size land well above 2 MB.
test('share GIF encoding clears the 2 MB floor', () => {
  const W = 720, H = 405, enc = GIFEncoder();
  for (let f = 0; f < 72; f++) {
    const d = new Uint8ClampedArray(W * H * 4);
    for (let p = 0; p < d.length; p += 4) { const n = Math.random() * 40; d[p] = 2 + n; d[p + 1] = 60 + n + (p / d.length) * 150; d[p + 2] = 40 + n; d[p + 3] = 255; }
    const pal = quantize(d, 256); enc.writeFrame(applyPalette(d, pal), W, H, { palette: pal, delay: 45 });
  }
  enc.finish();
  expect(enc.bytes().length).toBeGreaterThan(2 * 1024 * 1024);
});

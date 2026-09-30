import { GIFEncoder, quantize, applyPalette } from 'gifenc';

// Animated FEELESS share card as a GIF: royal-green light, sweeping flare, drifting sparks, a count-up
// headline and the FEE watermark. Rendered in the browser; nothing is uploaded.
const W = 720, H = 405, MIN_BYTES = 2 * 1024 * 1024;
const loadImg = src => new Promise(res => { if (!src) return res(null); const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
const ease = t => 1 - (1 - t) ** 3;

// Gains glow royal green; anything negative (drops, losses, flagged creators) gets its own crimson world.
const PALETTES = {
  up: { base: '#021a10', pools: ['18,192,122', '11,122,82'], fade: 'rgba(2,26,16,0)', flare: '184,255,228', spark: '157,255,217', kicker: '#9dffd9', big: '#12c07a', brand: '#12c07a', frame: 'rgba(18,192,122,.55)', panel: 'rgba(3,20,12,.55)', text: '#d9efe4', foot: '#8fbfa8' },
  down: { base: '#1a0208', pools: ['255,64,100', '140,20,50'], fade: 'rgba(26,2,8,0)', flare: '255,190,205', spark: '255,150,170', kicker: '#ffb3c3', big: '#ff6b8b', brand: '#ff6b8b', frame: 'rgba(255,90,122,.6)', panel: 'rgba(24,4,10,.6)', text: '#f3dbe1', foot: '#c9929f' },
};

function frame(g, card, logo, coin, t, seed) {
  const P = PALETTES[card.tone === 'down' ? 'down' : 'up'];
  // Base with two orbiting light pools.
  g.fillStyle = P.base; g.fillRect(0, 0, W, H);
  for (const [cx, cy, r, c] of [[W * (0.25 + 0.15 * Math.cos(t * 2 * Math.PI)), H * 0.3, 380, P.pools[0]], [W * (0.8 - 0.12 * Math.sin(t * 2 * Math.PI)), H * 0.85, 330, P.pools[1]]]) {
    const rg = g.createRadialGradient(cx, cy, 0, cx, cy, r); rg.addColorStop(0, `rgba(${c},.55)`); rg.addColorStop(1, P.fade); g.fillStyle = rg; g.fillRect(0, 0, W, H);
  }
  // Diagonal flare sweeping across once per loop.
  const fx = -W * 0.4 + t * W * 1.8; const fl = g.createLinearGradient(fx - 120, 0, fx + 120, H);
  fl.addColorStop(0, `rgba(${P.flare},0)`); fl.addColorStop(0.5, `rgba(${P.flare},.28)`); fl.addColorStop(1, `rgba(${P.flare},0)`); g.fillStyle = fl; g.fillRect(0, 0, W, H);
  // Sparks drifting upward.
  for (let i = 0; i < 46; i++) { const px = ((seed[i] * W) + t * 40 * (i % 3 + 1)) % W; const py = H - ((seed[i + 46] * H + t * H * (0.6 + seed[i] * 0.8)) % H); const a = 0.35 + 0.65 * Math.abs(Math.sin((t + seed[i]) * Math.PI * 2)); g.fillStyle = `rgba(${P.spark},${a})`; g.beginPath(); g.arc(px, py, 1 + seed[i + 20] * 2.2, 0, Math.PI * 2); g.fill(); }
  // Film grain: keeps gradients smooth in 256 colours (and makes the loop feel alive).
  const img = g.getImageData(0, 0, W, H); const d = img.data;
  for (let p = 0; p < d.length; p += 4) { const n = (Math.random() - 0.5) * 22; d[p] += n; d[p + 1] += n; d[p + 2] += n; }
  g.putImageData(img, 0, 0);
  // Watermark: big faint FEE (or FeeCat) mark, pulsing.
  if (logo) { g.globalAlpha = (card.mascot ? 0.16 : 0.1) + 0.05 * Math.sin(t * Math.PI * 2); g.drawImage(logo, W - 330, -20, 380, 380); g.globalAlpha = 1; }
  // Card content.
  g.fillStyle = P.panel; g.strokeStyle = P.frame; g.lineWidth = 2; g.beginPath(); g.roundRect(28, 28, W - 56, H - 56, 22); g.fill(); g.stroke();
  if (coin) { g.save(); g.beginPath(); g.arc(84, 92, 34, 0, Math.PI * 2); g.clip(); g.drawImage(coin, 50, 58, 68, 68); g.restore(); }
  g.fillStyle = P.kicker; g.font = '700 15px "Space Grotesk", sans-serif'; g.fillText(card.kicker || 'FEELESS', coin ? 134 : 56, 78);
  g.fillStyle = '#ffffff'; g.font = '800 34px "Space Grotesk", sans-serif'; g.fillText(card.title, coin ? 134 : 56, 114);
  const k = ease(Math.min(1, t * 2.2)); const big = card.bigValue != null ? `${card.bigPrefix || ''}${(card.bigValue * k).toFixed(card.bigDigits ?? 1)}${card.bigSuffix || ''}` : card.big;
  g.font = '400 76px "Bungee", sans-serif'; g.fillStyle = P.big; g.shadowColor = g.fillStyle; g.shadowBlur = 18 + 10 * Math.sin(t * Math.PI * 4); g.fillText(big, 54, 228); g.shadowBlur = 0;
  g.font = '500 17px "Space Grotesk", sans-serif'; g.fillStyle = P.text; (card.lines || []).slice(0, 3).forEach((l, i) => g.fillText(l, 56, 274 + i * 26));
  // FeeCat effects: a paw-print trail walks across the card.
  if (card.mascot) {
    g.fillStyle = P.spark;
    for (let i = 0; i < 7; i++) {
      const ph = (t * 1.4 + i / 7) % 1; const px = -40 + ph * (W + 80); const py = H - 150 + (i % 2 ? -14 : 12) + 10 * Math.sin(ph * Math.PI * 2);
      g.globalAlpha = 0.18 * Math.sin(ph * Math.PI); g.beginPath(); g.ellipse(px, py, 9, 7, 0, 0, Math.PI * 2); g.fill();
      for (const [dx, dy] of [[-9, -11], [-3, -15], [4, -15], [10, -11]]) { g.beginPath(); g.arc(px + dx, py + dy, 3.2, 0, Math.PI * 2); g.fill(); }
    }
    g.globalAlpha = 1;
  }
  // Brand mark.
  g.font = '400 20px "Bungee", sans-serif'; g.fillStyle = P.brand; g.fillText(card.mascot ? 'FEECAT' : 'FEELESS', W - 190, H - 52);
  g.font = '500 12px "Space Grotesk", sans-serif'; g.fillStyle = P.foot; g.fillText(card.footer || 'feeless · non-custodial trading', W - 262, H - 34);
}

export async function renderShareGif(card) {
  await document.fonts?.ready;
  const [logo, coin] = await Promise.all([loadImg(card.mascot === 'feecat' ? '/assets/feecat-mark.png' : '/assets/feeless-logo.png'), loadImg(card.imageUrl)]);
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d', { willReadFrequently: true });
  const seed = Array.from({ length: 120 }, (_, i) => Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1);
  for (const frames of [72, 120, 180]) {
    const enc = GIFEncoder();
    for (let f = 0; f < frames; f++) {
      frame(g, card, logo, coin, f / frames, seed);
      const { data } = g.getImageData(0, 0, W, H); const pal = quantize(data, 256); enc.writeFrame(applyPalette(data, pal), W, H, { palette: pal, delay: 45 });
      if (f % 8 === 7) await new Promise(r => setTimeout(r));  // keep the page responsive
    }
    enc.finish(); const bytes = enc.bytes();
    if (bytes.length >= MIN_BYTES || frames === 180) return new Blob([bytes], { type: 'image/gif' });
  }
  return null;
}

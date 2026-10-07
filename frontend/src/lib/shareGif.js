import { GIFEncoder, quantize, applyPalette } from 'gifenc';

// Animated FEELESS share card as a GIF: royal-green light, sweeping flare, drifting sparks, a count-up
// headline and the FEE watermark. Rendered in the browser; nothing is uploaded.
const W = 720, H = 405, MIN_BYTES = 2 * 1024 * 1024;
const loadImg = src => new Promise(res => { if (!src) return res(null); const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
const ease = t => 1 - (1 - t) ** 3;

// Gains glow royal green; anything negative (drops, losses, flagged creators) gets its own crimson world.
const PALETTES = {
  up: { base: '#021a10', pools: ['18,192,122', '11,122,82'], fade: 'rgba(2,26,16,0)', flare: '184,255,228', spark: '157,255,217', kicker: '#9dffd9', big: '#15d16a', brand: '#15d16a', frame: 'rgba(18,192,122,.55)', panel: 'rgba(3,20,12,.55)', text: '#d9efe4', foot: '#8fbfa8' },
  down: { base: '#1a0208', pools: ['255,64,100', '140,20,50'], fade: 'rgba(26,2,8,0)', flare: '255,190,205', spark: '255,150,170', kicker: '#ffb3c3', big: '#ff6b8b', brand: '#ff6b8b', frame: 'rgba(255,90,122,.6)', panel: 'rgba(24,4,10,.6)', text: '#f3dbe1', foot: '#c9929f' },
};

// 🎨 Designs (picked in the share preview). 'royal' = the original; each other design has its own colours + its own FX.
export const DESIGNS = [['royal', '🟩 Royal'], ['nebula', '🌌 Nebula'], ['gold', '🪙 Gold'], ['ice', '💎 Ice'], ['blaze', '🔥 Blaze'], ['synth', '🌆 Synthwave']];
const THEMES = {
  nebula: { base: '#0c0418', pools: ['150,80,255', '40,200,255'], fade: 'rgba(12,4,24,0)', flare: '220,190,255', spark: '210,180,255', kicker: '#d6b8ff', big: '#c58bff', brand: '#b98cff', frame: 'rgba(170,110,255,.6)', panel: 'rgba(16,6,32,.58)', text: '#eadfff', foot: '#a690c9' },
  gold: { base: '#140d02', pools: ['245,196,81', '168,114,10'], fade: 'rgba(20,13,2,0)', flare: '255,236,180', spark: '255,214,106', kicker: '#ffe39a', big: '#ffd56a', brand: '#f5c451', frame: 'rgba(245,196,81,.6)', panel: 'rgba(24,16,3,.6)', text: '#f7ecd2', foot: '#c9b07a' },
  ice: { base: '#020d18', pools: ['106,215,255', '190,240,255'], fade: 'rgba(2,13,24,0)', flare: '230,250,255', spark: '220,246,255', kicker: '#bfefff', big: '#9fe3ff', brand: '#9fe3ff', frame: 'rgba(159,227,255,.6)', panel: 'rgba(3,16,28,.6)', text: '#e3f6ff', foot: '#8fb8c9' },
  blaze: { base: '#180502', pools: ['255,122,47', '255,61,90'], fade: 'rgba(24,5,2,0)', flare: '255,214,170', spark: '255,177,92', kicker: '#ffc79a', big: '#ff9a4d', brand: '#ff7a2f', frame: 'rgba(255,122,47,.6)', panel: 'rgba(28,8,4,.6)', text: '#ffe6d6', foot: '#c99a80' },
  synth: { base: '#0a0216', pools: ['255,60,190', '60,220,255'], fade: 'rgba(10,2,22,0)', flare: '255,200,240', spark: '120,240,255', kicker: '#ff9be0', big: '#ff5fd2', brand: '#3cdcff', frame: 'rgba(255,95,210,.6)', panel: 'rgba(14,4,30,.58)', text: '#f6e3ff', foot: '#a98fc4' },
};

// 🌌 DEPTH for every design (royal too), under its signature effect: god-rays turning behind the mark, a perspective floor that
// scrolls toward the viewer, twinkling stars — then one extra per design (data rain · sunburst · embers · snow · a shooting star).
// All loop-safe in t (whole turns per loop).
function depthFx(g, theme, P, t, seed) {
  const T = Math.PI * 2; const cx = W * 0.8, cy = H * 0.3;
  g.save(); g.translate(cx, cy); g.rotate(t * T / 12);
  for (let i = 0; i < 12; i++) { g.rotate(T / 12); const gr = g.createLinearGradient(0, 0, 520, 0); gr.addColorStop(0, `rgba(${P.flare},${theme === 'gold' ? 0.2 : 0.11})`); gr.addColorStop(1, `rgba(${P.flare},0)`);
    g.fillStyle = gr; g.beginPath(); g.moveTo(0, 0); g.lineTo(520, -30); g.lineTo(520, 30); g.closePath(); g.fill(); }
  g.restore();
  if (theme !== 'synth') { const hz = H * 0.7; g.strokeStyle = `rgba(${P.pools[0]},.2)`; g.lineWidth = 1;   // floor (synth draws its own)
    for (let i = 0; i < 7; i++) { const y = hz + ((i + t) % 7) ** 2 * 3.1; g.globalAlpha = Math.min(1, (y - hz) / 60); g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    g.globalAlpha = 1; for (let i = -7; i <= 7; i++) { g.beginPath(); g.moveTo(W / 2 + i * 26, hz); g.lineTo(W / 2 + i * 150, H); g.stroke(); } }
  for (let i = 0; i < 26; i++) { const a = 0.15 + 0.6 * Math.abs(Math.sin((t * 2 + seed[i + 60]) * T)); g.fillStyle = `rgba(${P.flare},${a})`; g.fillRect(seed[i + 30] * W, seed[i + 4] * H * 0.66, 1.6, 1.6); }
  if (!THEMES[theme]) {            // royal: data rain
    for (let i = 0; i < 14; i++) { const x = seed[i] * W; const y = ((seed[i + 14] + t * (1 + (i % 3))) % 1) * (H + 80) - 80; const gr = g.createLinearGradient(x, y, x, y + 70); gr.addColorStop(0, `rgba(${P.spark},0)`); gr.addColorStop(1, `rgba(${P.spark},.5)`); g.fillStyle = gr; g.fillRect(x, y, 2, 70); }
  } else if (theme === 'blaze') {  // embers with tails
    for (let i = 0; i < 22; i++) { const x = (seed[i] * W + 30 * Math.sin((t + seed[i]) * T)) % W; const y = H - ((seed[i + 22] + t * (1 + (i % 2))) % 1) * H; g.fillStyle = `rgba(255,${150 + (i % 5) * 20},60,${0.25 + 0.6 * (y / H)})`; g.fillRect(x, y, 2.4, 7); }
  } else if (theme === 'ice') {    // snow
    for (let i = 0; i < 34; i++) { const x = (seed[i] * W + 22 * Math.sin((t * 2 + seed[i + 34]) * T) + W) % W; const y = ((seed[i + 34] + t * (1 + (i % 2))) % 1) * H; g.fillStyle = `rgba(${P.flare},.7)`; g.beginPath(); g.arc(x, y, 1 + (i % 3) * 0.7, 0, T); g.fill(); }
  } else if (theme === 'nebula') { // one shooting star per loop
    const k = (t * 1.6) % 1; const x = W * (0.2 + k * 0.7), y = H * (0.12 + k * 0.3); const gr = g.createLinearGradient(x - 90, y - 38, x, y); gr.addColorStop(0, `rgba(${P.flare},0)`); gr.addColorStop(1, `rgba(${P.flare},${0.9 * Math.sin(k * Math.PI)})`);
    g.strokeStyle = gr; g.lineWidth = 2.2; g.beginPath(); g.moveTo(x - 90, y - 38); g.lineTo(x, y); g.stroke();
  }
}

// One signature effect per design (drawn under the panel; cheap canvas strokes, loop-safe in t).
function designFx(g, theme, P, t, seed) {
  const T = Math.PI * 2;
  if (theme === 'nebula') {          // orbiting rings
    g.lineWidth = 2;
    for (let i = 0; i < 3; i++) { g.strokeStyle = `rgba(${P.pools[i % 2]},${0.35 - i * 0.08})`; g.beginPath(); g.ellipse(W * 0.72, H * 0.5, 170 + i * 46, 60 + i * 20, t * T + i, 0, T); g.stroke(); }
  } else if (theme === 'gold') {     // coin rain
    for (let i = 0; i < 18; i++) { const x = (seed[i] * W + i * 37) % W; const y = ((seed[i + 18] * H + t * H * (1 + seed[i] * 0.6)) % (H + 40)) - 20; const w = 9 * Math.abs(Math.cos((t * 3 + seed[i]) * T));
      g.fillStyle = `rgba(${P.spark},.85)`; g.beginPath(); g.ellipse(x, y, Math.max(1.5, w), 9, 0, 0, T); g.fill(); }
  } else if (theme === 'ice') {      // prism shards
    for (let i = 0; i < 12; i++) { const cx = (seed[i] * W), cy = (seed[i + 12] * H); const a = 0.15 + 0.25 * Math.abs(Math.sin((t + seed[i]) * T)); const r = 14 + seed[i + 24] * 26;
      g.fillStyle = `rgba(${P.flare},${a})`; g.beginPath(); g.moveTo(cx, cy - r); g.lineTo(cx + r * 0.5, cy); g.lineTo(cx, cy + r); g.lineTo(cx - r * 0.5, cy); g.closePath(); g.fill(); }
  } else if (theme === 'blaze') {    // flame tongues along the bottom
    for (let i = 0; i < 16; i++) { const x = i * (W / 15); const h = 50 + 40 * Math.abs(Math.sin((t * 2 + seed[i]) * T)); const gr = g.createLinearGradient(x, H, x, H - h);
      gr.addColorStop(0, `rgba(${P.pools[1]},.7)`); gr.addColorStop(1, `rgba(${P.pools[0]},0)`); g.fillStyle = gr; g.beginPath(); g.moveTo(x - 26, H); g.quadraticCurveTo(x, H - h * 1.4, x + 26, H); g.fill(); }
  } else if (theme === 'synth') {    // retro grid floor + sun
    const hz = H * 0.62; const sun = g.createLinearGradient(0, hz - 120, 0, hz); sun.addColorStop(0, 'rgba(255,200,90,.55)'); sun.addColorStop(1, 'rgba(255,60,190,.35)');
    g.fillStyle = sun; g.beginPath(); g.arc(W * 0.74, hz, 110, Math.PI, 0); g.fill();
    g.strokeStyle = `rgba(${P.pools[1]},.45)`; g.lineWidth = 1.5;
    for (let i = 0; i < 9; i++) { const y = hz + ((i + t) % 9) ** 2 * 2.6; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    for (let i = -8; i <= 8; i++) { g.beginPath(); g.moveTo(W / 2 + i * 22, hz); g.lineTo(W / 2 + i * 120, H); g.stroke(); }
  }
}

// The Fuse card as it looks in the app: portrait, tier gradient + edge, FUSE mark, tier name, coin logos, one line per coin.
function drawFuseCard(g, fz, imgs, t) {
  const T = Math.PI * 2; const cw = 196, ch = 300; const cx = 56 + cw / 2, cy = 52 + ch / 2;
  const a1 = fz.accent || '#15d16a', a2 = fz.accent2 || '#0b7a3e';
  g.save(); g.translate(cx, cy + 4 * Math.sin(t * T)); g.rotate(0.035 * Math.sin(t * T)); g.translate(-cw / 2, -ch / 2);
  g.shadowColor = a1; g.shadowBlur = 26 + 10 * Math.sin(t * T * 2);
  const bg = g.createLinearGradient(0, 0, cw, ch); bg.addColorStop(0, '#0b0f0c'); bg.addColorStop(1, '#050706');
  g.fillStyle = bg; g.beginPath(); g.roundRect(0, 0, cw, ch, 16); g.fill(); g.shadowBlur = 0;
  const ed = g.createLinearGradient(0, 0, cw, ch); ed.addColorStop(0, a1); ed.addColorStop(1, a2); g.strokeStyle = ed; g.lineWidth = 3; g.stroke();
  g.save(); g.beginPath(); g.roundRect(0, 0, cw, ch, 16); g.clip();           // sheen sweeping across the face
  const sx = -cw + ((t * 2) % 1) * cw * 3; const sh = g.createLinearGradient(sx, 0, sx + 90, ch); sh.addColorStop(0, 'rgba(255,255,255,0)'); sh.addColorStop(0.5, 'rgba(255,255,255,.13)'); sh.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = sh; g.fillRect(0, 0, cw, ch); g.restore();
  g.fillStyle = a1; g.font = '400 17px "Bungee", sans-serif'; g.fillText('FUSE', 14, 28);
  g.fillStyle = 'rgba(255,255,255,.7)'; g.font = '700 10px "Space Grotesk", sans-serif'; g.fillText(String(fz.name || '').toUpperCase(), 14, 44);
  const coins = (fz.coins || []).slice(0, 6); const n = coins.length || 1; const r = n <= 4 ? 20 : 15; const gap = Math.min(r * 2 + 8, (cw - 28 - r * 2) / Math.max(1, n - 1));
  coins.forEach((c, i) => { const x = 14 + r + i * gap, y = 82; const im = imgs[i];
    g.save(); g.beginPath(); g.arc(x, y, r, 0, T); g.closePath();
    if (im) { g.clip(); g.drawImage(im, x - r, y - r, r * 2, r * 2); } else { g.fillStyle = 'rgba(255,255,255,.1)'; g.fill(); g.fillStyle = '#fff'; g.font = `700 ${r}px "Space Grotesk", sans-serif`; g.textAlign = 'center'; g.fillText(String(c.symbol || '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 1).toUpperCase(), x, y + r * 0.36); g.textAlign = 'left'; }
    g.restore(); g.strokeStyle = c.locked ? '#f5c451' : a1; g.lineWidth = 1.5; g.beginPath(); g.arc(x, y, r, 0, T); g.stroke(); });
  coins.forEach((c, i) => { const y = 134 + i * 26; const up = (c.pct || 0) >= 0;
    g.fillStyle = '#fff'; g.font = '700 13px "Space Grotesk", sans-serif'; g.fillText(`${c.locked ? '🔒 ' : ''}$${String(c.symbol || '').slice(0, 9)}`, 14, y);
    g.fillStyle = up ? '#45e486' : '#ff8fa3'; g.font = '700 13px "JetBrains Mono", monospace'; g.textAlign = 'right'; g.fillText(`${up ? '+' : ''}${Number(c.pct || 0).toFixed(1)}%`, cw - 14, y); g.textAlign = 'left';
    const mx = Math.max(5, ...coins.map(k => Math.abs(k.pct || 0))); g.fillStyle = 'rgba(255,255,255,.08)'; g.fillRect(14, y + 6, cw - 28, 3);   /* how big each coin's move is, at a glance */
    g.fillStyle = up ? '#45e486' : '#ff8fa3'; g.fillRect(14, y + 6, (cw - 28) * Math.min(1, Math.abs(c.pct || 0) / mx) * ease(Math.min(1, t * 3 + 0.35)), 3); });
  if (fz.foot) { g.fillStyle = 'rgba(255,255,255,.06)'; g.beginPath(); g.roundRect(10, ch - 34, cw - 20, 24, 8); g.fill(); g.fillStyle = 'rgba(255,255,255,.85)'; g.font = '700 11px "JetBrains Mono", monospace'; g.textAlign = 'center'; g.fillText(String(fz.foot).slice(0, 26), cw / 2, ch - 18); g.textAlign = 'left'; }
  g.restore();
}

function frame(g, card, logo, coin, t, seed, s = 1) {
  const P = THEMES[card.theme] || PALETTES[card.tone === 'down' ? 'down' : 'up'];
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
  depthFx(g, card.theme, P, t, seed);
  if (THEMES[card.theme]) designFx(g, card.theme, P, t, seed);
  // Film grain: keeps gradients smooth in 256 colours (and makes the loop feel alive).
  const img = g.getImageData(0, 0, W * s, H * s); const d = img.data;
  for (let p = 0; p < d.length; p += 4) { const n = (Math.random() - 0.5) * (s > 1 ? 9 : 22); d[p] += n; d[p + 1] += n; d[p + 2] += n; }
  g.putImageData(img, 0, 0);
  // Watermark: big faint FEE (or FeeCat) mark, pulsing.
  if (logo) { g.globalAlpha = (card.mascot ? 0.16 : 0.1) + 0.05 * Math.sin(t * Math.PI * 2); g.drawImage(logo, W - 330, -20, 380, 380); g.globalAlpha = 1; }
  // 🃏 Fuse card share: the card itself (tier colours, its coins + logos + live %), rocking gently, on the left.
  const fz = card.fuse; const ox = fz ? 236 : 0;
  g.fillStyle = P.panel; g.strokeStyle = P.frame; g.lineWidth = 2; g.beginPath(); g.roundRect(28, 28, W - 56, H - 56, 22); g.fill(); g.stroke();
  if (fz) drawFuseCard(g, fz, card.coinImgs || [], t);
  if (coin && !fz) { g.save(); g.beginPath(); g.arc(84, 92, 34, 0, Math.PI * 2); g.clip(); g.drawImage(coin, 50, 58, 68, 68); g.restore(); }
  g.fillStyle = P.kicker; g.font = '700 15px "Space Grotesk", sans-serif'; g.fillText(card.kicker || 'FEELESS', (coin && !fz ? 134 : 56) + ox, 78);
  g.fillStyle = '#ffffff'; g.font = '800 34px "Space Grotesk", sans-serif'; g.fillText(card.title, (coin && !fz ? 134 : 56) + ox, 114);
  const k = ease(Math.min(1, t * 2.2)); const big = card.bigValue != null ? `${card.bigPrefix || ''}${(card.bigValue * k).toFixed(card.bigDigits ?? 1)}${card.bigSuffix || ''}` : card.big;
  g.font = '400 76px "Bungee", sans-serif'; g.fillStyle = P.big; g.shadowColor = g.fillStyle; g.shadowBlur = 18 + 10 * Math.sin(t * Math.PI * 4); g.font = fz ? '400 60px "Bungee", sans-serif' : g.font; g.fillText(big, 54 + ox, 228); g.shadowBlur = 0;
  if (card.bigSub) { const bw = g.measureText(big).width; g.font = '700 20px "JetBrains Mono", monospace'; g.fillStyle = P.text; g.fillText(card.bigSub, 54 + ox + bw + 12, 226); }
  const vit = fz ? (fz.vitals || []).slice(0, 4) : [];
  g.font = `500 ${vit.length ? 15 : 17}px "Space Grotesk", sans-serif`; g.fillStyle = P.text; (card.lines || []).slice(0, 3).forEach((l, i) => g.fillText(l, 56 + ox, (vit.length ? 258 : 274) + i * (vit.length ? 21 : 26)));
  // 🧮 the card's vitals in four tiles (fuse shares): put in · in the card now · profit pulled · swaps
  vit.forEach((v, i) => { const x = 56 + ox + i * 93, y = 292; g.fillStyle = 'rgba(255,255,255,0.08)'; g.beginPath(); g.roundRect(x, y, 87, 40, 9); g.fill();
    g.fillStyle = 'rgba(255,255,255,0.55)'; g.font = '600 9px "Space Grotesk", sans-serif'; g.fillText(String(v.label).toUpperCase().slice(0, 14), x + 8, y + 14);
    g.fillStyle = v.tone === 'bad' ? '#ff8fa3' : v.tone === 'ok' ? '#45e486' : '#ffffff'; g.font = '700 15px "JetBrains Mono", monospace'; g.fillText(String(v.value).slice(0, 9), x + 8, y + 32); });
  // Stats panel (case files): up to 6 labelled pills, 2 columns, coloured by verdict (ok = mint, bad = red).
  (card.stats || []).slice(0, 6).forEach((s, i) => {
    const x = 392 + (i % 2) * 150, y = 136 + Math.floor(i / 2) * 50;
    g.fillStyle = 'rgba(255,255,255,0.07)'; g.beginPath(); g.roundRect(x, y, 142, 42, 10); g.fill();
    g.fillStyle = 'rgba(255,255,255,0.55)'; g.font = '600 10px "Space Grotesk", sans-serif'; g.fillText(String(s.label).toUpperCase(), x + 10, y + 15);
    g.fillStyle = s.tone === 'bad' ? '#ff8fa3' : s.tone === 'ok' ? '#15d16a' : s.tone === 'warn' ? '#f5c451' : '#ffffff';
    g.font = '700 16px "Space Grotesk", sans-serif'; g.fillText(String(s.value).slice(0, 16), x + 10, y + 34);
  });
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
  const by = vit.length ? H - 42 : H - 52;   /* fuse shares: the brand sits on one line under the vitals */
  g.font = '400 20px "Bungee", sans-serif'; g.fillStyle = P.brand; g.fillText(card.mascot ? 'FEECAT' : 'FEELESS', W - 190, by);
  g.font = '500 12px "Space Grotesk", sans-serif'; g.fillStyle = P.foot; if (vit.length) g.fillText(card.footer || 'feeless', 56 + ox, by - 2); else g.fillText(card.footer || 'feeless · non-custodial trading', W - 262, H - 34);
}

// 🖼 The STILL share card (the default): the same card at 2× (1440×810 PNG), drawn once — instant, crisp, small. On top of the
// animated layout it gets a print finish: a dot lattice inside the panel, corner brackets, and a date stamp.
function finish(g, P) {
  g.save();
  g.fillStyle = `rgba(${P.spark},.07)`;
  for (let y = 44; y < H - 40; y += 14) for (let x = 44; x < W - 40; x += 14) g.fillRect(x, y, 1.2, 1.2);
  g.strokeStyle = P.brand; g.lineWidth = 2.5; g.lineCap = 'round';
  for (const [x, y, dx, dy] of [[40, 40, 1, 1], [W - 40, 40, -1, 1], [40, H - 40, 1, -1], [W - 40, H - 40, -1, -1]]) { g.beginPath(); g.moveTo(x + 22 * dx, y); g.lineTo(x, y); g.lineTo(x, y + 22 * dy); g.stroke(); }
  const d = new Date(); const stamp = `${d.toISOString().slice(0, 10)} · ${d.toISOString().slice(11, 16)} UTC`;
  g.font = '600 11px "JetBrains Mono", monospace'; g.fillStyle = P.foot; g.textAlign = 'right'; g.fillText(stamp, W - 56, 62); g.textAlign = 'left';
  g.restore();
}

export async function renderShareCard(card) {
  await document.fonts?.ready;
  const [logo, coin] = await Promise.all([loadImg(card.mascot === 'feecat' ? '/assets/feecat-mark.png' : '/assets/feeless-logo.png'), loadImg(card.imageUrl)]);
  if (card.fuse) card = { ...card, coinImgs: await Promise.all((card.fuse.coins || []).slice(0, 6).map(x => loadImg(x.logo))) };
  const S = 2; const c = document.createElement('canvas'); c.width = W * S; c.height = H * S; const g = c.getContext('2d', { willReadFrequently: true });
  g.scale(S, S);
  const seed = Array.from({ length: 120 }, (_, i) => Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1);
  frame(g, card, logo, coin, 0.5, seed, S);          // t = 0.5: the count-up has landed, lights mid-orbit
  finish(g, THEMES[card.theme] || PALETTES[card.tone === 'down' ? 'down' : 'up']);
  return new Promise(res => c.toBlob(b => res(b), 'image/png'));
}

export async function renderShareGif(card) {
  await document.fonts?.ready;
  const [logo, coin] = await Promise.all([loadImg(card.mascot === 'feecat' ? '/assets/feecat-mark.png' : '/assets/feeless-logo.png'), loadImg(card.imageUrl)]);
  if (card.fuse) card = { ...card, coinImgs: await Promise.all((card.fuse.coins || []).slice(0, 6).map(x => loadImg(x.logo))) };
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

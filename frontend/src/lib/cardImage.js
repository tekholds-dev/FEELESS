import { apiUrl } from './api';

// FEELESS card → 1000×1400 PNG for NFT images: same colours, crest, glyph/art, title and rarity as the 3D card.
const RANK = { common: 1, rare: 2, epic: 3, legendary: 4, mythic: 5 };
const loadImg = src => new Promise(res => { const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
const poly = (ctx, n, r, cx, cy, rot = -Math.PI / 2) => { ctx.beginPath(); for (let i = 0; i < n; i++) { const a = rot + (Math.PI * 2 * i) / n; ctx[i ? 'lineTo' : 'moveTo'](cx + r * Math.cos(a), cy + r * Math.sin(a)); } ctx.closePath(); };

export async function cardToPng(card) {
  const W = 1000, H = 1400, cx = W / 2, cy = 560;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d');
  const a = card.accent || '#19f58f', b = card.accent2 || '#f5c451', r = RANK[card.rarity] || 2;
  // base + design wash
  x.fillStyle = '#030a06'; x.fillRect(0, 0, W, H);
  let g = x.createRadialGradient(cx, 0, 50, cx, 0, 1100); g.addColorStop(0, `${a}66`); g.addColorStop(1, 'transparent'); x.fillStyle = g; x.fillRect(0, 0, W, H);
  g = x.createRadialGradient(cx, H, 50, cx, H, 900); g.addColorStop(0, `${b}55`); g.addColorStop(1, 'transparent'); x.fillStyle = g; x.fillRect(0, 0, W, H);
  if (card.design === 'holo') { const h = x.createLinearGradient(0, 0, W, H); ['#6ad7ff33', `${a}33`, '#ff5ad133', `${b}33`].forEach((s, i) => h.addColorStop(i / 3, s)); x.fillStyle = h; x.fillRect(0, 0, W, H); }
  if (card.design === 'glitch') { x.fillStyle = 'rgba(255,255,255,.05)'; for (let y = 0; y < H; y += 6) x.fillRect(0, y, W, 2); }
  if (card.design === 'circuit') { x.strokeStyle = `${a}55`; x.lineWidth = 4; [[60, 200, 400, 300], [940, 450, 620, 520], [80, 1000, 420, 900], [920, 1250, 600, 1180]].forEach(([x1, y1, x2, y2]) => { x.beginPath(); x.moveTo(x1, y1); x.lineTo(x2, y1); x.lineTo(x2, y2); x.stroke(); x.fillStyle = a; x.beginPath(); x.arc(x2, y2, 10, 0, 7); x.fill(); }); }
  if (card.design === 'ember') { x.strokeStyle = `${b}33`; x.lineWidth = 2; for (let yy = 0; yy < H; yy += 104) for (let xx = (yy / 104) % 2 ? 30 : 0; xx < W; xx += 60) { poly(x, 6, 30, xx, yy, 0); x.stroke(); } }
  if (card.design === 'obsidian') { x.strokeStyle = `${b}44`; x.lineWidth = 2; [[0, 0, 550, 0, 200, 450], [550, 0, 1000, 0, 800, 600], [200, 450, 800, 600, 450, 1000], [0, 850, 450, 1000, 0, 1400], [450, 1000, 1000, 950, 1000, 1400]].forEach(t => { x.beginPath(); x.moveTo(t[0], t[1]); x.lineTo(t[2], t[3]); x.lineTo(t[4], t[5]); x.closePath(); x.stroke(); }); }
  // frame
  x.lineWidth = r >= 4 ? 14 : 8; x.strokeStyle = r >= 4 ? b : a; x.strokeRect(24, 24, W - 48, H - 48);
  // crest
  const ring = x.createLinearGradient(cx - 250, cy - 250, cx + 250, cy + 250); ring.addColorStop(0, a); ring.addColorStop(0.5, '#ffffff'); ring.addColorStop(1, b);
  x.lineWidth = 14; x.strokeStyle = ring; x.fillStyle = 'rgba(0,0,0,.5)';
  if (r === 3) poly(x, 8, 260, cx, cy, -Math.PI / 8); else if (r === 2) poly(x, 6, 260, cx, cy); else { x.beginPath(); x.arc(cx, cy, 250, 0, 7); }
  x.fill(); x.stroke();
  if (r >= 4) { x.lineWidth = 5; poly(x, 8, 330, cx, cy, -Math.PI / 2); x.stroke(); poly(x, 8, 330, cx, cy, -Math.PI / 2 + Math.PI / 8); x.stroke(); }
  x.save(); x.beginPath(); x.arc(cx, cy, 190, 0, 7); x.fillStyle = '#020805'; x.fill(); x.clip();
  const art = card.art ? await loadImg(card.art.startsWith('/') ? apiUrl(card.art) : card.art) : null;
  if (art) x.drawImage(art, cx - 190, cy - 190, 380, 380);
  else { x.font = '200px serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(card.glyph || '✦', cx, cy + 10); }
  x.restore();
  // text
  x.textAlign = 'center'; x.fillStyle = '#eafff3'; x.font = '700 76px Inter, Arial, sans-serif'; x.fillText(card.title || '', cx, 1000, W - 120);
  x.fillStyle = 'rgba(234,255,243,.65)'; x.font = '500 34px "JetBrains Mono", monospace'; x.fillText(String(card.subtitle || '').toUpperCase(), cx, 1060, W - 120);
  x.fillStyle = a; x.font = '600 30px "JetBrains Mono", monospace'; x.fillText(`${String(card.rarity || 'rare').toUpperCase()} · FEELESS`, cx, 1300);
  for (let i = 0; i < 5; i++) { x.save(); x.translate(cx - 100 + i * 50, 120); x.rotate(Math.PI / 4); x.fillStyle = i < r ? a : 'transparent'; x.strokeStyle = a; x.lineWidth = 3; x.fillRect(-12, -12, 24, 24); x.strokeRect(-12, -12, 24, 24); x.restore(); }
  return c.toDataURL('image/webp', 0.92);
}

// Render + upload; resolves the upload path used as the NFT image.
export async function uploadCardImage(card) {
  const dataUrl = await cardToPng(card);
  const res = await fetch(apiUrl('/api/reputation/uploads'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataUrl }) });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.detail || 'Image upload failed');
  return d.url;
}

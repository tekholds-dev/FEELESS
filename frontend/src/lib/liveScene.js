// 🔴 THE LIVE SCENE (owner 2026-11-04): what a stream shows, drawn on one canvas with the browser's own Canvas and captureStream, so the owner can sort it before going live and no outside studio is needed.
// Monitors use the same frames visitors get: a private page is already blank here. Chat and mind lines are off until chosen.
export const SCENE_W = 1280; export const SCENE_H = 720;
export const DEFAULT_SCENE = { corner: 'right', size: 'm', monitors: true, minds: true, chat: false };
const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g; const PHONE = /(?<!\d)(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}/g;
export const safeLine = t => String(t || '').replace(EMAIL, '🔒').replace(PHONE, '🔒');
// Where everything goes. Pure, so a choice can be tested without a canvas.
export function layout(o) {
  const side = { s: 220, m: 300, l: 400 }[o.size] || 300; const m = 20; const panel = o.minds || o.chat;
  const agent = { x: o.corner === 'left' ? m : SCENE_W - side - m, y: SCENE_H - side - m, w: side, h: side };
  const panelW = panel ? 320 : 0; const panelX = o.corner === 'left' ? SCENE_W - panelW - m : m;
  const screensX = panel && o.corner !== 'left' ? panelX + panelW + m : m; const screensW = SCENE_W - (panel ? panelW + m : 0) - m * 2;
  const n = o.monitors ? 2 : 0; const w = n ? (screensW - m) / 2 : 0; const h = n ? Math.min(w * 0.72, SCENE_H - side - m * 3) : 0;
  const screens = n ? [0, 1].map(i => ({ x: screensX + i * (w + m), y: m, w, h })) : [];
  const half = (SCENE_H - m * 3) / (o.minds && o.chat ? 2 : 1);
  const minds = o.minds ? { x: panelX, y: m, w: panelW, h: half } : null;
  const chat = o.chat ? { x: panelX, y: o.minds ? m * 2 + half : m, w: panelW, h: half } : null;
  return { agent, screens, minds, chat };
}
export function mindLines(rows) { return (rows || []).filter(r => /MIND [AB]/.test(r.text || '')).slice(-8).map(r => safeLine(String(r.text).replace(/^🗣 /, ''))); }
export function chatLines(rows) { return (rows || []).filter(r => r.text && !/MIND [AB]/.test(r.text)).slice(-8).map(r => `${r.by === 'you' || r.by === 'user' ? 'Owner' : 'Agent'}: ${safeLine(r.text)}`); }
function rr(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function panel(g, b, title, lines, tone) {
  g.fillStyle = '#0a1030ee'; rr(g, b.x, b.y, b.w, b.h, 16); g.fill(); g.strokeStyle = tone; g.lineWidth = 1.5; g.stroke();
  g.fillStyle = tone; g.font = '800 13px "JetBrains Mono", monospace'; g.fillText(title, b.x + 14, b.y + 24);
  g.font = '500 14px Sora, sans-serif'; g.fillStyle = '#e8efff'; let y = b.y + 48; const max = b.y + b.h - 10;
  for (const l of [...lines].reverse()) { const words = l.split(' '); let row = ''; const rows = [];
    for (const w of words) { if (g.measureText(`${row}${w} `).width > b.w - 28) { rows.push(row); row = ''; } row += `${w} `; } rows.push(row);
    for (const t of rows.slice(0, 4)) { if (y > max) return; g.fillText(t, b.x + 14, y); y += 19; } y += 7; }
}
export function createScene({ face, catId, api = u => u }) {
  const canvas = document.createElement('canvas'); canvas.width = SCENE_W; canvas.height = SCENE_H; const g = canvas.getContext('2d');
  let o = { ...DEFAULT_SCENE }; let data = { rows: [], name: '' }; let on = false; let raf = 0; let timer = 0; let imgs = [null, null];
  const load = i => { const im = new Image(); im.onload = () => { imgs[i] = im; }; im.onerror = () => { imgs[i] = null; }; im.src = api(`/api/cats/${catId}/screen/${i}?t=${Date.now()}`); };
  const draw = () => {
    if (!g) return;
    g.fillStyle = '#050814'; g.fillRect(0, 0, SCENE_W, SCENE_H); g.strokeStyle = '#ffffff0c'; g.lineWidth = 1; for (let x = 0; x < SCENE_W; x += 64) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, SCENE_H); g.stroke(); } for (let y = 0; y < SCENE_H; y += 64) { g.beginPath(); g.moveTo(0, y); g.lineTo(SCENE_W, y); g.stroke(); }
    const L = layout(o);
    L.screens.forEach((b, i) => { g.save(); rr(g, b.x, b.y, b.w, b.h, 14); g.fillStyle = '#0a1030'; g.fill(); g.clip(); if (imgs[i]) g.drawImage(imgs[i], b.x, b.y, b.w, b.h); else { g.fillStyle = '#7f8fb8'; g.font = '600 16px Sora, sans-serif'; g.textAlign = 'center'; g.fillText(`Mind ${'AB'[i]} is resting`, b.x + b.w / 2, b.y + b.h / 2); g.textAlign = 'left'; } g.restore(); g.strokeStyle = i ? '#a06bff' : '#4fb8ff'; g.lineWidth = 2; rr(g, b.x, b.y, b.w, b.h, 14); g.stroke(); });
    if (L.minds) panel(g, L.minds, 'THE TWO MINDS', mindLines(data.rows), '#7fd0ff');
    if (L.chat) panel(g, L.chat, 'CHAT', chatLines(data.rows), '#c9a8ff');
    if (o.corner !== 'off' && face) { const b = L.agent; g.save(); rr(g, b.x, b.y, b.w, b.h, 20); g.clip(); try { g.drawImage(face, b.x, b.y, b.w, b.h); } catch { /* it is still loading */ } g.restore(); g.strokeStyle = '#b48cff'; g.lineWidth = 3; rr(g, b.x, b.y, b.w, b.h, 20); g.stroke(); g.fillStyle = '#050814dd'; const nm = String(data.name || ''); g.font = '800 15px Sora, sans-serif'; const tw = g.measureText(nm).width + 22; rr(g, b.x + 10, b.y + b.h - 38, tw, 28, 14); g.fill(); g.fillStyle = '#fff'; g.fillText(nm, b.x + 21, b.y + b.h - 19); }
  };
  const loop = () => { if (!on) return; draw(); raf = requestAnimationFrame(loop); };
  return { canvas, set: p => { o = { ...o, ...p }; }, get: () => o, feed: d => { data = { ...data, ...d }; },
    start: () => { if (on) return; on = true; load(0); load(1); timer = setInterval(() => { load(0); load(1); }, 4000); loop(); },
    stop: () => { on = false; cancelAnimationFrame(raf); clearInterval(timer); imgs = [null, null]; } };
}

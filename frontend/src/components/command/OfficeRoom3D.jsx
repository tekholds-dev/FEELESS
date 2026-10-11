import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { AG, ACT_FX, candleGeom } from './OfficeRoom';

// 🏢 THE CONTROL ROOM in real 3D (three.js, own lazy chunk). It draws ONLY the room model (`roomModel(o)` in OfficeRoom.jsx) — no model,
// nothing drawn; nothing in here invents a value.
//   · ten stations in TWO ROWS that snake (Tally → Devil left to right, Warden → Judge back), so the pipeline is one lit chevron path; each
//     station has its identity (agent colour on the rug light, desk strip, lamp, ring), a main monitor (its activity word + this pass's line)
//     and a side monitor (its real runtime per pass + its own record). The ring, rug and a one-shot ripple react to the desk's ACTIVITY word
//     (SCAN · PASS · WAIT · OBJECT · VETO · SIZED · SUBMITTED · CONFIRMED · PROTECT · TAKE · EXIT · LOGGING · JUDGE REVIEW) — a ripple fires
//     only when the word really changed between passes.
//   · the pass's CASE FILES float over the desk each one stands at (the current candidate lit by a beam); click one → its coin + that desk.
//   · THE REAL CARD on the hex platform between the rows: one pedestal per seat (height = % since entry, colour = who holds it, plate = the
//     desk's decision); an arc from the held coin to the switch-test challenger (green = the test passes).
//   · the wall: sign + your limits / restart readiness · the CURRENT CANDIDATE monitor (its candles + levels, the stage, the decision) ·
//     pipeline status · switch test / missed winners / review.
//   · hover = a tooltip of the real word behind the thing; click a bot / monitor / case / seat / the wall monitor; camera eases between
//     Main · The card · Top · Focus desk. Hidden tab / fx-lite / reduced motion = a still frame every 1–2s (never a blank room).
const XS = [-7.25, -3.8, -0.35, 3.1, 6.55];   // each station (desk + its bot to the right) is centred on the room
const Z1 = -1.4; const Z2 = 4.2; const WALL = -4.9; const PZ = 1.55;
export const DESK_AT = i => (i < 5 ? [XS[i], Z1] : [XS[9 - i], Z2]);   // the chain snakes: row 1 left → right, row 2 right → left
const LANE = i => { const [x, z] = DESK_AT(i); return new THREE.Vector3(x, 0.03, i < 5 ? z + 1.25 : z - 1.15); };
const mono = (px, w = 700) => `${w} ${px}px "JetBrains Mono", ui-monospace, monospace`;
const cut = (s, n) => { const t = String(s ?? ''); return t.length > n ? `${t.slice(0, n - 1)}…` : t; };
const mmss = s => { const v = Math.max(0, Math.round(s)); return `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`; };
const KIND_HEX = { agent: 0xa07bff, suggested: 0xf5c451, yours: 0xf5c451, engine: 0x6cc7ff, open: 0x2c4a3c };
const KIND_CSS = { agent: '#a07bff', suggested: '#f5c451', yours: '#f5c451', engine: '#6cc7ff', open: '#7d998b' };
const KIND_WORD = { agent: '🤖 AGENTS', suggested: '🤝 SUGGESTED', yours: '👤 YOURS', engine: '⚙ ENGINE', open: '▫ OPEN SEAT' };
const DEC_CSS = { HOLD: '#45e486', 'HOLD 5 MORE': '#45e486', PROTECT: '#f5c451', 'TAKE PROFIT': '#6cc7ff', EXIT: '#ff6b86', PULL: '#6cc7ff', SWAP: '#a07bff', FILLING: '#45e486', FULL: '#45e486', 'NO VALID ENTRY': '#7d998b', 'OFFICE WARMING UP': '#f5c451', 'CREATOR MANUAL': '#f5c451' };
const PULSE = { VETO: 1, EXIT: 0.9, OBJECT: 0.5, TAKE: 0.45, 'JUDGE REVIEW': 0.35, REVIEW: 0.35, SUBMITTED: 0.4, PROTECT: 0.3, ERROR: 1, STALE: 0.4 };
export const SEAT_GAP = 1.22;
export const seatX = (i, n) => (i - (n - 1) / 2) * (n <= 4 ? 1.6 : SEAT_GAP);   // up to four seats get room for their full plates; five or six close up
// a seat's pedestal height follows its % since entry (capped at ±30% so one runner never hides the rest), never a guess
export const seatH = pct => (pct == null ? 0.05 : 0.14 + Math.min(1, Math.abs(Number(pct)) / 30) * 0.95);
const hex = c => new THREE.Color(c || '#4d6a5c');

function tex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  t.userData.redraw = (...a) => { const g = c.getContext('2d'); g.clearRect(0, 0, w, h); draw(g, w, h, ...a); t.needsUpdate = true; }; return t;
}
function radial() {   // a soft round light pool (the station's rug light) — one texture, tinted per station
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); const r = g.createRadialGradient(64, 64, 4, 64, 64, 64);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.45, 'rgba(255,255,255,.35)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function wrap(g, text, x, y, maxCh, lh, maxLines) { const words = String(text || '').split(' '); let line = ''; let n = 0;
  for (const wd of words) { if ((`${line} ${wd}`).trim().length > maxCh && line) { g.fillText(line, x, y + n * lh); n += 1; line = wd; if (n >= maxLines) return; } else line = line ? `${line} ${wd}` : wd; }
  if (n < maxLines) g.fillText(line, x, y + n * lh); }
function drawDesk(g, w, h, s) {   // the main monitor: the desk's activity word + its line for this pass
  const c = s.color || '#7d998b'; g.fillStyle = '#030d09'; g.fillRect(0, 0, w, h); g.fillStyle = AG[s.key] || c; g.fillRect(0, 0, w, 8);
  g.fillStyle = AG[s.key] || '#cfe9db'; g.font = mono(22, 800); g.fillText(`${s.icon || ''} ${s.name.toUpperCase()}`, 14, 40);
  g.fillStyle = c; g.font = mono(44, 800); g.fillText(cut(s.act, 13), 14, 94);
  g.fillStyle = '#cfe9db'; g.font = mono(21, 600); wrap(g, s.line, 14, 132, 26, 26, 3);
}
function drawSide(g, w, h, s) {   // the side monitor: its real runtime per pass (sparkline) + its own record
  g.fillStyle = '#04100b'; g.fillRect(0, 0, w, h); const c = AG[s.key] || '#45e486'; g.strokeStyle = c; g.lineWidth = 3; g.strokeRect(2, 2, w - 4, h - 4);
  g.fillStyle = '#8fb9c9'; g.font = mono(16, 700); g.fillText('RUNTIME / PASS', 12, 26);
  const v = (s.series || []).filter(x => x != null); if (v.length > 1) { const hi = Math.max(...v); const lo = Math.min(...v); const sp = (hi - lo) || hi || 1;
    g.strokeStyle = c; g.lineWidth = 3; g.beginPath(); v.forEach((x, i) => { const X = 12 + (i / (v.length - 1)) * (w - 24); const Y = 92 - ((x - lo) / sp) * 50; if (i) g.lineTo(X, Y); else g.moveTo(X, Y); }); g.stroke(); }
  else { g.fillStyle = '#4d6a5c'; g.font = mono(16, 600); g.fillText('no passes timed yet', 12, 70); }
  g.fillStyle = '#e6fff0'; g.font = mono(20, 800); g.fillText(s.ms != null ? `${Number(s.ms) < 10 ? Number(s.ms).toFixed(2) : Math.round(s.ms)} ms` : '— ms', 12, 126);
  g.fillStyle = s.acc == null ? '#7d998b' : s.acc >= 55 ? '#45e486' : s.acc >= 45 ? '#f5c451' : '#ff6b86'; g.fillText(s.acc != null ? `${s.acc}% · n ${s.n}` : `n ${s.n || 0}`, 12, 150);
}
function drawSign(g, w, h, ready) {
  const warm = ready && !ready.live; const c = warm ? '#f5c451' : '#45e486';
  g.fillStyle = '#04140d'; g.fillRect(0, 0, w, h); g.strokeStyle = c; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  g.save(); g.transform(1, 0, -0.18, 1, 30, 0); g.fillStyle = c; g.shadowColor = c; g.shadowBlur = 22; g.font = mono(92, 800); g.fillText('FEELESS HQ', 30, 120); g.restore();
  g.shadowBlur = 0; g.fillStyle = warm ? '#ffe3a1' : '#b6f5d0'; g.font = mono(34, 700); g.fillText(warm ? cut(ready.state, 26) : ready ? 'AGENT OFFICE · LIVE' : 'AGENT OFFICE', 40, 190);
}
function drawLimits(g, w, h, lim, ready) {
  g.fillStyle = '#030d14'; g.fillRect(0, 0, w, h); g.strokeStyle = '#6cc7ff'; g.lineWidth = 5; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#8fb9c9'; g.font = mono(24, 800); g.fillText(lim?.manual ? 'YOUR LIMITS · ✋ MANUAL' : 'YOUR LIMITS', 22, 40);
  (lim?.rows || []).slice(0, 8).forEach(([l, mine, v], i) => { const col = i < 4 ? 0 : 1; const y = 80 + (i % 4) * 34; const x = 22 + col * 300;
    g.fillStyle = '#cfe9db'; g.font = mono(18, 600); g.fillText(cut(l, 14), x, y); g.fillStyle = mine ? '#f5c451' : '#6cc7ff'; g.font = mono(18, 800); g.fillText(mine ? `YOU ${cut(v, 6)}` : 'AGENTS', x + 168, y); });
  if (!lim) { g.fillStyle = '#7d998b'; g.font = mono(20, 600); g.fillText('not read yet', 22, 84); }
  g.fillStyle = '#8fb9c9'; g.font = mono(18, 800); g.fillText('READINESS', 22, h - 22);
  (ready?.steps || []).forEach(([wd, ok], i) => { const x = 150 + i * 112; g.fillStyle = ok ? '#45e486' : '#3a4f45'; g.beginPath(); g.arc(x, h - 28, 8, 0, 7); g.fill(); g.fillStyle = ok ? '#e6fff0' : '#7d998b'; g.font = mono(13, 700); g.fillText(cut(String(wd).replace('OFFICE ', '').replace('POSITIONS ', ''), 10), x + 12, h - 23); });
}
function drawStatus(g, w, h, st) {
  g.fillStyle = '#03101a'; g.fillRect(0, 0, w, h); g.strokeStyle = '#4fd8ff'; g.lineWidth = 5; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#8fb9c9'; g.font = mono(26, 800); g.fillText('PIPELINE STATUS', 22, 44);
  (st || []).forEach(([n, l, c], i) => { const y = 92 + i * 46; g.fillStyle = c; g.beginPath(); g.arc(34, y - 9, 9, 0, 7); g.fill(); g.fillStyle = '#e6fff0'; g.font = mono(32, 800); g.fillText(String(n), 56, y); g.fillStyle = '#8fb9c9'; g.font = mono(22, 600); g.fillText(l, 150, y - 2); });
}
function drawEdge(g, w, h, sw, missed) {
  g.fillStyle = '#0c0614'; g.fillRect(0, 0, w, h); g.strokeStyle = '#a07bff'; g.lineWidth = 5; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#c2a8ff'; g.font = mono(22, 800); g.fillText('SWITCH TEST', 20, 38);
  if (sw) { g.fillStyle = sw.ok ? '#45e486' : '#f5c451'; g.font = mono(20, 800); g.fillText(sw.ok ? 'SWITCH' : 'SEAT KEPT', w - 150, 38); g.fillStyle = '#ffffff'; g.font = mono(24, 800); g.fillText(`$${cut(sw.from || '—', 7)} → $${cut(sw.to || '—', 7)}`, 20, 72);
    g.fillStyle = '#8fb9c9'; g.font = mono(17, 600); wrap(g, sw.why, 20, 100, 40, 22, 2); }
  else { g.fillStyle = '#7d998b'; g.font = mono(18, 600); g.fillText('no held coin to test', 20, 74); }
  g.fillStyle = '#c2a8ff'; g.font = mono(20, 800); g.fillText(`MISSED WINNERS · ${missed?.n ?? 0}`, 20, h - 82); g.fillStyle = '#8fb9c9'; g.font = mono(16, 600); g.fillText(`${missed?.correct ?? 0} correct skips · review ${missed?.open ?? 0} waiting`, 20, h - 56);
  (missed?.reasons || []).slice(0, 2).forEach(([k, n], i) => { g.fillStyle = '#e6fff0'; g.font = mono(15, 700); g.fillText(`${n} × ${cut(k, 32)}`, 20, h - 32 + i * 20); });
}
// the wall monitor: every word is a field of the room model; the chart is `candleGeom` of the SAME rows the agents read
function drawWall(g, w, h, wall, now) {
  g.fillStyle = '#020b10'; g.fillRect(0, 0, w, h); g.strokeStyle = '#4fd8ff'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  if (!wall) { g.fillStyle = '#7d998b'; g.font = mono(34, 700); g.fillText('NO CANDIDATE AND NO OPEN POSITION THIS PASS', 40, h / 2); return; }
  g.fillStyle = '#8fb9c9'; g.font = mono(22, 800); g.fillText(wall.kind === 'position' ? 'OPEN POSITION' : 'CURRENT CANDIDATE', 30, 44);
  g.fillStyle = '#ffffff'; g.font = mono(66, 800); g.fillText(`$${cut(wall.symbol, 10)}`, 28, 112);
  g.fillStyle = '#c2a8ff'; g.font = mono(24, 700); g.fillText(`${cut(wall.stage, 12)} · ${cut(wall.decision, 18)}`, 30, 150);
  if (wall.move != null) { g.fillStyle = wall.move >= 0 ? '#45e486' : '#ff6b86'; g.font = mono(58, 800); g.fillText(`${wall.move >= 0 ? '+' : ''}${wall.move.toFixed(1)}%`, 28, 222); g.fillStyle = '#7d998b'; g.font = mono(18, 600); g.fillText(wall.kind === 'position' ? 'since entry' : 'in 5 min', 30, 248); }
  const rows = [['STRUCTURE', wall.structure], ['WARDEN', wall.warden], ['DEVIL', wall.devil], ['NEXT REVIEW', wall.reviewAt != null ? mmss(wall.reviewAt - now) : '—']];
  rows.forEach(([k, v], i) => { const y = 296 + i * 46; g.fillStyle = '#7d998b'; g.font = mono(16, 700); g.fillText(k, 30, y); g.fillStyle = k === 'DEVIL' && v === 'OBJECT' ? '#ff6b86' : '#e6fff0'; g.font = mono(24, 800); g.fillText(cut(v || '—', 20), 30, y + 24); });
  const X = 390, Y = 30, CW = w - X - 230, CH = h - 92; g.fillStyle = '#01060a'; g.fillRect(X, Y, CW, CH);
  const geo = candleGeom(wall.bars?.rows, wall.levels, CW, CH, 12);
  if (!geo) { g.fillStyle = '#7d998b'; g.font = mono(24, 700); g.fillText('NO CANDLE DATA FOR THIS COIN THIS PASS', X + 30, Y + CH / 2); }
  else {
    geo.lines.forEach(l => { const c = l.cls === 'is-take' ? '#45e486' : l.cls === 'is-stop' ? '#ff6b86' : l.cls === 'is-sup' ? '#4fd8ff' : '#ffffff'; g.strokeStyle = c; g.setLineDash([10, 7]); g.lineWidth = 2; g.beginPath(); g.moveTo(X, Y + l.y); g.lineTo(X + CW - 54, Y + l.y); g.stroke();
      g.setLineDash([]); g.fillStyle = c; g.font = mono(17, 700); g.fillText(l.label.toUpperCase(), X + CW - 150, Y + l.y - 5); });
    if (wall.bars.src === 'tape') { g.strokeStyle = '#45e486'; g.lineWidth = 3; g.beginPath(); geo.bars.forEach((b, i) => (i ? g.lineTo(X + b.x, Y + b.c) : g.moveTo(X + b.x, Y + b.c))); g.stroke(); }
    else geo.bars.forEach(b => { g.strokeStyle = g.fillStyle = b.up ? '#45e486' : '#ff6b86'; g.lineWidth = 2; g.beginPath(); g.moveTo(X + b.x, Y + b.h); g.lineTo(X + b.x, Y + b.l); g.stroke(); g.fillRect(X + b.x - b.bw / 2, Y + Math.min(b.o, b.c), b.bw, Math.max(2, Math.abs(b.c - b.o))); });
    if (wall.bars.src !== 'tape') geo.vols.forEach(v => { g.fillStyle = v.up ? 'rgba(69,228,134,.35)' : 'rgba(255,107,134,.35)'; g.fillRect(X + v.x - v.bw / 2, Y + CH - v.hgt, v.bw, v.hgt); });
    geo.off.forEach((l, i) => { g.fillStyle = l.cls === 'is-take' ? '#45e486' : l.cls === 'is-stop' ? '#ff6b86' : '#8fb9c9'; g.font = mono(16, 700); g.fillText(`${l.up ? '↑' : '↓'} ${l.label.toUpperCase()}`, X + 8 + geo.off.filter((x, j) => j < i && x.up === l.up).length * 190, l.up ? Y + 20 : Y + CH - 8); });
    const ly = Y + geo.y(geo.last); g.strokeStyle = '#f5c451'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X, ly); g.lineTo(X + CW - 54, ly); g.stroke(); g.fillStyle = '#f5c451'; g.font = mono(17, 800); g.fillText('NOW', X + CW - 50, ly + 6);
  }
  (wall.facts || []).forEach(([k, v], i) => { const y = 64 + i * 64; const x = w - 210; g.fillStyle = '#7d998b'; g.font = mono(16, 700); g.fillText(k, x, y); g.fillStyle = '#e6fff0'; g.font = mono(28, 800); g.fillText(cut(v, 9), x, y + 30); });
  g.fillStyle = '#7d998b'; g.font = mono(17, 600); g.fillText(cut(wall.caption, 100), X, h - 26);
}
const VEL_CSS = { ACCELERATING: ['▲ ACCEL', '#45e486'], STABLE: ['▬ STABLE', '#9fb3a8'], STALLING: ['◆ STALL', '#f5c451'], REVERSING: ['▼ REVERSE', '#ff6b86'], UNKNOWN: ['· READING', '#7d998b'] };
function drawSeat(g, w, h, s) {   // one seat plate: who holds it · % since entry · P/L velocity · this cycle's result · the best challenger and its margin (open: the next candidate + why)
  const dc = DEC_CSS[s.decision] || '#7d998b'; g.fillStyle = s.symbol ? '#03100b' : '#06160f'; g.fillRect(0, 0, w, h); const k = KIND_CSS[s.kind] || '#7d998b'; g.fillStyle = k; g.fillRect(0, 0, w, 10);
  g.strokeStyle = s.symbol ? k : dc; g.lineWidth = 4; g.strokeRect(2, 2, w - 4, h - 4); g.fillStyle = k; g.font = mono(20, 800); g.fillText(KIND_WORD[s.kind] || s.kind, 14, 36);
  if (!s.symbol) { g.fillStyle = dc; g.font = mono(26, 800); g.fillText(cut(s.decision, 20), 14, 80); g.fillStyle = s.ready ? '#45e486' : '#c9d8cf'; g.font = mono(28, 800); g.fillText(s.next ? `next $${cut(s.next, 8)}` : 'no candidate', 14, 122);
    g.fillStyle = s.ready ? '#45e486' : '#f5c451'; g.font = mono(20, 800); g.fillText(s.next ? (s.ready ? 'READY' : 'NOT READY') : '', 14, 156); g.fillStyle = '#9fb3a8'; g.font = mono(17, 600); g.fillText('cash is a valid position', 14, 186); return; }
  g.fillStyle = '#ffffff'; g.font = mono(38, 800); g.fillText(`$${cut(s.symbol, 8)}`, 14, 78);
  g.fillStyle = s.pct == null ? '#7d998b' : s.pct >= 0 ? '#45e486' : '#ff6b86'; g.font = mono(30, 800); g.fillText(s.pct == null ? '—' : `${s.pct >= 0 ? '+' : ''}${Number(s.pct).toFixed(1)}%`, 14, 116);
  const [vw, vc] = VEL_CSS[s.vel] || VEL_CSS.UNKNOWN; g.fillStyle = vc; g.font = mono(19, 800); g.fillText(vw, 170, 114);
  g.fillStyle = DEC_CSS[s.decision] || '#e6fff0'; g.font = mono(22, 800); g.fillText(cut(s.buying ? 'BUYING' : s.decision, 18), 14, 152);
  g.fillStyle = '#9fb3a8'; g.font = mono(16, 600); g.fillText(s.chal ? cut(`vs $${s.chal} ${s.margin != null ? `${s.margin >= 0 ? '+' : ''}${Math.round(s.margin)}/${Math.round(s.need)}` : ''}`, 28) : s.score != null ? `score ${Math.round(s.score)} · no challenger` : 'no challenger', 14, 184);
}
function drawCase(g, w, h, c) {
  const col = c.go ? '#45e486' : c.cleared ? '#6cc7ff' : '#f5c451'; g.fillStyle = c.current ? '#071a10' : '#050d0a'; g.fillRect(0, 0, w, h); g.strokeStyle = col; g.lineWidth = c.current ? 7 : 4; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#ffffff'; g.font = mono(34, 800); g.fillText(`$${cut(c.symbol, 8)}`, 14, 44); g.fillStyle = col; g.font = mono(18, 800); g.fillText(c.go ? 'GO' : c.cleared ? 'CLEARED' : cut(c.state, 10), w - 120, 40);
  g.fillStyle = '#8fb9c9'; g.font = mono(17, 600); g.fillText(cut(`${c.structure || 'no chart'} · at ${c.at}`, 26), 14, 78);
}
function drawPlatform(g, w, h, sm) { g.fillStyle = '#04140d'; g.fillRect(0, 0, w, h); g.fillStyle = '#45e486'; g.font = mono(36, 800); g.fillText('THE REAL CARD', 26, 46);
  g.fillStyle = '#e6fff0'; g.font = mono(22, 800); g.fillText(sm ? `SEATS ${sm.occupancy}/${sm.target} · BENCH ${sm.benchReady}/${sm.bench} · BUYS ${sm.buysLeft}` : 'height = % since entry · colour = who holds it', 26, 86); }
function drawChallenger(g, w, h, sw) {
  g.fillStyle = sw.ok ? '#052014' : '#1a1405'; g.fillRect(0, 0, w, h); g.strokeStyle = sw.ok ? '#45e486' : '#f5c451'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#8fb9c9'; g.font = mono(20, 700); g.fillText('CHALLENGER', 18, 34); g.fillStyle = '#ffffff'; g.font = mono(40, 800); g.fillText(`$${cut(sw.to || '—', 8)}`, 18, 84);
  g.fillStyle = sw.ok ? '#45e486' : '#f5c451'; g.font = mono(22, 800); g.fillText(sw.ok ? 'TAKES THE SEAT' : 'NOT YET', 18, 120);
}

function makeBot(k) {   // a small station figure — identity comes from its colour band, eyes and one silhouette detail, nothing more
  const g = new THREE.Group(); const white = new THREE.MeshPhysicalMaterial({ color: 0xe9eef2, roughness: 0.35, clearcoat: 0.7, clearcoatRoughness: 0.25 });
  const band = new THREE.MeshStandardMaterial({ color: AG[k], roughness: 0.4, emissive: AG[k], emissiveIntensity: 0.45 }); const dark = new THREE.MeshPhysicalMaterial({ color: 0x0b1118, roughness: 0.1, clearcoat: 1 });
  const eyeM = new THREE.MeshStandardMaterial({ color: 0, emissive: AG[k], emissiveIntensity: 2.4 });
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; p.add(o); return o; };
  const body = new THREE.Group(); g.add(body);
  add(new THREE.CapsuleGeometry(0.24, 0.2, 8, 20), white, 0, 0.4, 0, body);
  add(new THREE.TorusGeometry(0.245, 0.035, 8, 32), band, 0, 0.42, 0, body).rotation.x = Math.PI / 2;
  const head = new THREE.Group(); head.position.y = 0.86; body.add(head);
  add(new THREE.SphereGeometry(0.22, 28, 20), white, 0, 0, 0, head).scale.set(1.15, 0.9, 1);
  add(new THREE.SphereGeometry(0.2, 28, 14, -Math.PI * 0.4, Math.PI * 0.8, Math.PI * 0.3, Math.PI * 0.38), dark, 0, 0.01, 0.04, head).scale.set(1.18, 1, 1);
  const eyes = [-0.075, 0.075].map(x => add(new THREE.SphereGeometry(0.032, 10, 10), eyeM, x, 0.02, 0.23, head));
  if (k === 'sherlock') add(new THREE.CylinderGeometry(0.28, 0.28, 0.025, 28), band, 0, 0.15, 0, head);
  if (k === 'devil') [-0.14, 0.14].forEach(x => { add(new THREE.ConeGeometry(0.04, 0.16, 10), band, x, 0.21, 0, head).rotation.z = -x * 2; });
  if (k === 'trigger' || k === 'courier') add(new THREE.TorusGeometry(0.26, 0.018, 8, 28, Math.PI), band, 0, 0.02, 0, head);
  if (k === 'judge') add(new THREE.ConeGeometry(0.12, 0.15, 5), band, 0, 0.28, 0, head);
  if (k === 'warden') add(new THREE.BoxGeometry(0.32, 0.28, 0.04), band, 0, 0.48, 0.25, body);
  if (k === 'reaper') add(new THREE.ConeGeometry(0.25, 0.28, 20, 1, true), band, 0, 0.19, -0.02, head);
  if (k === 'weather') add(new THREE.SphereGeometry(0.06, 10, 10), eyeM, 0, 0.27, 0, head);
  if (k === 'tally') add(new THREE.BoxGeometry(0.3, 0.05, 0.05), band, 0, -0.02, 0.2, head);
  if (k === 'archivist') add(new THREE.BoxGeometry(0.22, 0.26, 0.1), band, 0, 0.44, -0.24, body);
  const arms = [-1, 1].map(sd => { const p = new THREE.Group(); p.position.set(sd * 0.28, 0.58, 0); body.add(p); add(new THREE.CapsuleGeometry(0.045, 0.2, 4, 10), white, 0, -0.14, 0, p); return p; });
  g.traverse(o => { o.userData.k = k; o.userData.kind = 'bot'; });
  return { g, body, head, eyes, arms, white };
}

export default function OfficeRoom3D({ model, onSel, onCoin, onSeat, onBoard, cam: camMode = 'main', rotate = false }) {
  const box = useRef(null); const tip = useRef(null); const api = useRef(null); const mRef = useRef(model); const camRef = useRef(camMode); const rotRef = useRef(rotate);
  mRef.current = model; camRef.current = camMode; rotRef.current = rotate;
  const onSelRef = useRef(onSel); onSelRef.current = onSel; const onCoinRef = useRef(onCoin); onCoinRef.current = onCoin;
  const onSeatRef = useRef(onSeat); onSeatRef.current = onSeat; const onBoardRef = useRef(onBoard); onBoardRef.current = onBoard;

  useEffect(() => {
    const host = box.current; if (!host) return undefined;
    const W = () => host.clientWidth || 900, H = () => host.clientHeight || 480;
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1)); renderer.setSize(W(), H());
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.18;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.prepend(renderer.domElement); renderer.domElement.className = 'or3-canvas';
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0x030b08); scene.fog = new THREE.Fog(0x030b08, 30, 52);
    const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.24;
    const fovFor = a => Math.max(42, Math.min(56, (2 * Math.atan(Math.tan((64 * Math.PI) / 360) / a) * 180) / Math.PI));   // the wall + all ten desks stay in frame at any width (a wide, short stage keeps ≥ 42° tall: the wall's top screens never cut)
    const cam = new THREE.PerspectiveCamera(fovFor(W() / H()), W() / H(), 0.1, 90); const pos = new THREE.Vector3(0, 13.1, 17.6); const look = new THREE.Vector3(0, 1.75, 0.15); cam.position.copy(pos); cam.lookAt(look);
    scene.add(new THREE.HemisphereLight(0xd8fff0, 0x0b1d16, 0.85));
    const key = new THREE.DirectionalLight(0xffffff, 1.7); key.position.set(-6, 14, 9); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -13, right: 13, top: 10, bottom: -10, near: 1, far: 40 }); key.shadow.normalBias = 0.03; scene.add(key);
    [[-6, 0x9fffd0], [0, 0xe8fff4], [6, 0xb8c8ff]].forEach(([x, c]) => { const pl = new THREE.PointLight(c, 30, 16, 1.6); pl.position.set(x, 6.2, 1.4); scene.add(pl); });   // three ceiling fixtures
    const M = (c, r = 0.5, m = 0) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });
    const E = (c, i = 1.4) => new THREE.MeshStandardMaterial({ color: 0, emissive: c, emissiveIntensity: i });
    const box3 = (w, h, dd, mat, x, y, z, cast = true) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, dd), mat); o.position.set(x, y, z); o.castShadow = cast; o.receiveShadow = true; scene.add(o); return o; };
    const plane = (w, h, t, x, y, z, ud) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: t, toneMapped: false })); m.position.set(x, y, z); if (ud) Object.assign(m.userData, ud); scene.add(m); return m; };
    // the room: a glossy floor with a faint grid, the back wall with light rails, two side walls
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(36, 26), new THREE.MeshStandardMaterial({ color: 0x06120d, roughness: 0.2, metalness: 0.4 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    const grid = new THREE.GridHelper(36, 36, 0x15d16a, 0x0c2e1f); grid.position.y = 0.004; grid.material.transparent = true; grid.material.opacity = 0.32; scene.add(grid);
    box3(22.4, 7.4, 0.2, M(0x0d2219, 0.8), 0, 3.7, WALL - 0.1); box3(22.4, 0.07, 0.05, E(0x45e486, 1.9), 0, 0.22, WALL + 0.02, false); box3(22.4, 0.07, 0.05, E(0x4fd8ff, 1.4), 0, 7.2, WALL + 0.02, false);
    [-11.2, 11.2].forEach(x => { box3(0.2, 7.4, 14, M(0x07150f, 0.86), x, 3.7, 1.8); box3(0.06, 0.06, 14, E(0x15d16a, 0.9), x + (x < 0 ? 0.12 : -0.12), 0.22, 1.8, false); });
    // the wall: sign · your limits + readiness (left) · the candidate monitor (centre) · pipeline status · switch test + missed winners (right)
    const sign = tex(720, 230, drawSign); plane(4.3, 1.37, sign, -8.0, 5.4, WALL + 0.03);
    const limT = tex(640, 300, drawLimits); const limP = plane(4.3, 2.02, limT, -8.0, 3.25, WALL + 0.03, { kind: 'board', board: 'limits' });
    const wallT = tex(1400, 640, drawWall); box3(9.8, 4.6, 0.12, M(0x0b1118, 0.3, 0.4), -0.3, 4.4, WALL + 0.0);
    const wallP = plane(9.6, 4.39, wallT, -0.3, 4.4, WALL + 0.07, { kind: 'wall' });
    const statT = tex(512, 336, drawStatus); const statP = plane(4.0, 2.62, statT, 7.6, 5.2, WALL + 0.03, { kind: 'board', board: 'pipeline' });
    const edgeT = tex(512, 300, drawEdge); const edgeP = plane(4.0, 2.34, edgeT, 7.6, 2.55, WALL + 0.03, { kind: 'board', board: 'switch' });

    const rugT = radial(); const deskM = M(0x1d3a2d, 0.3, 0.35); const legM = M(0x2a3d34, 0.3, 0.7);
    const st = (mRef.current?.stations || []).map((s0, i) => { const [x, z] = DESK_AT(i); const k = s0.key; const ag = AG[k];
      const rugM = new THREE.MeshBasicMaterial({ map: rugT, color: hex(ag), transparent: true, opacity: 0.32, blending: THREE.AdditiveBlending, depthWrite: false });
      const rug = new THREE.Mesh(new THREE.PlaneGeometry(4.1, 2.6), rugM); rug.rotation.x = -Math.PI / 2; rug.position.set(x, 0.008, z + 0.2); scene.add(rug);
      box3(2.7, 0.07, 1.05, deskM, x, 0.78, z); box3(2.7, 0.025, 0.04, E(ag, 1.4), x, 0.76, z + 0.53, false);
      [[-1.25, -0.42], [1.25, -0.42], [-1.25, 0.42], [1.25, 0.42]].forEach(([a, b]) => box3(0.05, 0.76, 0.05, legM, x + a, 0.38, z + b));
      const scr = tex(360, 230, drawDesk); box3(1.58, 1.02, 0.05, M(0x0b1118, 0.35), x - 0.3, 1.38, z - 0.3);
      const mon = plane(1.5, 0.96, scr, x - 0.3, 1.38, z - 0.272, { k, kind: 'monitor' }); box3(0.07, 0.36, 0.07, legM, x - 0.3, 0.98, z - 0.3);
      const sideT = tex(220, 170, drawSide); const side = new THREE.Mesh(new THREE.PlaneGeometry(0.66, 0.51), new THREE.MeshBasicMaterial({ map: sideT, toneMapped: false })); side.position.set(x + 0.72, 1.16, z - 0.2); side.rotation.y = -0.42;
      side.userData = { k, kind: 'monitor' }; scene.add(side);
      const scan = new THREE.Mesh(new THREE.PlaneGeometry(1.48, 0.05), new THREE.MeshBasicMaterial({ color: hex(ag), transparent: true, opacity: 0.0, blending: THREE.AdditiveBlending, depthWrite: false })); scan.position.set(x - 0.3, 1.38, z - 0.26); scene.add(scan);
      const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 12), E(ag, 2.6)); lamp.position.set(x + 1.2, 1.12, z - 0.35); scene.add(lamp); box3(0.03, 0.3, 0.03, legM, x + 1.2, 0.95, z - 0.35, false);
      const bx = x + 1.05; const bz = z + 0.75; const b = makeBot(k); b.g.scale.setScalar(1.3); b.g.position.set(bx, 0, bz); b.g.rotation.y = Math.atan2((x - 0.3) - bx, (z - 0.3) - bz); scene.add(b.g);
      const ringM = E(0x4d6a5c, 1.6); const ring = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.035, 8, 48), ringM); ring.rotation.x = -Math.PI / 2; ring.position.set(bx, 0.02, bz); scene.add(ring);
      const selR = new THREE.Mesh(new THREE.TorusGeometry(0.78, 0.024, 8, 56, Math.PI * 1.6), E(0xffffff, 2.4)); selR.rotation.x = -Math.PI / 2; selR.position.set(bx, 0.03, bz); selR.visible = false; scene.add(selR);
      const ripM = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }); const rip = new THREE.Mesh(new THREE.RingGeometry(0.6, 0.66, 48), ripM); rip.rotation.x = -Math.PI / 2; rip.position.set(bx, 0.035, bz); scene.add(rip);
      return { k, i, x, z, bx, bz, b, scr, sideT, mon, side, scan, rug, rugM, ringM, ring, selR, rip, ripM, ripAt: -9, act: null, color: '#4d6a5c', lab: null }; });
    // the chain on the floor: chevrons along the lane between consecutive desks (the snake), lit up to the desk the candidate stands at
    const chev = new THREE.ShapeGeometry(new THREE.Shape([new THREE.Vector2(-0.16, -0.13), new THREE.Vector2(0.16, 0), new THREE.Vector2(-0.16, 0.13), new THREE.Vector2(-0.06, 0)]));
    const segs = Array.from({ length: 9 }, (_, i) => { const a = LANE(i), b = LANE(i + 1); const pts = i === 4 ? [a, new THREE.Vector3(a.x + 2.2, 0.03, a.z), new THREE.Vector3(b.x + 2.2, 0.03, b.z), b] : [a, b];
      const m = new THREE.MeshBasicMaterial({ color: 0x15d16a, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }); const path = new THREE.CurvePath(); for (let j = 0; j < pts.length - 1; j += 1) path.add(new THREE.LineCurve3(pts[j], pts[j + 1]));
      const n = i === 4 ? 6 : 4; for (let j = 1; j < n; j += 1) { const u = j / n; const p = path.getPoint(u); const t = path.getTangent(u); const o = new THREE.Mesh(chev, m); o.rotation.x = -Math.PI / 2; o.rotation.z = Math.atan2(-t.z, t.x); o.position.set(p.x, 0.04, p.z); scene.add(o); }
      return { m, path }; });
    const pulse = new THREE.Mesh(new THREE.SphereGeometry(0.11, 14, 14), E(0xffffff, 3)); pulse.visible = false; scene.add(pulse);
    // 💵 THE REAL CARD on the hex platform between the rows
    const plat = new THREE.Mesh(new THREE.CylinderGeometry(3.0, 3.15, 0.24, 6), M(0x0a1712, 0.25, 0.55)); plat.position.set(0, 0.12, PZ); plat.rotation.y = Math.PI / 6; plat.receiveShadow = true; scene.add(plat);
    const edge = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.CylinderGeometry(3.0, 3.15, 0.24, 6)), new THREE.LineBasicMaterial({ color: 0x45e486 })); edge.position.copy(plat.position); edge.rotation.y = Math.PI / 6; scene.add(edge);
    const platT = tex(560, 104, drawPlatform); platT.userData.redraw(null); const platP = new THREE.Mesh(new THREE.PlaneGeometry(2.7, 0.5), new THREE.MeshBasicMaterial({ map: platT, toneMapped: false, transparent: true })); platP.rotation.x = -Math.PI / 2; platP.position.set(0, 0.245, PZ + 2.05); scene.add(platP);
    const spot = new THREE.SpotLight(0xd6ffe8, 46, 18, 0.55, 0.7, 1.6); spot.position.set(0, 8, PZ + 2); spot.target.position.set(0, 0.3, PZ); scene.add(spot); scene.add(spot.target);
    const slots = Array.from({ length: 6 }, (_, i) => { const grp = new THREE.Group(); grp.position.set(seatX(i, 6), 0.24, PZ); scene.add(grp);
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.38, 0.08, 32), M(0x10221a, 0.35, 0.4)); base.position.y = 0.04; grp.add(base);
      const colM = new THREE.MeshPhysicalMaterial({ color: 0x45e486, emissive: 0x45e486, emissiveIntensity: 0.55, roughness: 0.18, clearcoat: 1, transparent: true, opacity: 0.92 });
      const col = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1, 0.3), colM); col.castShadow = true; col.position.y = 0.08; grp.add(col);
      const ringM = E(0x2c4a3c, 1.4); const ring = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.025, 8, 40), ringM); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.09; grp.add(ring);
      const pT = tex(320, 200, drawSeat); const plate = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.94), new THREE.MeshBasicMaterial({ map: pT, toneMapped: false, transparent: true })); grp.add(plate);
      const ghostM = new THREE.MeshBasicMaterial({ color: 0x45e486, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false }); const ghost = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.5, 0.3), ghostM); ghost.position.y = 0.33; grp.add(ghost);
      grp.traverse(o => { o.userData.seat = i; o.userData.kind = 'seat'; });
      return { grp, col, colM, ring, ringM, plate, pT, ghost, ghostM, h: 0.05, want: 0.05, data: null }; });
    const chalT = tex(320, 140, drawChallenger); const chal = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 0.55), new THREE.MeshBasicMaterial({ map: chalT, toneMapped: false })); chal.visible = false; scene.add(chal);
    const arcM = E(0x45e486, 1.8); let arc = null; let curve = null; const spark = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 12), E(0xffffff, 3)); spark.visible = false; scene.add(spark);
    // the pass's case files, floating over the desk each one stands at (the current candidate under a beam)
    const caseObjs = []; const beamM = new THREE.MeshBasicMaterial({ color: 0x45e486, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.62, 1, 24, 1, true), beamM); beam.visible = false; scene.add(beam);

    let focusI = -1; let wall = null; let baseAt = Date.now() / 1000; let first = true; const clockT = new THREE.Clock();
    const apply = () => { const m = mRef.current; if (!m) return; wall = m.wall; baseAt = Date.now() / 1000; focusI = m.stations.findIndex(s => s.focus); const t = clockT.getElapsedTime();
      st.forEach(s => { const d = m.stations[s.i]; if (!d) return; s.d = d; s.sel = d.selected; s.focus = d.focus; s.scr.userData.redraw(d); s.sideT.userData.redraw(d);
        if (!first && s.act !== d.act) s.ripAt = t;   // a ripple only when the desk's word REALLY changed between passes
        s.act = d.act; s.color = d.color; s.ringM.emissive.set(d.color); s.ripM.color.set(d.color); s.selR.visible = !!d.selected;
        s.tip = `${d.name} · ${d.act} — ${d.actWhy}`; s.b.g.traverse(o => { o.userData.tip = s.tip; }); s.mon.userData.tip = `${d.name}'s monitor — ${d.line}`; s.side.userData.tip = `${d.name}: ${d.ms != null ? `${d.ms} ms last pass` : 'no pass timed'} · ${d.acc != null ? `${d.acc}% right over ${d.n}` : `${d.n} judged`}`; });
      segs.forEach((sg, i) => { const on = i < focusI; sg.m.color.setHex(on ? 0x45e486 : 0x15d16a); sg.m.opacity = on ? 0.95 : 0.3; });
      statT.userData.redraw(m.status); wallT.userData.redraw(wall, 0); sign.userData.redraw(m.ready); limT.userData.redraw(m.limits, m.ready); edgeT.userData.redraw(m.swap, m.missed); platT.userData.redraw(m.summary);
      statP.userData.tip = `pipeline: ${(m.status || []).map(([n, l]) => `${n} ${l}`).join(' · ')} — click for the seats + cycle log`; limP.userData.tip = `your limits — ${m.limits?.manual ? 'CREATOR MANUAL' : 'agents choose inside them'} · click to open them`;
      edgeP.userData.tip = m.swap ? `switch test: $${m.swap.from} vs $${m.swap.to} — ${m.swap.why} · click for every seat's test` : 'switch test: no held coin to test';
      wallP.userData.tip = wall ? `the wall: $${wall.symbol} — ${wall.kind === 'position' ? 'open position' : 'current candidate'} · ${wall.decision}` : 'nothing on the wall this pass';
      const ss = (m.seats || []).slice(0, 6); const n = Math.max(1, ss.length);
      slots.forEach((sl, i) => { const d = ss[i]; sl.data = d || null; sl.grp.visible = !!d; if (!d) return; sl.grp.position.x = seatX(i, n);
        sl.want = seatH(d.pct); const k = KIND_HEX[d.kind] ?? 0x45e486; const up = d.pct == null || d.pct >= 0;
        sl.col.visible = !!d.symbol; sl.ghost.visible = !d.symbol; sl.ghostM.color.set(DEC_CSS[d.decision] || '#7d998b'); sl.colM.color.setHex(up ? 0x45e486 : 0xff6b86); sl.colM.emissive.setHex(up ? 0x15d16a : 0xc0304e); sl.ringM.emissive.setHex(k); sl.pT.userData.redraw(d);
        sl.grp.traverse(o => { o.userData.tip = d.symbol ? `$${d.symbol} · ${d.kind} seat · ${d.pct == null ? '—' : `${d.pct >= 0 ? '+' : ''}${Number(d.pct).toFixed(1)}%`} · ${d.decision}${d.rule ? ` (${d.rule})` : ''}` : `open seat — ${d.decision}`; }); });
      if (arc) { scene.remove(arc); arc.geometry.dispose(); arc = null; curve = null; }
      const sw = m.swap; const fi = sw ? ss.findIndex(x => x.symbol && x.symbol === sw.from) : -1;
      if (sw && sw.to && fi >= 0) { const fx = seatX(fi, n); const a = new THREE.Vector3(fx, 0.24 + 0.08 + slots[fi].want + 0.05, PZ); const b = new THREE.Vector3(fx <= 0 ? 2.2 : -2.2, 3.0, PZ - 1.6);
        curve = new THREE.QuadraticBezierCurve3(a, new THREE.Vector3((a.x + b.x) / 2, 3.8, (a.z + b.z) / 2), b); arcM.emissive.setHex(sw.ok ? 0x45e486 : 0xf5c451); arcM.emissiveIntensity = sw.ok ? 2.2 : 0.9;
        arc = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, sw.ok ? 0.035 : 0.02, 8, false), arcM); scene.add(arc); chal.position.copy(b).add(new THREE.Vector3(0, 0.34, 0)); chal.visible = true; chalT.userData.redraw(sw);
        chal.userData.tip = `switch test: $${sw.from} → $${sw.to} — ${sw.why}`; }
      else chal.visible = false;
      caseObjs.forEach(c => { scene.remove(c.mesh); c.mesh.geometry.dispose(); c.mesh.material.dispose(); c.t.dispose(); }); caseObjs.length = 0; beam.visible = false;
      const perDesk = {};
      (m.cases || []).forEach(c => { const si = st.findIndex(s => s.k === c.at); if (si < 0) return; const k = (perDesk[c.at] = (perDesk[c.at] || 0) + 1) - 1; const s = st[si];
        const t = tex(300, 96, drawCase); t.userData.redraw(c); const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 0.4), new THREE.MeshBasicMaterial({ map: t, toneMapped: false, transparent: true }));
        mesh.position.set(s.x - 0.3, 2.45 + k * 0.48, s.z - 0.3); mesh.userData = { kind: 'case', sym: c.symbol, at: c.at, tip: `case file $${c.symbol} — at ${c.at} · ${c.state}${c.go ? ' · GO' : c.cleared ? ' · cleared' : ''}${c.structure ? ` · ${c.structure}` : ''}` };
        scene.add(mesh); caseObjs.push({ mesh, t, base: mesh.position.y, i: caseObjs.length, c });
        if (c.current) { beam.visible = true; beam.position.set(s.x - 0.3, (2.45 + 0.8) / 2, s.z - 0.3); beam.scale.set(1, 2.45 - 0.8, 1); } });
      first = false; };
    apply();

    // 🖱 hover tooltips + clicks: a bot or a monitor → that desk · a case file → its coin + its desk · a seat → its coin (Reaper) · the wall → the coin on it
    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2(); let hover = null;
    const pickables = () => [...st.flatMap(s => [s.b.g, s.mon, s.side]), ...slots.filter(x => x.grp.visible).map(x => x.grp), ...caseObjs.map(c => c.mesh), wallP, statP, limP, edgeP, ...(chal.visible ? [chal] : [])];
    const pick = e => { const rc = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ptr, cam); const hit = ray.intersectObjects(pickables(), true)[0]; return hit ? hit.object : null; };
    const onMove = e => { const o = pick(e); hover = o?.userData?.k || null; renderer.domElement.style.cursor = o ? 'pointer' : 'default'; const el = tip.current; if (!el) return;
      if (o?.userData?.tip) { const rc = host.getBoundingClientRect(); el.textContent = o.userData.tip; el.style.transform = `translate(${Math.min(e.clientX - rc.left + 14, rc.width - 260)}px, ${e.clientY - rc.top + 14}px)`; el.style.opacity = '1'; } else el.style.opacity = '0'; };
    const onLeave = () => { hover = null; if (tip.current) tip.current.style.opacity = '0'; };
    const onClick = e => { const o = pick(e); if (!o) return; const u = o.userData || {};
      if (u.kind === 'seat') { const d = slots[u.seat]?.data; if (onSeatRef.current) onSeatRef.current(d?.sb || (d?.symbol ? { symbol: d.symbol } : { empty: true })); else if (d?.symbol) { onCoinRef.current && onCoinRef.current(d.symbol); onSelRef.current('reaper'); } }
      else if (u.kind === 'board') { if (onBoardRef.current) onBoardRef.current(u.board); }
      else if (u.kind === 'case') { onCoinRef.current && onCoinRef.current(u.sym); onSelRef.current(u.at); }
      else if (u.kind === 'wall') { const w = mRef.current?.wall; if (w?.symbol) onCoinRef.current && onCoinRef.current(w.symbol); onSelRef.current(w?.kind === 'position' ? 'reaper' : mRef.current?.focus || 'tally'); }
      else if (u.k) onSelRef.current(u.k); };
    renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('pointerleave', onLeave); renderer.domElement.addEventListener('click', onClick);
    const labs = host.querySelector('.or3-labels'); st.forEach(s => { s.lab = labs?.children[s.i]; });

    const still = () => document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let seen = true; const io = new IntersectionObserver(es => { seen = es[0]?.isIntersecting ?? true; }); io.observe(host);
    const v = new THREE.Vector3(); const wantP = new THREE.Vector3(); const wantL = new THREE.Vector3(); let raf = 0, last = 0, wallAt = 0, ang = 0, prevT = 0;
    const frame = moving => {
      const t = clockT.getElapsedTime(); const dt = Math.min(0.1, t - prevT); prevT = t; const mode = camRef.current; const selS = st.find(s => s.sel);
      if (mode === 'top') { wantP.set(0, 21, 7.4); wantL.set(0, 0, 1.0); }
      else if (mode === 'card') { wantP.set(0, 6.4, PZ + 8.6); wantL.set(0, 1.0, PZ - 0.4); }
      else if (mode === 'focus' && selS) { wantP.set(selS.x * 0.8 + 0.6, 3.6, selS.z + 4.8); wantL.set(selS.x, 1.1, selS.z - 0.2); }
      else { if (rotRef.current && moving) ang += dt * 0.15; const a = rotRef.current ? Math.sin(ang) * 0.5 : 0;   // auto-rotate = a slow sweep across the room (a full orbit would go behind the wall)
        wantP.set(Math.sin(a) * 17.6, 13.1, Math.cos(a) * 17.6); wantL.set(0, 1.75, 0.15); }   // MAIN = the whole room: pulled back ~15% so every desk, the wall and the card platform sit in frame
      pos.lerp(wantP, moving ? 0.06 : 1); look.lerp(wantL, moving ? 0.08 : 1); cam.position.copy(pos); cam.lookAt(look);
      if (wall?.reviewAt != null && t - wallAt > 1) { wallAt = t; wallT.userData.redraw(wall, Date.now() / 1000 - baseAt); }   // the review clock on the wall ticks
      if (focusI > 0 && moving) { const u = (t * 0.12) % 1; const L = Math.min(focusI, 9); const seg = Math.floor(u * L); pulse.visible = true; pulse.position.copy(segs[seg].path.getPoint(u * L - seg)); pulse.position.y = 0.14; } else pulse.visible = false;
      st.forEach(s => { const { b } = s; const act = s.act || 'WAIT'; const busy = s.focus || ['SCAN', 'REVIEW', 'SUBMITTED', 'LOGGING', 'JUDGE REVIEW'].includes(act); const amp = PULSE[act] || 0;
        if (moving) { b.body.position.y = Math.abs(Math.sin(t * (busy ? 3.0 : 1.4) + s.i)) * 0.02; const sp = busy ? 8 : act === 'WAIT' ? 1.1 : 3.5; b.arms[0].rotation.x = -0.6 + Math.sin(t * sp + s.i) * 0.3; b.arms[1].rotation.x = -0.6 + Math.sin(t * sp + s.i + Math.PI) * 0.3;
          b.head.rotation.y = Math.sin(t * 0.6 + s.i) * (act === 'VETO' || act === 'OBJECT' ? 0.5 : 0.2); const blink = ((t + s.i * 0.7) % 4) < 0.12 ? 0.1 : 1; b.eyes.forEach(e => { e.scale.y = blink; });
          s.ringM.emissiveIntensity = (act === 'WAIT' ? 0.7 : 1.7) + (amp ? Math.sin(t * 5 + s.i) * amp * 1.1 : 0) + (s.focus ? 0.8 : 0); s.ring.scale.setScalar(1 + (amp ? Math.sin(t * 5 + s.i) * amp * 0.05 : 0));
          s.rugM.opacity = (act === 'WAIT' ? 0.16 : 0.32) + (s.sel ? 0.22 : 0) + (s.focus ? 0.14 : 0) + (amp ? Math.sin(t * 2.5 + s.i) * amp * 0.06 : 0);
          s.selR.rotation.z = t * (act === 'SUBMITTED' ? 2.2 : 0.6);
          const scan = act === 'SCAN' || act === 'LOGGING'; s.scan.material.opacity = scan ? 0.75 : 0; if (scan) s.scan.position.y = 1.38 - 0.44 + ((t * 0.7 + s.i * 0.13) % 1) * 0.88;
          const r = t - s.ripAt; if (r >= 0 && r < 1.2) { s.rip.scale.setScalar(1 + r * 1.6); s.ripM.opacity = (1 - r / 1.2) * 0.8; } else s.ripM.opacity = 0; }
        else { s.ringM.emissiveIntensity = act === 'WAIT' ? 0.7 : 1.7; s.rugM.opacity = (act === 'WAIT' ? 0.16 : 0.32) + (s.sel ? 0.22 : 0); s.scan.material.opacity = 0; s.ripM.opacity = 0; }
        b.white.emissive.setHex(hover === s.k ? 0x16351f : 0);
        if (s.lab) { v.set(s.bx, 1.95, s.bz); v.project(cam); const out = v.z > 1; s.lab.style.transform = `translate(${(v.x * 0.5 + 0.5) * renderer.domElement.clientWidth}px, ${(-v.y * 0.5 + 0.5) * renderer.domElement.clientHeight}px) translate(-50%, -100%)`; s.lab.style.visibility = out ? 'hidden' : 'visible'; } });
      slots.forEach((sl, i) => { if (!sl.grp.visible) return; sl.h += (sl.want - sl.h) * (moving ? 0.08 : 1); sl.col.scale.y = sl.h; sl.col.position.y = 0.08 + sl.h / 2; sl.plate.position.set(0, 0.08 + Math.max(sl.h, sl.ghost.visible ? 0.55 : 0) + 0.5, 0); if (sl.ghost.visible && moving) sl.ghostM.opacity = 0.12 + Math.sin(t * 3 + i) * 0.08; sl.plate.quaternion.copy(cam.quaternion);
        const d = sl.data; const filling = d && !d.symbol && d.decision === 'FILLING'; sl.ringM.emissiveIntensity = filling && moving ? 1.4 + Math.sin(t * 4 + i) * 1.1 : d?.selected ? 3 : 1.4; sl.ring.scale.setScalar(d?.selected ? 1.18 : 1); });
      caseObjs.forEach(c => { c.mesh.quaternion.copy(cam.quaternion); if (moving) c.mesh.position.y = c.base + Math.sin(t * 1.6 + c.i) * 0.03; c.mesh.scale.setScalar(c.c.selected ? 1.15 : c.c.current ? 1.08 : 1); });
      if (beam.visible && moving) beamM.opacity = 0.12 + Math.sin(t * 2) * 0.05;
      chal.quaternion.copy(cam.quaternion);
      if (curve && moving && arcM.emissiveIntensity > 1) { const u = (t * 0.45) % 1; spark.visible = true; spark.position.copy(curve.getPoint(u)); } else spark.visible = false;
      renderer.render(scene, cam);
    };
    const loop = now => { raf = requestAnimationFrame(loop); if (!seen) return;
      if (document.hidden || still()) { if (now - last > (document.hidden ? 2000 : 1000)) { last = now; frame(false); } return; }   // a still frame — never a blank room
      frame(true); };
    raf = requestAnimationFrame(loop); frame(false);
    const ro = new ResizeObserver(() => { renderer.setSize(W(), H()); cam.aspect = W() / H(); cam.fov = fovFor(cam.aspect); cam.updateProjectionMatrix(); }); ro.observe(host);
    api.current = { apply };
    return () => { cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('pointerleave', onLeave); renderer.domElement.removeEventListener('click', onClick);
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); const m = o.material; (Array.isArray(m) ? m : m ? [m] : []).forEach(mm => { if (mm.map) mm.map.dispose(); mm.dispose(); }); });
      rugT.dispose(); pm.dispose(); renderer.dispose(); renderer.domElement.remove(); api.current = null; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { api.current?.apply(); }, [model]);   // a new pass / another selection → monitors, rings, the wall, the chain, the card, the cases
  return <div className="or3" ref={box} data-testid="ofr-3d">
    <div className="or3-labels">{(model?.stations || []).map(s => <button key={s.key} type="button" className={`or3-lab ${s.cls} ${s.selected ? 'is-on' : ''} ${s.focus ? 'is-focus' : ''}`} style={{ '--ag': AG[s.key], '--act': ACT_FX[s.act] || '#7d998b' }}
      onClick={() => onSel(s.key)} aria-pressed={!!s.selected} data-tip={`${s.name} · ${s.act} — ${s.actWhy}`} data-testid={`desk-${s.key}`}><b>{s.name}</b><em>{s.act}</em></button>)}</div>
    <div className="or3-tip" ref={tip} aria-hidden />
  </div>;
}

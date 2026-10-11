import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { AG, ACT_FX, candleGeom, routePick } from './OfficeRoom';

// 🏢 THE CONTROL ROOM in real 3D (three.js, own lazy chunk). It draws ONLY the room model (`roomModel(o)` in OfficeRoom.jsx) — no model,
// nothing drawn; nothing in here invents a value.
//   · (look: a dark office — seated robots at black three-monitor desks with a green under-glow, glowing flow arrows, a hex platform under
//     its hologram, a neon sign, wall screens, ceiling light rails, plants, a tiled glossy floor, restrained bloom. Procedural geometry:
//     the repo carries no 3D model files, so nothing here is a downloaded asset or a static render — every screen is a live field.)
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
const XS = [-7.25, -3.8, -0.35, 3.1, 6.55];       // row 1: Tally · Sherlock · Weather · Trigger · Devil (left → right)
const XS2 = [-7.85, -4.6, 2.35, 5.45, 8.55];      // row 2: Warden · Courier · [THE REAL CARD] · Reaper · Archivist · Judge (left → right)
const Z1 = -1.4; const Z2 = 3.9; const WALL = -4.9; const PZ = 4.55; const PX = -1.15;   // the card's platform sits in row 2's gap, between Courier and Reaper
export const DESK_AT = i => (i < 5 ? [XS[i], Z1] : [XS2[i - 5], Z2]);   // both rows read left → right; the chain wraps from Devil back to Warden
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
export const seatX = (i, n) => (i - (n - 1) / 2) * (n <= 4 ? 1.15 : SEAT_GAP * 0.8);   // up to four seats get room for their full plates; five or six close up
// a seat's pedestal height follows its % since entry (capped at ±30% so one runner never hides the rest), never a guess
export const seatH = pct => (pct == null ? 0.05 : 0.14 + Math.min(1, Math.abs(Number(pct)) / 30) * 0.95);
const hex = c => new THREE.Color(c || '#4d6a5c');

function tex(w, h, draw, sc = 1) {   // sc = drawn at sc× resolution (the close-up camera reads it sharp); `draw` keeps its own w × h coordinates
  const c = document.createElement('canvas'); c.width = Math.round(w * sc); c.height = Math.round(h * sc); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  t.userData.redraw = (...a) => { const g = c.getContext('2d'); g.setTransform(sc, 0, 0, sc, 0, 0); g.clearRect(0, 0, w, h); draw(g, w, h, ...a); t.needsUpdate = true; }; return t;
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
function drawSign(g, w, h, ready) {   // the NEON sign on the left wall (transparent: the wall shows through) — its status line is the office's readiness
  const warm = ready && !ready.live; const c = warm ? '#f5c451' : '#5dff9f';
  g.save(); g.transform(1, 0, -0.2, 1, 70, 0); g.fillStyle = c; g.shadowColor = c; g.shadowBlur = 34; g.font = mono(148, 800); g.fillText('FEELESS', 18, 170); g.fillText('HQ', 18, 330);
  g.shadowBlur = 20; g.font = mono(70, 700); g.fillText('AGENT OFFICE', 30, 462); g.restore();
  g.shadowBlur = 0; g.fillStyle = warm ? '#ffe3a1' : '#b6f5d0'; g.font = mono(34, 700); g.fillText(warm ? cut(ready.state, 30) : ready ? '● LIVE' : '', 64, 530);
}
function drawTurnover(g, w, h, tv) {   // the right-wall screen: NEW COINS each cycle (the intake registry's new unique mints) — real counts, one bar per cycle
  g.fillStyle = '#020c09'; g.fillRect(0, 0, w, h); g.strokeStyle = '#45e486'; g.lineWidth = 4; g.strokeRect(2, 2, w - 4, h - 4);
  g.fillStyle = '#8fb9c9'; g.font = mono(22, 800); g.fillText('NEW COINS / CYCLE', 18, 36);
  const rows = (tv || []).filter(r => r && r[1] != null); if (!rows.length) { g.fillStyle = '#7d998b'; g.font = mono(20, 600); g.fillText('no cycle counted yet', 18, 90); return; }
  const mx = Math.max(1, ...rows.map(r => r[1])); const bw = (w - 40) / rows.length;
  rows.forEach((r, i) => { const hh = (r[1] / mx) * (h - 110); g.fillStyle = i === rows.length - 1 ? '#5dff9f' : '#1fae5c'; g.fillRect(20 + i * bw + 3, h - 40 - hh, bw - 6, hh); });
  g.fillStyle = '#e6fff0'; g.font = mono(30, 800); g.fillText(`${rows[rows.length - 1][1]} new`, w - 170, 38); g.fillStyle = '#7d998b'; g.font = mono(15, 600); g.fillText(`last ${rows.length} cycles · max ${mx}`, 20, h - 14);
}
function drawThird(g, w, h, s) {   // the third monitor: the desk's own record + why it did what it did this pass
  g.fillStyle = '#03100b'; g.fillRect(0, 0, w, h); const c = AG[s.key] || '#45e486'; g.strokeStyle = c; g.lineWidth = 3; g.strokeRect(2, 2, w - 4, h - 4);
  g.fillStyle = '#8fb9c9'; g.font = mono(16, 700); g.fillText(`RECORD · gen ${s.gen ?? 1}`, 12, 26);
  g.fillStyle = s.acc == null ? '#7d998b' : s.acc >= 55 ? '#45e486' : s.acc >= 45 ? '#f5c451' : '#ff6b86'; g.font = mono(34, 800); g.fillText(s.acc != null ? `${s.acc}%` : '—', 12, 66);
  g.fillStyle = '#9fb3a8'; g.font = mono(15, 600); g.fillText(`n ${s.n || 0} · ${s.status || '—'}`, 120, 64); g.fillStyle = '#cfe9db'; g.font = mono(15, 600); wrap(g, s.actWhy, 12, 96, 26, 19, 3);
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

const RB = (w, h, d, r = 0.08) => new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3));
function makeBot(k) {   // a seated office robot: glossy white shell, black visor with two LED eyes and ear lights in the desk's colour, one silhouette detail per desk
  const g = new THREE.Group(); const white = new THREE.MeshPhysicalMaterial({ color: 0xc9d2d9, roughness: 0.34, metalness: 0.08, clearcoat: 0.8, clearcoatRoughness: 0.2 });
  const grey = new THREE.MeshStandardMaterial({ color: 0x7f8c96, roughness: 0.4, metalness: 0.65 });
  const band = new THREE.MeshStandardMaterial({ color: AG[k], roughness: 0.35, emissive: AG[k], emissiveIntensity: 0.9 });
  const dark = new THREE.MeshPhysicalMaterial({ color: 0x04070a, roughness: 0.06, metalness: 0.3, clearcoat: 1 });
  const eyeM = new THREE.MeshStandardMaterial({ color: 0, emissive: AG[k], emissiveIntensity: 3.2 });
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; p.add(o); return o; };
  const body = new THREE.Group(); g.add(body);
  [-1, 1].forEach(sd => { add(new THREE.CapsuleGeometry(0.075, 0.3, 6, 12), white, sd * 0.12, 0.56, 0.17, body).rotation.x = Math.PI / 2;
    add(new THREE.CapsuleGeometry(0.065, 0.32, 6, 12), white, sd * 0.12, 0.31, 0.36, body); add(RB(0.13, 0.07, 0.22, 0.03), grey, sd * 0.12, 0.05, 0.42, body); });
  add(RB(0.46, 0.5, 0.32, 0.13), white, 0, 0.9, 0, body);
  add(RB(0.16, 0.07, 0.02, 0.02), band, 0, 0.97, 0.165, body);
  add(new THREE.TorusGeometry(0.2, 0.025, 8, 28), band, 0, 0.66, 0, body).rotation.x = Math.PI / 2;
  add(new THREE.CylinderGeometry(0.06, 0.07, 0.1, 14), grey, 0, 1.2, 0, body);
  const head = new THREE.Group(); head.position.y = 1.39; body.add(head);
  add(RB(0.44, 0.36, 0.38, 0.15), white, 0, 0, 0, head);
  add(RB(0.36, 0.2, 0.05, 0.06), dark, 0, 0.0, 0.18, head);
  const eyes = [-0.07, 0.07].map(x => add(new THREE.BoxGeometry(0.07, 0.04, 0.012), eyeM, x, 0.01, 0.208, head));
  [-1, 1].forEach(sd => { add(new THREE.CylinderGeometry(0.065, 0.065, 0.04, 18), band, sd * 0.235, 0, 0, head).rotation.z = Math.PI / 2; });
  if (k === 'sherlock') add(new THREE.CylinderGeometry(0.3, 0.3, 0.025, 28), band, 0, 0.19, 0, head);
  if (k === 'devil') [-0.14, 0.14].forEach(x => { add(new THREE.ConeGeometry(0.04, 0.16, 10), band, x, 0.24, 0, head).rotation.z = -x * 2; });
  if (k === 'trigger' || k === 'courier') add(new THREE.TorusGeometry(0.27, 0.018, 8, 28, Math.PI), band, 0, 0.04, 0, head);
  if (k === 'judge') add(new THREE.ConeGeometry(0.12, 0.15, 5), band, 0, 0.3, 0, head);
  if (k === 'warden') add(RB(0.3, 0.26, 0.04, 0.03), band, 0, 0.92, 0.18, body);
  if (k === 'reaper') add(new THREE.ConeGeometry(0.27, 0.3, 20, 1, true), band, 0, 0.2, -0.03, head);
  if (k === 'weather') add(new THREE.SphereGeometry(0.06, 10, 10), eyeM, 0, 0.27, 0, head);
  if (k === 'tally') add(new THREE.BoxGeometry(0.3, 0.05, 0.05), band, 0, -0.02, 0.21, head);
  if (k === 'archivist') add(RB(0.22, 0.26, 0.1, 0.03), band, 0, 0.92, -0.22, body);
  const arms = [-1, 1].map(sd => { const p = new THREE.Group(); p.position.set(sd * 0.3, 1.08, 0); body.add(p); add(new THREE.SphereGeometry(0.08, 14, 12), white, 0, 0, 0, p);
    add(new THREE.CapsuleGeometry(0.05, 0.22, 4, 10), white, 0, -0.15, 0, p); add(new THREE.CapsuleGeometry(0.045, 0.2, 4, 10), white, 0, -0.27, 0.12, p).rotation.x = Math.PI / 2; return p; });
  g.traverse(o => { o.userData.k = k; o.userData.kind = 'bot'; });
  return { g, body, head, eyes, arms, white };
}
function makeChair(mat, metal) {   // a black office chair (seat · back · arms · gas lift · five-star base) — one shared geometry set
  const g = new THREE.Group(); const add = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true; g.add(o); return o; };
  add(RB(0.58, 0.09, 0.52, 0.04), mat, 0, 0.48, 0); add(RB(0.56, 0.62, 0.08, 0.05), mat, 0, 0.86, -0.25); [-0.31, 0.31].forEach(x => add(RB(0.05, 0.05, 0.36, 0.02), metal, x, 0.66, 0));
  add(new THREE.CylinderGeometry(0.035, 0.035, 0.34, 10), metal, 0, 0.26, 0);
  for (let i = 0; i < 5; i += 1) { const a = (i / 5) * Math.PI * 2; const leg = add(RB(0.06, 0.04, 0.34, 0.015), metal, Math.sin(a) * 0.16, 0.06, Math.cos(a) * 0.16); leg.rotation.y = a; add(new THREE.SphereGeometry(0.035, 8, 8), mat, Math.sin(a) * 0.3, 0.035, Math.cos(a) * 0.3); }
  return g;
}
function makePlant(potM, leafM, leafG, seed) {   // a potted plant for the corners (deterministic leaves — the same plant every load)
  const g = new THREE.Group(); const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.28, 0.62, 24), potM); pot.position.y = 0.31; pot.castShadow = true; g.add(pot);
  let r = seed; const rnd = () => { r = (r * 9301 + 49297) % 233280; return r / 233280; };
  for (let i = 0; i < 16; i += 1) { const l = new THREE.Mesh(leafG, leafM); const a = rnd() * Math.PI * 2; const t = 0.35 + rnd() * 0.55; l.position.set(Math.sin(a) * 0.12, 0.62 + 0.45 + rnd() * 0.25, Math.cos(a) * 0.12);
    l.rotation.set(Math.cos(a) * t, 0, -Math.sin(a) * t); l.scale.set(1, 0.8 + rnd() * 0.7, 1); l.castShadow = true; g.add(l); }
  return g;
}
function floorTex() {   // dark tiles with faint seams (one 512px texture, repeated)
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d'); g.fillStyle = '#0a1511'; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(69,228,134,0.10)'; g.lineWidth = 3; g.strokeRect(1.5, 1.5, 509, 509); g.strokeStyle = 'rgba(0,0,0,0.35)'; g.lineWidth = 2; g.strokeRect(5, 5, 502, 502);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(18, 13); t.anisotropy = 8; return t;
}

export default function OfficeRoom3D({ model, onSel, onCoin, onSeat, onBoard, cam: camMode = 'main', rotate = false }) {
  const box = useRef(null); const tip = useRef(null); const api = useRef(null); const mRef = useRef(model); const camRef = useRef(camMode); const rotRef = useRef(rotate);
  mRef.current = model; camRef.current = camMode; rotRef.current = rotate;
  const onSelRef = useRef(onSel); onSelRef.current = onSel; const onCoinRef = useRef(onCoin); onCoinRef.current = onCoin;
  const onSeatRef = useRef(onSeat); onSeatRef.current = onSeat; const onBoardRef = useRef(onBoard); onBoardRef.current = onBoard;
  const [zoom, setZoom] = useState(null);   // 🔍 a close-up of one wall board / monitor (owner: "can't click board or stuff on wall to see closer")

  useEffect(() => {
    const host = box.current; if (!host) return undefined;
    const W = () => host.clientWidth || 900, H = () => host.clientHeight || 480;
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1)); renderer.setSize(W(), H());
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.85;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.prepend(renderer.domElement); renderer.domElement.className = 'or3-canvas';
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0x020806); scene.fog = new THREE.Fog(0x020806, 30, 54);
    const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.32;
    const fovFor = a => Math.max(44, Math.min(58, (2 * Math.atan(Math.tan((66 * Math.PI) / 360) / a) * 180) / Math.PI));   // the wall + all ten desks stay in frame at any width (a wide, short stage keeps ≥ 44° tall)
    const cam = new THREE.PerspectiveCamera(fovFor(W() / H()), W() / H(), 0.1, 90); const pos = new THREE.Vector3(0, 9.0, 14.8); const look = new THREE.Vector3(0, 1.55, -0.1); cam.position.copy(pos); cam.lookAt(look);
    // ✨ restrained bloom: only what is really lit (screens, LEDs, the neon sign, the flow arrows, the platform's hologram) glows
    const composer = new EffectComposer(renderer); composer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1)); composer.setSize(W(), H());
    composer.addPass(new RenderPass(scene, cam)); const bloom = new UnrealBloomPass(new THREE.Vector2(W(), H()), 0.16, 0.25, 0.97);   // 🌫 owner: "the glow of the atmosphere needs to be down" composer.addPass(bloom); composer.addPass(new OutputPass());
    scene.add(new THREE.HemisphereLight(0xcffff0, 0x06140e, 0.5));
    const key = new THREE.DirectionalLight(0xffffff, 1.0); key.position.set(-6, 14, 10); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -13, right: 13, top: 10, bottom: -10, near: 1, far: 42 }); key.shadow.normalBias = 0.03; key.shadow.radius = 4; scene.add(key);
    [[Z1 + 0.4, 0xe8fff4], [Z2 + 0.4, 0xd6ffe8]].forEach(([z, c]) => { const sp = new THREE.SpotLight(c, 20, 24, 0.95, 0.8, 1.5); sp.position.set(0, 9.5, z + 1.5); sp.target.position.set(0, 0, z); scene.add(sp); scene.add(sp.target); });   // a light pool over each row
    [[-6, 0x9fffd0], [0, 0xe8fff4], [6, 0xb8c8ff]].forEach(([x, c]) => { const pl = new THREE.PointLight(c, 11, 14, 1.6); pl.position.set(x, 6.6, -2.4); scene.add(pl); });   // the ceiling rail over the wall screens
    const M = (c, r = 0.5, m = 0) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });
    const E = (c, i = 1.4) => new THREE.MeshStandardMaterial({ color: 0, emissive: c, emissiveIntensity: i });
    const box3 = (w, h, dd, mat, x, y, z, cast = true, geo = null) => { const o = new THREE.Mesh(geo || new THREE.BoxGeometry(w, h, dd), mat); o.position.set(x, y, z); o.castShadow = cast; o.receiveShadow = true; scene.add(o); return o; };
    const plane = (w, h, t, x, y, z, ud, ry = 0, extra = {}) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: t, toneMapped: false, ...extra })); m.position.set(x, y, z); m.rotation.y = ry; if (ud) Object.assign(m.userData, ud); scene.add(m); return m; };
    // the room: a glossy tiled floor, a panelled back wall with light rails, two side walls, a ceiling rail of light panels over the wall screens
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(36, 26), new THREE.MeshPhysicalMaterial({ map: floorTex(), color: 0xffffff, roughness: 0.2, metalness: 0.35, clearcoat: 0.8, clearcoatRoughness: 0.22 }));
    floor.rotation.x = -Math.PI / 2; floor.position.z = 3; floor.receiveShadow = true; scene.add(floor);
    const wallM = M(0x0a1913, 0.78, 0.15); const panelM = M(0x0e2219, 0.55, 0.3); const railE = E(0x45e486, 0.8); const coolE = E(0x4fd8ff, 0.55);
    box3(22.4, 7.6, 0.2, wallM, 0, 3.8, WALL - 0.1);
    for (let i = 0; i < 11; i += 1) { const x = -10.2 + i * 2.04; box3(1.9, 6.6, 0.06, panelM, x, 3.6, WALL + 0.02); }   // wall panels
    box3(22.4, 0.06, 0.06, railE, 0, 0.24, WALL + 0.08, false); box3(22.4, 0.06, 0.06, coolE, 0, 7.15, WALL + 0.08, false);
    [-11.2, 11.2].forEach(x => { box3(0.2, 7.6, 15, wallM, x, 3.8, 2.2); box3(0.06, 0.06, 15, railE, x + (x < 0 ? 0.12 : -0.12), 0.24, 2.2, false);
      for (let i = 0; i < 5; i += 1) box3(0.05, 6.4, 2.6, panelM, x + (x < 0 ? 0.13 : -0.13), 3.6, -3.6 + i * 2.9); });
    box3(22.4, 0.3, 2.2, M(0x07120d, 0.6, 0.3), 0, 7.55, WALL + 1.0, false);   // the ceiling soffit over the wall …
    for (let i = 0; i < 6; i += 1) box3(2.6, 0.04, 0.5, E(0xdfffee, 0.55), -8.4 + i * 3.36, 7.39, WALL + 1.2, false);   // … with its light panels
    for (let i = 0; i < 12; i += 1) box3(0.035, 6.4, 0.03, E(0x2fe07a, 0.35), -11.22 + i * 2.04, 3.6, WALL + 0.07, false);   // vertical light seams between the wall panels
    // the screens: CURRENT CANDIDATE + PIPELINE STATUS on the back wall · the neon sign + your limits on the left wall · new coins per cycle + the switch test on the right
    const wallT = tex(1400, 640, drawWall, 1.5); box3(8.1, 3.75, 0.14, M(0x05080b, 0.25, 0.6), -1.7, 4.3, WALL + 0.02, true, RB(8.1, 3.75, 0.14, 0.06));
    const wallP = plane(7.85, 3.59, wallT, -1.7, 4.3, WALL + 0.1, { kind: 'wall' });
    const statT = tex(512, 336, drawStatus, 2); box3(3.8, 2.55, 0.12, M(0x05080b, 0.25, 0.6), 4.85, 4.55, WALL + 0.02, true, RB(3.8, 2.55, 0.12, 0.05));
    const statP = plane(3.62, 2.38, statT, 4.85, 4.55, WALL + 0.09, { kind: 'board', board: 'pipeline' });
        const sign = tex(900, 560, drawSign); plane(4.6, 2.86, sign, -8.95, 4.85, -3.95, null, 0.9, { transparent: true, depthWrite: false });
    const limT = tex(640, 300, drawLimits, 2); const limP = plane(3.0, 1.41, limT, -8.9, 2.3, -3.75, { kind: 'board', board: 'limits' }, 0.9);
    const turnT = tex(560, 330, drawTurnover, 2); const turnP = plane(3.1, 1.83, turnT, 8.95, 4.75, -3.85, { kind: 'board', board: 'pipeline' }, -0.9);
    const edgeT = tex(512, 300, drawEdge, 2); const edgeP = plane(3.0, 1.76, edgeT, 8.9, 2.35, -3.75, { kind: 'board', board: 'switch' }, -0.9);
    const potM = M(0x1a221e, 0.5, 0.2); const leafM = new THREE.MeshStandardMaterial({ color: 0x1f6b3a, roughness: 0.55, side: THREE.DoubleSide }); const leafG = new THREE.ConeGeometry(0.11, 1.0, 5, 1, true); leafG.translate(0, 0.5, 0);
    [[-10.1, -4.0, 3], [10.1, -4.0, 7], [-10.3, 7.8, 11], [10.3, 7.8, 13]].forEach(([x, z, sd]) => { const pl = makePlant(potM, leafM, leafG, sd); pl.position.set(x, 0, z); pl.scale.setScalar(1.35); scene.add(pl); });

    // the ten stations: a black desk with a green under-glow, three monitors (activity · runtime · record), keyboard, an office chair and the desk's robot sitting in it
    const rugT = radial(); const deskTop = new THREE.MeshPhysicalMaterial({ color: 0x0b110f, roughness: 0.22, metalness: 0.45, clearcoat: 1, clearcoatRoughness: 0.15 }); const legM = M(0x1f2a26, 0.3, 0.75);
    const bezel = new THREE.MeshPhysicalMaterial({ color: 0x05080b, roughness: 0.2, metalness: 0.6, clearcoat: 1 }); const glowE = E(0x15d16a, 0.7); const chairM = new THREE.MeshPhysicalMaterial({ color: 0x0c0f10, roughness: 0.42, metalness: 0.1, clearcoat: 0.4 });
    const deskG = RB(2.7, 0.08, 1.05, 0.03); const mainB = RB(1.5, 0.92, 0.05, 0.03); const sideB = RB(1.0, 0.64, 0.04, 0.025); const kbG = RB(0.6, 0.025, 0.2, 0.01);
    const st = (mRef.current?.stations || []).map((s0, i) => { const [x, z] = DESK_AT(i); const k = s0.key; const ag = AG[k];
      const rugM = new THREE.MeshBasicMaterial({ map: rugT, color: hex(ag), transparent: true, opacity: 0.05, blending: THREE.AdditiveBlending, depthWrite: false });
      const rug = new THREE.Mesh(new THREE.PlaneGeometry(4.0, 3.0), rugM); rug.rotation.x = -Math.PI / 2; rug.position.set(x, 0.008, z + 0.5); scene.add(rug);
      box3(2.7, 0.08, 1.05, deskTop, x, 0.78, z, true, deskG); box3(2.62, 0.03, 0.03, glowE, x, 0.72, z + 0.5, false);   // the green under-glow
      [-1.28, 1.28].forEach(a => box3(0.06, 0.74, 0.92, legM, x + a, 0.37, z)); box3(2.5, 0.42, 0.04, legM, x, 0.5, z - 0.44);
      box3(0.6, 0.025, 0.2, M(0x0d1412, 0.4, 0.4), x, 0.835, z + 0.22, true, kbG); box3(0.07, 0.02, 0.11, M(0x0d1412, 0.4, 0.4), x + 0.45, 0.83, z + 0.24);
      const scr = tex(360, 230, drawDesk, 2); box3(1.5, 0.92, 0.05, bezel, x, 1.58, z - 0.28, true, mainB);
      const mon = plane(1.42, 0.86, scr, x, 1.58, z - 0.25, { k, kind: 'monitor' }); box3(0.06, 0.4, 0.06, legM, x, 1.0, z - 0.3); box3(0.05, 0.5, 0.05, legM, x - 1.1, 1.05, z - 0.14); box3(0.05, 0.5, 0.05, legM, x + 1.1, 1.05, z - 0.14); box3(0.4, 0.02, 0.22, legM, x, 0.83, z - 0.3);
      const sideT = tex(220, 170, drawSide, 2); const sg = new THREE.Group(); sg.position.set(x - 1.1, 1.4, z - 0.12); sg.rotation.y = 0.42; scene.add(sg);
      const sb = new THREE.Mesh(sideB, bezel); sb.castShadow = true; sg.add(sb); const side = new THREE.Mesh(new THREE.PlaneGeometry(0.94, 0.59), new THREE.MeshBasicMaterial({ map: sideT, toneMapped: false })); side.position.z = 0.025; sg.add(side);
      side.userData = { k, kind: 'monitor' };
      const thirdT = tex(220, 170, drawThird, 2); const tg = new THREE.Group(); tg.position.set(x + 1.1, 1.4, z - 0.12); tg.rotation.y = -0.42; scene.add(tg);
      const tb = new THREE.Mesh(sideB, bezel); tb.castShadow = true; tg.add(tb); const third = new THREE.Mesh(new THREE.PlaneGeometry(0.94, 0.59), new THREE.MeshBasicMaterial({ map: thirdT, toneMapped: false })); third.position.z = 0.025; tg.add(third);
      third.userData = { k, kind: 'monitor' };
      const scan = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.04), new THREE.MeshBasicMaterial({ color: hex(ag), transparent: true, opacity: 0.0, blending: THREE.AdditiveBlending, depthWrite: false })); scan.position.set(x, 1.58, z - 0.24); scene.add(scan);
      const bx = x; const bz = z + 1.02; const chair = makeChair(chairM, legM); chair.position.set(bx, 0, bz + 0.04); chair.rotation.y = Math.PI; scene.add(chair);
      const b = makeBot(k); b.g.scale.setScalar(1.18); b.g.position.set(bx, 0.03, bz); scene.add(b.g);   // seated, facing the room
      const ringM = E(0x4d6a5c, 1.0); const ring = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.03, 8, 48), ringM); ring.rotation.x = -Math.PI / 2; ring.position.set(bx, 0.02, bz); scene.add(ring);
      const selR = new THREE.Mesh(new THREE.TorusGeometry(0.84, 0.024, 8, 56, Math.PI * 1.6), E(0xffffff, 2.4)); selR.rotation.x = -Math.PI / 2; selR.position.set(bx, 0.03, bz); selR.visible = false; scene.add(selR);
      const ripM = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }); const rip = new THREE.Mesh(new THREE.RingGeometry(0.66, 0.72, 48), ripM); rip.rotation.x = -Math.PI / 2; rip.position.set(bx, 0.035, bz); scene.add(rip);
      return { k, i, x, z, bx, bz, b, scr, sideT, thirdT, mon, side, third, scan, rug, rugM, ringM, ring, selR, rip, ripM, ripAt: -9, act: null, color: '#4d6a5c', lab: null }; });
    // the chain: a glowing arrow between consecutive desks (row 1 left → right, a turn down at the end, row 2 right → left), lit up to the desk the candidate stands at
    const arrowS = new THREE.Shape([new THREE.Vector2(-0.34, -0.07), new THREE.Vector2(0.06, -0.07), new THREE.Vector2(0.06, -0.17), new THREE.Vector2(0.34, 0), new THREE.Vector2(0.06, 0.17), new THREE.Vector2(0.06, 0.07), new THREE.Vector2(-0.34, 0.07)]);
    const arrowG = new THREE.ExtrudeGeometry(arrowS, { depth: 0.05, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 2 }); arrowG.center();
    const segs = Array.from({ length: 9 }, (_, i) => { const [xa, za] = DESK_AT(i); const [xb, zb] = DESK_AT(i + 1); const m = E(0x15d16a, 0.45);
      let p0, p1;
      if (i === 4) { p0 = new THREE.Vector3(xa, 0.07, 0.95); p1 = new THREE.Vector3(xb, 0.07, 0.95); }   // Devil → Warden: the aisle between the rows, on the floor
      else { p0 = new THREE.Vector3(xa + 1.38, 1.05, za + 0.2); p1 = new THREE.Vector3(xb - 1.38, 1.05, zb + 0.2); }
      if (i === 6) { p0 = new THREE.Vector3(xa + 1.38, 1.05, za + 0.9); p1 = new THREE.Vector3(xb - 1.38, 1.05, zb + 0.9); }   // Courier → Reaper passes in front of the card
      const mid = p0.clone().add(p1).multiplyScalar(0.5); const o = new THREE.Mesh(arrowG, m); o.position.copy(mid); o.rotation.set(-0.35, 0, 0);
      if (i === 4) { o.rotation.set(-Math.PI / 2, 0, Math.PI); o.scale.setScalar(1.6); }
      if (i === 6) o.scale.set(2.2, 1.2, 1);
      scene.add(o); const path = new THREE.CurvePath(); path.add(new THREE.LineCurve3(p0, p1)); return { m, path, o }; });
    const pulse = new THREE.Mesh(new THREE.SphereGeometry(0.09, 14, 14), E(0xffffff, 3)); pulse.visible = false; scene.add(pulse);
    // 💵 THE REAL CARD on the hex platform between the rows, under its hologram
    const plat = new THREE.Mesh(new THREE.CylinderGeometry(2.15, 2.32, 0.26, 6), new THREE.MeshPhysicalMaterial({ color: 0x08130f, roughness: 0.2, metalness: 0.7, clearcoat: 1 })); plat.position.set(PX, 0.13, PZ); plat.rotation.y = Math.PI / 6; plat.receiveShadow = true; plat.castShadow = true; scene.add(plat);
    const edge = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.CylinderGeometry(2.15, 2.32, 0.26, 6)), new THREE.LineBasicMaterial({ color: 0x5dff9f })); edge.position.copy(plat.position); edge.rotation.y = Math.PI / 6; scene.add(edge);
    const inner = new THREE.Mesh(new THREE.RingGeometry(1.78, 1.87, 6), new THREE.MeshBasicMaterial({ color: 0x45e486, toneMapped: false, side: THREE.DoubleSide })); inner.rotation.set(-Math.PI / 2, 0, Math.PI / 6); inner.position.set(PX, 0.265, PZ); scene.add(inner);
    const platT = tex(560, 104, drawPlatform, 2); platT.userData.redraw(null);
    const platP = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 0.63), new THREE.MeshBasicMaterial({ map: platT, toneMapped: false, transparent: true, opacity: 0.92, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    platP.position.set(PX, 3.05, PZ - 0.6); platP.rotation.x = -0.32; platP.scale.setScalar(1.25); platP.userData = { kind: 'holo', tip: 'the real card: seats · bench · buys left — click to look closer' }; scene.add(platP);   // the hologram over the card: seats · bench · buys left
    const holoM = new THREE.MeshBasicMaterial({ color: 0x45e486, transparent: true, opacity: 0.035, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const holo = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 1.8, 2.3, 6, 1, true), holoM); holo.position.set(PX, 1.42, PZ); holo.rotation.y = Math.PI / 6; scene.add(holo);
    const spot = new THREE.SpotLight(0xd6ffe8, 26, 16, 0.55, 0.7, 1.6); spot.position.set(PX, 8, PZ + 2); spot.target.position.set(PX, 0.3, PZ); scene.add(spot); scene.add(spot.target);
    const slots = Array.from({ length: 6 }, (_, i) => { const grp = new THREE.Group(); grp.position.set(PX + seatX(i, 6), 0.24, PZ); scene.add(grp);
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.38, 0.08, 32), M(0x10221a, 0.35, 0.4)); base.position.y = 0.04; grp.add(base);
      const colM = new THREE.MeshPhysicalMaterial({ color: 0x45e486, emissive: 0x45e486, emissiveIntensity: 0.3, roughness: 0.18, clearcoat: 1, transparent: true, opacity: 0.92 });
      const col = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1, 0.3), colM); col.castShadow = true; col.position.y = 0.08; grp.add(col);
      const ringM = E(0x2c4a3c, 1.4); const ring = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.025, 8, 40), ringM); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.09; grp.add(ring);
      const pT = tex(320, 200, drawSeat); const plate = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.94), new THREE.MeshBasicMaterial({ map: pT, toneMapped: false, transparent: true })); grp.add(plate);
      const ghostM = new THREE.MeshBasicMaterial({ color: 0x45e486, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false }); const ghost = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.5, 0.3), ghostM); ghost.position.y = 0.33; grp.add(ghost);
      grp.traverse(o => { o.userData.seat = i; o.userData.kind = 'seat'; });
      return { grp, col, colM, ring, ringM, plate, pT, ghost, ghostM, h: 0.05, want: 0.05, data: null }; });
    const chalT = tex(320, 140, drawChallenger); const chal = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 0.55), new THREE.MeshBasicMaterial({ map: chalT, toneMapped: false })); chal.visible = false; scene.add(chal);
    const arcM = E(0x45e486, 1.8); let arc = null; let curve = null; const spark = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 12), E(0xffffff, 3)); spark.visible = false; scene.add(spark);
    // the pass's case files, floating over the desk each one stands at (the current candidate under a beam)
    const caseObjs = []; const beamM = new THREE.MeshBasicMaterial({ color: 0x45e486, transparent: true, opacity: 0.08, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.62, 1, 24, 1, true), beamM); beam.visible = false; scene.add(beam);

    let focusI = -1; let wall = null; let baseAt = Date.now() / 1000; let first = true; const clockT = new THREE.Clock();
    const apply = () => { const m = mRef.current; if (!m) return; wall = m.wall; baseAt = Date.now() / 1000; focusI = m.stations.findIndex(s => s.focus); const t = clockT.getElapsedTime();
      st.forEach(s => { const d = m.stations[s.i]; if (!d) return; s.d = d; s.sel = d.selected; s.focus = d.focus; s.scr.userData.redraw(d); s.sideT.userData.redraw(d); s.thirdT.userData.redraw(d); s.third.userData.tip = `${d.name}'s record — ${d.acc != null ? `${d.acc}% right` : 'no judged record yet'} over ${d.n || 0} · ${d.actWhy || ''}`;
        if (!first && s.act !== d.act) s.ripAt = t;   // a ripple only when the desk's word REALLY changed between passes
        s.act = d.act; s.color = d.color; s.ringM.emissive.set(d.color); s.ripM.color.set(d.color); s.selR.visible = !!d.selected;
        s.tip = `${d.name} · ${d.act} — ${d.actWhy}`; s.b.g.traverse(o => { o.userData.tip = s.tip; }); s.mon.userData.tip = `${d.name}'s monitor — ${d.line}`; s.side.userData.tip = `${d.name}: ${d.ms != null ? `${d.ms} ms last pass` : 'no pass timed'} · ${d.acc != null ? `${d.acc}% right over ${d.n}` : `${d.n} judged`}`; });
      segs.forEach((sg, i) => { const on = i < focusI; sg.m.emissive.setHex(on ? 0x5dff9f : 0x15d16a); sg.m.emissiveIntensity = on ? 1.5 : 0.35; sg.o.userData.tip = on ? 'the candidate passed this step' : 'the chain: Tally → … → Judge'; });
      turnT.userData.redraw(m.turnover); turnP.userData.tip = `new coins per cycle (intake registry): ${(m.turnover || []).filter(r => r && r[1] != null).map(r => r[1]).join(' · ') || 'none counted yet'} — click for the intake + cycle log`;
      statT.userData.redraw(m.status); wallT.userData.redraw(wall, 0); sign.userData.redraw(m.ready); limT.userData.redraw(m.limits, m.ready); edgeT.userData.redraw(m.swap, m.missed); platT.userData.redraw(m.summary);
      statP.userData.tip = `pipeline: ${(m.status || []).map(([n, l]) => `${n} ${l}`).join(' · ')} — click for the seats + cycle log`; limP.userData.tip = `your limits — ${m.limits?.manual ? 'CREATOR MANUAL' : 'agents choose inside them'} · click to open them`;
      edgeP.userData.tip = m.swap ? `switch test: $${m.swap.from} vs $${m.swap.to} — ${m.swap.why} · click for every seat's test` : 'switch test: no held coin to test';
      wallP.userData.tip = wall ? `the wall: $${wall.symbol} — ${wall.kind === 'position' ? 'open position' : 'current candidate'} · ${wall.decision}` : 'nothing on the wall this pass';
      const ss = (m.seats || []).slice(0, 6); const n = Math.max(1, ss.length);
      slots.forEach((sl, i) => { const d = ss[i]; sl.data = d || null; sl.grp.visible = !!d; if (!d) return; sl.grp.position.x = PX + seatX(i, n);
        sl.want = seatH(d.pct); const k = KIND_HEX[d.kind] ?? 0x45e486; const up = d.pct == null || d.pct >= 0;
        sl.col.visible = !!d.symbol; sl.ghost.visible = !d.symbol; sl.ghostM.color.set(DEC_CSS[d.decision] || '#7d998b'); sl.colM.color.setHex(up ? 0x45e486 : 0xff6b86); sl.colM.emissive.setHex(up ? 0x15d16a : 0xc0304e); sl.ringM.emissive.setHex(k); sl.pT.userData.redraw(d);
        sl.grp.traverse(o => { o.userData.tip = d.symbol ? `$${d.symbol} · ${d.kind} seat · ${d.pct == null ? '—' : `${d.pct >= 0 ? '+' : ''}${Number(d.pct).toFixed(1)}%`} · ${d.decision}${d.rule ? ` (${d.rule})` : ''}` : `open seat — ${d.decision}`; }); });
      if (arc) { scene.remove(arc); arc.geometry.dispose(); arc = null; curve = null; }
      const sw = m.swap; const fi = sw ? ss.findIndex(x => x.symbol && x.symbol === sw.from) : -1;
      if (sw && sw.to && fi >= 0) { const fx = PX + seatX(fi, n); const a = new THREE.Vector3(fx, 0.24 + 0.08 + slots[fi].want + 0.05, PZ); const b = new THREE.Vector3(fx <= PX ? PX + 2.0 : PX - 2.0, 3.0, PZ - 1.6);
        curve = new THREE.QuadraticBezierCurve3(a, new THREE.Vector3((a.x + b.x) / 2, 3.8, (a.z + b.z) / 2), b); arcM.emissive.setHex(sw.ok ? 0x45e486 : 0xf5c451); arcM.emissiveIntensity = sw.ok ? 2.2 : 0.9;
        arc = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, sw.ok ? 0.035 : 0.02, 8, false), arcM); scene.add(arc); chal.position.copy(b).add(new THREE.Vector3(0, 0.34, 0)); chal.visible = true; chalT.userData.redraw(sw);
        chal.userData.tip = `switch test: $${sw.from} → $${sw.to} — ${sw.why}`; }
      else chal.visible = false;
      caseObjs.forEach(c => { scene.remove(c.mesh); c.mesh.geometry.dispose(); c.mesh.material.dispose(); c.t.dispose(); }); caseObjs.length = 0; beam.visible = false;
      const perDesk = {};
      (m.cases || []).forEach(c => { const si = st.findIndex(s => s.k === c.at); if (si < 0) return; const k = (perDesk[c.at] = (perDesk[c.at] || 0) + 1) - 1; const s = st[si];
        const t = tex(300, 96, drawCase); t.userData.redraw(c); const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 0.4), new THREE.MeshBasicMaterial({ map: t, toneMapped: false, transparent: true }));
        mesh.position.set(s.x, 2.32 + k * 0.46, s.z - 0.2); mesh.userData = { kind: 'case', sym: c.symbol, at: c.at, tip: `case file $${c.symbol} — at ${c.at} · ${c.state}${c.go ? ' · GO' : c.cleared ? ' · cleared' : ''}${c.structure ? ` · ${c.structure}` : ''}` };
        scene.add(mesh); caseObjs.push({ mesh, t, base: mesh.position.y, i: caseObjs.length, c });
        if (c.current) { beam.visible = true; beam.position.set(s.x, (2.32 + 0.85) / 2, s.z - 0.2); beam.scale.set(1, 2.32 - 0.85, 1); } });
      first = false; };
    apply();

    // 🖱 hover tooltips + clicks: a bot or a monitor → that desk · a case file → its coin + its desk · a seat → its coin (Reaper) · the wall → the coin on it
    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2(); let hover = null;
    // 🔍 CLOSE-UP: a screen (wall board · desk monitor · the card's hologram) fills the stage — the camera eases in front of it, square on
    let close = null;
    const zoomTo = o0 => { const desk = o0.userData?.kind === 'monitor' ? st.find(s => s.k === o0.userData.k) : null;
      const o = desk ? desk.mon : o0;   // a desk monitor → the whole desk (its three screens), seen from just over the robot's head
      const p = o.geometry?.parameters || {}; const ws = o.getWorldScale(new THREE.Vector3()); const w = desk ? 3.3 : (p.width || 1) * ws.x; const h = desk ? 1.3 : (p.height || 1) * ws.y;
      const c = o.getWorldPosition(new THREE.Vector3()); const n = new THREE.Vector3(0, 0, 1).applyQuaternion(o.getWorldQuaternion(new THREE.Quaternion())).normalize();
      const vf = (cam.fov * Math.PI) / 180; const hf = 2 * Math.atan(Math.tan(vf / 2) * cam.aspect);
      const d = Math.max(h / 2 / Math.tan(vf / 2), w / 2 / Math.tan(hf / 2)) * 1.32 + 0.05;   // the whole screen + room for the close-up bar
      const at = c.clone().addScaledVector(n, d); if (desk) at.y += 2.0;   // high enough to look over the seated robot
      close = { pos: at, look: c, mode: camRef.current }; setZoom(desk ? `${desk.d?.name || desk.k}'s desk` : o.userData?.tip ? String(o.userData.tip).split(' — ')[0] : 'close-up'); };
    const unzoom = () => { close = null; setZoom(null); };
    const ZOOMABLE = new Set(['wall', 'board', 'monitor', 'holo']);
    const pickables = () => [...st.flatMap(s => [s.b.g, s.mon, s.side, s.third]), ...slots.filter(x => x.grp.visible).map(x => x.grp), ...caseObjs.map(c => c.mesh), wallP, statP, limP, edgeP, turnP, platP, ...(chal.visible ? [chal] : [])];
    const pick = e => { const rc = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ptr, cam); const hit = ray.intersectObjects(pickables(), true)[0]; return hit ? hit.object : null; };
    const onMove = e => { const o = pick(e); hover = o?.userData?.k || null; renderer.domElement.style.cursor = o ? 'pointer' : 'default'; const el = tip.current; if (!el) return;
      if (o?.userData?.tip) { const rc = host.getBoundingClientRect(); el.textContent = o.userData.tip; el.style.transform = `translate(${Math.min(e.clientX - rc.left + 14, rc.width - 260)}px, ${e.clientY - rc.top + 14}px)`; el.style.opacity = '1'; } else el.style.opacity = '0'; };
    const onLeave = () => { hover = null; if (tip.current) tip.current.style.opacity = '0'; };
    const onClick = e => { const o = pick(e); if (!o) { if (close) unzoom(); return; }
      const ud = o.userData || {};
      if (ZOOMABLE.has(ud.kind)) zoomTo(o);   // 🔍 a screen → look at it up close (its panel view still opens beside the room)
      if (ud.kind !== 'holo') routePick(ud, mRef.current, i => slots[i]?.data, { sel: onSelRef.current, coin: onCoinRef.current, seat: onSeatRef.current, board: onBoardRef.current }); };
    const onKey = e => { if (e.key === 'Escape' && close) unzoom(); };
    window.addEventListener('keydown', onKey);
    renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('pointerleave', onLeave); renderer.domElement.addEventListener('click', onClick);
    const labs = host.querySelector('.or3-labels'); st.forEach(s => { s.lab = labs?.children[s.i]; });

    const still = () => document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const bloomOn = !document.body.classList.contains('fx-lite');   // lite mode: no bloom pass (the GPU budget goes to the page)
    let seen = true; const io = new IntersectionObserver(es => { seen = es[0]?.isIntersecting ?? true; }); io.observe(host);
    const v = new THREE.Vector3(); const wantP = new THREE.Vector3(); const wantL = new THREE.Vector3(); let raf = 0, last = 0, wallAt = 0, ang = 0, prevT = 0;
    const frame = moving => {
      const t = clockT.getElapsedTime(); const dt = Math.min(0.1, t - prevT); prevT = t; const mode = camRef.current; const selS = st.find(s => s.sel);
      if (close && close.mode !== mode) unzoom();   // a camera button ends the close-up
      if (close) { wantP.copy(close.pos); wantL.copy(close.look); }
      else if (mode === 'top') { wantP.set(0, 21, 7.4); wantL.set(0, 0, 1.0); }
      else if (mode === 'card') { wantP.set(PX, 6.4, PZ + 7.4); wantL.set(PX, 1.2, PZ - 0.6); }
      else if (mode === 'focus' && selS) { wantP.set(selS.x * 0.8 + 0.6, 3.6, selS.z + 4.8); wantL.set(selS.x, 1.1, selS.z - 0.2); }
      else { if (rotRef.current && moving) ang += dt * 0.15; const a = rotRef.current ? Math.sin(ang) * 0.5 : 0;   // auto-rotate = a slow sweep across the room (a full orbit would go behind the wall)
        wantP.set(Math.sin(a) * 14.8, 9.0, Math.cos(a) * 14.8); wantL.set(0, 1.55, -0.1); }   // MAIN = the whole room: pulled back ~15% so every desk, the wall and the card platform sit in frame
      pos.lerp(wantP, moving ? 1 - Math.exp(-dt * 3.6) : 1); look.lerp(wantL, moving ? 1 - Math.exp(-dt * 4.8) : 1); cam.position.copy(pos); cam.lookAt(look);   // time-based: lands in ~1s at any frame rate
      if (wall?.reviewAt != null && t - wallAt > 1) { wallAt = t; wallT.userData.redraw(wall, Date.now() / 1000 - baseAt); }   // the review clock on the wall ticks
      if (focusI > 0 && moving) { const u = (t * 0.12) % 1; const L = Math.min(focusI, 9); const seg = Math.floor(u * L); pulse.visible = true; pulse.position.copy(segs[seg].path.getPoint(u * L - seg)); } else pulse.visible = false;
      st.forEach(s => { const { b } = s; const act = s.act || 'WAIT'; const busy = s.focus || ['SCAN', 'REVIEW', 'SUBMITTED', 'LOGGING', 'JUDGE REVIEW'].includes(act); const amp = PULSE[act] || 0;
        if (moving) { b.body.position.y = Math.abs(Math.sin(t * (busy ? 3.0 : 1.4) + s.i)) * 0.02; const sp = busy ? 8 : act === 'WAIT' ? 1.1 : 3.5; b.arms[0].rotation.x = -0.6 + Math.sin(t * sp + s.i) * 0.3; b.arms[1].rotation.x = -0.6 + Math.sin(t * sp + s.i + Math.PI) * 0.3;
          b.head.rotation.y = Math.sin(t * 0.6 + s.i) * (act === 'VETO' || act === 'OBJECT' ? 0.5 : 0.2); const blink = ((t + s.i * 0.7) % 4) < 0.12 ? 0.1 : 1; b.eyes.forEach(e => { e.scale.y = blink; });
          s.ringM.emissiveIntensity = (act === 'WAIT' ? 0.3 : 0.7) + (amp ? Math.sin(t * 5 + s.i) * amp * 0.6 : 0) + (s.focus ? 0.4 : 0); s.ring.scale.setScalar(1 + (amp ? Math.sin(t * 5 + s.i) * amp * 0.05 : 0));
          s.rugM.opacity = (act === 'WAIT' ? 0.03 : 0.06) + (s.sel ? 0.08 : 0) + (s.focus ? 0.04 : 0) + (amp ? Math.sin(t * 2.5 + s.i) * amp * 0.03 : 0);
          s.selR.rotation.z = t * (act === 'SUBMITTED' ? 2.2 : 0.6);
          const scan = act === 'SCAN' || act === 'LOGGING'; s.scan.material.opacity = scan ? 0.75 : 0; if (scan) s.scan.position.y = 1.58 - 0.42 + ((t * 0.7 + s.i * 0.13) % 1) * 0.84;
          const r = t - s.ripAt; if (r >= 0 && r < 1.2) { s.rip.scale.setScalar(1 + r * 1.6); s.ripM.opacity = (1 - r / 1.2) * 0.8; } else s.ripM.opacity = 0; }
        else { s.ringM.emissiveIntensity = act === 'WAIT' ? 0.3 : 0.7; s.rugM.opacity = (act === 'WAIT' ? 0.03 : 0.06) + (s.sel ? 0.08 : 0); s.scan.material.opacity = 0; s.ripM.opacity = 0; }
        b.white.emissive.setHex(hover === s.k ? 0x16351f : 0);
        if (s.lab) { v.set(s.bx, 2.2, s.bz); v.project(cam); const out = v.z > 1; s.lab.style.transform = `translate(${(v.x * 0.5 + 0.5) * renderer.domElement.clientWidth}px, ${(-v.y * 0.5 + 0.5) * renderer.domElement.clientHeight}px) translate(-50%, -100%)`; s.lab.style.visibility = out ? 'hidden' : 'visible'; } });
      slots.forEach((sl, i) => { if (!sl.grp.visible) return; sl.h += (sl.want - sl.h) * (moving ? 0.08 : 1); sl.col.scale.y = sl.h; sl.col.position.y = 0.08 + sl.h / 2; sl.plate.position.set(0, 0.08 + Math.max(sl.h, sl.ghost.visible ? 0.55 : 0) + 0.5, 0); if (sl.ghost.visible && moving) sl.ghostM.opacity = 0.12 + Math.sin(t * 3 + i) * 0.08; sl.plate.quaternion.copy(cam.quaternion);
        const d = sl.data; const filling = d && !d.symbol && d.decision === 'FILLING'; sl.ringM.emissiveIntensity = filling && moving ? 1.4 + Math.sin(t * 4 + i) * 1.1 : d?.selected ? 3 : 1.4; sl.ring.scale.setScalar(d?.selected ? 1.18 : 1); });
      caseObjs.forEach(c => { c.mesh.quaternion.copy(cam.quaternion); if (moving) c.mesh.position.y = c.base + Math.sin(t * 1.6 + c.i) * 0.03; c.mesh.scale.setScalar(c.c.selected ? 1.15 : c.c.current ? 1.08 : 1); });
      if (beam.visible && moving) beamM.opacity = 0.06 + Math.sin(t * 2) * 0.025;
      chal.quaternion.copy(cam.quaternion);
      if (curve && moving && arcM.emissiveIntensity > 1) { const u = (t * 0.45) % 1; spark.visible = true; spark.position.copy(curve.getPoint(u)); } else spark.visible = false;
      if (bloomOn) composer.render(); else renderer.render(scene, cam);
    };
    const loop = now => { raf = requestAnimationFrame(loop); if (!seen) return;
      if (document.hidden || still()) { if (now - last > (document.hidden ? 2000 : 1000)) { last = now; frame(false); } return; }   // a still frame — never a blank room
      frame(true); };
    raf = requestAnimationFrame(loop); frame(false);
    const ro = new ResizeObserver(() => { renderer.setSize(W(), H()); composer.setSize(W(), H()); bloom.setSize(W(), H()); cam.aspect = W() / H(); cam.fov = fovFor(cam.aspect); cam.updateProjectionMatrix(); }); ro.observe(host);
    api.current = { apply, unzoom };
    return () => { cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); window.removeEventListener('keydown', onKey); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('pointerleave', onLeave); renderer.domElement.removeEventListener('click', onClick);
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); const m = o.material; (Array.isArray(m) ? m : m ? [m] : []).forEach(mm => { if (mm.map) mm.map.dispose(); mm.dispose(); }); });
      rugT.dispose(); pm.dispose(); composer.dispose(); renderer.dispose(); renderer.domElement.remove(); api.current = null; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { api.current?.apply(); }, [model]);   // a new pass / another selection → monitors, rings, the wall, the chain, the card, the cases
  return <div className={`or3 ${zoom ? 'is-zoom' : ''}`} ref={box} data-testid="ofr-3d">
    <div className="or3-labels">{(model?.stations || []).map(s => <button key={s.key} type="button" className={`or3-lab ${s.cls} ${s.selected ? 'is-on' : ''} ${s.focus ? 'is-focus' : ''}`} style={{ '--ag': AG[s.key], '--act': ACT_FX[s.act] || '#7d998b' }}
      onClick={() => onSel(s.key)} aria-pressed={!!s.selected} data-tip={`${s.name} · ${s.act} — ${s.actWhy}`} data-testid={`desk-${s.key}`}><b>{s.name}</b><em>{s.act}</em></button>)}</div>
    <div className="or3-tip" ref={tip} aria-hidden />
    {zoom && <div className="or3-zoom" data-testid="or3-zoom"><span>🔍 {zoom}</span><button type="button" className="m-btn" onClick={() => api.current?.unzoom()} data-testid="or3-unzoom">✕ Back to the room</button></div>}
  </div>;
}

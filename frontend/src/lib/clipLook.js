// 🎨 Slice 29: a clip's look in the page — the same words, beats and pops the renderer (backend/clip_look.py) uses, so the live preview in the
// editor shows what ffmpeg will make. Pure helpers only; the page never renders a file itself.
export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export const PLATS = [['tiktok', 'TikTok'], ['instagram', 'Reels'], ['youtube', 'Shorts'], ['x', 'X']];
export const DEFAULT_LOOK = { cap: { font: 'bold', color: 'white', hot: 'green', size: 'M', pos: 'low', mode: 'word', words: 3, case: 'upper' }, tr: 'cut',
  fx: { punch: false, shake: false, grade: 'none', speed: 'off', pop: false }, edit: { w: {}, off: 0 } };
export const FONT_CSS = { bold: "'Liberation Sans', Arial, 'Helvetica Neue', sans-serif", impact: "Impact, 'Haettenschweiler', 'Arial Narrow Bold', sans-serif",
  condensed: "'Avenir Next Condensed', 'Arial Narrow', sans-serif", rounded: "'Arial Rounded MT Bold', 'SF Pro Rounded', sans-serif", serif: "Georgia, 'Times New Roman', serif", chalk: "Chalkduster, 'Comic Sans MS', fantasy" };
export const FONT_WEIGHT = { bold: 800, impact: 400, condensed: 900, rounded: 700, serif: 700, chalk: 400 };
export const COLOR = { white: '#ffffff', cream: '#fff4d6', yellow: '#ffd60a', green: '#19e68c', cyan: '#28dcff', pink: '#ff46a0', orange: '#ff8c1e' };   // the rendered file's colours (backend COLORS)
export const GRADE_CSS = { none: 'none', warm: 'saturate(1.15) sepia(.12)', teal: 'hue-rotate(-10deg) saturate(1.1) contrast(1.04)', mono: 'grayscale(1) contrast(1.12)',
  punchy: 'contrast(1.12) saturate(1.3)', vintage: 'sepia(.35) contrast(.95) saturate(1.1)', cool: 'hue-rotate(8deg) saturate(1.05) brightness(1.02)' };
export const SIZE = { S: 0.8, M: 1, L: 1.2 };
export const POS = { top: 0.22, mid: 0.44, low: 0.64, bottom: 0.76 };
export const BASE_PX = { story: 88 / 1080, feed: 66 / 1080, wide: 60 / 1920 };   // caption size as a share of the frame width, per format
export const RATIO = { story: '9 / 16', feed: '1 / 1', wide: '16 / 9' };

/** Pure: any look → a whole look (defaults filled in). */
export function fullLook(l) {
  const a = l || {};
  return { cap: { ...DEFAULT_LOOK.cap, ...(a.cap || {}) }, tr: a.tr || 'cut', fx: { ...DEFAULT_LOOK.fx, ...(a.fx || {}) }, edit: { w: { ...((a.edit || {}).w || {}) }, off: Number((a.edit || {}).off || 0) }, ...(a.preset ? { preset: a.preset } : {}) };
}
const sorted = o => (o && typeof o === 'object' && !Array.isArray(o) ? Object.keys(o).sort().reduce((r, k) => ({ ...r, [k]: sorted(o[k]) }), {}) : o);
/** Pure: the look's design (not its word edits) — two clips with the same sig look the same. */
export function sig(l) { const a = fullLook(l); return JSON.stringify(sorted({ cap: a.cap, tr: a.tr, fx: a.fx })); }
/** Pure: the clip whose look is the same as `l`, or null. */
export function twinOf(l, clips, me) { const s = sig(l); return (clips || []).find(f => f.id !== me && f.studio?.look && sig(f.studio.look) === s) || null; }

/** Pure: the clip's words with the edits + offset applied (times from the clip start); '' drops a word. */
export function editedWords(ws, look) {
  const a = fullLook(look);
  return (ws || []).map(w => ({ ...w, w: a.edit.w[String(w.i)] ?? w.w, s: Math.max(0, w.s + a.edit.off), e: Math.max(0.05, w.e + a.edit.off) })).filter(w => String(w.w).trim());
}
/** Pure: caption groups (≤ `most` words, broken at punctuation or a pause) — backend clip_farm.groups. */
export function groupWords(ws, most = 3) {
  const out = []; let cur = [];
  ws.forEach((w, i) => { cur.push(w); const nx = ws[i + 1]; if (cur.length >= most || /[.,!?;:]$/.test(w.w) || !nx || nx.s - w.e > 0.6) { out.push(cur); cur = []; } });
  return out;
}
/** Pure: what the caption shows at second t → { g: words, hot: index } or null. */
export function captionAt(groups, t) {
  for (const g of groups) {
    const end = Math.max(g[g.length - 1].e, g[g.length - 1].s + 0.25);
    if (t >= g[0].s && t < end) { let hot = 0; g.forEach((w, i) => { if (t >= w.s) hot = i; }); return { g, hot }; }
  }
  return null;
}
/** Pure: new-sentence points (≥ 2.5 s apart, ≤ 7) — backend clip_look.beats. */
export function beats(ws, dur) {
  const pts = [0];
  for (let i = 1; i < ws.length; i += 1) {
    if ((ws[i].s - ws[i - 1].e > 0.3 || /[.!?]$/.test(ws[i - 1].w)) && ws[i].s - pts[pts.length - 1] >= 2.5 && ws[i].s < dur - 1.5) pts.push(Math.round(ws[i].s * 100) / 100);
  }
  return pts.slice(0, 7);
}
const STOP = new Set('the a an and or but so to of in on at for with from this that these those it its is are was were be been being i you he she we they me my your our their just like really very what when where which who how then than there here have has had do does did not no yes can could would should will about into out up down'.split(' '));
/** Pure: words that pop as stickers (numbers, long uncommon words, ≥ 3 s apart, ≤ 3) — backend clip_look.pops. */
export function pops(ws, dur) {
  const out = [];
  ws.forEach(w => { const t = String(w.w).replace(/[^\w$%'-]/g, ''); if ((/\d/.test(t) || (t.length >= 7 && !STOP.has(t.toLowerCase()))) && (!out.length || w.s - out[out.length - 1][0] >= 3) && w.s < dur - 0.8) out.push([w.s, t.toUpperCase()]); });
  return out.slice(0, 3);
}
/** Pure: the play speed at second t of the clip. */
export function speedAt(look, t, dur) { const sp = fullLook(look).fx.speed; return sp === 'tight' ? 1.1 : sp === 'ramp' && dur > 8 ? (t < dur - 2.5 ? 1.25 : 1) : 1; }
/** Pure: the preview's moving parts at second t: punch-in, a transition hit, a shake, a pop. */
export function fxAt(look, t, bts, pps, dur) {
  const a = fullLook(look); const out = { zoom: 1, hit: '', shake: false, pop: null, fade: 1 };
  if (a.fx.punch) { for (let i = 1; i < bts.length; i += 2) if (t >= bts[i] && t < (bts[i + 1] ?? dur + 1)) out.zoom = 1.12; }
  const near = bts.find(b => t >= b - 0.1 && t < b + 0.35);
  if (near != null && a.tr !== 'cut') out.hit = a.tr;
  if (a.tr === 'zoom' && near != null && t >= near) out.zoom *= 1 + 0.22 * Math.max(0, 1 - (t - near) / 0.35);
  if (a.tr === 'fade') out.fade = Math.min(1, t / 0.3, Math.max(0, dur - t) / 0.35);
  const p = pps.find(([at]) => t >= at && t < at + 0.8);
  if (a.fx.pop && p) out.pop = p[1];
  if (a.fx.shake && (pps.length ? pps : bts.slice(1, 3).map(b => [b])).some(([at]) => t >= at && t < at + 0.4)) out.shake = true;
  return out;
}
/** Pure: a short line about a look — backend clip_look.describe. */
export function describe(look, fonts = {}) {
  const a = fullLook(look); const on = ['punch', 'shake', 'pop'].filter(k => a.fx[k]).concat(a.fx.grade !== 'none' ? [`${a.fx.grade} grade`] : [], a.fx.speed !== 'off' ? [`speed ${a.fx.speed}`] : []);
  return `${fonts[a.cap.font] || a.cap.font} · ${a.cap.mode} · ${a.tr}${on.length ? ` · ${on.join(', ')}` : ''}`;
}

/** Pure: where a clip stands — posted, planned (it has a day) or waiting for the approve. */
export function clipStatus(f) { return f?.posted ? 'posted' : f?.studio?.slot ? 'planned' : 'approve'; }
/** Pure: the clips that pass the quick filters, best first (or newest). */
export function filterClips(clips, { status = 'all', run = 'all', min = 0, sort = 'score' } = {}) {
  return (clips || []).filter(f => f?.studio?.clip && (status === 'all' || clipStatus(f) === status) && (run === 'all' || f.studio.clip.run === run) && (Number(f.studio.clip.both) || 0) >= min)
    .sort((a, b) => (sort === 'new' ? (b.at || 0) - (a.at || 0) : (Number(b.studio.clip.both) || 0) - (Number(a.studio.clip.both) || 0)) || (a.studio.clip.rank || 0) - (b.studio.clip.rank || 0));
}
/** Pure: the clips grouped by the upload they came from, newest upload first. */
export function bySource(clips) {
  const m = new Map(); clips.forEach(f => { const k = f.studio.clip.run; if (!m.has(k)) m.set(k, { run: k, from: f.studio.clip.from, at: f.at || 0, rows: [] }); const g = m.get(k); g.rows.push(f); g.at = Math.max(g.at, f.at || 0); });
  return [...m.values()].sort((a, b) => b.at - a.at);
}
/** Pure: the week with `job` on `day` (or off the week when day is ''), one slot per clip, Mon → Sun then by time. */
export function moveSlot(slots, job, day, base = {}) {
  const rest = (slots || []).filter(s => s.job !== job); const old = (slots || []).find(s => s.job === job);
  const next = day ? [...rest, { time: '19:00', plats: ['tiktok', 'instagram', 'youtube'], why: '', ...base, ...old, job, day }] : rest;
  return next.sort((a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || String(a.time).localeCompare(String(b.time)));
}

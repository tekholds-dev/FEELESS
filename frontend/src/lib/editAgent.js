// 🎬 The studio's pure helpers (owner 2026-11-17, studio proposals 2–5): creator safe zones, hook templates, captions on the timeline,
// a free on-device "cut dead air", and the list of what an agent edit changed (shown, and undone in one tap). No DOM, no network.
import { clipLen } from './videoRender';

// Where the app's own buttons and words sit on top of a video, as fractions of the frame: keep faces and words out of these.
// 9:16 = TikTok / Reels / Shorts (handle + caption at the bottom, the like / share column on the right, the top bar).
export const SAFE = {
  '9:16': [{ x: 0, y: 0, w: 1, h: 0.1, why: 'top bar' }, { x: 0, y: 0.78, w: 1, h: 0.22, why: 'handle + caption' }, { x: 0.86, y: 0.36, w: 0.14, h: 0.42, why: 'like · share' }],
  '16:9': [{ x: 0, y: 0.88, w: 1, h: 0.12, why: 'player bar' }],
  '1:1': [{ x: 0, y: 0.86, w: 1, h: 0.14, why: 'feed caption' }],
};
// The hook: big words in the first 2.5 s, inside the safe area of that shape.
export function hookFor(aspect, t = 0) {
  const y = aspect === '9:16' ? 0.2 : aspect === '1:1' ? 0.16 : 0.14;
  return { at: Math.max(0, t), dur: 2.5, text: 'THE PAYOFF FIRST', y, size: aspect === '9:16' ? 0.075 : 0.09, color: '#ffffff' };
}
// Caption lines (seconds from the SOURCE file's start) → texts on the timeline under that clip: only what the clip keeps, moved by its trim and speed.
export function captionTexts(lines, clip, offset, aspect = '9:16') {
  const sp = clip.speed || 1; const y = aspect === '9:16' ? 0.7 : 0.8;
  return (lines || []).filter(l => l.at + l.dur > clip.in && l.at < clip.out).map(l => {
    const s = Math.max(l.at, clip.in); const e = Math.min(l.at + l.dur, clip.out);
    return { at: +(offset + (s - clip.in) / sp).toFixed(2), dur: +Math.max(0.2, (e - s) / sp).toFixed(2), text: String(l.text).toUpperCase(), y, size: 0.05, color: '#ffffff', cap: true };
  });
}
// Quiet spans in a mono sample array: windows of `win` s under `floor` (RMS) that last at least `min` s, each shrunk by `pad` s at both ends.
export function quietSpans(samples, rate, { win = 0.05, floor = 0.012, min = 0.6, pad = 0.12 } = {}) {
  const n = Math.max(1, Math.round(win * rate)); const out = []; let start = null;
  for (let i = 0; i * n < samples.length; i += 1) {
    let sum = 0; const a = i * n; const b = Math.min(samples.length, a + n);
    for (let k = a; k < b; k += 1) sum += samples[k] * samples[k];
    const quiet = Math.sqrt(sum / Math.max(1, b - a)) < floor; const t = a / rate;
    if (quiet && start === null) start = t;
    if ((!quiet || b >= samples.length) && start !== null) { const end = quiet ? b / rate : t; if (end - start >= min) out.push([start + pad, end - pad]); start = null; }
  }
  return out;
}
// One clip minus the quiet spans (source seconds) → the clips that stay, in order. Pieces under 0.15 s are dropped.
export function dropSpans(clip, spans, uid) {
  const keep = []; let from = clip.in;
  [...spans].sort((x, y) => x[0] - y[0]).forEach(([s, e]) => { if (e <= from || s >= clip.out) return; if (s - from >= 0.15) keep.push([from, Math.min(s, clip.out)]); from = Math.max(from, e); });
  if (clip.out - from >= 0.15) keep.push([from, clip.out]);
  return keep.map(([a, b], i) => ({ ...clip, id: i ? uid('c') : clip.id, in: +a.toFixed(3), out: +b.toFixed(3) }));
}
// What changed between two edits, in words (the agent's edit is shown before you keep it).
const secs = v => `${v.toFixed(1)} s`;
export function diffEdit(a, b, names = {}) {
  const out = []; const nm = c => names[c.src] || 'a clip';
  if (a.aspect !== b.aspect) out.push(`Shape ${a.aspect} → ${b.aspect}`);
  const A = new Map(a.clips.map(c => [c.id, c])); const B = new Map(b.clips.map(c => [c.id, c]));
  b.clips.forEach(c => { const o = A.get(c.id); if (!o) out.push(a.clips.some(x => x.src === c.src) ? `Kept a piece of ${nm(c)} (${secs(clipLen(c))})` : `Added ${nm(c)} (${secs(clipLen(c))})`); else if (Math.abs(clipLen(o) - clipLen(c)) > 0.05) out.push(`Trimmed ${nm(c)}: ${secs(clipLen(o))} → ${secs(clipLen(c))}`); else if ((o.speed || 1) !== (c.speed || 1)) out.push(`${nm(c)} at ${c.speed}x`); });
  a.clips.forEach(c => { if (!B.has(c.id)) out.push(`Cut ${nm(c)} (${secs(clipLen(c))})`); });
  const order = x => x.clips.map(c => c.id).filter(id => A.has(id) && B.has(id)).join();
  if (order(a) !== order(b)) out.push('Clips in a new order');
  const T = new Map(a.texts.map(x => [x.id, x]));
  b.texts.forEach(x => { const o = T.get(x.id); if (!o) out.push(`Words “${String(x.text).slice(0, 28)}” at ${secs(x.at)}`); else if (o.text !== x.text) out.push(`Words → “${String(x.text).slice(0, 28)}”`); });
  a.texts.forEach(x => { if (!b.texts.some(y => y.id === x.id)) out.push(`Removed “${String(x.text).slice(0, 28)}”`); });
  if ((a.music || []).length !== (b.music || []).length) out.push(`Sound tracks ${(a.music || []).length} → ${(b.music || []).length}`);
  const ta = a.clips.reduce((s, c) => s + clipLen(c), 0); const tb = b.clips.reduce((s, c) => s + clipLen(c), 0);
  if (Math.abs(ta - tb) > 0.05) out.push(`Length ${secs(ta)} → ${secs(tb)}`);
  return out;
}
// Words in the editor's agent box that this device does for free, before any model is asked.
export const DEAD_AIR = /\b(dead air|silen(ce|t)|pauses?|quiet (parts|bits|gaps))\b/i;
export const SWAP_HERE = /\b(swap|replace|put)\b.*\b(guy|person|man|woman|girl|dude|him|her|character|face)\b/i;

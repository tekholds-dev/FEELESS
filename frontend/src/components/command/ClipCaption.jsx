import React from 'react';
import { COLOR, FONT_CSS, FONT_WEIGHT, GRAD2, GRADE_CSS, emojiFor, fullLook, hookKey, keyword, safeTop } from '../../lib/clipLook';

// 🎨 Slice 29 add-on: a caption drawn in the page the way ffmpeg draws it in the file (backend clip_look.cap_pic / hook_band): the modern
// styles (thin stroke + soft shadow, never a slab; ≤ 2 tight lines; the spoken word popping in the accent; the sweep filling it) and the
// classic band. Used by the editor's live preview and by every template card's moving sample.
const clean = (w, up) => (up ? String(w).replace(/[^\w'’$%#@&!?.,-]/g, '').toUpperCase() || w : w);

/** The caption for one group of words, `hot` = the word being said. */
export function CapLayer({ cap, g, hot, scale = 1, frac = 1, top, anim = false }) {
  const up = cap.case === 'upper'; const hc = COLOR[cap.hot]; const base = COLOR[cap.color];
  if (cap.style === 'classic') {
    return <div className={`cse-cap is-${cap.mode}`} style={{ top: `${top * 100}%` }} data-testid="cse-cap">{g.map((x, i) => {
      const on = i === hot; const said = cap.mode === 'karaoke' && i <= hot;
      return <span key={`${x.i ?? x.w}-${i}`} className={on ? 'is-hot' : said ? 'is-said' : ''} style={{ color: (cap.mode === 'word' && on) || said ? hc : cap.mode === 'box' && on ? '#080c0a' : base }}>{clean(x.w, up)}</span>;
    })}</div>;
  }
  return <div className={`cse-cap is-m is-${cap.style}${anim ? ' is-anim' : ''}`} style={{ top: `${top * 100}%` }} data-testid="cse-cap">{g.map((x, i) => {
    const on = i === hot; const kw = keyword(x.w); const emo = cap.style === 'emoji' && on && kw ? emojiFor(x.w) : undefined;
    const st = on ? { '--sc': scale, ...(cap.style === 'sweep' && !anim ? { backgroundSize: `${Math.round(frac * 100)}% 100%, 100% 100%` } : {}) } : undefined;
    return <span key={`${x.i ?? x.w}-${i}`} className={`${on ? 'is-hot' : i < hot ? 'is-said' : ''}${kw ? ' is-kw' : ''}`} style={st} data-emo={emo}>{clean(x.w, up)}</span>;
  })}</div>;
}

/** The hook title for the first 2 s: white words, a thin stroke, a soft shadow, its key word in the accent. No slab. */
export function HookLayer({ hook, cap, top, px }) {
  const key = hookKey(hook); const words = String(hook || '').split(/\s+/).filter(Boolean);
  return <div className="cse-hook is-m" style={{ top: `${top}%`, fontSize: `${px}px` }} data-testid="cse-hook">{words.map((w, i) => <span key={i} className={w === key ? 'is-key' : ''}>{w}{i < words.length - 1 ? ' ' : ''}</span>)}</div>;
}

/** The css a stage needs for one look (font, size, accent, gradient colours). */
export function capVars(a, px) {
  const hot = a.cap.hot === 'white' && a.cap.style !== 'classic' ? COLOR.green : COLOR[a.cap.hot];
  return { '--cap-font': FONT_CSS[a.cap.font], '--cap-w': FONT_WEIGHT[a.cap.font], '--cap-px': `${px}px`, '--hot': hot, '--base': COLOR[a.cap.color], '--g2': GRAD2[a.cap.hot] || COLOR.cyan };
}

const SAMPLE = ['The', 'underwater', 'vehicle', 'went', '4,000', 'meters'];
/** A template's moving sample: a still of the clip with the template's captions cycling word by word (CSS does the pop / sweep). */
export function TplSample({ look, img, tick = 0, hook = 'A seven-foot titanium sphere' }) {
  const a = fullLook(look); const n = Math.max(2, Math.min(SAMPLE.length, a.cap.words)); const g = SAMPLE.slice(0, n).map((w, i) => ({ w, i }));
  const hot = tick % n; const px = 11 * ({ S: 0.85, M: 1, L: 1.15 }[a.cap.size] || 1);
  return <div className={`cst-tpl-sample cse-stage is-${a.cap.style}`} style={capVars(a, px)} aria-hidden="true">
    {img ? <img src={img} alt="" style={{ filter: GRADE_CSS[a.fx.grade] }} loading="lazy" /> : <i className="cst-tpl-bg" style={{ filter: GRADE_CSS[a.fx.grade] }} />}
    <HookLayer hook={hook} cap={a.cap} top={9} px={px * 0.8} />
    <CapLayer key={tick} cap={a.cap} g={g} hot={hot} top={safeTop(a.cap, null, 0.16)} anim />
  </div>;
}

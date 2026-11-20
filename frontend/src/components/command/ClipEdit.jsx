import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { Brain, Check, Clapperboard, Loader2, Pause, Play, RotateCcw, Undo2, Wand2 } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { BASE_PX, COLOR, DEFAULT_LOOK, FONT_CSS, FONT_WEIGHT, GRADE_CSS, POS, RATIO, SIZE, beats, captionAt, describe, editedWords, fullLook, fxAt, groupWords, pops, sig, speedAt } from '../../lib/clipLook';

// 🎬 Slice 29: one clip's editor. Captions (the words, their timing, font, colours, size, position, word-by-word highlight), a transition (cut,
// fade, zoom, whip, glitch) and effects (punch-in, shake, colour grade, speed ramp, word pop), from a preset or by hand, by the owner or the minds.
// The LIVE PREVIEW plays the clean upload in the browser with the look on top (instant, close to the file); RENDER makes the real file with ffmpeg
// on this machine ($0, no watermark). A look another clip already has can't be rendered: every clip looks its own.
const FMTS = [['story', '9:16'], ['feed', '1:1'], ['wide', '16:9']];
const MODE_TIP = { word: 'The word being said lights up', box: 'The word being said sits on a colour block', karaoke: 'Words fill with colour as they are said', plain: 'All one colour' };
const TR_TIP = { cut: 'Hard cuts', fade: 'Fade in, a dip at each new sentence, fade out', zoom: 'A zoom hit at each new sentence', whip: 'A whip blur at each new sentence', glitch: 'An RGB glitch at each new sentence' };
const FX = [['punch', 'Punch-in', 'Every other sentence zoomed in, like a jump cut'], ['shake', 'Shake', 'A short camera shake on the big words'], ['pop', 'Word pop', 'Numbers and big words pop up as stickers']];
const SPEED = [['off', '1×'], ['tight', '1.1×'], ['ramp', 'Ramp']];
const ago = at => { const m = Math.max(0, Math.round((Date.now() / 1000 - (at || 0)) / 60)); return m < 1 ? 'now' : m < 60 ? `${m} m` : m < 1440 ? `${Math.round(m / 60)} h` : `${Math.round(m / 1440)} d`; };

function Seg({ label, value, opts, onPick, tips, testid }) {
  return <div className="cse-field"><span className="m-label">{label}</span>
    <div className="m-seg" role="group" aria-label={label}>{opts.map(([k, l]) => <button key={k} type="button" aria-pressed={value === k} className={value === k ? 'active' : ''} onClick={() => onPick(k)} data-tip={tips?.[k]} data-testid={testid ? `${testid}-${k}` : undefined}>{l}</button>)}</div></div>;
}
function Swatches({ label, value, opts, onPick, testid }) {
  return <div className="cse-field"><span className="m-label">{label}</span><div className="cse-sw" role="group" aria-label={label}>{opts.map(k => <button key={k} type="button" aria-pressed={value === k} aria-label={k} className={value === k ? 'is-on' : ''} style={{ '--sw': COLOR[k] }} onClick={() => onPick(k)} data-tip={k} data-testid={testid ? `${testid}-${k}` : undefined} />)}</div></div>;
}

/** The look drawn over the playing clip: captions, the hook bar, pops, punch-in / shake / transition hits, the grade. */
function Preview({ look, ews, dur, t, fmt, w, hook, children }) {
  const a = fullLook(look); const groups = useMemo(() => groupWords(ews, a.cap.words), [ews, a.cap.words]);
  const bts = useMemo(() => beats(ews, dur), [ews, dur]); const pps = useMemo(() => pops(ews, dur), [ews, dur]);
  const cap = captionAt(groups, t); const fx = fxAt(a, t, bts, pps, dur); const px = BASE_PX[fmt] * SIZE[a.cap.size] * w;
  const up = a.cap.case === 'upper'; const hot = COLOR[a.cap.hot]; const base = COLOR[a.cap.color];
  const vstyle = { transform: `scale(${fx.zoom})${fx.shake ? ` translate(${Math.sin(t * 41) * 1.6}%, ${Math.cos(t * 37) * 1.1}%)` : ''}${fx.hit === 'whip' ? ` translateX(${Math.sin(t * 60) * 3}%)` : ''}`,
    filter: [GRADE_CSS[a.fx.grade], fx.hit === 'whip' ? 'blur(3px)' : '', fx.hit === 'glitch' ? 'drop-shadow(6px 0 0 rgb(255 0 80 / .55)) drop-shadow(-6px 0 0 rgb(0 220 255 / .55))' : ''].filter(x => x && x !== 'none').join(' ') || 'none', opacity: fx.fade };
  return <div className="cse-stage" style={{ aspectRatio: RATIO[fmt], '--cap-font': FONT_CSS[a.cap.font], '--cap-w': FONT_WEIGHT[a.cap.font], '--cap-px': `${px}px`, '--hot': hot, '--base': base }} data-testid="cse-stage">
    <div className="cse-vid" style={vstyle}>{children}</div>
    {t < 2.5 && hook ? <div className="cse-hook" style={{ top: `${{ story: 12, feed: 7, wide: 6 }[fmt]}%`, background: a.cap.hot === 'white' ? COLOR.green : hot, fontSize: `${px * 0.72}px` }}>{hook}</div> : null}
    {cap ? <div className={`cse-cap is-${a.cap.mode}`} style={{ top: `${POS[a.cap.pos] * 100}%` }} data-testid="cse-cap">{cap.g.map((x, i) => {
      const on = i === cap.hot; const said = a.cap.mode === 'karaoke' && i <= cap.hot;
      return <span key={`${x.i}-${i}`} className={on ? 'is-hot' : said ? 'is-said' : ''} style={{ color: (a.cap.mode === 'word' && on) || said ? hot : a.cap.mode === 'box' && on ? '#080c0a' : base }}>{up ? String(x.w).replace(/[^\w'’$%#@&!?.,-]/g, '').toUpperCase() || x.w : x.w}</span>;
    })}</div> : null}
    {fx.pop ? <motion.div key={fx.pop} className="cse-pop" initial={{ scale: 0.5, rotate: -7 }} animate={{ scale: 1, rotate: -5 }} transition={{ type: 'spring', stiffness: 520, damping: 14 }} style={{ background: a.cap.hot === 'white' ? COLOR.yellow : hot }}>{fx.pop}</motion.div> : null}
    {fx.hit === 'zoom' || fx.hit === 'glitch' ? <i className={`cse-flash is-${fx.hit}`} aria-hidden="true" /> : null}
  </div>;
}

export default function ClipEdit({ f, kit, run, api, busy, rendering, pick, onLook, onMind, onUndo, twin }) {
  const s = f.studio; const c = s.clip; const cur = useMemo(() => fullLook(s.look), [s.look]);
  const [draft, setDraft] = useState(cur); const [words, setWords] = useState(null); const [werr, setWerr] = useState(''); const [fmt, setFmt] = useState('story'); const [src, setSrc] = useState('live');
  const [t, setT] = useState(0); const [playing, setPlaying] = useState(false); const [w, setW] = useState(300); const [editI, setEditI] = useState(null); const [ask, setAsk] = useState('');
  const vid = useRef(null); const stageBox = useRef(null);
  useEffect(() => { setDraft(cur); }, [cur]);
  useEffect(() => { let on = true; setWords(null); setWerr(''); api(`/words?job=${encodeURIComponent(f.id)}`).then(j => on && setWords(j.words || [])).catch(e => on && setWerr(e.message)); return () => { on = false; }; }, [f.id, api]);
  useEffect(() => { const el = stageBox.current; if (!el || typeof ResizeObserver === 'undefined') return undefined; const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width))); ro.observe(el); return () => ro.disconnect(); }, []);
  const dur = c.dur || (c.e - c.s); const up = (run?.links || []).find(k => k.kind === 'upload' && !k.gone && !k.swept && (k.exp || 0) * 1000 > Date.now());
  const rendered = (s.files || []).find(x => x.piece === 'video' && x.format === fmt && x.url && !x.error);
  const live = src === 'live' && up && run?.converted?.url; const url = live ? `${apiUrl(run.converted.url)}#t=${c.s.toFixed(2)},${c.e.toFixed(2)}` : rendered ? apiUrl(rendered.url) : '';
  const off = live ? c.s : 0;
  useEffect(() => {   // the clip loops inside its window; the look follows the play head every frame
    const el = vid.current; if (!el) return undefined; let raf = 0;
    const tick = () => { const x = el.currentTime - off; if (live && x >= dur) { el.currentTime = off; } setT(Math.max(0, x)); if (live) el.playbackRate = speedAt(draft, x, dur); raf = requestAnimationFrame(tick); };
    const start = () => { setPlaying(true); cancelAnimationFrame(raf); raf = requestAnimationFrame(tick); }; const stop = () => { setPlaying(false); cancelAnimationFrame(raf); };
    const seek = () => { if (live && (el.currentTime < off - 0.2 || el.currentTime > off + dur)) el.currentTime = off; setT(Math.max(0, el.currentTime - off)); };
    el.addEventListener('play', start); el.addEventListener('pause', stop); el.addEventListener('loadedmetadata', seek); el.addEventListener('seeked', seek);
    return () => { cancelAnimationFrame(raf); el.removeEventListener('play', start); el.removeEventListener('pause', stop); el.removeEventListener('loadedmetadata', seek); el.removeEventListener('seeked', seek); };
  }, [url, live, off, dur, draft]);
  const ews = useMemo(() => editedWords(words || [], draft), [words, draft]);
  const capSet = p => setDraft(d => ({ ...d, preset: undefined, cap: { ...d.cap, ...p } })); const fxSet = p => setDraft(d => ({ ...d, preset: undefined, fx: { ...d.fx, ...p } }));
  const dirty = sig(draft) !== sig(cur) || JSON.stringify(draft.edit) !== JSON.stringify(cur.edit); const same = twin(draft);
  const fonts = kit?.fonts || { bold: 'Bold sans', impact: 'Impact', condensed: 'Condensed', rounded: 'Rounded', serif: 'Serif', chalk: 'Chalk' };
  const presets = kit?.presetLooks || {}; const locked = !!f.posted;
  const toggle = () => { const el = vid.current; if (!el) return; if (el.paused) el.play().catch(() => {}); else el.pause(); };
  const setWord = (i, v) => setDraft(d => ({ ...d, edit: { ...d.edit, w: { ...d.edit.w, [String(i)]: v } } }));
  const vs = (s.looks || []).slice().reverse();
  return <div className="cse" data-testid={`cse-${f.id}`}>
    <div className="cse-left">
      <div className="cse-head">{pick}<div className="m-seg" role="group" aria-label="Preview format">{FMTS.map(([k, l]) => <button key={k} type="button" aria-pressed={fmt === k} className={fmt === k ? 'active' : ''} onClick={() => setFmt(k)} data-testid={`cse-fmt-${k}`}>{l}</button>)}</div></div>
      <div className="cse-frame" ref={stageBox}>
        {src === 'live' && live ? <Preview look={draft} ews={ews} dur={dur} t={t} fmt={fmt} w={w} hook={s.hook}>
          <video ref={vid} key={url} src={url} muted playsInline preload="metadata" onClick={toggle} data-testid="cse-video" />
        </Preview> : <div className="cse-stage" style={{ aspectRatio: RATIO[fmt] }}>{rendered ? <video ref={vid} key={url} src={url} controls muted playsInline preload="metadata" data-testid="cse-rendered" /> : <span className="cst-nofile">not made</span>}</div>}
        <button type="button" className="cse-playbtn" onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} data-testid="cse-play">{playing ? <Pause size={16} /> : <Play size={16} />}</button>
      </div>
      <div className="cse-src">
        <div className="m-seg" role="group" aria-label="Show">{[['live', 'Live preview'], ['file', `Rendered · v${(s.looks || []).slice(-1)[0]?.v || 1}`]].map(([k, l]) => <button key={k} type="button" aria-pressed={src === k} className={src === k ? 'active' : ''} disabled={k === 'live' && !up} onClick={() => setSrc(k)} data-tip={k === 'live' ? 'Your clean upload with this look drawn on top, in the browser' : 'The real file ffmpeg made'} data-testid={`cse-src-${k}`}>{l}</button>)}</div>
        <small>{!up ? 'The upload this clip came from is gone (kept 7 days): you see the rendered file.' : src === 'live' ? `${t.toFixed(1)} / ${dur.toFixed(1)} s · the render is the true file` : 'The file that posts, as ffmpeg made it'}</small>
      </div>
      <ol className="cse-vers" aria-label="Look versions" data-testid="cse-vers">{vs.map(v => <li key={v.v} className={v.v === vs[0].v ? 'is-cur' : ''}>
        <em className="m-num">v{v.v}</em><span className={`cst-by is-${v.by}`}>{v.by}</span><small title={v.why}>{v.why || describe(v.look, fonts)}</small><small className="m-num">{ago(v.at)}</small>
        {v.v !== vs[0].v && !locked ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => onUndo(v.v)} data-tip={v.files ? 'Its files come straight back, no new render' : 'Renders it again'} data-testid={`cse-back-${v.v}`}><Undo2 size={11} /></button> : null}</li>)}</ol>
    </div>

    <div className="cse-right">
      <section className="cse-sec" aria-label="Presets"><h5><Wand2 size={12} /> Presets</h5>
        <div className="cse-presets">{Object.entries(presets).map(([k, p], i) => { const a = fullLook(p); return <button key={k} type="button" className={`cse-pre${draft.preset === k ? ' is-on' : ''}`} style={{ '--i': i, '--sw': COLOR[a.cap.hot], '--pf': FONT_CSS[a.cap.font] }} disabled={locked}
          onClick={() => setDraft(d => ({ ...fullLook(p), edit: d.edit, preset: k }))} data-tip={describe(p, fonts)} data-testid={`cse-pre-${k}`}><b>Aa</b><span>{k}</span><small>{a.tr}</small></button>; })}</div></section>

      <section className="cse-sec" aria-label="Captions"><h5>Captions</h5>
        <div className="cse-fonts" role="group" aria-label="Font">{Object.entries(fonts).map(([k, l]) => <button key={k} type="button" aria-pressed={draft.cap.font === k} className={draft.cap.font === k ? 'is-on' : ''} style={{ fontFamily: FONT_CSS[k], fontWeight: FONT_WEIGHT[k] }} disabled={locked} onClick={() => capSet({ font: k })} data-tip={l} data-testid={`cse-font-${k}`}>{l}</button>)}</div>
        <div className="cse-row">
          <Seg label="SIZE" value={draft.cap.size} opts={[['S', 'S'], ['M', 'M'], ['L', 'L']]} onPick={k => capSet({ size: k })} testid="cse-size" />
          <Seg label="WORDS" value={draft.cap.words} opts={[[1, '1'], [2, '2'], [3, '3']]} onPick={k => capSet({ words: k })} />
          <Seg label="CASE" value={draft.cap.case} opts={[['upper', 'AA'], ['said', 'Aa']]} onPick={k => capSet({ case: k })} />
        </div>
        <Seg label="HIGHLIGHT" value={draft.cap.mode} opts={[['word', 'Word'], ['box', 'Box'], ['karaoke', 'Karaoke'], ['plain', 'Plain']]} tips={MODE_TIP} onPick={k => capSet({ mode: k })} testid="cse-mode" />
        <Seg label="POSITION" value={draft.cap.pos} opts={[['top', 'Top'], ['mid', 'Middle'], ['low', 'Low'], ['bottom', 'Bottom']]} onPick={k => capSet({ pos: k })} testid="cse-pos" />
        <div className="cse-row"><Swatches label="TEXT" value={draft.cap.color} opts={kit?.colors || ['white', 'cream', 'yellow']} onPick={k => capSet({ color: k })} />
          <Swatches label="HIGHLIGHT COLOUR" value={draft.cap.hot} opts={kit?.hot || ['green', 'yellow', 'cyan', 'pink', 'orange', 'white']} onPick={k => capSet({ hot: k })} testid="cse-hot" /></div>
        <label className="cse-off"><span className="m-label">TIMING</span><input type="range" min={-1} max={1} step={0.05} value={draft.edit.off} disabled={locked} onChange={e => setDraft(d => ({ ...d, edit: { ...d.edit, off: Number(e.target.value) } }))} aria-label="Caption timing" data-testid="cse-off" /><em className="m-num">{draft.edit.off > 0 ? '+' : ''}{draft.edit.off.toFixed(2)} s</em></label>
        <div className="cse-words" aria-label="The words" data-testid="cse-words">{werr ? <small className="cst-err">{werr}</small> : !words ? <small className="cst-none"><Loader2 size={11} className="cst-spin" /> reading the words…</small>
          : words.map(x => { const v = draft.edit.w[String(x.i)] ?? x.w; return editI === x.i ? <input key={x.i} className="m-input cse-wi" autoFocus defaultValue={v} aria-label={`Word ${x.i + 1}`} data-testid={`cse-wi-${x.i}`}
            onBlur={e => { setWord(x.i, e.target.value.trim()); setEditI(null); }} onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur(); if (e.key === 'Escape') setEditI(null); }} />
            : <button key={x.i} type="button" disabled={locked} className={`cse-w${!v ? ' is-off' : v !== x.w ? ' is-ed' : ''}${t >= x.s + draft.edit.off && t < x.e + draft.edit.off ? ' is-now' : ''}`} onClick={() => setEditI(x.i)} data-tip={`${x.s.toFixed(1)} s · click to change, empty to drop`} data-testid={`cse-w-${x.i}`}>{v || x.w}</button>; })}
          {Object.keys(draft.edit.w).length ? <button type="button" className="m-btn cse-wreset" onClick={() => setDraft(d => ({ ...d, edit: { ...d.edit, w: {} } }))}><RotateCcw size={11} /> words as said</button> : null}</div>
      </section>

      <section className="cse-sec" aria-label="Transition and effects"><h5><Clapperboard size={12} /> Transition · effects</h5>
        <Seg label="TRANSITION" value={draft.tr} opts={(kit?.trans || ['cut', 'fade', 'zoom', 'whip', 'glitch']).map(k => [k, k[0].toUpperCase() + k.slice(1)])} tips={TR_TIP} onPick={k => setDraft(d => ({ ...d, preset: undefined, tr: k }))} testid="cse-tr" />
        <div className="cse-fx" role="group" aria-label="Effects">{FX.map(([k, l, tip]) => <button key={k} type="button" aria-pressed={draft.fx[k]} className={draft.fx[k] ? 'is-on' : ''} disabled={locked} onClick={() => fxSet({ [k]: !draft.fx[k] })} data-tip={tip} data-testid={`cse-fx-${k}`}><i aria-hidden="true" />{l}</button>)}</div>
        <div className="cse-field"><span className="m-label">GRADE</span><div className="cse-grades" role="group" aria-label="Colour grade">{(kit?.grades || Object.keys(GRADE_CSS)).map(k => <button key={k} type="button" aria-pressed={draft.fx.grade === k} className={draft.fx.grade === k ? 'is-on' : ''} disabled={locked} onClick={() => fxSet({ grade: k })} data-testid={`cse-grade-${k}`}><i style={{ filter: GRADE_CSS[k] }} aria-hidden="true" />{k}</button>)}</div></div>
        <Seg label="SPEED" value={draft.fx.speed} opts={SPEED} tips={{ off: 'Real time', tight: '10 % faster, sound kept in sync', ramp: '1.25× through the build-up, real time for the last 2.5 s' }} onPick={k => fxSet({ speed: k })} testid="cse-speed" />
      </section>

      <footer className="cse-go">
        <p className={`cse-uniq${same ? ' is-bad' : ''}`} data-testid="cse-uniq">{same ? `Same look as PoC #${same.n}: change one thing.` : <><Check size={12} /> No other clip looks like this.</>}</p>
        <div className="cse-btns">
          <button type="button" className="m-btn m-go" disabled={locked || !dirty || !!same || !!busy || rendering} onClick={() => onLook(draft, draft.preset ? `preset ${draft.preset}` : 'your edit')} data-tip="ffmpeg makes the 9:16, 1:1 and 16:9 files with this look, on this machine, $0" data-testid="cse-render">
            {busy === 'look' || rendering ? <><Loader2 size={13} className="cst-spin" /> Rendering…</> : <><Clapperboard size={13} /> Render</>}</button>
          <button type="button" className="m-btn" disabled={!dirty} onClick={() => setDraft(cur)}>Reset</button>
          <button type="button" className="m-btn" disabled={locked || !!busy || rendering} onClick={() => setDraft(d => ({ ...fullLook(DEFAULT_LOOK), edit: d.edit }))} data-tip="The plain look: white captions, green word, hard cuts">Plain</button>
        </div>
        <form className="cse-mind" onSubmit={e => { e.preventDefault(); onMind(ask); setAsk(''); }}>
          <input className="m-input" value={ask} onChange={e => setAsk(e.target.value)} placeholder="Ask the minds: funnier, calmer, more cinematic…" aria-label="What the minds should go for" disabled={locked} data-testid="cse-mind-ask" />
          <button type="submit" className="m-btn" disabled={locked || !!busy || rendering} data-tip="The lead PoC mind designs a look for this clip (never one another clip has), and it renders" data-testid="cse-mind">{busy === 'mind' ? <Loader2 size={13} className="cst-spin" /> : <Brain size={13} />} Minds pick</button>
        </form>
        {s.render?.state === 'failed' ? <small className="cst-err">Render failed: {s.render.err}</small> : s.render?.state === 'done' && s.render.secs ? <small className="cst-none">Last render: {s.render.secs} s, every format, $0.</small> : null}
      </footer>
    </div>
  </div>;
}

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Circle, Ellipse, Group, Image as KImage, Label, Layer, Rect, Stage, Star, Tag, Text, Transformer } from 'react-konva';
import { FRAMES, FRAME_KEYS, alpha, cropFor, frameLayers, history, newId, push, redo, reframe, reorder, undo } from '../../lib/pocPlay';
import '../../styles/pocPlay.css';

// 🎨 POC-PLAY (owner 2026-11-13): every PoC image / video opens here. Grab, move, resize, rotate, layer, crop, add text, shapes and badges,
// put it on a phone / billboard / shelf, undo / redo, export a PNG, or save it back into the proof as a NEW version (the original stays).
// Free: all of it runs in this browser (Konva, MIT); nothing is sent until you press Save. Loaded only when it opens (its own chunk).
const cssVar = n => { try { return getComputedStyle(document.body).getPropertyValue(n).trim(); } catch { return ''; } };
const tokens = () => ({ bg: cssVar('--m-bg') || 'black', text: cssVar('--m-text') || 'white', dim: cssVar('--m-dim') || 'gray', accent: cssVar('--m-accent') || 'lime',
  accentInk: cssVar('--m-accent-ink') || 'black', line: cssVar('--m-line-hi') || 'gray', ink: cssVar('--m-surface') || 'black', sky: cssVar('--m-surface-2') || 'gray',
  shade: 'rgba(0,0,0,.45)', clear: 'rgba(0,0,0,0)', glow: alpha(cssVar('--m-accent'), 0.18),
  note: cssVar('--m-warn') || 'gold', noteInk: cssVar('--m-bg') || 'black' });
const SWATCH_VARS = ['--m-text', '--m-accent', '--m-warn', '--m-danger', '--m-dim', '--m-bg'];

function loadImg(src) {
  return new Promise((res, rej) => { const i = new window.Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => rej(new Error('That picture would not load. Upload the file instead.')); i.src = src; });
}

function Node({ l, img, sel, onSel, onChange }) {
  const common = { id: l.id, x: l.x, y: l.y, rotation: l.rotation || 0, draggable: !l.deco, listening: !l.deco, onMouseDown: () => !l.deco && onSel(l.id), onTap: () => !l.deco && onSel(l.id),
    onDragEnd: e => onChange({ x: e.target.x(), y: e.target.y() }),
    onTransformEnd: e => { const n = e.target; const sx = n.scaleX(); const sy = n.scaleY(); n.scaleX(1); n.scaleY(1);
      const sized = l.type === 'circle' ? { radius: Math.max(4, (l.radius || 60) * Math.max(sx, sy)) } : l.type === 'text' || l.type === 'badge' ? { fontSize: Math.max(8, Math.round((l.fontSize || 40) * sy)), ...(l.width ? { width: Math.max(20, l.width * sx) } : {}) }
        : l.type === 'ellipse' ? { radiusX: Math.max(4, (l.radiusX || 60) * sx), radiusY: Math.max(4, (l.radiusY || 30) * sy) }
          : l.type === 'star' ? { outerRadius: Math.max(6, (l.outerRadius || 70) * Math.max(sx, sy)), innerRadius: Math.max(3, (l.innerRadius || 32) * Math.max(sx, sy)) }
          : { width: Math.max(8, (l.width || n.width()) * sx), height: Math.max(8, (l.height || n.height()) * sy) };
      onChange({ x: n.x(), y: n.y(), rotation: n.rotation(), ...sized }); } };
  if (l.type === 'image') return img ? <KImage {...common} image={img} width={l.width} height={l.height} crop={l.crop} cornerRadius={l.cornerRadius} stroke={sel ? undefined : l.stroke} /> : null;
  if (l.type === 'text') return <Text {...common} text={l.text} fontSize={l.fontSize} fontStyle={l.fontStyle || 'normal'} fontFamily={cssVar('--f-display') || 'sans-serif'} fill={l.fill} width={l.width} align={l.align || 'left'} />;
  if (l.type === 'rect') return <Rect {...common} width={l.width} height={l.height} fill={l.fill} cornerRadius={l.cornerRadius} stroke={l.stroke} strokeWidth={l.strokeWidth} shadowColor={l.shadowColor} shadowBlur={l.shadowBlur} shadowOffsetY={l.shadowOffsetY}
    fillLinearGradientStartPoint={l.fillLinearGradientStartPoint} fillLinearGradientEndPoint={l.fillLinearGradientEndPoint} fillLinearGradientColorStops={l.fillLinearGradientColorStops} />;
  if (l.type === 'circle') return <Circle {...common} radius={l.radius} fill={l.fill} />;
  if (l.type === 'ellipse') return <Ellipse {...common} radiusX={l.radiusX} radiusY={l.radiusY} fill={l.fill} />;
  if (l.type === 'star') return <Star {...common} numPoints={5} innerRadius={l.innerRadius || 32} outerRadius={l.outerRadius || 70} fill={l.fill} />;
  if (l.type === 'badge') return <Label {...common}><Tag fill={l.bg} cornerRadius={(l.fontSize || 40) * 0.6} /><Text text={l.text} fontSize={l.fontSize} fontStyle="bold" fontFamily={cssVar('--f-tech') || 'monospace'} fill={l.fill} padding={(l.fontSize || 40) * 0.35} /></Label>;
  if (l.type === 'note') return <Group {...common}><Rect width={l.width} height={l.height} fill={l.fill} cornerRadius={10} shadowColor="rgba(0,0,0,.35)" shadowBlur={18} shadowOffsetY={8} /><Text text={l.text} x={22} y={22} width={l.width - 44} fontSize={34} fontStyle="bold" fill={l.ink} fontFamily={cssVar('--f-ui') || 'sans-serif'} /></Group>;
  return null;
}

export default function PocPlay({ src, kind = 'image', from = null, title = 'Playground', media = [], onSave, onClose }) {
  const t = useMemo(tokens, []);
  const [frame, setFrame] = useState('free'); const [h, setH] = useState(() => history([])); const layers = h.now;
  const [sel, setSel] = useState(null); const [imgs, setImgs] = useState({}); const [main, setMain] = useState(null);
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(''); const [done, setDone] = useState(''); const [link, setLink] = useState('');
  const editBase = useRef(null); const boxRef = useRef(null); const stageRef = useRef(null); const trRef = useRef(null); const vidRef = useRef(null); const fileRef = useRef(null);
  const [box, setBox] = useState({ w: 600, h: 600 });
  const F = FRAMES[frame]; const scale = Math.min(box.w / F.w, box.h / F.h) || 0.5;
  const commit = useCallback(next => setH(x => push(x, typeof next === 'function' ? next(x.now) : next)), []);
  const remember = useCallback(async s => { if (imgs[s]) return imgs[s]; const i = await loadImg(s); setImgs(m => ({ ...m, [s]: i })); return i; }, [imgs]);

  useEffect(() => { const el = boxRef.current; if (!el) return undefined; const ro = new ResizeObserver(([e]) => setBox({ w: Math.max(200, e.contentRect.width), h: Math.max(240, e.contentRect.height) })); ro.observe(el); return () => ro.disconnect(); }, []);
  // the proof's own picture (a video starts from its first frame; pick any other frame with "Grab this frame")
  useEffect(() => { if (kind === 'video' || !src) return; let live = true; loadImg(src).then(i => { if (!live) return; setImgs(m => ({ ...m, [src]: i })); const m = { src, w: i.naturalWidth, h: i.naturalHeight }; setMain(m); setH(history(frameLayers('free', m, t))); }).catch(e => live && setErr(e.message)); return () => { live = false; }; }, [src, kind, t]);
  useEffect(() => { const tr = trRef.current; const st = stageRef.current; if (!tr || !st) return; const n = sel ? st.findOne(`#${sel}`) : null; tr.nodes(n ? [n] : []); tr.getLayer()?.batchDraw(); }, [sel, layers]);

  const grabFrame = useCallback(async (asMain = true) => {
    const v = vidRef.current; if (!v || !v.videoWidth) return;
    const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext('2d').drawImage(v, 0, 0);
    let url; try { url = c.toDataURL('image/png'); } catch { setErr('This video does not allow reuse. Download it and upload the file.'); return; }
    const i = await remember(url); const m = { src: url, w: i.naturalWidth, h: i.naturalHeight };
    if (asMain || !main) { setMain(m); commit(ls => reframe(ls, frame, m, t)); } else commit(ls => [...ls, { id: newId('i'), type: 'image', user: true, src: url, ...fitHalf(m) }]);
  }, [remember, main, frame, t, commit]); // eslint-disable-line react-hooks/exhaustive-deps
  const fitHalf = m => { const s = Math.min(F.w * 0.5 / m.w, F.h * 0.5 / m.h, 1); return { x: F.w * 0.25, y: F.h * 0.25, width: m.w * s, height: m.h * s }; };

  const pickFrame = k => { setFrame(k); setSel(null); commit(ls => reframe(ls, k, main, t)); };
  const change = (id, p) => commit(ls => ls.map(l => (l.id === id ? { ...l, ...p } : l)));
  const selL = layers.find(l => l.id === sel);
  const add = l => { const id = newId(l.type[0]); commit(ls => [...ls, { id, user: true, x: F.w / 2 - 150, y: F.h / 2 - 60, ...l }]); setSel(id); };
  const addImage = async s => { setErr(''); try { const i = await remember(s); const m = { src: s, w: i.naturalWidth, h: i.naturalHeight }; if (!main) { setMain(m); commit(ls => reframe(ls, frame, m, t)); } else add({ type: 'image', src: s, ...fitHalf(m) }); } catch (e) { setErr(e.message); } };
  const onFile = e => { const f = e.target.files?.[0]; e.target.value = ''; if (!f) return; if (!/^image\//.test(f.type)) { setErr('Pick a picture file.'); return; } const r = new FileReader(); r.onload = () => addImage(String(r.result)); r.readAsDataURL(f); };
  const del = () => { if (!selL || selL.deco) return; commit(ls => ls.filter(l => l.id !== sel)); if (selL.main) setMain(null); setSel(null); };
  const dup = () => { if (!selL || selL.deco) return; const id = newId('c'); commit(ls => [...ls, { ...selL, id, main: false, user: true, x: selL.x + 30, y: selL.y + 30 }]); setSel(id); };
  const crop = aspect => { if (selL?.type !== 'image') return; const i = imgs[selL.src]; if (!i) return; const c = cropFor(i.naturalWidth, i.naturalHeight, aspect); const s = (selL.width * selL.height) ** 0.5 / (c.width * c.height) ** 0.5; change(sel, { crop: c, width: c.width * s, height: c.height * s }); };

  useEffect(() => {
    const k = e => { if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return; const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); setH(x => (e.shiftKey ? redo(x) : undo(x))); } else if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); setH(redo); }
      else if ((e.key === 'Delete' || e.key === 'Backspace') && sel) { e.preventDefault(); del(); } else if (e.key === 'Escape') { if (sel) setSel(null); else onClose?.(); }
      else if (sel && e.key.startsWith('Arrow') && selL && !selL.deco) { e.preventDefault(); const d = e.shiftKey ? 20 : 4; change(sel, { x: selL.x + (e.key === 'ArrowLeft' ? -d : e.key === 'ArrowRight' ? d : 0), y: selL.y + (e.key === 'ArrowUp' ? -d : e.key === 'ArrowDown' ? d : 0) }); } };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }); // re-binds each render so it sees the newest selection

  const exportUrl = () => { setSel(null); trRef.current?.nodes([]); return stageRef.current.toDataURL({ pixelRatio: 1 / scale, mimeType: 'image/png' }); };
  const download = () => { setErr(''); try { const a = document.createElement('a'); a.href = exportUrl(); a.download = `feeless-${frame}.png`; a.click(); } catch { setErr('A picture from another site blocks the export. Upload that file instead of linking it.'); } };
  const save = async () => { setErr(''); setDone(''); let url; try { url = exportUrl(); } catch { setErr('A picture from another site blocks the export. Upload that file instead of linking it.'); return; }
    setBusy('save'); try { await onSave?.(url, frame, from); setDone('Saved into the proof as a new version. The original stays.'); } catch (e) { setErr(e.message); } setBusy(''); };

  const swatches = SWATCH_VARS.map(cssVar).filter(Boolean);
  return <div className="ppl" role="dialog" aria-modal="true" aria-label={`Playground: ${title}`} data-testid="poc-play">
    <header className="ppl-top">
      <span className="ppl-title"><small className="m-label">PLAYGROUND</small><b>{title}</b></span>
      <nav className="ppl-frames" aria-label="Frame">{FRAME_KEYS.map(k => <button key={k} type="button" className={frame === k ? 'is-on' : ''} aria-pressed={frame === k} onClick={() => pickFrame(k)} data-tip={FRAMES[k].tip} data-testid={`ppl-frame-${k}`}>{FRAMES[k].label}</button>)}</nav>
      <span className="ppl-acts">
        <button type="button" className="m-btn ppl-ic" disabled={!h.past.length} onClick={() => setH(undo)} data-tip="Undo (⌘Z)" aria-label="Undo" data-testid="ppl-undo">↶</button>
        <button type="button" className="m-btn ppl-ic" disabled={!h.future.length} onClick={() => setH(redo)} data-tip="Redo (⇧⌘Z)" aria-label="Redo" data-testid="ppl-redo">↷</button>
        <button type="button" className="m-btn" onClick={download} data-tip="Download this as a PNG" data-testid="ppl-png">PNG</button>
        {onSave ? <button type="button" className="m-btn m-go" disabled={!!busy || !layers.length} onClick={save} data-tip="Files it into this proof as a new version. The original stays." data-testid="ppl-save">{busy === 'save' ? 'Saving…' : 'Save to proof'}</button> : null}
        <button type="button" className="m-btn" onClick={onClose} aria-label="Close" data-tip="Close (Esc)" data-testid="ppl-close">✕</button>
      </span>
    </header>
    <div className="ppl-body">
      <div className="ppl-stage" ref={boxRef}>
        {kind === 'video' && !main ? <p className="ppl-hint">Pick the moment, then <b>Grab this frame</b>.</p> : null}
        <Stage ref={stageRef} width={F.w * scale} height={F.h * scale} scaleX={scale} scaleY={scale} className="ppl-canvas"
          onMouseDown={e => { if (e.target === e.target.getStage()) setSel(null); }} onTouchStart={e => { if (e.target === e.target.getStage()) setSel(null); }}>
          <Layer>{layers.map(l => <Node key={l.id} l={l} img={l.src ? imgs[l.src] : null} sel={sel === l.id} onSel={setSel} onChange={p => change(l.id, p)} />)}
            <Transformer ref={trRef} rotateEnabled keepRatio={selL?.type === 'image'} anchorSize={14} borderStroke={t.accent} anchorStroke={t.accent} anchorFill={t.bg} /></Layer>
        </Stage>
      </div>
      <aside className="ppl-side">
        {kind === 'video' ? <section className="ppl-sec"><span className="m-label">VIDEO</span>
          <video ref={vidRef} src={src} crossOrigin="anonymous" controls playsInline preload="auto" className="ppl-vid" onLoadedData={() => !main && grabFrame(true)} data-testid="ppl-video" />
          <span className="ppl-row"><button type="button" className="m-btn m-go" onClick={() => grabFrame(true)} data-tip="This moment becomes the main picture" data-testid="ppl-grab">Grab this frame</button>
            <button type="button" className="m-btn" disabled={!main} onClick={() => grabFrame(false)} data-tip="Add this moment as one more picture">+ as layer</button></span></section> : null}
        <section className="ppl-sec"><span className="m-label">ADD</span>
          <span className="ppl-grid">
            <button type="button" className="m-btn" onClick={() => add({ type: 'text', text: 'Your words', fontSize: 72, fontStyle: 'bold', fill: t.text, width: 600 })} data-testid="ppl-add-text" data-tip="A line of text">Text</button>
            <button type="button" className="m-btn" onClick={() => add({ type: 'rect', width: 300, height: 200, cornerRadius: 16, fill: t.accent })} data-testid="ppl-add-rect" data-tip="A box">Box</button>
            <button type="button" className="m-btn" onClick={() => add({ type: 'circle', radius: 110, fill: t.accent })} data-tip="A circle">Circle</button>
            <button type="button" className="m-btn" onClick={() => add({ type: 'star', outerRadius: 120, innerRadius: 52, fill: t.note })} data-tip="A star">Star</button>
            {['NEW', 'SALE', 'LIVE', '-50%'].map(b => <button key={b} type="button" className="m-btn" onClick={() => add({ type: 'badge', text: b, fontSize: 48, fill: t.accentInk, bg: t.accent })} data-testid={`ppl-badge-${b}`} data-tip={`A ${b} badge`}>{b}</button>)}
            <button type="button" className="m-btn" onClick={() => add({ type: 'note', width: 340, height: 240, text: 'An idea', fill: t.note, ink: t.noteInk })} data-tip="A sticky note">Note</button>
          </span>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={onFile} data-testid="ppl-file" />
          <span className="ppl-row"><button type="button" className="m-btn" onClick={() => fileRef.current?.click()} data-tip="Upload a product, logo or reference picture">Upload picture</button></span>
          <form className="ppl-row" onSubmit={e => { e.preventDefault(); if (/^https?:\/\//.test(link.trim())) { addImage(link.trim()); setLink(''); } else setErr('Paste a link that starts with https://'); }}>
            <input className="m-input" value={link} onChange={e => setLink(e.target.value)} placeholder="…or paste a picture link" aria-label="Picture link" data-testid="ppl-link" /><button type="submit" className="m-btn">Add</button></form>
          {media.length ? <span className="ppl-thumbs" aria-label="This proof's pictures">{media.filter(m => m.kind !== 'video' && m.url).slice(0, 8).map(m => <button key={m.id} type="button" onClick={() => addImage(m.url)} data-tip={m.label || 'Add this picture'}><img src={m.url} alt="" /></button>)}</span> : null}
        </section>
        <section className="ppl-sec" data-testid="ppl-selected"><span className="m-label">{selL ? `SELECTED · ${selL.type.toUpperCase()}` : 'SELECTED'}</span>
          {!selL ? <p className="ppl-note">Click anything on the canvas to move, resize or rotate it. Delete removes it; arrows nudge it.</p> : <>
            {selL.type === 'text' || selL.type === 'badge' || selL.type === 'note' ? <input className="m-input" value={selL.text} onFocus={() => { editBase.current = layers; }} onChange={e => setH(x => ({ ...x, now: x.now.map(l => (l.id === sel ? { ...l, text: e.target.value } : l)) }))}
              onBlur={() => { const base = editBase.current; editBase.current = null; if (base && base !== layers) setH(x => ({ past: [...x.past, base].slice(-60), now: x.now, future: [] })); }} aria-label="Text" data-testid="ppl-text" /> : null}
            {selL.type !== 'image' ? <span className="ppl-sw" role="radiogroup" aria-label="Colour">{swatches.map(c => <button key={c} type="button" role="radio" aria-checked={selL.fill === c} style={{ background: c }} onClick={() => change(sel, selL.type === 'badge' ? { bg: c } : { fill: c })} aria-label={`Colour ${c}`} />)}</span> : null}
            {selL.type === 'image' ? <span className="ppl-grid"><span className="ppl-note">Crop</span>{[['1:1', 1], ['4:5', 0.8], ['16:9', 16 / 9], ['9:16', 9 / 16]].map(([n, a]) => <button key={n} type="button" className="m-btn" onClick={() => crop(a)} data-testid={`ppl-crop-${n}`} data-tip={`Crop it to ${n}`}>{n}</button>)}
              <button type="button" className="m-btn" onClick={() => change(sel, { crop: undefined })} data-tip="Back to the whole picture">Full</button></span> : null}
            <span className="ppl-grid">
              <button type="button" className="m-btn" onClick={() => commit(ls => reorder(ls, sel, 'front'))} data-tip="Bring to front" data-testid="ppl-front">Front</button>
              <button type="button" className="m-btn" onClick={() => commit(ls => reorder(ls, sel, 'up'))} data-tip="One layer up">Up</button>
              <button type="button" className="m-btn" onClick={() => commit(ls => reorder(ls, sel, 'down'))} data-tip="One layer down">Down</button>
              <button type="button" className="m-btn" onClick={dup} data-tip="Make a copy" data-testid="ppl-dup">Copy</button>
              <button type="button" className="m-btn danger" onClick={del} data-tip="Delete (⌫)" data-testid="ppl-del">Delete</button>
            </span></>}
        </section>
        {err ? <p className="ppl-err" role="alert" data-testid="ppl-err">{err}</p> : null}
        {done ? <p className="ppl-ok" role="status" data-testid="ppl-done">{done}</p> : null}
      </aside>
    </div>
  </div>;
}

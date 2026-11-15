import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Excalidraw, MainMenu, convertToExcalidrawElements, exportToBlob, restoreElements } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import '../../styles/pocWire.css';

// 🧩 THE POC WIREFRAME BOARD (owner 2026-11-13: "a live canvas wireframe for their AI images and videos … wireframe a week of content";
// 2026-11-14: "a true live realtime wireframe from a good free and new source"). Excalidraw (MIT, free, open source): an infinite live canvas,
// frames, shapes, arrows, text, images, its own wireframe libraries, undo / redo, zoom, dark mode, export PNG / SVG. It opens with the picture already
// placed in a phone post, a square post and a billboard frame, plus a Mon–Sun week of empty post frames to plan around it. Save files ONE frame (or
// the whole board) back into the proof as a NEW version; the original stays. The board itself is kept in this browser per picture.
export const FRAMES = [['phone', 'Phone post 9:16', 270, 480], ['square', 'Square post 1:1', 360, 360], ['billboard', 'Billboard 16:9', 640, 360]];
export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const WEEK_Y = 560;   // the week row sits under the tallest frame (phone, 480)
const KEY = id => `feeless:pocwire:${id}`;

// The starting board, as Excalidraw skeletons. Pure (tested): frames in a row, the picture fitted inside each, the week below.
export function startBoard(fileId, w = 1, h = 1, title = 'Picture') {
  const out = []; let x = 0;
  FRAMES.forEach(([k, label, fw, fh]) => {
    const r = Math.min((fw - 24) / w, (fh - 24) / h); const iw = Math.round(w * r); const ih = Math.round(h * r);
    const img = `img-${k}`;
    const scr = `screen-${k}`;   // the frame's full screen: Excalidraw sizes a frame to its children, so this keeps the true 9:16 / 1:1 / 16:9 shape
    out.push({ type: 'rectangle', id: scr, x, y: 0, width: fw, height: fh, roundness: { type: 3 } });
    if (fileId) out.push({ type: 'image', id: img, fileId, x: x + (fw - iw) / 2, y: (fh - ih) / 2, width: iw, height: ih });
    out.push({ type: 'frame', id: `frame-${k}`, name: `${label} · ${title}`.slice(0, 60), children: fileId ? [scr, img] : [scr], x, y: 0, width: fw, height: fh });
    x += fw + 60;
  });
  DAYS.forEach((d, i) => {
    const fx = i * 190; const id = `day-${d}`;
    out.push({ type: 'rectangle', id: `${id}-card`, x: fx, y: WEEK_Y, width: 170, height: 210, strokeColor: 'transparent' });   // keeps the day frame full size
    out.push({ type: 'rectangle', id: `${id}-post`, x: fx + 12, y: WEEK_Y + 12, width: 146, height: 146, strokeStyle: 'dashed', label: { text: 'post' } });
    out.push({ type: 'rectangle', id: `${id}-cap`, x: fx + 12, y: WEEK_Y + 164, width: 146, height: 34, strokeColor: 'transparent', label: { text: 'caption · time', fontSize: 13, fontFamily: 2, strokeColor: 'black' } });   // a label, so it is measured once the font loads
    out.push({ type: 'frame', id, name: `${d} · week of content`, children: [`${id}-card`, `${id}-post`, `${id}-cap`], x: fx, y: WEEK_Y, width: 170, height: 210 });
  });
  return out;
}

// Excalidraw's dark theme inverts the canvas colours, so a white board shows near-black in dark mode and exports the same way.
const BOARD = 'white';
const toDataUrl = blob => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = no; r.readAsDataURL(blob); });
const sizeOf = url => new Promise(ok => { const i = new Image(); i.onload = () => ok([i.naturalWidth || 1, i.naturalHeight || 1]); i.onerror = () => ok([1, 1]); i.src = url; });

export default function PocWire({ src, kind = 'image', from = null, title = 'Picture', onSave, onClose }) {
  const [init, setInit] = useState(null); const [err, setErr] = useState(''); const [done, setDone] = useState(''); const [busy, setBusy] = useState('');
  const api = useRef(null); const dark = useMemo(() => !document.documentElement.classList.contains('light'), []);
  useEffect(() => {   // the saved board for this picture, else a fresh one with the picture placed in every frame
    let on = true;
    (async () => {
      try { const kept = JSON.parse(localStorage.getItem(KEY(from)) || 'null'); if (kept?.elements?.length) { if (on) setInit({ ...kept, appState: { ...(kept.appState || {}), collaborators: new Map() }, scrollToContent: true }); return; } } catch { /* a blocked or empty store: start fresh */ }
      let files = {}; let fileId = null; let wh = [1, 1];
      if (src && kind === 'image') {
        try { const blob = await (await fetch(src)).blob(); const dataURL = await toDataUrl(blob); wh = await sizeOf(dataURL); fileId = `poc-${from || 'pic'}`; files = { [fileId]: { id: fileId, dataURL, mimeType: blob.type || 'image/png', created: Date.now() } }; }
        catch { if (on) setErr('The picture could not be read here, so the board starts without it. Add it with the image tool.'); }
      }
      if (on) setInit({ elements: convertToExcalidrawElements(startBoard(fileId, wh[0], wh[1], title)), files, appState: { viewBackgroundColor: BOARD }, scrollToContent: true });
    })();
    return () => { on = false; };
  }, [src, kind, from, title]);
  const ready = a => {   // fit the board in view; once Excalidraw's hand font is in, re-measure the text (it was measured with a fallback font)
    api.current = a;
    setTimeout(() => { try { a.scrollToContent(undefined, { fitToContent: true }); } catch { /* opens where it was */ } }, 60);
    Promise.race([document.fonts?.load('20px Excalifont', 'caption · time post Mon Sun'), new Promise(r => setTimeout(r, 3000))]).then(() => {
      try { if (api.current === a) a.updateScene({ elements: restoreElements(a.getSceneElements(), null, { refreshDimensions: true }) }); } catch { /* the board still works */ }
    }, () => {});
  };
  const keep = (elements, appState, files) => { try { localStorage.setItem(KEY(from), JSON.stringify({ elements, files, appState: { viewBackgroundColor: appState.viewBackgroundColor } })); } catch { /* full or blocked: the board still works */ } };
  const exportPick = async () => {   // the selected frame, or the whole board when none is selected
    const a = api.current; if (!a) throw new Error('The board is still opening.');
    const all = a.getSceneElements(); const sel = a.getAppState().selectedElementIds || {};
    const frame = all.find(e => e.type === 'frame' && sel[e.id]);
    const elements = frame ? all.filter(e => e.id === frame.id || e.frameId === frame.id) : all;
    const blob = await exportToBlob({ elements, files: a.getFiles(), appState: { ...a.getAppState(), exportBackground: true, exportWithDarkMode: dark, viewBackgroundColor: a.getAppState().viewBackgroundColor || BOARD }, mimeType: 'image/png', exportPadding: frame ? 0 : 24 });
    return [await toDataUrl(blob), frame?.name || 'board'];
  };
  const save = async () => {
    setErr(''); setDone(''); setBusy('save');
    try { const [url, name] = await exportPick(); await onSave?.(url, 'wire', from); setDone(`Saved "${name}" into the proof as a new version. The original stays.`); } catch (e) { setErr(e.message || 'Could not export the board.'); }
    setBusy('');
  };
  const download = async () => {
    setErr(''); try { const [url, name] = await exportPick(); const a = document.createElement('a'); a.href = url; a.download = `${String(name).replace(/[^\w-]+/g, '-').slice(0, 40)}.png`; a.click(); } catch (e) { setErr(e.message || 'Could not export the board.'); }
  };
  return <div className="pwr" role="dialog" aria-modal="true" aria-label={`Wireframe board: ${title}`} data-testid="poc-wire">
    <header className="pwr-h"><span><b>🧩 WIREFRAME BOARD</b><small>Live canvas (Excalidraw, free and open source). Select a frame, then Save files just that frame. Your board stays in this browser.</small></span>
      <span className="pwr-acts"><button type="button" className="m-btn" disabled={!init || !!busy} onClick={download} data-tip="Downloads the selected frame, or the whole board, as a PNG" data-testid="pwr-download">Download PNG</button>
        <button type="button" className="m-btn m-go" disabled={!init || !!busy} onClick={save} data-tip="Files the selected frame (or the whole board) into the proof as a new version" data-testid="pwr-save">{busy === 'save' ? 'Saving…' : 'Save to proof'}</button>
        <button type="button" className="m-btn" onClick={onClose} aria-label="Close" data-tip="Close" data-testid="pwr-close">✕</button></span></header>
    {err ? <p className="pwr-note is-bad" role="alert">⚠ {err}</p> : done ? <p className="pwr-note" role="status" data-testid="pwr-done">{done}</p> : null}
    <div className="pwr-stage">{init ? <Excalidraw initialData={init} excalidrawAPI={ready} theme={dark ? 'dark' : 'light'} onChange={keep} name={title}
      UIOptions={{ canvasActions: { loadScene: false, saveToActiveFile: false } }}><MainMenu><MainMenu.DefaultItems.Export /><MainMenu.DefaultItems.SaveAsImage /><MainMenu.DefaultItems.ClearCanvas /><MainMenu.DefaultItems.ToggleTheme /><MainMenu.DefaultItems.ChangeCanvasBackground /></MainMenu></Excalidraw>
      : <p className="pwr-wait" role="status">Opening the board…</p>}</div>
  </div>;
}

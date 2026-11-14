import React, { useCallback, useRef, useState } from 'react';
import '../../styles/chatSize.css';

// ↕ AGX-3 · THE CHAT BOX YOU CAN SIZE (owner 2026-11-14): three sizes — Dock (small, the monitors lead), Half (today's size, the default) and
// Focus (the chat takes the desk; the monitors shrink to a strip) — or drag the top edge to any height. Double-click the chat's header = Focus
// (again = back). Remembered for this person on this browser (localStorage, try/catch: a private window just forgets).
export const SIZES = [['dock', 'Dock', 'Small chat: the monitors lead'], ['half', 'Half', 'The usual size'], ['focus', 'Focus', 'The chat takes the desk; the monitors shrink to a strip']];
const KEY = 'feeless-chat-size';
const MIN = 260;

/** Pure: a stored value → a safe size. Anything odd falls back to Half. */
export function readSize(raw) {
  try { const v = JSON.parse(raw || 'null'); if (v && SIZES.some(([k]) => k === v.mode)) return { mode: v.mode, h: null, back: v.back && v.back !== 'focus' ? v.back : 'half' };
    if (v && v.mode === 'custom' && Number(v.h) >= MIN) return { mode: 'custom', h: Math.round(Number(v.h)), back: 'half' }; } catch { /* bad JSON: default */ }
  return { mode: 'half', h: null, back: 'half' };
}
/** Pure: a dragged height, kept between MIN and the screen less room for the page's header. */
export const clampH = (h, screen) => Math.round(Math.max(MIN, Math.min(Number(h) || MIN, Math.max(MIN, (Number(screen) || 900) - 120))));

export function useChatSize() {
  const [s, setS] = useState(() => { try { return readSize(localStorage.getItem(KEY)); } catch { return readSize(null); } });
  const save = useCallback(next => { setS(next); try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private window: this visit only */ } }, []);
  const pick = useCallback(mode => save({ mode, h: null, back: mode === 'focus' ? (s.mode === 'focus' ? s.back : (s.mode === 'custom' ? 'half' : s.mode)) : s.back }), [s, save]);
  const toggleFocus = useCallback(() => (s.mode === 'focus' ? pick(s.back || 'half') : pick('focus')), [s, pick]);
  const drag = useCallback(h => save({ mode: 'custom', h: clampH(h, window.innerHeight), back: 'half' }), [save]);
  return { size: s, pick, toggleFocus, drag, attrs: { 'data-chat': s.mode, style: s.mode === 'custom' ? { '--cwb-h': `${s.h}px` } : undefined } };
}

/** The top edge: drag it up for a taller chat, down for a smaller one. Mouse, pen and touch (pointer events). Keyboard: ↑ / ↓ by 40 px. */
export function ChatGrip({ measure, onDrag }) {
  const start = useRef(null); const [live, setLive] = useState(null);
  const height = () => Number(measure?.()) || 480;
  const down = e => { e.preventDefault(); const box = e.currentTarget.parentElement; const k = box && box.offsetHeight ? box.getBoundingClientRect().height / box.offsetHeight : 1;   // the desk can be drawn scaled: screen px → layout px
    start.current = { y: e.clientY, h: height(), k: k > 0.2 && k < 5 ? k : 1 }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const at = e => clampH(start.current.h - (e.clientY - start.current.y) / start.current.k, window.innerHeight);
  const move = e => { if (!start.current) return; setLive(at(e)); };
  const up = e => { if (!start.current) return; const h = at(e); start.current = null; setLive(null); onDrag(h); };
  const key = e => { if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); onDrag(height() + (e.key === 'ArrowUp' ? 40 : -40)); } };
  return <div className={`csz-grip${live ? ' is-drag' : ''}`} role="separator" aria-orientation="horizontal" aria-label="Drag to resize the chat" tabIndex={0}
    onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={() => { start.current = null; setLive(null); }} onKeyDown={key}
    data-tip="Drag up or down to size the chat (or ↑ / ↓)" data-testid="csz-grip"><i aria-hidden="true" />{live ? <b className="m-num">{live}px</b> : null}</div>;
}

export function ChatSizeSeg({ size, pick }) {
  return <span className="m-seg csz-seg" role="radiogroup" aria-label="Chat size">{SIZES.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={size.mode === k}
    className={size.mode === k ? 'active' : ''} onClick={() => pick(k)} data-tip={tip} data-testid={`csz-${k}`}>{l}</button>)}</span>;
}

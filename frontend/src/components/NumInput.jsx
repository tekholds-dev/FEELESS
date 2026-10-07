import React, { useLayoutEffect, useRef, useState } from 'react';

// THE number box: shows thousands commas while you type (1,250,000.5) and hands plain digits ("1250000.5") to onChange / onBlur,
// so every caller keeps parsing with Number(e.target.value). Use it instead of <input type="number"> / inputMode="decimal".
export const stripNum = v => String(v ?? '').replace(/,/g, '');
export const commaNum = v => {
  const raw = stripNum(v);
  if (raw === '' || !/^-?\d*\.?\d*$/.test(raw)) return String(v ?? '');
  const neg = raw.startsWith('-'); const [int, dec] = (neg ? raw.slice(1) : raw).split('.');
  return `${neg ? '-' : ''}${int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}${raw.includes('.') ? `.${dec || ''}` : ''}`;
};
const sameNum = (a, b) => a === b || (Number.isFinite(Number(a)) && Number.isFinite(Number(b)) && Number(a) === Number(b));
const clean = (s, strict) => { let r = stripNum(s); if (!strict) return r; r = r.replace(/[^0-9.-]/g, '').replace(/(?!^)-/g, ''); const i = r.indexOf('.'); return i < 0 ? r : r.slice(0, i + 1) + r.slice(i + 1).replace(/\./g, ''); };

export default function NumInput({ value, defaultValue, onChange, onBlur, onFocus, onKeyDown, type, min, max, step, inputMode, placeholder, ...props }) {
  const strict = type === 'number'; const controlled = value !== undefined;
  const [draft, setDraft] = useState(() => stripNum(controlled ? value : defaultValue));
  const [focused, setFocused] = useState(false);
  const ref = useRef(null); const caret = useRef(null);
  const prop = stripNum(value);
  const raw = controlled ? (focused && sameNum(draft, prop) ? draft : prop) : draft;
  const shown = commaNum(raw);
  useLayoutEffect(() => {   // keep the caret after the same digit when a comma appears / goes
    const el = ref.current; if (caret.current == null || !el || document.activeElement !== el) return;
    let n = caret.current, i = 0; caret.current = null;
    while (i < shown.length && n > 0) { if (shown[i] !== ',') n -= 1; i += 1; }
    try { el.setSelectionRange(i, i); } catch (_) { /* not a text box */ }
  });
  const ev = v => { const t = { value: v, name: props.name, id: props.id, valueAsNumber: v === '' ? NaN : Number(v) }; return { target: t, currentTarget: t, preventDefault() {}, stopPropagation() {} }; };
  const send = v => { setDraft(v); onChange?.(ev(v)); };
  const change = e => { const el = e.target; caret.current = stripNum(el.value.slice(0, el.selectionStart ?? el.value.length)).length; send(clean(el.value, strict)); };
  const key = e => {
    onKeyDown?.(e);
    if (!strict || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
    const st = Number(step) > 0 ? Number(step) : 1; const d = (String(st).split('.')[1] || '').length;
    let n = (Number(raw) || 0) + (e.key === 'ArrowUp' ? st : -st);
    if (min !== undefined && min !== '' && n < Number(min)) n = Number(min);
    if (max !== undefined && max !== '' && n > Number(max)) n = Number(max);
    e.preventDefault(); send(String(Number(n.toFixed(Math.max(d, (raw.split('.')[1] || '').length)))));
  };
  return <input ref={ref} {...props} type="text" inputMode={inputMode || (strict && !String(step ?? '').includes('.') && step !== 'any' ? 'numeric' : 'decimal')} autoComplete={props.autoComplete || 'off'} placeholder={placeholder == null ? undefined : commaNum(placeholder)}
    value={shown} onChange={change} onKeyDown={key}
    onFocus={e => { setFocused(true); if (controlled) setDraft(prop); onFocus?.(e); }}
    onBlur={() => { setFocused(false); onBlur?.(ev(raw)); }} />;
}

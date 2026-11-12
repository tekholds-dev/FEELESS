import React, { useEffect, useRef, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import '../styles/actBtn.css';

// 🔘 ONE honest button (owner 2026-11-12): press ring → (money: a 2nd tap within 3.5 s) → busy spinner → ✓ ONLY when the server said OK,
// else a shake + the server's own reason in a toast. `run` returns a fetch Response (checked here) or anything else / throws.

/** fetch Response → its JSON, or throw the server's own reason (FastAPI `detail`, else `HTTP <code>`). */
export async function serverJson(r) {
  let d = null; try { d = await r.json(); } catch { /* empty body */ }
  if (!r.ok) throw new Error((d && (typeof d.detail === 'string' ? d.detail : d.detail?.[0]?.msg || d.error)) || `Server said no (HTTP ${r.status})`);
  return d;
}

// 🔘 twoTap(msg): the drop-in for window.confirm(msg) on any existing button (owner 2026-11-12: no native dialogs; money = 2 taps within 3.5 s).
// The 1st tap arms THAT button (amber pulse) and says what the 2nd tap does; the 2nd tap on the same button returns true. Keyed by the pressed
// button + the message without its numbers, so a live price ticking between taps never blocks it and two buttons never cross. Tests that mock
// window.confirm keep driving it.
let lastBtn = null; let armed = null;
if (typeof window !== 'undefined') window.addEventListener('pointerdown', e => { lastBtn = e.target?.closest?.('button,[role="button"]') || null; }, true);
export function twoTap(msg) {
  if (typeof window.confirm === 'function' && 'mock' in window.confirm) return window.confirm(msg);
  const el = (document.activeElement?.tagName === 'BUTTON' ? document.activeElement : null) || lastBtn;
  const key = String(msg).replace(/[\d.,$~%+−-]+/g, '#');
  if (armed && armed.el === el && armed.key === key && Date.now() - armed.at < 3500) { clearTimeout(armed.t); armed.el?.classList.remove('act-armed'); armed = null; return true; }
  if (armed) { clearTimeout(armed.t); armed.el?.classList.remove('act-armed'); }
  el?.classList.add('act-armed');
  armed = { el, key, at: Date.now(), t: setTimeout(() => { el?.classList.remove('act-armed'); armed = null; }, 3500) };
  toast.warning?.(`${msg}`, { description: 'Tap the same button again within 3.5 s to confirm.', duration: 3500 });
  return false;
}

export function ActBtn({ run, money = false, confirm = 'Tap again to confirm', done = 'Done', okToast = '', className = 'm-btn', children, disabled, onDone, ...rest }) {
  const [st, setSt] = useState('idle'); const t = useRef(0); const live = useRef(true);
  useEffect(() => () => { live.current = false; clearTimeout(t.current); }, []);
  const back = ms => { clearTimeout(t.current); t.current = setTimeout(() => live.current && setSt('idle'), ms); };
  const go = async () => {
    if (st === 'busy') return;
    if (money && st !== 'armed') { setSt('armed'); back(3500); return; }
    clearTimeout(t.current); setSt('busy');
    try {
      let out = await run();
      if (out && typeof out.ok === 'boolean' && typeof out.json === 'function') out = await serverJson(out);
      if (!live.current) return;
      setSt('ok'); back(1600); if (okToast) toast.success(okToast); onDone?.(out);
    } catch (e) {
      if (!live.current) return;
      setSt('fail'); back(700); toast.error(e?.message || 'That did not go through.');
    }
  };
  return <button type="button" {...rest} className={`${className} act act-${st}`} disabled={disabled || st === 'busy'} aria-busy={st === 'busy'} onClick={go} data-state={st}>
    {st === 'busy' ? <><Loader2 className="act-spin" size={14} aria-hidden="true" />{children}</> : st === 'armed' ? confirm : st === 'ok' ? <><Check size={14} aria-hidden="true" />{done}</> : children}
  </button>;
}

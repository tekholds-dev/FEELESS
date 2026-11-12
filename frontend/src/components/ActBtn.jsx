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

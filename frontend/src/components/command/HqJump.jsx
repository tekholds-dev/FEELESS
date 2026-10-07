import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { HQ_JUMPS, jumpSearch } from '../../lib/hqJump';

// Search bar on top of HQ: type what you want ("profiles", "rpc", "payouts") → Enter / click goes there. "/" focuses it.
export function HqJump({ tabs = [], onGo }) {
  const [q, setQ] = useState(''); const [at, setAt] = useState(0); const ref = useRef(null);
  const rows = useMemo(() => [...HQ_JUMPS.filter(j => tabs.some(t => t[0] === j.tab)), ...tabs.map(([tab, label]) => ({ label, words: tab, tab }))], [tabs]);
  const hits = useMemo(() => jumpSearch(q, rows), [q, rows]);
  useEffect(() => { const on = e => { if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(e.target?.tagName || '')) { e.preventDefault(); ref.current?.focus(); } };
    window.addEventListener('keydown', on); return () => window.removeEventListener('keydown', on); }, []);
  const go = j => { if (!j) return; setQ(''); setAt(0); ref.current?.blur(); onGo(j); };
  const key = e => { if (e.key === 'Enter') go(hits[at] || hits[0]); else if (e.key === 'Escape') { setQ(''); ref.current?.blur(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setAt(a => Math.min(hits.length - 1, a + 1)); } else if (e.key === 'ArrowUp') { e.preventDefault(); setAt(a => Math.max(0, a - 1)); } };
  return <div className="hqj" data-testid="hq-jump"><Search size={14} aria-hidden="true" />
    <input className="m-input" value={q} ref={ref} onChange={e => { setQ(e.target.value); setAt(0); }} onKeyDown={key} placeholder="Find anything in HQ…  ( / )" aria-label="Search HQ" data-testid="hq-jump-input" />
    {q && <ul className="hqj-list" role="listbox" data-testid="hq-jump-list">{hits.length ? hits.map((j, i) => <li key={j.label}><button type="button" role="option" aria-selected={i === at} className={i === at ? 'active' : ''} onMouseEnter={() => setAt(i)} onClick={() => go(j)}><b>{j.label}</b><small>{j.panel ? 'Fuse' : j.view ? 'Money' : 'Tab'}</small></button></li>)
      : <li className="hqj-none">Nothing called that — try "wallet", "fees", "rpc"</li>}</ul>}
  </div>;
}

import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, Lock, Search } from 'lucide-react';

// Swap desk executes on Solana only; other networks are shown but locked so nobody picks a
// token the router can't actually fill. EVM trades live in the Trade Desk (LI.FI).
const NETWORKS = [['solana', 'Solana', true], ['ethereum', 'Ethereum'], ['base', 'Base'], ['bsc', 'BNB'], ['arbitrum', 'Arbitrum']];

export function TokenPicker({ label, value, options, onChange, disabled, testId }) {
  const [open, setOpen] = useState(false);
  const [net, setNet] = useState('solana');
  const [q, setQ] = useState('');
  const box = useRef(null);
  const cur = options.find(o => o.mint === value) || options[0];
  useEffect(() => {
    if (!open) return undefined;
    const out = e => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    const esc = e => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', out); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('pointerdown', out); document.removeEventListener('keydown', esc); };
  }, [open]);
  const live = NETWORKS.find(n => n[0] === net)?.[2];
  const needle = q.trim().toLowerCase();
  const rows = live ? options.filter(o => (o.chain || 'solana') === 'solana' && (!needle || `${o.symbol} ${o.name} ${o.mint}`.toLowerCase().includes(needle))) : [];
  return <div className="tkp" ref={box}>
    <small>{label}</small>
    <button type="button" className="tkp-btn" data-testid={testId} disabled={disabled} aria-expanded={open} onClick={() => setOpen(o => !o)}>
      <span className="tkp-av">{cur?.symbol?.slice(0, 1)}</span><b>{cur?.symbol}</b><em>{cur?.name}</em><i className="tkp-chain">SOL</i><ChevronDown size={14} />
    </button>
    {open && <div className="tkp-pop" role="listbox">
      <nav>{NETWORKS.map(([id, name, ok]) => <button key={id} type="button" className={`${net === id ? 'on' : ''} ${ok ? '' : 'locked'}`} onClick={() => setNet(id)} title={ok ? name : `${name}: swap on the Trade Desk`}>{!ok && <Lock size={10} />}{name}</button>)}</nav>
      {live ? <>
        <div className="tkp-search"><Search size={13} /><input autoFocus aria-label="Filter tokens" placeholder="Filter tokens" value={q} onChange={e => setQ(e.target.value)} /></div>
        <div className="tkp-list">{rows.map(o => <button key={o.mint} type="button" role="option" aria-selected={o.mint === value} className={o.mint === value ? 'sel' : ''} onClick={() => { onChange(o.mint); setOpen(false); setQ(''); }}>
          <span className="tkp-av">{o.symbol?.slice(0, 1)}</span><b>{o.symbol}</b><em>{o.name}</em><code>{o.mint.slice(0, 4)}…{o.mint.slice(-4)}</code>
        </button>)}{!rows.length && <p>No match. Use the search above to find any Solana token.</p>}</div>
      </> : <div className="tkp-locked"><Lock size={18} /><b>Locked on this desk</b><p>The execution desk routes through Jupiter on Solana. {NETWORKS.find(n => n[0] === net)?.[1]} swaps and bridges run from the Trade Desk.</p></div>}
    </div>}
  </div>;
}

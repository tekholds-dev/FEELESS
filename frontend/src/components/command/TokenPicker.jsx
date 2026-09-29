import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { ChevronDown, Lock, Search } from 'lucide-react';

// Swap desk executes on Solana only; other networks are shown but locked so nobody picks a
// token the router can't actually fill. EVM trades live in the Trade Desk (LI.FI).
const NETWORKS = [['solana', 'Solana', true], ['base', 'Base'], ['ethereum', 'Ethereum'], ['bsc', 'BNB'], ['arbitrum', 'Arbitrum'], ['polygon', 'Polygon'], ['optimism', 'Optimism'], ['avalanche', 'Avalanche']];

export function TokenPicker({ label, value, options, onChange, onPickRemote, onNetwork, holdings = [], disabled, testId }) {
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
  // Any Solana coin: remote search (name, $ticker or contract) joins the local list, like Jupiter's picker.
  const [remote, setRemote] = useState([]);
  useEffect(() => {
    const term = q.trim();
    if (!open || !onPickRemote || term.length < 2) { setRemote([]); return undefined; }
    let alive = true;
    const t = setTimeout(() => fetch(apiUrl(`/api/reputation/tokens/search?q=${encodeURIComponent(term)}`)).then(r => r.json()).then(d => alive && setRemote(d.tokens || [])).catch(() => {}), 250);
    return () => { alive = false; clearTimeout(t); };
  }, [q, open, onPickRemote]);
  const avatar = o => (o?.icon ? <img className="tkp-av" src={o.icon} alt="" /> : <span className="tkp-av">{o?.symbol?.slice(0, 1)}</span>);
  const live = NETWORKS.find(n => n[0] === net)?.[2];
  const needle = q.trim().toLowerCase();
  const rows = live ? options.filter(o => (o.chain || 'solana') === 'solana' && (!needle || `${o.symbol} ${o.name} ${o.mint}`.toLowerCase().includes(needle))) : [];
  // Your coins first: wallet holdings matching the search, by USD value.
  const mine = holdings.filter(h => !needle || `${h.symbol} ${h.name} ${h.mint}`.toLowerCase().includes(needle)).slice(0, 8);
  const pickMine = h => { if (options.some(o => o.mint === h.mint)) onChange(h.mint); else onPickRemote?.(h); setOpen(false); setQ(''); };
  return <div className="tkp" ref={box}>
    {label && <small>{label}</small>}
    <button type="button" className="tkp-btn" data-testid={testId} disabled={disabled} aria-expanded={open} onClick={() => setOpen(o => !o)}>
      {avatar(cur)}<b>{cur?.symbol}</b><em>{cur?.name}</em><i className="tkp-chain">SOL</i><ChevronDown size={14} />
    </button>
    {open && <div className="tkp-pop" role="listbox">
      <nav>{NETWORKS.map(([id, name, ok]) => <button key={id} type="button" className={`${net === id ? 'on' : ''} ${ok ? '' : 'locked'}`} onClick={() => { if (!ok && onNetwork) { onNetwork(id); setOpen(false); } else setNet(id); }} title={ok || onNetwork ? name : `${name}: swap on the Trade Desk`}>{!ok && !onNetwork && <Lock size={10} />}{name}</button>)}</nav>
      {live ? <>
        <div className="tkp-search"><Search size={13} /><input autoFocus aria-label="Filter tokens" placeholder="Search name, $ticker or contract" value={q} onChange={e => setQ(e.target.value)} /></div>
        <div className="tkp-list">{mine.length > 0 && <><div className="tkp-group">In your wallet</div>{mine.map(h => <button key={`w-${h.mint}`} type="button" role="option" aria-selected={h.mint === value} className={`tkp-mine ${h.mint === value ? 'sel' : ''}`} onClick={() => pickMine(h)}>
          {avatar(h)}<b>{h.symbol}</b><em>{Number(h.amount).toLocaleString(undefined, { maximumFractionDigits: 4 })}</em><code>{h.usd != null ? `$${Number(h.usd).toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—'}</code>
        </button>)}<div className="tkp-group">All coins</div></>}{rows.filter(o => !mine.some(h => h.mint === o.mint)).map(o => <button key={o.mint} type="button" role="option" aria-selected={o.mint === value} className={o.mint === value ? 'sel' : ''} onClick={() => { onChange(o.mint); setOpen(false); setQ(''); }}>
          {avatar(o)}<b>{o.symbol}</b><em>{o.name}</em><code>{o.mint.slice(0, 4)}…{o.mint.slice(-4)}</code>
        </button>)}{remote.filter(t => !rows.some(o => o.mint === t.mint)).map(t => <button key={`r-${t.mint}`} type="button" role="option" aria-selected={false} onClick={() => { onPickRemote(t); setOpen(false); setQ(''); }}>
          {avatar(t)}<b>{t.symbol}{t.verified && <span className="tkp-ok" title="Verified by Jupiter"> ✓</span>}</b><em>{t.name}</em><code>{t.liquidity ? `liq $${Math.round(t.liquidity).toLocaleString()}` : `${t.mint.slice(0, 4)}…${t.mint.slice(-4)}`}</code>
        </button>)}{!rows.length && !remote.length && <p>{needle.length >= 2 ? 'Searching every Solana coin…' : 'Type a name, $ticker or paste a contract.'}</p>}</div>
      </> : <div className="tkp-locked"><Lock size={18} /><b>Locked on this desk</b><p>The execution desk routes through Jupiter on Solana. {NETWORKS.find(n => n[0] === net)?.[1]} swaps and bridges run from the Trade Desk.</p></div>}
    </div>}
  </div>;
}

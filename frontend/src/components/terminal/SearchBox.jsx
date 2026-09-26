import React, { useEffect, useRef, useState } from 'react';
import { Search, ArrowUpRight, Clock, User, Coins, Wallet } from 'lucide-react';
import { formatUSD, formatPct } from '../../lib/dexscreener';

const RECENT_KEY = 'feeless:recent-searches';
const readRecent = () => { try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').slice(0, 6); } catch { return []; } };
const pushRecent = item => { try { const next = [item, ...readRecent().filter(r => r.href !== item.href)].slice(0, 6); localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch { /* ignore */ } };
const ADDR = /^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$/;

// Header search: live coins + profiles + wallets as you type, keyboard-driven, "/" to focus.
export function SearchBox({ ecosystem, nav }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [coins, setCoins] = useState([]);
  const [people, setPeople] = useState([]);
  const [wallet, setWallet] = useState(null);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const input = useRef(null);
  const box = useRef(null);

  useEffect(() => {
    const onKey = e => { if (e.key === '/' && !/input|textarea|select/i.test(document.activeElement?.tagName || '') && !document.activeElement?.isContentEditable) { e.preventDefault(); input.current?.focus(); setOpen(true); } };
    const onClick = e => { if (!box.current?.contains(e.target)) setOpen(false); };
    window.addEventListener('keydown', onKey); document.addEventListener('mousedown', onClick);
    return () => { window.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onClick); };
  }, []);

  useEffect(() => {
    const term = q.trim();
    setActive(0);
    if (term.length < 2) { setCoins([]); setPeople([]); setWallet(null); return undefined; }
    let alive = true;
    setLoading(true);
    const t = setTimeout(async () => {
      const bare = term.replace(/^[@$]/, '');
      const [c, p, w] = await Promise.all([
        term.startsWith('@') ? Promise.resolve([]) : fetch(`https://api.dexscreener.com/latest/dex/search?q=${encodeURIComponent(({ btc: 'WBTC', bitcoin: 'WBTC', eth: 'WETH', ethereum: 'WETH' })[bare.toLowerCase()] || bare)}`).then(r => r.json()).then(d => {
          const seen = new Set();
          return (d.pairs || []).sort((a, b) => (b.volume?.h24 || 0) - (a.volume?.h24 || 0)).filter(x => { const k = x.baseToken?.address; if (seen.has(k)) return false; seen.add(k); return true; }).slice(0, 8);
        }).catch(() => []),
        fetch(`/api/reputation/search?q=${encodeURIComponent(bare)}`).then(r => r.json()).then(d => d.profiles || []).catch(() => []),
        ADDR.test(term) ? fetch(`/api/reputation/resolve/${encodeURIComponent(term)}`).then(r => (r.ok ? r.json() : { address: term, handle: term.slice(0, 6).toLowerCase(), maybeToken: true })).catch(() => ({ address: term, handle: term.slice(0, 6).toLowerCase(), maybeToken: true })) : Promise.resolve(null),
      ]);
      if (!alive) return;
      setCoins(c); setPeople(p); setWallet(w); setLoading(false);
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [q]);

  const items = [
    ...(wallet && !(wallet.maybeToken && coins.length) ? [{ kind: 'wallet', key: `w-${wallet.address}`, href: `/terminal/profile/${wallet.address}`, label: `Wallet profile @${wallet.handle}`, sub: `${wallet.address.slice(0, 6)}…${wallet.address.slice(-6)}` }] : []),
    ...people.map(p => ({ kind: 'profile', key: `p-${p.address}`, href: `/terminal/profile/${p.address}`, label: p.displayName || `@${p.handle}`, sub: `@${p.handle}`, img: p.avatarUrl })),
    ...coins.map(c => ({ kind: 'coin', key: `c-${c.pairAddress}`, href: `/?coin=${c.chainId}:${c.pairAddress}`, profile: `/terminal/coin/${c.chainId}/${c.pairAddress}`, label: `$${c.baseToken?.symbol}`, sub: `${c.baseToken?.name} · ${c.chainId}`, img: c.info?.imageUrl, price: c.priceUsd, change: c.priceChange?.h24, vol: c.volume?.h24 })),
  ];
  const recent = !q.trim() ? readRecent() : [];
  const list = q.trim() ? items : recent;

  const go = it => { pushRecent({ kind: it.kind, href: it.href, label: it.label, sub: it.sub, img: it.img }); setOpen(false); setQ(''); nav(it.href); };
  const submit = e => {
    e.preventDefault();
    if (list[active]) { go(list[active]); return; }
    const term = q.trim(); if (term) { setOpen(false); nav(`/terminal/discover?q=${encodeURIComponent(term.replace(/^[@$]/, ''))}`); }
  };
  const onKeyDown = e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive(a => Math.min(a + 1, list.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a - 1, 0)); }
    else if (e.key === 'Escape') { setOpen(false); input.current?.blur(); }
  };
  const Icon = { coin: Coins, profile: User, wallet: Wallet }[list[0]?.kind] || Clock;
  return <form ref={box} className="terminal-search search-box" onSubmit={submit} data-testid="terminal-search">
    <Search size={17} />
    <input ref={input} data-testid="terminal-search-input" aria-label="Search coins, @names or wallets" placeholder={`${ecosystem?.name || 'Search'} · coins, $TICKER, @name or wallet…  ( / )`} maxLength={120} value={q} onFocus={() => setOpen(true)} onChange={e => { setQ(e.target.value); setOpen(true); }} onKeyDown={onKeyDown} autoComplete="off" />
    <button data-testid="terminal-search-submit" title="Search" type="submit"><ArrowUpRight size={16} /></button>
    {open && (list.length > 0 || (q.trim().length >= 2 && !loading)) && <div className="search-drop" role="listbox" data-testid="search-results">
      {!q.trim() && <small className="sd-head"><Clock size={11} /> Recent</small>}
      {q.trim() && loading && !list.length && <small className="sd-head">Searching…</small>}
      {q.trim() && !loading && !list.length && <small className="sd-head">Nothing found — Enter searches all markets.</small>}
      {list.map((it, i) => { const I = { coin: Coins, profile: User, wallet: Wallet }[it.kind] || Icon; return <button type="button" key={it.key || it.href} role="option" aria-selected={i === active} className={`sd-row k-${it.kind} ${i === active ? 'active' : ''}`} onMouseEnter={() => setActive(i)} onMouseDown={e => { e.preventDefault(); go(it); }}>
        {it.img ? <img src={it.img} alt="" /> : <span className="sd-ic"><I size={14} /></span>}
        <span className="sd-main"><b>{it.label}</b><small>{it.sub}</small></span>
        {it.kind === 'coin' && <span className="sd-acts"><span className="sd-prof" role="button" tabIndex={-1} onMouseDown={e => { e.preventDefault(); e.stopPropagation(); go({ ...it, href: it.href }); }}>chart</span><span className="sd-prof" role="button" tabIndex={-1} onMouseDown={e => { e.preventDefault(); e.stopPropagation(); go({ ...it, href: it.profile }); }}>profile</span></span>}{it.kind === 'coin' && it.price && <span className="sd-num"><b>{formatUSD(it.price)}</b><small className={Number(it.change) >= 0 ? 'positive' : 'negative'}>{formatPct(it.change)} · vol {formatUSD(it.vol)}</small></span>}
        <em className="sd-kind">{it.kind}</em>
      </button>; })}
    </div>}
  </form>;
}

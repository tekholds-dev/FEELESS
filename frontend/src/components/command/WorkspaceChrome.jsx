import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Activity, ArrowUpRight, Globe2, ScanLine, Radio, X } from 'lucide-react';
import { useWorkspace, CONTEXTS } from '../../hooks/useWorkspace';
import { useMarket } from '../../hooks/useMarket';
import { formatTime, formatPct, formatUSD } from '../../lib/dexscreener';
import { apiUrl } from '../../lib/api';
import { TokenAvatar } from '../terminal/MarketPrimitives';

export const useClock = (ms = 1000) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(timer); }, [ms]);
  return now;
};

export const MouseGlow = () => {
  const ref = useRef();
  useEffect(() => {
    if (window.matchMedia('(pointer: coarse), (prefers-reduced-motion: reduce)').matches) return;
    const move = e => { if (ref.current) ref.current.style.transform = `translate(${e.clientX - 140}px,${e.clientY - 140}px)`; };
    window.addEventListener('pointermove', move, { passive: true });
    return () => window.removeEventListener('pointermove', move);
  }, []);
  return <div ref={ref} className="mouse-glow" aria-hidden="true" />;
};

export const ContextBar = () => {
  const { ecosystem, setEcosystem } = useWorkspace();
  const time = useClock();
  return <div className="context-bar" style={{ '--context-accent': ecosystem.color }}><span className="context-indicator"><i />NETWORK LINK</span><Globe2 size={15} /><select data-testid="workspace-ecosystem" aria-label="Active ecosystem" value={ecosystem.id} onChange={e => setEcosystem(e.target.value)}>{CONTEXTS.map(e => <option key={e.id} value={e.id}>{e.name}{e.isLaunchpad ? ' / WAR ROOM' : ' / INTELLIGENCE'}</option>)}</select><span className="context-chain" data-testid="context-chain">{ecosystem.chainId.toUpperCase()}</span><span className="context-clock" data-testid="terminal-clock">{new Date(time).toISOString().slice(11, 19)} UTC</span></div>;
};

export const AlphaTape = ({ horizontal = false }) => {
  const { ecosystem, selectPair } = useWorkspace();
  const nav = useNavigate(); const location = useLocation();
  const openPair = pair => { selectPair(pair); if (location.pathname !== '/terminal/chat') nav('/terminal/chat'); };
  const [type, setType] = useState('all');
  const { data, error } = useMarket(`/api/intelligence/tape?chain=${ecosystem.chainId}&venue=${ecosystem.isLaunchpad ? ecosystem.id : 'all'}&context=${ecosystem.id}`, 15000);
  const events = (data?.events || []).filter(e => type === 'all' || e.kind === type);
  return <section className={`alpha-tape ${horizontal ? 'tape-horizontal' : ''}`} data-testid="alpha-tape"><div className="alpha-title"><span><Radio size={15} /><b>ALPHA TAPE</b><i /></span><select aria-label="Alpha Tape signal type" data-testid="alpha-tape-filter" value={type} onChange={e => setType(e.target.value)}><option value="all">All signals</option>{[['NEW_PAIR', 'New pair'], ['TRENDING', 'Trending'], ['PRICE_VELOCITY', 'Price velocity'], ['LIQUIDITY_CHANGE', 'Liquidity delta'], ['VOLUME_CHANGE', 'Volume delta'], ['CONTRACT_SCANNED', 'CA scanned'], ['CHAT_CA_MENTION', 'Chat CA']].map(([id, name]) => <option value={id} key={id}>{name}</option>)}</select></div><div className="alpha-events custom-scroll">{!events.length && <div className="alpha-waiting" data-testid="alpha-tape-empty"><span className="signal-lines"><i /><i /><i /><i /></span>{error ? 'Signal provider unavailable.' : 'Listening for verified signals…'}<small>No invented activity. Unsupported transaction events are not emitted.</small></div>}{events.map(e => <button data-testid={`alpha-event-${e.id}`} key={e.id} className="alpha-event" onClick={() => openPair(e.pair)} title={e.detail}><span className={`event-kind event-${e.kind.toLowerCase()}`}>{e.kind.replaceAll('_', ' ')}</span><TokenAvatar pair={e.pair} size={26} /><span><b>{e.title}</b><small>{e.provider} · {formatTime(e.observed_at)}</small></span><ArrowUpRight size={13} /></button>)}</div><small className="tape-source">Provider observations & same-source snapshot changes. Not a transaction scanner.</small></section>;
};

export const PulseGrid = ({ pairs, community, fee, feeCat, loading }) => {
  const liquidity = pairs.reduce((n, p) => n + Number(p.liquidity?.usd || 0), 0);
  const velocity = pairs.filter(p => Number(p.priceChange?.m5) > 0).length;
  const items = [
    ['FEE NETWORK PULSE', fee?.status === 'market_observed' ? 'MARKET ONLINE' : 'AWAITING MARKET', fee?.stale ? 'Cached provider snapshot' : 'Exact mint / provider-backed', 'mint'],
    ['ECOSYSTEM FLOW', loading ? '—' : formatUSD(liquidity), 'Liquidity across this fetched feed', 'white'],
    ['MARKET VELOCITY', loading ? '—' : `${velocity} / ${pairs.length}`, 'Pools positive over 5m', 'mint'],
    ['COMMUNITY SIGNAL', community?.messages ?? '—', 'Actual messages / 7 days', 'white'],
    ['FEE-BACK ENGINE', 'PLANNED', '100% of eligible USD fee value', 'amber'],
    ['FEECAT DELIVERY', 'NOT ACTIVATED', feeCat?.status === 'market_observed' ? 'Market observed / payouts planned' : 'Awaiting verified market & program', 'amber'],
  ];
  return <div className="pulse-grid">{items.map(([label, value, detail, tone], i) => <div className={`pulse-cell ${tone}`} key={label} data-testid={`pulse-module-${i}`}><small><i />{label}</small><strong key={String(value)} data-testid={`pulse-value-${i}`}>{value}</strong><span>{detail}</span><div className="pulse-baseline" /></div>)}</div>;
};

export const ContractScanner = ({ onResolved }) => {
  const { ecosystem, selectPair } = useWorkspace();
  const nav = useNavigate(); const location = useLocation();
  const [input, setInput] = useState(''); const [result, setResult] = useState(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const scan = async e => {
    e.preventDefault(); setBusy(true); setError(''); setResult(null);
    try {
      const res = await fetch(apiUrl(`/api/market/scan?address=${encodeURIComponent(input.trim())}&context=${ecosystem.id}`));
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Enter a valid SPL or EVM contract address.');
      if (!data.pairs.length) throw new Error('No exact provider match for this contract.');
      setResult(data.pairs[0]); selectPair(data.pairs[0]); onResolved?.(data.pairs[0]);
      if (location.pathname !== '/terminal/chat') nav('/terminal/chat');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return <form className="ca-scanner" onSubmit={scan}><ScanLine size={18} /><input data-testid="ca-scanner-input" aria-label="Contract address scanner" value={input} onChange={e => setInput(e.target.value)} placeholder={`${ecosystem.name} · paste a CA to inspect`} maxLength={64} /><button className="btn-outline" data-testid="ca-scanner-submit" disabled={busy || !input.trim()}>{busy ? 'Resolving…' : 'Scan CA'}</button>{error && <p data-testid="ca-scanner-error" role="alert">{error}</p>}{result && <p className="positive" data-testid="ca-scanner-result">Exact match: {result.baseToken.symbol} · {result.chainId}. Provider match is not a security audit.</p>}</form>;
};
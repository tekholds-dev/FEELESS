import { LivePrice } from '../terminal/LiveCells';
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Star, Bell, Copy, CandlestickChart, ArrowUpRight } from 'lucide-react';
import { toast } from 'sonner';
import { useWorkspace } from '../../hooks/useWorkspace';
import { getEcosystem } from '../../lib/ecosystems';
import { LAUNCHPADS, matchesPad } from '../../lib/launchpads';
import { formatUSD, formatAge, shortAddress, dexUrl } from '../../lib/dexscreener';
import { TokenAvatar } from '../terminal/MarketPrimitives';
import { useClock } from './WorkspaceChrome';
import { useTilt } from '../../hooks/useTilt';
import { investigate } from '../CaseFile';

export const IntelligenceCard = ({ pair, id, snapshotTime }) => {
  const { selectPair: setSelectedPair, toggle, has, setAlertPair } = useWorkspace(); const nav = useNavigate(); const location = useLocation(); useClock(30000);
  const selectPair = pair => { setSelectedPair(pair); if (location.pathname !== '/terminal/chat') nav('/terminal/chat'); };
  const address = pair.baseToken?.address;
  const chain = getEcosystem(pair.chainId === 'bsc' ? 'bnb' : pair.chainId);
  const pad = LAUNCHPADS.find(p => matchesPad(pair, p.id));
  const external = url => { try { return new URL(url).protocol === 'https:'; } catch { return false; } };
  const copy = async () => { try { await navigator.clipboard.writeText(address); toast.success('Contract copied'); } catch { toast.error('Clipboard unavailable'); } };
  const tilt = useTilt(3);
  const ch = w => Number(pair.priceChange?.[w]);
  const buys = Number(pair.txns?.h24?.buys) || 0, sells = Number(pair.txns?.h24?.sells) || 0;
  const buyPct = buys + sells ? Math.round((buys / (buys + sells)) * 100) : null;
  const big = v => (Math.abs(v) >= 900 ? `${(v / 100 + 1).toFixed(1)}x` : `${Math.abs(v) >= 100 ? Math.round(v) : v.toFixed(1)}%`);
  return <article ref={tilt.ref} onMouseMove={tilt.onMouseMove} onMouseLeave={tilt.onMouseLeave} className="intelligence-card tilt-card" data-testid={id}><i className="tilt-glare" aria-hidden="true" />
    <div className="intel-card-heading"><TokenAvatar pair={pair} size={38} /><div><b>${pair.baseToken?.symbol}</b><small>{pair.baseToken?.name}</small></div>
      <div className="intel-price"><strong><LivePrice pair={pair} precise /></strong>{Number.isFinite(ch('h24')) && <span className={`intel-chip ${ch('h24') >= 0 ? 'up' : 'down'}`}>{ch('h24') >= 0 ? '+' : ''}{big(ch('h24'))}</span>}</div></div>
    <div className="intel-momentum">{['m5', 'h1', 'h6', 'h24'].map(w => Number.isFinite(ch(w)) ? <span key={w} className={ch(w) >= 0 ? 'up' : 'down'}><small>{w}</small>{ch(w) >= 0 ? '+' : ''}{big(ch(w))}</span> : null)}<em>{pair.chainId}{pad ? ` · ${pad.name}` : ''} · {pair.dexId || 'dex'}</em></div>
    <dl className="intel-stats">{[['MC', formatUSD(pair.marketCap || pair.fdv)], ['Liq', formatUSD(pair.liquidity?.usd)], ['Vol 24h', formatUSD(pair.volume?.h24)], ['Age', formatAge(pair.pairCreatedAt)]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {buyPct != null && <div className="intel-pressure" title={`${buys.toLocaleString()} buys · ${sells.toLocaleString()} sells (24h)`}><i style={{ width: `${buyPct}%` }} /><span>{buyPct}% buys</span><span>{buys + sells >= 1000 ? `${((buys + sells) / 1000).toFixed(1)}K` : buys + sells} txns</span></div>}
    <button className="intel-contract" data-testid={`${id}-copy`} title="Copy full contract" onClick={copy}>{shortAddress(address)}<Copy size={11} /></button><div className="intel-actions"><button data-testid={`${id}-chart`} onClick={() => selectPair(pair)}><CandlestickChart size={13} />Chart</button><button data-testid={`${id}-trade`} onClick={() => { selectPair(pair); nav('/terminal/trade'); }}><ArrowUpRight size={13} />Trade</button><button data-testid={`${id}-watch`} className={has(pair) ? 'is-saved' : ''} title="Watch token" onClick={() => toggle(pair)}><Star size={14} fill={has(pair) ? 'currentColor' : 'none'} /></button><button type="button" data-testid={`${id}-case`} title="Case file: risk, holders, creator" onClick={() => investigate(address)}>🔎</button><button data-testid={`${id}-alert`} title="Create token alert" onClick={() => { selectPair(pair); setAlertPair(pair); nav('/terminal/alerts'); }}><Bell size={14} /></button></div><div className="intel-links"><a data-testid={`${id}-dex`} href={dexUrl(pair)} target="_blank" rel="noreferrer">DEX ↗</a>{chain?.explorer && <a data-testid={`${id}-explorer`} href={`${chain.explorer}/${pair.chainId === 'solana' ? 'token' : 'token'}/${address}`} target="_blank" rel="noreferrer">Explorer ↗</a>}{(pair.info?.websites || []).filter(w => external(w.url)).slice(0, 1).map((w, i) => <a data-testid={`${id}-website-${i}`} key={i} href={w.url} target="_blank" rel="noreferrer">Website ↗</a>)}{(pair.info?.socials || []).filter(w => external(w.url)).slice(0, 2).map((w, i) => <a data-testid={`${id}-social-${i}`} key={i} href={w.url} target="_blank" rel="noreferrer">{w.type} ↗</a>)}</div><small className="intel-source">{snapshotTime ? `Message-time snapshot · ${new Date(snapshotTime).toLocaleDateString('en-US')}` : 'Provider snapshot'} · Not a security endorsement</small></article>;
};
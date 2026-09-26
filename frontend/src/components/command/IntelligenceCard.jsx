import { LivePrice } from '../terminal/LiveCells';
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Star, Bell, Copy, CandlestickChart, ArrowUpRight } from 'lucide-react';
import { toast } from 'sonner';
import { useWorkspace } from '../../hooks/useWorkspace';
import { getEcosystem } from '../../lib/ecosystems';
import { LAUNCHPADS, matchesPad } from '../../lib/launchpads';
import { formatUSD, formatPct, formatAge, shortAddress, dexUrl } from '../../lib/dexscreener';
import { TokenAvatar } from '../terminal/MarketPrimitives';
import { useClock } from './WorkspaceChrome';

export const IntelligenceCard = ({ pair, id, snapshotTime }) => {
  const { selectPair: setSelectedPair, toggle, has, setAlertPair } = useWorkspace(); const nav = useNavigate(); const location = useLocation(); useClock(30000);
  const selectPair = pair => { setSelectedPair(pair); if (location.pathname !== '/terminal/chat') nav('/terminal/chat'); };
  const address = pair.baseToken?.address;
  const chain = getEcosystem(pair.chainId === 'bsc' ? 'bnb' : pair.chainId);
  const pad = LAUNCHPADS.find(p => matchesPad(pair, p.id));
  const external = url => { try { return new URL(url).protocol === 'https:'; } catch { return false; } };
  const copy = async () => { try { await navigator.clipboard.writeText(address); toast.success('Contract copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <article className="intelligence-card" data-testid={id}><div className="intel-card-heading"><TokenAvatar pair={pair} size={34} /><div><b>{pair.baseToken?.symbol}</b><small>{pair.baseToken?.name}</small></div><span>{pair.chainId}</span></div><div className="intel-price"><strong><LivePrice pair={pair} precise /></strong><span className={Number(pair.priceChange?.h24) >= 0 ? 'positive' : 'negative'}>{formatPct(pair.priceChange?.h24)}</span></div><dl>{[['MCap', formatUSD(pair.marketCap)], ['FDV', formatUSD(pair.fdv)], ['Liquidity', formatUSD(pair.liquidity?.usd)], ['24h volume', formatUSD(pair.volume?.h24)], ['Pool age', formatAge(pair.pairCreatedAt)], ['DEX', pair.dexId || 'Unavailable'], ['Pair', `${pair.baseToken?.symbol || '?'} / ${pair.quoteToken?.symbol || '?'}`], ['Launchpad provenance', pad ? `${pad.name} venue` : 'Unverified'], ['Holders / concentration', 'Provider unavailable'], ['Liquidity lock status', 'Not verified']].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><button className="intel-contract" data-testid={`${id}-copy`} title="Copy full contract" onClick={copy}>{shortAddress(address)}<Copy size={11} /></button><div className="intel-actions"><button data-testid={`${id}-chart`} onClick={() => selectPair(pair)}><CandlestickChart size={13} />Chart</button><button data-testid={`${id}-trade`} onClick={() => { selectPair(pair); nav('/terminal/trade'); }}><ArrowUpRight size={13} />Trade</button><button data-testid={`${id}-watch`} className={has(pair) ? 'is-saved' : ''} title="Watch token" onClick={() => toggle(pair)}><Star size={14} fill={has(pair) ? 'currentColor' : 'none'} /></button><button data-testid={`${id}-alert`} title="Create token alert" onClick={() => { selectPair(pair); setAlertPair(pair); nav('/terminal/alerts'); }}><Bell size={14} /></button></div><div className="intel-links"><a data-testid={`${id}-dex`} href={dexUrl(pair)} target="_blank" rel="noreferrer">DEX ↗</a>{chain?.explorer && <a data-testid={`${id}-explorer`} href={`${chain.explorer}/${pair.chainId === 'solana' ? 'token' : 'token'}/${address}`} target="_blank" rel="noreferrer">Explorer ↗</a>}{(pair.info?.websites || []).filter(w => external(w.url)).slice(0, 1).map((w, i) => <a data-testid={`${id}-website-${i}`} key={i} href={w.url} target="_blank" rel="noreferrer">Website ↗</a>)}{(pair.info?.socials || []).filter(w => external(w.url)).slice(0, 2).map((w, i) => <a data-testid={`${id}-social-${i}`} key={i} href={w.url} target="_blank" rel="noreferrer">{w.type} ↗</a>)}</div><small className="intel-source">{snapshotTime ? `Message-time snapshot · ${new Date(snapshotTime).toLocaleDateString('en-US')}` : 'Provider snapshot'} · Not a security endorsement</small></article>;
};
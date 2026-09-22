import React, { useEffect, useState } from 'react';
import useSWR from 'swr';
import { Bell, Trash2, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { marketRequest, pairKey, formatUSD } from '../../lib/dexscreener';
import { MarketTable } from './MarketTable';

export function useLocalSettings() {
  const [settings, setSettings] = useState(() => {
    try { return { compact: false, autoRefresh: true, reducedMotion: false, fontScale: 'normal', ...JSON.parse(localStorage.getItem('feeless-settings') || '{}') }; }
    catch { return { compact: false, autoRefresh: true, reducedMotion: false, fontScale: 'normal' }; }
  });
  useEffect(() => { localStorage.setItem('feeless-settings', JSON.stringify(settings)); }, [settings]);
  return [settings, setSettings];
}

export function usePriceAlerts() {
  const [alerts, setAlerts] = useState(() => {
    try { const saved = JSON.parse(localStorage.getItem('feeless-alerts') || '[]'); return Array.isArray(saved) ? saved : []; } catch { return []; }
  });
  useEffect(() => { localStorage.setItem('feeless-alerts', JSON.stringify(alerts)); }, [alerts]);
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      for (const alert of alerts.filter(a => !a.triggered)) {
        try {
          if (alert.metric?.startsWith('event:')) {
            const data = await marketRequest(`/api/intelligence/tape?chain=${alert.chain}&context=${alert.context}`);
            const found = data.events.find(e => e.kind === alert.metric.slice(6) && new Date(e.observed_at).getTime() > alert.created_at);
            if (found && !cancelled) {
              setAlerts(list => list.map(a => a.id === alert.id ? { ...a, triggered: new Date().toISOString(), eventTitle: found.title } : a));
              toast.success(`Ecosystem alert: ${found.title}`);
            }
            continue;
          }
          const result = await marketRequest(`/pair/${alert.pair.chainId}/${alert.pair.pairAddress}`);
          const p = result.pairs[0];
          const raw = { price: p?.priceUsd, percentage: p?.priceChange?.h24, volume: p?.volume?.h24, liquidity: p?.liquidity?.usd, marketcap: p?.marketCap }[alert.metric || 'price'];
          const price = Number(raw);
          if (cancelled || result.stale || raw == null || !Number.isFinite(price)) continue;
          if (alert.direction === 'above' ? price >= alert.target : price <= alert.target) {
            setAlerts(list => list.map(a => a.id === alert.id ? { ...a, triggered: new Date().toISOString(), triggeredPrice: price } : a));
            toast.success(`${alert.pair.baseToken.symbol} ${alert.metric || 'price'} condition reached`);
          }
        } catch { /* Keep the alert armed until a fresh quote is available. */ }
      }
    };
    check(); const timer = setInterval(check, 60000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [alerts]);
  return [alerts, setAlerts];
}

export const AlertsPage = ({ alerts, setAlerts, selected, watchlist, ecosystem = { id: 'solana', chainId: 'solana' } }) => {
  const [chosen, setChosen] = useState('');
  const [target, setTarget] = useState('');
  const [direction, setDirection] = useState('above');
  const [metric, setMetric] = useState('price');
  const isEvent = metric.startsWith('event:');
  const choices = [...new Map([selected, ...watchlist].filter(Boolean).map(p => [pairKey(p), p])).values()];
  const submit = e => {
    e.preventDefault(); const pair = choices.find(p => pairKey(p) === chosen) || choices[0];
    if (!isEvent && (!pair || !Number.isFinite(Number(target)) || (metric !== 'percentage' && Number(target) <= 0))) return;
    if (alerts.filter(a => !a.triggered).length >= 5) { toast.error('Maximum five active alerts. Remove one to continue.'); return; }
    setAlerts([...alerts, { id: crypto.randomUUID(), pair, target: isEvent ? null : Number(target), direction, metric,
      chain: ecosystem.chainId, context: ecosystem.id, created_at: Date.now(), triggered: null }]); setTarget(''); toast.success('Conditional alert armed');
  };
  return <div className="document-page"><div className="page-heading"><span className="eyebrow">CONDITIONAL SIGNALS / {ecosystem.id.toUpperCase()}</span><h1>Stay on your levels.</h1><p>Checked every minute while the terminal is open. Browser-local. Provider outages postpone evaluation.</p></div><form className="alert-form" onSubmit={submit}><label>Signal<select data-testid="alert-metric" value={metric} onChange={e => setMetric(e.target.value)}>{[['price', 'Price · USD'], ['percentage', '24h move · %'], ['volume', '24h volume · USD'], ['liquidity', 'Liquidity · USD'], ['marketcap', 'Market cap · USD'], ['event:NEW_PAIR', 'New pool observed'], ['event:CONTRACT_SCANNED', 'Ecosystem CA scan'], ['event:CHAT_CA_MENTION', 'Chat CA mention'], ['event:LIQUIDITY_CHANGE', 'Ecosystem liquidity delta']].map(([id, label]) => <option key={id} value={id} label={label} />)}<option disabled label="New ATH — provider unavailable" /><option disabled label="Wallet event — indexer unavailable" /><option disabled label="Token listed — provenance unavailable" /></select></label>{!isEvent && <><label>Token<select data-testid="alert-token" value={chosen || (choices[0] && pairKey(choices[0])) || ''} onChange={e => setChosen(e.target.value)}>{!choices.length && <option value="" label="Select a market first" />}{choices.map(p => <option key={pairKey(p)} value={pairKey(p)} label={`${p.baseToken.symbol} · ${p.chainId}`} />)}</select></label><label>Condition<select data-testid="alert-direction" value={direction} onChange={e => setDirection(e.target.value)}><option value="above" label="At or above" /><option value="below" label="At or below" /></select></label><label>Target {metric === 'percentage' ? '%' : 'USD'}<input data-testid="alert-target" type="number" min={metric === 'percentage' ? undefined : '0.000000000001'} step="any" placeholder={metric === 'percentage' ? '10' : '0.001'} required value={target} onChange={e => setTarget(e.target.value)} /></label></>}<button className="btn-primary" data-testid="alert-create" disabled={!isEvent && !choices.length}><Plus size={16} />Create alert</button></form><div className="alerts-list">{!alerts.length && <div className="empty-table" data-testid="alerts-empty"><Bell size={25} />No alerts yet.</div>}{alerts.map(a => <div className="alert-row" key={a.id} data-testid={`alert-${a.id}`}><Bell size={18} /><span><b>{a.metric?.startsWith('event:') ? a.context : a.pair?.baseToken.symbol} · {a.metric || 'price'}</b><small>{a.metric?.startsWith('event:') ? 'New observations after creation' : `${a.direction === 'above' ? 'At or above' : 'At or below'} ${a.metric === 'percentage' ? `${a.target}%` : formatUSD(a.target)}`}</small></span><span className={a.triggered ? 'positive' : 'muted'} data-testid={`alert-status-${a.id}`}>{a.triggered ? a.eventTitle || 'Condition triggered' : 'Armed · checks every 60s'}</span><button title="Delete alert" data-testid={`alert-delete-${a.id}`} onClick={() => setAlerts(alerts.filter(item => item.id !== a.id))}><Trash2 size={16} /></button></div>)}</div></div>;
};

export const WatchlistPage = ({ watchlist, onSelect, has, toggle }) => {
  const key = watchlist.length ? `watch:${watchlist.map(pairKey).join(',')}` : null;
  const { data, isLoading } = useSWR(key, async () => Promise.all(watchlist.map(async p => {
    try { const result = await marketRequest(`/pair/${p.chainId}/${p.pairAddress}`); return { pair: result.pairs[0] || p, stale: result.stale || !result.pairs.length }; }
    catch { return { pair: p, stale: true }; }
  })), { refreshInterval: 60000, revalidateOnFocus: false, shouldRetryOnError: false });
  return <div className="watchlist-page"><div className="page-heading"><span className="eyebrow">YOUR PERSONAL RADAR</span><h1>Keep your conviction close.</h1><p>Watchlisted tokens · {watchlist.length} saved in this browser</p></div>{data?.some(p => p.stale) && <p className="market-error" data-testid="watchlist-stale">Some quotes are unavailable. Saved snapshots are shown for those tokens.</p>}<MarketTable pairs={data?.map(p => p.pair) || watchlist} loading={isLoading} onSelect={onSelect} has={has} toggle={toggle} prefix="watchlist" />{!watchlist.length && <p className="provider-note">Star a token in any market feed to save it here.</p>}</div>;
};
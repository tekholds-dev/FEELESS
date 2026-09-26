import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Bell, BellOff, Cat, Radar, Star, Trash2 } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { TokenAvatar } from '../terminal/MarketPrimitives';
import { AnimatedNumber } from '../terminal/AnimatedNumber';
import { fetchLivePrices, formatLivePrice } from '../../lib/livePrice';
import { formatPct, formatUSD, tokenKey } from '../../lib/dexscreener';

const OWNER_KEY = 'feeless-paper-owner';
const REASON = { liquidity: 'thin liquidity', volume: 'low volume', 'market cap band': 'outside MC band', 'too new': 'too new', '5m momentum': 'no 5m momentum', '1h move': '1h move out of range', '6h trend': '6h weak or overextended', overextended: 'overextended', 'buy pressure': 'sellers in control', 'not SOL-quoted': 'not a SOL pair', 'no live market': 'no live market' };

async function askNotify() {
  if (typeof Notification === 'undefined') return false;
  if (Notification.permission === 'granted') return true;
  if (Notification.permission === 'denied') return false;
  return (await Notification.requestPermission()) === 'granted';
}

export function AdvancedWatchlist() {
  const { watchlist, toggle, updateWatch } = useWorkspace();
  const navigate = useNavigate();
  const [prices, setPrices] = useState(new Map());
  const [reads, setReads] = useState({});
  const [cats, setCats] = useState([]);
  const load = useCallback(async () => { if (watchlist.length) setPrices(await fetchLivePrices(watchlist)); }, [watchlist]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 4000); return () => clearInterval(t); }, [load]);
  useEffect(() => {
    const sol = watchlist.filter(p => p.chainId === 'solana');
    if (!sol.length) return;
    fetch('/api/cats/evaluate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pairs: sol.map(p => ({ chainId: p.chainId, pairAddress: p.pairAddress })) }) })
      .then(r => r.json()).then(d => setReads(d.reads || {})).catch(() => {});
  }, [watchlist]);
  useEffect(() => {
    let owner = null; try { owner = localStorage.getItem(OWNER_KEY); } catch {}
    if (owner) fetch(`/api/cats?ownerId=${encodeURIComponent(owner)}`).then(r => r.json()).then(d => setCats(d.cats || [])).catch(() => {});
  }, []);
  const assignCat = async catId => {
    const symbols = watchlist.filter(p => p.chainId === 'solana').map(p => p.baseToken?.symbol).filter(Boolean).join(', ');
    if (!symbols) { toast.error('Cats trade Solana pairs — star a Solana coin first.'); return; }
    const res = await fetch(`/api/cats/${catId}/action`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'controls', allowlist: symbols }) });
    toast[res.ok ? 'success' : 'error'](res.ok ? 'Your Cat now trades only your watchlist (paper).' : 'Could not update that Cat.');
  };
  const toggleNotify = async pair => {
    const on = !pair.alerts?.notify;
    if (on && !(await askNotify())) { toast.error('Browser notifications are blocked — allow them for this site to get alerts.'); }
    updateWatch(pair, { alerts: { notify: on } });
  };
  if (!watchlist.length) return <section className="adv-watch-empty" data-testid="advanced-watchlist"><Star size={24} /><h2>Star coins to track them here.</h2><p>Open any coin — from the globe, Discover, or Pump Radar — and hit the star. Starred coins keep live prices, alerts, and Fee's read even after they drop off the globe.</p></section>;
  return <section className="adv-watch" data-testid="advanced-watchlist">
    <div className="adv-watch-head"><div><span className="eyebrow"><Star size={13} /> YOUR WATCHLIST · LIVE</span><h2>{watchlist.length} coin{watchlist.length === 1 ? '' : 's'} on watch</h2></div>
      <div className="adv-watch-cat"><Cat size={15} /><span>Let a Cat paper-trade only these coins</span>{cats.length ? <select defaultValue="" onChange={e => e.target.value && assignCat(e.target.value)}><option value="" disabled>Choose your Cat…</option>{cats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select> : <button type="button" className="btn-outline" onClick={() => navigate('/terminal/feecat/agents?create=1')}>Create a Cat</button>}</div></div>
    <div className="adv-watch-table" role="table">
      <div className="adv-watch-row adv-watch-labels" role="row"><span>Coin</span><span>Live price</span><span>Since starred</span><span>Fee's read</span><span>Alerts (vs starred price)</span><span /></div>
      {watchlist.map(pair => {
        const key = tokenKey(pair);
        const live = prices.get(key);
        const usd = live?.usd ?? Number(pair.priceUsd);
        const since = pair.watchedPrice && usd ? (usd / pair.watchedPrice - 1) * 100 : null;
        const read = reads[pair.pairAddress];
        const a = pair.alerts || { up: 20, down: 15, notify: false };
        return <div className="adv-watch-row" role="row" key={key}>
          <button type="button" className="adv-watch-coin" onClick={() => navigate(`/?coin=${pair.chainId}:${pair.pairAddress}`)} title="Open war room"><TokenAvatar pair={pair} size={30} /><span><b>{pair.baseToken?.symbol}</b><small>{pair.chainId} · {formatUSD(pair.marketCap || pair.fdv)} MC at star</small></span></button>
          <span className="mono"><AnimatedNumber value={usd} format={formatLivePrice} /><small>{live?.source || 'snapshot'}</small></span>
          <span className={since == null ? 'muted' : since >= 0 ? 'positive mono' : 'negative mono'}>{since == null ? '—' : <AnimatedNumber value={since} format={formatPct} />}<small>{pair.watchedAt ? new Date(pair.watchedAt).toLocaleDateString() : ''}</small></span>
          <span className={`fee-read ${read ? (read.passes ? 'pass' : 'fail') : ''}`}><Radar size={12} />{pair.chainId !== 'solana' ? 'Solana only' : !read ? '…' : read.passes ? 'Passes — Fee would buy' : `Skip: ${REASON[read.reason] || read.reason}`}</span>
          <span className="adv-watch-alerts">
            <label>▲<input type="number" min="1" max="1000" value={a.up} onChange={e => updateWatch(pair, { alerts: { up: Number(e.target.value) } })} />%</label>
            <label>▼<input type="number" min="1" max="100" value={a.down} onChange={e => updateWatch(pair, { alerts: { down: Number(e.target.value) } })} />%</label>
            <button type="button" className={`icon-btn small-icon ${a.notify ? 'is-on' : ''}`} title={a.notify ? 'Notifications on' : 'Turn on notifications'} onClick={() => toggleNotify(pair)}>{a.notify ? <Bell size={13} /> : <BellOff size={13} />}</button>
          </span>
          <button type="button" className="icon-btn small-icon" title="Remove" onClick={() => toggle(pair)}><Trash2 size={13} /></button>
        </div>;
      })}
    </div>
    <p className="reputation-view-hint">Alerts fire as browser notifications while FEELESS is open in any tab. Prices: Jupiter for Solana, DexScreener elsewhere, every 4s.</p>
  </section>;
}

// Runs app-wide: checks starred coins every 15s and notifies when an alert threshold is crossed.
export function WatchlistAlerts() {
  const { watchlist, updateWatch } = useWorkspace();
  useEffect(() => {
    const armed = watchlist.filter(p => p.alerts?.notify && p.watchedPrice);
    if (!armed.length) return undefined;
    const check = async () => {
      const prices = await fetchLivePrices(armed);
      armed.forEach(pair => {
        const usd = prices.get(tokenKey(pair))?.usd;
        if (!usd) return;
        const move = (usd / pair.watchedPrice - 1) * 100;
        const side = move >= (pair.alerts.up ?? 20) ? 'up' : move <= -(pair.alerts.down ?? 15) ? 'down' : null;
        if (!side || pair.alerts.lastFired === side) return;
        const text = `${pair.baseToken?.symbol} ${side === 'up' ? 'up' : 'down'} ${formatPct(move)} since you starred it (${formatLivePrice(usd)})`;
        toast[side === 'up' ? 'success' : 'error'](text);
        try { if (typeof Notification !== 'undefined' && Notification.permission === 'granted') new Notification('FEELESS watchlist', { body: text, tag: tokenKey(pair) }); } catch {}
        updateWatch(pair, { alerts: { lastFired: side } });
      });
    };
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, [watchlist, updateWatch]);
  return null;
}

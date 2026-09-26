import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Bell, BellOff, BellRing, Cat, ChevronDown, Radar, Send, SlidersHorizontal, Star, Trash2 } from 'lucide-react';
import { DEFAULT_PUSH_PREFS, disablePush, enablePush, pushStatus, pushSupported, readPushPrefs, savePushPrefs, syncPush, testPush } from '../../lib/push';
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

const PUSH_FLAG = 'feeless-push-on';
const pushOn = () => { try { return localStorage.getItem(PUSH_FLAG) === '1'; } catch { return false; } };
const RULE_DEFAULTS = { up: 20, down: 15, move24h: 0, liqDrain: 30, volSpike: 4, feeRead: true, creatorFlag: true };

function PushPanel({ watchlist }) {
  const [prefs, setPrefs] = useState(readPushPrefs);
  const [status, setStatus] = useState({ subscribed: false });
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(() => pushStatus().then(setStatus).catch(() => {}), []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 20000); return () => clearInterval(t); }, [refresh]);
  useEffect(() => {
    savePushPrefs(prefs);
    if (!status.subscribed) return undefined;
    const t = setTimeout(() => syncPush(watchlist, prefs).catch(() => {}), 800);
    return () => clearTimeout(t);
  }, [watchlist, prefs, status.subscribed]);
  const run = async fn => { setBusy(true); try { await fn(); } catch (e) { toast.error(e.message); } finally { setBusy(false); refresh(); } };
  const setPref = (k, v) => setPrefs(p => ({ ...p, [k]: v }));
  const supported = pushSupported();
  return <div className={`push-panel ${status.subscribed ? 'is-on' : ''}`} data-testid="push-panel">
    <div className="push-panel-head">
      <BellRing size={16} />
      <div><b>Push alerts {status.subscribed ? '· ON' : '· OFF'}</b><small>{status.subscribed ? `Server is watching ${status.watching} coin${status.watching === 1 ? '' : 's'} every 30s — alerts arrive even with FEELESS closed.` : supported ? 'Get alerts on this device even when FEELESS is closed.' : 'This browser does not support push notifications.'}</small></div>
      <div className="push-actions">
        {status.subscribed ? <>
          <button type="button" className="btn-outline" disabled={busy} onClick={() => run(async () => { await testPush(); toast.success('Test alert sent — check your notifications.'); })}><Send size={13} />Send test</button>
          <button type="button" className="btn-outline" disabled={busy} onClick={() => run(async () => { await disablePush(); try { localStorage.setItem(PUSH_FLAG, '0'); } catch {} toast.success('Push alerts turned off.'); })}>Turn off</button>
        </> : <button type="button" className="btn-primary" disabled={busy || !supported || !watchlist.length} onClick={() => run(async () => { await enablePush(watchlist, prefs); try { localStorage.setItem(PUSH_FLAG, '1'); } catch {} toast.success('Push alerts on.'); })}><BellRing size={13} />{watchlist.length ? 'Enable push alerts' : 'Star a coin first'}</button>}
      </div>
    </div>
    <div className="push-filters">
      <label>Cooldown<select value={prefs.cooldownMin} onChange={e => setPref('cooldownMin', Number(e.target.value))}>{[10, 30, 60, 180].map(m => <option key={m} value={m}>{m < 60 ? `${m} min` : `${m / 60} h`}</option>)}</select></label>
      <label>Only coins with liquidity ≥<select value={prefs.minLiquidity} onChange={e => setPref('minLiquidity', Number(e.target.value))}>{[[0, 'any'], [10000, '$10K'], [50000, '$50K'], [250000, '$250K']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <label>Quiet hours<select value={prefs.quietStart == null ? 'off' : `${prefs.quietStart}-${prefs.quietEnd}`} onChange={e => { const v = e.target.value; if (v === 'off') setPrefs(p => ({ ...p, quietStart: null, quietEnd: null })); else { const [a, b] = v.split('-').map(Number); setPrefs(p => ({ ...p, quietStart: a, quietEnd: b })); } }}><option value="off">off</option><option value="23-7">11pm – 7am</option><option value="0-8">midnight – 8am</option><option value="22-9">10pm – 9am</option></select></label>
      <button type="button" className="push-reset" onClick={() => setPrefs(DEFAULT_PUSH_PREFS)}>Reset filters</button>
    </div>
    {status.recent?.length > 0 && <div className="push-recent"><small>RECENT ALERTS</small>{status.recent.slice(0, 5).map((r, i) => <span key={i}><i className={r.result === 'ok' ? 'ok' : 'err'} />{r.text}<time>{new Date(r.at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></span>)}</div>}
  </div>;
}

function RuleEditor({ pair, onChange }) {
  const r = { ...RULE_DEFAULTS, ...(pair.alerts || {}) };
  const num = (k, label, hint, max) => <label className="rule-num"><span>{label}</span><input type="number" min="0" max={max} value={r[k]} onChange={e => onChange({ [k]: Number(e.target.value) })} /><small>{hint}</small></label>;
  const tog = (k, label, hint) => <label className="rule-tog"><input type="checkbox" checked={!!r[k]} onChange={e => onChange({ [k]: e.target.checked })} /><span>{label}<small>{hint}</small></span></label>;
  return <div className="rule-editor">
    {num('up', '▲ Up %', 'from star price', 1000)}{num('down', '▼ Down %', 'from star price', 100)}{num('move24h', '24h move %', '0 = off', 100000)}
    {num('liqDrain', 'Liquidity drain %', 'vs liquidity at star', 100)}{num('volSpike', 'Volume spike ×', '5m pace vs daily', 50)}
    {tog('feeRead', "Fee's read", 'when Fee would buy')}{tog('creatorFlag', 'Creator flagged', 'rug / serial dumper')}
  </div>;
}

export function AdvancedWatchlist() {
  const { watchlist, toggle, updateWatch } = useWorkspace();
  const navigate = useNavigate();
  const [prices, setPrices] = useState(new Map());
  const [reads, setReads] = useState({});
  const [cats, setCats] = useState([]);
  const [open, setOpen] = useState('');
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
    <PushPanel watchlist={watchlist} />
    <div className="adv-watch-table" role="table">
      <div className="adv-watch-row adv-watch-labels" role="row"><span>Coin</span><span>Live price</span><span>Since starred</span><span>Fee's read</span><span>Alert rules</span><span /></div>
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
            <small className="rule-summary">▲{a.up ?? 20}% ▼{a.down ?? 15}%{a.liqDrain ? ` · liq −${a.liqDrain}%` : ''}{a.volSpike ? ` · vol ${a.volSpike}×` : ''}</small>
            <button type="button" className={`icon-btn small-icon ${a.notify ? 'is-on' : ''}`} title={a.notify ? 'In-tab alerts on' : 'In-tab alerts off'} onClick={() => toggleNotify(pair)}>{a.notify ? <Bell size={13} /> : <BellOff size={13} />}</button>
            <button type="button" className={`icon-btn small-icon ${open === key ? 'is-on' : ''}`} title="Alert rules" onClick={() => setOpen(open === key ? '' : key)}><SlidersHorizontal size={13} /><ChevronDown size={11} /></button>
          </span>
          <button type="button" className="icon-btn small-icon" title="Remove" onClick={() => toggle(pair)}><Trash2 size={13} /></button>
          {open === key && <RuleEditor pair={pair} onChange={patch => updateWatch(pair, { alerts: patch })} />}
        </div>;
      })}
    </div>
    <p className="reputation-view-hint">Push alerts are evaluated on the server every 30s. The bell turns on in-tab alerts for when push is off. Prices: Jupiter for Solana, DexScreener elsewhere.</p>
  </section>;
}

// Runs app-wide: checks starred coins every 15s and notifies when an alert threshold is crossed.
export function WatchlistAlerts() {
  const { watchlist, updateWatch } = useWorkspace();
  useEffect(() => {
    const armed = pushOn() ? [] : watchlist.filter(p => p.alerts?.notify && p.watchedPrice);
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

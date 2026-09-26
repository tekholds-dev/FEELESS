import React, { useEffect, useState } from 'react';
import { formatUSD, formatPct, shortAddress, formatAge } from '../../lib/dexscreener';
import { LivePrice } from '../terminal/LiveCells';

const ago = ts => { const s = Math.max(0, Date.now() / 1000 - ts); return s < 60 ? `${Math.floor(s)}s` : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };

// Every coin gets a profile: identity + market + holder intel on the front, live activity on the back.
export function CoinProfile({ chain, pairAddress }) {
  const [pair, setPair] = useState(null);
  const [intel, setIntel] = useState(null);
  const [rep, setRep] = useState(null);
  const [flipped, setFlipped] = useState(false);
  const [calls, setCalls] = useState([]);
  const [chat, setChat] = useState([]);
  const [trades, setTrades] = useState([]);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(`https://api.dexscreener.com/latest/dex/pairs/${chain}/${pairAddress}`).then(r => r.json()).then(d => alive && setPair(d.pairs?.[0] || null)).catch(() => {});
    load(); const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, [chain, pairAddress]);
  const mint = pair?.baseToken?.address;
  useEffect(() => {
    if (!mint) return;
    fetch(`/api/reputation/intel/${chain}/${mint}`).then(r => r.json()).then(setIntel).catch(() => {});
    fetch(`/api/reputation/token/${chain}/${pairAddress}?baseTokenAddress=${mint}`).then(r => r.json()).then(setRep).catch(() => {});
  }, [chain, pairAddress, mint]);
  useEffect(() => {
    if (!flipped) return undefined;
    let alive = true;
    const load = () => {
      fetch(`/api/reputation/calls/recent?pair=${pairAddress}&limit=30`).then(r => r.json()).then(d => alive && setCalls(d.calls || [])).catch(() => {});
      Promise.all(['bulls', 'trenches', 'bears'].map(side => fetch(`/api/reputation/chat/coin-${chain}-${pairAddress}-${side}`).then(r => r.json()).then(d => (d.messages || []).map(m => ({ ...m, side }))).catch(() => [])))
        .then(all => alive && setChat(all.flat().sort((a, b) => b.ts - a.ts).slice(0, 30)));
      fetch(`/api/candles/trades/${chain}/${pairAddress}`).then(r => r.json()).then(d => alive && d.trades?.length && setTrades(d.trades.slice(0, 40))).catch(() => {});
    };
    load(); const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, [flipped, chain, pairAddress]);
  if (!pair) return <section className="coin-profile" data-testid="coin-profile"><p className="wp-bio">Loading coin…</p></section>;
  const tx = pair.txns?.h24 || {}; const b = tx.buys || 0; const s = tx.sells || 0;
  const snip = intel?.sniperWallets?.length ?? null; const bund = intel?.bundledWallets?.length ?? null;
  return <section className="coin-profile" data-testid="coin-profile">
    <div className="cp-banner" style={pair.info?.header ? { backgroundImage: `url(${pair.info.header})` } : undefined} />
    <div className="cp-head">
      <div className="cp-logo">{pair.info?.imageUrl ? <img src={pair.info.imageUrl} alt="" /> : <span>{pair.baseToken.symbol.slice(0, 2)}</span>}</div>
      <div className="cp-id"><h1>${pair.baseToken.symbol} <small>{pair.baseToken.name}</small></h1><span>{chain} · {pair.dexId} · pool {formatAge(pair.pairCreatedAt)} old · <code>{shortAddress(mint)}</code></span>
        <div className="cp-links">{(pair.info?.socials || []).map(x => <a key={x.url} href={x.url} target="_blank" rel="noopener noreferrer">{x.type}</a>)}{(pair.info?.websites || []).slice(0, 1).map(x => <a key={x.url} href={x.url} target="_blank" rel="noopener noreferrer">website</a>)}<a href={`/?coin=${chain}:${pairAddress}`}>Chart + trade →</a></div></div>
      <button type="button" className="btn-outline wp-flip-btn" data-testid="coin-flip" onClick={() => setFlipped(f => !f)}>{flipped ? '↺ Profile' : '↻ Activity'}</button>
    </div>
    {!flipped ? <div className="cp-grid">
      <div className="cp-card"><h4>Market</h4>
        <div className="cp-kv"><span>Price</span><b><LivePrice pair={pair} precise /></b></div>
        <div className="cp-kv"><span>5m / 1h / 24h</span><b>{formatPct(pair.priceChange?.m5)} · {formatPct(pair.priceChange?.h1)} · {formatPct(pair.priceChange?.h24)}</b></div>
        <div className="cp-kv"><span>Market cap</span><b>{formatUSD(pair.marketCap || pair.fdv)}</b></div>
        <div className="cp-kv"><span>Liquidity</span><b>{formatUSD(pair.liquidity?.usd)}</b></div>
        <div className="cp-kv"><span>24h volume</span><b>{formatUSD(pair.volume?.h24)}</b></div>
        <div className="cp-flow"><i style={{ width: `${b + s ? (b / (b + s)) * 100 : 50}%` }} /><small>{b.toLocaleString()} buys · {s.toLocaleString()} sells (24h)</small></div>
      </div>
      <div className="cp-card"><h4>Holder intel <small>FEELESS on-chain</small></h4>
        {!intel ? <p className="wp-bio">Scanning holders…</p> : <>
          <div className="cp-kv"><span>Top 10 wallets</span><b className={intel.top10Pct > 35 ? 'negative' : 'positive'}>{intel.top10Pct != null ? `${intel.top10Pct.toFixed(1)}%` : '—'}</b></div>
          <div className="cp-kv"><span>Insiders / dev</span><b>{intel.insidersHoldingPct?.toFixed?.(1) ?? '—'}% / {intel.devHoldingPct?.toFixed?.(1) ?? '—'}%</b></div>
          <div className="cp-kv"><span>🎯 Snipers</span><b className={snip > 10 ? 'negative' : ''}>{snip ?? '—'}</b></div>
          <div className="cp-kv"><span>📦 Bundled wallets</span><b className={bund > 0 ? 'negative' : ''}>{bund ?? '—'}</b></div>
          {(intel.flags || []).map(f => <p key={f} className="cp-flag">⚠️ {f}</p>)}
        </>}
      </div>
      <div className="cp-card"><h4>Creator</h4>
        {!rep?.creator ? <p className="wp-bio">Creator not identified yet (mint authority renounced or history still loading).</p> : <>
          <a className="cp-creator" href={`/terminal/profile/${rep.creator}`}>{shortAddress(rep.creator)} ↗</a>
          <div className="cp-kv"><span>Reputation</span><b className={rep.badge === 'flagged' ? 'negative' : rep.badge === 'trusted' ? 'positive' : ''}>{rep.badge}{rep.score != null ? ` · ${rep.score}` : ''}</b></div>
        </>}
      </div>
    </div> : <div className="cp-grid cp-activity" data-testid="coin-activity">
      <div className="cp-card"><h4>Live trades</h4>{!trades.length ? <p className="wp-bio">Trade feed is rate-limited — refreshing…</p> : trades.map((t, i) => <div key={i} className={`cp-trade ${t.kind === 'buy' || t.type === 'buy' ? 'buy' : 'sell'}`}><b>{(t.kind || t.type || '').toUpperCase()}</b><span>{formatUSD(t.volumeUsd ?? t.usd)}</span><small>{t.maker || t.wallet ? <a href={`/terminal/profile/${t.maker || t.wallet}`}>{shortAddress(t.maker || t.wallet)}</a> : ''} · {t.ts || t.time ? ago((t.ts || t.time) > 1e12 ? (t.ts || t.time) / 1000 : (t.ts || t.time)) : ''}</small></div>)}</div>
      <div className="cp-card"><h4>Calls <small>Call Ledger</small></h4>{!calls.length ? <p className="wp-bio">No calls yet.</p> : calls.map(c => <div key={c.id} className="cp-call"><b>{c.caller}</b><span>@ {formatUSD(c.mcAtCall)}</span><small>{ago(c.at)} ago</small></div>)}</div>
      <div className="cp-card"><h4>Chat mentions</h4>{!chat.length ? <p className="wp-bio">Quiet so far.</p> : chat.map(m => <div key={m.id} className="cp-msg"><b>{m.username}</b> <em>{m.side}</em><p>{m.text}</p></div>)}</div>
    </div>}
  </section>;
}

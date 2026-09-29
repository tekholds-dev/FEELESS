import React, { useEffect, useState } from 'react';
import { Activity, Rocket, Zap, ArrowUpRight } from 'lucide-react';
import { formatUSD, shortAddress } from '../../lib/dexscreener';
import { usePumpNetwork, launchToPair, ageLabel, buyPressure, TRADE_STREAM_NOTE } from '../../lib/pumpNetwork';
import { isPumpCoin } from '../../lib/pumpCallouts';

const useNow = (ms = 1000) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(t); }, [ms]);
  return now;
};

const DUST_DEV_BUY_SOL = 0.05;

const CurveBar = ({ pct }) => pct == null ? null : <span className="pump-curve" title={`≈${pct}% of the bonding curve filled`}><i style={{ width: `${Math.max(2, pct)}%` }} /><em>{pct}%</em></span>;

// Live pump.fun launches and migrations from the FEELESS Pump network (PumpPortal stream).
export const PumpPulse = ({ onSelect }) => {
  const { data, error } = usePumpNetwork('/api/pump/pulse?limit=30', 2000);
  const now = useNow();
  const series = data?.launchesPerMinute || [];
  const peak = Math.max(1, ...series);
  const live = data?.status === 'live';
  const [serious, setSerious] = useState(() => { try { return localStorage.getItem('feeless-pulse-serious') !== '0'; } catch { return true; } });
  useEffect(() => { try { localStorage.setItem('feeless-pulse-serious', serious ? '1' : '0'); } catch {} }, [serious]);
  // "Serious only": hide dust dev buys and repeat tickers (copycat spam) so real launches stand out.
  const launches = (data?.launches || []).filter((l, i, all) => !serious
    || (Number(l.devBuySol) >= DUST_DEV_BUY_SOL && all.findIndex(x => (x.symbol || '').toLowerCase() === (l.symbol || '').toLowerCase()) === i));
  return <section className="pump-pulse" data-testid="pump-pulse">
    <header className="pump-pulse-head">
      <span className="eyebrow"><span className={`pulse-dot ${live ? 'on' : ''}`} />PUMP PULSE · FEELESS PUMP NETWORK</span>
      <span className="pump-pulse-state">{error ? 'Offline' : live ? 'Live · PumpPortal stream' : data ? 'Reconnecting…' : 'Connecting…'}</span>
    </header>
    <div className="pump-pulse-kpis">
      <span><small>Launches / min</small><b>{data ? data.lastMinute : '—'}</b></span>
      <span className="pump-pulse-spark" aria-label="Launches per minute, last 15 minutes">{series.map((c, i) => <i key={i} style={{ height: `${Math.round(c / peak * 100)}%` }} title={`${c} launches`} />)}</span>
      <span><small>Migrations seen</small><b>{data?.migrations?.length ?? '—'}</b></span>
      <span><small>SOL</small><b>{data?.solUsd ? `$${Number(data.solUsd).toFixed(2)}` : '—'}</b></span>
    </div>
    {error && !data && <p className="pump-pulse-empty">Pump network is offline: {error}</p>}
    <div className="pump-pulse-cols">
      <div>
        <h4><Rocket size={13} />Fresh launches<label className="pump-serious"><input type="checkbox" checked={serious} onChange={e => setSerious(e.target.checked)} />Serious only</label></h4>
        <ol className="pump-pulse-list">{launches.slice(0, 12).map(l => <li key={l.mint}>
          <button type="button" onClick={() => onSelect?.(launchToPair(l))} data-testid={`pump-launch-${l.mint}`}>
            <span className="pump-sym">{(l.symbol || '?').slice(0, 3).toUpperCase()}</span>
            <span className="pump-name"><b>{l.symbol || 'Unnamed'}</b><small>{l.name}</small></span>
            <span className="pump-meta"><small>{ageLabel(l.at, now)} ago</small><small>dev {l.devBuySol} SOL</small></span>
            <span className="pump-mc"><b>{l.marketCapUsd ? formatUSD(l.marketCapUsd) : '—'}</b><CurveBar pct={l.curveProgress} /></span>
            {l.mayhem && <em className="pump-tag">MAYHEM</em>}
          </button>
        </li>)}</ol>
        {data && !launches.length && <p className="pump-pulse-empty">{serious && data.launches?.length ? 'Only dust and copycat launches right now. Untick “Serious only” to see them.' : 'Waiting for the next launch…'}</p>}
      </div>
      <div>
        <h4><Zap size={13} />Migrations</h4>
        <ol className="pump-pulse-list is-migrations">{(data?.migrations || []).slice(0, 8).map(m => <li key={m.signature || m.mint}>
          <a href={`https://pump.fun/coin/${m.mint}`} target="_blank" rel="noopener noreferrer">
            <span className="pump-name"><b>{m.symbol || shortAddress(m.mint)}</b><small>{m.pool === 'pump-amm' ? 'Graduated → PumpSwap' : `Migrated → ${m.pool || 'pool'}`}</small></span>
            <span className="pump-meta"><small>{ageLabel(m.at, now)} ago</small></span><ArrowUpRight size={12} />
          </a>
        </li>)}</ol>
        {data && !data.migrations?.length && <p className="pump-pulse-empty">No migrations since the stream connected.</p>}
      </div>
    </div>
  </section>;
};

// Live order flow for a Pump coin on the trench floor: pressure, curve progress and the trade tape.
export const PumpFlow = ({ pair }) => {
  const mint = pair?.baseToken?.address;
  const enabled = isPumpCoin(pair);
  const { data } = usePumpNetwork(enabled ? `/api/pump/coin/${encodeURIComponent(mint)}/flow` : null, 2000);
  const now = useNow();
  if (!enabled) return null;
  const pressure = buyPressure(data, pair);
  const tapeLive = data?.status === 'live';
  const trades = data?.trades || [];
  return <section className="pump-flow" data-testid="pump-flow">
    <header><span className="eyebrow"><Activity size={13} />PUMP FLOW · {pair.baseToken?.symbol}</span><small>{tapeLive ? 'Live trade tape' : TRADE_STREAM_NOTE[data?.status] || 'Pump network connecting…'}</small></header>
    <div className="pump-flow-stats">
      <div className="pump-pressure">
        <span><small>5m buy pressure</small><b className={pressure && pressure.pct >= 50 ? 'positive' : 'negative'}>{pressure ? `${pressure.pct}%` : '—'}</b></span>
        <div className="pump-pressure-bar"><i style={{ width: `${pressure?.pct ?? 50}%` }} /></div>
        <small>{pressure?.basis || 'No 5m trades reported yet'}</small>
      </div>
      <span><small>Net 5m</small><b className={Number(data?.netSol) >= 0 ? 'positive' : 'negative'}>{tapeLive ? `${data.netSol >= 0 ? '+' : ''}${data.netSol} SOL` : '—'}</b></span>
      <span><small>Traders 5m</small><b>{tapeLive ? data.traders : '—'}</b></span>
      <span><small>Whales ≥2 SOL</small><b>{tapeLive ? data.whales : '—'}</b></span>
      <span><small>Bonding curve</small>{data?.curveProgress != null ? <CurveBar pct={data.curveProgress} /> : <b>{pair.dexId === 'pump.fun' ? '—' : 'Graduated'}</b>}</span>
    </div>
    {tapeLive && <ol className="pump-tape" aria-label="Live trades">{trades.slice(0, 14).map(t => <li key={t.signature} className={t.side}>
      <b>{t.side === 'buy' ? 'BUY' : 'SELL'}</b><span>{t.sol} SOL{t.usd ? <small> ${t.usd.toLocaleString()}</small> : null}</span>
      <span className="pump-tape-trader">{shortAddress(t.trader)}</span><time>{ageLabel(t.at, now)}</time>
    </li>)}{!trades.length && <li className="pump-tape-wait">Watching for the next trade…</li>}</ol>}
  </section>;
};

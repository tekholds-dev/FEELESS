import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createChart, createSeriesMarkers, CandlestickSeries, HistogramSeries, LineSeries, ColorType } from 'lightweight-charts';
import { useMarket } from '../../hooks/useMarket';
import { dexUrl, formatUSD } from '../../lib/dexscreener';
import { DataStatus } from './MarketPrimitives';
import { recordPricePoint, getPriceTrail } from '../../lib/priceHistory';
import { recordCandleTick, fetchFeelessCandles } from '../../lib/candles';
import { fetchLivePrice } from '../../lib/livePrice';

const LIVE_INTERVAL_SECONDS = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 };

export const PriceChart = ({ pair, interval, showVolume, metric = 'price', markers = [] }) => {
  const container = useRef(null);
  const seriesRef = useRef(null);
  const lastBarRef = useRef(null);
  const markersRef = useRef(null);
  const [livePrice, setLivePrice] = useState(null);
  const [feelessCandles, setFeelessCandles] = useState([]);
  const [candleProvider, setCandleProvider] = useState('');
  const [candlesLoaded, setCandlesLoaded] = useState(false);
  const priceMetric = metric === 'price';
  const [dayMode, setDayMode] = useState(() => typeof document !== 'undefined' && document.body.classList.contains('theme-day'));
  // Candles come only from the FEELESS candle service (GeckoTerminal behind a shared cache + our own ticks).
  const { data, loading, error } = useMarket(null);
  const providerError = error || data?.error;
  const metricLabel = metric === 'marketCap' ? 'Market cap' : 'FDV';
  const metricValue = metric === 'marketCap' ? pair?.marketCap : pair?.fdv;
  const metricAvailable = metricValue !== null && metricValue !== undefined && metricValue !== '' && Number.isFinite(Number(metricValue));
  const price = Number(pair?.priceUsd);
  const ratio = !priceMetric && metricAvailable && price > 0 ? Number(metricValue) / price : 1;
  const metricChart = !priceMetric && metricAvailable && price > 0;
  const charting = priceMetric || metricChart;
  const candleRows = useMemo(() => Array.isArray(data?.candles)
    ? [...new Map(data.candles
      .filter(row => Array.isArray(row) && row.length >= 6 && row.slice(0, 6).every(value => Number.isFinite(Number(value))))
      .map(row => row.slice(0, 6).map(Number))
      .map(row => [row[0], row])).values()].sort((a, b) => a[0] - b[0])
    : [], [data?.candles]);

  // Record every live price we see for this pair, regardless of candle provider health —
  // both locally (instant fallback for this browser) and server-side (so the FEELESS
  // candle aggregator keeps building real, shared OHLCV history for everyone).
  useEffect(() => {
    if (pair?.pairAddress && pair?.priceUsd != null) {
      recordPricePoint(pair.pairAddress, pair.priceUsd);
      recordCandleTick(pair.chainId, pair.pairAddress, pair.priceUsd, pair.volume?.h24);
    }
  }, [pair?.chainId, pair?.pairAddress, pair?.priceUsd, pair?.volume?.h24]);

  const needsFallback = (priceMetric || metricChart) && candlesLoaded;
  useEffect(() => {
    setFeelessCandles([]);
    setCandlesLoaded(false);
    if (!pair?.pairAddress) return undefined;
    let alive = true;
    const load = () => fetchFeelessCandles(pair.chainId, pair.pairAddress, interval)
      .then(res => { if (alive && Array.isArray(res?.candles)) { setFeelessCandles(res.candles); setCandleProvider(res.provider || 'FEELESS'); } })
      .catch(() => {})
      .finally(() => { if (alive) setCandlesLoaded(true); });
    load();
    const timer = setInterval(load, 60000);
    return () => { alive = false; clearInterval(timer); };
  }, [pair?.chainId, pair?.pairAddress, interval]);
  const usingFeelessCandles = needsFallback && feelessCandles.length >= 2;

  const usingFallbackTrail = needsFallback && !usingFeelessCandles;
  const trail = useMemo(() => {
    if (!usingFallbackTrail || !pair?.pairAddress) return [];
    const points = getPriceTrail(pair.pairAddress);
    return points.map(pt => ({ time: Math.floor(pt.t / 1000), value: pt.p * ratio }))
      .filter((pt, i, arr) => i === 0 || pt.time !== arr[i - 1].time);
  }, [usingFallbackTrail, pair?.pairAddress, ratio]);
  const baseCandles = useMemo(() => candleRows.length ? candleRows : usingFeelessCandles ? feelessCandles : [], [candleRows, usingFeelessCandles, feelessCandles]);
  const displayCandles = useMemo(() => ratio === 1 ? baseCandles : baseCandles.map(([t, o, h, l, c, v]) => [t, o * ratio, h * ratio, l * ratio, c * ratio, v]), [baseCandles, ratio]);
  const hasChart = displayCandles.length > 0 || trail.length >= 2;
  useEffect(() => {
    if (typeof document === 'undefined') return undefined;
    const sync = () => setDayMode(document.body.classList.contains('theme-day'));
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!container.current || !hasChart) return;
    container.current.replaceChildren();
    const chart = createChart(container.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: dayMode ? '#edf4ef' : '#080e0d' },
        textColor: dayMode ? '#315b43' : '#8c9b94',
        fontFamily: 'JetBrains Mono',
        fontSize: 10,
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: dayMode ? '#d8e8dc' : '#ffffff04' },
        horzLines: { color: dayMode ? '#d8e8dc' : '#ffffff06' },
      },
      rightPriceScale: { borderColor: dayMode ? '#aac7b3' : '#203129' },
      timeScale: { borderColor: dayMode ? '#aac7b3' : '#203129', timeVisible: true, secondsVisible: false, maxBarSpacing: 14, rightOffset: 4 },
      localization: { locale: 'en-US', priceFormatter: n => formatUSD(n) }, crosshair: { mode: 0 },
    });
    if (displayCandles.length) {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: dayMode ? '#08764e' : '#00e7a0',
        downColor: '#b42346',
        wickUpColor: dayMode ? '#08764e' : '#00e7a0',
        wickDownColor: '#b42346',
        borderVisible: false,
        priceFormat: { type: 'custom', formatter: n => formatUSD(n) },
      });
      const bars = displayCandles.map(([time, open, high, low, close]) => ({ time, open, high, low, close }));
      series.setData(bars);
      seriesRef.current = { kind: 'candle', series };
      lastBarRef.current = bars[bars.length - 1] || null;
      series.priceScale().applyOptions({ scaleMargins: { top: .12, bottom: showVolume ? .24 : .12 } });
      if (showVolume) {
        const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '', lastValueVisible: false, priceLineVisible: false });
        volume.priceScale().applyOptions({ scaleMargins: { top: .84, bottom: 0 } });
        volume.setData(displayCandles.map(([time, open, , , close, value]) => ({
          time,
          value,
          color: close >= open
            ? (dayMode ? '#08764e55' : '#00e7a042')
            : (dayMode ? '#b4234655' : '#f5688050'),
        })));
      }
    } else {
      const line = chart.addSeries(LineSeries, {
        color: dayMode ? '#08764e' : '#00e7a0',
        lineWidth: 2,
        priceFormat: { type: 'custom', formatter: n => formatUSD(n) },
      });
      line.setData(trail);
      seriesRef.current = { kind: 'line', series: line };
      lastBarRef.current = trail.length ? { ...trail[trail.length - 1] } : null;
      line.priceScale().applyOptions({ scaleMargins: { top: .16, bottom: .16 } });
    }
    chart.timeScale().fitContent();
    return () => { seriesRef.current = null; markersRef.current = null; chart.remove(); };
  }, [displayCandles, trail, hasChart, dayMode, showVolume]);

  // Meta overlays (Trenches calls, Fee's trades) snapped to the candle they happened in.
  useEffect(() => {
    const ref = seriesRef.current;
    if (!ref) return;
    const bucket = LIVE_INTERVAL_SECONDS[interval] || 3600;
    const list = (markers || []).filter(m => Number.isFinite(m.time))
      .map(m => ({ ...m, time: Math.floor(m.time / bucket) * bucket }))
      .sort((a, b) => a.time - b.time);
    if (!markersRef.current) markersRef.current = createSeriesMarkers(ref.series, list);
    else markersRef.current.setMarkers(list);
  }, [markers, interval, displayCandles, trail, dayMode]);

  // Live ticks: every 3s pull the pair's current price straight from DexScreener and
  // update the forming candle in place (no redraw, zoom preserved).
  useEffect(() => {
    if (!charting || !pair?.pairAddress || !pair?.chainId) return undefined;
    const bucket = LIVE_INTERVAL_SECONDS[interval] || 3600;
    let alive = true;
    const tick = async () => {
      if (document.hidden) return;
      try {
        const live = await fetchLivePrice(pair);
        const usd = Number(live?.usd);
        if (!alive || !(usd > 0)) return;
        setLivePrice({ usd, change: live?.change24h, at: Date.now(), source: live?.source });
        const value = usd * ratio;
        const ref = seriesRef.current;
        const last = lastBarRef.current;
        if (!ref || !last) return;
        const t = Math.floor(Date.now() / 1000 / bucket) * bucket;
        if (ref.kind === 'candle') {
          const bar = t > last.time ? { time: t, open: last.close, high: Math.max(last.close, value), low: Math.min(last.close, value), close: value }
            : { ...last, high: Math.max(last.high, value), low: Math.min(last.low, value), close: value };
          ref.series.update(bar);
          lastBarRef.current = bar;
        } else {
          const point = { time: Math.max(t, last.time), value };
          ref.series.update(point);
          lastBarRef.current = point;
        }
      } catch {
        // Keep the last real candle; never invent a tick.
      }
    };
    tick();
    const timer = setInterval(tick, 2000);
    return () => { alive = false; clearInterval(timer); };
  }, [charting, pair?.baseToken?.address, pair?.chainId, pair?.pairAddress, interval, ratio]);
  return <div className="chart-area" data-testid="price-chart">
    {charting && !candlesLoaded && <div className="chart-message" data-testid="chart-loading"><span className="loader" />Loading on-chain candles…</div>}
    {charting && !loading && usingFallbackTrail && trail.length < 2 && <div className="chart-message chart-building" role="status" data-testid="chart-building">
      <span className="signal-lines"><i /><i /><i /><i /></span>
      <strong>Building a live price trail for this pool.</strong>
      <span>Full candle history is temporarily unavailable from the provider. FEELESS is recording every price it observes here — check back shortly, or view the external chart now.</span>
      <a data-testid="chart-fallback-link" href={dexUrl(pair)} target="_blank" rel="noreferrer">Open chart on DexScreener ↗</a>
    </div>}
    {charting && usingFeelessCandles && candleProvider !== 'GeckoTerminal' && <div className="chart-stale-note" role="status">Showing FEELESS-observed candles ({feelessCandles.length} bars from real recorded prices) — full {data?.provider || 'provider'} candle history is temporarily unavailable.</div>}
    {charting && usingFallbackTrail && trail.length >= 2 && <div className="chart-stale-note" role="status">Live price trail recorded by this browser — full {data?.provider || 'provider'} candle history is temporarily unavailable.</div>}
    {metricChart && hasChart && <div className="chart-stale-note metric-derived-note" role="status" data-testid={`chart-${metric}-derived`}>{metricLabel} chart = real price candles × token supply (supply is fixed, so the shape is exact). Now {formatUSD(metricValue)}.</div>}
    {!priceMetric && metricAvailable && !loading && !hasChart && !usingFallbackTrail && <div className="metric-snapshot" data-testid={`chart-${metric}-snapshot`}><span className="metric-snapshot-label">{metricLabel} snapshot</span><strong>{formatUSD(metricValue)}</strong><small>Provider supplied the current {metricLabel.toLowerCase()} only. Historical {metricLabel.toLowerCase()} candles are unavailable.</small></div>}
    {!priceMetric && !metricAvailable && <div className="chart-message metric-unavailable" role="status" data-testid={`chart-${metric}-unavailable`}><strong>{metricLabel} unavailable</strong><span>The provider did not supply a {metricLabel.toLowerCase()} value for this pair. No value is estimated.</span></div>}
    {charting && hasChart && <div className="candle-canvas" ref={container} data-testid="candlestick-canvas" />}
    <div className="chart-source"><span>{priceMetric ? (candleRows.length ? `${data?.provider || 'GeckoTerminal'} · OHLCV` : usingFeelessCandles ? `${candleProvider || 'FEELESS'} · OHLCV` : 'FEELESS local trail · price only') : metricChart && hasChart ? `${metricLabel} · derived from ${candleProvider || 'FEELESS'} price candles` : `Provider pair snapshot · ${metricLabel}`}</span>{charting ? (livePrice && Date.now() - livePrice.at < 10000 ? <span className="data-status live-tick"><i />LIVE · {livePrice.source || 'DEX'}</span> : <DataStatus data={data} id="chart-data-status" />) : <span className="data-status"><i />{metricAvailable ? 'LIVE · snapshot' : 'UNAVAILABLE'}</span>}</div>
  </div>;
};
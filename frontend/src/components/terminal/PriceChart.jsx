import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createChart, createSeriesMarkers, CandlestickSeries, HistogramSeries, LineSeries, ColorType } from 'lightweight-charts';
import { useMarket } from '../../hooks/useMarket';
import { dexUrl, formatUSD } from '../../lib/dexscreener';
import { DataStatus } from './MarketPrimitives';
import { recordPricePoint, getPriceTrail } from '../../lib/priceHistory';
import { recordCandleTick, fetchFeelessCandles, getCachedCandles, cacheCandles, prefetchAllIntervals } from '../../lib/candles';
import { scrubCandles } from '../../lib/chartMath';
import { fetchLivePrice } from '../../lib/livePrice';
import { computeFeeRead } from './FeeLiveRead';
import { snapMarkers, tradeLevels } from '../../lib/chartMarkers';

const LIVE_INTERVAL_SECONDS = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 };


const ageLabel = t => { const s = (Date.now() - t) / 1000; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : s < 86400 * 60 ? `${Math.round(s / 86400)}d` : `${Math.round(s / 86400 / 30)}mo`; };

export const PriceChart = ({ pair, interval, showVolume, metric = 'price', markers = [], feeLive: feeLiveProp, userEntry = null, userTrades = null }) => {
  // Every chart gets the same tools: pages that don't control Fee's overlay get a built-in toggle.
  const [feeOwn, setFeeOwn] = useState(false);
  const feeLive = feeLiveProp ?? feeOwn;
  // Coin age always shows: pool creation time, or the coin's earliest pool when the pool lacks it.
  const [createdAt, setCreatedAt] = useState(pair?.pairCreatedAt || null);
  useEffect(() => {
    setCreatedAt(pair?.pairCreatedAt || null);
    const mint = pair?.baseToken?.address;
    if (pair?.pairCreatedAt || !mint || !pair?.chainId) return undefined;
    let alive = true;
    fetch(`https://api.dexscreener.com/token-pairs/v1/${pair.chainId}/${mint}`).then(r => r.json())
      .then(list => { const ts = (list || []).map(x => x.pairCreatedAt).filter(Boolean); if (alive && ts.length) setCreatedAt(Math.min(...ts)); }).catch(() => {});
    return () => { alive = false; };
  }, [pair?.chainId, pair?.baseToken?.address, pair?.pairCreatedAt]);
  const container = useRef(null);
  const seriesRef = useRef(null);
  const lastBarRef = useRef(null);
  const markersRef = useRef(null);
  const [livePrice, setLivePrice] = useState(null);
  const [feePos, setFeePos] = useState(null);
  const [feeOpen, setFeeOpen] = useState(false);
  const priceLinesRef = useRef([]);
  const [feelessCandles, setFeelessCandles] = useState([]);
  // Chart style: 'auto' (line when data is sparse, candles otherwise), or forced 'line' / 'candle'.
  const sparseRef = useRef(false);
  const [chartStyle, setChartStyle] = useState(() => { try { return localStorage.getItem('feeless:chart-style') || 'auto'; } catch { return 'auto'; } });
  const toggleStyle = () => setChartStyle(cur => { const next = sparseRef.current ? 'candle' : 'line'; try { localStorage.setItem('feeless:chart-style', next); } catch { /* private mode */ } return next; });
  const [olderCandles, setOlderCandles] = useState([]);
  const olderState = useRef({ loading: false, exhausted: false });
  const rangeRef = useRef(null);
  const [candleProvider, setCandleProvider] = useState('');
  const [candlesLoaded, setCandlesLoaded] = useState(false);
  const priceMetric = metric === 'price';
  const [dayMode, setDayMode] = useState(() => typeof document !== 'undefined' && document.body.classList.contains('theme-day'));
  // Candles come only from the FEELESS candle service (Jupiter/Alchemy/Helius behind a shared cache + our own ticks).
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
  // Dependencies below are explicit; CRA's older hook parser misreads optional nested pair fields.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const cached = pair?.pairAddress ? getCachedCandles(pair.chainId, pair.pairAddress, interval) : null;
    setFeelessCandles(cached?.candles || []);
    if (cached) setCandleProvider(cached.provider || 'FEELESS');
    setOlderCandles([]);
    olderState.current = { loading: false, exhausted: false };
    rangeRef.current = null;
    setCandlesLoaded(!!cached);
    if (!pair?.pairAddress) return undefined;
    let alive = true;
    const load = () => fetchFeelessCandles(pair.chainId, pair.pairAddress, interval, undefined, pair.baseToken?.address)
      .then(res => { if (!res?.partial) cacheCandles(pair.chainId, pair.pairAddress, interval, res); if (alive && Array.isArray(res?.candles)) { setFeelessCandles(res.candles); setCandleProvider(res.provider || 'FEELESS'); if (res.partial) setTimeout(() => { if (alive) load(); }, 2500); } })
      .catch(() => {})
      .finally(() => { if (alive) setCandlesLoaded(true); });
    load();
    prefetchAllIntervals(pair.chainId, pair.pairAddress, pair.baseToken?.address);
    // Poll fast until real provider candles arrive, then settle to once a minute.
    let timer = setInterval(() => { load(); }, 15000);
    const settle = setTimeout(() => { clearInterval(timer); timer = setInterval(load, 60000); }, 120000);
    return () => { alive = false; clearInterval(timer); clearTimeout(settle); };
  }, [pair?.baseToken?.address, pair?.chainId, pair?.pairAddress, interval]);
  const allFeeless = useMemo(() => {
    if (!olderCandles.length) return feelessCandles;
    const first = feelessCandles.length ? feelessCandles[0][0] : Infinity;
    return [...olderCandles.filter(c => c[0] < first), ...feelessCandles];
  }, [olderCandles, feelessCandles]);
  const usingFeelessCandles = needsFallback && allFeeless.length >= 2;

  const usingFallbackTrail = needsFallback && !usingFeelessCandles;
  const trail = useMemo(() => {
    if (!usingFallbackTrail || !pair?.pairAddress) return [];
    const points = getPriceTrail(pair.pairAddress);
    return points.map(pt => ({ time: Math.floor(pt.t / 1000), value: pt.p * ratio }))
      .filter((pt, i, arr) => i === 0 || pt.time !== arr[i - 1].time);
  }, [usingFallbackTrail, pair?.pairAddress, ratio]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const baseCandles = useMemo(() => candleRows.length ? scrubCandles(candleRows) : usingFeelessCandles ? scrubCandles(allFeeless) : [], [candleRows, usingFeelessCandles, allFeeless]);
  const displayCandles = useMemo(() => ratio === 1 ? baseCandles : baseCandles.map(([t, o, h, l, c, v]) => [t, o * ratio, h * ratio, l * ratio, c * ratio, v]), [baseCandles, ratio]);
  const hasChart = displayCandles.length > 0 || trail.length >= 2;
  // The socket/polling lifecycle is intentionally keyed to the full pair object and its stable identifiers.
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // Price precision sized to the coin: sub-cent memecoins need 6–10 decimals or every axis tick reads $0.00.
    const refPrice = Math.abs(Number(displayCandles.length ? displayCandles[displayCandles.length - 1][4] : trail[trail.length - 1]?.value) || 1);
    const decimals = Math.min(12, Math.max(2, -Math.floor(Math.log10(refPrice)) + 3));
    const minMove = Number((10 ** -decimals).toFixed(decimals));
    const axisFormat = n => (Math.abs(n) >= 1000 ? formatUSD(n) : `$${Number(n).toFixed(decimals)}`);
    chart.applyOptions({ localization: { locale: 'en-US', priceFormatter: axisFormat } });
    // A few self-recorded bars (quiet coin, no provider history yet) read as noise as candles;
    // show them as a clean price line until real history arrives.
    const autoSparse = displayCandles.length < 3; // candles by default; line only when there's almost nothing to draw
    const sparse = displayCandles.length > 0 && (chartStyle === 'line' || (chartStyle === 'auto' && autoSparse));
    sparseRef.current = sparse;
    const lineData = sparse ? displayCandles.map(([time, , , , close]) => ({ time, value: close })) : trail;
    if (displayCandles.length && !sparse) {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: dayMode ? '#08764e' : '#00e7a0',
        downColor: '#b42346',
        wickUpColor: dayMode ? '#08764e' : '#00e7a0',
        wickDownColor: '#b42346',
        borderVisible: false,
        priceFormat: { type: 'custom', formatter: axisFormat, minMove },
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
        color: dayMode ? '#08764e' : '#00e7a0', lineWidth: 2,
        priceFormat: { type: 'custom', formatter: axisFormat, minMove },
      });
      line.setData(lineData);
      seriesRef.current = { kind: 'line', series: line };
      lastBarRef.current = lineData.length ? { ...lineData[lineData.length - 1] } : null;
      line.priceScale().applyOptions({ scaleMargins: { top: .16, bottom: .16 } });
    }
    const ts = chart.timeScale();
    const n = sparse ? lineData.length : displayCandles.length || trail.length;
    if (rangeRef.current) ts.setVisibleLogicalRange(rangeRef.current);
    else if (n > 160) ts.setVisibleLogicalRange({ from: n - 150, to: n + 4 });
    else {
      // Young coins: few bars should fill the chart, not huddle in a corner.
      const w = container.current?.clientWidth || 600;
      ts.applyOptions({ maxBarSpacing: 48, barSpacing: Math.max(6, Math.min(48, (w - 90) / Math.max(n + 4, 8))) });
      ts.fitContent();
    }
    // Zoom/scroll out past the first bar → page in older real history.
    const onRange = range => {
      if (!range) return;
      rangeRef.current = range;
      const st = olderState.current;
      if (range.from > 8 || st.loading || st.exhausted || !displayCandles.length || !pair?.pairAddress) return;
      st.loading = true;
      const firstTime = displayCandles[0][0];
      fetchFeelessCandles(pair.chainId, pair.pairAddress, interval, firstTime, pair.baseToken?.address).then(res => {
        const older = (res?.candles || []).filter(c => c[0] < firstTime);
        if (!older.length) { st.exhausted = true; return; }
        // Older history must join the chart continuously; a jump means a different price source
        // (e.g. a stale pool) — never splice that in.
        const join = older[older.length - 1][4], first = displayCandles[0][4];
        if (!(join > 0 && first > 0 && join / first < 2.5 && first / join < 2.5)) { st.exhausted = true; return; }
        const r = rangeRef.current;
        if (r) rangeRef.current = { from: r.from + older.length, to: r.to + older.length };
        setOlderCandles(prev => { const seen = new Set(prev.map(c => c[0])); return [...older.filter(c => !seen.has(c[0])), ...prev].sort((a, b) => a[0] - b[0]); });
      }).catch(() => { st.exhausted = true; }).finally(() => { st.loading = false; });
    };
    ts.subscribeVisibleLogicalRangeChange(onRange);
    return () => { ts.unsubscribeVisibleLogicalRangeChange(onRange); seriesRef.current = null; markersRef.current = null; chart.remove(); };
  }, [displayCandles, trail, hasChart, dayMode, showVolume, chartStyle]); // eslint-disable-line react-hooks/exhaustive-deps

  // Meta overlays (Trenches calls, Fee's trades) snapped to the candle they happened in.
  useEffect(() => {
    const ref = seriesRef.current;
    if (!ref) return;
    const bucket = LIVE_INTERVAL_SECONDS[interval] || 3600;
    // Snap each pin onto a point the series really has (candle or line mode); a trade newer than the last bar
    // sits on the last bar, one older than the chart is dropped. Otherwise the chart silently hides it.
    let times = [];
    try { times = (ref.series.data?.() || []).map(d => d.time).filter(Number.isFinite); } catch { times = []; }
    // Pins that know their price (your fills) sit exactly at that price, scaled like the candles (MC charts too).
    const list = snapMarkers(markers, times, bucket).map(({ price, ...m }) => (Number(price) > 0 ? { ...m, price: Number(price) * ratio } : m));
    try {
      if (!markersRef.current) markersRef.current = createSeriesMarkers(ref.series, list);
      else markersRef.current.setMarkers(list);
    } catch {
      // Chart was torn down between render and effect (rapid prop changes); skip this pass.
    }
  }, [markers, interval, displayCandles, trail, dayMode, ratio]);

  // Fee cat live mode: is the Leader in this coin right now?
  useEffect(() => {
    if (!feeLive || !pair?.pairAddress) { setFeePos(null); return undefined; }
    let alive = true;
    const load = () => fetch('/api/cats/leader').then(r => r.json()).then(d => { if (alive) setFeePos((d.cat?.positions || []).find(p => p.pairAddress === pair.pairAddress) || null); }).catch(() => {});
    load(); const t = setInterval(load, 20000);
    return () => { alive = false; clearInterval(t); };
  }, [feeLive, pair?.pairAddress]);
  // Fee works on MC charts too: every level is scaled by the same supply ratio as the candles.
  const feeRead = useMemo(() => (feeLive && charting ? computeFeeRead(displayCandles, ratio === 1 ? pair : { ...pair, priceUsd: price * ratio }, feePos && ratio !== 1 ? { ...feePos, entryPriceUsd: Number(feePos.entryPriceUsd) * ratio } : feePos) : null), [feeLive, charting, displayCandles, pair, feePos, ratio, price]);

  // Draw Fee's levels as price lines; turning Fee off removes every one of them.
  useEffect(() => {
    const ref = seriesRef.current;
    const clear = () => { priceLinesRef.current.forEach(l => { try { ref?.series.removePriceLine(l); } catch { /* chart gone */ } }); priceLinesRef.current = []; };
    clear();
    if (!ref || !feeRead) return clear;
    const seen = displayCandles.slice(-300);
    const band = seen.length ? { lo: Math.min(...seen.map(c => c[3])), hi: Math.max(...seen.map(c => c[2])) } : null;
    const add = (price, color, title, style = 2) => {
      if (!Number.isFinite(price) || price <= 0) return;
      // A level 3x outside the visible range would squash every candle into a flat line.
      if (band && (price < band.lo / 1.5 || price > band.hi * 1.5)) return; // never let an overlay squash the candles
      try { priceLinesRef.current.push(ref.series.createPriceLine({ price, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true, title })); }
      catch { /* chart torn down between render and effect */ }
    };
    add(feeRead.resistance, '#fa708c', '🐱 resistance');
    add(feeRead.support, '#12c07a', '🐱 support');
    if (feeRead.vwap) add(feeRead.vwap, '#e9bd65', '🐱 fair value', 1);
    if (feeRead.entry) { add(feeRead.entry, '#5ec8ff', '🐱 Fee entry', 0); add(feeRead.entry * 0.9, '#ff5d73', '🐱 stop −10%', 3); add(feeRead.entry * 1.22, '#7df9d0', '🐱 target +22%', 3); }
    // Fibonacci retracements of the visible swing: where Fee expects bounces / rejections.
    const recent = displayCandles.slice(-120);
    if (recent.length > 10) {
      const hi = Math.max(...recent.map(c => c.high)); const lo = Math.min(...recent.map(c => c.low));
      if (hi > lo) [[0.382, '#b388ff'], [0.5, '#9e8cff'], [0.618, '#8a79ff']].forEach(([f, c]) => add(hi - (hi - lo) * f, c, `🐱 fib ${f}`, 3));
    }
    return clear;
  }, [feeRead, displayCandles, trail, dayMode, showVolume]);

  // The viewer's own levels (from their real swaps): the blended break-even (fees in, bold gold) plus one thin line
  // per trade at the exact pool price it filled at — B1, B2… for buys, S1… for sells.
  const entryLinesRef = useRef([]);
  const tradeKey = (userTrades || []).map(t => `${t.tx}:${t.fillPrice}`).join('|');
  useEffect(() => {
    const ref = seriesRef.current;
    const drop = () => { entryLinesRef.current.forEach(l => { try { ref?.series.removePriceLine(l); } catch { /* chart gone */ } }); entryLinesRef.current = []; };
    drop();
    if (!ref || !charting) return drop;
    const add = o => { try { entryLinesRef.current.push(ref.series.createPriceLine({ axisLabelVisible: true, ...o })); } catch { /* chart torn down */ } };
    tradeLevels(userTrades).forEach(t => add({ price: t.price * ratio, color: t.side === 'sell' ? '#ff8fa3aa' : '#16d67faa', lineWidth: 1, lineStyle: 2, title: t.title }));
    if (userEntry > 0) add({ price: userEntry * ratio, color: '#f5c542', lineWidth: 2, lineStyle: 0, title: '◆ break-even (fees in)' });
    return drop;
  }, [userEntry, tradeKey, charting, ratio, displayCandles]); // eslint-disable-line react-hooks/exhaustive-deps

  // Live ticks: every 3s pull the pair's current price straight from DexScreener and
  // update the forming candle in place (no redraw, zoom preserved).
  useEffect(() => {
    if (!charting || !pair?.pairAddress || !pair?.chainId) return undefined;
    const bucket = LIVE_INTERVAL_SECONDS[interval] || 3600;
    let alive = true;
    const apply = (usd, live) => {
      try {
        if (!alive || !(usd > 0)) return;
        setLivePrice({ usd, change: live?.change24h, at: Date.now(), source: live?.source });
        const value = usd * ratio;
        const ref = seriesRef.current;
        const last = lastBarRef.current;
        if (!ref || !last) return;
        const ref0 = last.close ?? last.value;
        if (ref0 > 0 && !(value > ref0 / 20 && value < ref0 * 20)) return; // bad read, not a real 1s move
        const t = Math.floor(Date.now() / 1000 / bucket) * bucket;
        if (ref.kind === 'candle') {
          // Missed buckets (hidden tab, stalled stream): draw them flat at the last close — never skip a candle.
          for (let gt = last.time + bucket; gt < t && t - gt < bucket * 500; gt += bucket) {
            ref.series.update({ time: gt, open: last.close, high: last.close, low: last.close, close: last.close });
          }
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
    const tick = async () => {
      if (document.hidden) return;
      try { const live = await fetchLivePrice(pair); apply(Number(live?.usd), live); } catch { /* next tick */ }
    };
    // Solana: server pushes every new price over one shared websocket per pool (fan-out, scales with
    // pools not users). Polling stays on as a slower safety net and takes over if the stream drops.
    let ws = null; let streaming = false;
    if (pair?.chainId === 'solana' && pair?.pairAddress && typeof WebSocket !== 'undefined') {
      try {
        ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/candles/stream/solana/${pair.pairAddress}${pair.baseToken?.address ? `?mint=${pair.baseToken.address}` : ''}`);
        ws.onopen = () => { streaming = true; };
        ws.onmessage = e => { try { const m = JSON.parse(e.data); apply(Number(m.p), { source: 'live stream' }); } catch { /* ignore */ } };
        ws.onclose = () => { streaming = false; };
      } catch { ws = null; }
    }
    tick();
    let n = 0;
    const timer = setInterval(() => { n += 1; if (!streaming || n % 4 === 0) tick(); }, 1200);   // ≤1.5s freshness; ~5s when streaming
    return () => { alive = false; clearInterval(timer); try { ws?.close(); } catch { /* ignore */ } };
  }, [charting, interval, pair, pair?.baseToken?.address, pair?.chainId, pair?.pairAddress, ratio]);
  const [livePx, setLivePx] = useState(null);
  useEffect(() => { if (!feePos) return undefined; const t = setInterval(() => { const b = lastBarRef.current; if (b) setLivePx(b.close ?? b.value); }, 1200); return () => clearInterval(t); }, [feePos]);
  // The last bar is a market cap when the chart shows MC: convert back to a price before comparing to entry.
  const fillPx = livePx ? livePx / (ratio || 1) : null;
  const feePnl = feePos?.entryPriceUsd > 0 && (fillPx || feePos.lastPriceUsd) ? ((fillPx || feePos.lastPriceUsd) / feePos.entryPriceUsd - 1) * 100 : feePos?.currentChange;
  // SOL/USD from the pair itself (priceUsd / priceNative on a SOL-quoted pool): turns the SOL stake into dollars.
  const solUsd = /^W?SOL$/i.test(pair?.quoteToken?.symbol || '') && Number(pair?.priceNative) > 0 ? Number(pair.priceUsd) / Number(pair.priceNative) : null;
  const feePnlUsd = solUsd && feePnl != null ? Number(feePos?.costSol || 0) * solUsd * feePnl / 100 : null;
  const shortPct = v => (Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : ''}${v.toFixed(Math.abs(v) >= 100 ? 0 : 1)}%`);
  const usd = v => `${v < 0 ? '−' : '+'}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(2)}`;
  return <div className="chart-area" data-testid="price-chart">
    {feeLive && feePos && feePnl != null && <div className={`fee-pnl ${feePnl >= 0 ? 'up' : 'down'}`} data-testid="fee-pnl"><span>🐱 Fee is in</span><b>{shortPct(feePnl)}</b>{feePnlUsd != null && <b className="fee-pnl-usd">{usd(feePnlUsd)}</b>}<small>{Number(feePos.costSol).toFixed(2)} SOL{solUsd ? ` ($${(Number(feePos.costSol) * solUsd).toFixed(2)})` : ''}{feePos.peakChange ? ` · peak +${Number(feePos.peakChange).toFixed(1)}%` : ''}</small></div>}
    {charting && !candlesLoaded && <div className="chart-message" data-testid="chart-loading"><span className="loader" />Loading on-chain candles…</div>}
    {charting && !loading && usingFallbackTrail && trail.length < 2 && <div className="chart-message chart-building" role="status" data-testid="chart-building">
      <span className="signal-lines"><i /><i /><i /><i /></span>
      <strong>Building a live price trail for this pool.</strong>
      <span>Full candle history is temporarily unavailable from the provider. FEELESS is recording every price it observes here — check back shortly, or view the external chart now.</span>
      <a data-testid="chart-fallback-link" href={dexUrl(pair)} target="_blank" rel="noreferrer">Open chart on DexScreener ↗</a>
    </div>}
    {charting && usingFeelessCandles && candleProvider === 'FEELESS' && <div className="chart-stale-note chart-stale-pill" role="status" title="Full provider candle history is rate-limited right now; FEELESS is showing real prices it recorded itself and will fill in history automatically.">● {allFeeless.length} FEELESS-recorded bars · full history loading</div>}
    {charting && usingFallbackTrail && trail.length >= 2 && <div className="chart-stale-note" role="status">Live price trail recorded by this browser — full {data?.provider || 'provider'} candle history is temporarily unavailable.</div>}
    {metricChart && hasChart && <div className="chart-stale-note metric-derived-note" role="status" title={`${metricLabel} chart = real price candles × token supply`} data-testid={`chart-${metric}-derived`}>{metricLabel} chart = real price candles × token supply (supply is fixed, so the shape is exact). Now {formatUSD(metricValue)}.</div>}
    {!priceMetric && metricAvailable && !loading && !hasChart && !usingFallbackTrail && <div className="metric-snapshot" data-testid={`chart-${metric}-snapshot`}><span className="metric-snapshot-label">{metricLabel} snapshot</span><strong>{formatUSD(metricValue)}</strong><small>Provider supplied the current {metricLabel.toLowerCase()} only. Historical {metricLabel.toLowerCase()} candles are unavailable.</small></div>}
    {!priceMetric && !metricAvailable && <div className="chart-message metric-unavailable" role="status" data-testid={`chart-${metric}-unavailable`}><strong>{metricLabel} unavailable</strong><span>The provider did not supply a {metricLabel.toLowerCase()} value for this pair. No value is estimated.</span></div>}
    {charting && hasChart && <div className="candle-canvas" ref={container} data-testid="candlestick-canvas" />}
    {charting && hasChart && <div className="chart-foot-chips">{createdAt && <span className="chart-age" title={new Date(createdAt).toLocaleString()}>🕒 Created {ageLabel(createdAt)} ago</span>}{feeLiveProp === undefined && <button type="button" className={`chart-fee-toggle ${feeOwn ? 'on' : ''}`} onClick={() => setFeeOwn(v => !v)}>🐱 Fee {feeOwn ? 'on' : 'off'}</button>}</div>}
    {charting && hasChart && displayCandles.length > 0 && <button type="button" className="chart-style-toggle" data-testid="chart-style-toggle" onClick={toggleStyle} title="Switch line / candles">{chartStyle === 'line' || (chartStyle === 'auto' && displayCandles.length < 3) ? '▮ Candles' : '〰 Line'}</button>}
    {feeRead && hasChart && <div className={`fee-live-read stance-${feeRead.stance.replace(/\s/g, '-')} ${feeOpen ? '' : 'min'}`} data-testid="fee-live-read">
      <button type="button" className="flr-head" onClick={() => setFeeOpen(o => !o)}><span className="flr-cat">🐱</span><b>Fee · live read</b><em>{feeRead.stance}</em><i className="flr-dot" /></button>
      {feeOpen && <><ul>{feeRead.lines.map((l, i) => <li key={i}>{l}</li>)}</ul>
        <div className="flr-liq"><span>💧 {formatUSD(feeRead.liq)}</span>{feeRead.liqRatio != null && <span className={feeRead.liqRatio < 0.05 ? 'thin' : ''}>{(feeRead.liqRatio * 100).toFixed(1)}% of MC</span>}{feeRead.flow1 != null && <span className="flr-flow"><i style={{ width: `${feeRead.flow1 * 100}%` }} /></span>}</div>
        <small>Rules-based read from the candles on screen · not financial advice</small></>}
    </div>}
    <div className="chart-source"><span>{priceMetric ? (candleRows.length ? `${data?.provider || 'Jupiter'} · OHLCV` : usingFeelessCandles ? `${candleProvider || 'FEELESS'} · OHLCV` : 'FEELESS local trail · price only') : metricChart && hasChart ? `${metricLabel} · derived from ${candleProvider || 'FEELESS'} price candles` : `Provider pair snapshot · ${metricLabel}`}</span>{charting ? (livePrice && Date.now() - livePrice.at < 10000 ? <span className="data-status live-tick"><i />LIVE · {livePrice.source || 'DEX'}</span> : <DataStatus data={data} id="chart-data-status" />) : <span className="data-status"><i />{metricAvailable ? 'LIVE · snapshot' : 'UNAVAILABLE'}</span>}</div>
  </div>;
};

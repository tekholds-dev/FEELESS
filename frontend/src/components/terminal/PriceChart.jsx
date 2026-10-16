import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChartBg } from './ChartBg';
import { bumpChart } from '../../lib/chartFrame';
import { useChartBg } from '../../lib/chartBg';
import { ChartToolsMenu, useToolDraw } from './ChartTools';
import { ChartPulse } from './ChartPulse';
import { ChartPnl } from './ChartPnl';
import { ChartLive } from './ChartLive';
import { CandleFx } from './CandleFx';
import { ChartLevels } from './ChartLevels';
import { feeLevels, ownLevels, toolLevels, germLevels } from '../../lib/chartLevels';
import { useGerm } from '../../lib/germ';
import { mergeLiveBar, liveBar } from '../../lib/tween';
import { scaleKeep } from '../../lib/chartLevels';
import { tickGuard } from '../../lib/tickGuard';
import { mcapOf } from '../../lib/mcap';
import { toolRead, useChartTools, germ as germOf } from '../../lib/chartTools';
import { ChartGrab } from './ChartGrab';
import { withGrab } from '../../lib/chartGrab';
import { createChart, createSeriesMarkers, CandlestickSeries, HistogramSeries, LineSeries, ColorType } from 'lightweight-charts';
import { useMarket } from '../../hooks/useMarket';
import { dexUrl, formatUSD } from '../../lib/dexscreener';
import { DataStatus } from './MarketPrimitives';
import { recordPricePoint, getPriceTrail } from '../../lib/priceHistory';
import { recordCandleTick, fetchFeelessCandles, getCachedCandles, cacheCandles, prefetchAllIntervals } from '../../lib/candles';
import { scrubCandles } from '../../lib/chartMath';
import { fetchLivePrice } from '../../lib/livePrice';
import { computeFeeRead } from './FeeLiveRead';
import { snapMarkers } from '../../lib/chartMarkers';

const LIVE_INTERVAL_SECONDS = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 };


const ageLabel = t => { const s = (Date.now() - t) / 1000; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : s < 86400 * 60 ? `${Math.round(s / 86400)}d` : `${Math.round(s / 86400 / 30)}mo`; };

export const PriceChart = ({ pair, interval, showVolume, metric = 'price', markers = [], feeLive: feeLiveProp, userEntry = null, userTrades = null, fuse: fuse0 = null, pnl, plain = false }) => {
  // ✋ a level dragged on this chart and CONFIRMED by the card sits where it was dropped until the card's next read
  const [grabbed, setGrabbed] = useState(null);
  useEffect(() => { setGrabbed(null); }, [fuse0?.pairAddress, fuse0?.slPct, fuse0?.lockPct, fuse0?.trailPct, fuse0?.tpPct]);
  useEffect(() => { const on = e => { const d = e.detail || {}; if (d.pairAddress === fuse0?.pairAddress || d.kind === 'lock' || d.kind === 'trail') setGrabbed(o => ({ ...(o || {}), [d.kind]: d.pct })); };
    window.addEventListener('feeless:fuse-level-done', on); return () => window.removeEventListener('feeless:fuse-level-done', on); }, [fuse0?.pairAddress]);
  const fuse = useMemo(() => withGrab(fuse0, grabbed), [fuse0, grabbed]);
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
    fetch(`/api/market/tokens/${pair.chainId}/${mint}`).then(r => r.json())
      .then(list => { const ts = (list || []).map(x => x.pairCreatedAt).filter(Boolean); if (alive && ts.length) setCreatedAt(Math.min(...ts)); }).catch(() => {});
    return () => { alive = false; };
  }, [pair?.chainId, pair?.baseToken?.address, pair?.pairCreatedAt]);
  const container = useRef(null);
  const seriesRef = useRef(null);
  const chartRef = useRef(null);
  const lastBarRef = useRef(null);
  const shownRef = useRef(null);   // the close the forming candle is DRAWN with right now (= the last real tick) — the live P&L tag rides it
  const markersRef = useRef(null);
  const [livePrice, setLivePrice] = useState(null);
  const liveBarRef = useRef(null);   // the forming candle as the LIVE feed built it (kept across history reloads)
  const [feePos, setFeePos] = useState(null);
  const [feeOpen, setFeeOpen] = useState(false);
  const [feelessCandles, setFeelessCandles] = useState([]);
  // Chart style: 'auto' (line when data is sparse, candles otherwise), or forced 'line' / 'candle'.
  const sparseRef = useRef(false);
  const [chartStyle, setChartStyle] = useState(() => { try { return localStorage.getItem('feeless:chart-style') || 'auto'; } catch { return 'auto'; } });
  const keepRef = useRef([]);   // 📐 entry + stop the scale must keep on screen (set from the levels below, read by every series it builds)
  const keepScale = base => { const r = base(); if (!r || !r.priceRange) return r; const keep = scaleKeep(keepRef.current, lastBarRef.current?.close ?? lastBarRef.current?.value);
    return keep.length ? { ...r, priceRange: { minValue: Math.min(r.priceRange.minValue, ...keep), maxValue: Math.max(r.priceRange.maxValue, ...keep) } } : r; };
  const toggleStyle = () => setChartStyle(cur => { const next = sparseRef.current ? 'candle' : 'line'; try { localStorage.setItem('feeless:chart-style', next); } catch { /* private mode */ } return next; });
  const [olderCandles, setOlderCandles] = useState([]);
  const olderState = useRef({ loading: false, exhausted: false });
  const rangeRef = useRef(null);
  const [candleProvider, setCandleProvider] = useState('');
  const [candlesLoaded, setCandlesLoaded] = useState(false);
  const priceMetric = metric === 'price';
  const bgKind = useChartBg();
  const [fxLite, setFxLite] = useState(() => typeof document !== 'undefined' && (document.body.classList.contains('fx-lite') || !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches));
  useEffect(() => { if (typeof document === 'undefined') return undefined; const sync = () => setFxLite(document.body.classList.contains('fx-lite') || !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
    const o = new MutationObserver(sync); o.observe(document.body, { attributes: true, attributeFilter: ['class'] }); return () => o.disconnect(); }, []);
  const bgOn = bgKind !== 'default' && !fxLite && !plain;   /* `plain` = a working chart (the Agents cockpit): candles + levels only, no scene */   /* lite mode / reduced motion = the plain chart, whatever was picked */
  const [dayMode, setDayMode] = useState(() => typeof document !== 'undefined' && document.body.classList.contains('theme-day'));
  // Candles come only from the FEELESS candle service (Jupiter/Alchemy/Helius behind a shared cache + our own ticks).
  const { data, loading } = useMarket(null);
  const metricLabel = metric === 'marketCap' ? 'Market cap' : 'FDV';
  const metricValue = metric === 'marketCap' ? mcapOf(pair?.priceUsd, pair?.marketCap, pair?.baseToken?.address) : pair?.fdv;   // 📊 a launchpad coin with no cap yet: price × its fixed 1B supply
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
      .then(res => { cacheCandles(pair.chainId, pair.pairAddress, interval, res);   /* partial (own ticks) too: a remount paints them at once, the next load replaces them */ if (alive && Array.isArray(res?.candles)) { setFeelessCandles(res.candles); setCandleProvider(res.provider || 'FEELESS'); if (res.partial) setTimeout(() => { if (alive) load(); }, 2500); } })
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
        background: { type: ColorType.Solid, color: bgOn ? 'transparent' : dayMode ? '#edf4ef' : '#080e0d' },   /* 🎨 a picked scene shows through */
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
    const axisFormat = n => (!(n >= 0) ? '' : Math.abs(n) >= 1000 ? formatUSD(n) : `$${Number(n).toFixed(decimals)}`);   // a price or market cap is never negative: the volume margin below the lowest candle prints no fake "$-2.00K"
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
        priceFormat: { type: 'custom', formatter: axisFormat, minMove }, autoscaleInfoProvider: keepScale,
      });
      const bars = displayCandles.map(([time, open, high, low, close]) => ({ time, open, high, low, close }));
      series.setData(mergeLiveBar(bars, liveBarRef.current, interval, pair?.pairAddress));   // 🕯 a history reload never overwrites the LIVE forming candle
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
        priceFormat: { type: 'custom', formatter: axisFormat, minMove }, autoscaleInfoProvider: keepScale,
      });
      line.setData(lineData);
      seriesRef.current = { kind: 'line', series: line };
      lastBarRef.current = lineData.length ? { ...lineData[lineData.length - 1] } : null;
      line.priceScale().applyOptions({ scaleMargins: { top: .16, bottom: .16 } });
    }
    chartRef.current = chart;
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
      rangeRef.current = range; bumpChart(container.current);   // ⚡ overlays redraw on a scroll / zoom
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
    const box_ = container.current;
    const ro = typeof ResizeObserver === 'function' && box_ ? new ResizeObserver(() => bumpChart(box_)) : null;   // ⚡ … and on a resize
    ro?.observe(box_);
    bumpChart(box_);   // new data drawn
    return () => { ro?.disconnect(); ts.unsubscribeVisibleLogicalRangeChange(onRange); seriesRef.current = null; chartRef.current = null; markersRef.current = null; chart.remove(); };
  }, [displayCandles, trail, hasChart, dayMode, showVolume, chartStyle, bgOn]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // 📏 every level on the chart is a LIVE row (ChartLevels): Fee's read, your own fills + entry, a Fuse card's / the agents' levels and
  // the chart tools — one list, drawn by one overlay. No static price lines.
  const feeLv = useMemo(() => {
    if (!feeRead) return [];
    const seen = displayCandles.slice(-300); const recent = displayCandles.slice(-120);
    const band = seen.length ? { lo: Math.min(...seen.map(c => c.low)), hi: Math.max(...seen.map(c => c.high)) } : null;
    return feeLevels(feeRead, band, recent.length > 10 ? { hi: Math.max(...recent.map(c => c.high)), lo: Math.min(...recent.map(c => c.low)) } : null);
  }, [feeRead, displayCandles]);
  const tradeKey = (userTrades || []).map(t => `${t.tx}:${t.fillPrice}`).join('|');
  const ownLv = useMemo(() => (charting ? ownLevels({ userTrades, userEntry, fuse, ratio }) : []),
    [userEntry, tradeKey, charting, ratio, fuse?.entry, fuse?.stop, fuse?.lock, fuse?.trail, (fuse?.lines || []).map(l => `${l?.px}:${l?.title}`).join('|')]); // eslint-disable-line react-hooks/exhaustive-deps

  // 🧰 chart tools (FVG · magnets · gun line · germ · meta edge): read from the candles on screen, drawn on every chart
  const toolsOn = useChartTools();
  const toolsRead = useMemo(() => (charting && toolsOn.length ? toolRead(displayCandles, toolsOn) : null), [charting, toolsOn, displayCandles]);
  useToolDraw(seriesRef, chartRef, container, toolsRead, [dayMode, showVolume, chartStyle, bgOn, hasChart]);
  const agentGerm = useGerm(plain ? null : pair?.baseToken?.address);
  const germLv = useMemo(() => (charting && !plain ? germLevels({ candles: displayCandles, interval, agent: agentGerm, ratio, germFn: toolsRead?.germ ? null : germOf }) : []), [charting, plain, displayCandles, interval, agentGerm, ratio, toolsRead]);   // 🦠 the germ on every chart, every timeframe
  const levels = useMemo(() => [...ownLv, ...feeLv, ...toolLevels(toolsRead), ...germLv], [ownLv, feeLv, toolsRead, germLv]);
  // 📐 the scale always keeps your entry + stop on screen (a seat's own entry too), never a level far away
  const seatEntry = pnl && typeof pnl === 'object' ? (Number(pnl.pos?.fillPrice) || Number(pnl.pos?.avgEntry) || 0) * (ratio || 1) : 0;
  const keepKey = useMemo(() => [...ownLv.map(r => ({ id: r.id, title: r.title, px: r.px })), ...(seatEntry > 0 ? [{ id: 'entry', px: seatEntry }] : [])], [ownLv, seatEntry]);
  keepRef.current = keepKey;

  // Live ticks: every 3s pull the pair's current price straight from DexScreener and
  // update the forming candle in place (no redraw, zoom preserved).
  // The stream is keyed by the POOL, never by the pair object or the cap ratio: a parent that rebuilds `pair` each render (or passes a live
  // cap) used to tear the websocket down and reconnect on every price tick (10 "connection open" a minute for one coin).
  const pairLive = useRef(pair); pairLive.current = pair;
  const ratioLive = useRef(ratio); ratioLive.current = ratio;
  useEffect(() => {
    const pair = pairLive.current;   // eslint-disable-line no-shadow
    if (!charting || !pair?.pairAddress || !pair?.chainId) return undefined;
    const bucket = LIVE_INTERVAL_SECONDS[interval] || 3600;
    let alive = true;
    const guard = tickGuard();   // 🕯 one bad print never draws a candle (held until the next tick confirms or drops it)
    // 🕯 REAL TICKS ONLY (owner, 2026-10-13: "current candle morphing before it becomes its true shape — can't have that"): the forming
    // candle is redrawn ONLY when a real price tick lands (the stream re-reads the price right after each on-chain swap), at exactly that
    // price — no eased in-between frames. It used to glide ~350ms through prices nobody traded at.
    const apply = (usd, live) => {
      try {
        if (!alive || !(usd > 0)) return;
        const value = usd * ratioLive.current;
        const ref = seriesRef.current;
        const last = lastBarRef.current;
        const ref0 = last ? last.close ?? last.value : 0;
        if (ref0 > 0 && !(value > ref0 / 20 && value < ref0 * 20)) return; // bad read, not a real 1s move
        if (guard(ref0, value) == null) return;   // the header price never shows a print the candle would not draw either
        setLivePrice({ usd, change: live?.change24h, at: Date.now(), source: live?.source });
        if (!ref || !last) return;
        const t = Math.floor(Date.now() / 1000 / bucket) * bucket;
        if (ref.kind === 'candle') {
          // 🕯 true data only (`liveBar`): a 1–2 bucket gap continues from the last close; a stale history (a coin indexed late) opens the new
          // candle at the first REAL tick and leaves the gap empty — no fake candle from an old price, no invented flat minutes
          const lb = liveBar(last, value, t, bucket);
          lb.fill.forEach(f => { try { ref.series.update(f); } catch { /* chart gone */ } });
          const bar = lb.bar;
          ref.series.update(bar); shownRef.current = value;
          lastBarRef.current = bar; liveBarRef.current = { ...bar, iv: interval, pool: pairLive.current?.pairAddress };
          bumpChart(container.current);   // ⚡ a real tick: the overlays follow it on the next frame
        } else {
          const point = { time: Math.max(t, last.time), value };
          ref.series.update(point);
          lastBarRef.current = point; shownRef.current = value; bumpChart(container.current);
        }
      } catch {
        // Keep the last real candle; never invent a tick.
      }
    };
    const tick = async () => {
      if (document.hidden) return;
      try { const live = await fetchLivePrice(pairLive.current); apply(Number(live?.usd), live); } catch { /* next tick */ }
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
    const timer = setInterval(() => { if (!streaming) tick(); }, 1200);   // backup poll ONLY while the stream is down: one price feed per candle, never two
    return () => { alive = false; clearInterval(timer); try { ws?.close(); } catch { /* ignore */ } };
  }, [charting, interval, pair?.baseToken?.address, pair?.chainId, pair?.pairAddress]);
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
  return <div className={`chart-area ${bgOn ? 'has-bg' : ''}`} data-testid="price-chart">
    {bgOn && <ChartBg kind={bgKind} />}
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
    {charting && hasChart && displayCandles.length > 0 && <ChartToolsMenu read={toolsRead} />}
    {charting && hasChart && pair?.chainId === 'solana' && pair?.baseToken?.address && <ChartPulse mint={pair.baseToken.address} beat={livePrice?.usd} />}
    {charting && hasChart && !plain && !fxLite && <CandleFx seriesRef={seriesRef} chartRef={chartRef} lastBarRef={lastBarRef} shownRef={shownRef} container={container} />}
    {charting && hasChart && levels.length > 0 && <ChartLevels levels={levels} seriesRef={seriesRef} chartRef={chartRef} lastBarRef={lastBarRef} shownRef={shownRef} container={container} fmt={formatUSD} />}
    {charting && hasChart && <ChartPnl pair={pair} price={livePrice?.usd} pnl={pnl} live={{ seriesRef, chartRef, lastBarRef, shownRef, container, ratio, fmt: v => formatUSD(v * ratio) }} />}
    {charting && hasChart && !(pnl && typeof pnl === 'object') && fuse?.entry > 0 && <ChartLive seriesRef={seriesRef} chartRef={chartRef} lastBarRef={lastBarRef} shownRef={shownRef} container={container} ratio={ratio}
      entry={fuse.entry} at={fuse.at || null} label={fuse.card ? '⚛ CARD' : 'SEAT'} entryWord={formatUSD(fuse.entry * ratio)} />}
    {charting && hasChart && fuse?.tpl && <ChartGrab seriesRef={seriesRef} container={container} fuse={fuse} ratio={ratio} />}
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

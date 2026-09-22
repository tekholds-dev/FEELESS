import React, { useEffect, useMemo, useRef } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, ColorType } from 'lightweight-charts';
import { useMarket } from '../../hooks/useMarket';
import { dexUrl, formatUSD } from '../../lib/dexscreener';
import { DataStatus, MarketError } from './MarketPrimitives';

export const PriceChart = ({ pair, interval, showVolume }) => {
  const container = useRef(null);
  const { data, loading, error, reload } = useMarket(pair ? `/candles/${pair.chainId}/${pair.pairAddress}?interval=${interval}` : null);
  const providerError = error || data?.error;
  const candleRows = useMemo(() => Array.isArray(data?.candles)
    ? [...new Map(data.candles
      .filter(row => Array.isArray(row) && row.length >= 6 && row.every(Number.isFinite))
      .map(row => [row[0], row])).values()].sort((a, b) => a[0] - b[0])
    : [], [data?.candles]);
  useEffect(() => {
    if (!container.current || !candleRows.length) return;
    const chart = createChart(container.current, {
      autoSize: true, layout: { background: { type: ColorType.Solid, color: '#080e0d' }, textColor: '#8c9b94', fontFamily: 'JetBrains Mono', fontSize: 10, attributionLogo: true },
      grid: { vertLines: { color: '#ffffff04' }, horzLines: { color: '#ffffff06' } },
      rightPriceScale: { borderColor: '#203129' }, timeScale: { borderColor: '#203129', timeVisible: true, secondsVisible: false },
      localization: { locale: 'en-US', priceFormatter: n => formatUSD(n) }, crosshair: { mode: 0 },
    });
    const series = chart.addSeries(CandlestickSeries, { upColor: '#00e7a0', downColor: '#f56880', wickUpColor: '#00e7a0', wickDownColor: '#f56880', borderVisible: false, priceFormat: { type: 'custom', formatter: n => formatUSD(n) } });
    series.setData(candleRows.map(([time, open, high, low, close]) => ({ time, open, high, low, close })));
    series.priceScale().applyOptions({ scaleMargins: { top: .12, bottom: showVolume ? .24 : .12 } });
    if (showVolume) {
      const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '', lastValueVisible: false, priceLineVisible: false });
      volume.priceScale().applyOptions({ scaleMargins: { top: .84, bottom: 0 } });
      volume.setData(candleRows.map(([time, open, , , close, value]) => ({ time, value, color: close >= open ? '#00e7a042' : '#f5688050' })));
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candleRows, showVolume]);
  return <div className="chart-area" data-testid="price-chart">
    {loading && <div className="chart-message" data-testid="chart-loading"><span className="loader" />Loading on-chain candles…</div>}
    {providerError && <div className="chart-message" data-testid="chart-provider-failure">
      <MarketError
        error={`Unable to load candle history from GeckoTerminal. ${providerError}`}
        description="This is a provider failure, not confirmation that the pool has no history. Retry the candle request or use the external chart."
        reload={reload}
        focusable
        retryLabel={`Retry ${interval} candle history`}
        id="chart-error"
      />
      <a data-testid="chart-fallback-link" href={dexUrl(pair)} target="_blank" rel="noreferrer">Open chart on DexScreener ↗</a>
    </div>}
    {!loading && !providerError && !candleRows.length && <div className="chart-message" role="status" aria-live="polite" tabIndex="0" data-testid="chart-empty">
      <strong>No candle history for this pool yet.</strong>
      <span>GeckoTerminal returned an empty history for the selected {interval} interval. This is different from a provider outage; try another interval or check the external chart.</span>
      <a data-testid="chart-empty-dex-link" href={dexUrl(pair)} target="_blank" rel="noreferrer">View on DexScreener ↗</a>
    </div>}
    <div className="candle-canvas" ref={container} data-testid="candlestick-canvas" />
    <div className="chart-source"><span>GeckoTerminal · OHLCV</span><DataStatus data={data} id="chart-data-status" /></div>
  </div>;
};
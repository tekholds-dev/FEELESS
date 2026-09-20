import React, { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, ColorType } from 'lightweight-charts';
import { useMarket } from '../../hooks/useMarket';
import { dexUrl, formatUSD } from '../../lib/dexscreener';
import { DataStatus, MarketError } from './MarketPrimitives';

export const PriceChart = ({ pair, interval, showVolume }) => {
  const container = useRef(null);
  const { data, loading, error, reload } = useMarket(pair ? `/candles/${pair.chainId}/${pair.pairAddress}?interval=${interval}` : null);
  useEffect(() => {
    if (!container.current || !data?.candles?.length) return;
    const chart = createChart(container.current, {
      autoSize: true, layout: { background: { type: ColorType.Solid, color: '#080e0d' }, textColor: '#8c9b94', fontFamily: 'JetBrains Mono', fontSize: 10, attributionLogo: true },
      grid: { vertLines: { color: '#ffffff04' }, horzLines: { color: '#ffffff06' } },
      rightPriceScale: { borderColor: '#203129' }, timeScale: { borderColor: '#203129', timeVisible: true, secondsVisible: false },
      localization: { locale: 'en-US', priceFormatter: n => formatUSD(n) }, crosshair: { mode: 0 },
    });
    const series = chart.addSeries(CandlestickSeries, { upColor: '#00e7a0', downColor: '#f56880', wickUpColor: '#00e7a0', wickDownColor: '#f56880', borderVisible: false, priceFormat: { type: 'custom', formatter: n => formatUSD(n) } });
    const rows = [...new Map(data.candles.filter(r => r.length >= 6 && r.every(Number.isFinite))
      .map(r => [r[0], r])).values()].sort((a, b) => a[0] - b[0]);
    series.setData(rows.map(([time, open, high, low, close]) => ({ time, open, high, low, close })));
    series.priceScale().applyOptions({ scaleMargins: { top: .12, bottom: showVolume ? .24 : .12 } });
    if (showVolume) {
      const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '', lastValueVisible: false, priceLineVisible: false });
      volume.priceScale().applyOptions({ scaleMargins: { top: .84, bottom: 0 } });
      volume.setData(rows.map(([time, open, , , close, value]) => ({ time, value, color: close >= open ? '#00e7a042' : '#f5688050' })));
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [data, showVolume]);
  return <div className="chart-area" data-testid="price-chart">
    {loading && <div className="chart-message" data-testid="chart-loading"><span className="loader" />Loading on-chain candles…</div>}
    {error && <div className="chart-message"><MarketError error={error} reload={reload} id="chart-error" /><a data-testid="chart-fallback-link" href={dexUrl(pair)} target="_blank" rel="noreferrer">Open chart on DexScreener ↗</a></div>}
    {!loading && !error && !data?.candles?.length && <div className="chart-message" data-testid="chart-empty">No candle history for this pool yet.<a data-testid="chart-empty-dex-link" href={dexUrl(pair)} target="_blank" rel="noreferrer">View on DexScreener ↗</a></div>}
    <div className="candle-canvas" ref={container} data-testid="candlestick-canvas" />
    <div className="chart-source"><span>GeckoTerminal · OHLCV</span><DataStatus data={data} id="chart-data-status" /></div>
  </div>;
};
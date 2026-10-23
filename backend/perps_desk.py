"""📉 THE PERPS DESK (owner, 2026-10-22: "find 2-3 perps sites we can wire in, one with big degen leverage"). Pure + tested.

Read-only market data from Hyperliquid's public info API (POST /info {"type": "metaAndAssetCtxs"} → [meta.universe, ctxs] aligned by index):
mark price, 24h move, hourly funding (as APR — positive = longs pay shorts), open interest in $, 24h volume, max leverage. The desk then routes
to a venue US traders can legally use (owner, 2026-10-23: "no Drift or Hyperliquid if there's no way in the USA — find perps we can use"):
KRAKEN PRO (CFTC-regulated perps via Bitnomial since 2026-06-15: BTC ETH SOL XRP ADA LINK DOGE LTC AVAX) and COINBASE (perpetual-style
futures via its CFTC-registered FCM since 2025-07: BTC ETH at launch). Hyperliquid's numbers are a global price / funding REFERENCE only —
nothing routes there. Only coins a US venue lists are shown. `liq_move` = how far price can move against a position before it is liquidated.
Re-check each venue's market list when you touch this (sources: Kraken / Coinbase launch notes, 2025–26).
"""
INFO = 'https://api.hyperliquid.xyz/info'
TOP = 12
US_VENUES = {'kraken': ('BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'LINK', 'DOGE', 'LTC', 'AVAX'), 'coinbase': ('BTC', 'ETH')}


def venues_for(coin):
    """The US-legal venues that list this coin's perps (empty = no US route → the row is not shown)."""
    return [v for v, coins in US_VENUES.items() if coin in coins]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def rows(payload, top=TOP):
    """[meta, ctxs] → the busiest markets, biggest 24h volume first."""
    try:
        uni, ctxs = payload[0]['universe'], payload[1]
    except (TypeError, KeyError, IndexError):
        return []
    out = []
    for u, c in zip(uni, ctxs):
        if u.get('isDelisted'):
            continue
        mark, prev, fund, oi, vol = _f(c.get('markPx')), _f(c.get('prevDayPx')), _f(c.get('funding')), _f(c.get('openInterest')), _f(c.get('dayNtlVlm'))
        if not mark:
            continue
        coin = u.get('name')
        if not venues_for(coin):
            continue
        out.append({'coin': coin, 'mark': mark, 'ch24': round((mark / prev - 1) * 100, 2) if prev else None,
                    'fundApr': round(fund * 24 * 365 * 100, 1) if fund is not None else None, 'oiUsd': round((oi or 0) * mark), 'vol24': round(vol or 0),
                    'maxLev': int(u.get('maxLeverage') or 0), 'venues': venues_for(coin)})
    return sorted(out, key=lambda r: -r['vol24'])[:top]


def liq_move(lev):
    """% the price can move against you before a liquidation, ignoring fees / maintenance margin (≈ 100 / leverage)."""
    return round(100 / max(1.0, float(lev or 1)), 2)

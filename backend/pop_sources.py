"""🛰 PoP SOURCES: each mind reads its own perps sources, never its partner's and never the ones it read last time. Every number is measured against the chart (Coinbase). Free public reads, no key, nothing is traded.
Each parser takes the JSON a source returned → {'px', 'funding' (% per 8 h), 'oi'} or raises. A source that fails is recorded as a gap, never guessed."""
import asyncio
import time

KRAKEN = {'SOL': 'SOLUSD', 'ETH': 'ETHUSD', 'BTC': 'XBTUSD'}
PAPRIKA = {'SOL': 'sol-solana', 'ETH': 'eth-ethereum', 'BTC': 'btc-bitcoin'}
DERIBIT = {'SOL': 'SOL_USDC-PERPETUAL', 'ETH': 'ETH-PERPETUAL', 'BTC': 'BTC-PERPETUAL'}
OFF_BPS = 25.0        # further than this from the chart: flagged, and not filed as a verified fact
SHOW = 2              # sources a mind reads for a proof


def _f(v):
    return float(v) if v not in (None, '') else None


def _kraken(j, m):
    return {'px': _f(list(j['result'].values())[0]['c'][0])}


def _hyper(j, m):
    i = [a['name'] for a in j[0]['universe']].index(m); x = j[1][i]
    return {'px': _f(x['markPx']), 'funding': _f(x['funding']) * 800, 'oi': _f(x['openInterest'])}   # hourly → % per 8 h


def _dydx(j, m):
    x = j['markets'][f'{m}-USD']
    return {'px': _f(x['oraclePrice']), 'funding': _f(x['nextFundingRate']) * 800, 'oi': _f(x['openInterest'])}   # hourly → % per 8 h


def _deribit(j, m):
    x = j['result']
    return {'px': _f(x['last_price']), 'funding': _f(x.get('funding_8h') or 0) * 100, 'oi': _f(x.get('open_interest'))}


def _okx(j, m):
    return {'px': _f(j['data'][0]['last'])}


SOURCES = {
    'kraken.com': ('spot', lambda m: f'https://api.kraken.com/0/public/Ticker?pair={KRAKEN[m]}', _kraken),
    'bitstamp.net': ('spot', lambda m: f'https://www.bitstamp.net/api/v2/ticker/{m.lower()}usd/', lambda j, m: {'px': _f(j['last'])}),
    'gemini.com': ('spot', lambda m: f'https://api.gemini.com/v1/pubticker/{m.lower()}usd', lambda j, m: {'px': _f(j['last'])}),
    'coinpaprika.com': ('index', lambda m: f'https://api.coinpaprika.com/v1/tickers/{PAPRIKA[m]}?quotes=USD', lambda j, m: {'px': _f(j['quotes']['USD']['price'])}),
    'okx.com': ('perp', lambda m: f'https://www.okx.com/api/v5/market/ticker?instId={m}-USD-SWAP', _okx),
    'hyperliquid.xyz': ('perp', None, _hyper),
    'deribit.com': ('perp', lambda m: f'https://www.deribit.com/api/v2/public/ticker?instrument_name={DERIBIT[m]}', _deribit),
    'dydx.trade': ('perp', lambda m: f'https://indexer.dydx.trade/v4/perpetualMarkets?ticker={m}-USD', _dydx),
}


def history(folders, mind):
    """A mind's source record from its filed proofs, oldest first: {site: {'n', 'fails', 'dev'}} and the sites of its last proof."""
    book, last = {}, []
    for f in folders or []:
        rows = (f.get('sources') or {}).get(str(mind)) or []
        if rows:
            last = [r.get('site') for r in rows]
        for r in rows:
            b = book.setdefault(r.get('site'), {'n': 0, 'fails': 0, 'dev': 0.0, 'read': 0})
            b['n'] += 1
            if r.get('ok') and r.get('devBps') is not None:
                b['read'] += 1; b['dev'] += abs(r['devBps'])
            else:
                b['fails'] += 1
    return book, last


def pick(folders, mind, taken=(), n=SHOW):
    """Different every time: never a site the partner took, never the mind's own last sources while others are left. Then the ones it has read least, a failing or off-chart source last. One perps source first, because only they carry funding."""
    book, last = history(folders, mind)
    def score(site):
        b = book.get(site) or {'n': 0, 'fails': 0, 'dev': 0.0, 'read': 0}
        return (site in last, b['fails'], b['n'], (b['dev'] / b['read']) if b['read'] else 0.0, site)
    free = sorted((s for s in SOURCES if s not in taken), key=score)
    perp = next((s for s in free if SOURCES[s][0] == 'perp'), None)
    rest = [s for s in free if s != perp]
    return ([perp] if perp else [])[:n] + rest[:max(0, n - (1 if perp else 0))]


def measure(site, market, read, chart_px, ms=0):
    """One read against the chart. → the row every folder files."""
    px = (read or {}).get('px')
    if not px or px <= 0 or not chart_px:
        return {'site': site, 'market': market, 'ok': False, 'kind': SOURCES[site][0], 'ms': ms}
    dev = round((px / chart_px - 1) * 10000, 1)
    return {'site': site, 'market': market, 'ok': True, 'kind': SOURCES[site][0], 'px': px, 'devBps': dev, 'off': abs(dev) > OFF_BPS, 'ms': ms,
            **({'funding': round(read['funding'], 5)} if read.get('funding') is not None else {}), **({'oi': read['oi']} if read.get('oi') is not None else {})}


async def read_one(http, site, market, chart_px):
    kind, url, parse = SOURCES[site]; t0 = time.time()
    try:
        r = await asyncio.wait_for(http.post('https://api.hyperliquid.xyz/info', json={'type': 'metaAndAssetCtxs'}) if url is None else http.get(url(market)), 6)
        return measure(site, market, parse(r.json(), market), chart_px, int((time.time() - t0) * 1000))
    except Exception:   # noqa: BLE001 — any failure is a recorded gap, and the mind is told it has no read from there
        return measure(site, market, None, chart_px, int((time.time() - t0) * 1000))


async def read_mind(http, sites, reads):
    """Every chosen source, on every market the chart has."""
    return list(await asyncio.gather(*(read_one(http, s, r['market'], r['px']) for s in sites for r in reads)))


def line(row):
    """A source's numbers for the model, with how far it sits from the chart."""
    if not row.get('ok'):
        return f"{row['site']} {row['market']}: no read"
    extra = (f" · funding {row['funding']:+.4f}% per 8h" if row.get('funding') is not None else '') + (f" · open interest {row['oi']:,.0f}" if row.get('oi') is not None else '')
    return f"{row['site']} {row['market']}: ${row['px']:,.2f} ({row['devBps']:+.1f} bps from the chart{', OFF' if row.get('off') else ''}){extra}"


def facts(rows, at):
    """Reads the chart agrees with become Research DNA evidence. An off-chart or failed read is not a fact."""
    out = []
    for r in rows:
        if r.get('ok') and not r.get('off'):
            out.append({'label': f"{r['market']} price", 'value': r['px'], 'site': r['site'], 'url': r['site'], 'at': at, 'verified': True, 'support': f"{r['px']} within {OFF_BPS} bps of the chart"})
            if r.get('funding') is not None:
                out.append({'label': f"{r['market']} funding", 'value': r['funding'], 'site': r['site'], 'url': r['site'], 'at': at, 'verified': True, 'support': f"{r['funding']}% per 8h"})
    return out

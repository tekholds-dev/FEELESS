"""📊 MARKET CAP IS THE CHART LANGUAGE (owner, 2026-10-12): a candle's price OHLC × the token's SUPPLY = its market-cap OHLC. One
resolver for that supply, in this order — and never an invented number:

  1. the canonical MintState's own supply (already resolved from an exact source: kept, it does not wobble with a provider's cap)
  2. launch metadata / a reliable token supply the row carries (our holder scan reads the mint's supply from the chain)
  3. a supported launchpad's fixed supply — Pump / Bonk launches mint exactly 1,000,000,000 tokens (the mint address ends in pump / bonk)
  4. the live market cap ÷ the live price from the same row (kept while a later read agrees within 10%)

Nothing → (None, None): the page says MARKET CAP UNAVAILABLE. It never falls back to charting the raw token price.
Pure — no fetch."""
LAUNCH_SUPPLY = 1_000_000_000.0
EXACT = ('token', 'launchpad')
STICKY_PCT = 10.0


def _f(v):
    try:
        x = float(v)
        return x if x == x and x not in (float('inf'), float('-inf')) else 0.0
    except (TypeError, ValueError):
        return 0.0


def is_launchpad(mint):
    return isinstance(mint, str) and mint.lower().endswith(('pump', 'bonk'))


def resolve(mint, price=None, mcap=None, known=None, prev=None):
    """→ (supply, source) · source = token | launchpad | market · (None, None) = unavailable."""
    ps, psrc = (prev or (None, None))
    if _f(ps) > 0 and psrc in EXACT:
        return _f(ps), psrc
    if _f(known) > 0:
        return _f(known), 'token'
    if is_launchpad(mint):
        return LAUNCH_SUPPLY, 'launchpad'
    p, mc = _f(price), _f(mcap)
    if p > 0 and mc > 0:
        s = mc / p
        if _f(ps) > 0 and abs(s / _f(ps) - 1) * 100 <= STICKY_PCT:
            return _f(ps), psrc or 'market'
        return s, 'market'
    if _f(ps) > 0:
        return _f(ps), psrc or 'market'
    return None, None


def mc(price, supply):
    """price × supply, or None when either is unknown (never 0, never the raw price)."""
    p, s = _f(price), _f(supply)
    return round(p * s, 2) if p > 0 and s > 0 else None


def mc_bar(bar, supply):
    """[t, o, h, l, c, v] in price → the same candle in market cap (volume untouched). None when the supply is unknown."""
    s = _f(supply)
    if s <= 0 or not bar or len(bar) < 5:
        return None
    return [bar[0], _f(bar[1]) * s, _f(bar[2]) * s, _f(bar[3]) * s, _f(bar[4]) * s] + list(bar[5:6])

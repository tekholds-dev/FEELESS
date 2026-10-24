"""⏱ KALSHI ODDS — the US-legal (CFTC-regulated) up / down markets, read-only, pure (`tests/test_kalshi_odds.py`). No order, no account.

The perps desk's ⏱ KALSHI tab: every market an UP / DOWN from $1 (each contract pays $1).
  · CRYPTO — BTC · ETH · SOL · DOGE · XRP: "price up in the next 15 mins?" (KX{COIN}15M: target, YES / NO asks, close) + the soonest
    day's above / below ladder (KX{COIN}D) — its strike nearest the live mark.
  · INDEXES — S&P 500 (KXINXU) · Nasdaq-100 (KXNASDAQ100U): "above X at <hour>?" ladders only — UP / DOWN = the soonest window's
    AT-THE-MONEY strike (the YES ask nearest 50 ¢: the market's own "from here"). Read via /events → that one event's markets (the
    Nasdaq ladder is 1,000+ rows across days).
Kalshi's public market data needs no key (api.elections.kalshi.com/trade-api/v2). Trading = DFlow's tokenized Kalshi markets
(kalshi_trade.py) — needs DFlow's production key + the user's Proof KYC.
"""
from fnum import nan_safe as _f

API = 'https://api.elections.kalshi.com/trade-api/v2'
MARKETS = {   # key → name, kind, the 15-min series (crypto) and the ladder series
    'BTC': {'name': 'Bitcoin', 'kind': 'crypto', 'm15': 'KXBTC15M', 'day': 'KXBTCD'},
    'ETH': {'name': 'Ethereum', 'kind': 'crypto', 'm15': 'KXETH15M', 'day': 'KXETHD'},
    'SOL': {'name': 'Solana', 'kind': 'crypto', 'm15': 'KXSOL15M', 'day': 'KXSOLD'},
    'DOGE': {'name': 'Dogecoin', 'kind': 'crypto', 'm15': 'KXDOGE15M', 'day': 'KXDOGED'},
    'XRP': {'name': 'XRP', 'kind': 'crypto', 'm15': 'KXXRP15M', 'day': 'KXXRPD'},
    'SPX': {'name': 'S&P 500', 'kind': 'index', 'm15': None, 'day': 'KXINXU'},
    'NDX': {'name': 'Nasdaq-100', 'kind': 'index', 'm15': None, 'day': 'KXNASDAQ100U'},
}
COINS = tuple(k for k, v in MARKETS.items() if v['kind'] == 'crypto')


def series(coin, kind):   # (kept for callers) the 15-min or the ladder series of a market
    m = MARKETS.get(coin) or {}
    return m.get('m15') if kind == '15m' else m.get('day')


def _px(v):
    x = _f(v)
    return round(x, 4) if 0 < x <= 1 else None


def strike(m):
    """A market's strike: `floor_strike`, else `custom_strike.floor_strike` (the DOGE ladder), else the ticker's '-T<strike>' tail."""
    s = _f((m or {}).get('floor_strike'))
    if s > 0:
        return s
    s = _f(((m or {}).get('custom_strike') or {}).get('floor_strike'))
    if s > 0:
        return s
    t = str((m or {}).get('ticker') or '')
    return _f(t.rsplit('-T', 1)[1]) if '-T' in t else 0.0


def _live(markets):
    return [m for m in markets or [] if m.get('status') in ('active', 'open')]


def fifteen(markets):
    """The open 15-minute 'up?' market → {ticker, target, yes, no, closes, vol24, oi} or None (no live market / no ask)."""
    live = [m for m in _live(markets) if m.get('market_type', 'binary') == 'binary']
    if not live:
        return None
    m = sorted(live, key=lambda x: str(x.get('close_time') or ''))[0]   # the soonest close = the window running now
    yes, no = _px(m.get('yes_ask_dollars')), _px(m.get('no_ask_dollars'))
    if yes is None and no is None:
        return None
    return {'ticker': m.get('ticker'), 'target': _f(m.get('floor_strike')) or None, 'yes': yes, 'no': no, 'closes': m.get('close_time'),
            'vol24': round(_f(m.get('volume_24h_fp'))), 'oi': round(_f(m.get('open_interest_fp')))}


def nearest(markets, mark):
    """The soonest day's ladder → the strike nearest the live mark: {ticker, strike, yes, closes} or None."""
    mk = _f(mark)
    rows = [m for m in _live(markets) if strike(m) > 0 and _px(m.get('yes_ask_dollars')) is not None]
    if not rows or mk <= 0:
        return None
    soon = min(str(x.get('close_time') or '9') for x in rows)   # the soonest day on the ladder (the series lists several days at once)
    m = min([x for x in rows if str(x.get('close_time') or '9') == soon], key=lambda x: abs(strike(x) - mk))
    return {'ticker': m.get('ticker'), 'strike': strike(m), 'yes': _px(m.get('yes_ask_dollars')), 'closes': m.get('close_time')}


def atm(markets):
    """An index ladder (one event) → its AT-THE-MONEY strike as the window's UP / DOWN: the YES ask nearest 50 ¢ — UP = YES ('above the
    target at the close'), DOWN = NO. {ticker, target, yes, no, closes, title} or None. A one-sided book (no NO ask) is still shown; the
    trade quotes it live."""
    rows = [m for m in _live(markets) if strike(m) > 0 and _px(m.get('yes_ask_dollars')) is not None]
    if not rows:
        return None
    soon = min(str(x.get('close_time') or '9') for x in rows)
    m = min([x for x in rows if str(x.get('close_time') or '9') == soon], key=lambda x: (abs(_px(x['yes_ask_dollars']) - 0.5), strike(x)))
    return {'ticker': m.get('ticker'), 'target': strike(m), 'yes': _px(m.get('yes_ask_dollars')), 'no': _px(m.get('no_ask_dollars')), 'closes': m.get('close_time'),
            'vol24': round(_f(m.get('volume_24h_fp'))), 'oi': round(_f(m.get('open_interest_fp')))}


def soonest_event(events):
    """/events rows → the event ticker that settles first (its `strike_date`), or None."""
    ev = [e for e in events or [] if e.get('event_ticker')]
    return min(ev, key=lambda e: str(e.get('strike_date') or '9'))['event_ticker'] if ev else None


def payout(ask, stake=1.0):
    """$ back on a win for `stake` at this ask (each contract pays $1): stake / ask. None when there is no ask."""
    a = _f(ask)
    return round(_f(stake) / a, 2) if 0 < a <= 1 else None

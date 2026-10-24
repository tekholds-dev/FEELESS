"""⏱ KALSHI ODDS — the US-legal (CFTC-regulated) crypto event markets, read-only, pure (`tests/test_kalshi_odds.py`). No order, no account.

The Perps dash shows what Kalshi's market prices for each perps coin right now:
  · 15-MIN UP — "BTC / ETH / SOL price up in next 15 mins?" (series KX{COIN}15M): the target price, YES / NO asks (= the odds, $ per
    $1 contract), the close time, volume, open interest;
  · 5 PM — the day's "above $X at 5 pm EDT?" ladder (KX{COIN}D): the strike nearest the live mark and its YES ask.
Kalshi's public market data needs no key (api.elections.kalshi.com/trade-api/v2/markets). Trading these from a wallet = DFlow's tokenized
Kalshi markets — needs DFlow's production key + the user's Proof KYC (CLAUDE.md › P0 #0); until then the dash shows the odds only.
"""
from fnum import nan_safe as _f

API = 'https://api.elections.kalshi.com/trade-api/v2/markets'
COINS = ('BTC', 'ETH', 'SOL')


def series(coin, kind):
    return f'KX{coin}15M' if kind == '15m' else f'KX{coin}D'


def _px(v):
    x = _f(v)
    return round(x, 4) if 0 < x <= 1 else None


def fifteen(markets):
    """The open 15-minute 'up?' market → {ticker, target, yes, no, closes (iso), vol24, oi} or None (no live market / no ask)."""
    live = [m for m in markets or [] if m.get('status') in ('active', 'open') and m.get('market_type', 'binary') == 'binary']
    if not live:
        return None
    m = sorted(live, key=lambda x: str(x.get('close_time') or ''))[0]   # the soonest close = the window running now
    yes, no = _px(m.get('yes_ask_dollars')), _px(m.get('no_ask_dollars'))
    if yes is None and no is None:
        return None
    return {'ticker': m.get('ticker'), 'target': _f(m.get('floor_strike')) or None, 'yes': yes, 'no': no, 'closes': m.get('close_time'),
            'vol24': round(_f(m.get('volume_24h_fp'))), 'oi': round(_f(m.get('open_interest_fp')))}


def nearest(markets, mark):
    """The soonest day's ladder → the strike nearest the live mark: {ticker, strike, yes, closes} or None. Strikes ride `floor_strike`."""
    mk = _f(mark)
    rows = [m for m in markets or [] if m.get('status') in ('active', 'open') and _f(m.get('floor_strike')) > 0 and _px(m.get('yes_ask_dollars')) is not None]
    if not rows or mk <= 0:
        return None
    soon = min(str(x.get('close_time') or '9') for x in rows)   # the soonest day on the ladder (the series lists several days at once)
    m = min([x for x in rows if str(x.get('close_time') or '9') == soon], key=lambda x: abs(_f(x['floor_strike']) - mk))
    return {'ticker': m.get('ticker'), 'strike': _f(m['floor_strike']), 'yes': _px(m.get('yes_ask_dollars')), 'closes': m.get('close_time')}


def payout(ask, stake=1.0):
    """$ back on a win for `stake` at this ask (each contract pays $1): stake / ask. None when there is no ask."""
    a = _f(ask)
    return round(_f(stake) / a, 2) if 0 < a <= 1 else None

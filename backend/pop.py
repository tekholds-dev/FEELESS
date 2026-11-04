"""📉 PoP — PROOF OF PERPS (owner 2026-11-04). The perps twin of a PoW folder: both minds read the live market on their own, each calls a side and its
levels, and the engine files the trade only when they agree on the market and the side, taking the safer of both numbers. It then runs on true prices
with hard exits: take profit, stop, liquidation, time.

PAPER ONLY. Nothing is signed, sent or held. Real orders wait for their own guards and the owner's approval (WORK_QUEUE FC04, DECISIONS #1 and #8).
P/L here never includes fees. Pure and tested: the service holds the store, the clock and the network.
"""
import json
import re

MARKETS = ('SOL', 'ETH', 'BTC')
LEV_MIN, LEV_MAX = 1.1, 5.0       # the desk allows far more; an agent's proof stays small enough that a normal day does not liquidate it
TP_RANGE = (0.5, 25.0)            # take profit, % price move
SL_RANGE = (0.3, 10.0)            # stop, % price move
HOLD_MAX_S = 3600                 # a proof ends within the hour
COLLATERAL_USD = 10.0             # the paper stake every proof is measured on
FILED_MAX = 40
SYS = ('You are {name}, one of two independent minds filing a PoP (Proof of Perps) on FEELESS. This is a paper trade on true prices. Read the live market below and '
       'make your own call. Reply JSON only: {{"market": "SOL|ETH|BTC", "side": "long|short|none", "lev": 1.1-5, "tp_pct": price move %, "sl_pct": price move %, "why": "one line citing the numbers"}}. '
       'Use "none" when nothing in the numbers justifies a trade. The other mind does not see your answer.')
COMMANDS = [('file a PoP', 'Both minds: read SOL, ETH and BTC, call a side, and run a paper perps trade on true prices if they agree'), ('stop PoP', 'Ends the open PoP at the live price')]
_START = re.compile(r'(?i)^\s*(?:/pop\b|(?:file|start|run|do)\s+(?:a\s+|the\s+)?pop\b|pop\s*$|proof of perps\s*$)')
_STOP = re.compile(r'(?i)^\s*(?:stop|end|close)\s+(?:the\s+)?pop\b')


def command(text):
    t = str(text or '')
    return 'stop' if _STOP.match(t) else 'start' if _START.match(t) else None


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _clip(v, lo, hi):
    return max(lo, min(hi, _f(v, lo)))


def parse_call(raw):
    """A mind's reply → its clamped call, or None when it gave no usable side (no trade is ever guessed from prose)."""
    m = re.search(r'\{.*\}', str(raw or ''), re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        return None
    market, side = str(d.get('market') or '').upper(), str(d.get('side') or '').lower()
    if market not in MARKETS or side not in ('long', 'short'):
        return None
    return {'market': market, 'side': side, 'lev': round(_clip(d.get('lev'), LEV_MIN, LEV_MAX), 2), 'tp': round(_clip(d.get('tp_pct'), *TP_RANGE), 2), 'sl': round(_clip(d.get('sl_pct'), *SL_RANGE), 2), 'why': str(d.get('why') or '')[:220]}


def agree(calls):
    """Every mind must call the same market and side. → (the trade on the safer numbers, why) or (None, why). The tighter take profit, stop and leverage win."""
    calls = list(calls or [])
    if not calls or any(c is None for c in calls):
        return None, 'a mind called no trade'
    if len({(c['market'], c['side']) for c in calls}) > 1:
        return None, ' vs '.join(f"{c['side']} {c['market']}" for c in calls)
    c0 = calls[0]
    return {'market': c0['market'], 'side': c0['side'], 'lev': min(c['lev'] for c in calls), 'tp': min(c['tp'] for c in calls), 'sl': min(c['sl'] for c in calls)}, 'both minds agree'


def liq_move_pct(lev):
    """The price move that wipes the collateral, a little before 100% for maintenance margin."""
    return round(100 / max(_f(lev), 1.0) * 0.9, 2)


def move_pct(entry, px, side):
    entry, px = _f(entry), _f(px)
    if entry <= 0 or px <= 0:
        return 0.0
    return (px / entry - 1) * 100 * (1 if side == 'long' else -1)


def roe_pct(trade, px):
    return round(move_pct(trade.get('entry'), px, trade.get('side')) * _f(trade.get('lev'), 1), 2)


def hard_exit(trade, px, now):
    """The first hard exit reached, or None. A liquidation outranks a stop on the same read."""
    if _f(px) <= 0:
        return None
    mv = move_pct(trade.get('entry'), px, trade.get('side'))
    if mv <= -liq_move_pct(trade.get('lev')):
        return 'liquidated'
    if mv <= -_f(trade.get('sl')):
        return 'stop'
    if mv >= _f(trade.get('tp')):
        return 'take profit'
    if _f(now) - _f(trade.get('openedAt')) >= HOLD_MAX_S:
        return 'time'
    return None


def close(trade, px, now, why):
    """The filed result. A liquidation loses the whole stake, however far the last read overshot."""
    roe = -100.0 if why == 'liquidated' else roe_pct(trade, px)
    return {**trade, 'status': 'closed', 'exit': _f(px), 'closedAt': round(_f(now)), 'why': why, 'roePct': roe, 'pnlUsd': round(COLLATERAL_USD * roe / 100, 2), 'won': roe > 0}


def market_line(s):
    """A market read for the model: numbers only."""
    return f"{s['market']}-PERP price ${s['px']:,.2f} · 24h {s['chgPct']:+.2f}% · range ${s['low']:,.2f} to ${s['high']:,.2f} · volume {s['vol']:,.0f}"


def read_market(market, stats, ticker):
    """Coinbase's public stats + ticker → the market read, or None when either has no price."""
    px, opn = _f((ticker or {}).get('price')), _f((stats or {}).get('open'))
    if px <= 0 or opn <= 0:
        return None
    return {'market': market, 'px': px, 'chgPct': round((px / opn - 1) * 100, 2), 'high': _f(stats.get('high')), 'low': _f(stats.get('low')), 'vol': _f(stats.get('volume'))}

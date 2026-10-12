"""⚡ MARKET-EVENT WAKEUPS (owner, 2026-10-11: "the chart should DRIVE the timing — the timer should never be the reason we miss the move").

The office keeps its ~60s full pass. Between passes the 6-second fast guard reads the SAME live price the FEELESS charts draw (the candles
service's stream price, one batched local call) and these pure rules decide whether that price is a MATERIAL change for a held position
(→ Reaper's tick now, on freshly refreshed live candles) or for a waiting candidate (→ an early agents' pass, so Trigger re-reads it).
No new polling of any provider. Pure + tested (`tests/test_market_wake.py`).
"""

MOVE_POS = 2.5        # % since Reaper's last decision price → wake
NEW_HIGH = 1.0        # a new local high this many points above the recorded peak → wake (let it run / arm the trail)
GIVEBACK_MIN = 2.0    # a winner (peak ≥ RUN_MIN) giving back ≥ max(2 pts, 30% of its peak) → wake NOW
GIVEBACK_SHARE = 0.30
RUN_MIN = 3.0
MOVE_CAND = 3.0       # a waiting candidate moving this much since its read → wake Trigger
BREAKOUT = 0.5        # % above the candidate's local high (its last candles) = a live breakout
GAP_POS = 6.0         # seconds between two wakes of the same position
GAP_CAND = 8.0        # seconds between two early agent passes (a pass reads every coin: it is not free)
RUN_STATES = ('ACCELERATING', 'RUNNING', 'STALLING', 'REVERSING', 'BREAKING DOWN')


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def position_wake(p, px):
    """A held position (Reaper's record: entry, peak %, decPx = the price of its last decision, thesis support / invalidation) and the
    live price now → [reasons] (empty = nothing material)."""
    p = p or {}
    entry, px = _f(p.get('entry')), _f(px)
    if entry <= 0 or px <= 0:
        return []
    pct = (px / entry - 1) * 100
    out = []
    dec = _f(p.get('decPx'))
    if dec > 0 and abs(px / dec - 1) * 100 >= MOVE_POS:
        out.append(f"price {(px / dec - 1) * 100:+.1f}% since the last decision")
    peak = _f(p.get('peak'))
    if pct >= peak + NEW_HIGH and pct > 0:
        out.append(f'new high {pct:+.1f}%')
    if peak >= RUN_MIN and peak - pct >= max(GIVEBACK_MIN, peak * GIVEBACK_SHARE):
        out.append(f'reversal: {pct:+.1f}% from a {peak:+.1f}% peak')
    th = p.get('thesis') or {}
    for k, w in (('invalidation', 'invalidation'), ('support', 'support')):
        lv = _f(th.get(k))
        if lv > 0 and px < lv <= (dec or px * 1.5):
            out.append(f'crossed below {w}')
            break
    return out


def candidate_wake(c, px):
    """A waiting candidate ({px: price at its read, high: its local high from the live candles}) and the live price → [reasons]."""
    c = c or {}
    px, at = _f(px), _f(c.get('px'))
    if px <= 0 or at <= 0:
        return []
    out = []
    mv = (px / at - 1) * 100
    if abs(mv) >= MOVE_CAND:
        out.append(f'{mv:+.1f}% since its read')
    hi = _f(c.get('high'))
    if hi > 0 and px >= hi * (1 + BREAKOUT / 100) and at < hi * (1 + BREAKOUT / 100):
        out.append('live breakout above its local high')
    return out


def due(last_at, now, gap):
    return now - _f(last_at) >= gap


def run_state(pct, peak, vel=None, broke=False):
    """While holding: ACCELERATING · RUNNING · STALLING · REVERSING · BREAKING DOWN (support / invalidation lost)."""
    pct, peak = _f(pct), _f(peak)
    if broke:
        return 'BREAKING DOWN'
    if vel == 'REVERSING' or (peak >= RUN_MIN and peak - pct >= max(GIVEBACK_MIN, peak * GIVEBACK_SHARE)):
        return 'REVERSING'
    if vel == 'ACCELERATING' and pct > 0:
        return 'ACCELERATING'
    if pct > 0 and peak - pct <= max(1.0, peak * 0.15):
        return 'RUNNING'
    return 'STALLING'


# chart_intel state → the owner's market-phase words (CURRENT live candles)
PHASE_OF = {'EARLY': 'EARLY MOVE', 'ACCUMULATION': 'BASE', 'COMPRESSION': 'BASE', 'RANGE': 'BASE', 'CHOP': 'BASE',
            'BREAKOUT ATTEMPT': 'BREAKOUT', 'CONFIRMED BREAKOUT': 'BREAKOUT', 'STRONG UPTREND': 'RUNNING', 'UPTREND': 'RUNNING', 'PULLBACK IN UPTREND': 'RUNNING',
            'PARABOLIC': 'ACCELERATION', 'DISTRIBUTION': 'DISTRIBUTION', 'FAILED BREAKOUT': 'REVERSAL',
            'DOWNTREND': 'COLLAPSE', 'LIQUIDITY FAILURE': 'COLLAPSE', 'BOT LADDER': 'COLLAPSE'}


def market_phase(chart, li=None):
    """BASE · EARLY MOVE · ACCELERATION · BREAKOUT · RUNNING · DISTRIBUTION · REVERSAL · COLLAPSE from the live chart (+ the launch read)."""
    st = (chart or {}).get('state')
    ph = (li or {}).get('phase')
    if ph in ('DISTRIBUTION', 'COLLAPSE'):
        return ph
    if ph == 'ACCELERATING' and PHASE_OF.get(st) in (None, 'BASE', 'EARLY MOVE'):
        return 'ACCELERATION'
    return PHASE_OF.get(st) or ('EARLY MOVE' if ph == 'EARLY FOMO' else None)


def ages(now, price_at=None, tape_at=None, candle_at=None, input_at=None, decision_at=None):
    """Data freshness for a seat (seconds; None = never read) — nothing is called LIVE on stale inputs."""
    a = lambda t: None if not t else max(0, round(now - _f(t)))
    out = {'price': a(price_at), 'tape': a(tape_at), 'candle': a(candle_at), 'input': a(input_at), 'decision': a(decision_at)}
    known = [v for v in out.values() if v is not None]
    out['stale'] = bool(known) and (out['price'] is None or out['price'] > 30 or (out['candle'] is not None and out['candle'] > 90))
    return out

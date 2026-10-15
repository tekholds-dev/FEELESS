"""⏱ THE CANDLE CLOCK (owner, 2026-10-15: "countdown till candle close is another vital for AI / agents to know the best entry"). Pure + tested.

Measured on 292 confirmed real agent trades (buy send time inside its 5-minute candle), oldest 60% / newest 40%, rugs left OUT:
  first 100s of the 5m candle   +2.6% avg, 60% won   ·   −2.8% avg, 40% won
  the rest of the candle         +6.6% avg, 69% won   ·   +1.0% avg, 51% won
(and more of the rugs). So a NEW agent buy waits until the 5-minute candle is 100s old — a wait, never a veto; the seat fills the moment it
passes. The 1-minute candle showed no stable edge, so it is only shown. `candleClock` false = off. The regret ledger grades what it held back."""

FIVE = 300
EARLY_SEC = 100


def clock(now):
    """→ {s1, left1, s5, left5}: seconds into / until the close of the current 1m and 5m candle (UTC buckets, like the charts)."""
    s1, s5 = int(now) % 60, int(now) % FIVE
    return {'s1': s1, 'left1': 60 - s1, 's5': s5, 'left5': FIVE - s5}


def wait_why(now, cfg=None):
    """The reason a new buy waits right now, or None."""
    if (cfg or {}).get('candleClock') is False:
        return None
    c = clock(now)
    if c['s5'] < EARLY_SEC:
        return f"⏱ the 5m candle is {c['s5']}s old — buys wait until {EARLY_SEC}s (record: entries in the first {EARLY_SEC}s did worse in both halves)"
    return None


def line(now):
    """For a model case: where we are inside the candles right now."""
    c = clock(now)
    return f"1m candle {c['s1']}s in, closes in {c['left1']}s · 5m candle {c['s5']}s in, closes in {c['left5']}s" + (' · EARLY in the 5m candle (our record: worse entries)' if c['s5'] < EARLY_SEC else '')

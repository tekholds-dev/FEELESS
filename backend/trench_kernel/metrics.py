"""📏 THE KERNEL'S TIMINGS — what the page needs to prove the office is fast where it matters. Pure.

`Timings` = bounded rings of measured durations (p50 / p95 / last / n), noted by the service at the moment each thing happens:
  readyToSeatSec        a candidate turned READY → the seat was created for it (decision → order)
  discoveryToEntrySec   first seen by the kernel → seated
  ageAtEntryMin         the coin's launch age when it was seated
  wakeToDecisionSec     a live market event woke the office → the kernel had re-judged
`execution(ledger, events, card, now)` reads the keeper's own rows for the agents' fills: decision → submitted (the seat event → the tx
sent), submitted → confirmed (the keeper's `landSec`: sent → booked from the chain), and the whole decision → confirmed. The ledger is
the truth: a fill is `status: filled` with a signature — nothing here guesses one.
"""
KEEP = 200
WINDOW_SEC = 24 * 3600.0
MATCH_SEC = 300.0   # a seat event and the buy it caused are at most this far apart


from fnum import nan_safe as _f


def _p(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * q))], 2) if xs else None


def stat(xs):
    xs = [x for x in xs if x is not None]
    return {'n': len(xs), 'p50': _p(xs, 0.5), 'p95': _p(xs, 0.95), 'last': round(xs[-1], 2) if xs else None, 'max': round(max(xs), 2) if xs else None}


class Timings:
    def __init__(self):
        self.rings = {}

    def note(self, key, value):
        if value is None:
            return
        self.rings[key] = (self.rings.get(key) or [])[-(KEEP - 1):] + [round(_f(value), 3)]

    def view(self):
        return {k: stat(v) for k, v in sorted(self.rings.items())}


def execution(ledger, events, card, now, window=WINDOW_SEC):
    """The agents' real fills of the last `window`, timed from the keeper's ledger. → {fills, decisionToSubmitSec, submitToConfirmSec
    (fill latency), decisionToConfirmSec, pending, unmatched} — `unmatched` = seat events with no filled buy yet (still landing, or the
    seat went back to cash)."""
    t0 = _f(now) - window
    buys = [r for r in ledger or [] if r.get('side') == 'buy' and r.get('status') == 'filled' and r.get('sig') and (card is None or r.get('card') == card) and _f(r.get('at')) >= t0 - MATCH_SEC]
    d2s, s2c, d2c, unmatched, used = [], [], [], 0, set()
    for e in events or []:
        if e.get('kind') != 'agent' or e.get('move') not in ('fill', 'swap') or _f(e.get('at')) < t0 or not e.get('mint'):
            continue
        at = _f(e['at'])
        r = next((r for r in buys if r.get('mint') == e['mint'] and id(r) not in used and -5 <= _f(r.get('confirmedAt') or r.get('at')) - at <= MATCH_SEC), None)
        if not r:
            unmatched += 1
            continue
        used.add(id(r))
        conf = _f(r.get('confirmedAt') or r.get('at'))
        land = r.get('landSec')
        sent = _f(r.get('sentAt')) or (conf - _f(land) if land is not None else 0.0)
        if sent > 0:
            d2s.append(max(0.0, sent - at))
        if land is not None:
            s2c.append(_f(land))
        d2c.append(max(0.0, conf - at))
    lands = [_f(r.get('landSec')) for r in buys if r.get('landSec') is not None]
    return {'fills': len(d2c), 'decisionToSubmitSec': stat(d2s), 'submitToConfirmSec': stat(s2c), 'decisionToConfirmSec': stat(d2c),
            'fillLatencySec': stat(lands), 'unmatched': unmatched, 'windowH': round(window / 3600, 1)}

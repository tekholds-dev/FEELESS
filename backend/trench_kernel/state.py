"""📦 ONE canonical MintState per mint + ONE candidate lifecycle + the event-emitting store (owner's command-kernel spec, 2026-10-12).

Every source (open board · newest launches · Pump live / pulse / trending / migrations · callouts · movers · volume · new pools · tracked lists)
lands in the SAME MintState — a mint is never two candidates. Each section carries its OWN timestamp (priceAt · marketAt · candleAt · holderAt
· walletAt · researchAt · executionAt): nothing pretends to be fresher than its slowest input.

Candidate lifecycle (one meaning everywhere):
  DISCOVERED → TRACKING → CONTENDING → READY → ORDER_PENDING → HELD → EXIT_PENDING → CLOSED
Data that has not arrived yet (holder scan, early wallets, research, candles, unknown age / cap) is a PENDING data state, never a rejection.
Cooldown is metadata (`coolUntil`), not a separate universe. Pure (no I/O) and fast; tested in tests/test_trench_kernel.py.
"""
import time as _time

STATES = ('DISCOVERED', 'TRACKING', 'CONTENDING', 'READY', 'ORDER_PENDING', 'HELD', 'EXIT_PENDING', 'CLOSED')
DATA = ('PENDING', 'READY', 'UNKNOWN', 'FAILED')
EVENTS = ('new', 'price', 'volume', 'buyers', 'liquidity', 'candle', 'chart', 'holders', 'wallets', 'research', 'order', 'peak', 'invalidation')
MATERIAL = {'price': 2.0, 'liquidity': 10.0, 'volume': 50.0, 'buyers': 15.0}   # % change that counts as an event
KEEP = 3000


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _pct(a, b):
    a, b = _f(a), _f(b)
    return abs(b / a - 1) * 100 if a > 0 and b > 0 else 0.0


def from_row(row, now, sources=()):
    """The desk row (Tally's tape + the board's numbers + the chart read + the launch intel) → one MintState. Pure."""
    x = row or {}
    n, v, ch, li = x.get('nums') or {}, x.get('vitals') or {}, x.get('chart') or {}, x.get('li') or {}
    safe = v.get('safe')
    soc = bool(x.get('site') or x.get('x') or v.get('site') or v.get('x') or (x.get('social') or {}).get('ok'))
    return {
        'identity': {'mint': x.get('mint'), 'symbol': x.get('symbol'), 'pair': x.get('pair') or x.get('pairAddress'),
                     'sources': sorted(set(list(sources or ()) + [s for s in (x.get('src') or []) if isinstance(s, str)])),
                     'ageH': v.get('ageH'), 'launch': (x.get('launch') or {}).get('type')},
        'market': {'price': _f(x.get('px')) or None, 'marketCap': v.get('mcap'), 'liquidity': n.get('liq') or v.get('liq'), 'volume5m': n.get('v5'),
                   'volume1h': v.get('vol1h'), 'pace': n.get('pace'), 'buyShare': n.get('buy'), 'move5m': n.get('d5'), 'liqChange': n.get('liqD'),
                   'trades1h': v.get('txns1h'), 'priceAt': now, 'marketAt': now},
        'chart': {'state': ch.get('state'), 'phase': x.get('mp'), 'src': ch.get('src'), 'candles': ch.get('n'), 'quality': (ch.get('q') or {}).get('state'),
                  'entry': (ch.get('entry') or [None])[0], 'candleAt': ch.get('at') or (now if ch.get('src') == 'candles' else None)},
        'chain': {'holderStatus': 'READY' if safe is not None else 'PENDING', 'holderSafe': safe, 'top10': v.get('top10'), 'rug': v.get('rug'),
                  'earlyWallets': li.get('ewp') or ('PENDING' if not li else 'UNKNOWN'), 'press': li.get('press'), 'pressWhy': li.get('pressWhy'),
                  'cls': li.get('cls'), 'holderAt': v.get('scanAt') or (now if safe is not None else None), 'walletAt': li.get('at') or (now if li else None)},
        'research': {'status': 'READY' if soc else 'UNKNOWN', 'site': x.get('site') or v.get('site'), 'x': x.get('x') or v.get('x'), 'researchAt': now if soc else None},
        'objections': [list(o)[:2] for o in (x.get('ev') or []) if o],   # Devil's EVIDENCE from the senses (trench_kernel.senses.evidence) — never the paper desk's objs / drule
        'row': x,   # the desk row itself (opportunity.* reads it); never serialised into the payload
    }


def material(prev, cur):
    """Which events a new MintState raises against the previous one (only what changed enough to matter)."""
    if not prev:
        return ['new']
    ev = []
    pm, cm = prev['market'], cur['market']
    if _pct(pm.get('price'), cm.get('price')) >= MATERIAL['price']:
        ev.append('price')
    if _pct(pm.get('liquidity'), cm.get('liquidity')) >= MATERIAL['liquidity']:
        ev.append('liquidity')
    if _pct(pm.get('volume5m'), cm.get('volume5m')) >= MATERIAL['volume']:
        ev.append('volume')
    if pm.get('buyShare') is not None and cm.get('buyShare') is not None and abs(_f(cm['buyShare']) - _f(pm['buyShare'])) >= MATERIAL['buyers']:
        ev.append('buyers')
    if prev['chart'].get('state') != cur['chart'].get('state') or prev['chart'].get('phase') != cur['chart'].get('phase'):
        ev.append('chart')
    if prev['chain'].get('holderStatus') != cur['chain'].get('holderStatus'):
        ev.append('holders')
    if prev['chain'].get('earlyWallets') != cur['chain'].get('earlyWallets'):
        ev.append('wallets')
    if prev['research'].get('status') != cur['research'].get('status'):
        ev.append('research')
    return ev


class MintStore:
    """The ONE place a mint's state lives. `ingest` upserts rows from any source (deduped by mint) and returns the events raised; only the
    mints with events are re-judged by the brain. Bounded; counts duplicates dropped and events for the metrics."""

    def __init__(self):
        self.mints = {}       # mint → MintState
        self.cand = {}        # mint → {status, since, coolUntil, why}
        self.stats = {'events': 0, 'dupes': 0, 'ingested': 0, 'firstSeen': {}}

    def ingest(self, rows, now, source=None):
        """→ {mint: [events]} for the rows that changed materially (a new mint raises 'new')."""
        out, seen = {}, set()
        for r in rows or []:
            m = (r or {}).get('mint')
            if not m:
                continue
            if m in seen:   # the same mint twice in one batch (two sources): one object, the duplicate dropped
                self.stats['dupes'] += 1
                continue
            seen.add(m)
            prev = self.mints.get(m)
            srcs = ((prev or {}).get('identity') or {}).get('sources') or []
            cur = from_row(r, now, srcs + ([source] if source else []))
            ev = material(prev, cur)
            self.mints[m] = cur
            self.stats['ingested'] += 1
            if 'new' in ev:
                self.stats['firstSeen'][m] = now
                self.cand.setdefault(m, {'status': 'DISCOVERED', 'since': now})
            if ev:
                out[m] = ev
                self.stats['events'] += len(ev)
        if len(self.mints) > KEEP:   # bounded: the oldest-seen mints that hold no position go first
            for m in sorted(self.mints, key=lambda k: self.stats['firstSeen'].get(k, 0))[:len(self.mints) - KEEP]:
                if (self.cand.get(m) or {}).get('status') not in ('ORDER_PENDING', 'HELD', 'EXIT_PENDING'):
                    self.mints.pop(m, None); self.cand.pop(m, None); self.stats['firstSeen'].pop(m, None)
        return out

    def set_status(self, m, status, now, why=None):
        assert status in STATES, status
        c = self.cand.setdefault(m, {'status': 'DISCOVERED', 'since': now})
        if c['status'] != status:
            c.update(status=status, since=now)
        if why is not None:
            c['why'] = why
        return c


def ages(ms, now):
    """Per-section freshness (seconds; None = never read) — the UI shows these instead of one generic 'live'."""
    a = lambda t: None if not t else round(max(0.0, now - _f(t)), 1)
    return {'price': a(ms['market'].get('priceAt')), 'market': a(ms['market'].get('marketAt')), 'candle': a(ms['chart'].get('candleAt')),
            'holders': a(ms['chain'].get('holderAt')), 'wallets': a(ms['chain'].get('walletAt')), 'research': a(ms['research'].get('researchAt'))}


def times(ms):
    """Per-section ABSOLUTE timestamps (None = never read) — stable between passes, so an unchanged coin produces no delta."""
    a = lambda t: None if not t else round(_f(t), 2)
    return {'price': a(ms['market'].get('priceAt')), 'market': a(ms['market'].get('marketAt')), 'candle': a(ms['chart'].get('candleAt')),
            'holders': a(ms['chain'].get('holderAt')), 'wallets': a(ms['chain'].get('walletAt')), 'research': a(ms['research'].get('researchAt'))}


def now():
    return _time.time()

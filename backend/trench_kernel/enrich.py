"""🔎 THE ONE ENRICHMENT SCHEDULER — deep chain scans (holders · early wallets · launch facts) by PRIORITY, on a BUDGET, with freshness that
survives a restart. Pure state machine (no I/O, no clock of its own); the service owns the actual scan and calls `request → due → started →
finished`. Tested in tests/test_kernel_enrich.py.

WHY (measured after a restart, 2026-10-12): 808 logical RPC calls → 1,062 physical attempts → 612 rate-limit answers, 104 holder scans
queued at once. Nothing was wrong with any single scan: every board build asked for every coin it listed, the scan cache had forgotten
everything older than its TTL, and nothing ordered or paced the work. So:

  PRIORITY   0 HELD · 1 READY · 2 a hunter lane's coin / a coin someone is LOOKING at · 3 top CONTENDING · 4 fast movers · 5 everything else
  BUDGET     in RPC CALLS a second (a first scan of a coin ≈ 40 calls, a re-scan ≈ 4): a token bucket that halves itself when a scan comes
             back rate-limited and recovers 10% a clean scan — the work adapts to what the lanes can answer instead of hammering them
  FRESHNESS  lastSuccessfulScan / lastAttempt per mint, saved to disk: after a restart a coin scanned 5 minutes ago is still FRESH, and one
             that is not waits its turn in the queue (a held or ready coin first; the rest staggered) — never 100 scans at once
  NEGATIVE   a scan that failed is not asked again for a doubling back-off (45s → 15 min); RATE_LIMITED and UNAVAILABLE are states of the
             EVIDENCE — the coin stays visible and ranked, it is never rejected for them
  LOW PRIORITY coins already scanned are re-scanned 4× less often (an unchanged coin nobody is acting on is not re-read every 15 minutes)

Holder data enriches reasoning; it must never dominate RPC, and a brand-new coin enters discovery and ranking with ZERO chain calls.
"""
PRIO = {'HELD': 0, 'READY': 1, 'ARMED': 2, 'LOOK': 2, 'CONTENDING': 3, 'MOVER': 4, 'REST': 5}
PRIO_NAME = {0: 'HELD', 1: 'READY', 2: 'ARMED / LOOK', 3: 'CONTENDING', 4: 'MOVER', 5: 'REST'}
STATUS = ('FRESH', 'STALE', 'PENDING', 'RATE_LIMITED', 'UNAVAILABLE')   # states of the EVIDENCE (never a candidate state)
TTL = 900.0             # a complete scan is FRESH this long …
LOW_TTL_MULT = 4.0      # … × this for a coin nobody is acting on (priority ≥ 4)
COST_NEW, COST_RESCAN = 40.0, 4.0     # RPC calls: launch facts are read once (~40 calls), a holder re-scan is ~4
CALLS_PER_SEC = 2.0     # the scheduler's budget across every lane (the lanes' own limits still apply underneath)
BURST = 48.0            # one first scan + two re-scans may start at once; never more
RATE_FLOOR = 0.25       # the adaptive rate never drops under a quarter of the budget
CONCURRENCY = 4
BACKOFF = (45.0, 90.0, 180.0, 360.0, 900.0)   # failed 1× … 5×+
RATE_LIMIT_BACKOFF = 30.0
QUEUE_MAX = 400
BOOT_GRACE = 120.0      # after a start: low-priority first requests are spread over this long (deterministic jitter per mint)
KEEP = 4000             # freshness records kept (newest)


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _jit(mint):
    """A stable 0…1 for a mint (so a stagger is reproducible and needs no random source)."""
    h = 0
    for ch in str(mint):
        h = (h * 131 + ord(ch)) % 1_000_003
    return h / 1_000_003


class Enricher:
    def __init__(self, boot_at=0.0, calls_per_sec=CALLS_PER_SEC, concurrency=CONCURRENCY, ttl=TTL):
        self.boot = _f(boot_at)
        self.base = max(0.05, _f(calls_per_sec))
        self.rate = self.base
        self.concurrency = int(concurrency)
        self.ttl = _f(ttl)
        self.tokens, self.tokAt = COST_RESCAN * 2, self.boot      # a restart starts with room for two re-scans, not a burst
        self.fresh = {}       # mint → {'ok': last success, 'try': last attempt, 'fails': n, 'until': negative-cache end, 'rl': rate-limited last time}
        self.queue = {}       # mint → {'prio', 'at' (queued), 'why', 'notBefore', 'cost'}
        self.inflight = {}    # mint → started at
        self.count = {'requested': 0, 'started': 0, 'completed': 0, 'failed': 0, 'skippedFresh': 0, 'deferred': 0, 'rateLimited': 0, 'dropped': 0, 'joined': 0}
        self.started_by = {}  # priority → scans started

    # ── freshness ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def ttl_for(self, prio):
        return self.ttl * (LOW_TTL_MULT if int(prio) >= 4 else 1.0)

    def is_fresh(self, mint, now, prio=5):
        f = self.fresh.get(mint)
        return bool(f and f.get('ok') and now - _f(f['ok']) < self.ttl_for(prio))

    def status(self, mint, now):
        """The EVIDENCE state of a coin's deep scan — never a verdict on the coin."""
        f = self.fresh.get(mint) or {}
        if f.get('ok') and now - _f(f['ok']) < self.ttl:
            return 'FRESH'
        if mint in self.inflight or mint in self.queue:
            return 'STALE' if f.get('ok') else 'PENDING'
        if _f(f.get('until')) > now:
            return 'RATE_LIMITED' if f.get('rl') else 'UNAVAILABLE'
        return 'STALE' if f.get('ok') else 'PENDING'

    # ── the queue ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def request(self, mint, prio, why, now, known=True):
        """Ask for a coin's deep scan. → 'fresh' (nothing to do) · 'inflight' · 'queued' · 'deferred' (negative cache / the queue is full
        of more important coins). A coin already queued keeps its place and takes the HIGHER priority of the two requests."""
        if not mint:
            return 'deferred'
        prio = int(prio)
        self.count['requested'] += 1
        if self.is_fresh(mint, now, prio):
            self.count['skippedFresh'] += 1
            return 'fresh'
        if mint in self.inflight:
            self.count['joined'] += 1
            return 'inflight'
        f = self.fresh.get(mint) or {}
        if _f(f.get('until')) > now and prio > 0:     # a failed scan rests (a HELD coin may always try again)
            self.count['deferred'] += 1
            return 'deferred'
        q = self.queue.get(mint)
        if q:
            self.count['joined'] += 1
            if prio < q['prio']:
                q.update(prio=prio, why=why, notBefore=min(_f(q.get('notBefore')), now) if prio <= 3 else q.get('notBefore'))
            return 'queued'
        nb = now
        if prio >= 4 and now - self.boot < BOOT_GRACE:   # after a start the low-priority first scans are spread out, never fired together
            nb = max(now, self.boot + BOOT_GRACE * _jit(mint))
        if len(self.queue) >= QUEUE_MAX:
            worst = max(self.queue.items(), key=lambda kv: (kv[1]['prio'], kv[1]['at']))
            if worst[1]['prio'] <= prio:
                self.count['dropped'] += 1
                return 'deferred'
            self.queue.pop(worst[0]); self.count['dropped'] += 1
        self.queue[mint] = {'prio': prio, 'at': now, 'why': str(why)[:40], 'notBefore': nb, 'cost': COST_RESCAN if (known or f.get('ok')) else COST_NEW}
        return 'queued'

    def _refill(self, now):
        self.tokens = min(BURST, self.tokens + max(0.0, now - self.tokAt) * self.rate)
        self.tokAt = now

    def due(self, now):
        """The scans to START now, most important first: inside the concurrency limit and the call budget. A HELD coin's scan is never
        held back by the budget (it borrows; the bucket goes negative and the rest wait)."""
        self._refill(now)
        out = []
        order = sorted(((q['prio'], q['at'], m) for m, q in self.queue.items() if _f(q['notBefore']) <= now))
        for prio, _at, m in order:
            if len(self.inflight) + len(out) >= self.concurrency:
                break
            cost = self.queue[m]['cost']
            if self.tokens < cost and prio > 0:
                break     # strictly by priority: a cheaper low-priority scan never jumps a waiting important one
            self.tokens -= cost
            out.append(m)
        return out

    def started(self, mint, now):
        q = self.queue.pop(mint, None) or {'prio': 5}
        self.inflight[mint] = now
        self.fresh[mint] = {**(self.fresh.get(mint) or {}), 'try': now}
        self.count['started'] += 1
        self.started_by[q['prio']] = self.started_by.get(q['prio'], 0) + 1
        return q

    def finished(self, mint, now, ok, rate_limited=False):
        """A scan ended. Success → fresh for the TTL. Failure → a doubling back-off; a rate-limited one also halves the scheduler's rate."""
        self.inflight.pop(mint, None)
        f = dict(self.fresh.get(mint) or {})
        if ok:
            f.update(ok=now, fails=0, until=0.0, rl=False)
            self.count['completed'] += 1
            self.rate = min(self.base, self.rate * 1.1)
        else:
            n = int(f.get('fails') or 0) + 1
            f.update(fails=n, until=now + (RATE_LIMIT_BACKOFF if rate_limited and n <= 1 else BACKOFF[min(n, len(BACKOFF)) - 1]), rl=bool(rate_limited))
            self.count['failed'] += 1
            if rate_limited:
                self.count['rateLimited'] += 1
                self.rate = max(self.base * RATE_FLOOR, self.rate * 0.5)
        self.fresh[mint] = f
        if len(self.fresh) > KEEP:
            for m in sorted(self.fresh, key=lambda k: max(_f(self.fresh[k].get('ok')), _f(self.fresh[k].get('try'))))[:len(self.fresh) - KEEP]:
                if m not in self.inflight and m not in self.queue:
                    self.fresh.pop(m, None)

    def note_success(self, mint, at):
        """A scan that ran outside the queue (a user opened a coin's case file) still counts as fresh evidence."""
        f = dict(self.fresh.get(mint) or {})
        if _f(at) > _f(f.get('ok')):
            f.update(ok=_f(at), fails=0, until=0.0, rl=False)
            self.fresh[mint] = f

    def next_in(self, now):
        """Seconds until something could start (None = nothing waiting) — for the service's one wake-up timer."""
        if not self.queue:
            return None
        if len(self.inflight) >= self.concurrency:
            return 1.0
        self._refill(now)
        best = min(self.queue.values(), key=lambda q: (q['prio'], q['at']))
        wait_nb = max(0.0, min(_f(q['notBefore']) for q in self.queue.values()) - now)
        wait_tok = 0.0 if self.tokens >= best['cost'] or best['prio'] == 0 else (best['cost'] - self.tokens) / max(self.rate, 1e-6)
        return round(max(0.05, min(30.0, max(wait_nb, wait_tok))), 2)

    # ── persistence ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def snapshot(self, now, max_age=6 * 3600.0):
        """What survives a restart: when each coin was last scanned / tried and how often it failed (newest KEEP, ≤ max_age)."""
        rows = {m: [round(_f(f.get('ok')), 1), round(_f(f.get('try')), 1), int(f.get('fails') or 0), round(_f(f.get('until')), 1), 1 if f.get('rl') else 0]
                for m, f in self.fresh.items() if now - max(_f(f.get('ok')), _f(f.get('try'))) <= max_age}
        return {'v': 1, 'at': now, 'rows': rows}

    def restore(self, snap, now, have=None):
        """Bring the freshness book back. `have` = the mints whose scan RESULT is also back in memory: a coin whose result is gone is not
        called fresh (its `ok` is dropped), so the next request scans it — in its turn. → how many records came back"""
        n = 0
        for m, r in ((snap or {}).get('rows') or {}).items():
            try:
                ok, tr, fails, until, rl = (list(r) + [0, 0, 0, 0, 0])[:5]
            except TypeError:
                continue
            if have is not None and m not in have:
                ok = 0.0
            if m not in self.fresh:
                self.fresh[m] = {'ok': _f(ok), 'try': _f(tr), 'fails': int(fails or 0), 'until': _f(until), 'rl': bool(rl)}
                n += 1
        return n

    # ── metrics ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def metrics(self, now):
        q = list(self.queue.values())
        return {'queueDepth': len(q), 'oldestQueueAge': round(max((now - _f(x['at']) for x in q), default=0.0), 1) if q else 0.0, 'inflight': len(self.inflight),
                'byPriority': {PRIO_NAME.get(p, str(p)): sum(1 for x in q if x['prio'] == p) for p in sorted({x['prio'] for x in q})},
                'startedByPriority': {PRIO_NAME.get(p, str(p)): n for p, n in sorted(self.started_by.items())},
                'holderScansStarted': self.count['started'], 'holderScansCompleted': self.count['completed'], 'holderScansFailed': self.count['failed'],
                'holderScansSkippedFresh': self.count['skippedFresh'], 'holderScansDeferred': self.count['deferred'] + self.count['dropped'], 'joined': self.count['joined'],
                'rateLimited': self.count['rateLimited'], 'requested': self.count['requested'], 'callsPerSec': round(self.rate, 2), 'budgetCallsPerSec': self.base,
                'concurrency': self.concurrency, 'known': len(self.fresh), 'bootAgo': round(now - self.boot, 1), 'nextIn': self.next_in(now)}

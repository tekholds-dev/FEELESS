"""📡 DexScreener pacing — ONE choke point per process for every request to api.dexscreener.com.

DexScreener allows ~300 requests a minute per IP (pairs / tokens / search) and ~60 for profiles, boosts and takeovers. The market
service (5001) and the reputation service (5077) share the owner's IP, and 34 call sites in reputation_service called it with no
pacing at all: after a restart they burst 100–190 calls a minute from 5001 alone, DexScreener answered 429, and lists that are built
from its data (🔥 Pump trending in the swap picker) went EMPTY. Each process gets its own share (`install(rpm)`; together < 300):
requests wait for a slot instead of bursting (never longer than `MAX_WAIT`), and a 429 pauses that host for Retry-After seconds
(default 15) — the next callers wait it out instead of hammering. Pure pacing: payloads, URLs and caching are unchanged.
"""
import asyncio
import time

import httpx

HOST = 'api.dexscreener.com'
SLOW_PATHS = ('/token-profiles', '/token-boosts', '/community-takeovers', '/orders')   # the 60-a-minute endpoints
MAX_WAIT = 12.0          # a request never waits longer than this for a slot (callers have caches + stale data behind them)
COOL_DEFAULT = 15.0      # a 429 without Retry-After pauses this long
COOL_MAX = 60.0


class Bucket:
    """Token bucket: `rpm` a minute, bursts up to `burst`. `clock` is injectable for tests."""

    def __init__(self, rpm, burst=None, clock=time.monotonic):
        self.rate = rpm / 60.0
        self.cap = float(burst if burst is not None else max(3, rpm // 10))
        self.tokens = self.cap
        self.clock = clock
        self.at = clock()
        self.cool_until = 0.0
        self.waits = 0
        self.limited = 0

    def _fill(self):
        now = self.clock()
        self.tokens = min(self.cap, self.tokens + (now - self.at) * self.rate)
        self.at = now
        return now

    def wait_for(self):
        """Seconds until this request may go (0 = now); takes the slot when it returns 0."""
        now = self._fill()
        if now < self.cool_until:
            return self.cool_until - now
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0
        return (1 - self.tokens) / self.rate

    def cool(self, secs):
        self.limited += 1
        self.cool_until = max(self.cool_until, self.clock() + max(1.0, min(COOL_MAX, secs)))
        self.tokens = 0.0


_BUCKETS = {}
_lock = None


def bucket_for(path):
    return _BUCKETS.get('slow' if path.startswith(SLOW_PATHS) else 'main')


def retry_after(resp):
    try:
        return float(resp.headers.get('retry-after') or COOL_DEFAULT)
    except (TypeError, ValueError):
        return COOL_DEFAULT


async def acquire(path, sleep=asyncio.sleep):
    b = bucket_for(path)
    if not b:
        return
    waited = 0.0
    while waited < MAX_WAIT:
        w = b.wait_for()
        if w <= 0:
            return
        b.waits += 1
        step = min(w, MAX_WAIT - waited)
        await sleep(step)
        waited += step


def stats():
    return {k: {'waits': b.waits, 'limited': b.limited, 'coolingSec': round(max(0.0, b.cool_until - b.clock()), 1)} for k, b in _BUCKETS.items()}


def install(rpm=120, slow_rpm=25):
    """Pace every httpx request to DexScreener in THIS process. Idempotent."""
    _BUCKETS['main'] = Bucket(rpm)
    _BUCKETS['slow'] = Bucket(slow_rpm, burst=3)
    if getattr(httpx.AsyncClient.send, '_ds_paced', False):
        return
    orig = httpx.AsyncClient.send

    async def send(self, request, *a, **kw):
        if request.url.host != HOST:
            return await orig(self, request, *a, **kw)
        path = request.url.path
        await acquire(path)
        resp = await orig(self, request, *a, **kw)
        if resp.status_code == 429:
            b = bucket_for(path)
            if b:
                b.cool(retry_after(resp))
        return resp

    send._ds_paced = True
    httpx.AsyncClient.send = send

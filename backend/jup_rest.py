"""📡 A REFUSED JUPITER READ LANE RESTS (pure pacing, one choke point per process — the DexScreener one is `ds_pace`).

2026-10-13, market service, 21 minutes: 389 token lookups on the public lane and 147 on the read key — every one answered 429, and each
refused call was followed by the next half a second later, which is what keeps a rate-limited lane shut. A lane = host + key + path family
(`/tokens/` or `/price/`). After a 429 the lane rests its Retry-After (1–30s, else REST_SEC); while it rests a call to it answers 429 at once,
with NO network request — callers already treat 429 as "use the other source / the last copy". Swap / quote paths are never touched:
the keeper paces its own lanes. `stats()` counts what was really sent, refused and spared."""
import time

import httpx

HOSTS = ('lite-api.jup.ag', 'api.jup.ag')
FAMILIES = ('/tokens/', '/price/')
REST_SEC = 8.0
_rest = {}
_stats = {'sent': 0, 'refused': 0, 'spared': 0}


def lane_of(host, path, key=''):
    """The lane a request rides, or None when it is not a Jupiter READ (quotes / swaps / other hosts)."""
    if host not in HOSTS:
        return None
    fam = next((f for f in FAMILIES if str(path or '').startswith(f)), None)
    return None if not fam else f"{host}|{str(key or '')[-6:]}|{fam}"


def rest_sec(retry_after):
    try:
        v = float(retry_after)
        return v if 1.0 <= v <= 30.0 else REST_SEC
    except (TypeError, ValueError):
        return REST_SEC


def resting(lane, now):
    return now < _rest.get(lane, 0.0)


def note(lane, status, retry_after, now):
    """Record one real answer: a 429 puts the lane to rest."""
    _stats['sent'] += 1
    if status == 429:
        _stats['refused'] += 1
        _rest[lane] = now + rest_sec(retry_after)


def stats():
    now = time.time()
    return {**_stats, 'resting': sum(1 for v in _rest.values() if v > now)}


def install():
    """Rest refused Jupiter read lanes for every httpx request in THIS process. Idempotent."""
    if getattr(httpx.AsyncClient.send, '_jup_rest', False):
        return
    orig = httpx.AsyncClient.send

    async def send(self, request, *a, **kw):
        lane = lane_of(request.url.host, request.url.path, request.headers.get('x-api-key'))
        if not lane:
            return await orig(self, request, *a, **kw)
        if resting(lane, time.time()):
            _stats['spared'] += 1
            return httpx.Response(429, request=request, headers={'x-feeless-rest': '1'}, content=b'{}')
        resp = await orig(self, request, *a, **kw)
        note(lane, resp.status_code, resp.headers.get('retry-after'), time.time())
        return resp

    send._jup_rest = True
    for flag in ('_ds_paced',):   # keep the DexScreener pacer's own idempotence mark when it wrapped first
        if getattr(orig, flag, False):
            setattr(send, flag, True)
    httpx.AsyncClient.send = send

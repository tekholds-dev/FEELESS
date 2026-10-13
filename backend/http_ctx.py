"""⚡ ONE TLS context per process for every httpx.AsyncClient.

Most call sites open a client per request (`async with httpx.AsyncClient(...)`). Each new client built its own SSL context — loading the
whole CA bundle again: ~6 ms of blocked event loop on an idle machine, seconds under memory pressure, hundreds of times a minute
(loop_lag, 2026-10-12: stalls on the `httpx.AsyncClient(` line of _live_px, _jup_prices, _rpc_physical …). A client that does not pass
its own `verify` now shares one context (same CA bundle, same verification). Nothing else about a client changes.
"""
import httpx

_state = {'ctx': None, 'installed': False, 'shared': 0}


def context():
    if _state['ctx'] is None:
        _state['ctx'] = httpx.create_ssl_context()
    return _state['ctx']


def install():
    if _state['installed']:
        return
    _state['installed'] = True
    orig = httpx.AsyncClient.__init__

    def init(self, *a, **k):
        if 'verify' not in k and 'transport' not in k and 'mounts' not in k:
            k['verify'] = context()
            _state['shared'] += 1
        orig(self, *a, **k)
    httpx.AsyncClient.__init__ = init


def stats():
    return {'shared': _state['shared']}

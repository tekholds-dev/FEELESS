"""🛡 SITE-2 · HTTP ARMOR: one plain ASGI middleware, the same on all four services (5001 · 5077 · 5088 · 5099). Tested: tests/test_http_armor.py.

  SIZE      a request body over its cap is refused with 413 before the route reads it (Content-Length up front; a chunked body is counted as it
            arrives). Uploads get the bigger cap. Our own services between themselves get the biggest.
  SLOW      a client that dribbles its body (slowloris) gets 408: each chunk must arrive within CHUNK_S and the whole body within BODY_S.
  BULKHEAD  each route group (the first four path parts) may run at most PER_ROUTE requests at once from outside. One stuck or flooded
            endpoint fills only its own lane and answers 503 + Retry-After; every other route keeps its full speed.
Our own services (internal addresses) are never bulkheaded. Nothing here blocks anyone: the per-IP write limits stay in guard.py.
"""
import asyncio
import json
import time

MAX_BODY = 8 * 1024 * 1024
MAX_UPLOAD = 40 * 1024 * 1024
MAX_INTERNAL = 64 * 1024 * 1024
UPLOAD_HINTS = ('/upload', '/files', '/image', '/avatar', '/media', '/attach', '/shot')
CHUNK_S = 10.0
BODY_S = 30.0
PER_ROUTE = 48


def route_key(path):
    return '/'.join(str(path or '/').split('/')[:5])


def cap_for(path, internal):
    if internal:
        return MAX_INTERNAL
    p = str(path or '').lower()
    return MAX_UPLOAD if any(h in p for h in UPLOAD_HINTS) else MAX_BODY


async def _send_json(send, status, detail, headers=()):
    body = json.dumps({'detail': detail}).encode()
    await send({'type': 'http.response.start', 'status': status, 'headers': [(b'content-type', b'application/json'), (b'content-length', str(len(body)).encode()), *headers]})
    await send({'type': 'http.response.body', 'body': body})


class HttpArmor:
    def __init__(self, app, is_internal=None, per_route=None, chunk_s=None, body_s=None):
        self.app = app; self.is_internal = is_internal or (lambda ip: False)
        self.per_route = per_route or PER_ROUTE; self.chunk_s = chunk_s or CHUNK_S; self.body_s = body_s or BODY_S
        self.busy = {}

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            return await self.app(scope, receive, send)
        ip = (scope.get('client') or ('', 0))[0]
        internal = bool(self.is_internal(ip))
        path = scope.get('path') or '/'
        cap = cap_for(path, internal)
        hdrs = dict((k.lower(), v) for k, v in scope.get('headers') or [])
        try:
            declared = int(hdrs.get(b'content-length', b'0') or 0)
        except ValueError:
            declared = 0
        if declared > cap:
            return await _send_json(send, 413, f'Too large: the most this accepts is {cap // (1024 * 1024)} MB.')
        key = route_key(path)
        if not internal:
            if self.busy.get(key, 0) >= self.per_route:
                return await _send_json(send, 503, 'This part of the site is busy. Try again in a moment.', [(b'retry-after', b'2')])
            self.busy[key] = self.busy.get(key, 0) + 1
        try:
            body = b''; t0 = time.monotonic(); more = scope.get('method') in ('POST', 'PUT', 'PATCH', 'DELETE')
            while more:   # the whole body first, under its cap and its clock; the route then reads it from memory
                left = self.body_s - (time.monotonic() - t0)
                try:
                    msg = await asyncio.wait_for(receive(), timeout=max(0.05, min(self.chunk_s, left)))
                except asyncio.TimeoutError:
                    return await _send_json(send, 408, 'The request body came too slowly.')
                if msg.get('type') != 'http.request':
                    return None   # the client left
                body += msg.get('body') or b''
                if len(body) > cap:
                    return await _send_json(send, 413, f'Too large: the most this accepts is {cap // (1024 * 1024)} MB.')
                more = bool(msg.get('more_body'))
            if scope.get('method') not in ('POST', 'PUT', 'PATCH', 'DELETE'):
                return await self.app(scope, receive, send)   # nothing was read: the route gets the untouched stream
            replay = [{'type': 'http.request', 'body': body, 'more_body': False}]

            async def replay_receive():
                return replay.pop() if replay else await receive()   # after the body: only the real disconnect
            await self.app(scope, replay_receive, send)
        finally:
            if not internal:
                self.busy[key] = max(0, self.busy.get(key, 1) - 1)
                if not self.busy[key]:
                    self.busy.pop(key, None)

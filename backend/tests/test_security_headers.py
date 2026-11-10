"""SITE-9: the reputation and market services send nosniff + no-referrer on every response (5088 already did)."""
from fastapi.testclient import TestClient


def test_reputation_and_server_send_security_headers():
    import reputation_service as rs
    r = TestClient(rs.app).get('/api/reputation/metas')
    assert r.headers.get('x-content-type-options') == 'nosniff' and r.headers.get('referrer-policy') == 'no-referrer'


def test_a_coins_logo_url_can_never_make_the_server_call_a_private_address(monkeypatch):
    """SITE-9: metadata URLs are the launcher's choice. Loopback / LAN are refused, and so is a public URL that redirects to one."""
    import asyncio
    import feeless_mcp as fm
    import reputation_service as rs
    monkeypatch.setattr(fm, 'safe_url', lambda u: None if 'public.example' in u else 'private')
    called = []

    class R:
        def __init__(self, code, loc=None, body=b'x'): self.status_code = code; self.headers = {'location': loc, 'content-type': 'image/png'} if loc else {'content-type': 'image/png'}; self.content = body
    class Http:
        async def get(self, u, **k):
            called.append(u); assert k.get('follow_redirects') is False
            return R(302, 'http://127.0.0.1:5088/api/cats/leader') if u.endswith('/hop') else R(200)
    run = lambda urls: asyncio.run(rs._fetch_first(Http(), urls))
    assert run(['http://127.0.0.1:5088/x', 'http://192.168.1.20:1234/v1/models']) is None and called == []
    assert run(['https://public.example/hop']) is None and called == ['https://public.example/hop']     # the redirect target was never called
    assert run(['https://public.example/logo.png']) == ('image/png', b'x')


def test_writes_are_rate_limited_per_caller_and_internal_calls_never(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, 'WRITES_PER_MIN', 3); rs._WRITE_HITS.clear()
    c = TestClient(rs.app)
    codes = [c.post('/api/reputation/pv', json={}, headers={'x-forwarded-for': '9.9.9.9'}).status_code for _ in range(5)]
    assert codes[3:] == [429, 429] and 429 not in codes[:3]
    assert c.post('/api/reputation/pv', json={}, headers={'x-forwarded-for': '8.8.8.8'}).status_code != 429     # another caller is untouched
    assert c.get('/api/reputation/metas', headers={'x-forwarded-for': '9.9.9.9'}).status_code == 200            # reads are never limited
    assert c.post('/api/reputation/internal/notify', json={}, headers={'x-forwarded-for': '9.9.9.9', 'x-feeless-internal': 'x'}).status_code != 429
    rs._WRITE_HITS.clear()

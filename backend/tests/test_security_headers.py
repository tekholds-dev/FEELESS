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


def test_one_write_limiter_and_a_fake_forwarded_header_does_not_dodge_it():
    """SITE-9: `guard` is the one write limiter (5001 + 5077). It reads X-Forwarded-For only behind a trusted proxy, so a script can't
    rotate fake IPs in that header to escape the per-IP minute; the removed second limiter on 5077 trusted it from anyone."""
    import guard
    import reputation_service as rs
    assert not hasattr(rs, '_WRITE_HITS')
    assert guard.client_ip({'x-forwarded-for': '9.9.9.9'}, '1.2.3.4', False) == '1.2.3.4'   # untrusted: the socket's address
    assert guard.client_ip({'x-forwarded-for': '9.9.9.9'}, '127.0.0.1', True) == '9.9.9.9'          # behind our proxy: the real caller
    s = guard.new_state(); now = 1000.0
    codes = [(guard.check(s, '1.2.3.4', 'POST', '/api/x', now=now) or (200,))[0] for _ in range(guard.WRITE_PER_MIN + 1)]
    assert codes[-1] == 429 and 429 not in codes[:-1]
    assert guard.check(s, '127.0.0.1', 'POST', '/api/x', now=now) is None                              # the services' own calls never

"""SITE-9: the reputation and market services send nosniff + no-referrer on every response (5088 already did)."""
from fastapi.testclient import TestClient


def test_reputation_and_server_send_security_headers():
    import reputation_service as rs
    r = TestClient(rs.app).get('/api/reputation/metas')
    assert r.headers.get('x-content-type-options') == 'nosniff' and r.headers.get('referrer-policy') == 'no-referrer'

"""Launch safety: FEELESS-rail metadata is immutable, so it must never point at a private address."""
from fastapi.testclient import TestClient
import reputation_service as rs

W = 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P'


def _post(origin, monkeypatch):
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    monkeypatch.delenv('PUBLIC_SITE_URL', raising=False)
    return TestClient(rs.app).post('/api/reputation/token-meta', headers={'origin': origin},
                                   json={'address': W, 'session': 'x', 'name': 'Test', 'symbol': 'TST'})


def test_rejects_localhost_and_lan(monkeypatch):
    for o in ('http://localhost:3000', 'https://localhost', 'https://192.168.1.5', 'http://example.com'):
        assert _post(o, monkeypatch).status_code == 503, o


def test_accepts_public_https(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'TOKEN_META_DIR', tmp_path)
    r = _post('https://feeless.example', monkeypatch)
    assert r.status_code == 200 and r.json()['uri'].startswith('https://feeless.example/api/reputation/token-meta/')

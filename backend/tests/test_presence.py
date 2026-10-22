"""🟢 presence: online / away show as chosen, invisible always reads offline, silence for STALE_SEC = offline, memory is capped."""
import presence as pr


def test_modes_staleness_and_cap(monkeypatch):
    s = {}
    pr.beat(s, 'A', 'online', 100); pr.beat(s, 'B', 'away', 100); pr.beat(s, 'C', 'invisible', 100); pr.beat(s, 'D', 'hacker', 100)
    assert [pr.status(s, w, 150) for w in 'ABCD'] == ['online', 'away', 'offline', 'online']
    assert pr.status(s, 'A', 100 + pr.STALE_SEC + 1) == 'offline' and pr.status(s, 'Z', 100) == 'offline'
    monkeypatch.setattr(pr, 'MAX_ROWS', 3)
    for i in range(5):
        pr.beat(s, f'W{i}', 'online', 200 + i)
    assert len(s) == 3 and set(s) == {'W2', 'W3', 'W4'}


def test_the_routes_need_a_session_to_beat_and_read_in_bulk(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    c = TestClient(rs.app)
    assert c.post('/api/reputation/presence', json={'address': 'A' * 44, 'session': 'nope', 'mode': 'online'}).status_code == 401
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    assert c.post('/api/reputation/presence', json={'address': 'A' * 44, 'session': 'ok', 'mode': 'away'}).json()['mode'] == 'away'
    assert c.get(f"/api/reputation/presence?a={'A' * 44},{'B' * 44}").json() == {'A' * 44: 'away', 'B' * 44: 'offline'}

import json
import reputation_service as rs
from fastapi.testclient import TestClient


def test_public_board_never_leaks_report_text(monkeypatch):
    rs.BUGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    rs.BUGS_PATH.write_text(json.dumps({'bugs': [{'id': 'b1', 'text': 'secret 9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin', 'kind': 'security', 'count': 1, 'at': 1, 'address': 'ME'}]}))
    r = TestClient(rs.app).get('/api/reputation/support').json()
    assert r['reports'][0]['title'].startswith('🔒') and 'address' not in r['reports'][0] and 'text' not in r['reports'][0]
    assert r['counts']['open'] == 1 and len(r['ladder']) == 4


def test_actions_need_a_signed_wallet():
    c = TestClient(rs.app)
    assert c.post('/api/reputation/support', json={'wallet': 'x' * 32, 'session': '', 'q': 'A real question?', 'options': ['a', 'b']}).status_code == 401

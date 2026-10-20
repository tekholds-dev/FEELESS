def test_cats_ai_merges_nexas_fresh_read_and_admin_route_is_owner_only(monkeypatch):
    import time
    import reputation_service as rs
    from fastapi.testclient import TestClient
    rs._nexa_mem.put({'last': {'avoid': ['PX'], 'exit': ['PE'], 'favor': [], 'why': 'w', 'at': time.time()}}, time.time())
    rs._feecat_ai.update(avoid=['PA'], exit=[], read=time.time())
    c = TestClient(rs.app)
    d = c.get('/api/reputation/cats-ai').json()
    assert d['avoid'] == ['PA', 'PX'] and d['exit'] == ['PE'] and 'NEXA' in d['models']
    assert c.get('/api/reputation/admin/nexa').status_code in (401, 403)
    rs._nexa_mem.put({'last': {'avoid': ['PX'], 'at': time.time() - 2000}}, time.time())
    assert 'PX' not in c.get('/api/reputation/cats-ai').json()['avoid']   # a stale read is not acted on

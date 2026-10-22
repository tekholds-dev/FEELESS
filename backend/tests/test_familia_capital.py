"""👑 Fee City in the public world view + the owner's Familia rules route (owner, 2026-10-21)."""


def test_world_view_has_five_cities_the_capital_landmarks_and_the_ladder(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(rs, '_cartels_now', lambda now: [])
    c = TestClient(rs.app)
    d = c.get('/api/reputation/familia-world').json()
    assert [x['key'] for x in d['cities']] == ['fee', 'harbor', 'heights', 'bay', 'docks']
    assert d['cities'][0]['plots'] == 24 and sum(x['plots'] for x in d['cities']) == len(d['blocks'])
    assert {l['key'] for l in d['landmarks']} == {'arena', 'house', 'mansion', 'shield', 'launch'} and all(l['lore'] for l in d['landmarks'])
    assert d['rules']['fuseMinMp'] == 2000 and isinstance(d['ranked'], list)


def test_familia_rules_route_is_owner_only_and_clamps(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    c = TestClient(rs.app)
    assert c.get('/api/reputation/admin/familia/rules').status_code in (401, 403)
    store = {}
    monkeypatch.setattr(rs, '_require_owner', lambda request: 'OWNER')
    monkeypatch.setattr(rs, '_admin_load', lambda: store)
    monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    monkeypatch.setattr(rs, '_audit', lambda *a, **k: None)
    try:
        d = c.post('/api/reputation/admin/familia/rules', json={'blockMp': 3000, 'fuseMinMp': 2500, 'hitCapUsd': 999}).json()
        assert d['rules']['blockMp'] == 3000 and d['rules']['fuseMinMp'] == 2500 and d['rules']['hitCapUsd'] == 100
        assert d['blockPrice']['fee'] == int(3000 * 2.5) and len(d['economy']['cities']) == 5
    finally:
        rs._fworld.set_rules(rs._fworld.RULES)

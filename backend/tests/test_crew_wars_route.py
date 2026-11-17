def test_the_war_list_has_its_own_route_never_the_family_lookup():
    import reputation_service as rs
    paths = [r.path for r in __import__('_routes').flat_routes(rs.app)]
    assert '/api/reputation/crew-wars' in paths
    assert '/api/reputation/crews/wars' not in paths   # /crews/{cid} would swallow it

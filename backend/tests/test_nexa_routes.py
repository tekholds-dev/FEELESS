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


def test_a_background_read_is_the_fast_numbers_only_read_until_the_full_one_is_due(monkeypatch):
    import asyncio
    import time
    import reputation_service as rs
    P1, P2 = 'A' * 44, 'B' * 44
    asks = []

    async def fake_ask(http, env, cfg, q, **kw):
        asks.append({'q': q, **kw})
        return {'text': '{"exit":["O1"],"avoid":[],"favor":["N1"],"why":"N1 40 buyers"}' if kw.get('system') == rs._nexa.ASK_FAST else 'no json', 'ms': 1800}

    async def no_rules():
        return {}

    async def no_px(m):
        return {}
    monkeypatch.setattr(rs._air.ROUTER, 'ask', fake_ask)
    monkeypatch.setattr(rs, '_feecat_packet', lambda: {'openTrades': [{'pairAddress': P1, 'symbol': 'BONK', 'cap': 45000}], 'nextCoins': [{'pairAddress': P2, 'symbol': 'WIF', 'buyers': 40}]})
    monkeypatch.setattr(rs, '_feecat_rules', no_rules)
    monkeypatch.setattr(rs, '_agent_inherit_rows', lambda limit=12: [])
    monkeypatch.setattr(rs, '_live_px', no_px)
    monkeypatch.setattr(rs._air, 'provider', lambda env, k, cfg: {})
    monkeypatch.setattr(rs._air, 'rig', lambda prov, k, d: 0)
    rs._nexa_rt.update(busy=False, chatAt=0)
    now = time.time()
    rs._nexa_mem.put({'fullAt': now - 60}, now)   # the full read ran a minute ago → this one is FAST
    asyncio.run(rs._nexa_tick(now, {}, {}))
    a = asks[-1]
    assert a['system'] == rs._nexa.ASK_FAST and a['tune']['maxTok'] == rs._nexa.FAST_TOK and P1 not in a['q'] and a['q'].startswith('O1 $BONK')
    st = rs._nexa_mem.get()
    assert st['mode'] == 'fast' and st['last']['exit'] == [P1] and st['last']['favor'] == [P2] and st['reads'][-1]['mode'] == 'fast'
    rs._nexa_mem.put({**st, 'fullAt': now - 4000, 'at': 0}, now)   # an hour on → the FULL read
    asyncio.run(rs._nexa_tick(now + 1, {}, {}))
    assert asks[-1]['system'] != rs._nexa.ASK_FAST and rs._nexa_mem.get()['mode'] == 'full'

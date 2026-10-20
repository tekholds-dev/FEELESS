import why_pump as wp


PAIR = {'baseToken': {'address': 'M', 'symbol': 'PKMN'}, 'marketCap': 400000, 'liquidity': {'usd': 60000},
        'priceChange': {'m5': 4, 'h1': 120, 'h6': 300, 'h24': 1327}, 'volume': {'m5': 9000, 'h1': 150000, 'h24': 300000},
        'txns': {'h1': {'buys': 700, 'sells': 300}}, 'info': {'websites': [{'url': 'https://pkmn.fun'}], 'socials': [{'type': 'twitter', 'url': 'https://x.com/pkmn'}, {'type': 'telegram', 'url': 'javascript:x'}]}}


def test_numbers_fill_from_the_pair_and_name_the_biggest_move():
    n = wp.from_pair(PAIR, wp.numbers({'row': {'top10': 22}}))
    assert n['symbol'] == 'PKMN' and n['buyShare'] == 70.0 and n['top10'] == 22
    assert wp.biggest_move(n) == ('24 hours', 1327)
    assert wp.headline_of(n).startswith('$PKMN pumped 14.3x in 24 hours')
    assert wp.socials_of(PAIR) == {'site': 'https://pkmn.fun', 'x': 'https://x.com/pkmn'}   # a javascript: link never passes


def test_engine_drivers_are_measured_and_strongest_first():
    n = wp.from_pair(PAIR, {'callers': 4, 'pros': 1})
    d = wp.engine_drivers(n)
    assert all(x['source'] == 'ENGINE' for x in d)
    assert '50%' in d[0]['why'] and 'hour' in d[0]['why']
    assert any('4 Pump callers' in x['why'] for x in d) and any('70% of trades are buys' in x['why'] for x in d)
    assert wp.verdict_of(n) == 'CALLERS'


def test_model_driver_with_an_invented_source_is_dropped():
    txt = '{"headline": "PKMN ran on a Nintendo rumor", "verdict": "news", "drivers": [{"why": "a tweet", "source": "https://x.com/fake/1"}, {"why": "real story", "source": "https://news.site/a"}, {"why": "volume", "source": "ENGINE"}], "risk": "rumor dies"}'
    m = wp.parse(txt, ['https://news.site/a'])
    assert [x['source'] for x in m['drivers']] == ['https://news.site/a', 'ENGINE'] and m['verdict'] == 'NEWS'
    a = wp.answer({'symbol': 'PKMN'}, [{'why': 'volume', 'source': 'ENGINE'}, {'why': 'buyers', 'source': 'ENGINE'}], m, [{'title': 't', 'url': 'https://news.site/a'}])
    assert a['by'] == 'model' and len(a['drivers']) == 3 and a['sources'][0]['url'] == 'https://news.site/a'
    assert wp.parse('no json here', []) is None


def test_endpoint_answers_from_the_engine_and_caches_for_everyone(monkeypatch):
    import asyncio
    import reputation_service as rs
    from fastapi.testclient import TestClient

    async def pair(m):
        return PAIR
    monkeypatch.setattr(rs, '_why_pair', pair)

    async def cr(m):
        return {'row': {}}
    monkeypatch.setattr(rs, 'coin_read', cr)
    import feeless_mcp as mcp
    monkeypatch.setattr(mcp, '_search_rows', lambda q, n: [])
    rs._why_cache.clear()
    c = TestClient(rs.app)
    mint = 'J49Y17m7PYYYs6WfCZAJjiu6F633dNDMtL3t8UXPgxga'
    r = c.get(f'/api/reputation/why-pump/{mint}').json()
    assert r['by'] == 'engine' and r['headline'].startswith('$PKMN') and r['drivers']
    assert c.get(f'/api/reputation/why-pump/{mint}').json()['cached'] is True
    assert c.get('/api/reputation/why-pump-board').json()['recent'][0]['mint'] == mint
    assert c.get('/api/reputation/why-pump/notamint').status_code == 400


def test_a_model_restating_our_number_is_one_driver():
    m = {'drivers': [{'why': '67% of trades are buys, buyers dominate', 'source': 'ENGINE'}]}
    a = wp.answer({'symbol': 'X'}, [{'why': '67% of trades are buys — buyers are in control', 'source': 'ENGINE'}, {'why': 'top 10 hold 56%', 'source': 'ENGINE'}], m, [])
    assert [d['why'] for d in a['drivers']] == ['67% of trades are buys, buyers dominate', 'top 10 hold 56%']

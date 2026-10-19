import reputation_service as rs


def test_feecat_reads_each_coin_like_the_agents_and_hears_the_models():
    c = {'chart': {'state': 'UPTREND', 'germDist': 6.4, 'hl': 3, 'll': 0, 'distHigh': 12.3}}
    r = rs.feecat_read(c, ['hhhl', 'germ'], None)
    assert r == {'setups': ['hhhl', 'germ'], 'bad': None, 'struct': 'UPTREND', 'germ': 6.4, 'hl': 3, 'll': 0, 'distHigh': 12.3}
    log = [{'mint': 'M', 'model': 'OSSY', 'action': 'BUY', 'why': 'germ floor', 'at': 900},
           {'mint': 'M', 'model': 'G4', 'action': 'TALK', 'view': 'SELL', 'why': 'lower low', 'at': 950},
           {'model': 'G4', 'action': 'REVIEW', 'symbol': 'X', 'pct': 5, 'why': 'held to the take line', 'at': 960}]
    w = rs.duo_word(log, 'M', 1000)
    assert w['who'] == 'G4' and w['action'] == 'SELL' and w['ago'] == 50
    assert rs.duo_word(log, 'M', 1000 + 4000) is None
    les = rs.duo_lessons(log, {'G4': {'n': 3}})
    assert les['record'] == {'G4': {'n': 3}} and les['lessons'][0]['lesson'] == 'held to the take line'

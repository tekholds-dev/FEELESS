import time


def test_cooling_off_and_proven_callers_lists(monkeypatch):
    import reputation_service as rs
    tv = lambda word, rug=20: {'call': ['x', word, 'good'], 'rug': rug}
    rows = [{'mint': 'D', 'symbol': 'DRY', 'pairAddress': 'pd', 'price': 1, 'safe': True, 'vol1h': 10, 'tv': tv('DRYING UP')},
            {'mint': 'C', 'symbol': 'COOL', 'pairAddress': 'pc', 'price': 1, 'safe': True, 'vol1h': 90, 'tv': tv('COOLING')},
            {'mint': 'U', 'symbol': 'UNSAFE', 'pairAddress': 'pu', 'price': 1, 'safe': False, 'tv': tv('COOLING')},
            {'mint': 'R', 'symbol': 'RUGGY', 'pairAddress': 'pr', 'price': 1, 'safe': True, 'tv': tv('COOLING', 80)},
            {'mint': 'B', 'symbol': 'BOND', 'pairAddress': 'pb', 'price': 1, 'safe': True, 'mcap': 10_000, 'tv': tv('BOND RUN')},
            {'mint': 'P', 'symbol': 'PRO', 'pairAddress': 'pp', 'price': 1, 'safe': True, 'mcap': 10_000, 'tv': tv('WATCH')}]
    monkeypatch.setattr(rs, '_open_board', lambda: rows)
    ex = rs._exhale_rows()
    assert [r['symbol'] for r in ex] == ['DRY', 'COOL']                  # DRYING UP (+1.9%) before COOLING (+0.6%); unsafe / rug 80 out
    assert ex[0]['baseAddress'] == 'D' and 'drying up' in ex[0]['divisionLabel']
    now_ms = time.time() * 1000
    monkeypatch.setitem(rs._pump_calls, 'callers', {'ace': {'proven': True, 'medMult': 2.0, 'wonPct': 80, 'n': 5}})
    monkeypatch.setitem(rs._pump_calls, 'calls', [{'user': 'ace', 'mint': 'P', 'at': now_ms - 20 * 60000, 'atMc': 9_500},
                                                   {'user': 'ace', 'mint': 'B', 'at': now_ms - 5 * 60000, 'atMc': 9_500}])
    pc = rs._procall_rows()
    assert [r['symbol'] for r in pc] == ['PRO']                          # a BOND RUN read (−84% record) is never listed
    assert '@ace called it 20m ago' in pc[0]['divisionLabel']


def test_narrative_leaders_list_and_its_gate(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs._mt, 'trending', lambda st, now: [{'term': 'botpfp', 'kind': 'wave', 'today': 40, 'coins': []}])
    rows = [{'mint': 'O', 'symbol': 'BOTPFP', 'pairAddress': 'po', 'price': 1, 'mcap': 9e5, 'ageH': 4, 'site': 's', 'safe': True, 'vol1h': 5e4,
             'tv': {'call': ['x', 'WATCH', 'warn'], 'rug': 20}}]
    monkeypatch.setattr(rs, '_open_board', lambda: rows)
    out = rs._wave_rows()
    assert [r['symbol'] for r in out] == ['BOTPFP'] and 'original of the "botpfp" wave' in out[0]['divisionLabel']
    monkeypatch.setattr(rs, '_list_records', lambda: {'wave': {'n': 4, 'medPct': 9}})
    assert not rs._wave_ready()                                         # too few settled: the engine does not seat it yet
    monkeypatch.setattr(rs, '_list_records', lambda: {'wave': {'n': 12, 'medPct': 2.5}})
    assert rs._wave_ready()
    rows[0]['tv'] = {'call': ['☠', 'RUG BAIT', 'bad'], 'rug': 80}
    assert rs._wave_rows() == []                                        # a rug-bait read is never listed

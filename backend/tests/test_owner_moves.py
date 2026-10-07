import owner_moves as om


def _card(events):
    return {'label': '🔥 Prime Blaze', 'events': events}


def test_owner_moves_are_read_from_the_cards_own_activity_once_each():
    ev = [{'at': 100.0, 'kind': 'rotate', 'symbol': 'OLD', 'why': '🎯 your pick — swapped in at the round', 'to': ['JIPPI']},
          {'at': 110.0, 'kind': 'seat', 'symbol': 'SND', 'why': '🎯 your pick $SND fills seat 4 of 4 with an equal share', 'to': ['SND']},
          {'at': 120.0, 'kind': 'rotate', 'symbol': 'BEAST', 'why': '⇄ swapped by hand', 'to': ['CRAWL']},
          {'at': 130.0, 'kind': 'skim', 'symbol': 'JIPPI', 'why': '💰 profit of $JIPPI taken ($0.17), its stake keeps riding'},
          {'at': 131.0, 'kind': 'skim', 'symbol': 'JIPPI', 'why': '💰 auto: +50% — profit of $JIPPI taken'},              # the engine's: not a move of yours
          {'at': 132.0, 'kind': 'skim', 'symbol': 'POD', 'why': '💚 full stack — $POD skimmed', 'stack': True},
          {'at': 140.0, 'kind': 'skim', 'symbol': 'POD', 'why': '🏠 initial of $POD taken out', 'house': True},
          {'at': 150.0, 'kind': 'ride', 'symbol': 'JIPPI', 'why': '+122% ≥ +50% — ❄ frozen (riding)'},
          {'at': 160.0, 'kind': 'rotate', 'symbol': 'X', 'why': '✅ your pick $X failed verification before the bell'},
          {'at': 170.0, 'kind': 'compound', 'why': 'idle cash back into the card'}]
    coin = lambda s: None if s == 'SND' else {'mint': f'MINT_{s}_xxxxxxxx', 'pair': 'P' + s, 'px': 2.0}
    log, added = om.collect({}, _card(ev), coin, 200.0)
    assert [(m['kind'], m['symbol']) for m in added] == [('pick', 'JIPPI'), ('swap', 'CRAWL'), ('skim', 'JIPPI'), ('house', 'POD'), ('lock', 'JIPPI')]   # $SND had no price: skipped
    assert log['seenAt'] == 170.0 and added[-1]['engine'] and not added[0]['engine']
    log2, again = om.collect(log, _card(ev), coin, 300.0)
    assert again == [] and len(log2['rows']) == 5


def test_a_move_is_judged_half_an_hour_later_and_good_ones_become_chat_lines():
    rows = [{'id': 'pick:a:1', 'at': 0.0, 'kind': 'pick', 'symbol': 'UP', 'mint': 'A', 'px0': 1.0, 'card': '🔥 Prime Blaze'},
            {'id': 'skim:b:1', 'at': 0.0, 'kind': 'skim', 'symbol': 'DROP', 'mint': 'B', 'px0': 1.0, 'card': '🔥 Prime Blaze'},
            {'id': 'pick:c:1', 'at': 0.0, 'kind': 'pick', 'symbol': 'RUG', 'mint': 'C', 'px0': 1.0},
            {'id': 'cut:d:1', 'at': 0.0, 'kind': 'cut', 'symbol': 'RAN', 'mint': 'D', 'px0': 1.0},
            {'id': 'pick:e:1', 'at': 1500.0, 'kind': 'pick', 'symbol': 'NEW', 'mint': 'E', 'px0': 1.0}]
    px = {'A': 1.34, 'B': 0.8, 'D': 1.5, 'E': 9.0}
    early, none = om.settle({'rows': rows}, px.get, 1000.0)
    assert none == []                                                               # too soon
    log, done = om.settle({'rows': rows}, px.get, 1900.0)
    res = {r['symbol']: (r['pct'], r['result']) for r in done}
    assert res == {'UP': (34.0, 'good'), 'DROP': (-20.0, 'good'), 'RAN': (50.0, 'bad')}   # sold before a −20% = good exit; cut before a +50% = left early
    assert all(r.get('pct') is None for r in log['rows'] if r['symbol'] in ('RUG', 'NEW'))   # no price yet: waits; $NEW is too young
    log, gone = om.settle(log, px.get, 7300.0)
    assert {r['symbol']: r['pct'] for r in gone}['RUG'] == -100.0                    # no price after 2h = gone
    s = om.summary(log)
    assert s['pick']['n'] == 3 and s['pick']['good'] == 2 and s['pick']['bad'] == 1 and s['skim']['good'] == 1 and s['cut']['bad'] == 1
    lines = dict(om.calls([{'id': 'lock:x:1', 'kind': 'lock', 'symbol': 'JIPPI', 'card': '🔥 Prime Blaze'}], done))
    assert 'just locked on 🔥 Prime Blaze' in lines['lock:lock:x:1']
    assert '✅ Good call: 🎯 pick $UP onto 🔥 Prime Blaze 32m ago — +34% since.' == lines['move:pick:a:1']
    assert 'Good exit' in lines['move:skim:b:1'] and '-20% since' in lines['move:skim:b:1'] and 'move:cut:d:1' not in lines
    assert om.verdict('pick', 3) == 'flat' and om.verdict('house', -40) == 'good'

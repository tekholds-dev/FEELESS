import trench_brain as tb


def row(m, px=1.0, **k):
    return {'mint': m, 'symbol': m.upper(), 'price': px, 'ageH': 0.5, 'mcap': 50e3, 'buyShare': 60, 'top10': 20, 'safe': True, **k}


def test_first_touch_settles_hit_cut_end_and_gone_after_watching_the_whole_hour():
    st = tb.track({}, [row('a'), row('b'), row('c'), row('d'), row('e')], lambda m: None, 0)
    assert set(st['open']) == {'a', 'b', 'c', 'd', 'e'}
    st = tb.track(st, [], lambda m: {'a': 1.6, 'b': 0.65, 'c': 1.1, 'e': 0.6}.get(m), 120)   # a +60 · b −35 · c drifts · d no price · e −40
    assert not st['done'] and st['open']['b']['x'] == {'-20': 120, '-30': 120}           # still watched after the cut
    st = tb.track(st, [], lambda m: {'a': 1.6, 'b': 0.65, 'c': 1.1, 'e': 1.7}.get(m), 1800)   # e shakes out, then runs +70
    st = tb.track(st, [], lambda m: {'a': 1.6, 'b': 0.65, 'c': 1.1, 'e': 1.7}.get(m), 3700)
    how = {d['mint']: (d['how'], d['play']) for d in st['done']}
    assert how == {'a': ('hit', 50.0), 'b': ('cut', -30.0), 'c': ('end', 10.0), 'd': ('gone', -100.0), 'e': ('cut', -30.0)}
    st2 = tb.track(st, [row('a')], lambda m: None, 3800)          # not noted again inside 6h
    assert 'a' not in st2['open']
    s = tb.stops(st['done'])['by']                                # the same five paths replayed with every ticket stop
    assert s[30]['shook'] == 1 and s[50]['hit'] > s[30]['hit']   # −30 shook e out before its +50; −50 kept it
    assert tb.play(st['done'][-1] if st['done'][-1]['mint'] == 'e' else [d for d in st['done'] if d['mint'] == 'e'][0], 50, 0) == 50.0


def test_the_brain_names_the_stop_that_paid_once_it_has_enough_paths():
    d = lambda i, x, end=0.0: {'mint': str(i), 'at': i, 'x': x, 'end': end, 'gone': False, 'f': []}
    done = [d(i, {'-20': 1, '-30': 2, '50': 3}) for i in range(20)] + [d(100 + i, {'-20': 1, '-30': 2, '-50': 3}, -60) for i in range(15)]
    st = tb.stops(done)
    assert st['by'][30]['avg'] == -30.0 and st['by'][50]['avg'] > 0 and st['best'] in (50, 70, 0)   # shake-outs cost the tight stop everything
    assert tb.stops(done[:10])['best'] is None                  # too few paths → no stop is named


def test_learns_pairs_and_ranks_unseen_coins_walk_forward():
    done = []
    for i in range(120):                                         # top-10 under 15 + site & X hit · everything else gets cut
        good = i % 3 == 0
        f = tb.feats(row('m%d' % i, top10=10 if good else 40, site='s' if good else None, x='x' if good else None))
        done.append({'mint': 'm%d' % i, 'at': i, 'play': 50.0 if good else -30.0, 'how': 'hit' if good else 'cut', 'f': f})
    tbl = tb.table(done)
    assert tbl['soc:site+x & top10:<15']['med'] == 50.0 and tbl['*']['n'] == 120
    good = tb.score(row('n', top10=10, site='s', x='x'), tbl)
    bad = tb.score(row('o', top10=40), tbl)
    assert good['est'] > 0 > bad['est'] and good['hit'] > bad['hit'] and good['why']
    p = tb.proof(done)
    assert p['proven'] and p['top'] == 50.0 and p['bottom'] == -30.0 and p['n'] == 48


def test_not_trusted_on_noise_or_thin_samples():
    import random
    rnd = random.Random(1)
    done = [{'mint': str(i), 'at': i, 'play': rnd.choice([50.0, -30.0, -30.0]), 'how': 'x', 'f': tb.feats(row(str(i), top10=rnd.choice([10, 40])))} for i in range(150)]
    assert not tb.proof(done)['proven']                         # features carry no signal → never trusted
    assert not tb.proof(done[:20])['proven']                    # too few test coins
    assert tb.score(row('z'), {}) is None


def test_summary_and_missing_readings_never_guessed():
    assert tb.feats({'mint': 'a'}) == []
    s = tb.summary(tb.track({}, [row('a')], lambda m: None, 0))
    assert s['open'] == 1 and s['n'] == 0 and not s['proof']['proven'] and s['tp'] == 50

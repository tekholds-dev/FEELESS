import trench_brain as tb


def row(m, px=1.0, **k):
    return {'mint': m, 'symbol': m.upper(), 'price': px, 'ageH': 0.5, 'mcap': 50e3, 'buyShare': 60, 'top10': 20, 'safe': True, **k}


def test_first_touch_settles_hit_cut_end_and_gone():
    st = tb.track({}, [row('a'), row('b'), row('c'), row('d')], lambda m: None, 0)
    assert set(st['open']) == {'a', 'b', 'c', 'd'}
    px = {'a': 1.6, 'b': 0.65, 'c': 1.1}                        # a hits +50 first, b cuts −30 first, c drifts, d vanishes
    st = tb.track(st, [], lambda m: px.get(m), 120)
    how = {d['mint']: (d['how'], d['play']) for d in st['done']}
    assert how == {'a': ('hit', 50.0), 'b': ('cut', -30.0)}
    st = tb.track(st, [], lambda m: px.get(m), 3700)
    how = {d['mint']: (d['how'], d['play']) for d in st['done']}
    assert how['c'] == ('end', 10.0) and how['d'] == ('gone', -100.0)
    st = tb.track(st, [row('a')], lambda m: None, 3800)          # not noted again inside 6h
    assert 'a' not in st['open']


def test_a_coin_that_dipped_then_ran_counts_as_cut_first():
    st = tb.track({}, [row('a')], lambda m: None, 0)
    st = tb.track(st, [], lambda m: 0.6, 60)                     # −40% first
    assert st['done'][0]['how'] == 'cut'


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

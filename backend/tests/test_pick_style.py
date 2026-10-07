import pick_style as ps


def _pick(i, **kw):
    base = {'ageH': 2 + i % 5, 'liq': 60_000 + 5_000 * (i % 6), 'mcap': 400_000 + 50_000 * (i % 4), 'vol1h': 80_000, 'chg1h': 30 + i % 20, 'chg5m': 2, 'buyShare': 62}
    return {**base, **kw}


def _log(n=20):
    log = []
    for i in range(n):
        log = ps.note(log, f'M{i}', f'S{i}', ps.snap(_pick(i)), 1000.0 * i)
    return log


def test_no_style_until_eight_picks_and_the_same_coin_in_ten_minutes_is_one_pick():
    assert ps.profile(_log(7)) is None and ps.profile(_log(8))['n'] == 8
    log = ps.note(_log(3), 'M2', 'S2', ps.snap(_pick(2)), 2000.0 + 300)      # 5 min after its own pick
    assert len(log) == 3
    assert ps.snap({'ageH': 0, 'liq': None}) is None                          # nothing readable = no note
    assert ps.note([], 'X', 'X', None, 1.0) == []


def test_a_coin_like_the_owners_picks_scores_high_and_a_different_kind_scores_low():
    prof = ps.profile(_log())
    like = ps.match(_pick(3), prof); old_major = ps.match({'ageH': 9000, 'liq': 9_000_000, 'mcap': 900_000_000, 'vol1h': 5_000_000, 'chg1h': 0.2, 'chg5m': 0, 'buyShare': 50}, prof)
    assert like >= 80 and old_major <= 15
    assert ps.match({'ageH': 3}, prof) is None and ps.match(_pick(1), None) is None   # too little to tell / no style yet


def test_rank_puts_matches_first_and_keeps_the_rest_in_order_and_words_read_plainly():
    prof = ps.profile(_log())
    a, b, c = {'mint': 'a', 'ageH': 9000, 'liq': 9e6, 'mcap': 9e8, 'vol1h': 5e6, 'chg1h': 0, 'buyShare': 50}, {'mint': 'b', **_pick(2)}, {'mint': 'c'}
    out = ps.rank([a, b, c], prof)
    assert [x['mint'] for x in out] == ['b', 'a', 'c'] and out[0]['styleMatch'] >= 80 and 'styleMatch' not in out[2]
    assert ps.rank([a, b], None) == [a, b]
    w = ps.words(prof)
    assert any(x.startswith('age 2h–6h') for x in w) and any('buyers 62%–62%' in x for x in w) and ps.words(None) == []

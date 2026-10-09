import meme_terms as mt


def test_the_wave_original_is_picked_never_a_copycat():
    trend = [{'term': 'botpfp', 'kind': 'wave', 'today': 62, 'coins': ['C2']},
             {'term': 'tiny', 'kind': 'wave', 'today': 3},
             {'term': 'gm', 'kind': 'chat', 'today': 99}]
    rows = [{'mint': 'O', 'symbol': 'BOTPFP', 'mcap': 900_000, 'ageH': 5, 'site': 'https://x.io', 'safe': True, 'vol1h': 80_000},
            {'mint': 'C1', 'symbol': 'BOTPFP2', 'mcap': 20_000, 'ageH': 1, 'site': 'https://y.io', 'safe': True, 'vol1h': 9_000},
            {'mint': 'C2', 'symbol': 'BABYBOT', 'mcap': 40_000, 'ageH': 2, 'x': 'https://x.com/b', 'safe': True, 'vol1h': 9_000},
            {'mint': 'T', 'symbol': 'TINY', 'mcap': 1e6, 'site': 's', 'safe': True, 'vol1h': 1e5}]
    out = mt.wave_leaders(trend, rows)
    assert [r['mint'] for r in out] == ['O'] and out[0]['wave'] == {'term': 'botpfp', 'copycats': 1, 'today': 62}
    rows[0]['site'] = None
    assert mt.wave_leaders(trend, rows) == []                       # the leader has no site / X → no pick (a copycat never stands in)
    rows[0].update(site='s', safe=False)
    assert mt.wave_leaders(trend, rows) == []                       # failed the safety scan

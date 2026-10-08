import coin_clean as cc


def test_clean_coin_scores_ten():
    row = {'buyShare': 62, 'liquidityUsd': 80_000, 'vol1h': 55_000, 'change1h': 12}
    intel = {'top10Pct': 14, 'devHoldingPct': 1, 'insidersHoldingPct': 2, 'bundledWallets': [], 'snipersHoldingPct': 0.5,
             'flaggedFunders': [], 'flaggedHoldings': [], 'creator': 'C'}
    s = cc.score(row, intel, 'clean')
    assert s['score'] == 10 and s['tier'] == 'clean' and not s['fails'] and not s['unknown']


def test_giftr_like_rug_is_risky_and_unknown_is_never_a_point():
    # $giftr (2026-10-08): a thin curve pool, creator still a top holder, buyers ~75% (a pump), $15K an hour
    row = {'buyShare': 75, 'liquidityUsd': 7_980, 'vol1h': 15_000, 'change1h': 60}
    intel = {'top10Pct': 18.2, 'devHoldingPct': 4.4, 'creator': 'C'}
    s = cc.score(row, intel, 'watch')
    assert 'pool $25K+' in s['fails'] and '$20K+ traded this hour, not dumping' in s['fails']
    assert 'snipers + bundlers hold under 5%' in s['unknown'] and s['score'] <= 6
    assert cc.score({}, {})['score'] == 0

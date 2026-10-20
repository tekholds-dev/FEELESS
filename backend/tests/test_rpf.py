import rpf

NOW = 1_000_000.0


def _real():
    return {'website': {'url': 'https://x.io', 'reachable': True, 'mintMatch': 'yes', 'docs': ['https://docs.x.io'], 'domain': {'ageDays': 120}},
            'x': {'url': 'https://x.com/p', 'available': True, 'followers': 8000, 'joined': NOW - 200 * 86400, 'mintMentioned': True, 'lastPostAt': NOW - 3600},
            'legal': {'level': 'PARTIAL'}, 'narrative': {'class': 'UTILITY / PROJECT'}, 'cross': {}}


def test_a_project_with_history_scores_real_with_cited_parts():
    s = rpf.score(_real(), {'liq': 50000, 'vital': {'organicPct': 30}}, NOW)
    assert s['grade'] == 'REAL' and s['score'] >= 80 and s['out'] is None
    assert any('THIS contract' in w for w, _ in s['parts']) and any('domain 120 days' in w for w, _ in s['parts'])


def test_a_bare_meme_is_a_meme_and_unknowns_are_named_not_scored():
    s = rpf.score({'narrative': {'class': 'MEME'}}, {}, NOW)
    assert s['grade'] == 'MEME' and s['score'] == 0 and 'no website' in s['unknown'] and 'no X' in s['unknown']


def test_another_coins_contract_or_a_copycat_is_out():
    p = _real(); p['website']['mintMatch'] = 'no'
    assert rpf.score(p, {}, NOW)['grade'] == 'OUT'
    p = _real(); p['cross'] = {'copycat': True}
    assert rpf.score(p, {}, NOW)['grade'] == 'OUT'


def test_board_keeps_real_and_maybe_only_best_first():
    b = rpf.board({'A': _real(), 'B': {'narrative': {'class': 'MEME'}}}, {'A': {'symbol': 'AAA', 'pair': 'P'}}, NOW)
    assert [x['mint'] for x in b] == ['A'] and b[0]['symbol'] == 'AAA'


def test_track_grades_once_at_1h_and_24h_and_a_vanished_coin_is_minus_100():
    st = rpf.track({}, [{'mint': 'A', 'grade': 'REAL', 'score': 80}, {'mint': 'B', 'grade': 'MAYBE', 'score': 35}], lambda m: 1.0, NOW)
    st = rpf.track(st, [{'mint': 'A', 'grade': 'REAL', 'score': 80}], lambda m: 1.5, NOW + 3700)   # not noted twice
    assert st['open']['A']['pct1h'] == 50.0 and len(st['open']) == 2
    st = rpf.track(st, [], lambda m: 2.0 if m == 'A' else 0, NOW + 86400 + 2000)
    pr = rpf.proof(st)
    assert pr['REAL']['n'] == 1 and pr['REAL']['med24h'] == 100.0 and pr['MAYBE']['med24h'] == -100.0 and not pr['REAL']['proven']


def test_a_big_platform_domain_earns_no_age_points():
    p = _real(); p['website']['domain'] = {'ageDays': 7000}
    s = rpf.score(p, {}, NOW)
    assert not any('days old' in w and 'domain' in w for w, _ in s['parts']) and any('big platform' in u for u in s['unknown'])

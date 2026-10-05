import feecat_brain as fb

NOW = 10 * 86400


def ex(n, pct, pnl, age=3600):
    return [{'pnlSol': pnl, 'changeAtExit': pct, 'exitAt': NOW - age - i} for i in range(n)]


def test_cold_at_once_on_a_losing_window():
    s = fb.strength(ex(6, -8, -0.01), NOW)
    assert s['level'] == 'cold' and s['mult'] == 0.6


def test_hot_needs_both_windows_and_two_checks_in_a_row():
    good = ex(6, 12, 0.02) + ex(6, 9, 0.01, age=2 * 86400)        # 6 in 24h, 12 in 72h, all winning
    first = fb.strength(good, NOW)
    assert first['level'] == 'steady' and first['pending'] == 'hot'
    second = fb.strength(good, NOW, prev=first)
    assert second['level'] == 'hot' and second['mult'] == 1.15
    only24 = ex(6, 12, 0.02)                                          # 72h has too few trades → never hot
    assert fb.strength(only24, NOW, prev={'level': 'steady', 'pending': 'hot'})['level'] == 'steady'


def test_never_presses_while_discipline_cuts_and_steady_with_no_data():
    good = ex(6, 12, 0.02) + ex(6, 9, 0.01, age=2 * 86400)
    s = fb.strength(good, NOW, prev={'level': 'hot'}, disc={'sizeMult': 0.5})
    assert s['level'] == 'steady'
    assert fb.strength([], NOW)['level'] == 'steady'

import raceway as rw


def test_daily_track_is_the_same_for_everyone_and_on_the_streets():
    a, b = rw.daily_track('2026-10-27'), rw.daily_track('2026-10-27')
    assert a == b and a['cps'] != rw.daily_track('2026-10-28')['cps']
    assert len(a['cps']) == rw.RACE_CPS
    for x, z in a['cps']:                                                        # every checkpoint is a road crossing
        assert x % rw.RACE_CELL == 0 and z % rw.RACE_CELL == 0 and 0 <= x <= rw.RACE_GRID * rw.RACE_CELL
    assert 0 < a['min'] < a['par']


def test_an_honest_run_passes_and_cheats_do_not():
    t = rw.daily_track('2026-10-27'); par = t['par']
    splits = [int(par * (k + 1) / len(t['cps'])) for k in range(len(t['cps']))]
    assert rw.check(t, par, splits, elapsed=par / 1000) is None
    assert 'straight line' in rw.check(t, t['min'] - 1, [int((t['min'] - 1) * (k + 1) / 6) for k in range(6)], elapsed=999)
    assert 'clock' in rw.check(t, par, splits, elapsed=1.0)                      # reported 30 s, the server saw 1 s
    assert 'order' in rw.check(t, par, list(reversed(splits)), elapsed=par / 1000)
    assert 'Every checkpoint' in rw.check(t, par, splits[:-1], elapsed=par / 1000)


def test_mp_pays_once_a_day_and_the_board_keeps_each_best():
    t = rw.daily_track('2026-10-27')
    mp, paid = rw.race_mp(t['par'] - 1, t, [])
    assert mp == rw.RACE_MP + rw.RACE_PAR_MP and paid == ['finish', 'par']
    assert rw.race_mp(t['par'] - 1, t, paid)[0] == 0                             # the second run today pays nothing more
    rows = {}
    assert rw.record(rows, 'WALLETAAAAAAAAAAAAAAA1', 50000, 'bike', 'Sicario', 'FRT')
    assert not rw.record(rows, 'WALLETAAAAAAAAAAAAAAA1', 60000, 'car', 'Sicario', 'FRT')   # slower doesn't replace a best
    rw.record(rows, 'tg:42', 40000, 'car', 'tg racer', '')
    assert [r['ms'] for r in rw.board(rows)] == [40000, 50000] and rw.board(rows)[0]['place'] == 1


def test_errand_delivery_starts_at_home_and_changes_every_ten_minutes():
    a = rw.errand_track('pizza', 'fam-1', 1000.0)
    assert a['kind'] == 'errand' and len(a['cps']) == 2 and a['store'] == 'pizza'
    assert a == rw.errand_track('pizza', 'fam-1', 1150.0) and a['cps'] != rw.errand_track('pizza', 'fam-1', 1300.0)['cps']

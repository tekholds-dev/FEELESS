import pytest
import rep_markets as rm

NOW = 1_800_000_000.0


def mk(st, kind='up', px=1.0):
    m = rm.make(kind, 'M1', 'AAA', px, NOW)
    st.setdefault('markets', []).append(m)
    return m


def test_winners_are_paid_from_the_losing_side_by_their_stake():
    st = {}
    m = mk(st)
    rm.stake(st, 'w1', m['id'], 'yes', 100, NOW, rep=90)
    rm.stake(st, 'w2', m['id'], 'yes', 300, NOW, rep=10)
    rm.stake(st, 'w3', m['id'], 'no', 200, NOW, rep=50)
    rm.mark(m, 1.2, NOW + 1800)
    assert rm.settle(st, NOW + 1800) == []                     # an UP market waits for its close
    done = rm.settle(st, NOW + 3600)
    assert done and m['result'] == 'yes'
    assert st['banks']['w1']['chips'] == rm.CHIPS_WEEK - 100 + 100 + 50
    assert st['banks']['w2']['chips'] == rm.CHIPS_WEEK - 300 + 300 + 150
    assert st['banks']['w3']['chips'] == rm.CHIPS_WEEK - 200 and st['banks']['w3']['lost'] == 200
    assert rm.season_pts(st['banks']['w2']) == 15


def test_rep_weighted_odds_show_when_trusted_wallets_disagree_with_the_crowd():
    st = {}
    m = mk(st)
    rm.stake(st, 'whale', m['id'], 'yes', 500, NOW, rep=5)       # big chips, no record
    rm.stake(st, 'pro', m['id'], 'no', 100, NOW, rep=95)          # small chips, a record
    o = rm.odds(m)
    assert o['crowd'] > 75 and o['rep'] < 50 and o['split'] is True


def test_double_and_rug_settle_the_moment_they_happen_and_a_vanished_coin_is_a_rug():
    st = {}
    d = mk(st, 'double'); r = mk(st, 'rug'); r2 = mk(st, 'rug')
    for m in (d, r):
        rm.stake(st, 'w1', m['id'], 'yes', 50, NOW); rm.stake(st, 'w2', m['id'], 'no', 50, NOW)
    rm.mark(d, 2.1, NOW + 600); rm.mark(r, 0.15, NOW + 600); rm.mark(r2, 1.0, NOW + 60)
    rm.settle(st, NOW + 600)
    assert d['result'] == 'yes' and r['result'] == 'yes' and r2['state'] == 'open'
    rm.settle(st, NOW + 60 + rm.GONE_SEC)
    assert r2['result'] == 'yes'


def test_the_rules_hold():
    st = {}
    m = mk(st)
    with pytest.raises(ValueError):
        rm.stake(st, 'w1', m['id'], 'yes', 5, NOW)                # under the minimum
    rm.stake(st, 'w1', m['id'], 'yes', 100, NOW)
    with pytest.raises(ValueError):
        rm.stake(st, 'w1', m['id'], 'no', 100, NOW)               # both sides
    with pytest.raises(ValueError):
        rm.stake(st, 'w2', m['id'], 'yes', 100, m['closesAt'] - 30)   # locked before the close
    st['banks']['w1']['chips'] = 20
    with pytest.raises(ValueError):
        rm.stake(st, 'w1', m['id'], 'yes', 100, NOW)              # not enough chips


def test_a_one_sided_market_refunds_and_a_new_week_resets_the_bank():
    st = {}
    m = mk(st)
    rm.stake(st, 'w1', m['id'], 'yes', 100, NOW)
    rm.mark(m, 2.0, NOW + 100)
    rm.settle(st, NOW + 3600)
    assert st['banks']['w1']['chips'] == rm.CHIPS_WEEK
    st['banks']['w1']['chips'] = 3
    assert rm.bank(st, 'w1', NOW + 8 * 86400)['chips'] == rm.CHIPS_WEEK


def test_new_markets_come_from_the_live_lists():
    st = {}
    rows = [{'mint': 'A', 'symbol': 'A'}, {'mint': 'B', 'symbol': 'B', 'ageH': 2}, {'mint': 'C', 'symbol': 'C', 'rug': 70}]
    out = rm.new_markets(st, rows, {'A': 1, 'B': 1, 'C': 1}, NOW)
    kinds = sorted(m['kind'] for m in out)
    assert kinds == ['double', 'rug', 'up', 'up']
    assert rm.new_markets(st, rows, {'A': 1, 'B': 1, 'C': 1}, NOW + 60) == []   # one coin once per open market


def test_service_uses_its_own_alias():
    src = open(__import__('pathlib').Path(__file__).resolve().parent.parent / 'reputation_service.py').read()
    assert 'import rep_markets as _repm' in src and 'import rep_markets as _rm' not in src


def test_each_kind_prefers_a_coin_not_already_in_a_market():
    st = {}
    rows = [{'mint': 'A', 'symbol': 'A', 'ageH': 1, 'rug': 60}, {'mint': 'B', 'symbol': 'B'}, {'mint': 'C', 'symbol': 'C', 'ageH': 2, 'rug': 70}]
    out = rm.new_markets(st, rows, {'A': 1, 'B': 1, 'C': 1}, NOW)
    by = {m['kind']: m['mint'] for m in out if m['kind'] != 'up'}
    assert by == {'double': 'C', 'rug': 'C'} or len({m['mint'] for m in out}) >= 3

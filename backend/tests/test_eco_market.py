"""PoEco rebuilt (owner 2026-11-13): a sealed market call on live pools, graded by pure math. No network in here — fake pairs only."""
import pytest

import eco_market as m

PAIR = lambda addr, sym, liq, vol, price=1.0, chg=0.0: {   # noqa: E731
    'pairAddress': addr, 'baseToken': {'symbol': sym}, 'quoteToken': {'symbol': 'SOL'},
    'priceUsd': str(price), 'liquidity': {'usd': liq}, 'volume': {'h24': vol}, 'priceChange': {'h24': chg}}


def test_rows_drop_broken_pairs_and_sort_deepest_first():
    rows = m.rows_of([PAIR('a', 'AAA', 1000, 500), PAIR('b', 'BBB', 9000, 100), {'junk': 1}, PAIR('c', 'CCC', 0, 50), PAIR('d', 'DDD', 10, 0)])
    assert [r['addr'] for r in rows] == ['b', 'a'] and rows[0]['pair'] == 'BBB/SOL'


def test_the_call_is_measurable_sealed_and_deterministic():
    rows = m.rows_of([PAIR('a', 'AAA', 10000, 9000), PAIR('b', 'BBB', 20000, 4000)])
    f1 = m.make_call(rows, 1, now=1000)
    f2 = m.make_call(rows, 1, now=1000)
    assert f1['kind'] == 'market' and f1['due'] == 1000 + m.DAY and f1['status'] == 'open'
    assert f1['baseline']['pick']['addr'] == 'a'   # a turns its liquidity 0.9x vs b 0.2x
    assert 'AAA/SOL posts more 24h volume than BBB/SOL' in f1['q']
    assert f1['hash'] == f2['hash'] and len(f1['hash']) == 32   # same read, same seal
    with pytest.raises(ValueError):
        m.make_call(rows[:1], 2)   # one pool is no market


def test_reality_grades_it_not_a_hand():
    rows = m.rows_of([PAIR('a', 'AAA', 10000, 9000), PAIR('b', 'BBB', 20000, 4000)])
    f = m.make_call(rows, 1, now=1000)
    with pytest.raises(ValueError):
        m.grade(f, rows, now=1000 + 10)   # not due yet
    fresh = m.rows_of([PAIR('a', 'AAA', 10000, 7000), PAIR('b', 'BBB', 20000, 6000)])
    m.grade(f, fresh, now=1000 + m.DAY + 1)
    assert f['graded'] == 'right' and f['status'] == 'closed' and f['after']['marginUsd'] == 1000.0
    r = m.receipt(f)
    assert r['proof'] == 'PoEco' and r['hash'] == f['hash'] and r['baseline'] and r['after']


def test_a_dead_pool_is_a_wrong_call_and_a_graded_folder_stays():
    rows = m.rows_of([PAIR('a', 'AAA', 10000, 9000), PAIR('b', 'BBB', 20000, 4000)])
    f = m.make_call(rows, 1, now=1000)
    m.grade(f, m.rows_of([PAIR('b', 'BBB', 20000, 6000)]), now=1000 + m.DAY + 1)
    assert f['graded'] == 'wrong' and 'dark' in f['after']['note']
    before = dict(f)
    m.grade(f, [], now=1000 + m.DAY + 99)   # grading twice changes nothing
    assert f == before

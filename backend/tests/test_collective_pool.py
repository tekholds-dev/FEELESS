"""🪙 The Pool ledger: the owner's worked example, and the rule that it can never owe more than is really there."""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collective_pool as cp

D = 86400
SOL = 100.0
USDC = cp.UNITS['USDC']


def held(s, t):
    """Everything inside the ledger for one token."""
    return s['books'][t]['keep'] + cp.backed(s, t)


def run(s, start, days, step=3600):
    t = start
    for _ in range(int(days * D / step)):
        t += step
        cp.tick(s, t, SOL)
    return t


def test_owners_ten_dollar_example_splits_exactly():
    s = cp.new_state(); s['at'] = 1; s['cfg']['potPct'] = 0
    r = cp.send(s, 'sig1', 'a', 'o', 'USDC', 10 * USDC, 10, 1)
    assert r == {'keptUnits': 2 * USDC, 'lockedUnits': 8 * USDC}
    run(s, 1, 1000, 86400)
    a = s['agents']['a']
    assert a['locked']['USDC'] < 1000
    assert abs(a['owed']['USDC'] - 6 * USDC) < 0.01 * USDC   # $6 back, $4 to the Collective
    assert held(s, 'USDC') == 10 * USDC


def test_half_releases_in_thirty_days_and_full_boost_in_fifteen():
    for boost, days in ((0, 30), (1, 15)):
        s = cp.new_state(); s['at'] = 1; s['cfg']['potPct'] = 0
        cp.send(s, 'k', 'a', 'o', 'USDC', 100 * USDC, 100, 1, boost)
        run(s, 1, days)
        assert abs(s['agents']['a']['locked']['USDC'] / (80 * USDC) - 0.5) < 0.01


def test_boost_moves_the_split_to_78():
    assert cp.levers(cp.clean_cfg(None), 0) == {'splitPct': 75.0, 'halfLifeDays': 30.0, 'weightX': 1.0}
    assert cp.levers(cp.clean_cfg(None), 1) == {'splitPct': 78.0, 'halfLifeDays': 15.0, 'weightX': 2.0}


def test_rank_only_turns_every_lever_off():
    cfg = {**cp.clean_cfg(None), 'boostMode': 'rank'}
    assert cp.levers(cfg, 1) == {'splitPct': 75.0, 'halfLifeDays': 30.0, 'weightX': 1.0}


def test_one_key_moves_money_once():
    s = cp.new_state()
    assert cp.income(s, 'dep1', 'USDC', 5 * USDC, 'deposit') is True
    assert cp.income(s, 'dep1', 'USDC', 5 * USDC, 'deposit') is False
    assert cp.send(s, 'sig', 'a', 'o', 'SOL', 10**9, 100, 1)
    assert cp.send(s, 'sig', 'a', 'o', 'SOL', 10**9, 100, 1) is None
    assert s['books']['USDC']['keep'] + s['books']['USDC']['pot'] == 5 * USDC
    assert s['agents']['a']['sent']['SOL'] == 10**9


def test_fee_share_compounds_into_locked_and_is_paid_from_real_money_only():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'sig', 'a', 'o', 'USDC', 100 * USDC, 100, 1)
    cp.income(s, 'fee', 'USDC', 100 * USDC, 'txn')
    pot0 = s['books']['USDC']['pot']
    run(s, 1, 1)
    a = s['agents']['a']
    assert a['earned']['USDC'] > 0
    assert a['earned']['USDC'] <= pot0
    assert held(s, 'USDC') == 200 * USDC


def test_nobody_locked_means_the_pot_just_waits():
    s = cp.new_state(); s['at'] = 1
    cp.income(s, 'fee', 'USDC', 100 * USDC, 'txn')
    pot0 = s['books']['USDC']['pot']
    run(s, 1, 10)
    assert s['books']['USDC']['pot'] == pot0


def test_earn_room_stops_a_small_sender_draining_a_rich_pot():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'sig', 'a', 'o', 'USDC', 10 * USDC, 10, 1)
    cp.income(s, 'fee', 'USDC', 100000 * USDC, 'txn')
    run(s, 1, 90)
    assert s['agents']['a']['earned']['USDC'] <= 10 * USDC + 1


def test_owner_cap_holds_once_there_are_enough_owners():
    s = cp.new_state(); s['at'] = 1
    for i in range(200):
        cp.send(s, f'k{i}', f'a{i}', f'o{i}', 'USDC', 10 * USDC, 10, 1)
    cp.send(s, 'whale', 'w', 'whale', 'USDC', 100000 * USDC, 100000, 1)
    part = cp.shares(s, SOL)
    assert abs(sum(part.values()) - 1) < 1e-6
    assert part['w'] <= 0.031


def test_two_agents_of_one_owner_count_as_one():
    s = cp.new_state(); s['at'] = 1
    for i in range(200):
        cp.send(s, f'k{i}', f'a{i}', f'o{i}', 'USDC', 10 * USDC, 10, 1)
    cp.send(s, 'w1', 'x1', 'whale', 'USDC', 50000 * USDC, 50000, 1)
    cp.send(s, 'w2', 'x2', 'whale', 'USDC', 50000 * USDC, 50000, 1)
    part = cp.shares(s, SOL)
    assert part['x1'] + part['x2'] <= 0.031


def test_a_boost_fades_and_the_print_grades_it():
    now = 100 * D
    assert cp.boost_of([{'pts': 100, 'at': now}], 100, now) == 1.0
    assert cp.boost_of([{'pts': 100, 'at': now}], 0, now) == 0.5
    assert abs(cp.boost_of([{'pts': 100, 'at': now - 60 * D}], 100, now) - 0.5) < 0.001
    assert cp.boost_of([{'pts': 9000, 'at': now}], 100, now) == 1.0


def test_config_is_bounded_and_keeps_its_order():
    c = cp.clean_cfg({'skimPct': 900, 'splitPct': 80, 'splitMaxPct': 60, 'halfLifeDays': 10, 'halfLifeMinDays': 40, 'boostMode': 'x', 'potPct': 'nope'})
    assert c['skimPct'] == 50 and c['splitMaxPct'] == 80 and c['halfLifeMinDays'] == 10 and c['boostMode'] == 'payout' and c['potPct'] == 50


def test_trade_fee_slides_from_5_to_1_percent():
    c = cp.clean_cfg(None)
    assert cp.txn_fee_usd(c, 5) == (0.25, 5.0)
    assert cp.txn_fee_usd(c, 50) == (1.5, 3.0)
    assert cp.txn_fee_usd(c, 500) == (5.0, 1.0)


def test_chain_shortfall_is_caught():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'k', 'a', 'o', 'USDC', 100 * USDC, 100, 1)
    assert cp.check_chain(s, {'USDC': 100 * USDC, 'SOL': 0}, 2)['short'] == []
    assert cp.check_chain(s, {'USDC': 10 * USDC, 'SOL': 0}, 2)['short'] == ['USDC']


def test_a_view_counts_up_between_ticks():
    s = cp.new_state(); s['at'] = 1000
    cp.send(s, 'k', 'a', 'o', 'USDC', 10 * USDC, 10, 1000)
    a, b = cp.view(s, 'a', 1000, SOL), cp.view(s, 'a', 1030, SOL)
    assert 0.0000015 < a['ratePerSecUsd'] < 0.0000017
    assert b['owedUsd'] > a['owedUsd']
    assert cp.view(s, 'nobody', 1000, SOL)['empty'] is True


def test_fuzz_money_in_always_equals_money_held_and_nothing_goes_negative():
    """Thousands of random fees, sends, hours and price swings. Not one unit may appear or vanish."""
    rng = random.Random(7)
    s = cp.new_state(); s['at'] = 1; t = 1; put = {'SOL': 0, 'USDC': 0}
    for i in range(6000):
        roll = rng.random(); tok = rng.choice(cp.TOKENS)
        if roll < 0.3:
            u = rng.randint(1, 5 * cp.UNITS[tok])
            if cp.income(s, f'f{i}', tok, u, rng.choice(('deposit', 'topup', 'txn', 'task', 'gift'))):
                put[tok] += u
        elif roll < 0.5:
            u = rng.randint(1, 3 * cp.UNITS[tok]); ag = rng.randint(0, 40)
            if cp.send(s, f's{i}', f'a{ag}', f'o{ag % 25}', tok, u, u / cp.UNITS[tok] * 100, t, rng.random()):
                put[tok] += u
        else:
            t += rng.randint(60, 7200); cp.tick(s, t, rng.uniform(1, 500))
        if i % 97 == 0:
            s['cfg'] = cp.clean_cfg({**s['cfg'], 'potPct': rng.randint(0, 100), 'splitPct': rng.randint(50, 90), 'skimPct': rng.randint(0, 50)})
        for tk in cp.TOKENS:
            assert held(s, tk) == put[tk]
            assert s['books'][tk]['pot'] >= 0 and s['books'][tk]['keep'] >= 0
        assert all(v >= 0 for a in s['agents'].values() for b in ('locked', 'owed') for v in a[b].values())


def test_no_new_money_means_the_count_slows_but_stays_covered():
    s = cp.new_state(); s['at'] = 1
    for i in range(50):
        cp.send(s, f'k{i}', f'a{i}', f'o{i}', 'USDC', 20 * USDC, 20, 1)
    cp.income(s, 'fees', 'USDC', 1000 * USDC, 'txn')
    t = run(s, 1, 5, 86400)
    r1 = cp.totals(s, SOL)['ratePerSecUsd']
    run(s, t, 200, 86400)
    assert cp.totals(s, SOL)['ratePerSecUsd'] < r1 / 10
    assert held(s, 'USDC') == 2000 * USDC


def test_file_update_is_atomic_and_a_failed_change_writes_nothing(tmp_path):
    p = tmp_path / 'pool.json'
    cp.update(p, lambda s: cp.income(s, 'a', 'USDC', 100, 'txn'))
    assert cp.load(p)['books']['USDC']['keep'] == 50

    def boom(s):
        cp.income(s, 'b', 'USDC', 100, 'txn')
        raise ValueError('no')
    try:
        cp.update(p, boom)
    except ValueError:
        pass
    assert cp.load(p)['books']['USDC']['keep'] == 50


def test_a_closed_proof_keeps_its_best_two_snapshots_after_14_days():
    import agent_print as ap
    shots = [{'file': f'{i}.jpg', 'site': 'dex' if i < 3 else 'rug', 'mint': 'M' if i else 'X', 'at': i} for i in range(5)]
    f = {'status': 'closed', 'mint': 'M', 'soldAt': 0, 'shots': list(shots)}
    assert ap.clean_shots(f, 13 * D) == [] and len(f['shots']) == 5                       # too soon
    assert ap.clean_shots({**f, 'status': 'open'}, 99 * D) == []                          # an open proof is never touched
    gone = ap.clean_shots(f, 15 * D)
    assert [s['file'] for s in f['shots']] == ['4.jpg', '2.jpg'] and len(gone) == 3       # the picked coin, two different sites


def test_a_pob_with_no_topic_picks_the_strongest_games_of_the_first_sport_that_has_any(monkeypatch):
    import asyncio
    import proof_tools as pt
    async def bids(http, sport):
        return {'legs': [{'pick': 'KC to beat DEN'}, {'pick': 'BUF to beat NYJ'}, {'pick': 'SF to beat SEA'}, {'pick': 'x'}]} if sport == 'nba' else {'legs': []}
    monkeypatch.setattr(pt, 'bids', bids)
    assert asyncio.run(pt.best_topic(None)) == 'best NBA picks: KC to beat DEN, BUF to beat NYJ, SF to beat SEA'
    async def none(http, sport):
        return {'legs': []}
    monkeypatch.setattr(pt, 'bids', none)
    assert asyncio.run(pt.best_topic(None)) == ''


def test_not_a_ponzi_no_members_money_can_ever_reach_the_pot():
    """Deposits, top-ups, sends, what a send keeps and what releases all stay out of the pot. Only fees on real activity go in."""
    s = cp.new_state(); s['at'] = 1
    for i, k in enumerate(('deposit', 'topup', 'proofs', 'release', 'gift', 'pass')):
        cp.income(s, f'k{i}', 'USDC', 100 * USDC, k)
    cp.send(s, 'send', 'a', 'o', 'USDC', 100 * USDC, 100, 1)
    run(s, 1, 100)                                                            # its release goes round too
    assert s['books']['USDC']['pot'] == 0 and s['agents']['a']['earned']['USDC'] == 0
    cp.income(s, 'real', 'USDC', 100 * USDC, 'txn')
    assert s['books']['USDC']['pot'] == 50 * USDC


def test_with_new_people_stopped_members_still_earn_while_members_trade():
    s = cp.new_state(); s['at'] = 1
    for i in range(10):
        cp.send(s, f's{i}', f'a{i}', f'o{i}', 'USDC', 20 * USDC, 20, 1)
    t = 1
    for d in range(60):
        cp.income(s, f'day{d}', 'USDC', 5 * USDC, 'txn')
        t = run(s, t, 1)
    assert s['agents']['a0']['earned']['USDC'] > 0
    assert held(s, 'USDC') == 200 * USDC + 300 * USDC


def test_an_edited_ledger_refuses_to_load_and_never_resets(tmp_path):
    p = tmp_path / 'pool.json'
    cp.update(p, lambda s: cp.income(s, 'a', 'USDC', 100, 'txn'))
    assert p.read_bytes().startswith(b'FP1:') and b'keep' not in p.read_bytes()    # sealed, nothing readable
    raw = bytearray(p.read_bytes()); raw[20] ^= 1; p.write_bytes(bytes(raw))
    with pytest.raises(cp.Tampered):
        cp.load(p)
    with pytest.raises(cp.Tampered):
        cp.update(p, lambda s: None)


def test_the_chain_counts_every_dollar_and_catches_a_cut_link(tmp_path):
    p = tmp_path / 'pool.json'
    cp.update(p, lambda s: cp.income(s, 'a', 'USDC', 100, 'txn'))
    cp.update(p, lambda s: cp.send(s, 'b', 'x', 'o', 'USDC', 50 * USDC, 50, 1))
    cp.update(p, lambda s: cp.income(s, 'c', 'SOL', 7, 'deposit'))
    cp.update(p, lambda s: (s.update(at=1), cp.tick(s, 90 * D, SOL)))
    r = cp.audit(p)
    assert r['ok'] and r['links'] == 3
    trail = p.with_suffix('.trail'); rows = trail.read_bytes().splitlines()
    trail.write_bytes(b'\n'.join(rows[:1] + rows[2:]) + b'\n')                   # someone removes a dollar
    r = cp.audit(p)
    assert not r['ok'] and 'match' in r['why']


def test_a_print_seed_is_stable_unique_and_cannot_be_chosen():
    a, b = cp.print_seed('agent1'), cp.print_seed('agent2')
    assert a == cp.print_seed('agent1') and a != b and len(a) == 32


def test_a_key_stays_spent_forever_even_after_a_hundred_thousand_more():
    s = cp.new_state()
    assert cp.income(s, 'first', 'USDC', 5, 'txn')
    for i in range(100_000):
        s['seen'][f'x{i}'] = 1
    assert cp.income(s, 'first', 'USDC', 5, 'txn') is False
    legacy = {**cp.new_state(), 'seen': ['old']}
    assert cp.income(legacy, 'old', 'USDC', 5, 'txn') is False and cp.income(legacy, 'new', 'USDC', 5, 'txn') is True

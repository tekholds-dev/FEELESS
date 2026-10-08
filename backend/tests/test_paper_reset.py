import random

import arena_prime as ap
import paper_reset as pr

NOW = 10 * 86400


def _card(**k):
    return {'tpl': 'safe', 'label': 'Prime Diamond', 'putInUsd': 20.0, 'startUsd': 1.5, 'rounds': 25, 'at': NOW - 5 * 86400, **k}


def test_a_paper_card_is_broke_at_a_quarter_of_what_was_put_in_after_a_real_try():
    assert pr.is_broke(_card(), 4.9, NOW) is True and pr.is_broke(_card(), 5.1, NOW) is False
    assert pr.is_broke(_card(rounds=3), 0.5, NOW) is False                          # not enough rounds played
    assert pr.is_broke(_card(at=NOW - 600), 0.5, NOW) is False                      # just dealt
    assert pr.is_broke(_card(), 0.5, NOW, last_reset=NOW - 3600) is False           # one reset per tier per 6h
    assert pr.is_broke(_card(real=True), 0.1, NOW) is False                         # the real-money card is never reset
    assert pr.is_broke(_card(putInUsd=0, startUsd=0), 0.0, NOW) is False


def test_a_fresh_config_is_never_the_old_one_nor_any_scrapped_one_and_proven_comes_first():
    old = pr.current({}, 'safe')
    assert old['pickStyle'] == 'hunt'
    new = pr.fresh_config(old, [], rnd=random.Random(1))
    assert pr.sig(new['cfg']) != pr.sig(old) and new['source'] == 'fresh' and new['cfg']['pickStyle'] != 'hunt'
    assert all(ap.clean_exit(k, v) == v for k, v in new['exits'].items())          # every value is one the engine accepts
    prov = {'rideAt': 30, 'rideTrail': 10, 'rotateMinDrop': 5, 'rotateConfirm': 3, 'minHoldMins': 30, 'pickStyle': 'sniper'}
    p = pr.fresh_config(old, [], proven=[prov], rnd=random.Random(2))
    assert p['source'] == 'proven' and p['cfg']['pickStyle'] == 'sniper' and p['exits']['rideAt'] == 30.0
    scrapped = [pr.scrap_row('safe', _card(), p['cfg'], 1.0, NOW)]                  # the proven one died too → it is scrapped, never offered again
    again = pr.fresh_config(p['cfg'], scrapped, proven=[prov], rnd=random.Random(3))
    assert again['source'] == 'fresh' and pr.sig(again['cfg']) != pr.sig(p['cfg'])


def test_a_style_no_other_paper_card_plays_is_preferred():
    old = {**pr.current({}, 'safe')}
    others = ('sniper', 'human', 'majors')                                          # hunt (old) · engine is the only free one
    for seed in range(6):
        assert pr.fresh_config(old, [], other_styles=others, rnd=random.Random(seed))['cfg']['pickStyle'] == 'engine'


def test_apply_writes_exits_and_selection_and_the_engine_reads_them_back():
    new = pr.fresh_config(pr.current({}, 'safe'), [], proven=[{'rideAt': 30, 'rideTrail': 10, 'rotateMinDrop': 5, 'rotateConfirm': 3, 'minHoldMins': 30, 'pickStyle': 'engine'}], rnd=random.Random(4))
    prime = pr.apply({}, 'safe', new)
    cfg = ap.clean_cfg(prime['cfg'])
    played = ap.tier_cfg(cfg, 'safe')
    assert played['pickStyle'] == 'engine' and played['rideAt'] == 30.0 and played['minHoldMins'] == 30.0
    assert ap.tier_cfg(ap.clean_cfg({}), 'safe')['pickStyle'] == 'hunt'               # other tiers / defaults are untouched
    assert pr.describe(new['cfg']).startswith('🧠 engine order')


def test_scrap_row_keeps_what_it_was_and_what_it_did():
    c = pr.current({}, 'safe')
    r = pr.scrap_row('safe', _card(), c, 1.3, NOW)
    assert r['sig'] == pr.sig(c) and r['valueUsd'] == 1.3 and r['putInUsd'] == 20.0 and r['rounds'] == 25 and 'runner hunt' in r['text']


def test_a_sim_strategy_becomes_a_candidate_with_valid_exits_and_selection_numbers():
    sim = {'tp': '300', 'sl': '15', 'minDrop': '20', 'rideAt': '150', 'trail': '8', 'confirm': '2', 'age': '12', 'pool': '50', 'edge': '1', 'rest': '30', 'buy': '70', 'floor': '3', 'vol': '100', 'mom': '40'}
    c = pr.from_sim(sim)
    assert c['tp'] == 300.0 and c['sl'] == 15.0 and c['rotateMinDrop'] == 20.0 and c['rideAt'] == 150.0 and c['rideTrail'] == 8.0 and c['rotateConfirm'] == 2 and c['minHoldMins'] == 30.0
    assert c['pickNum'] == {'runnerMinAgeH': 12.0, 'runnerMinLiqK': 50.0, 'runnerMinBuy': 70.0, 'runnerMinVolK': 100.0, 'runnerMinChg1h': 40.0, 'edgeFloor': 3.0, 'edgeGate': True}
    assert pr.from_sim({}) == {} and pr.from_sim({'sl': '70'}) == {}                                # nothing valid → no candidate (a 70% stop is outside what the engine accepts)
    new = pr.fresh_config(pr.current({}, 'safe'), [], proven=[{**c, 'pickStyle': 'sniper'}], rnd=random.Random(5))
    assert new['source'] == 'proven' and new['pick']['runnerMinLiqK'] == 50.0 and new['pick']['pickStyle'] == 'sniper'
    played = ap.tier_cfg(ap.clean_cfg(pr.apply({}, 'safe', new)['cfg']), 'safe')
    assert played['runnerMinLiqK'] == 50.0 and played['pickStyle'] == 'sniper'

"""The tick's broke-reset: a paper tier card at ≤ 25% of its put-in is removed (the next tick deals a fresh one), its config is scrapped for good and a new one
is written; the real card, healthy cards and locked tiers are never touched."""
import arena_prime as ap

NOW = 10 * 86400


def _card(tpl, cash, **k):
    return {'tpl': tpl, 'label': f'card {tpl}', 'legs': [], 'cash': cash, 'parked': {}, 'putInUsd': 20.0, 'startUsd': 3.0, 'rounds': 40, 'at': NOW - 5 * 86400, **k}


def test_broke_paper_cards_restart_on_a_new_config_and_the_old_one_is_scrapped():
    import reputation_service as rs
    d = {'prime': {'cfg': {}, 'locks': {'balanced': {'x': 1}}}}
    cards = {'safe': _card('safe', 1.3), 'next': _card('next', 12.0), 'balanced': _card('balanced', 0.8), 'degen': _card('degen', 0.5, real=True)}
    before = rs._prime.tier_cfg(rs._prime.clean_cfg(d['prime']['cfg']), 'safe')
    out = rs._paper_broke(d, cards, {}, NOW)
    assert set(out) == {'next', 'balanced', 'degen'}                                    # safe went broke → removed; healthy, locked and real stay
    pr = d['prime']
    assert [x['tpl'] for x in pr['scrapped']] == ['safe'] and pr['scrapped'][0]['valueUsd'] == 1.3 and pr['scrapped'][0]['putInUsd'] == 20.0
    after = rs._prime.tier_cfg(rs._prime.clean_cfg(pr['cfg']), 'safe')
    assert after['pickStyle'] != before['pickStyle']                                    # a different selection style
    assert pr['brokeAt']['safe'] == NOW and pr['renewed']['safe']['n'] == 1 and pr['renewed']['safe']['source'] in ('fresh', 'proven')
    # the same tier going broke again an hour later is not reset again (6h cooldown), and a second reset scraps the NEW config too
    again = rs._paper_broke(d, {'safe': _card('safe', 1.0)}, {}, NOW + 3600)
    assert 'safe' in again and len(pr['scrapped']) == 1
    rs._paper_broke(d, {'safe': _card('safe', 1.0, at=NOW - 86400)}, {}, NOW + 7 * 3600)
    assert len(pr['scrapped']) == 2 and pr['renewed']['safe']['n'] == 2 and pr['scrapped'][1]['sig'] != pr['scrapped'][0]['sig']
    third = rs._prime.tier_cfg(rs._prime.clean_cfg(pr['cfg']), 'safe')
    assert {x['sig'] for x in pr['scrapped']}.isdisjoint({__import__('paper_reset').sig(__import__('paper_reset').current(rs._prime.clean_cfg(pr['cfg']), 'safe'))})   # the live config is never a scrapped one

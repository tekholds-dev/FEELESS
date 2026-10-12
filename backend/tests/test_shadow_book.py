"""📄 Emergency edge audit: agents on paper, a shadow book with a control group, graded after costs at fixed horizons (no hindsight)."""
import shadow_book as sb
import arena_prime as ap


def row(m, opp=50, px=1.0):
    return {'mint': m, 'symbol': m, 'opp': opp, 'px': px, 'vitals': {'ageH': 1}, 'nums': {'liq': 20000}}


def test_paper_is_the_default_and_the_tick_never_buys_on_paper():
    assert ap.clean_cfg({})['agentPaper'] is True and ap.clean_cfg({'agentPaper': False})['agentPaper'] is False
    src = open(__import__('reputation_service').__file__).read()
    assert "if cfg_t.get('agentPaper'):" in src and 'plan_ = []' in src                     # seat fills → shadow book only
    assert "if x['action'] == 'swap' and paper_:" in src                                     # switch-ins too (exits still act)


def test_controls_are_from_the_same_moment_and_never_the_chosen_coin():
    c = sb.controls([row('A')], [row('A'), row('B', 80), row('C', 10), row('D', 30)], [row('W')], 1000)
    assert c['ctl_top']['mint'] == 'B' and c['ctl_random']['mint'] in ('C', 'D') and c['ctl_wait']['mint'] == 'W'
    assert sb.controls([row('A')], [row('A')], [], 1) == {}


def test_grading_uses_only_prices_seen_after_the_decision_net_of_measured_cost():
    b = sb.note({}, row('A'), 'fill', 1000, 1.0, 3.0)
    b = sb.note(b, row('A'), 'fill', 1100, 1.0, 3.0)                 # deduped inside 10 min
    assert len(b['rows']) == 1
    b = sb.settle(b, {'A': 1.10}, 1000 + 61)                          # 30s and 1m graded at the first read after them
    assert b['rows'][0]['h'] == {'30': 10.0, '60': 10.0}
    b = sb.settle(b, {'A': 0.90}, 1000 + 305)
    assert b['rows'][0]['h']['300'] == -10.0 and b['rows'][0]['lo'] == -10.0 and b['rows'][0]['hi'] == 10.0
    rep = sb.report(b)
    assert rep['fill']['60']['avg'] == 7.0 and rep['fill']['300']['avg'] == -13.0      # gross − 3% measured cost
    b = sb.settle(b, {}, 1000 + 3600 + 400)                            # no price well past the hour = vanished
    assert b['rows'][0]['h']['3600'] == -100.0


def test_the_verdict_never_says_more_than_the_numbers():
    assert 'not enough yet' in sb.verdict({})
    mk = lambda avg: {'300': {'n': 40, 'avg': avg, 'med': avg, 'won': 50, 'pf': 1}}
    assert 'NOT better than a random' in sb.verdict({'fill': mk(-5), 'ctl_random': mk(-2)})
    assert 'still losing after costs' in sb.verdict({'fill': mk(-1), 'ctl_random': mk(-4)})
    assert 'positive and better than random' in sb.verdict({'fill': mk(2), 'ctl_random': mk(-1)})


def test_the_judge_proposes_but_never_moves_a_live_threshold():
    import judge_review as jr
    promoted = [{'penalty': 'thin pool', 'points': -8}]
    assert jr.penalties(promoted) == {} and jr.penalties(promoted, live=True) == {'thin pool': -8.0}


def test_a_held_card_gets_no_engine_replacement_of_any_kind():
    """2026-10-12: under the agents' hold a refused agent buy became $Business (stuck-buy swap) and a stop's reserved seat bought $CHILLGUY (30s fallback)."""
    mk = lambda i: {'mint': f'R{i}', 'pairAddress': f'PR{i}', 'symbol': f'R{i}', 'price': 1.0, 'liq': 500_000, 'liquidityUsd': 500_000, 'score': 90 - i, 'stars': 3, 'chg1h': 5.0}
    held, chill = [mk(i) for i in range(3)], {**mk(9), 'chg5m': 1.0, 'cStruct': 'up'}
    base = {'coins': 4, 'rotateHours': 0.25, 'rescuePct': 0, 'cycleEvery': 0, 'cycles': {t: 'off' for t in ap.DEFAULT_CYCLES}, 'lockBankPct': 0, 'tpStakeUsd': 0}
    cfg = {**ap.clean_cfg(base), 'seatFallback': [chill]}
    card = ap.deal('degen', [], held, ap.clean_cfg({**base, 'coins': 3}), 0.0, [], shape='degen')
    seat = {**card['legs'][-1], 'mint': 'GONE', 'pairAddress': 'PG', 'units': 0.0, 'costUsd': 0.0, 'reserveUsd': 0.3, 'placeholder': True}
    card = {**card, 'legs': card['legs'] + [seat], 'cash': card.get('cash', 0) + 1.0, 'holdAll': True, 'holdBy': 'agents', 'seatEmptyAt': 0.0}
    px = {x['pairAddress']: 1.0 for x in held + [chill]}
    out = ap.tick(card, px, [], held, cfg, 500.0, [], {}, {})
    assert 'R9' not in {l.get('mint') for l in out['legs']}
    src = open(__import__('reputation_service').__file__).read()
    assert "if cur.get('holdBy') in ('proof', 'agents'):   # 🎮 held: the ENGINE swaps nothing in" in src

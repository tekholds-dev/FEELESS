"""⚡ Open trenching (owner, 2026-10-12): volume + newness + live narrative rank the seats; only execution safety can stop a buy."""
from pathlib import Path

import office as of
import opportunity as opp

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def row(m='M', age=0.05, mc=40_000, d5=6.0, buy=62, liq=20_000, v5=8_000, pace=2.0, **k):
    return {'mint': m, 'symbol': m, 'px': 1.0, 'nums': {'v5': v5, 'pace': pace, 'liq': liq, 'd5': d5, 'buy': buy},
            'vitals': {'mcap': mc, 'liq': liq, 'ageH': age, 'vol1h': 20_000, 'txns1h': 300, 'safe': False, 'rug': 80}, **k}


def test_no_reputation_or_holder_gate_only_execution_safety():
    assert opp.open_ok(row()) is None                                  # holder scan FAILED + rug 80: not a reason in open mode
    assert opp.open_ok(row(liq=3_000)).startswith('pool under the keeper floor')
    assert opp.open_ok(row(age=7)) == 'not ≤ 6h old' and opp.open_ok(row(mc=250_000)).startswith('outside')
    assert opp.open_ok({**row(), 'chart': {'state': 'DATA INVALID'}}).startswith('market data')
    assert opp.open_ok(row(v5=50, pace=0.05)).startswith('dead')


def test_the_live_narrative_comes_from_this_pass_only_and_weak_ones_are_skipped():
    assert opp.narrative(row())[0] == 'HOT EARLY MOVE'
    assert opp.narrative(row(age=2, d5=3, buy=60, pace=1.2))[0] == 'RUNNING'
    assert opp.narrative(row(age=2, d5=0.2, pace=0.5))[0] == 'STALLING'
    assert opp.narrative(row(d5=-20))[0] == 'COLLAPSING' and opp.open_ok(row(d5=-20)).startswith('collapsing')
    assert opp.narrative({**row(), 'li': {'ewp': 'DUMPING'}})[0] == 'DISTRIBUTING'
    assert opp.narrative({**row(age=2), 'mp': 'BREAKOUT'})[0] == 'BREAKOUT'


def test_ranking_is_newness_times_volume_times_buyers_times_momentum():
    new_hot = opp.open_score(row())[0]
    old_quiet = opp.open_score(row('O', age=5.5, v5=900, pace=0.8, d5=0.5))[0]
    assert new_hot > old_quiet
    assert opp.open_score(row(), {'M': 1.3})[0] > new_hot > opp.open_score(row(), {'M': 0.7})[0]   # the Judge moves the weight, never vetoes
    assert opp.open_score({**row(), 'li': {'ewp': 'WARNING'}})[0] < new_hot


def test_open_mode_fills_every_empty_seat_through_the_one_path_and_the_warden_keeps_only_execution():
    assert "if (cfg_t.get('agentOpen') and empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD'" in SRC and SRC.count('_prime.agent_seat(') == 1
    base = {'liq': 500_000, 'ageH': 0.05, 'courier': 'OK', 'holderSoft': ['Top 10 under'], 'li': {'press': 'HIGH', 'pressWhy': 'x'}}
    assert of.warden(0.13, {**base, 'open': True})['allowed'] == 0.13          # age / holder / exit-risk rules don't apply in open mode
    assert of.warden(0.13, {**base, 'open': True, 'courier': 'BAD'})['veto']    # execution health still does
    w = of.warden(0.05, {**base, 'open': True, 'rtPct': 2.4, 'feeUsd': 0.001}, floor=0.05)
    assert w['veto'] and 'SIZE TOO SMALL FOR COSTS' in w['rules'][-1]['why']

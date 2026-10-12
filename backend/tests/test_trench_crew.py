"""🪖 The trench crew: ten roles, one hard wall at the money boundary; Devil weighs, Warden shrinks, Sherlock's unknown is research."""
from pathlib import Path

import office as of
import opportunity as opp
import trench_crew as crew

ROOT = Path(__file__).resolve().parents[2]


def row(**k):
    return {'mint': 'M', 'symbol': 'M', 'px': 1.0, 'nums': {'v5': 8_000, 'pace': 2.0, 'liq': 20_000, 'd5': 6.0, 'buy': 62},
            'vitals': {'mcap': 40_000, 'liq': 20_000, 'ageH': 0.3, 'vol1h': 20_000, 'txns1h': 300}, **k}


def test_ten_roles_and_the_doc_say_the_same_thing():
    assert list(crew.CREW) == ['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge']
    doc = (ROOT / 'docs' / 'TRENCH_CREW.md').read_text()
    assert all(role in doc for role, _does, _never in crew.CREW.values()) and 'HARD WALL' in doc


def test_devil_objections_are_confidence_not_vetoes_and_only_a_dev_dump_is_the_wall():
    plain = opp.open_score(row())[0]
    warned = row(objs=[['rug_signs', 'x'], ['identity', 'y'], ['ran', 'z']])
    assert opp.open_ok(warned) is None and opp.open_score(warned)[0] < plain                  # weighed, not blocked
    assert crew.devil_factor(row(objs=[['rug_meter', '']] * 9))[0] == crew.DEVIL_MIN         # never below ×0.6
    assert opp.open_ok(row(li={'press': 'HIGH', 'pressWhy': 'creator sold $400 in 90s'})) == 'the dev is dumping now'


def test_sherlock_unknown_is_a_research_state_not_a_rejection():
    unknown = row(vitals={**row()['vitals'], 'safe': None, 'site': None, 'x': None}, social=None)
    assert opp.open_ok(unknown) is None


def test_warden_shrinks_in_trench_mode_and_only_execution_can_veto():
    ctx = {'open': True, 'liq': 500_000, 'ageH': 0.05, 'courier': 'OK', 'holderSoft': ['Top 10 under'], 'li': {'press': 'HIGH', 'pressWhy': 'early wallet sold'},
           'weather': {'regime': 'HOSTILE', 'mods': {'size': 0.25}}}
    w = of.warden(1.0, ctx)
    assert not w['veto'] and w['allowed'] == 0.5 and all(r['mult'] >= crew.SHRINK_FLOOR for r in w['rules'])
    assert of.warden(1.0, {**ctx, 'courier': 'BAD'})['veto']

"""COL-10: method kits are read-only, measured against outside-settled results, and quarantined when following them does clearly worse."""
import pytest

import method_kits as mk


def _env(i, won, kind='pob'):
    return {'kind': kind, 'id': f'b{i}', 'outcome': {'strength': 'outside', 'state': 'proved' if won else 'not'}}


def test_reliability_measures_and_quarantines_only_with_enough_settled():
    thick = {'sites': ['a.com', 'b.com', 'c.com', 'd.com'], 'board': [{}, {}], 'calls': [{'why': 'x'}]}
    envs, by = [], {}
    for i in range(12):   # followed: 2 of 12 won
        envs.append(_env(i, i < 2)); by[('pob', f'b{i}')] = thick
    for i in range(12, 24):   # skipped: 8 of 12 won
        envs.append(_env(i, i < 20)); by[('pob', f'b{i}')] = {}
    r = mk.reliability(envs, by)['compare-before-settling']
    assert (r['followed'], r['skipped'], r['followedWin'], r['skippedWin'], r['state']) == (12, 12, 0.167, 0.667, 'quarantined')
    assert 'compare-before-settling' not in mk.active_line('pob', {'compare-before-settling': r})   # a quarantined kit is no longer offered
    few = mk.reliability(envs[:5] + envs[12:17], by)['compare-before-settling']
    assert few['state'] == 'unmeasured' and 'compare-before-settling' in mk.active_line('pob', {'compare-before-settling': few})


def test_a_kit_can_never_ask_for_more_than_read():
    assert all(set(k['permissions']) <= {'read'} for k in mk.KITS.values())
    mk.KITS['bad'] = {'v': 1, 'kinds': ('pow',), 'permissions': ('read', 'wallet'), 'what': 'x', 'check': lambda k, f: True}
    try:
        with pytest.raises(AssertionError):
            for _id, _k in mk.KITS.items():
                assert set(_k['permissions']) <= set(mk.PERMISSIONS), _id
    finally:
        mk.KITS.pop('bad')

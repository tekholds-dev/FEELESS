"""🧩 COL-10: kits combined. A pair that wins more together than either alone is proposed; once approved it is followed only when both are."""
import method_kits as mk


def _rows(n_both_win, n_both, n_a_only_win, n_a_only):
    env, fol = [], {}
    def add(i, plan, record, win):
        f = {'id': f'f{i}', 'plan': ['x'] if plan else None, 'sitesRead': ['a'] if record else None}
        fol[('pos', f'f{i}')] = f; env.append({'kind': 'pos', 'id': f'f{i}', 'outcome': {'strength': 'outside', 'state': 'proved' if win else 'not'}})
    i = 0
    for j in range(n_both):
        add(i, True, True, j < n_both_win); i += 1
    for j in range(n_a_only):
        add(i, True, False, j < n_a_only_win); i += 1
    return env, fol


def test_a_pair_that_wins_together_is_proposed_then_checks_both(tmp_path):
    env, fol = _rows(9, 12, 3, 12)   # plan + record: 75% · plan alone: 25%
    rows = mk.combos(env, fol)
    pair = next(r for r in rows if r['combo'] == ['plan-first', 'read-the-record-first'])
    assert pair['proposed'] and pair['settled'] == 12 and pair['bothWin'] == 0.75 and pair['kinds'] == ['pop', 'pos', 'pow']
    ex = mk.approve_combo(tmp_path, pair)
    kit = mk.all_kits(ex)[pair['id']]
    assert kit['permissions'] == ('read',) and kit['check']('pos', {'plan': ['x'], 'sitesRead': ['a']}) and not kit['check']('pos', {'plan': ['x']})
    assert not next(r for r in mk.combos(env, fol, ex) if r['id'] == pair['id'])['proposed']   # approved once, never proposed again
    assert pair['id'] in mk.reliability(env, fol, ex)   # measured like any kit


def test_too_few_settled_or_no_lift_is_never_proposed():
    env, fol = _rows(4, 5, 1, 5)
    assert not any(r['proposed'] for r in mk.combos(env, fol))
    env, fol = _rows(6, 12, 6, 12)   # 50% both, 50% alone: no lift
    assert not any(r['proposed'] for r in mk.combos(env, fol))

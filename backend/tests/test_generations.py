"""🧬 ONE lifecycle for all ten roles (trench_kernel/lifecycle.py): real-money evidence only; a failed generation is replaced on the
evaluation that condemns it, the next one starts from DEFAULTS plus only the fix for how the last failed, and a SHADOW / RETIRED generation
has no live authority."""
import generations as gn
import office as of
import trench_kernel.brain as tb
import trench_kernel.lifecycle as lc

from kernel_helpers import row

T0 = 10_000.0   # (a generation is not replaced in its first hour)


def losses(n, desk, cause, at=T0 - 5000, resp=60):
    return [{'kind': 'loss', 'at': at + i, 'resp': {desk: resp}, 'cause': cause, 'lossClass': 'BAD EXIT'} for i in range(n)]


def book(**roles):
    b = lc.new_book(0.0)
    for r in lc.ROLES:
        b['roles'][r]['bornAt'] = 1.0
    for r, v in roles.items():
        b['roles'][r].update(v)
    return b


def test_every_role_uses_the_one_book_with_the_same_fields():
    gens = lc.generations(book(), T0)
    assert [g['role'] for g in gens] == list(tb.ROLES) == list(lc.ROLES) and all(g['status'] == 'ACTIVE' for g in gens)
    assert all(set(g) >= {'role', 'generation', 'bornAt', 'status', 'decisions', 'winsAttributed', 'lossesAttributed', 'netImpact', 'lessonVector', 'lineage', 'lastEvaluation'} for g in gens)
    assert set(lc.STATUSES) == {'ACTIVE', 'PROBATION', 'SHADOW', 'RETIRED'}


def test_the_two_old_books_migrate_once_into_the_one():
    four = {'gen': {'tally': 7, 'devil': 2}, 'born': {'tally': 50.0}, 'lineage': [{'agent': 'devil', 'gen': 1, 'born': 1, 'died': 40, 'why': 'paper', 'lesson': ['a', 'b']}]}
    office = {'gen': {'reaper': 3}, 'born': {'reaper': 90.0}, 'tune': {'reaper': {'stopPct': 20.0}}, 'lineage': [{'agent': 'reaper', 'gen': 2, 'at': 90, 'why': 'x', 'oldTune': {'stopPct': 30.0}}]}
    b = lc.new_book(100.0, four, office)
    assert b['roles']['tally']['gen'] == 7 and b['roles']['devil']['gen'] == 2 and b['roles']['reaper']['gen'] == 3
    assert b['roles']['reaper']['lesson'] == {'stopPct': 20.0} and b['roles']['reaper']['bornAt'] == 90.0
    assert {(x['role'], x['gen'], x['status']) for x in b['lineage']} == {('devil', 1, 'RETIRED'), ('reaper', 2, 'RETIRED')}


def test_a_failed_reaper_is_replaced_now_and_the_new_generation_fixes_only_how_it_failed():
    b = book(reaper={'lesson': {'stopPct': 40.0}})
    b2, ev = lc.evaluate(b, losses(3, 'reaper', 'gave_back'), T0, tunable=of.TUNABLE)
    r = b2['roles']['reaper']
    assert r['gen'] == 2 and r['status'] == 'ACTIVE' and r['bornAt'] == T0
    assert r['lesson'] == {'protectAt': 4.0, 'giveBackPct': 35.0}                       # the fix only — the old stopPct 40 is NOT inherited
    x = b2['lineage'][-1]
    assert (x['role'], x['gen'], x['status']) == ('reaper', 1, 'SHADOW') and x['lesson'] == {'stopPct': 40.0} and 'arms its trail at +4%' in x['changed']
    assert ev == [e for e in ev if e['role'] == 'reaper'] and ev[0]['kind'] == 'replaced' and ev[0]['to'] == 2
    b3, ev3 = lc.evaluate(b2, losses(3, 'reaper', 'gave_back'), T0 + 100, tunable=of.TUNABLE)   # its new life starts clean: old losses don't count twice
    assert b3['roles']['reaper']['gen'] == 2 and not ev3


def test_the_same_rule_replaces_a_brain_side_role_and_an_office_role():
    b, ev = lc.evaluate(book(), losses(3, 'trigger', 'crowd_fomo') + losses(4, 'warden', 'thin_pool'), T0, tunable=of.TUNABLE)
    assert {e['role'] for e in ev if e['kind'] == 'replaced'} == {'trigger', 'warden'}
    assert b['roles']['trigger']['lesson'] == {'lateMove': 25.0} and b['roles']['warden']['lesson'] == {'poolSharePct': 0.75}
    assert all(b['roles'][r]['gen'] == 1 for r in lc.ROLES if r not in ('trigger', 'warden'))


def test_probation_is_shown_and_it_is_still_the_only_generation_in_control():
    b, ev = lc.evaluate(book(), losses(2, 'devil', 'rugged'), T0)
    d = b['roles']['devil']
    assert d['status'] == 'PROBATION' and d['gen'] == 1 and ev[0]['kind'] == 'probation'
    assert lc.has_authority(b, 'devil', 1) and 'devil' in lc.lessons(b)
    b, ev = lc.evaluate(b, losses(2, 'devil', 'rugged') + [{'kind': 'win', 'at': T0 - 10, 'exit': 'R7 trail'}], T0 + 1)
    assert b['roles']['devil']['status'] == 'ACTIVE' and ev[0]['kind'] == 'cleared'     # a credited win clears it


def test_one_valid_loss_or_a_loss_pinned_elsewhere_never_replaces_a_role():
    b, ev = lc.evaluate(book(), losses(1, 'warden', 'variance') + losses(5, 'warden', 'thin_pool', resp=30), T0)   # 30 = not PINNED on it
    assert b['roles']['warden']['gen'] == 1 and b['roles']['warden']['status'] == 'ACTIVE' and not ev
    few = losses(3, 'reaper', 'gave_back') + [{'kind': 'win', 'at': T0 - 1, 'exit': 'R7 trail'}]
    assert lc.evaluate(book(), few, T0)[0]['roles']['reaper']['gen'] == 1                # 3 losses − 1 win credited: PROBATION, not replaced
    young = book(reaper={'bornAt': T0 - 60})
    assert lc.evaluate(young, losses(3, 'reaper', 'gave_back', at=T0 - 50), T0)[0]['roles']['reaper']['gen'] == 1   # a generation gets its first hour


def test_a_retired_or_shadow_generation_has_no_live_authority():
    b, _ = lc.evaluate(book(devil={'lesson': {'strong': 0.75}}), losses(3, 'devil', 'rugged'), T0)
    assert not lc.has_authority(b, 'devil', 1) and lc.has_authority(b, 'devil', 2)
    assert lc.lessons(b)['devil'] == {'strong': 0.8}                                     # the brain can only ever read the generation in control
    assert lc.lesson_value(b, 'devil', 'strong') == 0.8 and b['lineage'][-1]['lesson'] == {'strong': 0.75}
    stale = {**b, 'roles': {**b['roles'], 'devil': {**b['roles']['devil'], 'status': 'RETIRED'}}}
    assert 'devil' not in lc.lessons(stale) and lc.lesson_value(stale, 'devil', 'strong') == 0.85   # no live generation → the default, never an old lesson


def test_the_brain_plays_the_live_generations_lesson():
    ms_row = row('L', d5=10.0, age=0.05)                                                  # +10% in 5 min, HOT EARLY MOVE (≥ +12% is a spike: it waits)
    import trench_kernel.kernel as tk
    k = tk.Kernel(); k.run([ms_row], 100.0, {})
    assert k.dec['L']['opinions']['trigger']['state'] == 'ENTER'
    k = tk.Kernel(); k.run([ms_row], 100.0, {'lessons': {'trigger': {'lateMove': 8.0}}})
    assert k.dec['L']['opinions']['trigger']['state'] == 'ARM' and k.dec['L']['status'] != 'READY'   # the new Trigger generation arms it instead of chasing
    ev = row('E', ev=[['rug_meter', 'rug meter 60']])
    a = tk.Kernel(); a.run([ev], 100.0, {})
    b_ = tk.Kernel(); b_.run([ev], 100.0, {'lessons': {'devil': {'strong': 0.8}}})
    assert b_.dec['E']['rank'] < a.dec['E']['rank']
    k = tk.Kernel(); k.run([row('S', d5=30.0, age=0.05)], 100.0, {})
    assert k.dec['S']['opinions']['trigger']['state'] == 'WAIT'   # 🚀 a +30% spike is never entered: it waits for the germ pullback


def test_a_shadow_retires_after_a_day_and_only_one_shadow_per_role():
    b, _ = lc.evaluate(book(), losses(3, 'reaper', 'gave_back'), T0, tunable=of.TUNABLE)
    b, _ = lc.evaluate(b, losses(3, 'reaper', 'held_too_long', at=T0 + 100), T0 + 4000, tunable=of.TUNABLE)
    assert [(x['gen'], x['status']) for x in b['lineage'] if x['role'] == 'reaper'] == [(1, 'RETIRED'), (2, 'SHADOW')]
    b, _ = lc.evaluate(b, [], T0 + 4000 + lc.SHADOW_SEC + 1)
    assert all(x['status'] == 'RETIRED' for x in b['lineage'])
    past = next(g for g in lc.generations(b, T0 + 4000) if g['role'] == 'reaper')['lineage']
    assert [p['gen'] for p in past] == [2, 1]


def test_integrity_roles_are_judged_on_integrity_never_on_a_trades_result():
    rv = losses(9, 'courier', 'rugged')
    assert lc.evaluate(book(), rv, T0)[0]['roles']['courier']['gen'] == 1
    b, ev = lc.evaluate(book(), rv, T0, integrity={'courier': 3, 'archivist': 2})
    assert b['roles']['courier']['gen'] == 2 and b['roles']['archivist']['status'] == 'PROBATION' and b['roles']['judge']['status'] == 'ACTIVE'


def test_the_office_desks_lesson_is_their_tunables():
    b, ev = lc.evaluate(book(), losses(3, 'reaper', 'gave_back'), T0, tunable=of.TUNABLE)
    b, tune = lc.sync_office(b, {'reaper': {'stopPct': 40.0}, 'warden': {'ddPct': 30.0}}, {'reaper'})
    assert tune['reaper'] == {'protectAt': 4.0, 'giveBackPct': 35.0} and tune['warden'] == {'ddPct': 30.0}
    assert of.tune({'tune': tune}, 'reaper', 'protectAt') == 4.0 and of.tune({'tune': tune}, 'reaper', 'stopPct') == 30.0   # back to the default
    assert b['roles']['warden']['lesson'] == {'ddPct': 30.0}                             # a value the office promoted is the live generation's lesson


def test_improvements_are_bounded_and_start_from_defaults():
    patch, words = gn.improve('reaper', ['held_too_long', 'gave_back'], of.TUNABLE)
    assert patch == {'timeMaxMin': 60.0, 'stopPct': 20.0, 'protectAt': 4.0, 'giveBackPct': 35.0}
    for k, v in patch.items():
        _d, lo, hi, _ = of.TUNABLE['reaper'][k]
        assert lo <= v <= hi
    assert gn.improve('weather', ['gave_back'], of.TUNABLE) == ({}, ['clean defaults — no specific failure pattern to fix'])
    for role, causes in lc.CAUSE_PATCH.items():
        for cause, items in causes.items():
            for key, val, _w in items:
                _d, lo, hi, _ = {**of.TUNABLE, **lc.KERNEL_TUNABLE}[role][key]
                assert lo <= val <= hi, (role, key)


def test_the_shadow_record_compares_old_and_new_on_the_same_real_exits():
    pos = [{'closedAt': 200 + i, 'path': [2, 7, 4.5, 3, -2]} for i in range(6)]   # new banks +4.5 (35% give-back), old waits to +3
    old, new = {'stopPct': 30, 'protectAt': 6, 'giveBackPct': 50}, {'stopPct': 20, 'protectAt': 4, 'giveBackPct': 35}
    r = gn.shadow_record(pos, old, new, 100, 50, of.reaper_replay)
    assert r['n'] == 6 and r['new'] > r['old'] and r['verdict'] == 'new generation better'
    assert 'too early' in gn.shadow_record(pos[:2], old, new, 100, 50, of.reaper_replay)['verdict']


def test_a_generation_that_won_hands_down_what_it_won_with_and_a_loser_hands_down_nothing():
    prev = {'stopPct': 22.0, 'protectAt': 9.0}
    # it never won: nothing is inherited (no inherited fear) — only the fix
    assert lc.improve('reaper', ['gave_back'], of.TUNABLE, prev=prev, wins=1)[0] == {'protectAt': 4.0, 'giveBackPct': 35.0}
    # it won 4 real trades: the stop it won with is kept; the trail it FAILED on is replaced by the fix, never kept
    lesson, words = lc.improve('reaper', ['gave_back'], of.TUNABLE, prev=prev, wins=4)
    assert lesson == {'stopPct': 22.0, 'protectAt': 4.0, 'giveBackPct': 35.0} and any('kept stopPct 22' in w for w in words)
    lo, hi = of.TUNABLE['reaper']['stopPct'][1], of.TUNABLE['reaper']['stopPct'][2]
    assert lo <= lc.improve('reaper', [], of.TUNABLE, prev={'stopPct': 999, 'notAKey': 1}, wins=5)[0]['stopPct'] <= hi     # clamped; unknown keys dropped
    assert gn.improve('reaper', ['gave_back'], of.TUNABLE, prev=prev, wins=4)[0] == lesson

"""🧬 True substitution: a failed generation loses control at once, the next one is ACTIVE on the same tick with only the fix for how the
last one failed (from defaults), and the old one is judged in SHADOW on the same real exits."""
import agents as ag
import generations as gn
import office as of


def losses(n, desk, cause, at=10):
    return [{'kind': 'loss', 'at': at + i, 'resp': {desk: 1}, 'cause': cause, 'lossClass': 'BAD EXIT'} for i in range(n)]


def test_a_failed_reaper_is_replaced_now_and_the_new_generation_fixes_how_it_failed():
    o = of.demote({'tune': {'reaper': {'stopPct': 40.0}}}, {}, 100.0, losses(3, 'reaper', 'gave_back'))
    assert o['gen']['reaper'] == 2 and o['born']['reaper'] == 100.0
    assert o['tune']['reaper'] == {'protectAt': 4.0, 'giveBackPct': 35.0}          # the fix only — the old stopPct 40 is NOT inherited
    x = o['lineage'][-1]
    assert x['oldTune']['stopPct'] == 40.0 and x['newTune']['protectAt'] == 4.0 and 'arms its trail at +4%' in x['changed']


def test_its_own_judged_record_replaces_it_too_with_no_tunable_needed():
    o = of.demote({'born': {'reaper': 0.0}}, {'reaper': {'status': 'demoted', 'why': '34% right over 158 samples'}}, 5000.0, [])
    assert o['gen']['reaper'] == 2 and '34% right' in o['lineage'][-1]['why']
    assert of.demote(o, {'reaper': {'status': 'demoted', 'why': 'x'}}, 5100.0, [])['gen']['reaper'] == 2   # a fresh generation gets an hour


def test_one_valid_loss_never_replaces_a_desk():
    assert of.demote({}, {}, 100.0, losses(1, 'warden', 'variance')).get('gen', {}).get('warden') is None


def test_improvements_are_bounded_and_never_stricter_about_what_may_be_bought():
    patch, words = gn.improve('reaper', ['held_too_long', 'gave_back'], of.TUNABLE)
    assert patch == {'timeMaxMin': 60.0, 'stopPct': 20.0, 'protectAt': 4.0, 'giveBackPct': 35.0}
    for k, v in patch.items():
        _d, lo, hi, _ = of.TUNABLE['reaper'][k]
        assert lo <= v <= hi
    assert gn.improve('weather', ['gave_back'], of.TUNABLE) == ({}, ['clean defaults — no specific failure pattern to fix'])
    assert 'barBump' not in ag.lesson({}, 'trigger')                                    # no inherited fear for the four desks either


def test_no_probation_in_control_for_the_four_desks():
    st = {'born': {'devil': 0}, 'realReviews': [{'kind': 'loss', 'at': 10 + i, 'resp': {'devil': 60}} for i in range(3)]}
    assert ag.survival(st)['devil']['status'] == 'scrap'                                  # 3 net real losses → replaced by evolve on the next pass
    assert ag.survival({**st, 'realReviews': st['realReviews'][:2]})['devil']['status'] == 'watch'


def test_the_shadow_record_compares_old_and_new_on_the_same_real_exits():
    pos = [{'closedAt': 200 + i, 'path': [2, 7, 4.5, 3, -2]} for i in range(6)]   # new banks +4.5 (35% give-back), old waits to +3
    old, new = {'stopPct': 30, 'protectAt': 6, 'giveBackPct': 50}, {'stopPct': 20, 'protectAt': 4, 'giveBackPct': 35}
    r = gn.shadow_record(pos, old, new, 100, 50, of.reaper_replay)
    assert r['n'] == 6 and r['new'] > r['old'] and r['verdict'] == 'new generation better'
    assert 'too early' in gn.shadow_record(pos[:2], old, new, 100, 50, of.reaper_replay)['verdict']


def test_every_role_has_one_active_generation_and_the_replaced_one_is_shadow_then_retired():
    office = {'gen': {'reaper': 3}, 'born': {'reaper': 9000}, 'lineage': [{'agent': 'reaper', 'gen': 1, 'at': 100, 'why': 'a'}, {'agent': 'reaper', 'gen': 2, 'at': 9000, 'why': 'b'}]}
    lc = gn.lifecycle({}, office, 9500)
    assert len(lc) == 10 and all(v['active']['status'] == 'ACTIVE' for v in lc.values())
    assert lc['reaper']['active']['gen'] == 3 and [p['status'] for p in lc['reaper']['past']] == ['SHADOW', 'RETIRED']
    assert gn.lifecycle({}, office, 9000 + gn.SHADOW_SEC + 1)['reaper']['past'][0]['status'] == 'RETIRED'
    assert gn.lifecycle({}, {**office, 'benched': ['reaper']}, 9500)['reaper']['active']['status'] == 'BENCHED'

"""👁 After the exit: Reaper's replay sees the whole move, not a path that ends at its own sale."""
import after_path as ap
import office as of


def _pos(i, path, entry=1.0):
    return {'mint': f'M{i}', 'closedAt': 1000.0 + i, 'entry': entry, 'confirmed': True, 'path': path}


def test_an_exit_is_watched_for_30_minutes_and_a_coin_with_no_price_left_ends_at_minus_100():
    st = ap.watch({}, [_pos(1, [2, 5, 3]), {'mint': 'U', 'closedAt': 5, 'entry': 1.0, 'confirmed': False}, {'mint': 'Z', 'closedAt': 6, 'confirmed': True}], 1000.0)
    assert list(st['open']) == ['M1|1001'] and ap.mints(st) == ['M1']                    # unconfirmed / no entry price = not watched
    st = ap.step(st, {'M1': 1.10}, 1010.0)
    st = ap.step(st, {'M1': 1.20}, 1020.0)                                               # 10s later: too soon for a second reading
    assert st['open']['M1|1001']['pts'] == [10.0]
    st = ap.step(st, {'M1': 1.30}, 1050.0)
    st = ap.step(st, {'M1': 1.25}, 1000.0 + ap.AFTER_SEC + 1)
    assert not st['open'] and st['done']['M1|1001'] == [10.0, 30.0, 25.0]
    assert ap.full(_pos(1, [2, 5, 3]), st['done']) == [2, 5, 3, 10.0, 30.0, 25.0] and ap.full(_pos(2, [1]), st['done']) is None
    gone = ap.step(ap.step(ap.watch({}, [_pos(3, [1])], 0.0), {'M3': 1.05}, 40.0), {}, 40.0 + ap.GONE_SEC + 1)
    assert gone['done']['M3|1003'] == [5.0, -100.0]                                      # a rug after our exit is what a wider trail eats
    assert ap.watch(st, [_pos(1, [2, 5, 3])], 9999.0)['open'] == {}                      # never watched twice


def test_the_grid_only_says_a_wider_trail_pays_on_enough_full_paths_and_the_truncated_path_alone_can_never_show_it():
    live = {'protectAt': 4.0, 'giveBackPct': 35.0, 'stopPct': 30.0, 'timeMaxMin': 120.0}
    pos = [_pos(i, [2, 5, 3]) for i in range(40)]                                         # each banked ~+3% on the tight trail…
    done = {ap.key_of(p): [8, 14, 22, 30, 18] for p in pos}                              # …and the coin went on to +30%
    assert of.reaper_replay([2, 5, 3], live, 50.0) == 3.0
    g = ap.grid(pos, done, of.reaper_replay, live, 50.0)
    assert g['n'] == 40 and g['live']['avg'] == 3.0 and g['best']['avg'] > 10 and g['pays'] and g['left'] > 7 and 'PAYS' in ap.words(g)
    few = ap.grid(pos[:10], done, of.reaper_replay, live, 50.0)
    assert few['pays'] is False and '10 of 30' in ap.words(few)
    rug = {ap.key_of(p): [-40, -100.0] for p in pos}                                      # the coins died after we left: tight was right
    g2 = ap.grid(pos, rug, of.reaper_replay, live, 50.0)
    assert g2['pays'] is False and g2['best']['avg'] <= g2['live']['avg'] + ap.EDGE
    assert ap.grid(pos, {}, of.reaper_replay, live, 50.0)['n'] == 0 and 'no exit' in ap.words({})


def test_the_shadow_test_runs_on_whole_moves_and_the_model_can_only_ask_for_one_notch_into_shadow():
    live_tune = {'reaper': {'protectAt': 4.0, 'giveBackPct': 30.0}}
    old = [_pos(i, [2, 5, 3]) for i in range(12)]
    after = {ap.key_of(p): [8, 14, 22, 30, 18] for p in old}
    o = of.judge_candidates({'tune': live_tune}, {'positions': old}, {}, None, 5000.0, after=after)
    c = next(iter(o['candidates'].values()))
    assert c['status'] == 'shadow' and c['key'] in ('giveBackPct', 'protectAt') and c['value'] > of.tune({'tune': live_tune}, 'reaper', c['key'])   # WIDER, found on full paths
    trunc = of.judge_candidates({'tune': live_tune}, {'positions': old}, {}, None, 5000.0)                    # the old truncated replay: nothing wider can win
    assert not any(x['value'] > 30 and x['key'] == 'giveBackPct' for x in (trunc.get('candidates') or {}).values())
    new = [{**_pos(100 + i, [2, 5, 3]), 'closedAt': 6000.0 + i} for i in range(3)]
    o2 = of.judge_candidates(o, {'positions': old + new}, {}, None, 7000.0, after=after)                      # closed, after-path not filed yet: not counted
    assert next(iter(o2['candidates'].values()))['shadow'] == []
    after2 = {**after, **{ap.key_of(p): [9, 20] for p in new}}
    o3 = of.judge_candidates(o2, {'positions': old + new}, {}, None, 9000.0, after=after2)
    o3 = of.judge_candidates(o3, {'positions': old + new}, {}, None, 9100.0, after=after2)                    # …counted once, never twice
    assert len(next(iter(o3['candidates'].values()))['shadow']) == 3
    base = {'tune': live_tune}
    o4, why = of.model_candidate(base, 'giveBackPct', 'up', 12, 'winners banked at +2% then ran', 100.0)
    c4 = next(iter(o4['candidates'].values()))
    assert why is None and c4['value'] == 40.0 and c4['status'] == 'shadow' and c4['evidence']['from'] == 'model coach' and of.tune(o4, 'reaper', 'giveBackPct') == 30.0
    assert of.model_candidate(o4, 'protectAt', 'up', 12, 'x', 101.0)[1]                                        # one candidate at a time
    assert of.model_candidate(base, 'giveBackPct', 'up', 3, 'x', 100.0)[1] and of.model_candidate(base, 'stopLine', 'up', 12, 'x', 100.0)[1]
    assert of.model_candidate({'tune': {'reaper': {'giveBackPct': 70.0}}}, 'giveBackPct', 'up', 12, 'x', 100.0)[1] == 'no notch left that way'

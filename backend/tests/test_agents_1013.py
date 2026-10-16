"""2026-10-13: the owner's volume limits, each desk's own vote, the dial lab, the model's chart-reading record, the 24h local boost."""
import ai_chat as ac
import ai_learn as al
import judge_review as jr
import office_edge as oe
import opportunity as opp
import paper_desk as pd
from trench_kernel import universe as uni


def teardown_function():
    uni.set_band({}); uni.set_trending([])


def test_volume_limits_widen_the_lane_and_pump_trending_skips_the_age_line():
    uni.set_band({'agentMcMax': 5e6, 'agentMaxAgeH': 24, 'agentMinVol1h': 25000, 'agentPumpTrend': 'first'}); uni.set_trending(['T'])
    assert uni.band() == (12000.0, 5e6) and uni.limits()['minVol'] == 25000
    assert uni.in_lane({'mint': 'T', 'mcap': 2e6, 'vol1h': 60000, 'ageH': 200})        # on Pump trending: no age line
    assert not uni.in_lane({'mint': 'X', 'mcap': 2e6, 'vol1h': 60000, 'ageH': 200})    # not trending: 24h line
    assert not uni.in_lane({'mint': 'X', 'mcap': 2e6, 'vol1h': 6000, 'ageH': 2})       # under the volume floor
    uni.set_band({'agentPumpTrend': 'only'}); uni.set_trending(['T'])
    assert not uni.in_lane({'mint': 'X', 'mcap': 50000, 'vol1h': 6000, 'ageH': 2}) and uni.in_lane({'mint': 'T', 'mcap': 50000, 'vol1h': 6000, 'ageH': 2})
    row = {'mint': 'X', 'px': 1, 'vitals': {'mcap': 50000, 'ageH': 2}, 'nums': {'liq': 20000, 'v5': 5000}}
    assert 'Pump trending' in (opp.open_ok(row) or '')
    s_t, parts = opp.open_score({**row, 'mint': 'T'}); s_x, _ = opp.open_score(row)
    assert s_t > s_x and ('🔥 pump trending', uni.TREND_RANK) in parts


def test_unknown_limit_values_fall_back_and_the_controls_list_them():
    assert uni.clean_limits({'agentMaxAgeH': 5, 'agentMinVol1h': 7, 'agentPumpTrend': 'yolo'}) == {'maxAgeH': 6.0, 'minVol': 1000.0, 'trend': 'off', 'minAgeH': 0.0, 'germMax': 15}
    keys = [c['key'] for c in oe.controls({})]
    assert {'agentMaxAgeH', 'agentMinVol1h', 'agentPumpTrend'} <= set(keys) and 10_000_000.0 in oe.OPTIONS['agentMcMax']
    assert oe.clean_policy({'agentPumpTrend': 'first'})['agentPumpTrend'] == 'first'


def test_each_desk_is_scored_on_its_own_vote():
    op = {'tally': {'move5m': 3, 'vpm': 10}, 'sherlock': {'factor': 1.0, 'unknown': []}, 'weather': {'factor': 0.9}, 'trigger': {'state': 'ENTER'},
          'devil': {'objections': [('x', 'STRONG_WARNING', 'w')]}, 'warden': {'size': 0.5}}
    v = jr.votes_of(op)
    assert v == {'tally': 'go', 'sherlock': 'go', 'weather': 'doubt', 'trigger': 'go', 'devil': 'doubt', 'warden': 'doubt'}
    win = {'realPct': 5, 'thesis': {'votes': {'tally': 'go', 'sherlock': 'go', 'weather': 'go', 'trigger': 'go', 'devil': 'doubt', 'warden': 'go'}}}
    loss = {'realPct': -20, 'thesis': {'votes': {'tally': 'go', 'sherlock': 'go', 'weather': 'go', 'trigger': 'go', 'devil': 'doubt', 'warden': 'go'}}}
    r = jr.desk_votes([win, loss] * 3)
    assert r['devil']['n'] == 6 and r['devil']['lone'] == 6 and r['devil']['loneRight'] == 3 and r['devil']['rightPct'] == 50
    assert r['trigger']['go'] == {'n': 6, 'med': -7.5}
    old = {'realPct': 3, 'wx': 'HOSTILE', 'warden': 0.25, 'tag': '🤖 agents · 🎯 ARMED (seat target)'}   # an older trade: what the archive kept
    assert jr.votes_from_pos(old) == {'weather': 'doubt', 'warden': 'doubt', 'trigger': 'doubt'}


def test_dial_lab_says_how_little_the_dial_changes():
    done = [{'tw': 'lean +3.0 ≥ bar 2.0', 'lean': 3.0, 'p5': 4}, {'tw': 'lean -50 under the bar 2.0', 'lean': -50, 'p5': -9}, {'tw': 'lean 2.2 ≥ bar 2.0', 'lean': 2.2, 'p5': -3}]
    r = pd.dial_replay(done)
    assert r['normal']['n'] == 2 and r['chill']['n'] == 1 and r['crazy']['n'] == 2 and r['near'] == 1 and r['calls'] == 3


def test_model_chart_reads_are_graded_and_local_kept_apart():
    b = {}
    b = al.note(b, 'sherlock', 'M1', 'CONTEND', 1.0, 0, phase='LATE_FOMO', ephase='BREAKOUT', src='local')
    b = al.note(b, 'sherlock', 'M2', 'CONTEND', 1.0, 0, phase='EARLY ACCELERATION', ephase='BREAKOUT', src='openrouter')
    b = al.settle(b, {'M1': 0.5, 'M2': 1.2}, al.JUDGE_SEC + 1)
    v = al.vital_record(b)
    assert v['PHASE:LATE']['med'] == -50 and v['SPLIT:MODEL-LATE']['n'] == 1 and v['SRC:LOCAL']['n'] == 1 and v['SRC:CLOUD']['n'] == 1
    assert 'your LATE reads -50%' in al.chart_line(v)


def test_local_boost_runs_faster_for_24h_and_pauses_on_browser_lag():
    s = ac.clean_settings({'localBoost': True, 'now': 1000})
    assert s['localBoostUntil'] == 1000 + ac.BOOST_SEC and ac.clean_settings(s)['localBoostUntil'] == s['localBoostUntil']   # survives a reload
    assert ac.lane_every(s, 2000, [])[0] == ac.BOOST_EVERY
    assert ac.lane_every(s, 2000, [{'fps': 12}])[0] == ac.NORMAL_EVERY                    # a browser reports lag → back to normal
    assert ac.lane_every(s, 2000, [], last_ms=40000)[0] == 80                           # never more than half the time
    assert ac.lane_every(s, 1000 + ac.BOOST_SEC + 1, [])[0] == ac.NORMAL_EVERY          # 24h later it ends by itself
    w = ac.watch_note(ac.watch_note({}, 3600, True, 20000), 3700, False, why='paused')
    assert ac.watch_view(w, s, 2000)['hours'][0] == {'hour': 3600, 'n': 1, 'ok': 1, 'fail': 0, 'avgSec': 20.0, 'paused': 1}


def test_a_cut_off_json_answer_reads_as_its_reply_never_raw_json():
    t = '{"reply":"Courier, archivist and judge show 0 real decisions.","proposals":[{"agent":"desk","kind":"idea","key":"Unk'
    assert ac.parse_improve(t) == ('Courier, archivist and judge show 0 real decisions.', [], [])
    assert ac.parse_improve('plain words') == ('plain words', [], [])


def test_green_exits_by_rule_vs_the_live_trail():
    import after_path as ap
    ps = [{'confirmed': True, 'realPct': 5, 'rule': 'R9 time', 'mint': f'M{i}', 'closedAt': i, 'path': [1, 3, 5]} for i in range(3)]
    done = {ap.key_of(p): [8, 12, 9] for p in ps}
    rows = ap.by_rule(ps, done, lambda f, live, take: max(f) - 2, {}, 50)
    assert rows == [{'rule': 'R9', 'n': 3, 'real': 5.0, 'trail': 10.0, 'left': 5.0}] and 'R9 3×' in ap.rule_words(rows)

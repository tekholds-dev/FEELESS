"""🔁 Agents stop recycling the same losers + 🏛 established volume coins are reviewable + 🧠 every confirmed exit is a lesson (2026-10-11)."""
import agents as ag
import office_edge as oe
import real_learn as rl
import runners


def test_established_mirrors_the_pick_rule():
    assert ag.ESTABLISHED_H == runners.PICK_OLD_H and ag.ESTABLISHED_LIQ == runners.PICK_OLD_LIQ


def test_established_coin_failing_only_top10_counts_as_scanned():
    bonk = {'symbol': 'Bonk', 'safe': False, 'fails': ['Top 10 under 25%'], 'ageH': 10828, 'liq': 439_000}
    r = ag.established(bonk)
    assert r['safe'] is True and r['established'] is True
    assert bonk['safe'] is False   # the caller's row is never mutated


def test_established_never_lifts_other_fails_or_young_or_thin():
    base = {'safe': False, 'fails': ['Top 10 under 25%'], 'ageH': 500, 'liq': 200_000}
    assert ag.established({**base, 'fails': ['Top 10 under 25%', 'Creator not a rugger (suspect)']})['safe'] is False
    assert ag.established({**base, 'fails': ['Dev holds under 5%']})['safe'] is False
    assert ag.established({**base, 'fails': []})['safe'] is False
    assert ag.established({**base, 'ageH': 100})['safe'] is False
    assert ag.established({**base, 'liq': 50_000})['safe'] is False
    assert ag.established({**base, 'ageH': None})['safe'] is False
    assert ag.established({**base, 'safe': None})['safe'] is None   # never scanned stays unscanned


def test_any_confirmed_losing_exit_blocks_a_rebuy_for_6h():
    now = 100_000.0
    closed = [{'mint': 'DOTF', 'confirmed': True, 'realPct': -0.4, 'closedAt': now},
              {'mint': 'WIN', 'confirmed': True, 'realPct': 12.0, 'closedAt': now},
              {'mint': 'UNK', 'confirmed': False, 'realPct': None, 'closedAt': now}]
    lost = oe.note_lost({'OLD': now - oe.FAILED_SEC - 1, 'KEEP': now - 60}, closed, now)
    assert set(lost) == {'DOTF', 'KEEP'}   # loser in, winner free, unconfirmed not judged, expired dropped


def test_confirmed_agent_exit_becomes_a_lesson_once():
    pos = {'mint': 'M', 'sym': 'M', 'confirmed': True, 'realPct': -3.5, 'since': 1000.0, 'closedAt': 1900.0,
           'rule': 'R9 windows used', 'tag': '🤖 agents · best available', 'launch': {'ageH': 200.0}}
    st = rl.note_closed({}, pos, 2000.0)
    p = st['pieces'][0]
    assert p['pct'] == -3.5 and p['holdMin'] == 15.0 and 'age:>7d' in p['k'] and 'tag:🤖' in p['k'] and 'by:engine' in p['k']
    assert rl.note_closed(st, pos, 2000.0) == st   # same coin within 15 min = not twice
    assert rl.note_closed({}, {**pos, 'confirmed': False}, 2000.0) == {}


def test_universe_is_under_200k_live_cap_and_bands_are_context():
    import opportunity as op
    assert ag.AGENT_MAX_MCAP == 200_000 == op.MAX_MCAP and op.MIN_LIQ == ag.CONTROL_MIN_LIQ
    assert ag.in_lane({'mcap': 150_000}) and ag.in_lane({'mcap': 5_000, 'ageH': 0.01}) and ag.in_lane({'mcap': 90_000, 'ageH': 900})   # age is never a veto
    assert not ag.in_lane({'mcap': 200_000}) and not ag.in_lane({'mcap': 0}) and not ag.in_lane({})
    assert ag.trench_band(8_000) == 'NEWBORN MICRO' and ag.trench_band(120_000) == 'MOMENTUM TRENCH' and ag.trench_band(250_000) is None


def test_the_board_shows_the_newest_launches_not_only_the_strongest_reads():
    old = [{'mint': f'o{i}', 'vitals': {'ageH': 500}} for i in range(30)]
    new = [{'mint': f'n{i}', 'vitals': {'ageH': i * 0.1}} for i in range(30)] + [{'mint': 'unk', 'vitals': {}}]
    rows = ag.view_rows(old + new)
    assert [r['mint'] for r in rows[:24]] == [f'o{i}' for i in range(24)]
    assert [r['mint'] for r in rows[24:]] == [f'n{i}' for i in range(24)]   # newest first, age unknown left out
    assert len(ag.view_rows(new[:5] + old)) == 24                             # young coins already in the top are not repeated


def _row(m, **k):
    base = {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'vitals': {'safe': True, 'liq': 40_000, 'rug': 10, 'vol1h': 20_000},
            'nums': {'liq': 40_000, 'c1': 20}, 'trigger': ['wait', 'lean +0.3 under the bar 1.0'], 'why': {'lean': 0.3}, 'chart': {'state': 'RANGE'}, 'objs': []}
    for kk, vv in k.items():
        base[kk] = {**base[kk], **vv} if isinstance(vv, dict) and isinstance(base.get(kk), dict) else vv
    return base


def test_a_lane_launch_seat_is_a_trench_leg_for_the_keeper():
    import arena_prime as ap
    card = {'legs': [], 'cash': 1.0, 'events': []}
    row = {'mint': 'NEW', 'symbol': 'NEW', 'pairAddress': 'PNEW', 'price': 0.001, 'trench': True}
    got = ap.agent_seat(card, row, {}, {'coins': 4}, 1000.0)
    assert got['legs'][0]['trench'] is True and got['legs'][0]['rideOrRug'] is True
    old = ap.agent_seat(card, {**row, 'trench': False}, {}, {'coins': 4}, 1000.0)
    assert 'trench' not in old['legs'][0]
    assert ag.CONTROL_MIN_LIQ == 10_000   # above the keeper's own trench floor ($8K): a seat the agents take is not refused for its pool


def test_the_fill_hands_the_trench_flag_to_the_seat():
    src = open('backend/reputation_service.py').read()
    i = src.index('cur = _prime.agent_seat(cur, {')
    assert "'trench': t_['trench']" in src[i:i + 400]   # $MM was refused at the general $16K floor: the flag never reached the leg


def test_keeper_tops_up_agent_seats_but_never_a_young_pick_ticket():
    import fuse_wallet as fw
    assert fw.agent_seat({'ticket': True, 'bought': {'tag': '🤖 agents · seat floor'}})
    assert not fw.agent_seat({'ticket': True, 'bought': {'tag': '🎟 your pick'}})
    assert not fw.agent_seat({})


def test_judge_rules_on_real_seats_double_and_studies_misses():
    st = {'realPieces': [{'symbol': 'A', 'mint': 'A', 'pct': 12, 'holdMin': 4, 'at': 1}, {'symbol': 'B', 'mint': 'B', 'pct': -22, 'holdMin': 9, 'at': 2},
                         {'symbol': 'C', 'mint': 'C', 'pct': -5, 'holdMin': 20, 'at': 3}, {'symbol': 'D', 'mint': 'D', 'pct': 1, 'at': 4}]}
    j = ag.judge(st)
    assert j['real'] == {'wins': 1, 'losses': 2}
    assert j['score']['tally']['credit'] == 2 and j['score']['devil']['blame'] == 2 and j['score']['trigger']['blame'] == 2   # real counts double
    assert j['trial'] in ('devil', 'trigger') and j['mvp'] == 'tally'
    assert ag.real_ruling({'pct': 30, 'holdMin': 45})['credit'] == 'sherlock'
    st2 = {'done': [{'kind': 'wait', 'p5': 25, 'at': 1, 'tw': 'lean +0.4 under the bar 1.0', 'mint': 'X'},
                    {'kind': 'wait', 'p5': 12, 'at': 2, 'tw': 'lean +0.7 under the bar 1.0', 'mint': 'Y'},
                    {'kind': 'wait', 'p5': 30, 'at': 3, 'tw': '+22% in 5 min — that is the top', 'mint': 'Z'}]}
    m = ag.miss_study(st2)
    assert m[0]['why'] == 'lean # under the bar #' and m[0]['n'] == 2

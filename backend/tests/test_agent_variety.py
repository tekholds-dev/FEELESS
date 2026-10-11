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


def test_agents_hunt_only_new_launches_under_1m():
    assert ag.AGENT_MAX_MCAP == 1_000_000 and ag.AGENT_MAX_AGE_H == 24
    assert ag.under_cap({'mcap': 990_000}) and not ag.under_cap({'mcap': 1_000_000}) and ag.under_cap({})
    assert ag.in_lane({'mcap': 400_000, 'ageH': 2}) and ag.in_lane({'ageH': 0.01})          # a seconds-old launch with no cap yet
    assert not ag.in_lane({'mcap': 400_000, 'ageH': 770})                                    # $QUBT: old and flat — never again
    assert not ag.in_lane({'mcap': 2_000_000, 'ageH': 1}) and not ag.in_lane({'mcap': 400_000})   # over the cap · age unknown


def test_the_board_shows_the_newest_launches_not_only_the_strongest_reads():
    old = [{'mint': f'o{i}', 'vitals': {'ageH': 500}} for i in range(30)]
    new = [{'mint': f'n{i}', 'vitals': {'ageH': i * 0.1}} for i in range(30)] + [{'mint': 'unk', 'vitals': {}}]
    rows = ag.view_rows(old + new)
    assert [r['mint'] for r in rows[:24]] == [f'o{i}' for i in range(24)]
    assert [r['mint'] for r in rows[24:]] == [f'n{i}' for i in range(24)]   # newest first, age unknown left out
    assert len(ag.view_rows(new[:5] + old)) == 24                             # young coins already in the top are not repeated

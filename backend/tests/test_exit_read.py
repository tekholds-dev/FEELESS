"""🧠☠ The model's exit read: one word, graded on what the coin did next, and it moves Reaper only once its own record proves it."""
import exit_read as er


def test_words_from_the_models_answer():
    assert er.word_of({'call': 'EXIT'}) == 'TIGHTEN'
    assert er.word_of({'call': 'HOLD', 'confidence_delta': -0.2}) == 'TIGHTEN'
    assert er.word_of({'call': 'HOLD', 'confidence_delta': 0}) == 'RIDE'
    assert er.word_of({'call': 'HOLD', 'confidence_delta': 0, 'risk_flags': ['dev selling']}) is None   # a named risk is never a ride
    assert er.word_of({'call': 'WATCH'}) is None and er.word_of(None) is None


def test_graded_15_minutes_later_and_renoted_once_per_5_minutes():
    b = er.note({}, 'M', 'TIGHTEN', 1.0, 12, 0)
    b = er.note(b, 'M', 'TIGHTEN', 1.1, 14, 60)          # same word, same coin, inside 5 min → one read
    assert len(b['open']) == 1
    b = er.settle(b, {'M': 0.9}, 100)                    # too soon → waits
    assert b['open'] and not b.get('done')
    b = er.settle(b, {'M': 0.9}, 1000)
    assert b['done'][0]['move'] == -10.0


def test_shadow_until_proven_then_bounded_effects():
    b = {}
    for i in range(er.MIN_N - 1):
        b = er.note(b, f'M{i}', 'TIGHTEN', 1.0, 10, i * 400)
    b = er.settle(b, {f'M{i}': 0.95 for i in range(40)}, 10**6)
    assert not er.record(b)['TIGHTEN']['proven']                          # 19 graded: still shadow
    assert er.effects({'X': {'word': 'TIGHTEN', 'at': 0}}, er.record(b), 10) == {}
    b = er.settle(er.note(b, 'MZ', 'TIGHTEN', 1.0, 10, 0), {'MZ': 0.9}, 10**6)
    rec = er.record(b)
    assert rec['TIGHTEN']['proven'] and rec['TIGHTEN']['med'] <= -er.EDGE_PCT
    assert er.effects({'X': {'word': 'TIGHTEN', 'at': 0}}, rec, 10) == {'X': 'tight'}
    assert er.effects({'X': {'word': 'TIGHTEN', 'at': 0}}, rec, er.FRESH_SEC + 1) == {}   # a stale read does nothing
    assert er.effects({'X': {'word': 'TIGHTEN', 'at': 0}}, rec, 10, on=False) == {}        # owner switch off
    assert er.effects({'X': {'word': 'RIDE', 'at': 0}}, rec, 10) == {}                     # RIDE unproven


def test_a_ride_that_kept_falling_is_never_proven():
    b = {}
    for i in range(30):
        b = er.note(b, f'M{i}', 'RIDE', 1.0, 10, i)
    b = er.settle(b, {f'M{i}': 0.97 for i in range(30)}, 10**6)
    assert not er.record(b)['RIDE']['proven']


def test_reaper_reads_the_cache_only_and_the_model_is_still_advisory():
    import ai_router as air
    assert 'exit' in air.ADVISORY_ROLES and 'reaper' in air.FORBIDDEN_ROLES
    src = open(__import__('office').__file__).read()
    assert 'ai_exit' in src and 'ai_router' not in src   # Reaper takes the read handed to it, never a model call


def test_widen_is_a_red_seat_the_model_reads_as_held_and_it_needs_its_own_record():
    import exit_read as er
    hold = {'call': 'HOLD', 'confidence_delta': 0.05, 'risk_flags': []}
    assert er.word_of(hold, -4.0) == 'WIDEN' and er.word_of(hold, 3.0) == 'RIDE' and er.word_of(hold) == 'RIDE'
    assert er.word_of({'call': 'HOLD', 'confidence_delta': 0.0, 'risk_flags': ['dev selling']}, -4.0) is None
    book = {'done': [{'word': 'WIDEN', 'move': 4.0} for _ in range(er.MIN_N)]}
    rec = er.record(book)
    assert rec['WIDEN']['proven'] and rec['WIDEN']['right'] == 100
    assert er.effects({'M': {'word': 'WIDEN', 'at': 100}}, rec, 150) == {'M': 'widen'}
    assert er.effects({'M': {'word': 'WIDEN', 'at': 100}}, er.record({'done': []}), 150) == {}   # unproven = nothing
    assert er.fresh_words({'M': {'word': 'WIDEN', 'at': 100}}, 150) == {}                      # WIDEN never sets snapshot counts


def test_a_proven_widen_gives_a_red_seat_room_but_never_past_the_cap_or_your_line():
    import office as of
    import exit_read as er
    LEG_ = {'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 1.0, 'at': 1, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}}
    ROW_ = {'mint': 'A', 'symbol': 'A', 'pair': 'PA', 'px': 0.95, 'why': {'lean': 1.0, 'drivers': []}, 'trigger': ['wait', ''], 'devil': ['—', ''], 'nums': {'d5': -1, 'buy': 55, 'liq': 60_000},
            'vitals': {'safe': True, 'rug': 5}}
    base = of.reap([LEG_], [ROW_], {'PA': 0.95}, {}, None, 100)[1][0]['stop']
    w = of.reap([LEG_], [ROW_], {'PA': 0.95}, {}, None, 100, ai_exit={'A': 'widen'})[1][0]['stop']
    assert w < base and -w <= er.WIDEN_MAX
    own = of.reap([{**LEG_, 'ownerLvAt': 50, 'sl': 8}], [ROW_], {'PA': 0.95}, {}, None, 100, ai_exit={'A': 'widen'})[1][0]['stop']
    assert own == -8   # your dragged line wins

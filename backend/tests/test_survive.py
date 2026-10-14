"""🪫 The agents keep working while the owner sleeps: the brake can't lock the card all morning, the regret ledger can't flip-flop, the patience
valve fills an empty seat (and closes itself on a losing record), the build queue is read from the file."""
import capital as cap
import office_edge as oe
import regret as rg


def test_brake_releases_after_three_real_wins_and_halves_not_quarters():
    assert cap.brake(2.1, 5.8, recent=[-5, 3, 8, 2])['on'] is False and cap.brake(2.1, 5.8, recent=[-5, 3, 8, 2])['released']
    b = cap.brake(2.1, 5.8, recent=[4, -9, 2])
    assert b['on'] and '6h high' in b['why']
    assert cap.for_door({'brake': b}, 'ready')['mult'] == cap.BRAKE_MULT == 0.5


def test_regret_note_keeps_the_rest_list_so_a_rollback_rests():
    book = {'open': [], 'done': [], 'tune': {}, 'log': [], 'hold': {'aiWait': 1000.0}}
    b = rg.note(book, 'M', 'taken', 1.0, 1074.0, 'X')
    assert b['hold'] == {'aiWait': 1000.0}


def test_valve_opens_after_ten_minutes_only_for_wait_for_confirmation_and_closes_on_a_losing_record():
    c = [{'mint': 'A', 'status': 'CONTENDING', 'chartWait': True, 'chartCall': 'WAIT FOR CONFIRMATION', 'size': 0.5, 'rank': 150},
         {'mint': 'B', 'status': 'CONTENDING', 'chartWait': True, 'chartCall': 'SKIP', 'size': 0.5, 'rank': 300},
         {'mint': 'C', 'status': 'CONTENDING', 'chartWait': True, 'chartCall': 'WAIT FOR PULLBACK', 'size': 0.5, 'rank': 250}]
    assert oe.valve_fill(c, 1000, 1000 + 300) == []                                   # 5 min: not yet
    assert [x['mint'] for x in oe.valve_fill(c, 1000, 1000 + 601)] == ['A']            # SKIP / PULLBACK never
    assert oe.valve_fill(c, 1000, 2000, last_at=1500) == []                            # one per 15 min
    assert oe.valve_fill(c, 1000, 2000, blocked=('A',)) == []
    lose = [{'tag': '🤖 agents · 🪫 VALVE (empty seat)', 'realPct': -5}] * 12
    assert oe.valve_record(lose)['open'] is False and oe.valve_fill(c, 1000, 2000, rec=oe.valve_record(lose)) == []
    assert oe.valve_record([{'tag': 'x', 'realPct': -5}])['n'] == 0


def test_build_queue_reads_the_file_every_time():
    src = open(__file__.replace('tests/test_survive.py', 'reputation_service.py')).read()
    i = src.index('def _build_state():')
    assert "if _chat.get('build') is None" not in src[i:i + 400]


def test_clone_catches_near_tickers_and_reaper_rides_real_volume():
    import taught_rules as tr
    assert tr.clone({'mint': 'N', 'symbol': 'SpaceX AI'}, traded=[('SPACEX', 'O')])
    assert tr.clone({'mint': 'N', 'symbol': 'Chat GPT'}, traded=[('ChatGPT', 'O')])
    assert tr.clone({'mint': 'N', 'symbol': 'SOL'}, traded=[('SOLAMI', 'O')]) is None        # short tickers never prefix-match
    import office as of
    src = open(of.__file__).read()
    assert 'R10r riding the volume' in src and "not (riding_ and pct > p['peak'] * (1 - RIDE_GIVE / 100))" in src

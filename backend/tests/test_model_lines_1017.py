"""🎯 owner, 2026-10-17: the models get full line access — take / stop / TRAIL on their own trade AND on the agents' coins (never the owner's)."""
import ai_seat as seat
import office as of


def test_parse_reads_trail_and_clamps_it():
    d = seat.parse('{"action":"HOLD","why":"HH/HL holds","tp":60,"sl":12,"trail":90}', [], True)
    assert d['tp'] == 60 and d['sl'] == 12 and d['trail'] == 70
    assert seat.lines_word({'aiTrail': 30}, d) == {'tp': 60, 'sl': 12, 'trail': 70}
    assert 'TRAIL' in seat.lines_why({'trail': 40}, {'aiTrail': 30})


def test_idle_read_can_set_lines_on_a_card_coin():
    d = seat.idle_parse('{"coin":"ABC","view":"HOLD","why":"germ floor","conf":70,"sl":10,"trail":40}', {'ABC': 'M1'})
    assert d['mint'] == 'M1' and d['sl'] == 10 and d['trail'] == 40 and 'tp' not in d


from test_office import leg, trow


def test_a_model_trail_banks_an_agents_coin_and_never_an_owner_pick():
    run = lambda l, px, pos, now: of.reap([l], [trow('A')], {'PA': px}, {'agentTakePct': 500, 'agentScalp': False}, pos, now)
    pos, _, _ = run(leg('A', aiTrail=70), 1.30, None, 3600)
    _, rep, _ = run(leg('A', aiTrail=70), 1.15, pos, 3660)
    assert rep[0]['action'] is None                                                     # the model gave it 70% room: +15% off a +30% peak is kept
    pos, _, _ = run(leg('A', aiTrail=30), 1.30, None, 3600)
    _, rep, _ = run(leg('A', aiTrail=30), 1.15, pos, 3660)
    assert rep[0]['rule'].startswith('R7') and rep[0]['action'] == 'pull'                # 30% room: sold
    pos, _, _ = run(leg('A', aiTrail=40, picked=True), 1.30, None, 3600)
    _, rep, _ = run(leg('A', aiTrail=40, picked=True), 1.15, pos, 3660)
    assert rep[0]['rule'] != 'R7a model trail' and rep[0]['action'] is None              # your pick: notes only


def test_hold_soft_lets_the_models_own_trail_sell(monkeypatch):
    monkeypatch.setattr(of, 'HOLD_SOFT', True)
    run = lambda l, px, pos, now: of.reap([l], [trow('A')], {'PA': px}, {'agentTakePct': 500, 'agentScalp': False}, pos, now)
    pos, _, _ = run(leg('A', aiTrail=30), 1.30, None, 3600)
    _, rep, _ = run(leg('A', aiTrail=30), 1.15, pos, 3660)
    assert rep[0]['action'] == 'pull'
    pos, _, _ = run(leg('A'), 1.30, None, 3600)
    _, rep, _ = run(leg('A'), 1.12, pos, 3660)
    assert rep[0]['action'] is None                                                      # no model trail: the soft exit still waits for TIGHTEN


def test_your_drag_on_a_model_trade_moves_its_line():
    import arena_prime as ap
    card = {'legs': [{'pairAddress': 'P', 'symbol': 'Z', 'aiSeat': True, 'aiTp': 40, 'aiSl': 20, 'units': 1}], 'events': []}
    c = ap.set_leg(card, 'P', tp=80, sl=12, now=10)
    assert c['legs'][0]['aiTp'] == 80 and c['legs'][0]['aiSl'] == 12


def test_owner_chat_words_become_lines():
    assert seat.owner_lines('adjust tp to 100 and sl 20') == {'tp': 100.0, 'sl': 20.0}
    assert seat.owner_lines('trail 35') == {'trail': 35.0} and seat.owner_lines('hold it') == {}


def test_holding_packet_is_slim_and_owner_first():
    pk = seat.packet([{'mint': 'X', 'symbol': 'X'}] * 5, {'symbol': 'H'}, learn={'ownerSays': 'tp 80', 'confidence': 'c', 'ownerStudy': ['long'], 'byModel': {}})
    assert list(pk)[0] == 'OWNER' and 'candidates' not in pk and set(pk['learn']) == {'confidence'}
    assert 'candidates' in seat.packet([{'mint': 'X'}], None)


def test_set_leg_trail_and_its_event():
    import arena_prime as ap
    c = ap.set_leg({'legs': [{'pairAddress': 'P', 'symbol': 'Z', 'units': 1}], 'events': []}, 'P', trail=35, now=5)
    assert c['legs'][0]['aiTrail'] == 35 and 'trail' in c['events'][-1]['why']


def test_reaper_is_calm_on_a_winner_he_holds():
    t = of.calm_words('+9.7% and a lower high — banked before it is given back', 9.7, 14.0)
    assert t.startswith('✅ holding +9.7% (peak +14.0%)') and 'banks only if it keeps fading' in t


def test_top_ups_are_one_trade_on_the_tape():
    import coach
    b = lambda at, usd: {'side': 'buy', 'status': 'filled', 'sig': f's{at}', 'mint': 'M', 'symbol': 'ONE', 'usd': usd, 'at': at, 'agent': True}
    sells = [{'side': 'sell', 'status': 'filled', 'sig': 'x', 'mint': 'M', 'usd': 1, 'at': 50}]
    rows = coach.trade_tape([b(10, 0.5), b(15, 0.2), b(60, 0.3)] + sells, [])
    assert len(rows) == 2 and rows[-1]['buy']['usd'] == 0.7                                # 10 + its 15s top-up = one trade; 60 (after a sale) = a new one


def test_a_line_move_is_graded_like_a_call():
    assert seat.lines_view({'tp': 80}, {'aiTp': 40}) == 'HOLD'                          # more room = "it stays up"
    assert seat.lines_view({'trail': 20}, {'aiTrail': 40}) == 'SELL'                     # tighter = "get out"
    assert seat.lines_view({'tp': 80}, {}) is None                                       # a first line is not a call
    assert 'ownerHoldWins' in seat.HELD_LEARN


def test_desktop_installer_picks_the_server_model_and_falls_back():
    import feeless_mcp as f
    t = f.install_script('http://x/mcp', 'T', model='qwen/qwen3-4b-2507')
    assert 'qwen/qwen3-4b-2507' in t and 'get "$MODEL" -y' in t and 'FALLBACK="google/gemma-4-e2b"' in t and 'model-failed' in t
    assert 'FEELESS_LM_MODEL="$MODEL"' not in t                                         # the hourly re-pull no longer pins the old model


def test_seat_names_the_model_that_holds_it():
    from trench_kernel import positions as ps
    import inspect
    assert ps.MODEL_NAME == {'lan': 'G4', 'local': 'OSSY'} and "'model': MODEL_NAME.get(l.get('aiBy')" in inspect.getsource(ps.card_seats)


def test_duo_update_is_a_stream_kind():
    from trench_kernel import events
    assert 'duo_update' in events.KINDS


def test_desktop_runs_two_parallel_slots():
    import feeless_mcp as f, ai_router as ar
    t = f.install_script('http://x/mcp', 'T')
    assert '--parallel $PAR' in t and 'FEELESS_LM_PAR:-2' in t and 'FEELESS_LM_CTX:-8704' in t
    assert ar.PROVIDERS['lan'][7] == ar.LAN_PARALLEL == 2                                 # the router sends two at once to match


def test_both_models_get_the_voice_and_respect_the_boss():
    for n in ('SYSTEM', 'ADVISE', 'IDLE'):
        assert 'THE BOSS' in getattr(seat, n) and 'witty' in getattr(seat, n)
    import fee_voice
    assert 'THE BOSS' in fee_voice.PERSONA


def test_snapshot_and_final_review():
    line = seat.snapshot_line({'pct': 12.3, 'peak': 20, 'heldMin': 14, 'yourTp': 40}, {'state': 'UPTREND', 'germDist': 4.2, 'hl': 3, 'll': 0}, 'PROTECT · R7', 'BUYERS')
    assert line.startswith('📸 5-min snapshot · +12.3%') and '3 HL / 0 LL' in line and 'Reaper PROTECT' in line
    assert seat.review_parse('{"grade":"b","why":"held the base","lesson":"trail wider on HH/HL"}') == {'grade': 'B', 'why': 'held the base', 'lesson': 'trail wider on HH/HL'}
    assert seat.review_parse('{"grade":"great"}') is None and 'THE BOSS' in seat.REVIEW and seat.SNAP_EVERY == 300

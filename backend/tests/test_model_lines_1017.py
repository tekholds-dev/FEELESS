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

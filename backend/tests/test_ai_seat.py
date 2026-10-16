"""🧠 G4's own seat: the minute decision is parsed safely, paper pays the real swap cost, and on the card the agents only argue."""
import ai_chat as aic
import ai_seat as seat
import office as of
import office_edge as oe


def test_parse_never_acts_on_an_invented_mint_or_an_impossible_action():
    good = seat.parse('ok {"action":"BUY","mint":"AAA","why":"buyers 70%","conf":80,"watch":"germ lost"}', ['AAA', 'BBB'], False)
    assert good == {'action': 'BUY', 'mint': 'AAA', 'why': 'buyers 70%', 'conf': 80, 'watch': 'germ lost'}
    made_up = seat.parse('{"action":"BUY","mint":"ZZZ","why":"moon"}', ['AAA'], False)
    assert made_up['action'] == 'WAIT' and made_up['mint'] == '' and 'not on the list' in made_up['why']
    assert seat.parse('{"action":"BUY","mint":"AAA"}', ['AAA'], True)['action'] == 'HOLD'      # the seat already holds a coin
    assert seat.parse('{"action":"SELL"}', ['AAA'], False)['action'] == 'WAIT'                  # nothing to sell
    assert seat.parse('{"action":"WAIT"}', [], True)['action'] == 'HOLD'
    assert seat.parse('no json here', ['AAA'], False) is None and seat.parse('{"action":"YOLO"}', [], False) is None
    assert seat.parse('{"action":"HOLD","conf":900}', [], True)['conf'] == 100


def test_paper_seat_opens_at_the_live_price_and_pays_the_swap_cost_both_ways():
    px = {'AAA': 1.0}
    b, ev = seat.paper_step({}, {'action': 'BUY', 'mint': 'AAA', 'why': 'x'}, {'AAA': {'symbol': 'A'}}, px.get, 100)
    assert ev == {'kind': 'buy', 'symbol': 'A', 'px': 1.0} and b['open']['entry'] == 1.0
    px['AAA'] = 1.10
    b, ev = seat.paper_step(b, {'action': 'HOLD', 'why': ''}, {}, px.get, 160)
    assert ev is None and round(b['open']['peak'], 1) == 10.0
    b, ev = seat.paper_step(b, {'action': 'SELL', 'why': 'faded'}, {}, px.get, 220)
    assert ev['kind'] == 'sell' and b['open'] is None and b['closed'][0]['pct'] == round(10.0 - 2 * seat.PAPER_COST_PCT, 2)
    assert seat.record(b['closed'])['n'] == 1 and seat.record([])['n'] == 0
    assert 'after costs' in seat.record_words(seat.record(b['closed']))


def test_due_and_fresh_and_packet():
    assert seat.due(0, 60) and not seat.due(100, 130)
    assert seat.fresh({'at': 100}, 200) and not seat.fresh({'at': 100}, 100 + seat.FRESH_SEC + 1) and not seat.fresh(None, 1)
    assert seat.packet([], None)['yourSeat'] == 'EMPTY'
    h = seat.held_row({'symbol': 'A', 'mint': 'AAA', 'entry': 1.0, 'at': 0}, 1.2, 600, [{'rule': 'R7', 'pct': 20.0, 'why': 'trail'}])
    assert h['pct'] == 20.0 and h['heldMin'] == 10.0 and h['pressure'][0].startswith('R7 at +20.0%')


def test_the_owner_turns_the_seat_and_the_scale_out_on_in_the_limits():
    assert oe.clean_policy({})['agentAiSeat'] == 'off' and oe.clean_policy({'agentAiSeat': 'real'})['agentAiSeat'] == 'real'
    assert oe.clean_policy({'agentAiSeat': 'yolo'})['agentAiSeat'] == 'off'
    assert oe.policy({'agentScale': '20/50'})['scale'] == (20.0, 50.0) and oe.policy({'agentScale': 'off'})['scale'] is None


def test_on_g4s_seat_the_agents_only_argue_and_a_pulled_pool_still_sells(monkeypatch):
    monkeypatch.setattr(of, 'SCALE_AT', 10.0)
    leg = {'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 1.0, 'at': 1, 'liq': 60_000, 'liqNow': 60_000,
           'bought': {'tag': '🤖 🧠 G4 seat'}, 'aiSeat': True}
    row = {'mint': 'A', 'symbol': 'A', 'pair': 'PA', 'px': 1.11, 'why': {'lean': 2.0, 'drivers': []}, 'trigger': ['wait', ''], 'devil': ['—', ''],
           'nums': {'d5': 4, 'buy': 60, 'liq': 60_000}, 'vitals': {'safe': True, 'rug': 5}, 'launch': {'ageH': 0.03}}
    cfg = {'agentTakePct': 50, 'agentScalp': False}
    pos, rep, _ = of.reap([leg], [row], {'PA': 1.11}, cfg, None, 100)            # a young coin at +11%: R6y would sell it all
    assert rep[0]['action'] is None and "G4's seat" in rep[0]['evidence']
    assert pos['A']['g4'] and pos['A']['pressure'][-1]['rule'] in ('R6y', 'R6h')   # … the take, filed as pressure G4 reads next minute
    _, rep, _ = of.reap([{**leg, 'liqNow': 10_000}], [row], {'PA': 1.11}, cfg, pos, 160)
    assert rep[0]['action'] == 'pull' and rep[0]['rule'].startswith('R1')      # a pulled pool still sells it


def test_g4_minute_thoughts_reach_the_activity_pane():
    rows = aic.activity(g4=[{'at': 5, 'mode': 'paper', 'action': 'BUY', 'symbol': 'A', 'mint': 'AAA', 'why': 'buyers 70%', 'conf': 70,
                             'vitals': {'cap': 40000, 'buyers': 70}, 'pressure': ['R7 at +5%'], 'qwen': 'CAUTION'}])
    g = [r for r in rows if r['kind'] == 'g4'][0]
    assert g['title'].startswith('G4 BUY $A') and g['tone'] == 'ok' and 'cap 40000' in g['vitals'] and g['qwen'] == 'CAUTION'


def test_g4_and_the_mac_model_take_turns_and_each_has_its_own_record():
    assert seat.turn([], 'lan', 'local') == ('lan', 'local')
    log = [{'by': 'lan', 'action': 'BUY', 'symbol': 'A', 'why': 'buyers 70%', 'model': 'Vega'}]
    assert seat.turn(log, 'lan', 'local') == ('local', 'lan')                       # the other model decides next
    assert seat.turn(log + [{'by': None, 'action': 'NO ANSWER'}], 'lan', 'local') == ('local', 'lan')   # a missed minute does not count as a turn
    assert seat.partner_of(log, 'local') == {'model': 'Vega', 'action': 'BUY', 'symbol': 'A', 'why': 'buyers 70%'} and seat.partner_of(log, 'lan') is None
    assert seat.packet([], None, None, {'action': 'BUY'})['partner'] == {'action': 'BUY'}
    px = {'A': 1.0}
    b, _ = seat.paper_step({}, {'action': 'BUY', 'mint': 'A', 'why': ''}, {'A': {'symbol': 'A'}}, px.get, 0, 'lan')
    px['A'] = 0.9
    b, _ = seat.paper_step(b, {'action': 'SELL', 'why': ''}, {}, px.get, 60, 'local')
    assert set(seat.by_model(b['closed'])) == {'lan'}                                  # the trade is the opener's


def test_gpt_oss_channel_tags_never_reach_the_parser_or_the_chat():
    import ai_router as ar
    raw = '<|channel|>analysis thinking<|end|><|start|>assistant<|channel|>final <|constrain|>JSON<|message|>{"action":"WAIT"}'
    assert ar.harmony_clean(raw) == '{"action":"WAIT"}' and ar.harmony_clean('hi there') == 'hi there' and ar.harmony_clean(None) == ''


def test_the_owner_s_one_time_switch_puts_the_seat_on_paper_once(monkeypatch):
    import asyncio
    import reputation_service as rs
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'realCfg': {'agentAiSeat': 'off'}}})
    assert asyncio.run(rs._g4seat_fix_1016(100)) is True
    pr = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    assert pr['realCfg']['agentAiSeat'] == 'paper' and 'agentAiSeat' in pr['realOwnerSet']
    assert asyncio.run(rs._g4seat_fix_1016(200)) is False                     # once only: the owner's later change stands


def test_a_buy_by_symbol_or_mint_prefix_maps_to_the_listed_coin_only():
    mints, syms = ['AAAmintXYZ123456', 'BBBmint'], {'PEPE': 'AAAmintXYZ123456', 'DOG': 'BBBmint'}
    assert seat.parse('{"action":"BUY","mint":"$pepe"}', mints, False, syms)['mint'] == 'AAAmintXYZ123456'
    assert seat.parse('{"action":"BUY","mint":"AAAmintXYZ"}', mints, False, syms)['mint'] == 'AAAmintXYZ123456'
    assert seat.parse('{"action":"BUY","mint":"SHIB"}', mints, False, syms)['action'] == 'WAIT'   # not on the list: never bought

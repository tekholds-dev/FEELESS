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
    assert seat.turn(log, 'lan', 'local') == ('lan', 'local')                         # a BUY that never got seated is not a turn
    assert seat.turn(log, 'lan', 'local', holding=True, holder='lan') == ('lan', 'local')   # the opener runs its own trade to the exit
    assert seat.turn(log, 'lan', 'local', holding=True, holder='local', opener='lan') == ('local', 'lan')
    assert seat.turn(log, 'lan', 'local', opener='lan') == ('local', 'lan')           # seat empty again → the other model hunts
    assert seat.turn(log, 'lan', 'local', opener='local') == ('lan', 'local')
    talk = [{'by': 'local', 'talk': True, 'model': 'OSSY', 'view': 'SELL', 'why': 'buyers 40%', 'at': 50, 'conf': 60}]
    assert seat.talk_of(talk, 'lan')['says'] == 'SELL' and seat.talk_of(talk, 'local') is None and seat.talk_of(talk, 'lan', since=60) is None
    assert seat.packet([], {'symbol': 'A'}, says={'says': 'SELL'})['partnerSays'] == {'says': 'SELL'}
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


def test_the_code_lab_asks_for_a_live_preview_and_pulls_html_out_of_any_answer():
    import ai_play as p
    assert '"preview"' in p.ASK and 'RUNS' in p.PREVIEW_ASK
    h = p.html_of('sure:\n```html\n<button id=b>BUY</button><script>b.onclick=()=>1</script>\n```')
    assert h.startswith('<!doctype html>') and 'Content-Security-Policy' in h and '<button id=b>BUY</button>' in h
    assert p.html_of('just words') is None


def test_each_machine_gets_its_own_name_in_the_fee_prompt():
    import feeless_mcp as f
    assert f.fee_prompt().startswith('You are OSSY') and f.fee_prompt('G4').startswith('You are G4') and '{NAME}' not in f.fee_prompt()


def test_a_question_about_our_trades_or_a_named_coin_never_searches_the_web():
    import ai_chat as a
    assert not a.should_search('currently running over 100% with elon what have you guys learn from this trade specifically?', ['ELON'])
    assert not a.should_search("no what moves did you learn from my trade, we dont need a web search lol")
    assert a.should_search('who won the broncos game last night') and a.should_search('search the news on solana today')
    assert a.named_syms('elon and $bubble', ['ELON']) == ['BUBBLE', 'ELON'] and a.named_syms('hello there', ['ELON']) == []


def test_the_router_tries_models_in_the_order_it_is_given():
    import ai_router as ar
    assert ar.route_order(('local', 'lan'), ['lan', 'local', 'groq']) == ['local', 'lan']
    assert ar.route_order(None, ['lan', 'local']) == ['lan', 'local'] and ar.route_order(('xai',), ['lan']) == []


def test_a_masked_or_missing_mint_still_buys_the_one_coin_its_own_why_names():
    syms = {'RUNE': 'RUNEMINT111', 'DOGX': 'DOGXMINT222'}
    # OSSY copied the address; the router masks long runs as ••• — its why names RUNE (live 2026-10-16: every OSSY buy was refused)
    d = seat.parse('{"action":"BUY","mint":"•••","why":"RUNE rank104, +3.2% 5m, 58 buyers"}', list(syms.values()), False, syms)
    assert d['action'] == 'BUY' and d['mint'] == 'RUNEMINT111'
    assert seat.parse('{"action":"BUY","coin":"$dogx","why":"x"}', list(syms.values()), False, syms)['mint'] == 'DOGXMINT222'
    two = seat.parse('{"action":"BUY","mint":"","why":"RUNE or DOGX"}', list(syms.values()), False, syms)
    assert two['action'] == 'WAIT'                                                      # names two coins: never guessed
    assert seat.parse('I would WAIT here, nothing clean', [], False)['action'] == 'WAIT'  # no JSON, a plain action word
    assert 'mint' not in seat.packet([{'symbol': 'RUNE', 'mint': 'RUNEMINT111'}], None)['candidates'][0]   # the model is shown symbols only


def test_when_no_model_answers_the_agents_decide_the_seat():
    c = [{'symbol': 'A', 'mint': 'AAA', 'status': 'CONTENDING', 'trigger': 'ARM'}, {'symbol': 'B', 'mint': 'BBB', 'status': 'READY', 'trigger': 'ENTER'}]
    assert seat.agents_pick(c)['mint'] == 'BBB'
    assert seat.backup(c, False) == {**seat.backup(c, False), 'action': 'BUY', 'mint': 'BBB'}
    assert seat.backup(c[:1], False)['action'] == 'WAIT' and seat.backup(c, True)['action'] == 'HOLD'
    assert seat.turn([{'by': 'agents', 'action': 'BUY'}], 'lan', 'local') == ('lan', 'local')   # an agents' backup buy is nobody's turn



def test_each_lm_model_takes_at_most_four_background_calls_a_minute():
    import ai_router as air
    assert not air.minute_cap([100, 110, 120], 130, 4) and air.minute_cap([100, 110, 120, 125], 130, 4)
    assert not air.minute_cap([10, 20, 30, 40], 130, 4)          # older than a minute: free again


def test_activity_is_never_dead_card_moves_your_studied_moves_and_the_judges_lessons_all_log():
    rows = aic.activity(card=[{'at': 10, 'kind': 'agent', 'why': '🤖 agents filled seat 2 with $ABC'}],
                        moves=[{'at': 9, 'kind': 'pick', 'symbol': 'X', 'pct': 12.0, 'result': 'good'}, {'at': 8, 'kind': 'stopped', 'symbol': 'Y'}],
                        reviews=[{'at': 7, 'sym': 'Z', 'pct': -9.0, 'lossClass': 'BAD TIMING', 'desk': 'trigger', 'change': 'Trigger: wait for the pullback'}],
                        g4=[{'at': 6, 'model': 'AGENTS', 'mode': 'real', 'action': 'WAIT', 'why': 'no model answered'}])
    kinds = [r['kind'] for r in rows]
    assert kinds == ['card', 'you', 'you', 'learn', 'g4']
    assert rows[0]['who'] == 'agents' and rows[1]['title'] == 'your pick $X → +12.0% since' and rows[1]['tone'] == 'ok'
    assert 'being watched' in rows[2]['title'] and 'pullback' in rows[3]['sub'] and rows[4]['title'].startswith('AGENTS WAIT')


def test_each_model_learns_from_its_own_its_partners_the_owners_and_the_agents_real_trades():
    les = seat.lessons([{'aiBy': 'lan', 'sym': 'A', 'realPct': 12.0, 'rule': 'R7'}, {'aiBy': 'local', 'sym': 'B', 'realPct': -5.0}], 'owner 3 trades', 'agents 9 trades')
    b = seat.learn_block(les, 'local', 'lan', {'lan': 'G4', 'local': 'OSSY'}.get)
    assert '1 trades, 0% won' in b['you'] and '$B -5.0%' in b['you'] and b['partner'].startswith('G4: 1 trades, 100% won') and '$A +12.0% (R7)' in b['partner']
    assert b['owner'] == 'owner 3 trades' and b['agents'] == 'agents 9 trades'
    assert seat.packet([], None, learn=b)['learn'] == b and 'BRAG' in seat.SYSTEM
    assert seat.learn_block({}, 'lan', 'local')['you'] == 'no real trades yet'


def test_the_holding_model_sets_its_own_take_and_stop_and_reaper_obeys_them():
    d = seat.parse('{"action":"HOLD","why":"x","tp":40,"sl":90}', [], True)
    assert d['tp'] == 40.0 and d['sl'] == 44.0                       # the −45% floor stays under any stop it sets
    assert 'tp' not in seat.parse('{"action":"WAIT","why":"x","tp":40}', [], False)
    import office as of
    assert 'R5m' in of.G4_HARD and 'R6m' in of.G4_HARD
    assert seat.held_row({'symbol': 'A', 'entry': 1.0, 'aiTp': 40, 'aiSl': 15}, 1.1, 0)['yourTp'] == 40


def test_the_holder_can_trim_part_of_its_trade():
    d = seat.parse('{"action":"TRIM","pct":40,"why":"bank some","sl":20}', [], True)
    assert d['action'] == 'TRIM' and d['trim'] == 50 and d['sl'] == 20.0
    assert seat.parse('{"action":"TRIM","pct":80}', [], False)['action'] == 'WAIT'   # nothing held = nothing to trim


def test_each_model_talks_in_its_own_voice_and_only_about_the_trade_it_holds():
    import ai_seat as seat
    assert 'OSSY' in seat.sys_for(seat.SYSTEM, 'local') and 'laid back' in seat.sys_for(seat.SYSTEM, 'local')
    assert 'Corleone' in seat.sys_for(seat.ADVISE, 'lan') and 'GODFATHER' in seat.sys_for(seat.ADVISE, 'lan')
    pk = seat.packet([], {'symbol': 'MAKERS', 'pct': 20}, partner={'model': 'G4', 'action': 'SELL', 'symbol': 'QUID', 'why': 'QUID ran'},
                     learn={'ownerHoldWins': 'boss held $QUID +15%'})
    assert '$MAKERS' in pk['NOW'] and 'pastLessons' in pk and 'learn' not in pk
    assert 'why' not in pk['partner']   # the partner's words on ANOTHER coin never sit beside this trade


def test_a_models_full_line_is_never_cut():
    import ai_seat as seat
    long_ = 'held the base, ' * 30
    d = seat.parse('{"action":"HOLD","why":"%s"}' % long_, [], True)
    assert len(d['why']) >= len(long_.strip()) - 1 and 'under 160 chars' not in seat.SYSTEM + seat.ADVISE + seat.IDLE


def test_a_hunting_turn_passes_only_when_the_hunter_really_answered():
    import ai_seat as seat
    log = [{'by': 'agents', 'action': 'WAIT', 'at': 10 + i} for i in range(9)]
    assert seat.hunt_answers(log, 'lan', 0) == 0   # G4 could not answer: its turn stays
    log += [{'by': 'lan', 'action': 'WAIT', 'at': 20 + i} for i in range(5)] + [{'by': 'lan', 'action': 'TALK', 'talk': True, 'at': 30}]
    assert seat.hunt_answers(log, 'lan', 0) == seat.HUNT_PASS_N


def test_g4_says_it_in_four_sentences_and_a_cut_json_answer_never_shows_raw():
    import ai_seat as seat
    story = '{"action":"HOLD","coin":"","why":"Godfather said hold. I hold Glow at 8%. No lower low. Germ intact. I watch the 1m. I don\'t panic. I wait'
    d = seat.parse(story, [], True)
    assert d['action'] == 'HOLD' and '{' not in d['why'] and d['why'].count('.') <= 4 and not d['why'].startswith('Godfather said hold')   # 🎩 he said nothing that minute: the made-up quote is dropped
    assert seat.short_why('A. B. C. D. E. F.') == 'A. B. C. D.'


def test_your_chat_lines_never_scroll_out_of_the_chat():
    import ai_seat as seat
    rows = [{'at': 1, 'by': 'owner', 'why': 'hold till lower lows'}] + [{'at': 10 + i, 'by': 'lan', 'why': f'hold {i}'} for i in range(40)]
    w = seat.chat_window(rows, n=24)
    assert w[0]['why'] == 'hold till lower lows' and len(w) == 25 and [r['at'] for r in w] == sorted(r['at'] for r in w)


def test_the_partner_advises_on_the_holders_trade_never_its_own():
    import ai_seat as seat
    pk = seat.packet([], {'symbol': 'Glow', 'pct': 28}, record='3 trades', partner={'model': 'OSSY', 'action': 'HOLD', 'symbol': 'Glow', 'why': 'x'})
    a = seat.advise_packet(pk, 'G4', 'OSSY')
    assert "G4 holds $Glow" in a['NOW'] and 'NOT yours' in a['NOW'] and 'yourSeat' not in a and 'yourRecord' not in a and a['G4Seat']['symbol'] == 'Glow'
    assert 'partner' not in a and 'never your trade' in seat.ADVISE


def test_a_model_adopts_the_agents_seat_on_the_coin_it_picked_never_a_second_buy():
    import ai_seat as seat
    legs = [{'mint': 'ON', 'symbol': 'onboard', 'units': 10}, {'mint': 'MK', 'symbol': 'MAKERS', 'units': 5, 'picked': True}]
    assert seat.adoptable(legs, 'ON')['symbol'] == 'onboard'
    assert seat.adoptable(legs, 'MK') is None                                    # your pick is never taken over
    assert seat.adoptable(legs + [{'mint': 'X', 'aiSeat': True, 'units': 1}], 'ON') is None   # one model seat at a time


def test_the_agents_read_the_trail_the_models_really_use():
    import ai_seat as seat
    log = [{'action': 'LINES', 'by': 'lan', 'at': 100, 'lines': {'trail': t}} for t in (30, 35, 40, 45, 35)] + [{'action': 'LINES', 'by': 'owner', 'at': 100, 'lines': {'trail': 90}}]
    assert seat.models_trail(log, 200) == 35 and seat.models_trail(log[:3], 200) is None


def test_the_models_bank_a_sale_for_up_to_three_rounds():
    import ai_seat as seat, arena_prime as ap
    d = seat.parse('{"action":"TRIM","pct":50,"why":"skim","bank":5}', [], True)
    assert d['action'] == 'TRIM' and d['bank'] == 3                                  # capped at 3 rounds
    assert 'bank' not in seat.parse('{"action":"HOLD","why":"x","bank":2}', [], True)
    c = ap.park_bank({'cash': 1.0, 'holdCashUsd': 0.2, 'rounds': 7, 'events': []}, 0.5, 2, 100, 'X', 'OSSY')
    assert c['holdCashUsd'] == 0.7 and c['skimPark'][-1]['hold'] == 2 and c['skimPark'][-1]['round'] == 7
    assert ap.park_bank({'cash': 1.0}, 0.5, 0, 100) == {'cash': 1.0}


def test_the_models_predictions_are_parsed_per_coin_for_grading():
    import ai_seat as seat
    d = seat.parse('{"action":"HOLD","why":"x","pred":12,"preds":{"ABC":-8,"ZZZ":400,"NOPE":5}}', ['MA', 'MZ'], True, {'ABC': 'MA', 'ZZZ': 'MZ'})
    assert d['preds'] == {'_self': 12.0, 'MA': -8.0, 'MZ': 300.0}                   # unknown symbols dropped, wild calls capped


def test_agents_only_take_a_coin_a_model_backed_and_the_newest_word_wins():
    from ai_seat import duo_backs
    now = 10_000.0
    assert duo_backs([], [], 'M', now) == (False, 'no model has backed it')
    assert duo_backs([{'at': now - 60, 'by': 'G4', 'action': 'BUY', 'mint': 'M'}], [], 'M', now)[0] is True
    assert duo_backs([], [{'at': now - 300, 'prov': 'lan', 'mint': 'M', 'pred': 6}], 'M', now)[0] is True
    assert duo_backs([], [{'at': now - 300, 'prov': 'lan', 'mint': 'M', 'pred': 2}], 'M', now)[0] is False   # +2 is not backing
    # a newer SELL / down call cancels an older BUY
    ok, why = duo_backs([{'at': now - 600, 'by': 'G4', 'action': 'BUY', 'mint': 'M'}], [{'at': now - 60, 'prov': 'local', 'mint': 'M', 'pred': -8}], 'M', now)
    assert ok is False and '-8' in why
    assert duo_backs([{'at': now - 5000, 'by': 'G4', 'action': 'BUY', 'mint': 'M'}], [], 'M', now)[0] is False   # stale
    assert duo_backs([{'at': now - 60, 'by': 'OSSY', 'action': 'HOLD', 'view': 'SELL', 'mint': 'M'}], [], 'M', now)[0] is False


def test_a_models_seat_with_no_free_cash_trims_the_agents_biggest_coin_never_your_pick():
    import arena_prime as ap
    card = {'cash': 0.0, 'legs': [
        {'pairAddress': 'A', 'symbol': 'A', 'units': 100, 'entry': 0.01, 'costUsd': 1.0},
        {'pairAddress': 'B', 'symbol': 'B', 'units': 300, 'entry': 0.01, 'costUsd': 3.0, 'picked': True},
        {'pairAddress': 'C', 'symbol': 'C', 'units': 200, 'entry': 0.01, 'costUsd': 2.0}]}
    c, got, sym = ap.make_room(card, 1.0, {'A': 0.01, 'B': 0.01, 'C': 0.01}, None, 100, 4, 'OSSY')
    assert sym == 'C' and 0.4 < got <= 0.5 and c['cash'] == round(got, 6)
    assert next(l for l in c['legs'] if l['symbol'] == 'B')['units'] == 300   # your pick is never trimmed
    assert next(l for l in c['legs'] if l['symbol'] == 'C')['trimAt'] == 100
    only_yours = {'cash': 0, 'legs': [card['legs'][1]]}
    assert ap.make_room(only_yours, 1.0, {'B': 0.01}, None, 100, 4)[1] == 0


def test_a_model_never_quotes_the_godfather_when_he_said_nothing():
    import ai_seat as s
    t = 'Godfather said hold, so we hold. Germ floor 4% under, buyers 61%. Riding to the take.'
    assert 'said hold' not in s.short_why(t)
    assert 'Germ floor' in s.short_why(t)
    assert 'said hold' in s.short_why(t, spoke=True)
    assert s.short_why('Godfather, I am holding: germ 4% under.') .startswith('Godfather, I am holding')
    assert 'boss wants' not in s.short_why('The boss wants us to hold. Tape is green.')


def test_streak_brake_and_owner_lines_expire():
    import ai_seat as s
    assert s.streak_brake([5, -1, -2, -3]).startswith('last 3 real trades')
    assert s.streak_brake([-1, -2, 4]) is None and s.streak_brake([-1, -2]) is None
    held = {'at': 1000}
    line = {'at': 1100, 'mint': 'M', 'by': 'owner', 'why': 'hold'}
    assert s.owner_line_live(line, held, [], 1200)
    assert not s.owner_line_live({**line, 'at': 500}, held, [], 1200)                       # said in an earlier trade of this coin
    assert not s.owner_line_live(line, held, [], 1100 + s.OWNER_LINE_SEC + 1)              # too old
    replies = [{'at': 1150, 'mint': 'M', 'model': 'G4'}, {'at': 1160, 'mint': 'M', 'model': 'OSSY'}]
    assert not s.owner_line_live(line, held, replies, 1200)                                # answered twice already


def test_a_model_never_pulls_a_stop_into_the_price_and_line_jitter_is_ignored():
    import ai_seat as s
    leg = {'aiSl': 12.0, 'aiTrail': 35.0}
    assert s.line_change(leg, {'aiSl': 3}, pct_now=-2.0) == {'aiSl': 8.0}          # −3% asked at −2% → the −8% floor ($Normie / $BACKERS)
    assert s.line_change({}, {'aiSl': 9}, pct_now=-7.0) == {'aiSl': 11.0}            # never closer than 4 points under the live %
    assert s.line_change(leg, {'aiTrail': 30}, pct_now=1.0) == {}                   # 35 ↔ 30 every minute is noise
    assert s.line_change(leg, {'aiTrail': 45, 'aiTp': 60}, pct_now=1.0) == {'aiTrail': 45.0, 'aiTp': 60.0}
    assert s.parse('{"action": "HOLD", "sl": 3}', [], holding=True).get('sl') == 8.0

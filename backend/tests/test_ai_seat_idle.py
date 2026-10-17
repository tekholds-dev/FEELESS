import ai_seat as s


def test_lines_word_keeps_only_changed_lines():
    assert s.lines_word({'aiTp': 40, 'aiSl': 20}, {'tp': 40, 'sl': 15}) == {'sl': 15}
    assert s.lines_word({}, {'tp': 30}) == {'tp': 30}
    assert s.lines_word({'aiTp': 30}, {'action': 'HOLD'}) == {}


def test_lines_why_reads_set_and_moved():
    assert s.lines_why({'tp': 30}) == 'set TP +30%'
    assert s.lines_why({'sl': 15}, {'aiSl': 25}) == 'moved SL −25% → −15%'


def test_idle_turn_alternates():
    assert s.idle_turn([], 'lan', 'local') == 'lan'
    assert s.idle_turn([{'idle': True, 'by': 'lan'}], 'lan', 'local') == 'local'
    assert s.idle_turn([{'idle': True, 'by': 'local'}, {'by': 'lan'}], 'lan', 'local') == 'lan'


def test_idle_parse_needs_a_coin_on_the_card():
    syms = {'BONK': 'm1', 'WIF': 'm2'}
    assert s.idle_parse('{"coin":"$BONK","view":"sell","why":"sellers lead","conf":70}', syms) == {'view': 'SELL', 'mint': 'm1', 'why': 'sellers lead', 'conf': 70}
    assert s.idle_parse('{"coin":"","view":"HOLD","why":"WIF buyers 70%"}', syms)['mint'] == 'm2'
    assert s.idle_parse('{"coin":"PEPE","view":"HOLD","why":"x"}', syms) is None
    assert s.idle_parse('{"coin":"BONK","view":"BUY"}', syms) is None


def test_recent_ai_buys_reads_model_fills_only():
    ev = [{'kind': 'agent', 'move': 'fill', 'mint': 'a', 'at': 100, 'why': '🤖 agents filled seat 2 of 4 with $1 — 🧠 OSSY: buyers 70'},
          {'kind': 'agent', 'move': 'fill', 'mint': 'b', 'at': 100, 'why': '🤖 agents filled seat 3 of 4 with $X — ARMED'},
          {'kind': 'agent', 'move': 'fill', 'mint': 'c', 'at': 100 - 7 * 3600, 'why': '🧠 G4: old'}]
    assert s.recent_ai_buys(ev, 200) == {'a'}


def test_cook_holds_an_early_sell_unless_really_losing():
    d = {'action': 'SELL', 'why': 'move5m -7'}
    assert s.cook(d, {'heldMin': 0.6, 'pct': 0.7})['action'] == 'HOLD'
    assert s.cook(d, {'heldMin': 0.6, 'pct': -12})['action'] == 'SELL'
    assert s.cook(d, {'heldMin': 5, 'pct': 0.7})['action'] == 'SELL'
    assert s.cook({'action': 'HOLD'}, {'heldMin': 1, 'pct': 0})['action'] == 'HOLD'


def test_germ_rank_orders_floor_first():
    assert s.germ_rank(4, 15) == 0 and s.germ_rank(30, 15) == 1 and s.germ_rank(None, 15) == 2 and s.germ_rank(-2, 15) == 1


def test_recent_ai_syms():
    ev = [{'kind': 'agent', 'move': 'fill', 'symbol': 'GTA6', 'at': 100, 'why': '🧠 OSSY: x'}]
    assert s.recent_ai_syms(ev, 200) == {'GTA6'}


def test_structure_hold_keeps_a_base_on_slow_volume():
    d = {'action': 'SELL', 'why': 'volume slow'}
    assert s.structure_hold(d, {'pct': -1}, {'germDist': 6})['action'] == 'HOLD'
    assert s.structure_hold(d, {'pct': 1}, {'germ5Dist': 9})['action'] == 'HOLD'
    assert s.structure_hold(d, {'pct': 1}, {'hl': 3, 'll': 0})['action'] == 'HOLD'
    assert s.structure_hold(d, {'pct': 1}, {'hl': 3, 'll': 1})['action'] == 'SELL'          # base broke
    assert s.structure_hold(d, {'pct': 1}, {'germDist': 6}, sellers=True)['action'] == 'SELL'  # sellers lead
    assert s.structure_hold(d, {'pct': -12}, {'germDist': 6})['action'] == 'SELL'           # really losing
    assert s.structure_hold(d, {'pct': 1}, {'germDist': 30})['action'] == 'SELL'


def test_chart_view_reads_both_lenses():
    v = s.chart_view({'germDist': 4.2, 'germ5Dist': 11, 'state': 'PULLBACK', 'hl': 2, 'll': 0})
    assert v['germ1m'] == 4.2 and v['germ5m'] == 11 and v['higherLows'] == 2


def test_snapshot_field_is_line():
    import ai_snapshot as snp
    r = snp.snapshot({'src': 'candles', 'rows': [[i, 1, 1, 1, 1 + i / 100, 1] for i in range(5)]})
    assert r['line']


def test_merge_log_keeps_a_line_written_while_the_model_thought():
    before = [{'at': 1, 'by': 'lan', 'action': 'HOLD', 'why': 'a'}]
    disk = before + [{'at': 2, 'by': 'owner', 'action': 'TALK', 'why': 'hold macca'}]
    ours = before + [{'at': 3, 'by': 'local', 'action': 'HOLD', 'why': 'b'}]
    m = s.merge_log(ours, disk)
    assert [r['at'] for r in m] == [1, 2, 3]

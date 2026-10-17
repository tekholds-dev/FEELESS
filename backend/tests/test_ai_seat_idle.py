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

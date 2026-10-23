import pytest
import launch_cat as lc

ROW = {'id': 'openai/gpt-oss-20b', 'name': 'gpt-oss-20b', 'context_length': 131072, 'pricing': {'prompt': '0.000000018', 'completion': '0.00000009'},
       'supported_parameters': ['reasoning', 'response_format', 'tools'], 'architecture': {'input_modalities': ['text']}, 'benchmarks': {'artificial_analysis': {'intelligence_index': 52}}}
BIG = {'id': 'x/vision-pro', 'name': 'Vision Pro', 'context_length': 200000, 'pricing': {'prompt': '0.000003', 'completion': '0.000015'},
       'architecture': {'input_modalities': ['text', 'image']}}


def test_slim_categorizes_and_prices_a_decision():
    r = lc.slim(ROW)
    assert r['inUsd'] == 0.018 and r['outUsd'] == 0.09
    assert set(r['cats']) >= {'degen', 'trading', 'thinking', 'reasoning'} and 'meta' not in r['cats']
    assert r['perDecision'] == round((0.018 * 1800 + 0.09 * 220) / 1e6, 6)
    assert lc.slim(BIG)['cats'] == ['meta']


def test_catalog_puts_our_three_on_top_when_listed():
    c = lc.catalog([ROW, BIG, {'id': 'a/b:batch'}])
    assert [r['tag'] for r in c['rec']] == ['FEELESS PICK'] and len(c['models']) == 2   # 🔒 public tags never name OSSY / G4 / NEXA
    assert any(k['key'] == 'meta' and k['n'] == 1 for k in c['cats'])


def test_plan_counts_calls_per_mode():
    a, b = lc.slim(ROW), lc.slim(BIG)
    one = lc.plan([a], 'discuss')
    assert one['calls'] == 1 and one['perTrade'] == round(a['perDecision'] * 4, 6)
    two = lc.plan([a, b], 'together')
    assert two['calls'] == 2 and two['trades'] == int(10 / two['perTrade'])


def test_prompt_is_locked_once_set_and_brains_capped_at_two():
    b = lc.clean({'brains': ['a', 'b', 'c'], 'prompt': 'buy germ floors', 'brainMode': 'battle'})
    assert b['brains'] == ['a', 'b'] and b['promptLocked']
    b2 = lc.clean({'prompt': 'yolo everything'}, b)
    assert b2['prompt'] == 'buy germ floors' and b2['brainMode'] == 'battle'
    with pytest.raises(ValueError):
        lc.clean({'brains': ['z']}, ids={'a'})
    assert lc.clean({'brains': ['a'], 'brainMode': 'discuss'})['brainMode'] == 'turns'


def test_live_asks_only_on_ten_percent_moves_and_three_times():
    pos = {'entryPriceNative': 1.0, 'lastPx': 1.05}
    assert not lc.live_due(pos)
    pos['lastPx'] = 0.89
    assert lc.live_due(pos)
    pos.update(brainAsks=3)
    assert not lc.live_due(pos)


def test_modes_pick_who_answers_and_how_words_merge():
    b = {'brains': ['a', 'b'], 'brainMode': 'turns'}
    assert lc.who_asks(b, 0) == ['a'] and lc.who_asks(b, 1) == ['b']
    b['brainMode'] = 'together'
    assert lc.who_asks(b, 5) == ['a', 'b']
    assert lc.merge(b, [('a', 'BUY'), ('b', 'SKIP')], 'buy') == 'SKIP'
    assert lc.merge(b, [('a', 'SELL'), ('b', 'SELL')], 'live') == 'SELL'
    b['brainMode'] = 'discuss'
    assert lc.merge(b, [('a', 'BUY'), ('b', 'SKIP')], 'buy') == 'SKIP'
    assert lc.merge(b, [], 'live') == 'HOLD'


def test_billing_pauses_payg_at_zero_and_profit_pays_the_owed():
    b = {'credit': 0.01, 'billing': 'payg'}
    lc.charge(b, 0.03)
    assert b['credit'] == 0 and b['owed'] == 0.02 and not lc.can_ask(b)
    p = {'credit': 0, 'billing': 'profit', 'owed': 0.5}
    assert lc.can_ask(p)
    assert lc.settle(p, 0.3) == 0.3 and p['owed'] == 0.2
    p['owed'] = 2.0
    assert not lc.can_ask(p)


def test_parse_word_reads_json_or_a_lone_word():
    assert lc.parse_word('{"word": "buy", "why": "germ floor"}', 'buy') == ('BUY', 'germ floor')
    assert lc.parse_word('I would SELL now', 'live')[0] == 'SELL'
    assert lc.parse_word('HOLD or SELL', 'live')[0] == ''
    m = lc.ask_messages({'prompt': 'only HH/HL', 'chime': [{'text': 'watch the dev'}]}, '$X', partner='SKIP')
    assert 'only HH/HL' in m[0]['content'] and 'watch the dev' in m[1]['content'] and 'PARTNER' in m[1]['content']

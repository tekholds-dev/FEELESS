"""❓ A coin / make-money ask gets at most 3 questions — only what it is missing — and the owner's next message answers them. No model call."""
import pytest


def test_coin_ask_asks_only_what_is_missing():
    cq = pytest.importorskip('clarify')
    intent, q = cq.questions('launch my coin')
    assert intent == 'coin' and len(q) == 3 and 'ticker' in q[0] and 'never on FEELESS' in q[1]
    intent, q = cq.questions('make a coin $FEEL on pump.fun', has_files=True)
    assert intent == 'coin' and q == ['How much SOL for the first buy from its wallet? (0 = none)']
    assert cq.questions('launch a coin $FEEL on pump.fun with 0.1 SOL first buy') == (None, [])


def test_money_ask_and_plain_asks():
    cq = pytest.importorskip('clarify')
    intent, q = cq.questions('make me some money fast')
    assert intent == 'money' and len(q) == 3
    assert cq.questions('make me money with $50, safe, this week') == (None, [])
    assert cq.questions('what is 2 + 2?') == (None, [])


def test_the_next_message_answers_and_runs_the_full_task():
    cq = pytest.importorskip('clarify')
    cat = {}
    assert cq.take(cat, 'launch my coin', now=100)[0] == 'ask' and cat['clarify']['intent'] == 'coin'
    step, text = cq.take(cat, '$FEEL, pump.fun, 0.05 SOL', now=200)
    assert step == 'go' and text.startswith('launch my coin') and '$FEEL, pump.fun, 0.05 SOL' in text and 'clarify' not in cat
    cq.take(cat, 'launch my coin', now=300)
    assert cq.take(cat, 'what is 2 + 2?', now=300 + cq.TTL + 1) == ('go', 'what is 2 + 2?')   # expired: a fresh ask

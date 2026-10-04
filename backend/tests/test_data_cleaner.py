"""🧹 Data cleaner: only stale derived blocks go; text, author, coin identity and fresh messages are untouched; a second pass frees nothing."""
import data_cleaner as dc

PAIR = {'chainId': 'solana', 'pairAddress': 'P1', 'baseToken': {'symbol': 'AAA'}, 'priceUsd': '1.5', 'info': {'imageUrl': 'x'}, 'signals': {'v': 'x' * 3000}, 'quality': {'q': 1}, 'observedAt': 't'}
MSG = lambda ts, **k: {'id': 'm', 'text': 'look at this', 'address': 'W', 'ts': ts, 'tokens': [{'chainId': 'solana', 'pairAddress': 'P1', 'pair': dict(PAIR)}], **k}


def test_old_chat_token_snapshots_lose_only_their_stale_signal_blocks():
    now = 10_000.0
    doc = {'rooms': {'r': [MSG((now - 7200) * 1000), MSG((now - 60) * 1000), {'id': 'plain', 'text': 'gm', 'ts': 1}]}, 'lastTs': {'W': 5}}
    out, st = dc.slim_chat(doc, now)
    old, fresh, plain = out['rooms']['r']
    assert st['messages'] == 1 and st['bytes'] > 3000 and out['lastTs'] == {'W': 5}
    assert old['text'] == 'look at this' and old['address'] == 'W'
    assert old['tokens'][0]['pair'] == {k: v for k, v in PAIR.items() if k not in dc.STALE_PAIR_KEYS}    # coin, price at post time, logo stay
    assert 'signals' in fresh['tokens'][0]['pair'] and plain == {'id': 'plain', 'text': 'gm', 'ts': 1}     # fresh + plain untouched
    assert 'signals' in doc['rooms']['r'][0]['tokens'][0]['pair']                                         # the input is never mutated
    assert dc.slim_chat(out, now)[1] == {'messages': 0, 'bytes': 0}                                        # idempotent

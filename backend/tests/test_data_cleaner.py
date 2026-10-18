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


def test_blocklist_slim_forgets_idle_unblocked_wallets_and_keeps_every_blocked_one():
    import data_cleaner as dc
    now = 100 * 86400
    doc = {'wallets': {'idle': {'mints': {'a': 'sniper'}, 'lastSeen': 0}, 'fresh': {'mints': {'a': 'sniper'}, 'lastSeen': now - 60},
                       'rep': {'mints': {}, 'reported': True, 'lastSeen': 0}, 'blk': {'mints': {str(i): 'bundler' for i in range(60)}, 'lastSeen': 0}}}
    out, st = dc.slim_blocklist(doc, now, 3)
    assert set(out['wallets']) == {'fresh', 'rep', 'blk'} and st == {'dropped': 1, 'trimmed': 1}
    assert len(out['wallets']['blk']['mints']) == 40 and out['wallets']['blk']['strikes'] == 60


def test_meme_terms_drop_refs_of_words_no_longer_in_any_day():
    import meme_terms as mt
    s = mt.learn({}, [('alpha', 'coin', 'c1')], 0)
    s = mt.learn(s, [('beta', 'coin', 'c2')], 40 * 86400)
    assert 'alpha' not in s['refs'] and 'alpha' not in s['src'] and 'alpha' not in s['firstSeen'] and 'beta' in s['refs']

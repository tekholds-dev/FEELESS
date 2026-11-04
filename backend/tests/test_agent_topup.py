"""💸 Top-ups: only the owner's yes sends, a page cannot choose where money goes unnoticed, and nothing real is touched. Fake wallet, fake chain."""
import asyncio
import pytest
import agent_topup as tu

A = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'
MANUALS = {'pump.fun': {'site': 'pump.fun', 'slug': 'pump', 'url': 'https://pump.fun', 'state': 'read', 'kinds': ['pow']}}


def test_the_ways_to_ask():
    assert tu.ask('top up pump', MANUALS) == {'word': 'pump', 'usd': None, 'address': None}
    assert tu.ask('Top-up pump $1.50', MANUALS)['usd'] == 1.5
    assert tu.ask('add $2 to pump', MANUALS) == {'word': 'pump', 'usd': 2.0, 'address': None}
    assert tu.ask(f'top up pump 3 to {A}', MANUALS)['address'] == A
    assert tu.ask('how do I top up my pump account?', MANUALS) is None and tu.ask('file a pump pow', MANUALS) is None


def test_the_ways_to_answer():
    assert tu.reply('yes') == {'yes': True, 'usd': None}
    assert tu.reply('Yes, top up $1.50') == {'yes': True, 'usd': 1.5}
    assert tu.reply('yes 2') == {'yes': True, 'usd': 2.0}
    assert tu.reply('ok send $3') == {'yes': True, 'usd': 3.0}
    assert tu.reply('no') == {'yes': False} and tu.reply('not now') == {'yes': False}
    assert tu.reply(A) == {'address': A}
    for other in ('yes but what about the other coin', 'yesterday was good', 'no way that pumps', 'what is the fee?'):
        assert tu.reply(other) is None


def test_addresses_and_limits():
    assert tu.valid_address(A) and not tu.valid_address('1' * 44) and not tu.valid_address('0OIl' * 10) and not tu.valid_address('abc')
    assert tu.amount_why(1.5) == '' and tu.amount_why(None) and tu.amount_why(0.1) and tu.amount_why(26)
    assert tu.address_in({'0': {'note': f'found {A} on the wallet page'}}) == A
    assert tu.address_in({'0': {'note': f'{A}'}, '1': {'note': 'DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy'}}) is None   # two answers: none is trusted
    assert tu.address_in({'0': {'note': 'walled'}}) is None


def test_a_read_address_needs_its_last_4_typed():
    read = tu.card('pump.fun', 'u', 1.5, A, 'read', 1.0); pasted = tu.card('pump.fun', 'u', 1.5, A, 'owner', 1.0)
    assert not tu.check_ok(read, '') and not tu.check_ok(read, 'xxxx') and tu.check_ok(read, A[-4:]) and tu.check_ok(pasted, '')
    assert tu.card('pump.fun', 'u', None, None, 'read', 1.0)['state'] == 'needs_address' and tu.expired(read, 1000) and not tu.expired(read, 2)


# the service's doors, on fakes
class Http:
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


@pytest.fixture
def fs(monkeypatch, tmp_path):
    import feecat_service as fs
    sent = []
    fs._WORK.clear()
    monkeypatch.setattr(fs.httpx, 'AsyncClient', Http)

    async def price(_h): return 100.0
    async def bal(_h, _a): return 0.0, 1.0
    async def onchain(_h, _a): return 0.25
    async def rpc(_h, m, _p): return {'value': {'blockhash': 'x'}}
    async def post(_h, _c, rec): sent.append(rec); rec['sig'] = 'SIG'
    monkeypatch.setattr(fs, '_sol_usd', price); monkeypatch.setattr(fs, '_agent_usdc', bal); monkeypatch.setattr(fs, '_lamports_sol', onchain)
    monkeypatch.setattr(fs._crpc, '_rpc', rpc); monkeypatch.setattr(fs._at, '_circle_post', post)
    monkeypatch.setattr(fs, 'pot_transfer_tx', lambda src, dst, lamports, bh: {'src': src, 'dst': dst, 'lamports': lamports})
    fs.sent = sent
    return fs


def _cat(**kw):
    return {'id': 'c1', 'chat': [], 'agentWallet': {'address': 'WALLET', 'circleAcct': 'agent'}, 'brainsCfg': {'brains': ['m/a']}, 'siteManuals': dict(MANUALS), 'siteSessions': {'pump.fun': {'ctx': 'x'}}, **kw}


def test_yes_sends_once_to_that_address_and_files_it(fs):
    cat = _cat(topup=tu.card('pump.fun', 'https://pump.fun', 1.5, A, 'owner', __import__('time').time()))
    ok, say = asyncio.run(fs._topup_send(cat, 'c1', 1.5, ''))
    assert ok and fs.sent[0]['tx'] == {'src': 'WALLET', 'dst': A, 'lamports': 15000000}
    assert 'SIG' in say and 'topup' not in cat and cat['topups'][-1]['before'] == 0.25 and cat['topups'][-1]['sol'] == 0.015
    ok, say = asyncio.run(fs._topup_send(cat, 'c1', 1.5, ''))   # the card is gone: a second yes sends nothing
    assert not ok and len(fs.sent) == 1


def test_nothing_moves_without_the_check_or_over_the_limit_or_past_its_gas(fs):
    now = __import__('time').time()
    read = _cat(topup=tu.card('pump.fun', 'u', 1.5, A, 'read', now))
    assert not asyncio.run(fs._topup_send(read, 'c1', 1.5, ''))[0] and not fs.sent
    assert asyncio.run(fs._topup_send(read, 'c1', 1.5, A[-4:]))[0] and len(fs.sent) == 1
    fs.sent.clear()
    assert not asyncio.run(fs._topup_send(_cat(topup=tu.card('pump.fun', 'u', 26, A, 'owner', now)), 'c1', 26, ''))[0]
    assert not asyncio.run(fs._topup_send(_cat(topup=tu.card('pump.fun', 'u', 1.5, A, 'owner', now - 9999)), 'c1', 1.5, ''))[0]
    assert not asyncio.run(fs._topup_send(_cat(topup=tu.card('pump.fun', 'u', 1.5, 'WALLET', 'owner', now)), 'c1', 1.5, ''))[0]   # never to itself
    no_wallet = _cat(topup=tu.card('pump.fun', 'u', 1.5, A, 'owner', now), agentWallet={'address': 'WALLET'})
    assert not asyncio.run(fs._topup_send(no_wallet, 'c1', 1.5, ''))[0]
    assert not fs.sent


def test_chat_answers_change_the_card_but_a_model_cannot(fs):
    now = __import__('time').time()
    cat = _cat(topup=tu.card('pump.fun', 'u', None, A, 'owner', now))
    assert fs._topup_answer(cat, {'yes': True, 'usd': None})['ask'] and 'topup' in cat
    assert fs._topup_answer(cat, {'yes': False})['say'].startswith('💸 Okay') and 'topup' not in cat
    assert 'topup' not in fs._no_keys(_cat(topup={'x': 1})) and 'topups' not in fs._no_keys(_cat(topups=[1]))

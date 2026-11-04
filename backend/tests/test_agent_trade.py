"""🏇 Agent trades: a cat's proposal filled from its own Crossmint wallet — every server guard, the exact-coins check, one in flight, a lost
reply never becomes a second trade, ASK ME waits for the owner. Network faked; nothing is sent."""
import asyncio

import pytest

import agent_trade as at

ADDR = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'
M = 'COINmint11111111111111111111111111111111111'
TX = 'AQID'   # base64 of bytes 01 02 03
NOW = 10_000.0


def cat(mode='auto', **k):
    return {'id': 'c1', 'name': 'Mittens', 'mode': 'real', 'realWallet': 'OWNER', 'budgetSol': 0.05, 'agentWallet': {'address': ADDR, 'mode': mode},
            'proposals': [], 'realHeld': {}, **k}


def prop(pid='p1', side='buy', **k):
    return {'id': pid, 'side': side, 'mint': M, 'pair': 'P', 'symbol': 'CAT', 'at': NOW - 5, 'until': NOW + 800, 'status': 'pending', **({'sol': 0.05} if side == 'buy' else {'fraction': 1.0}), **k}


class R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text, self.headers = code, body, str(body), {'content-type': 'application/json'}

    def json(self):
        return self._b


class Net:
    """holdings → quote → Crossmint create / read, each answer scripted."""
    def __init__(self, sol=1.0, tok=0.0, quote=None, cm=(201, {'id': 'T1', 'status': 'pending'}), read=(200, {'status': 'success', 'onChain': {'txId': 'SIG123'}})):
        self.sol, self.tok, self.quote, self.cm, self.read, self.calls = sol, tok, quote, cm, read, []

    async def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append(('GET', url))
        if url.endswith(f'/holdings/{ADDR}'):
            return R(200, {'tokens': [{'mint': at.SOL, 'amount': self.sol}, {'mint': M, 'amount': self.tok}]})
        return R(*self.read)

    async def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(('POST', url, json, headers))
        if url.endswith('/quote'):
            return R(200, self.quote or {'input_mint': json['input_mint'], 'output_mint': json['output_mint'], 'order_id': 'O1', 'quote': {'transaction': TX}})
        return R(*self.cm)


def test_guards_budget_daily_cap_gas_and_sell_only_what_it_holds():
    c = cat()
    assert at.guard(c, prop(), 1.0, 0, NOW) == (at.SOL, M, '0.05')
    with pytest.raises(ValueError, match='per-buy budget'):
        at.guard(c, prop(sol=0.2), 1.0, 0, NOW)
    with pytest.raises(ValueError, match='gas'):
        at.guard(c, prop(), 0.055, 0, NOW)
    c['agentTx'] = [{'side': 'buy', 'sol': 0.05, 'status': 'success', 'at': NOW - 100}] * 4    # 4 × budget spent today
    with pytest.raises(ValueError, match='daily cap'):
        at.guard(c, prop(), 1.0, 0, NOW)
    with pytest.raises(ValueError, match='really bought'):
        at.guard(cat(), prop(side='sell'), 1.0, 5.0, NOW)
    held = cat(realHeld={M: {'symbol': 'CAT'}})
    assert at.guard(held, prop(side='sell', fraction=0.5), 1.0, 5.0, NOW) == (M, at.SOL, '2.5')
    with pytest.raises(ValueError, match='none of that coin'):
        at.guard(held, prop(side='sell'), 1.0, 0.0, NOW)
    with pytest.raises(ValueError, match='one trade at a time'):
        at.guard(cat(agentTx=[{'status': 'pending'}]), prop(), 1.0, 0, NOW)


def test_auto_sends_the_exact_coins_from_its_wallet_and_settles_done_with_the_signature():
    c = cat(); p = prop(); c['proposals'] = [p]; net = Net()
    words = asyncio.run(at.run(net, 'sk_production_k', c, NOW))
    q = next(x for x in net.calls if x[0] == 'POST' and x[1].endswith('/quote'))
    assert q[2] == {'input_mint': at.SOL, 'output_mint': M, 'amount': '0.05', 'wallet': ADDR, 'slippage_bps': at.SLIP_BPS}
    cm = next(x for x in net.calls if x[0] == 'POST' and '/transactions' in x[1])
    assert cm[1].endswith(f'/wallets/{ADDR}/transactions') and cm[2] == {'params': {'transaction': at.b58_tx(TX)}} and cm[3]['x-idempotency-key'] == 'feeless-c1-p1'
    assert c['agentTx'][0]['status'] == 'pending' and 'tx' not in c['agentTx'][0] and 'sent from its wallet' in words[0]
    assert p['status'] == 'pending'                                            # not done until Crossmint says success
    words = asyncio.run(at.run(net, 'sk_production_k', c, NOW + 10))
    assert p['status'] == 'done' and p['sig'] == 'SIG123' and c['realHeld'][M]['agent'] and '✅ BUY $CAT' in words[0]


def test_a_quote_for_other_coins_is_never_sent_and_a_refusal_fails_with_crossmints_words():
    c = cat(); p = prop(); c['proposals'] = [p]
    bad = Net(quote={'input_mint': at.SOL, 'output_mint': 'OTHER', 'quote': {'transaction': TX}})
    asyncio.run(at.run(bad, 'sk_production_k', c, NOW))
    assert not any('/transactions' in x[1] for x in bad.calls) and 'did not match' in p['agentWhy'] and not c.get('agentTx')
    c2 = cat(); p2 = prop(); c2['proposals'] = [p2]
    asyncio.run(at.run(Net(cm=(403, {'message': 'missing scope wallets:transactions.create'})), 'sk_production_k', c2, NOW))
    assert c2['agentTx'][0]['status'] == 'failed' and 'scope' in c2['agentTx'][0]['error'] and 'scope' in p2['agentWhy']


def test_a_lost_reply_is_asked_again_with_the_same_key_never_a_second_trade():
    c = cat(); p = prop(); c['proposals'] = [p]
    asyncio.run(at.run(Net(cm=(502, {'message': 'gateway'})), 'sk_production_k', c, NOW))
    rec = c['agentTx'][0]
    assert rec['status'] == 'sending' and rec['tx'] and at.in_flight(c)          # remembered, and it blocks any other trade
    net = Net()
    asyncio.run(at.run(net, 'sk_production_k', c, NOW + 30))
    posts = [x for x in net.calls if x[0] == 'POST']
    assert len(posts) == 1 and posts[0][3]['x-idempotency-key'] == 'feeless-c1-p1' and not any(x[1].endswith('/quote') for x in posts)   # same key, no new quote
    assert rec['id'] == 'T1' and 'tx' not in rec


def test_ask_me_waits_for_the_owner_and_a_success_after_the_clock_ran_out_still_marks_the_coin():
    c = cat('approve'); p = prop(); c['proposals'] = [p]
    assert not at.wants(c, p, NOW)
    p['approved'] = NOW
    assert at.wants(c, p, NOW)
    p['agentTry'] = NOW - 10
    assert not at.wants(c, p, NOW)                                             # a guard stopped it a moment ago: wait
    c2 = cat(); p2 = prop(status='expired'); c2['proposals'] = [p2]
    rec = {'pid': 'p1', 'side': 'buy', 'status': 'pending', 'id': 'T1'}
    assert at.settle(c2, rec, {'status': 'success', 'onChain': {'txId': 'S'}}, NOW) and p2['status'] == 'done' and M in c2['realHeld']
    c3 = cat(); p3 = prop(); c3['proposals'] = [p3]
    at.settle(c3, {'pid': 'p1', 'side': 'buy', 'status': 'pending'}, {'status': 'failed', 'error': 'slippage'}, NOW)
    assert p3['status'] == 'failed' and p3['why2'] == 'slippage' and M not in c3['realHeld']


# ---- ♻ rent back: an agent closes its empty coin accounts (network faked; nothing is sent) ----
class SweepNet:
    def __init__(self, reply=(200, {'closed': 2, 'sol': 0.003, 'signature': 'SIG'}), status='success'):
        self.reply, self.status, self.asked = reply, status, []

    async def post(self, url, json=None, headers=None, timeout=None):
        if url.endswith('/internal/agent-close-empty'):
            self.asked.append(json)
            return R(*self.reply)
        if url.endswith('/rpc'):
            v = {'unseen': None, 'failed': {'err': 'x', 'confirmationStatus': 'confirmed'}, 'success': {'err': None, 'confirmationStatus': 'confirmed'}}[self.status]
            return R(200, {'result': {'value': [v]}})
        raise AssertionError(url)


def own(**k):
    c = cat(**k)
    c['agentWallet'].update(provider='circle', circleAcct='agent', circleId='w1')
    return c


def test_rent_comes_back_only_once_the_chain_confirms_it():
    c, net = own(), SweepNet()
    assert asyncio.run(at.sweep_rent(net, c, NOW)) is None
    assert c['rentSweep']['status'] == 'sent' and not c['rentSweep'].get('backSol')
    word = asyncio.run(at.sweep_rent(net, c, NOW + 20))
    assert '0.003000 SOL rent back' in word and c['rentSweep']['backSol'] == 0.003 and c['rentSweep']['closedN'] == 2
    assert asyncio.run(at.sweep_rent(net, c, NOW + 40)) is None and len(net.asked) == 1     # waits its 10 minutes
    asyncio.run(at.sweep_rent(net, c, NOW + at.SWEEP_S + 1))
    assert len(net.asked) == 2


def test_rent_sweep_keeps_every_coin_in_use_and_waits_for_a_live_trade():
    c = own(realHeld={'HELD': {}}, proposals=[{'status': 'pending', 'mint': 'ASKED'}, {'status': 'done', 'mint': 'OLD'}], positions=[{'mint': 'BOOK'}], agentTx=[{'status': 'success', 'mint': 'SOLD'}])
    net = SweepNet()
    asyncio.run(at.sweep_rent(net, c, NOW))
    assert net.asked[0]['keep'] == sorted(['ASKED', 'BOOK', 'HELD', at.USDC])
    busy, net2 = own(agentTx=[{'status': 'pending', 'mint': 'X'}]), SweepNet()
    assert asyncio.run(at.sweep_rent(net2, busy, NOW)) is None and not net2.asked


def test_rent_sweep_never_touches_a_wallet_that_is_not_the_agents_own():
    fee = own()
    fee['agentWallet']['circleAcct'] = None     # Fee's assigned wallet
    net = SweepNet()
    assert asyncio.run(at.sweep_rent(net, fee, NOW)) is None and not net.asked
    assert asyncio.run(at.sweep_rent(net, cat(), NOW)) is None and not net.asked  # Crossmint


def test_a_failed_close_claims_no_rent_and_backs_off():
    for status, later in (('failed', 20), ('unseen', at.NEVER_LANDED_S + 1)):
        c, net = own(), SweepNet(status=status)
        asyncio.run(at.sweep_rent(net, c, NOW))
        assert 'no rent moved' in asyncio.run(at.sweep_rent(net, c, NOW + later))
        assert c['rentSweep']['status'] == 'failed' and not c['rentSweep'].get('backSol')
        asyncio.run(at.sweep_rent(net, c, NOW + at.SWEEP_S + later))
        assert len(net.asked) == 1                                               # an hour, not 10 minutes
        asyncio.run(at.sweep_rent(net, c, NOW + at.SWEEP_FAILED_S + 1 + later))
        assert len(net.asked) == 2


def test_nothing_empty_or_a_silent_service_sends_nothing():
    for reply in ((200, {'closed': 0}), (502, {'detail': 'x'})):
        c = own()
        assert asyncio.run(at.sweep_rent(SweepNet(reply=reply), c, NOW)) is None
        assert c['rentSweep'].get('status') is None and c['rentSweep']['at'] == round(NOW)

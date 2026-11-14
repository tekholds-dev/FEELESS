"""✅ chain_rpc.land — one signed transaction watched until it lands or provably can't (network faked)."""
import asyncio

import chain_rpc


def _run(answers, **kw):
    casts = []
    async def rpc(_h, method, _p):
        a = answers[method]
        return a.pop(0) if isinstance(a, list) else a
    async def cast(_h, tx):
        casts.append(tx)
    async def nap(_s):
        return None
    return asyncio.run(chain_rpc.land(rpc, cast, nap, None, 'SIG', 'TX', **kw)), casts


def test_confirmed_failed_dropped_by_height_and_by_blockhash():
    ok = {'value': [{'confirmationStatus': 'confirmed', 'err': None}]}
    assert _run({'getSignatureStatuses': ok}, last_height=100)[0] == 'confirmed'
    assert _run({'getSignatureStatuses': {'value': [{'err': {'x': 1}}]}}, last_height=100)[0] == 'failed'
    st, casts = _run({'getSignatureStatuses': {'value': [None]}, 'getBlockHeight': [99, 101]}, last_height=100)
    assert st == 'dropped' and casts == ['TX']                       # re-broadcast while valid, dropped once past its height
    st, casts = _run({'getSignatureStatuses': {'value': [None]}, 'isBlockhashValid': [{'value': True}, {'value': False}]}, blockhash='BH')
    assert st == 'dropped' and casts == ['TX']                       # a user-signed tx: no height known → the blockhash decides
    late = {'getSignatureStatuses': [{'value': [None]}, {'value': [None]}, ok], 'getBlockHeight': [99, 101]}
    assert _run(late, last_height=100)[0] == 'confirmed'             # landed in the last moment: the final look sees it
    assert _run({'getSignatureStatuses': {'value': [None]}}, cap=0)[0] == 'unknown'

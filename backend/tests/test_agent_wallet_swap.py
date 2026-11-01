"""👛 The desktop wallet app: the owner swaps SOL ⇄ USDC inside the agent's OWN wallet — gas kept, only the exact quote signed, balance read back."""
import asyncio

import pytest

import feecat_service as fs

CAT = {'id': 'w1', 'name': 'Happy', 'agentWallet': {'address': 'AGT', 'circleAcct': 'agent', 'circleId': 'cid'}}


def test_the_swap_plan_keeps_gas_and_refuses_dust():
    assert fs.swap_plan('SOL>USDC', 0, 0.03, 0) == (fs._at.SOL, fs._cf_usdc, 0.02)            # "all" = everything over the gas reserve
    assert fs.swap_plan('USDC>SOL', 1, 0.01, 1.35) == (fs._cf_usdc, fs._at.SOL, 1.0)
    for side, amt, sol, usdc, why in [('SOL>USDC', 0.025, 0.03, 0, 'keeps 0.01 SOL'), ('USDC>SOL', 0.1, 0, 5, 'smallest'), ('SOL>BONK', 1, 1, 1, 'Swap SOL')]:
        with pytest.raises(ValueError, match=why):
            fs.swap_plan(side, amt, sol, usdc)


def _run(monkeypatch, quote, text='USDC>SOL', cap=1):
    store = {'cats': {'w1': {**CAT}}}; bal = {'v': (1.35, 0.0075)}; signed = []
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: 'OWNER')

    async def usdc(http, addr):
        return bal['v']

    async def circle(http, cat, rec):
        signed.append(rec['tx']); rec['sig'] = 'SIG'; bal['v'] = (0.35, 0.0179)

    class H:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, **k):
            class R: status_code = 200
            R.json = staticmethod(lambda: quote(json)); return R()
    async def nap(_): return None
    monkeypatch.setattr(fs, '_agent_usdc', usdc); monkeypatch.setattr(fs._at, '_circle_post', circle)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', H); monkeypatch.setattr(fs.asyncio, 'sleep', nap)
    return store, signed, asyncio.run(fs.cat_work('w1', fs.WorkPayload(op='wallet_swap', text=text, cap=cap, session='s')))


def test_a_swap_signs_only_the_exact_quote_and_reads_the_balance_back(monkeypatch):
    store, signed, out = _run(monkeypatch, lambda j: {'input_mint': j['input_mint'], 'output_mint': j['output_mint'], 'quote': {'transaction': 'TX'}})
    assert signed == ['TX'] and out['swap']['landed'] and out['sol'] == 0.0179 and out['usdc'] == 0.35
    assert store['cats']['w1']['walletSwaps'][-1]['side'] == 'USDC>SOL'


def test_a_quote_for_other_coins_is_never_signed(monkeypatch):
    with pytest.raises(fs.HTTPException) as e:
        _run(monkeypatch, lambda j: {'input_mint': j['input_mint'], 'output_mint': 'BONK', 'quote': {'transaction': 'TX'}})
    assert e.value.status_code == 502

"""SITE-17 C03: marginfi · Save · Phoenix · PumpSwap buildings are built only by real on-chain accounts. Fixture = real accounts read
2026-11-10 (owner → accounts round trip on mainnet), so the byte offsets are checked against the chain, not guessed."""
import base64
import json
from pathlib import Path

import base58

import block_markets as bm

FX = json.loads((Path(__file__).parent / 'fixtures' / 'block_chain_accounts.json').read_text())
B = base64.b64decode


def test_marginfi_account_values_collateral_and_debt_from_its_banks():
    m = FX['marginfi']
    banks = {base58.b58decode(k): B(v) for k, v in m['banks'].items()}
    px = {base58.b58decode(k): v for k, v in m['prices'].items()}
    h = bm.marginfi_held([B(a) for a in m['accounts']], banks, px)
    assert h['n'] == 1 and h['gross'] > 1000 and 0 < h['debt'] < h['gross'] and abs(h['usd'] - (h['gross'] - h['debt'])) < 0.05
    assert bm.marginfi_held([B(a) for a in m['accounts']], {}, px) is None   # no bank read → never a made-up value


def test_save_obligation_reads_deposits_and_risk():
    h = bm.save_held([B(a) for a in FX['save']])
    assert h == {'n': 1, 'usd': h['gross'], 'debt': 0.0, 'gross': h['gross'], 'risk': 0.0} and h['gross'] > 100
    assert bm.save_held([b'\0' * 1300]) is None


def test_phoenix_counts_only_approved_seats():
    h = bm.phoenix_held([B(a) for a in FX['phoenix']])
    assert h['n'] == 2 and len(h['markets']) == 2
    assert bm.phoenix_held([B(FX['phoenix'][0])[:72] + (0).to_bytes(8, 'little') + B(FX['phoenix'][0])[80:]]) is None


def test_pumpswap_lp_value_matches_the_pool_liquidity():
    p = FX['pumpswap']
    h = bm.pumpswap_held({p['lp']: (p['held'], p['supply'])}, {p['lp']: B(p['pool'])}, {p['lp']: p['quote_reserve']},
                         {'So11111111111111111111111111111111111111112': p['sol_usd']})
    assert h['n'] == 1 and abs(h['usd'] - p['dexscreener_liq']) / p['dexscreener_liq'] < 0.05   # whole supply = the whole pool


def test_buildings_prove_by_chain_and_errand_on_a_risky_loan():
    for k in ('marginfi', 'save', 'phoenix', 'pumpswap'):
        assert bm.proof_of(k)[0] == 'chain' and bm.needs([{'key': k}])[k] is True
    b = bm.view([{'key': 'save'}], {'save': {'name': 'Save'}}, {'save': {'n': 1, 'usd': 50, 'debt': 400, 'risk': 0.9}}, mine=True)[0]
    assert b['state'] == 'built' and b['debt'] == 400 and [e['kind'] for e in b['errands']] == ['health']
    other = bm.view([{'key': 'save'}], {}, {'save': {'n': 1, 'usd': 50, 'debt': 400}}, mine=False)[0]
    assert 'debt' not in other and other['band']


def test_a_spent_helius_plan_moves_the_block_reads_to_the_next_node(monkeypatch):
    """SITE-17: Helius answering 429 'max usage reached' rests THAT node until its plan resets and the reader's getProgramAccounts lands on the
    next one; a node that refuses getProgramAccounts on its plan (Tatum) is skipped for that method only. Live 2026-11-13: 1 × 429 + 3 refusals
    rotated, all five readers answered."""
    import asyncio
    import chain_rpc as cr
    from test_rpc_method_refusal import _Http, _Res
    monkeypatch.setattr(cr, 'RPC_POOL', ['helius', 'tatum', 'alchemy']); monkeypatch.setattr(cr, 'KEEPER_LANES', ['helius', 'tatum', 'alchemy'])
    monkeypatch.setattr(cr, 'RPC_MAX_RETRIES', 3); monkeypatch.setattr(cr, '_dedicated', None)
    cr._unsupported.clear(); cr._rpc_cooldown_until.clear(); cr._quota_until.clear()

    def plan(url, m):
        if url == 'helius':
            r = _Res(429); r.text = '{"error":{"code":-32429,"message":"max usage reached"}}'; return r
        if url == 'tatum' and m == 'getProgramAccounts':
            return _Res(403)
        return _Res(200, {'result': [url]})
    h = _Http(plan)
    assert asyncio.run(cr._rpc(h, 'getProgramAccounts', ['MFv2', {}], scan=False)) == ['alchemy']
    assert cr._rpc_cooldown_until.get('helius', 0) > 0 and ('tatum', 'getProgramAccounts') in cr._unsupported
    h.calls.clear()
    assert asyncio.run(cr._rpc(h, 'getProgramAccounts', ['MFv2', {'x': 1}], scan=False)) == ['alchemy'] and h.calls == [('alchemy', 'getProgramAccounts')]

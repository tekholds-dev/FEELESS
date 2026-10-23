import base64

import pytest
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

import jup_keys
import lend_borrow as lb

CB = Pubkey.from_string('ComputeBudget111111111111111111111111111111')


def _tx(payer, progs, extra_signer=None):
    ixs = [Instruction(p, b'\x01', [AccountMeta(payer, True, True)] + ([AccountMeta(extra_signer, True, False)] if extra_signer else [])) for p in progs]
    msg = MessageV0.try_compile(payer, ixs, [], Hash.default())
    return base64.b64encode(bytes(VersionedTransaction(msg, [NullSigner(payer)] + ([NullSigner(extra_signer)] if extra_signer else [])))).decode()


VAULTS = Pubkey.from_string(lb.VAULTS)
SOL = 'So11111111111111111111111111111111111111112'


def _vault(i, sym, mint, price, cf=800, lt=850, borrow=lb.USDC, borrowable='5000000000000', dec=9):
    return {'id': i, 'supplyToken': {'symbol': sym, 'address': mint, 'decimals': dec, 'price': str(price)},
            'borrowToken': {'symbol': 'USDC', 'address': borrow, 'decimals': 6, 'price': '1'}, 'collateralFactor': str(cf),
            'liquidationThreshold': str(lt), 'liquidationPenalty': '100', 'borrowRate': '831', 'supplyRate': '383',
            'borrowable': borrowable, 'minimumBorrowing': '1061893'}


VLIST = [_vault(1, 'WSOL', SOL, 100), _vault(2, 'WSOL', SOL, 100, borrow='Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'),
         _vault(40, 'JUP', 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', 0.3, cf=500, lt=700, dec=6),
         _vault(11, 'cbBTC', 'cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij', 80000, cf=850, lt=900, dec=8),
         _vault(99, 'BONK', 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', 0.00002)]


def test_markets_keep_one_usdc_vault_per_coin_in_order():
    rows = lb.markets(VLIST)
    assert [r['coin'] for r in rows] == ['SOL', 'BTC', 'JUP']        # USDT vault + unknown coins out
    sol = rows[0]
    assert sol['vaultId'] == 1 and sol['cf'] == 0.8 and sol['lt'] == 0.85 and sol['borrowApr'] == 8.31
    assert sol['maxLev'] == 1.7 and sol['minDebt'] == 1.06               # 10 points under the vault's 80 % max LTV
    assert lb.markets('junk') == [] and lb.markets([{'id': 1}]) == []


def test_plan_is_the_real_math_with_guards():
    sol = lb.markets(VLIST)[0]
    p = lb.plan(sol, '0.5', 1.5)                                         # $50 of SOL at 1.5×
    assert p['debt'] == 25 and p['debtUnits'] == '25000000' and p['colUnits'] == '500000000'
    assert p['exposure'] == pytest.approx(0.75)                          # 0.5 locked + 0.25 bought
    assert p['liq'] == pytest.approx(25 / (0.5 * 0.85)) and p['toLiqPct'] == pytest.approx(41.2, abs=0.1)
    assert p['dayCost'] == pytest.approx(25 * 0.0831 / 365, abs=1e-4)
    for col, lev, why in (('0', 1.5, 'above zero'), ('0.5', 1.8, 'Leverage runs'), ('0.01', 1.3, 'lends at least'), ('25', 1.5, 'capped')):
        with pytest.raises(ValueError, match=why):
            lb.plan(sol, col, lev)


def test_requests_are_cleaned_and_close_is_repay_all_withdraw_all():
    me = str(Keypair().pubkey())
    assert lb.clean_request({'address': me, 'vaultId': 1, 'col': '1', 'lev': 1.5})[:4] == ('open', me, 1, 0)
    for bad in ({'address': me, 'act': 'sell', 'vaultId': 1}, {'address': 'x', 'vaultId': 1}, {'address': me}, {'address': me, 'act': 'close', 'vaultId': 1}):
        with pytest.raises(ValueError):
            lb.clean_request(bad)
    b = lb.body_for('close', me, 1, 77)
    assert b['positionId'] == 77 and b['colAmount'] == b['debtAmount'] == str(-(2 ** 127))


def test_only_the_users_own_vault_transaction_passes():
    me = Keypair().pubkey()
    assert lb.verify(_tx(me, [CB, VAULTS, VAULTS]), str(me))[0]
    assert not lb.verify(_tx(me, [CB]), str(me))[0]                     # never calls Jupiter Lend vaults
    assert not lb.verify(_tx(me, [VAULTS, Keypair().pubkey()]), str(me))[0]
    assert not lb.verify(_tx(me, [VAULTS], extra_signer=Keypair().pubkey()), str(me))[0]


def test_positions_keep_known_vaults_and_skip_unknown_shapes():
    mk = {r['vaultId']: r for r in lb.markets(VLIST)}
    raw = [{'vaultId': 1, 'nftId': 10389}, {'vault': {'id': 40}, 'positionId': 5}, {'vaultId': 7, 'nftId': 3}, {'nope': 1}, 'x']
    assert lb.positions(raw, mk) == [{'vaultId': 1, 'nftId': 10389, 'coin': 'SOL'}, {'vaultId': 40, 'nftId': 5, 'coin': 'JUP'}]


def test_lend_keys_try_the_read_key_then_the_keeper_lanes():
    env = {'JUPITER_API_KEY': 'a', 'JUPITER_API_KEY_2': 'b', 'JUPITER_API_KEY_3': 'c'}
    assert jup_keys.lend_keys(env) == ['c', 'b', 'a'] and jup_keys.lend_keys({}) == []


def test_the_route_builds_verifies_and_falls_through_a_busy_key(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    me = Keypair().pubkey(); good = _tx(me, [CB, VAULTS]); bad = _tx(me, [VAULTS, Keypair().pubkey()])
    sent = []

    class R:
        def __init__(self, code, body):
            self.status_code, self._b = code, body

        def json(self):
            return self._b

    class H:
        def __init__(self, tx):
            self.tx = tx

        async def request(self, method, url, headers=None, timeout=None, json=None, params=None):
            sent.append((method, url, (headers or {}).get('x-api-key'), json))
            if url.endswith('/vaults'):
                return R(200, VLIST)
            if url.endswith('/positions'):
                return R(200, [{'vaultId': 1, 'nftId': 9}])
            return R(429, {}) if (headers or {}).get('x-api-key') == 'k2' else R(200, {'nftId': 10389, 'transaction': self.tx})
    monkeypatch.setenv('JUPITER_API_KEY', 'k1'); monkeypatch.setenv('JUPITER_API_KEY_2', 'k2')
    monkeypatch.delenv('JUPITER_READ_KEY', raising=False)
    for k in ('3', '4', '5', '6'):
        monkeypatch.delenv(f'JUPITER_API_KEY_{k}', raising=False)
    rs._flv_hits.clear(); rs._flv_vaults.clear()
    c = TestClient(rs.app)
    monkeypatch.setattr(rs, '_ai_http', lambda: H(good))
    g = c.get('/api/reputation/familia/leverage', params={'address': str(me)}).json()
    assert [m['coin'] for m in g['markets']] == ['SOL', 'BTC', 'JUP'] and g['positions'] == [{'vaultId': 1, 'nftId': 9, 'coin': 'SOL'}]
    r = c.post('/api/reputation/familia/leverage', json={'address': str(me), 'vaultId': 1, 'col': '0.5', 'lev': 1.5})
    assert r.status_code == 200 and r.json()['transaction'] == good and r.json()['nftId'] == 10389 and r.json()['plan']['debt'] == 25
    ops = [s for s in sent if s[1].endswith('/operate')]
    assert [s[2] for s in ops] == ['k2', 'k1']                          # the busy key fell through to the next one
    assert ops[-1][3] == {'signer': str(me), 'vaultId': 1, 'positionId': 0, 'colAmount': '500000000', 'debtAmount': '25000000'}
    r = c.post('/api/reputation/familia/leverage', json={'address': str(me), 'act': 'close', 'vaultId': 1, 'nftId': 9})
    assert r.status_code == 200 and r.json()['plan'] is None and sent[-1][3]['debtAmount'] == lb.ALL
    assert c.post('/api/reputation/familia/leverage', json={'address': str(me), 'vaultId': 2, 'col': '1', 'lev': 1.5}).status_code == 400
    assert c.post('/api/reputation/familia/leverage', json={'address': str(me), 'vaultId': 1, 'col': '0.5', 'lev': 3}).status_code == 400
    monkeypatch.setattr(rs, '_ai_http', lambda: H(bad))
    r = c.post('/api/reputation/familia/leverage', json={'address': str(me), 'vaultId': 1, 'col': '0.5', 'lev': 1.5})
    assert r.status_code == 502 and 'Refused before your wallet saw it' in r.json()['detail']

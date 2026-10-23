"""🌉 Bridge + ⛽ gas: LI.FI's Solana routes are opened before a wallet sees them, sent once, tracked; the gas station reads every tank
even when the keyed RPC is spent. The network is faked throughout — nothing reaches LI.FI, Solana or an EVM node."""
import asyncio
import base64
import struct

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

import lifi

ME = Keypair()
LIFI = Pubkey.from_string(lifi.LIFI_SVM)
RELAY = Pubkey.from_string('99vQwtBwYtrqqD9YSXbdum3KBdxPAVxYTaQ3cfnJSrN2')
SYSTEM = Pubkey.from_string(lifi.SYSTEM)
TOKEN = Pubkey.from_string(lifi.TOKEN)
EVM = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'


def _sys(tag, lamports, src, dst):
    return Instruction(SYSTEM, struct.pack('<IQ', tag, lamports), [AccountMeta(src, True, True), AccountMeta(dst, False, True)])


def _tok(tag, amount, owner):   # Transfer: source, destination, owner · TransferChecked: source, mint, destination, owner
    keys = [AccountMeta(Keypair().pubkey(), False, True) for _ in range(3 if tag == 12 else 2)]
    return Instruction(TOKEN, bytes([tag]) + struct.pack('<Q', amount), keys + [AccountMeta(owner, True, False)])


def _route(payer, ixs, extra=None, sign_with=None, blockhash=None):
    base = [Instruction(LIFI, b'\x01', [AccountMeta(payer, True, True)] + ([AccountMeta(extra, True, False)] if extra else []))]
    msg = MessageV0.try_compile(payer, base + ixs, [], blockhash or Hash.default())
    signers = [sign_with or NullSigner(payer)] + ([NullSigner(extra)] if extra else [])
    return base64.b64encode(bytes(VersionedTransaction(msg, signers))).decode()


def _relay_ix(payer):
    return Instruction(RELAY, b'\x02', [AccountMeta(payer, True, True)])


def test_only_the_users_lifi_route_passes():
    me = ME.pubkey(); other = Keypair().pubkey(); fee = Keypair().pubkey()
    ok = _route(me, [_sys(2, 50_000, me, fee), _relay_ix(me)])
    assert lifi.verify_svm(ok, str(me), lifi.SOL_NATIVE, 20_000_000)[:2] == (True, None)
    cases = [(_route(me, [_relay_ix(me), Instruction(Keypair().pubkey(), b'', [AccountMeta(me, True, True)])]), 'does not know'),
             (_route(other, [_relay_ix(other)]), 'fee payer'),
             (_route(me, [_relay_ix(me)], extra=other), 'besides you'),
             (_route(me, [_tok(4, 1, me)]), 'approves a spender'),
             (_route(me, [_tok(13, 1, me)]), 'approves a spender'),
             (_route(me, [_tok(6, 1, me)]), 'owner'),
             (_route(me, [Instruction(SYSTEM, struct.pack('<I', 1) + bytes(32), [AccountMeta(me, True, True)])]), 'hands your wallet'),
             (_route(me, [_sys(2, 20_000_000 + lifi.RENT_SLACK + 1, me, other)]), 'more SOL')]
    for tx, why in cases:
        got = lifi.verify_svm(tx, str(me), lifi.SOL_NATIVE, 20_000_000)
        assert got[0] is False and why in got[1], (why, got)
    msg = MessageV0.try_compile(me, [_relay_ix(me)], [], Hash.default())   # never goes through LI.FI
    assert 'LI.FI' in lifi.verify_svm(base64.b64encode(bytes(VersionedTransaction(msg, [NullSigner(me)]))).decode(), str(me))[1]
    usdc = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    assert lifi.verify_svm(_route(me, [_tok(12, 5_000_000, me)]), str(me), usdc, 5_000_000)[0]
    assert 'more tokens' in lifi.verify_svm(_route(me, [_tok(12, 5_000_001, me)]), str(me), usdc, 5_000_000)[1]
    assert lifi.verify_svm(_route(me, [_sys(2, 650_240, me, other), _tok(12, 5_000_000, me)]), str(me), usdc, 5_000_000)[0]   # rent beside a token route
    assert not lifi.verify_svm('nope', str(me))[0]
    assert not lifi.verify_svm(ok, str(me), signed=True)[0]                                       # the wallet never signed
    assert lifi.verify_svm(_route(me, [_relay_ix(me)], sign_with=ME), str(me), signed=True)[0]


def test_the_fingerprint_ignores_only_the_blockhash_and_a_quote_sends_once():
    me = ME.pubkey()
    a = VersionedTransaction.from_bytes(base64.b64decode(_route(me, [_relay_ix(me)])))
    b = VersionedTransaction.from_bytes(base64.b64decode(_route(me, [_relay_ix(me)], blockhash=Hash.new_unique())))
    c = VersionedTransaction.from_bytes(base64.b64decode(_route(me, [_relay_ix(me), _sys(2, 1, me, Keypair().pubkey())])))
    assert lifi.fingerprint(a.message) == lifi.fingerprint(b.message) != lifi.fingerprint(c.message)
    lifi._svm_quotes.clear()
    lifi.remember('fp1', 'me', now=1000)
    assert not lifi.take('fp1', 'someone-else', now=1001)
    assert lifi.take('fp1', 'me', now=1001) and not lifi.take('fp1', 'me', now=1002)    # once
    lifi.remember('fp2', 'me', now=1000)
    assert not lifi.take('fp2', 'me', now=1000 + 901)                                   # expired


class _R:
    def __init__(self, body, code=200):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


def _fake_http(monkeypatch, quotes, sends=None, status=None):
    """LI.FI + the Solana relay, faked: `quotes` is a list of quote bodies returned in order."""
    calls = []

    class Http:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None, headers=None):
            calls.append((url, dict(params or {})))
            if url.endswith('/quote'):
                return _R(quotes.pop(0))
            if url.endswith('/status'):
                return _R(status or {})
            return _R({'lifi': None})

        async def post(self, url, json=None):
            calls.append((url, json))
            return _R(sends.pop(0) if sends else {'result': 'SIG'})
    monkeypatch.setattr(lifi.httpx, 'AsyncClient', Http)
    monkeypatch.setattr(lifi, '_fee_bps', lambda: asyncio.sleep(0, 0))
    app = FastAPI()
    app.include_router(lifi.create_lifi_router())
    return TestClient(app), calls


def _quote(tx, tool='relaydepository', to=EVM, frm=None):
    return {'tool': tool, 'transactionRequest': {'data': tx}, 'action': {'fromAddress': frm or str(ME.pubkey()), 'toAddress': to}, 'estimate': {}}


def test_a_solana_quote_is_opened_remembered_sent_once_and_tracked(monkeypatch):
    me = ME.pubkey(); lifi._svm_quotes.clear()
    good = _route(me, [_relay_ix(me)])
    bad = _route(me, [_relay_ix(me), Instruction(Keypair().pubkey(), b'', [AccountMeta(me, True, True)])])
    c, calls = _fake_http(monkeypatch, [_quote(bad, 'mayanFastMCTP'), _quote(good)])
    q = {'fromChain': lifi.SOLANA, 'toChain': 8453, 'fromToken': lifi.SOL_NATIVE, 'toToken': lifi.NATIVE, 'fromAmount': '20000000',
         'fromAddress': str(me), 'toAddress': EVM}
    r = c.get('/api/lifi/quote', params=q)
    assert r.status_code == 200 and r.json()['feeless']['safety']['verified']
    assert [p.get('denyBridges') for u, p in calls if u.endswith('/quote')] == [None, 'mayanFastMCTP']   # the refused bridge is asked around
    assert calls[0][1]['toAddress'] == EVM
    signed = _route(me, [_relay_ix(me)], sign_with=ME, blockhash=Hash.new_unique())      # the wallet signs with a fresh blockhash
    c2, sent = _fake_http(monkeypatch, [], sends=[{'result': 'SIG1'}])
    assert c2.post('/api/lifi/solana/send', json={'signed': signed}).json() == {'signature': 'SIG1'}
    assert sent[0][1]['method'] == 'sendTransaction' and sent[0][0] == lifi.RELAY
    assert c2.post('/api/lifi/solana/send', json={'signed': signed}).status_code == 409             # no resubmits
    other = _route(me, [_relay_ix(me), _sys(2, 1, me, Keypair().pubkey())], sign_with=ME)
    assert c2.post('/api/lifi/solana/send', json={'signed': other}).status_code in (400, 409)       # never quoted
    c3, _ = _fake_http(monkeypatch, [], status={'status': 'DONE', 'receiving': {'txHash': '0xabc', 'amount': '850000000000000', 'token': {'decimals': 18, 'symbol': 'ETH'}}})
    st = c3.get('/api/lifi/status', params={'txHash': '5' * 88, 'fromChain': lifi.SOLANA, 'toChain': 8453}).json()
    assert st['status'] == 'DONE' and st['receiving'] == '0xabc' and st['got'] == pytest.approx(0.00085) and st['symbol'] == 'ETH'


def test_quotes_refuse_another_payout_wallet_and_dead_chains(monkeypatch):
    me = ME.pubkey(); lifi._svm_quotes.clear()
    c, _ = _fake_http(monkeypatch, [_quote(_route(me, [_relay_ix(me)]), to='0x' + '1' * 40)])
    q = {'fromChain': lifi.SOLANA, 'toChain': 8453, 'fromToken': lifi.SOL_NATIVE, 'toToken': lifi.NATIVE, 'fromAmount': '20000000', 'fromAddress': str(me), 'toAddress': EVM}
    r = c.get('/api/lifi/quote', params=q)
    assert r.status_code == 502 and 'different wallet' in r.json()['detail'] and not lifi._svm_quotes
    assert c.get('/api/lifi/quote', params={**q, 'toAddress': ''}).status_code == 400                # Solana → EVM needs your EVM side
    assert c.get('/api/lifi/quote', params={**q, 'toChain': 7777777}).status_code == 400            # Zora: LI.FI no longer routes it
    evm_q = {'transactionRequest': {'to': '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE', 'chainId': 8453}, 'estimate': {},
             'action': {'fromAddress': EVM, 'toAddress': str(me)}}
    c2, _ = _fake_http(monkeypatch, [evm_q])
    back = c2.get('/api/lifi/quote', params={'fromChain': 8453, 'toChain': lifi.SOLANA, 'fromToken': lifi.NATIVE, 'toToken': lifi.SOL_NATIVE,
                                             'fromAmount': '2000000000000000', 'fromAddress': EVM, 'toAddress': str(me)})
    assert back.status_code == 200 and back.json()['feeless']['safety']['contract'].lower() == '0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'


def test_the_gas_station_reads_every_tank_when_the_keyed_rpc_is_spent(monkeypatch):
    import reputation_service as rs
    hit = []

    class Http:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None):
            hit.append(url)
            if 'publicnode' in url or 'era.zksync' in url or 'drpc' in url:
                return _R({'result': hex(10 ** 16)})
            raise RuntimeError('quota')
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Http)
    monkeypatch.setattr(rs, '_native_prices', lambda http: asyncio.sleep(0, {'ETH': 3000, 'BNB': 600, 'AVAX': 25, 'POL': 0.2, 'CRO': 0.1}))
    monkeypatch.setattr(rs, '_rpc', lambda http, m, p: asyncio.sleep(0, {'value': 2 * 10 ** 9}))
    monkeypatch.setattr(rs, '_sol_usd', lambda: asyncio.sleep(0, 150.0))
    monkeypatch.setattr(rs, 'EVM_RPC', {c: f'https://{c}.keyed.invalid' for c in rs.EVM_RPC})
    d = asyncio.run(rs.gas_check(EVM, sol=str(ME.pubkey())))
    chains = {c['chain']: c for c in d['chains']}
    assert 'zora' not in chains and len(chains) == 11 and all(c['balance'] == 0.01 for c in chains.values())
    assert chains['base']['usd'] == 30.0 and chains['base']['enough']
    assert d['solana'] == {'chain': 'solana', 'symbol': 'SOL', 'address': str(ME.pubkey()), 'balance': 2.0, 'usd': 300.0}
    assert asyncio.run(rs.gas_check(EVM))['solana'] is None

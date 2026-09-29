"""Trading engine: Swap API first (FEELESS fee + our broadcast), Ultra only as an opt-in fallback.
Jupiter and the RPC are faked; nothing leaves the process."""
import base64
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('JUPITER_API_KEY', 'test'); os.environ.setdefault('SOLANA_RPC_URL', 'http://rpc.test')
pytest.importorskip('solders')
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from solders.hash import Hash  # noqa: E402
from solders.keypair import Keypair  # noqa: E402
from solders.message import MessageV0  # noqa: E402
from solders.signature import Signature  # noqa: E402
from solders.transaction import VersionedTransaction  # noqa: E402

import trading  # noqa: E402

SOL = 'So11111111111111111111111111111111111111112'
MEME = '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump'
WALLET = 'Wa11et1111111111111111111111111111111111111'


class Orders:
    def __init__(self):
        self.rows = {}

    async def insert_one(self, r):
        self.rows[r['order_id']] = dict(r)

    async def find_one(self, q, proj=None):
        return self.rows.get(q['order_id'])

    async def update_one(self, q, u):
        self.rows[q['order_id']].update(u['$set'])

    async def find_one_and_update(self, q, u, **_):
        r = self.rows.get(q['order_id'])
        if not r or r['state'] != q.get('state', r['state']):
            return None
        r.update(u['$set'])
        return r


@pytest.fixture
def engine():
    db = type('DB', (), {'swap_orders': Orders()})()
    svc = trading.TradingService(db)
    state = {'calls': [], 'swap_down': False, 'rpc': [],
             'fee': {'bps': 1500, 'ultraBps': 255, 'feeAccount': 'FeeAcct', 'referralAccount': 'Ref', 'engine': 'swap',
                     'ultraFallback': False, 'priorityMaxLamports': 150000, 'notes': []}}

    async def metadata(m):
        return {'mint': m, 'decimals': 9 if m == SOL else 6}

    async def jupiter(method, path, params=None, json=None, **_):
        state['calls'].append((path, params, json))
        if path.startswith('/swap/v1') and state['swap_down']:
            raise HTTPException(503, 'Swap API down.')
        if path == '/swap/v1/quote':
            return {'outAmount': '1000', 'otherAmountThreshold': '990', 'swapUsdValue': '1.2'}
        if path == '/swap/v1/swap':
            if json.get('feeAccount') in state.get('rejected', ()):
                raise HTTPException(400, 'Invalid feeAccount for this route.')
            return {'swapTransaction': 'VFg=', 'lastValidBlockHeight': 100, 'prioritizationFeeLamports': 150000}
        if path == '/swap/v2/order':
            return {'outAmount': '999', 'transaction': 'VUw=', 'requestId': 'r'}

    async def fee_rule(_body):
        return dict(state['fee'])

    async def rpc(method, params):
        state['rpc'].append(method)
        return {'value': [{'confirmationStatus': 'confirmed'}]} if method == 'getSignatureStatuses' else 'sig'

    svc.metadata, svc.jupiter, svc.fee_rule, svc.rpc = metadata, jupiter, fee_rule, rpc
    app = FastAPI()
    app.include_router(svc.router())
    return TestClient(app), state, db


def quote(client):
    return client.post('/api/trading/quote', json={'input_mint': SOL, 'output_mint': MEME, 'amount': '0.01', 'slippage_bps': 100, 'wallet': WALLET})


def test_swap_api_charges_the_feeless_fee_and_caps_priority(engine):
    client, state, _ = engine
    body = quote(client).json()
    built = next(j for p, _, j in state['calls'] if p == '/swap/v1/swap')
    assert body['engine'] == 'swap' and body['feeless_fee']['bps'] == 1500
    assert next(q for p, q, _ in state['calls'] if p == '/swap/v1/quote')['platformFeeBps'] == 1500
    assert built['feeAccount'] == 'FeeAcct'
    assert built['prioritizationFeeLamports'] == {'priorityLevelWithMaxLamports': {'maxLamports': 150000, 'priorityLevel': 'high'}}
    assert not any(p == '/swap/v2/order' for p, _, _ in state['calls'])


def test_trading_pauses_when_swap_api_fails_and_fallback_is_off(engine):
    client, state, _ = engine
    state['swap_down'] = True
    res = quote(client)
    assert res.status_code == 503 and 'Nothing was sent' in res.json()['detail']
    assert not any(p == '/swap/v2/order' for p, _, _ in state['calls'])


def test_ultra_fallback_only_when_switched_on(engine):
    client, state, _ = engine
    state['swap_down'] = True
    state['fee']['ultraFallback'] = True
    body = quote(client).json()
    ultra = next(q for p, q, _ in state['calls'] if p == '/swap/v2/order')
    assert body['engine'] == 'ultra' and body['feeless_fee']['bps'] == 255 and ultra['referralFee'] == 255


def test_swap_engine_broadcasts_itself_and_refuses_replays(engine):
    client, state, db = engine
    kp = Keypair()
    msg = MessageV0.try_compile(kp.pubkey(), [], [], Hash.default())
    order_id = 'e' * 36
    db.swap_orders.rows[order_id] = {'order_id': order_id, 'state': 'quoted', 'wallet': str(kp.pubkey()), 'expires_at': time.time() + 30,
                                     'simulated': True, 'engine': 'swap', 'quote': {
                                         'transaction': base64.b64encode(bytes(VersionedTransaction.populate(msg, [Signature.default()]))).decode(),
                                         'lastValidBlockHeight': 10**9}}
    signed = base64.b64encode(bytes(VersionedTransaction(msg, [kp]))).decode()
    first = client.post('/api/trading/execute', json={'order_id': order_id, 'signed_transaction': signed}).json()
    assert first['state'] == 'confirmed' and 'sendTransaction' in state['rpc']
    assert not any(p == '/swap/v2/execute' for p, _, _ in state['calls'])
    again = client.post('/api/trading/execute', json={'order_id': order_id, 'signed_transaction': signed}).json()
    assert again['detail'].startswith('Already processed')


def test_fee_is_locked_a_rejected_fee_account_never_lets_the_trade_through_free(engine):
    client, state, _ = engine
    state['rejected'] = {'FeeAcct'}
    res = quote(client)
    assert res.status_code == 503 and 'fee account rejected' in res.json()['detail']
    assert not any(p == '/swap/v1/swap' and 'feeAccount' not in (j or {}) for p, _, j in state['calls'])


def test_second_fee_account_is_tried_before_giving_up(engine):
    client, state, _ = engine
    state['fee']['feeAccounts'] = ['FeeAcct', 'UsdcAcct']
    state['rejected'] = {'FeeAcct'}
    body = quote(client).json()
    assert body['feeless_fee']['bps'] == 1500
    assert [j['feeAccount'] for p, _, j in state['calls'] if p == '/swap/v1/swap'] == ['FeeAcct', 'UsdcAcct']


def test_rejected_fee_goes_to_ultra_only_when_the_fallback_is_on(engine):
    client, state, _ = engine
    state['rejected'] = {'FeeAcct'}
    state['fee']['ultraFallback'] = True
    body = quote(client).json()
    assert body['engine'] == 'ultra' and body['feeless_fee']['bps'] == 255

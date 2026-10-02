"""Circle wallets: labels persist; sends need a valid address, a positive amount and the typed confirmation."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip('solders')
rs = pytest.importorskip('reputation_service')
TO = 'Dest111111111111111111111111111111111111WXYZ'


def test_meta_and_send_guards(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'CIRCLE_META_PATH', tmp_path / 'c.json')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'audit': []}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    sent = []

    async def circle(method, path, body=None):
        sent.append((path, body)); return {'id': 'tx1', 'state': 'INITIATED'}
    monkeypatch.setattr(rs, '_circle', circle)
    asyncio.run(rs.circle_wallet_meta(None, 'w1', rs.CircleMetaIn(name='Ops wallet', description='gas + airdrops')))
    assert asyncio.run(rs.circle_meta_get(None))['w1']['description'] == 'gas + airdrops'
    for bad in (dict(to='nope', confirm='nope'[-4:], amount='1'), dict(to=TO, confirm='0000', amount='1'), dict(to=TO, confirm='WXYZ', amount='-2')):
        with pytest.raises(rs.HTTPException):
            asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', **bad)))
    monkeypatch.setattr(rs, 'CIRCLE_DEST_PATH', tmp_path / 'd.json')
    monkeypatch.setattr(rs, '_seasons', lambda: {'seasons': []}); monkeypatch.setattr(rs, '_pools', lambda: {'pools': []})
    monkeypatch.setattr(rs, 'ROUTES_PATH', tmp_path / 'r.json'); monkeypatch.setattr(rs, '_owner_wallets', lambda: {'Owner'}); monkeypatch.setattr(rs, '_admin_wallets', lambda: {'Owner'})
    with pytest.raises(rs.HTTPException) as unknown:   # not a HQ wallet and not saved → refused
        asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', to=TO, amount='2.5', confirm='WXYZ')))
    assert unknown.value.status_code == 403
    asyncio.run(rs.circle_destination_save(None, rs.CircleDestIn(address=TO, label='Cold wallet')))
    out = asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', to=TO, amount='2.5', confirm='WXYZ')))
    assert out['state'] == 'INITIATED' and sent[-1][0] == '/transfer' and sent[-1][1]['amount'] == '2.5'


def test_reserve_pays_via_circle_once(monkeypatch, tmp_path):
    """Reserve wallet is a Circle wallet: typed PAY <total>, one Circle send per holder, failed rows retry alone."""
    RES = 'Resv111111111111111111111111111111111111111'
    A, B = 'Aaaa111111111111111111111111111111111111111', 'Bbbb111111111111111111111111111111111111111'
    store = {'seasons': [{'id': 's1', 'reserveWallet': RES}]}
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_seasons', lambda: store)
    monkeypatch.setattr(rs, '_json_save', lambda path, d: None)
    monkeypatch.setattr(rs, '_json_load', lambda path, default=None: {})
    monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)

    async def plan(s, d):
        return {'rows': [{'address': A, 'tier': 'Gold', 'sol': 0.2}, {'address': B, 'tier': 'Bronze', 'sol': 0.1}]}
    monkeypatch.setattr(rs, '_reserve_plan', plan)
    sent, fail_b = [], [True]

    async def circle(method, path, body=None):
        if path == '/wallets':
            return {'wallets': [{'id': 'cw', 'address': RES, 'blockchain': 'SOL', 'balances': [{'symbol': 'SOL', 'tokenId': 'sol', 'amount': '1'}]}]}
        if body['to'] == B and fail_b[0]:
            raise rs.HTTPException(502, 'Circle down')
        sent.append(body); return {'id': 'tx-' + body['to'][:4], 'state': 'INITIATED'}
    monkeypatch.setattr(rs, '_circle', circle)
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 1')))
    out = asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 0.3')))
    assert out['wallets'] == 1 and out['failed'][0]['address'] == B and sent[0]['amount'] == '0.2'
    fail_b[0] = False
    out = asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 0.1')))
    assert out['ok'] and [s['to'] for s in sent] == [A, B]
    with pytest.raises(rs.HTTPException):   # everything paid: nothing to send twice
        asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 0')))
    assert len(store['reservePayouts']['s1']['rows']) == 2


def test_circle_autostarts_when_down(monkeypatch):
    """Owner call while the sidecar is down: it's started once, then the request goes through."""
    import httpx
    started, calls = [], []

    async def start():
        started.append(1); return True

    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def request(self, method, url, json=None):
            calls.append(url)
            if not started:
                raise httpx.ConnectError('down')
            return httpx.Response(200, json={'ok': True})
    monkeypatch.setattr(rs, '_circle_start', start)
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Client)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(rs.asyncio, 'sleep', lambda s: real_sleep(0))
    assert asyncio.run(rs._circle('GET', '/status')) == {'ok': True} and len(started) == 1


def test_money_pulse_one_read_for_every_card(monkeypatch):
    """Pulse: one getMultipleAccounts for all wallets, Circle listed, reserve plan fed from that read."""
    RES = 'Resv111111111111111111111111111111111111111'
    rpc_calls = []
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_owner_wallets', lambda: {'Owner'})
    monkeypatch.setattr(rs, '_fee_cfg', lambda: {'platformFeeBps': 50, 'engine': 'swap'})
    monkeypatch.setattr(rs, '_seasons', lambda: {'seasons': [{'id': 's1', 'name': 'S1', 'reserveWallet': RES, 'badgeRewardPct': 10, 'start': 0, 'end': 1}], 'scores': {}})
    monkeypatch.setattr(rs, '_pools', lambda: {'pools': []})
    monkeypatch.setattr(rs, '_json_load', lambda path, default=None: {} if default is None else default)
    rs._pulse_cache.clear()

    async def rpc(http, method, params):
        rpc_calls.append(method); return {'value': [{'lamports': 3_000_000_000, 'data': ['', 'base64']} for _ in params[0]]}

    async def circle(method, path, body=None):
        return {'wallets': [{'id': 'c', 'address': RES, 'blockchain': 'SOL', 'balances': []}]}
    monkeypatch.setattr(rs, '_rpc', rpc); monkeypatch.setattr(rs, '_circle', circle)
    out = asyncio.run(rs.admin_money_pulse(None))
    assert rpc_calls == ['getMultipleAccounts']
    assert out['reserves']['s1']['poolSol'] == 3.0 and out['circle']['up'] and out['circle']['wallets'][0]['address'] == RES
    assert any(c['key'] == 'jup' for c in out['checks'])
    assert asyncio.run(rs.admin_money_pulse(None)).get('cached')


def test_card_edit_and_catalog(monkeypatch, tmp_path):
    """Owner edits a badge card; the catalog carries the look plus what the card earns from pools."""
    monkeypatch.setattr(rs, 'CARDS_PATH', tmp_path / 'cards.json')
    monkeypatch.setattr(rs, 'COLLECTION_PATH', tmp_path / 'col.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'badges': {'W1': {'custom-og': {'id': 'custom-og', 'label': 'OG', 'icon': '⭐', 'tone': 'gold'}}}})
    monkeypatch.setattr(rs, '_admin_save', lambda d: None); monkeypatch.setattr(rs, '_audit', lambda *a: None)
    monkeypatch.setattr(rs, '_seasons', lambda: {'seasons': [], 'scores': {}})
    monkeypatch.setattr(rs, '_pools', lambda: {'pools': [{'name': 'OG pool', 'mode': 'pct', 'weights': {'badge:custom-og': 30}, 'payouts': [{'perKey': {'badge:custom-og': 0.2}}]}]})
    rs._cards_cache.clear()

    class Req:
        async def json(self): return {'title': 'Original Gangster', 'design': 'glitch', 'lore': 'Here before the chart.'}
    card = asyncio.run(rs.admin_card_edit(Req(), 'badge:custom-og'))
    assert card['title'] == 'Original Gangster' and card['design'] == 'glitch' and card['holders'] == 1
    assert card['earnedEach'] == 0.2 and card['earns'][0]['pct'] == 30
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_card_edit(Req(), 'nope:<script>'))


def test_launch_check_pump(monkeypatch):
    """Receipt check: mint on-chain + listed on pump.fun + DexScreener, each answered independently."""
    import httpx
    MINT = 'Mint1111111111111111111111111111111111pump'

    async def rpc(http, method, params):
        return {'value': {'lamports': 1}}

    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url):
            if 'pump.fun' in url:
                return httpx.Response(200, json={'mint': MINT})
            return httpx.Response(200, json={'pairs': None})
    monkeypatch.setattr(rs, '_rpc', rpc); monkeypatch.setattr(rs.httpx, 'AsyncClient', Client)
    out = asyncio.run(rs.launch_check(MINT, 'pump'))
    assert out['onChain'] and out['onPump'] and out['onDex'] is False and out['pumpUrl'].endswith(MINT)
    assert asyncio.run(rs.launch_check(MINT, 'feeless'))['onPump'] is None


def test_nft_crossmint_create_drop_and_metaplex_record(monkeypatch, tmp_path):
    """Crossmint: created + dropped through its API (typed DROP n). Metaplex: only what the owner's wallet signed is recorded."""
    IMG = '/api/reputation/uploads/' + 'a' * 32 + '.png'
    W1, W2 = 'Aaaa1111111111111111111111111111111111111111', 'Bbbb1111111111111111111111111111111111111111'
    monkeypatch.setattr(rs, 'NFT_PATH', tmp_path / 'nft.json')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner1111111111111111111111111111111111111111')
    monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    monkeypatch.setenv('PUBLIC_SITE_URL', 'https://feeless.xyz'); monkeypatch.setenv('CROSSMINT_API_KEY', 'sk_staging_x')
    calls = []

    async def api(platform, method, path, body=None):
        calls.append((platform, path, body))
        return {'id': 'cm-col-1'} if path.endswith('/collections') else {'id': f"nft-{len(calls)}"}
    monkeypatch.setattr(rs, '_nft_api', api)

    class Req:
        headers = {}
        def __init__(self, body): self.body = body
        async def json(self): return self.body
    c = asyncio.run(rs.nft_create(Req({'name': 'OG Cards', 'symbol': 'OG', 'platform': 'crossmint', 'image': IMG, 'supply': 5})))
    assert c['address'] == 'cm-col-1' and c['status'] == 'live' and calls[0][2]['metadata']['imageUrl'] == 'https://feeless.xyz' + IMG
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.nft_drop(Req({}), c['id'], rs.NftDropIn(to=[W1, W2], confirm='DROP 1')))
    out = asyncio.run(rs.nft_drop(Req({}), c['id'], rs.NftDropIn(to=[W1, W2, 'junk'], confirm='DROP 2')))
    assert out['minted'] == 2 and calls[-1][2]['recipient'] == f'solana:{W2}'

    mp = asyncio.run(rs.nft_create(Req({'name': 'Core Cards', 'symbol': 'CORE', 'platform': 'metaplex', 'image': IMG})))
    assert mp['status'] == 'draft'
    COL = 'Coxx1111111111111111111111111111111111111111'

    async def verify(sig, signer, touch):
        assert signer.startswith('Owner') and COL in touch
    monkeypatch.setattr(rs, '_nft_verify', verify)
    rec = asyncio.run(rs.nft_onchain(Req({}), mp['id'], rs.NftOnchainIn(address=COL, signature='5' * 88)))
    assert rec['address'] == COL and rec['status'] == 'live'
    meta = asyncio.run(rs.nft_meta(f"{mp['id']}-3.json", type('R', (), {'base_url': 'http://x/'})()))
    assert meta['name'] == 'Core Cards #3'


def test_confirmed_trade_notifies_once_and_refreshes_holdings(monkeypatch, tmp_path):
    """The trading service reports a confirmed trade: the fee lands in the ledger, the trader gets ONE notice
    (deduped by signature with the receipt's), and their cached holdings are dropped."""
    W = 'Aaaa1111111111111111111111111111111111111111'
    SIG = '5' * 88
    monkeypatch.setattr(rs, 'FEE_LEDGER_PATH', tmp_path / 'l.json'); monkeypatch.setattr(rs, 'REF_PATH', tmp_path / 'r.json')
    monkeypatch.setattr(rs, 'REF_CFG_PATH', tmp_path / 'rc.json'); monkeypatch.setattr(rs, 'NOTIF_PATH', tmp_path / 'n.json')
    monkeypatch.setattr(rs, 'SEASONS_PATH', tmp_path / 's.json'); monkeypatch.setattr(rs, 'season_award', lambda *a: None)
    monkeypatch.setattr(rs, '_seasons', lambda: rs._json_load(tmp_path / 's.json', {'seasons': [], 'scores': {}}))
    monkeypatch.setattr(rs, '_internal_key', lambda: 'k')
    rs._pf_cache[W] = (0, {'stale': True})

    class Req:
        headers = {'x-feeless-internal': 'k'}
    body = rs.TradeLanded(wallet=W, signature=SIG, inUsd=100, feeBps=50, inputMint=rs.WSOL, outputMint='Coin1111111111111111111111111111111111111111')
    asyncio.run(rs.internal_trade(Req(), body))
    asyncio.run(rs.internal_trade(Req(), body))   # duplicate report: ignored
    box = rs._json_load(tmp_path / 'n.json', {})[W]
    assert len(box) == 1 and box[0]['text'].startswith('✅ Buy confirmed') and W not in rs._pf_cache
    assert rs._json_load(tmp_path / 'l.json', {})[W][0]['feeUsd'] == 0.5


def test_feeless_trade_feeds_the_position(monkeypatch, tmp_path):
    """A confirmed FEELESS buy gives an instant position (avg entry + chart pin), even when the wallet-history
    provider has nothing yet."""
    W, COIN = 'Aaaa1111111111111111111111111111111111111111', 'Coin1111111111111111111111111111111111111111'
    for k in ('FEE_LEDGER_PATH', 'FEE_TOTALS_PATH', 'FEELESS_TRADES_PATH', 'REF_PATH', 'REF_CFG_PATH', 'NOTIF_PATH', 'SEASONS_PATH'):
        monkeypatch.setattr(rs, k, tmp_path / f'{k}.json')
    monkeypatch.setattr(rs, 'season_award', lambda *a: None); monkeypatch.setattr(rs, '_internal_key', lambda: 'k')
    monkeypatch.setattr(rs, '_seasons', lambda: rs._json_load(tmp_path / 'SEASONS_PATH.json', {'seasons': [], 'scores': {}}))

    async def no_history(a, limit=40):
        raise RuntimeError('provider down')
    monkeypatch.setattr(rs, 'wallet_trades', no_history)

    class Req:
        headers = {'x-feeless-internal': 'k'}
    asyncio.run(rs.internal_trade(Req(), rs.TradeLanded(wallet=W, signature='5' * 88, inUsd=50, feeBps=50, inputMint=rs.WSOL, outputMint=COIN, inAmount=0.4, outAmount=1000)))
    pos = asyncio.run(rs.position(W, COIN))['position']
    # quote-only estimate: $50 + the 0.5% FEELESS fee over 1000 coins, never rosier than reality; flagged as not exact
    assert pos['avgEntry'] == 0.05025 and pos['buys'] == 1 and pos['trades'][0]['side'] == 'buy' and pos['exact'] is False
    # the exact on-chain fill saved at confirmation replaces the estimate: $57.50 really left the wallet for 1000 coins
    fill = {'side': 'buy', 'tokens': 1000.0, 'sol': 0.46, 'usd': 57.5, 'networkSol': 0.00001, 'token': COIN, 'tx': '6' * 88}
    asyncio.run(rs.internal_trade(Req(), rs.TradeLanded(wallet=W, signature='6' * 88, inUsd=50, feeBps=50, inputMint=rs.WSOL, outputMint=COIN, inAmount=0.4, outAmount=1000, fill=fill)))
    rows = rs._json_load(rs.FEELESS_TRADES_PATH, {})[W]
    assert rows[-1]['via'] == 'chain' and rows[-1]['usd'] == 57.5 and rows[-1]['price'] == 0.0575

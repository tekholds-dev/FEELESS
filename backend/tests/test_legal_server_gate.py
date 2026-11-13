"""⚖ LEGAL-1 (d): the server holds a money route for a wallet the legal gate holds (a direct API call can't skip the browser), and an exit
(a sell back into SOL / USDC, closing a perp, a withdraw) is never held. Network faked; stores are the conftest sandbox."""
from fastapi import HTTPException

import legal as L
import test_trading_engine as te

engine = te.engine   # the swap engine on fakes, as a fixture here too

ME = 'A' * 32


def _state(accepted=False, country='US', blocked=None):
    s = L.new_state()
    if blocked:
        for f, cs in blocked.items():
            s['cfg']['features'][f]['blocked'] = cs
    if accepted:
        L.accept(s, ME, L.VERSION, country, True, True, now=1)
    return s


def test_hold_is_the_browser_gate_on_the_stored_acceptance():
    assert 'accept the terms' in L.hold(_state(), 'swap', ME)
    assert L.hold(_state(accepted=True), 'swap', ME) == ''
    assert L.hold(_state(accepted=True, country='GB', blocked={'perps': ['GB']}), 'perps', ME) == 'Perps + leverage (Jupiter Perps / Lend) are closed in GB.'   # its own stated country counts
    assert L.hold(_state(accepted=True), 'swap', ME, country='IR') == 'FEELESS is not available in IR.'
    assert L.hold(_state(), 'site', ME) == ''
    gb = _state(accepted=True, country='GB', blocked={'perps': ['GB']})
    assert 'closed in GB' in L.hold(gb, 'perps', ME, country='US') and 'closed in GB' in L.hold(gb, 'perps', ME, country='XX')   # a header never hides the stated country
    assert set(L.PERPS_EXITS) == {'decrease-position', 'create-tpsl', 'cancel-tpsl', 'update-tpsl'} and 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' in L.EXIT_MINTS


def test_the_swap_engine_refuses_a_held_buy_but_never_a_sell_back_to_sol(engine, monkeypatch):
    client, state, _ = engine
    state['legal'] = 'Swaps (Jupiter route, user-signed) are closed in GB.'
    r = te.quote(client)
    assert r.status_code == 403 and 'closed in GB' in r.json()['detail'] and not any(p.startswith('/swap/') for p, _, _ in state['calls'])
    sell = client.post('/api/trading/quote', json={'input_mint': te.MEME, 'output_mint': te.SOL, 'amount': '1', 'slippage_bps': 100, 'wallet': te.WALLET})
    assert sell.status_code == 200 and state['legal_asked'] == [te.WALLET]   # the sell was never asked about
    import trading
    monkeypatch.setattr(trading, '_internal_key', lambda: 'k')
    agent = client.post('/api/trading/quote', headers={'x-feeless-internal': 'k'}, json={'input_mint': te.SOL, 'output_mint': te.MEME, 'amount': '0.01', 'slippage_bps': 100, 'wallet': te.WALLET})
    assert agent.status_code == 200 and state['legal_asked'] == [te.WALLET]   # an agent's internal quote skips it (gated when its owner funded it)
    state['legal'] = ''
    assert te.quote(client).status_code == 200


def test_only_a_pass_is_cached_so_a_wallet_that_just_accepted_trades_at_once(monkeypatch):
    import asyncio

    import trading
    answers = ['Confirm you are 18+ and accept the terms first.', '']; asked = []

    class Rep:
        def __init__(self, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            asked.append(1); why = answers.pop(0) if answers else ''
            return type('R', (), {'status_code': 200, 'json': lambda self: {'why': why}})()
    monkeypatch.setattr(trading.httpx, 'AsyncClient', Rep)
    svc = trading.TradingService(None); req = type('R', (), {'headers': {}})()
    assert asyncio.run(svc.legal_why(ME, req)) != ''          # held
    assert asyncio.run(svc.legal_why(ME, req)) == ''          # accepted a second later: asked again, goes on
    assert asyncio.run(svc.legal_why(ME, req)) == '' and len(asked) == 2   # the pass is kept


def test_the_swap_engine_goes_on_when_the_legal_service_is_down(monkeypatch):
    import trading

    class Down:
        def __init__(self, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            raise trading.httpx.ConnectError('down')
    monkeypatch.setattr(trading.httpx, 'AsyncClient', Down)
    svc = trading.TradingService(None)
    req = type('R', (), {'headers': {}})()
    import asyncio
    assert asyncio.run(svc.legal_why(ME, req)) == ''


def test_reputation_money_routes_hold_entries_and_never_exits(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(rs, '_legal_state', None)
    monkeypatch.setattr(rs, '_any_agent_wallets', lambda: set())
    c = TestClient(rs.app)
    # perps: opening is held, closing goes on to the transaction check (which refuses the junk bytes, not the law)
    r = c.post('/api/reputation/familia/perps-real/execute', json={'action': 'increase-position', 'signed': 'x', 'address': ME})
    assert r.status_code == 403 and 'accept the terms' in r.json()['detail']
    r = c.post('/api/reputation/familia/perps-real/execute', json={'action': 'decrease-position', 'signed': 'x', 'address': ME})
    assert r.status_code == 400 and r.json()['detail'].startswith('Refused')
    r = c.post('/api/reputation/familia/perps-real/execute', json={'action': 'create-tpsl', 'signed': 'x', 'address': ME})
    assert r.status_code == 400 and r.json()['detail'].startswith('Refused')   # a stop-loss on a held position is an exit
    assert c.post('/api/reputation/familia/perps-real', json={'act': 'grow', 'address': ME}).status_code == 403   # any open-shaped build is checked
    r = c.post('/api/reputation/familia/perps-real/execute', json={'action': 'increase-position', 'signed': 'x', 'address': ME}, headers={'cf-ipcountry': 'US'})
    assert r.status_code == 403
    # lend: a deposit is held; a withdraw goes on (stopped here before any network call)

    async def no_hub():
        raise HTTPException(418, 'past the gate')
    monkeypatch.setattr(rs, 'familia_pools', no_hub)
    dep = {'address': ME, 'asset': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'amount': '1'}
    assert c.post('/api/reputation/familia-pools/earn', json={**dep, 'side': 'deposit'}).status_code == 403
    assert c.post('/api/reputation/familia-pools/earn', json={**dep, 'side': 'withdraw'}).status_code == 418
    # the internal gate the swap engine asks: key only, then the same answer
    monkeypatch.setattr(rs, '_internal_key', lambda: 'k')
    assert c.get(f'/api/reputation/internal/legal-gate?wallet={ME}').status_code == 403
    out = c.get(f'/api/reputation/internal/legal-gate?wallet={ME}&feature=swap', headers={'x-feeless-internal': 'k'}).json()
    assert out['ok'] is False and 'accept the terms' in out['why']
    rs._legal_s()['accept'][ME] = {'v': L.VERSION, 'country': 'US', 'adult': True, 'notRestricted': True, 'at': 1}
    assert c.get(f'/api/reputation/internal/legal-gate?wallet={ME}&feature=swap&country=IR', headers={'x-feeless-internal': 'k'}).json()['why'] == 'FEELESS is not available in IR.'
    assert c.get(f'/api/reputation/internal/legal-gate?wallet={ME}&feature=swap', headers={'x-feeless-internal': 'k'}).json() == {'ok': True, 'why': ''}
    assert c.post('/api/reputation/familia-pools/earn', json={**dep, 'side': 'deposit'}).status_code == 418   # accepted: past the gate


def test_agent_trades_quote_with_the_internal_key():
    from pathlib import Path
    src = (Path(__file__).parent.parent / 'agent_trade.py').read_text()
    assert "json={'input_mint': i, 'output_mint': o, 'amount': amount, 'wallet': addr, 'slippage_bps': SLIP_BPS}, headers=_internal_headers()" in src

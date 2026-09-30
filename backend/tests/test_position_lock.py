"""Position rows: a trade already counted for points still gets its entry saved, and locked rows always win.
All network is faked."""
import asyncio

import pytest

pytest.importorskip('solders')
rs = pytest.importorskip('reputation_service')

W, COIN = 'Aaaa1111111111111111111111111111111111111111', 'Coin1111111111111111111111111111111111111111'


def _isolate(monkeypatch, tmp_path):
    for k in ('FEE_LEDGER_PATH', 'FEE_TOTALS_PATH', 'FEELESS_TRADES_PATH', 'REF_PATH', 'REF_CFG_PATH', 'NOTIF_PATH', 'SEASONS_PATH'):
        monkeypatch.setattr(rs, k, tmp_path / f'{k}.json')
    monkeypatch.setattr(rs, 'season_award', lambda *a: None); monkeypatch.setattr(rs, '_internal_key', lambda: 'k')
    monkeypatch.setattr(rs, '_seasons', lambda: rs._json_load(tmp_path / 'SEASONS_PATH.json', {'seasons': [], 'scores': {}}))

    async def fixed_sol():
        return 150.0
    monkeypatch.setattr(rs, '_sol_usd', fixed_sol)


class Req:
    headers = {'x-feeless-internal': 'k'}


def test_a_trade_already_counted_for_points_still_gets_its_locked_entry(monkeypatch, tmp_path):
    """Owner's bug: the PAID buy's signature was already in the points list, so every later save was skipped as a
    duplicate and the trade never got an entry row."""
    _isolate(monkeypatch, tmp_path)
    rs._json_save(tmp_path / 'SEASONS_PATH.json', {'seasons': [], 'scores': {}, 'tradeSigs': ['paid']})
    fill = {'side': 'buy', 'tokens': 103.9455, 'sol': 0.007675, 'usd': 1.15125, 'poolUsd': 1.1505, 'solUsd': 150.0, 'priced': 'signing', 'locked': True, 'token': COIN, 'tx': 'paid'}
    out = asyncio.run(rs.internal_trade(Req(), rs.TradeLanded(wallet=W, signature='paid', inUsd=1.15, inputMint=rs.WSOL, outputMint=COIN, outAmount=103.9455, fill=fill)))
    assert out.get('duplicate') is True                                   # no double points…
    row = rs._json_load(rs.FEELESS_TRADES_PATH, {})[W][0]
    assert row['locked'] is True and row['usd'] == 1.15125 and row['priced'] == 'signing'   # …but the entry is saved
    # a later, weaker (unlocked estimate) call never replaces the locked row
    asyncio.run(rs.internal_trade(Req(), rs.TradeLanded(wallet=W, signature='paid', inUsd=9.99, inputMint=rs.WSOL, outputMint=COIN, outAmount=103.9455)))
    assert rs._json_load(rs.FEELESS_TRADES_PATH, {})[W][0]['usd'] == 1.15125


def test_locked_rows_beat_estimates_and_unlocked_scans(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)

    async def no_history(a, limit=40):
        raise RuntimeError('provider down')
    monkeypatch.setattr(rs, 'wallet_trades', no_history)

    async def fills(address):   # quote estimate for the same trade: different, weaker numbers
        return [{'ts': 1, 'side': 'buy', 'usd': 1.30, 'price': 1.30 / 103.9455, 'tokens': 103.9455, 'token': COIN, 'tx': 'paid', 'via': 'estimate'}]

    async def chain(address, token):
        return {'balance': 103.9455, 'fills': [{'ts': 1, 'side': 'buy', 'usd': 1.15125, 'price': 1.15125 / 103.9455, 'tokens': 103.9455, 'poolUsd': 1.1505,
                                                'token': COIN, 'tx': 'paid', 'via': 'chain', 'priced': 'signing', 'locked': True}]}

    async def nothing(*a):
        return None
    monkeypatch.setattr(rs, '_feeless_fills', fills); monkeypatch.setattr(rs, '_chain_fills', chain); monkeypatch.setattr(rs, '_repair_estimates', nothing)
    pos = asyncio.run(rs.position(W, COIN))['position']
    assert abs(pos['avgEntry'] - 1.15125 / 103.9455) < 1e-12 and pos['locked'] is True and pos['investedUsd'] == 1.15
    assert abs(pos['trades'][0]['fillPrice'] - 1.1505 / 103.9455) < 1e-12

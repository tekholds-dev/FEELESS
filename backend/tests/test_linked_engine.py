"""Linked engine: trades earn season points once, watched wallets alert, after-the-sell lessons."""
import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip('solders')
rs = pytest.importorskip('reputation_service')
W = 'W' * 43


def test_trade_points_weight_fees_and_cap():
    assert rs.trade_points(100, 200) == 40.5   # $2 fee ×20 + $100/200
    assert rs.trade_points(100, 0) == 0.5      # fee-free $FEE buy still counts a little
    assert rs.trade_points(1e6, 2000) == 50    # capped


def test_internal_trade_awards_once(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'SEASONS_PATH', tmp_path / 's.json'); monkeypatch.setattr(rs, '_internal_key', lambda: 'k')
    got = []
    monkeypatch.setattr(rs, 'season_award', lambda a, p, r: got.append((a, p)))

    class Req:
        headers = {'x-feeless-internal': 'k'}
    body = rs.TradeLanded(wallet=W, signature='sig1', inUsd=100, feeBps=200)
    assert asyncio.run(rs.internal_trade(Req(), body))['points'] == 40.5
    assert asyncio.run(rs.internal_trade(Req(), body))['duplicate'] is True
    assert got == [(W, 40.5)]

    class Bad:
        headers = {'x-feeless-internal': 'nope'}
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.internal_trade(Bad(), body))


def test_watch_alerts_only_new_and_flags_suspect_dumps():
    now = time.time()
    trades = [{'ts': now - 500, 'side': 'buy', 'symbol': 'OLD', 'usd': 5, 'token': 'T0'},
              {'ts': now - 10, 'side': 'sell', 'symbol': 'RUG', 'usd': 1200, 'token': 'T1', 'pair': 'P1', 'tx': 'x1'}]
    out = rs.watch_alerts(W, trades, now - 100, {'level': 'suspect', 'label': 'Suspect'}, 'Dev')
    assert len(out) == 1 and 'Dev is dumping $RUG ($1,200)' in out[0]['text'] and 'Suspect' in out[0]['text'] and 'P1' in out[0]['url']
    assert 'sold' in rs.watch_alerts(W, trades, now - 100, {'level': 'clean'}, 'Dev')[0]['text']


def test_after_sell_lessons():
    trades = [{'side': 'sell', 'price': 1.0, 'token': 'A', 'symbol': 'A'}, {'side': 'sell', 'price': 1.0, 'token': 'B'},
              {'side': 'buy', 'price': 1.0, 'token': 'C'}, {'side': 'sell', 'price': 1.0, 'token': 'D'}]
    rows = rs.after_sell_lessons(trades, {'A': 2.0, 'B': 0.5, 'C': 9})
    assert [(r['token'], r['lesson']) for r in rows] == [('A', 'runner'), ('B', 'saved')]


def test_protected_wallet_quick_rep_is_feeless(monkeypatch):
    monkeypatch.setattr(rs, '_protected_wallets', lambda: {W})
    assert rs._quick_rep(W)['level'] == 'feeless'

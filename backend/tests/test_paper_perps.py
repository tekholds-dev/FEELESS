"""📉 Paper perps (docs/DECISIONS.md #1): live mark, real funding, liquidation at the real distance — paper only, never an order."""
import asyncio
import json

import pytest

import paper_perps as pp

NOW = 1_800_000_000.0


def test_a_paper_long_marks_funds_and_closes():
    b = pp.blank(NOW)
    p = pp.open_pos(b, 'BTC', 'long', 100, 10, 50_000, 40, NOW)
    assert b['cash'] == pp.START - 100 and p['size'] == pytest.approx(0.02) and p['liq'] == pytest.approx(50_000 * (1 - (0.1 - pp.MAINT)))
    v = pp.mark(p, 51_000, 0, NOW)
    assert v['pnl'] == pytest.approx(20.0) and v['pnlPct'] == pytest.approx(20.0) and not v['liquidated']
    f = pp.mark(dict(p, fund=0.0, fundAt=NOW), 50_000, 36.5, NOW + 86400)     # a day at +36.5 %/yr on $1,000: longs pay $1
    assert f['pnl'] == pytest.approx(-1.0, abs=1e-6)
    rec = pp.close_pos(b, p['id'], 51_000, 0, NOW + 60)
    assert rec['pnl'] == pytest.approx(20.0) and b['cash'] == pytest.approx(pp.START + 20) and b['open'] == [] and b['realized'] == pytest.approx(20)


def test_shorts_receive_positive_funding_and_a_wipe_out_liquidates_on_the_read():
    b = pp.blank(NOW)
    s = pp.open_pos(b, 'ETH', 'short', 200, 5, 2000, 25, NOW)
    assert pp.mark(dict(s), 2000, 36.5, NOW + 86400)['pnl'] > 0                  # shorts collect a positive rate
    pp.open_pos(b, 'SOL', 'long', 100, 20, 100, 20, NOW)
    v = pp.view(b, {'ETH': {'mark': 2000, 'fundApr': 0}, 'SOL': {'mark': 95, 'fundApr': 0}}, NOW + 10)   # SOL −5 % at 20× = liquidated
    assert [x['coin'] for x in v['liquidated']] == ['SOL'] and v['liquidated'][0]['pnl'] == -100 and v['liquidated'][0]['why'] == 'liquidated'
    assert [x['coin'] for x in v['open']] == ['ETH'] and v['trades'] == 1 and v['winPct'] == 0
    assert v['equity'] == pytest.approx(pp.START - 100, abs=0.01)


def test_the_ticket_refuses_what_a_venue_would():
    b = pp.blank(NOW)
    for args, why in ((('BTC', 'up', 100, 5, 1, 40), 'Long or short'), (('BTC', 'long', 100, 50, 1, 40), 'up to 40'), (('BTC', 'long', 5, 2, 1, 40), 'smallest'),
                      (('BTC', 'long', 1e6, 2, 1, 40), 'paper cash'), (('BTC', 'long', 100, 2, 0, 40), 'no live price')):
        with pytest.raises(ValueError, match=why):
            pp.open_pos(b, *args, NOW)
    for _ in range(pp.MAX_OPEN):
        pp.open_pos(b, 'BTC', 'long', 10, 2, 1, 40, NOW)
    with pytest.raises(ValueError, match='at once'):
        pp.open_pos(b, 'BTC', 'long', 10, 2, 1, 40, NOW)


def test_the_paper_desk_through_the_service_never_touches_a_venue(monkeypatch):
    import reputation_service as rs
    me = 'P' * 44
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    rs._perps_cache.update(at=9e18, rows=[{'coin': 'BTC', 'mark': 60_000.0, 'fundApr': 10.0, 'maxLev': 40, 'venues': ['kraken']}])
    rs.PAPER_PERPS_PATH.write_text('{}')
    v = asyncio.run(rs.familia_paper_perps_act(rs.PaperPerpAct(address=me, session='s', act='open', coin='btc', side='short', margin=250, lev=4)))
    assert v['open'][0]['side'] == 'short' and v['cash'] == pp.START - 250
    pid = v['open'][0]['id']
    v = asyncio.run(rs.familia_paper_perps(me, 's'))
    assert v['open'][0]['id'] == pid
    v = asyncio.run(rs.familia_paper_perps_act(rs.PaperPerpAct(address=me, session='s', act='close', id=pid)))
    assert v['open'] == [] and v['trades'] == 1
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        asyncio.run(rs.familia_paper_perps_act(rs.PaperPerpAct(address=me, session='s', act='open', coin='DOGE', side='long', margin=50, lev=2)))
    src = open(rs.__file__).read()
    i = src.index('async def familia_paper_perps_act('); body = src[i:src.index('\n\n\n', i)]
    assert 'http' not in body.replace('HTTPException', '')                                   # nothing in the paper desk calls out
    rs._perps_cache.update(at=0.0, rows=[])

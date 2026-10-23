"""💎 ONE points system (docs/DECISIONS.md #3): points → your family's bank at 1 : 100, ≤ 1,000 points a week, never without a family."""
import asyncio
import json

import pytest
from fastapi import HTTPException


def _setup(rs, monkeypatch, me, points=5000, family=True):
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    rs.POINTS_PATH.write_text(json.dumps({me: {'total': points, 'spent': 0, 'claims': {}, 'log': []}}))
    st = {'crews': {'c1': {'id': 'c1', 'tag': 'SIC', 'owner': me, 'members': [me], 'city': {'bank': 50}}}} if family else {'crews': {}}
    rs.CREWS_PATH.write_text(json.dumps(st))
    import crews as cr
    monkeypatch.setattr(cr, 'crew_of', lambda s, a: (s.get('crews') or {}).get('c1') if a == me and (s.get('crews') or {}).get('c1') else None)
    monkeypatch.setattr(rs, '_seat_of', lambda s, a: a)
    monkeypatch.setattr(rs._fcity, 'city_of', lambda c, now: c['city'])


def test_points_power_the_family_bank_with_a_weekly_cap(monkeypatch):
    import reputation_service as rs
    me = 'M' * 44
    _setup(rs, monkeypatch, me)
    item = next(x for x in rs.SHOP if x['id'] == 'family-mp')
    assert item['cost'] * rs.MP_PER_PT == item['grant']['mp'] == 10_000
    out = asyncio.run(rs.shop_buy(rs.BuyIn(address=me, session='s', item='family-mp')))
    assert out['balance'] == 4900 and json.loads(rs.CREWS_PATH.read_text())['crews']['c1']['city']['bank'] == 10_050
    for _ in range(9):
        asyncio.run(rs.shop_buy(rs.BuyIn(address=me, session='s', item='family-mp')))
    with pytest.raises(HTTPException) as e:
        asyncio.run(rs.shop_buy(rs.BuyIn(address=me, session='s', item='family-mp')))   # the 11th 100 points this week
    assert e.value.status_code == 400 and 'a week' in e.value.detail
    assert json.loads(rs.POINTS_PATH.read_text())[me]['spent'] == 1000


def test_no_family_no_mp(monkeypatch):
    import reputation_service as rs
    me = 'N' * 44
    _setup(rs, monkeypatch, me, family=False)
    with pytest.raises(HTTPException) as e:
        asyncio.run(rs.shop_buy(rs.BuyIn(address=me, session='s', item='family-mp')))
    assert 'Join a family' in e.value.detail and json.loads(rs.POINTS_PATH.read_text())[me]['spent'] == 0

"""Quest API: daily check-in builds a streak once per day; admin edits are validated; grants show up. Network faked."""
import asyncio
import time

import pytest

rs = pytest.importorskip('reputation_service')
W = 'Aaaa1111111111111111111111111111111111111111'


class Req:
    def __init__(self, body): self._b = body
    async def json(self): return self._b


def _iso(monkeypatch, tmp_path):
    for k in ('QUESTS_PATH', 'QUEST_STATE_PATH', 'FEELESS_TRADES_PATH', 'CALLS_PATH', 'REF_PATH', 'FOLLOW_PATH', 'POINTS_PATH', 'ADMIN_PATH'):
        monkeypatch.setattr(rs, k, tmp_path / f'{k}.json')
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: rs.primary_of(a))
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    monkeypatch.setattr(rs, '_chat_load', lambda: {'rooms': {}})
    async def board(days=90): return {'rows': []}
    async def zero(a): return 0.0
    async def mints(): return {'fee': 'FeeMint'}
    monkeypatch.setattr(rs, 'caller_board', board); monkeypatch.setattr(rs, '_fee_usd', zero); monkeypatch.setattr(rs, '_ecosystem_mints', mints)
    rs._quest_cache.clear(); rs._rarity_cache.clear()


def test_checkin_once_a_day_and_streak(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    yday = time.strftime('%Y-%m-%d', time.gmtime(time.time() - 86400))
    rs._json_save(rs.QUEST_STATE_PATH, {rs.primary_of(W): {'days': [yday], 'first': time.time() - 2 * 86400}})
    a = asyncio.run(rs.quest_checkin(rs.QuestCheckin(address=W, session='s')))
    b = asyncio.run(rs.quest_checkin(rs.QuestCheckin(address=W, session='s')))
    assert a['fresh'] and a['streak'] == 2 and not b['fresh'] and b['days'] == 2
    s = asyncio.run(rs.quest_board(W))
    assert s['quests']['daily']['tasks'][0]['done'] and s['metrics']['streak'] == 2


def test_admin_edit_validation_and_grant(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_quests_save(Req({'badges': {'q-trader': {'tasks': [{'metric': 'nope', 'target': 1}]}}})))
    out = asyncio.run(rs.admin_quests_save(Req({'badges': {'q-trader': {'name': 'Degen Trader', 'tasks': [{'metric': 'trades', 'target': 3, 'label': '3 trades'}]}}})))
    assert next(b for b in out['badges'] if b['id'] == 'q-trader')['name'] == 'Degen Trader'
    asyncio.run(rs.admin_quests_grant(Req({'address': W, 'badge': 'frsv-vip', 'action': 'grant'})))
    s = asyncio.run(rs.quest_board(W))
    vip = next(b for b in s['badges'] if b['id'] == 'frsv-vip')
    assert vip['earned'] and vip['granted']

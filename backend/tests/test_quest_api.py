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


def test_tool_events_verified_and_capped(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    monkeypatch.setattr(rs, '_push_load', lambda: {'subs': {}})
    rs._json_save(rs.FEELESS_TRADES_PATH, {rs.primary_of(W): [{'tx': 'SIG1', 'side': 'buy', 'usd': 5, 'token': 'X', 'ts': time.time()}]})
    ev = lambda kind, ref: asyncio.run(rs.quest_event(rs.QuestEvent(address=W, session='s', kind=kind, ref=ref)))
    with pytest.raises(rs.HTTPException):
        ev('warroom_trade', 'NOT-MINE')          # only your own verified trades count
    assert ev('warroom_trade', 'SIG1')['counted'] and not ev('warroom_trade', 'SIG1')['counted']
    assert ev('case_open', 'WalletA')['counted'] and not ev('case_open', 'WalletA')['counted']   # once per wallet per day
    s = asyncio.run(rs.quest_board(W))
    assert s['metrics']['warroom_trades'] == 1 and s['metrics']['cases_opened'] == 1
    assert next(t for t in s['quests']['weekly']['tasks'] if t['id'] == 'warroom')['done']


def test_season_paused_until_launch_then_scores(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    monkeypatch.setattr(rs, '_push_load', lambda: {'subs': {}})
    monkeypatch.setattr(rs, 'COLLECTION_PATH', tmp_path / 'col.json')
    assert asyncio.run(rs.quest_leaderboard())['paused']
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_quest_season(Req({'awardWeek': True})))   # nothing awarded while paused
    out = asyncio.run(rs.admin_quest_season(Req({'paused': False})))
    assert not out['season']['paused'] and out['season']['start']
    asyncio.run(rs.quest_checkin(rs.QuestCheckin(address=W, session='s')))
    s = asyncio.run(rs.quest_board(W))
    assert s['season']['score'] >= 10           # today's check-in counts toward the live season

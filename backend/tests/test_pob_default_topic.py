"""Owner 2026-11-10: "I asked for a PoB, this did a trench coin." A PoB with no topic bets on today's best games; the coin board only when asked."""
import asyncio


def test_a_topicless_pob_researches_todays_games_not_the_coin_board(monkeypatch):
    import feecat_service as fs
    goals, filed = [], []
    async def best(http, ask=''): return 'best NBA picks: Knicks, Celtics'
    monkeypatch.setattr(fs._tools, 'best_topic', best)
    monkeypatch.setattr(fs, '_read_start', lambda cat, goal, who, kind='': goals.append(goal) or 'stop here')   # stop before real windows open
    monkeypatch.setattr(fs, '_pob_file', lambda cat, rec, line: filed.append(rec))
    async def board(*a): raise AssertionError('the coin board must not be read')
    monkeypatch.setattr(fs, '_pob_board', board)
    cat = {'id': 'c', 'brainsCfg': {'brains': ['a/x']}}
    fs._POB_WANT['c'] = 'start'
    asyncio.run(fs._pob_tick(None, cat, 1000.0))
    assert filed[-1]['topic'] == 'best NBA picks: Knicks, Celtics' and 'Knicks' in goals[-1]
    async def none(http, ask=''): return ''
    monkeypatch.setattr(fs._tools, 'best_topic', none)
    fs._POB_WANT['c'] = 'start'; asyncio.run(fs._pob_tick(None, cat, 1001.0))
    assert filed[-1]['topic'] == "tonight's best games"   # no games feed: still sports, never coins


def test_the_board_only_when_asked(monkeypatch):
    import feecat_service as fs
    read = []
    async def board(http, cat, now): read.append(1); return []
    monkeypatch.setattr(fs, '_pob_board', board); monkeypatch.setattr(fs, '_pob_file', lambda *a: None)
    cat = {'id': 'd', 'pobBoard': True}
    fs._POB_WANT['d'] = 'start'; asyncio.run(fs._pob_tick(None, cat, 1000.0))
    assert read == [1] and 'pobAsk' not in cat

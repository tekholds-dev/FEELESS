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


def test_a_topic_read_is_shared_with_the_next_pob_on_that_topic(monkeypatch):
    """COL-9: one agent's fresh browser read of a topic is reused by any agent's next PoB on it; never browsed twice, stale ones are not."""
    import feecat_service as fs
    fs._TOPIC_READS.clear(); filed, opened = [], []
    async def topic_file(cat, rd, now, notes, why): filed.append((cat['id'], rd, notes, why))
    monkeypatch.setattr(fs, '_pob_topic_file', topic_file)
    monkeypatch.setattr(fs, '_read_start', lambda *a, **k: opened.append(1) or 'stop')
    monkeypatch.setattr(fs, '_pob_file', lambda *a: None)
    fs._topic_keep({'id': 'a'}, {'topic': 'NBA tonight', 'sites': ['espn.com']}, 1000.0, {'0': {'note': 'Knicks -4.5 at home, Brunson back; Celtics on a back-to-back ' * 2}})
    fs._topic_keep({'id': 'a'}, {'topic': 'thin'}, 1000.0, {'0': {'note': 'short'}})   # read nothing real: never shared
    assert 'thin' not in fs._TOPIC_READS
    cat = {'id': 'b', 'pobAsk': 'nba  Tonight', 'brainsCfg': {'brains': ['a/x', 'b/y']}}
    fs._POB_WANT['b'] = 'start'; asyncio.run(fs._pob_tick(None, cat, 1600.0))
    cid, rd, notes, why = filed[-1]
    assert cid == 'b' and rd['sharedFrom'] == 'a' and why == 'shared read' and 'Knicks' in notes['1']['note'] and not opened
    assert fs._TOPIC_READS['nba tonight']['reused'] == 1
    cat2 = {'id': 'c', 'pobAsk': 'NBA tonight', 'brainsCfg': {'brains': ['a/x']}}
    fs._POB_WANT['c'] = 'start'; asyncio.run(fs._pob_tick(None, cat2, 1000.0 + fs.READ_FRESH_S['pob'] + 1))
    assert opened == [1]   # stale: it browses itself

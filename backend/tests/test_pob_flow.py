"""🌐 A PoP / PoB's site read, end to end with a fake browser and fake minds: it reads first, calls on what it read, and says so when it could not browse."""
import asyncio
import json
import pytest


@pytest.fixture
def fs(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_work_live', lambda: True)
    fs._WORK.clear(); fs._POB_WANT.clear(); fs._POP_WANT.clear()
    return fs


def _cat():
    return {'id': 'c1', 'name': 'Happy', 'chat': [], 'brainsCfg': {'brains': ['a/one', 'b/two'], 'credit': 5.0, 'kind': 'trading'}}


def _task(tid='t1', done=False, notes=('saw +4%', 'saw +5%')):
    return {'done': done, 'task': {'id': tid, 'windows': [{'i': i, 'goal': 'g', 'answer': n, 'cost': .001, 'steps': [{'action': 'open', 'detail': 'https://dexscreener.com/x'}]} for i, n in enumerate(notes)]}}


def _board(fs, monkeypatch, staked):
    async def board(http, cat, now):
        return [{'id': 'm1', 'q': 'SOL up?', 'sym': 'SOL', 'crowd': 50, 'n': 1, 'locksAt': now + 900, 'now': now}]

    async def rep(http, body):
        staked.append(body)
        return {'market': {'state': 'open'}}
    monkeypatch.setattr(fs, '_pob_board', board); monkeypatch.setattr(fs, '_pob_rep', rep)


def test_a_proof_read_is_capped_silent_and_owes_no_flat_fee(fs, monkeypatch):
    async def run_():
        ran = []

        async def fake_run(*a, **k):
            ran.append(a)
        monkeypatch.setattr(fs, '_work_run', fake_run)
        cat = _cat()
        assert fs._read_start(cat, 'read sites', '') == ''
        await asyncio.sleep(0)
        t = fs._WORK['c1']['task']
        assert t['proofRead'] and t['research'] and t['mode'] == 'jobs' and t['jobs'] == ['read sites', 'read sites']
        assert ran[0][3] == 'read sites' and ran[0][4] <= fs._pow.ROUND_USD * 2   # its own small ceiling, per mind
        assert 'workNow' not in cat   # a restart never re-runs it as a chat ask
        fs._WORK['c1']['done'] = True; t['status'] = 'done'; t['cost'] = 0.01
        store = {'cats': {'c1': cat}}; fs._work_settle(store)
        assert not cat.get('feesDue') and cat['chat'] == [] and [j['proof'] for j in cat.get('jobs') or []] == ['proof']   # AGT-9: its research job is filed in Jobs, tagged; the chat stays quiet
    asyncio.run(run_())


def test_a_busy_window_never_blocks_the_proof_and_its_folder_says_so(fs, monkeypatch):
    fs._WORK['c1'] = {'done': False, 'task': {'id': 'other'}}
    assert fs._read_start(_cat(), 'x', '') == 'its windows were busy'


def test_pob_reads_first_then_bids_only_on_agreement(fs, monkeypatch):
    staked = []; _board(fs, monkeypatch, staked); seen = []

    async def ask(cat, i, sys_, user_, max_tokens=180, cost_to=None):
        seen.append(user_)
        return json.dumps({'market': 'm1', 'side': 'yes', 'why': 'up'})
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    monkeypatch.setattr(fs, '_read_start', lambda cat, goal, who, kind='': fs._WORK.__setitem__(cat['id'], _task()) or '')

    async def run_():
        cat = {**_cat(), 'pobBoard': True}; fs._POB_WANT['c1'] = 'start'   # the free-chip board, asked for (a plain PoB now bets on games)
        await fs._pob_tick(None, cat, 1000.0)
        assert cat['pobRead']['tid'] == 't1' and not staked and not seen     # reading, no call yet
        await fs._pob_tick(None, cat, 1001.0)
        assert not staked                                                    # still reading
        fs._WORK['c1']['done'] = True
        await fs._pob_tick(None, cat, 1002.0)
        assert 'saw +4%' in seen[0] and 'saw +5%' in seen[1] and 'saw +5%' not in seen[0]   # each mind only its own read
        assert staked[0]['op'] == 'stake' and staked[0]['side'] == 'yes' and cat['pobRun']['browsed']['0']['sites'] == ['dexscreener.com']
        fs._POB_WANT['c1'] = 'start'; n = len(staked)
        await fs._pob_tick(None, cat, 1003.0)
        assert len(staked) == n                                              # an open PoB never places a second bid
    asyncio.run(run_())


def test_pob_files_no_bid_when_the_minds_split(fs, monkeypatch):
    staked = []; _board(fs, monkeypatch, staked); sides = iter(['yes', 'no'])

    async def ask(cat, i, sys_, user_, max_tokens=180, cost_to=None):
        return json.dumps({'market': 'm1', 'side': next(sides), 'why': 'x'})
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    monkeypatch.setattr(fs, '_read_start', lambda cat, goal, who, kind='': 'its windows were busy')

    async def run_():
        cat = {**_cat(), 'pobBoard': True}; fs._POB_WANT['c1'] = 'start'   # the free-chip board, asked for (a plain PoB now bets on games)
        await fs._pob_tick(None, cat, 1000.0)
        f = cat['pobFolders'][0]
        assert not staked and f['noTrade'] and f['why'] == 'the minds disagreed' and f['browseWhy'] == 'its windows were busy'
    asyncio.run(run_())


def test_a_read_that_runs_long_is_stopped_and_files_what_it_reached(fs):
    cat = _cat(); fs._WORK['c1'] = _task()
    rd = {'tid': 't1', 'at': 1}
    assert fs._read_check(cat, rd, 10)[0] is False
    done, notes, why = fs._read_check(cat, rd, fs.READ_S + 2)
    assert done and fs._WORK['c1']['task']['stop'] and notes['0']['note'] == 'saw +4%' and why
    fs._WORK.clear()
    done, notes, why = fs._read_check(cat, rd, 10)
    assert done and notes == {} and 'ended' in why


def test_pop_reads_sites_then_each_mind_gets_its_own_note(fs, monkeypatch):
    seen = []

    class R:
        status_code = 200

        def __init__(self, j):
            self._j = j

        def json(self):
            return self._j

    async def read(http, m):
        return {'market': m, 'px': 100.0, 'chgPct': 1, 'high': 101, 'low': 99, 'vol': 1}

    async def chart(http, m):
        return ''

    async def gather_(http, cat, reads, idx, rid, now):
        return {}

    async def ask(cat, i, sys_, user_, max_tokens=180, cost_to=None):
        seen.append(user_)
        return '{"market":"SOL","side":"long","lev":2,"tp_pct":2,"sl_pct":1,"why":"funding at 0.01 percent and price held the 88 support"}'
    monkeypatch.setattr(fs, '_pop_read', read); monkeypatch.setattr(fs, '_pop_chart', chart); monkeypatch.setattr(fs, '_pop_gather', gather_); monkeypatch.setattr(fs, '_pow2_ask', ask)
    monkeypatch.setattr(fs, '_read_start', lambda cat, goal, who, kind='': fs._WORK.__setitem__(cat['id'], _task()) or '')

    async def run_():
        cat = _cat(); fs._POP_WANT['c1'] = 'start'
        async def price(http, m):
            return 100.0
        monkeypatch.setattr(fs, '_pop_price', price)
        await fs._pop_tick(None, cat, 1000.0)
        assert cat['popRead']['do'] == 'start' and not seen and not cat.get('popRun')
        fs._WORK['c1']['done'] = True
        await fs._pop_tick(None, cat, 1001.0)
        assert 'saw +4%' in seen[0] and 'saw +5%' not in seen[0] and 'popRead' not in cat
        assert cat['popRun']['browsed']['1']['note'] == 'saw +5%' and cat['popRun']['paper'] is True
    asyncio.run(run_())



def test_a_topic_pob_reads_keeps_snapshots_calls_blind_and_stakes_nothing(fs, monkeypatch, tmp_path):
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path)
    asks = []

    async def ask(cat, i, sys_, user_, n, box):
        asks.append((i, user_)); box['cost'] += 0.001
        return '{"picks":[{"pick":"Chiefs -3","confidence":70,"why":"espn 3.5"}]}'

    async def stake(*a, **k):
        raise AssertionError('a topic PoB never stakes')
    monkeypatch.setattr(fs, '_pow2_ask', ask); monkeypatch.setattr(fs, '_pob_rep', stake)
    cat = {'id': 'c1', 'chat': [], 'proofHosts': ['espn.com'], 'brainsCfg': {'brains': ['m/a', 'm/b']}}
    fs._WORK['c1'] = {'task': {'windows': [{'i': 0, '_shots': [{'site': 'espn.com', 'url': 'u', 'title': 't', 'jpg': b'J', 'at': 1}]}, {'i': 1}]}}
    notes = {'0': {'sites': ['espn.com'], 'note': 'Chiefs -3 on espn', 'cost': 0.01}, '1': {'sites': ['covers.com'], 'note': 'Chiefs -3 on covers', 'cost': 0.01}}
    asyncio.run(fs._pob_topic_file(cat, {'topic': 'best nfl picks', 'sites': ['espn.com'], 'who': ''}, 100.0, notes, ''))
    f = cat['pobFolders'][-1]
    assert f['topic'] == 'best nfl picks' and f['agreed'] == ['Chiefs -3'] and f['status'] == 'closed' and 'chips' not in f and 'proofHosts' not in cat
    assert f['shots'][0]['site'] == 'espn.com' and fs._ck.unseal_bytes((tmp_path / 'pob100' / 'm0_0.jpg').read_bytes(), 'c1') == b'J'
    assert 'Chiefs -3 on covers' not in asks[0][1] and 'Chiefs -3 on espn' not in asks[1][1]   # blind
    json.dumps(f)


def test_a_new_build_folder_survives_the_save(fs):
    """Real 500 found 2026-11-05: the save put back an old copy of the owner's fields, so a first folder vanished and the reply crashed."""
    store = fs._load(); cat = {'id': 'ws1', 'name': 'W', 'status': 'stopped', 'workspaces': []}; store.setdefault('cats', {})['ws1'] = cat; fs.keep_owned(cat); fs._save(store)
    cat = fs._load()['cats']['ws1']; store = fs._load(); cat = store['cats']['ws1']
    row = fs._feat.new_folder(cat, 'build', 'x', 1); fs.keep_owned(cat); fs._save(store)
    assert cat['workspaces'][-1]['id'] == row['id'] and fs._load()['cats']['ws1']['workspaces'][-1]['id'] == row['id']

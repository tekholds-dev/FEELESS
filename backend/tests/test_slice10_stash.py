"""🧠 Slice 10 · the stash brain: kept 3 ways, sorted by everything on the page, asked first, sealed by category, brains only, never leaked."""
import asyncio
import json
import logging

import pytest

import stash_brain as sb
import stash_sort as ss

ENV = {'BROKER_SECRET_KEY': 'slice10-test-secret'}
MARK = 'ZQXMARKER7731'   # a word only the page has: it must never show outside a brain's read
BOARD = (f'NBA odds tonight Nov 18. Bulls vs Lakers spread Lakers -4.5 (-110), moneyline Bulls +160, total 228.5. Also on the board: '
         f'Clippers vs Spurs spread Clippers -2 (-108), total 221.5. Kawhi Leonard (questionable). {MARK} ' + 'More lines and notes. ' * 20)
HTML = f'<html><head><title>NBA Odds Tonight</title></head><body><p>{BOARD}</p></body></html>'
URL = 'https://www.covers.com/nba/odds'


class FakeReader:
    """A reader page: no live screen, its HTML held after goto."""
    live = False

    def __init__(self, pages):
        self.pages, self.url, self.title, self._html, self.opened = pages, None, None, '', []

    async def goto(self, url):
        self.opened.append(url); self.url = url; self._html = self.pages[url]; self.title = 'NBA Odds Tonight'
        return 'page text: ' + self._html[:200]

    async def click(self, text):
        return await self.goto(URL)

    async def read(self):
        return self._html

    async def shot(self):
        return None

    async def close(self):
        return None


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, '_free_shot', lambda url: asyncio.sleep(0, result=b'\xff\xd8JPEGfake' + b'0' * 500))
    return tmp_path / 'stash_brain'


def test_a_page_is_sorted_by_everything_on_it_not_only_why_it_was_opened():
    s = ss.sort(BOARD, URL, 'NBA Odds Tonight', now=1795000000)
    for t in ('team:bulls', 'team:lakers', 'team:clippers', 'team:spurs', 'league:nba', 'market:spread', 'market:moneyline', 'market:total', 'player:kawhi leonard'):
        assert t in s['tags'], t
    assert any(t.startswith('date:') for t in s['tags']) and s['cat'] == 'nba' and s['fresh'] <= 30 * 60
    assert ss.sort('The heat of the game felt like magic to the kings of the hill.', 'https://blog.example/x')['tags'] == ['site:blog.example']   # plain words are not teams
    nums = [n['n'] for n in ss.numbers_of(BOARD)]
    assert '-4.5' in nums and '+160' in nums and '221.5' in nums


def test_kept_three_ways_sealed_by_category_and_the_index_names_nothing(root):
    tok = sb.open_run('read:t1', 'a1', 'pob')
    got = sb.keep(root, tok, URL, 'NBA Odds Tonight', BOARD, HTML, b'\xff\xd8JPEG' + b'1' * 300, load=4.2, provider='kernel', env=ENV)
    files = sorted(p.suffix for p in (root / 'nba').iterdir())
    assert files == ['.html', '.jpg', '.scrape'] and got['cat'] == 'nba'
    for p in list((root / 'nba').iterdir()) + [root / 'index.db']:
        raw = p.read_bytes()
        for w in (MARK, 'Clippers', 'clippers', 'covers.com/nba', 'Kawhi'):
            assert w.encode() not in raw, (p.name, w)
    assert (root / 'nba' / f"{got['pid']}.scrape").read_bytes().startswith(b'FS2:')
    with pytest.raises(Exception):   # another category's key opens nothing
        sb._open((root / 'nba' / f"{got['pid']}.scrape").read_bytes(), 'nfl', ENV)


def test_a_clippers_ask_finds_the_bulls_lakers_page_and_counts_the_hit(root):
    t1 = sb.open_run('read:first', 'a1', 'pob', now=1000)
    sb.keep(root, t1, URL, 'NBA Odds Tonight', BOARD, HTML, None, load=5.0, provider='kernel', now=1000, env=ENV)
    sb.close_run(t1)
    t2 = sb.open_run('read:second', 'a2', 'pob', now=1100)
    got = sb.ask(root, t2, 'Clippers vs Spurs tonight: best bet', now=1100, env=ENV)
    assert len(got) == 1 and MARK in got[0]['text'] and got[0]['url'] == URL
    assert sb.ask(root, t2, 'Chiefs vs Bills', now=1100, env=ENV) == []          # nothing on that page
    assert sb.ask(root, t2, 'Clippers vs Spurs', now=1000 + 3600, env=ENV) == []  # stale: browse again, never trusted
    rec = sb.record_for(root, ['read:second'])
    assert rec['hits'] == 1 and rec['browsed'] == 0 and rec['savedSecs'] > 5 and rec['from'] == ['read:first'] and rec['pages'][0]['hit']
    first = sb.record_for(root, ['read:first'])
    assert first['browsed'] == 1 and first['hits'] == 0 and first['pages'][0]['scrape']['nums'] > 5


def test_only_a_brain_inside_a_run_can_read(root):
    t = sb.open_run('read:x')
    sb.keep(root, t, URL, 't', BOARD, HTML, env=ENV)
    sb.close_run(t)
    for fn in (lambda: sb.url_hit(root, t, URL, env=ENV), lambda: sb.ask(root, None, 'Clippers', env=ENV), lambda: sb.keep(root, 'made-up', URL, 't', BOARD, env=ENV)):
        with pytest.raises(sb.Sealed):
            fn()


def test_ask_first_then_delta_browse_through_the_page_a_mind_drives(root):
    async def go():
        # run 1 browses and keeps
        task1 = {'id': 't1', 'jobs': ['Bulls vs Lakers: read the odds'], 'text': ''}
        inner1 = FakeReader({URL: HTML})
        tok1, (p1,) = sb.start_run(task1, [inner1], [{'provider': 'kernel'}], root.parent, 'read:t1', 'a1', 'pob', env=ENV)
        await p1.goto(URL)
        await p1.close(); sb.end_run(task1, tok1, [p1])
        assert inner1.opened == [URL] and task1['stash']['browsed'] == 1 and task1['stash']['kept'] == 1
        assert sb.record_for(root, ['read:t1'])['pages'][0]['shot']['bytes'] > 0   # the reader's page got its picture from the free browser
        # run 2: the ask hands both minds the page, a goto on it opens from the stash, a click needs the real page
        task2 = {'id': 't2', 'jobs': ['Clippers vs Spurs tonight', 'Clippers vs Spurs tonight, other angle'], 'text': ''}
        inner2 = FakeReader({URL: HTML})
        tok2, (p2,) = sb.start_run(task2, [inner2], [{'provider': 'kernel'}], root.parent, 'read:t2', 'a2', 'pob', env=ENV)
        assert all('FROM THE FEELESS STASH' in j and MARK in j for j in task2['jobs']) and task2['stash']['hits'] == 1
        seen = await p2.goto(URL)
        assert 'FROM THE FEELESS STASH' in seen and inner2.opened == [] and p2.url == URL
        assert await p2.shot() is None   # its sealed picture never reaches a screen
        with pytest.raises(RuntimeError):
            await p2.find_private('() => 1')   # a stash page has no live screen: a resting monitor fails closed
        await p2.click('more')
        assert inner2.opened == [URL, URL]   # hands needed: the real page opened, then the click
        sb.end_run(task2, tok2, [p2])
        rec = sb.record_for(root, ['read:t2'])
        assert rec['hits'] == 2 and rec['browsed'] >= 1 and rec['savedSecs'] > 0 and rec['paidEqUsd'] > 0
        with pytest.raises(sb.Sealed):
            sb.url_hit(root, tok2, URL, env=ENV)   # the run is over: its token is dead
    asyncio.run(go())


def test_private_and_signed_in_pages_are_never_kept(root):
    async def go():
        u1, u2 = 'https://mail.google.com/mail/u/0', 'https://pump.fun/board'
        inner = FakeReader({u1: HTML, u2: HTML})
        tok, (p,) = sb.start_run({'id': 't', 'text': 'x'}, [inner], [{}], root.parent, 'read:p', skip_hosts=['pump.fun'], env=ENV)
        await p.goto(u1); await p.goto(u2)
        assert p.counts['kept'] == 0 and p.counts['skipped'] == 2
        sb.close_run(tok)
    asyncio.run(go())


def test_no_sealed_text_reaches_logs_prints_the_call_log_the_record_or_any_api_answer(root, tmp_path, monkeypatch, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    t1 = sb.open_run('read:a'); sb.keep(root, t1, URL, 'NBA Odds Tonight', BOARD, HTML, b'\xff\xd8' + b'2' * 200, load=3, env=ENV); sb.close_run(t1)
    t2 = sb.open_run('read:b'); assert sb.ask(root, t2, 'Clippers', env=ENV); sb.url_hit(root, t2, URL, env=ENV); sb.close_run(t2)
    rec = json.dumps(sb.record_for(root, ['read:a', 'read:b'])); panel = json.dumps(sb.stats(root))
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, 'DATA_DIR', root.parent)
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    api = TestClient(fs.app).get('/api/cats/proofs/stash-brain')
    assert api.status_code == 200 and api.json()['pages'] == 1 and api.json()['hits'] == 2
    calls = root.parent / 'mind_calls.jsonl'
    out = capsys.readouterr()
    for where, text in (('record', rec), ('panel', panel), ('api', api.text), ('stdout', out.out), ('stderr', out.err), ('logs', caplog.text),
                        ('call log', calls.read_text() if calls.exists() else '')):
        for w in (MARK, 'Kawhi', '-4.5 (-110)', 'covers.com/nba/odds'):
            assert w not in text, (where, w)
    assert 'nba' in panel and '"hitRate"' in panel


def test_the_record_row_and_the_slice14_shape():
    import proof_record as pr
    f = {'id': 'pob1', 'kind': 'PoB', 'topic': 'x', 'stash': {'hits': 3, 'browsed': 2, 'stale': 1, 'kept': 2, 'savedSecs': 12.5, 'savedUsd': 0.0003, 'paidEqUsd': 0.036}}
    row = next(r for r in pr.checks('pob', f, []) if r['key'] == 'stash')
    assert row['ok'] and '3 stash hits, 2 pages browsed' in row['why']
    assert not any(r['key'] == 'stash' for r in pr.checks('pob', {'id': 'p'}, []))   # an old folder keeps its old rows (no back pedal)


def test_a_sent_back_pob_waits_for_its_stopped_read_to_close_never_files_busy(monkeypatch):
    """Found on the Slice 10 TEST run (PoB #12): a read stopped at READ_S was still closing when the footprint gate sent it back, so the re-read
    filed an empty PoB 'its windows were busy'. It now waits a tick and starts once the old read is done."""
    fs = pytest.importorskip('feecat_service')
    fs._WORK.clear(); fs._POB_WANT.clear(); started = []
    monkeypatch.setattr(fs, '_work_live', lambda *_a: True)
    monkeypatch.setattr(fs, '_read_start', lambda cat, goal, who, kind='': started.append(goal) or 'stop here')
    cat = {'id': 'c1', 'name': 'S', 'chat': [], 'pobAsk': 'Knicks vs Timberwolves tonight', 'pobBy': 'test', 'brainsCfg': {'brains': ['a/one', 'b/two'], 'credit': 5.0}}
    fs._WORK['c1'] = {'done': False, 'task': {'id': 'old', 'stop': True}}
    fs._POB_WANT['c1'] = 'start'
    asyncio.run(fs._pob_tick(None, cat, 1000.0))
    assert cat.get('pobAsk') and not started and not cat.get('pobFolders') and fs._POB_WANT['c1'] == 'start'   # waits; nothing filed
    fs._WORK['c1']['done'] = True
    monkeypatch.setattr(fs, '_pob_games', lambda topic: asyncio.sleep(0, result=[]))
    monkeypatch.setattr(fs, '_pob_facts', lambda g: asyncio.sleep(0, result=''))
    asyncio.run(fs._pob_tick(None, cat, 1001.0))
    assert started   # the old read closed: the re-read starts now

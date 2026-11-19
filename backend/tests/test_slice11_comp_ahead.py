"""📡 Slice 11 · COMP stays ahead: scheduled plain reads into the stash (no model), a new PoB beside every other agent's PoB on the same game
(and COMP's reference), one COMP task per filing for owner agents only, and the Living Atlas's first piece (atoms with a freshness clock,
source trust moving with settled outcomes). Network faked everywhere."""
import asyncio
import json

import pytest

import atlas
import comp_ahead as ca
import comp_task as ct
import pob_peers as pp
import proof_record as pr
import stash_brain as sb

ENV = {'BROKER_SECRET_KEY': 'slice11-test-secret'}
MARK = 'ZQXATLAS5521'   # a word only the pages and facts have: it must never show outside a brain's read
NOW = float(int(__import__("time").time()))   # the real clock: a run token dies 3 h after it opens
GAME = {'id': '401910022', 'sport': 'nba', 'at': '2026-11-20T01:00Z', 'state': 'pre', 'status': '11/19 - 8:00 PM EST', 'line': 'SA -16.5', 'total': 226.5,
        'teams': [{'name': 'LA Clippers', 'short': 'Clippers', 'abbr': 'LAC', 'kalshi': 0.11, 'chance': 0.105}, {'name': 'San Antonio Spurs', 'short': 'Spurs', 'abbr': 'SA', 'kalshi': 0.89, 'chance': 0.895}]}
DETAIL = {'state': 'pre', 'line': 'SA -16.5', 'total': 226.5, 'teams': [
    {'name': 'LA Clippers', 'abbr': 'LAC', 'side': 'away', 'record': '4-9', 'sideRecord': '0-5', 'form': ['W', 'L'], 'injuries': [{'name': 'Bradley Beal', 'status': 'Out'}],
     'leaders': [{'stat': 'Points', 'name': 'Darius Garland', 'value': '21.2'}]},
    {'name': 'San Antonio Spurs', 'abbr': 'SA', 'side': 'home', 'record': '12-3', 'sideRecord': '5-3', 'form': ['W', 'W'], 'injuries': [{'name': MARK.title(), 'status': 'Out'}],
     'leaders': [{'stat': 'Points', 'name': 'Victor Wembanyama', 'value': '28.4'}]}]}
ODDS = f'<html><title>NBA Odds</title><body>NBA odds tonight. Clippers vs Spurs spread Spurs -16.5, total 226.5. Knicks vs Timberwolves moneyline. {MARK} ' + 'lines ' * 60 + '</body></html>'


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv('BROKER_SECRET_KEY', ENV['BROKER_SECRET_KEY'])
    ct._TASKS.clear(); ct._REFUSED.clear(); ca.STATE.update(running=False, last=None)
    reads = {'detail': 0, 'pages': []}

    async def upcoming(http, now, leagues=ca.LEAGUES):
        return [json.loads(json.dumps(GAME))]

    async def detail(http, sport, gid, names=()):
        reads['detail'] += 1
        return json.loads(json.dumps(DETAIL))

    class Reader:
        def __init__(self, http):
            self.url, self._html, self.title = None, '', None

        async def goto(self, url):
            reads['pages'].append(url); self.url = url; self._html = ODDS
            return ODDS

    async def coins(http, n=ca.MAX_COINS):
        return [{'pairAddress': 'PairAbc', 'dexId': 'pumpswap', 'priceUsd': '0.0006', 'liquidity': {'usd': 93978}, 'volume': {'h24': 3482480, 'h1': 696048},
                 'priceChange': {'h1': 111, 'h24': 176}, 'marketCap': 604355, 'pairCreatedAt': 1792070460000, 'txns': {'h1': {'buys': 1, 'sells': 2}},
                 'baseToken': {'symbol': 'DACITY', 'name': 'DacityCoin', 'address': 'MintAbc'}}]

    async def no_board(http, url, **kw):
        return None

    import proof_tools as pt
    import cat_browser as cb
    monkeypatch.setattr(ca, 'upcoming', upcoming); monkeypatch.setattr(pt, 'game_detail', detail); monkeypatch.setattr(cb, 'ReaderPage', Reader)
    monkeypatch.setattr(ca, 'hot_coins', coins); monkeypatch.setattr(pt, '_get', no_board)
    monkeypatch.setattr(sb, '_free_shot', lambda url: asyncio.sleep(0, result=b'\xff\xd8JPEGfake' + b'0' * 400))
    return tmp_path, reads


# ── the Living Atlas ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_same_fact_from_three_sites_is_one_atom_with_three_sources(tmp_path):
    root = atlas.root_of(tmp_path); tok = sb.open_run('comp:t', 'comp', 'comp', NOW)
    rows = [{'subject': 'game:nba:1', 'what': 'line', 'value': 'SA -16.5', 'host': h, 'kind': 'line', 'cat': 'nba', 'label': 'Clippers at Spurs'} for h in ('espn.com', 'https://www.covers.com/x', 'oddsshark.com')]
    assert atlas.put(root, tok, rows, NOW, env=ENV) == 1
    got = atlas.facts(root, tok, ['game:nba:1'], NOW + 60, env=ENV)
    assert len(got) == 1 and sorted(s['host'] for s in got[0]['sources']) == ['covers.com', 'espn.com', 'oddsshark.com'] and got[0]['agree'] and got[0]['fresh']
    assert atlas.stats(root, NOW)['multi'] == 1 and atlas.stats(root, NOW)['sources'] == 3


def test_facts_age_by_kind_and_a_stale_one_says_so(tmp_path):
    root = atlas.root_of(tmp_path); tok = sb.open_run('comp:t', 'comp', 'comp', NOW)
    atlas.put(root, tok, [{'subject': 'game:nba:1', 'what': 'line', 'value': '-3', 'host': 'espn.com', 'kind': 'line', 'cat': 'nba'},
                          {'subject': 'game:nba:1', 'what': 'mint', 'value': 'abc', 'host': 'espn.com', 'kind': 'launch', 'cat': 'nba'}], NOW, env=ENV)
    later = NOW + 31 * 60
    by = {a['what']: a for a in atlas.facts(root, tok, ['game:nba:1'], later, env=ENV)}
    assert not by['line']['fresh'] and by['mint']['fresh']   # live lines go stale in 30 min, a launch fact never
    assert 'STALE' in atlas.facts_line(list(by.values()))
    assert atlas.due(root, 'game:nba:1', ('line',), later, env=ENV) and not atlas.due(root, 'game:nba:1', ('mint',), later, env=ENV)
    assert atlas.stats(root, later)['stale'] == 1


def test_atoms_are_sealed_at_rest_and_open_only_to_a_brain_run(tmp_path):
    root = atlas.root_of(tmp_path); tok = sb.open_run('comp:t', 'comp', 'comp', NOW)
    atlas.put(root, tok, [{'subject': f'player:{MARK.lower()}', 'what': 'status', 'value': MARK, 'host': 'espn.com', 'kind': 'injury', 'cat': 'nba', 'label': MARK}], NOW, env=ENV)
    raw = (root / 'atlas.db').read_bytes()
    assert MARK.encode() not in raw and MARK.lower().encode() not in raw
    with pytest.raises(sb.Sealed):
        atlas.facts(root, 'no-token', [f'player:{MARK.lower()}'], NOW, env=ENV)
    sb.close_run(tok)
    with pytest.raises(sb.Sealed):
        atlas.put(root, tok, [], NOW, env=ENV)
    assert MARK not in json.dumps(atlas.stats(root, NOW))


def test_trust_moves_with_settled_outcomes_once_per_proof(tmp_path):
    root = atlas.root_of(tmp_path)
    assert atlas.settle(root, 'pob:a:1', ['espn.com', 'kalshi.com'], 'nba', True, NOW) == ['espn.com', 'kalshi.com']
    assert atlas.settle(root, 'pob:a:1', ['espn.com'], 'nba', True, NOW) == []          # the same proof never moves a source twice
    atlas.settle(root, 'pob:a:2', ['kalshi.com'], 'nba', False, NOW)
    t = {r['host']: r for r in atlas.trust_rows(root, 'nba')}
    assert t['espn.com']['trust'] > 0.5 > t['kalshi.com']['trust'] or t['kalshi.com']['trust'] == 0.5
    assert t['espn.com']['right'] == 1 and t['kalshi.com']['right'] == 1 and t['kalshi.com']['wrong'] == 1 and t['espn.com']['trust'] > t['kalshi.com']['trust']


def test_the_most_trusted_source_gives_the_value_a_brain_reads(tmp_path):
    root = atlas.root_of(tmp_path); tok = sb.open_run('comp:t', 'comp', 'comp', NOW)
    atlas.put(root, tok, [{'subject': 'game:nba:1', 'what': 'win chance spurs', 'value': v, 'host': h, 'kind': 'winchance', 'cat': 'nba'} for h, v in (('kalshi.com', 0.89), ('polymarket.com', 0.80))], NOW, env=ENV)
    for i in range(3):
        atlas.settle(root, f'r{i}', ['polymarket.com'], 'nba', True, NOW)
    a = atlas.facts(root, tok, ['game:nba:1'], NOW, topic='nba', env=ENV)[0]
    assert a['value'] == 0.80 and a['by'] == 'polymarket.com' and not a['agree']


# ── COMP reads ahead ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_pass_reads_whats_coming_up_into_the_stash_and_atlas_with_no_model(env, monkeypatch, capsys):
    d, reads = env
    import feecat_service as fs
    called = []
    monkeypatch.setattr(fs, '_or_call', lambda *a, **k: called.append(1))
    row = asyncio.run(ca.run_pass(d, http=object(), now=NOW))
    assert row['games'] == 1 and reads['detail'] == 1 and len(reads['pages']) == 4 and row['coins'] == 1 and row['newAtoms'] > 10 and row['shots'] == 4
    assert not called   # no model was ever asked
    st = sb.stats(sb.root_of(d), NOW)
    assert st['pages'] == 6 and {c['cat'] for c in st['cats']} >= {'nba', 'coins'}
    tok = sb.open_run('read:t9', 'cat1', 'pob', NOW)
    got = sb.ask(sb.root_of(d), tok, 'Clippers vs Spurs tonight', NOW + 60)
    assert got and all(sb._RUNS[tok]['ref'] == 'read:t9' for _ in got)
    assert any(str(r).startswith('comp:ahead:') for r in sb.record_for(sb.root_of(d), ['read:t9'])['from'])   # the brain's hits came from COMP's reads
    refs = ca.load_refs(d)
    assert refs['401910022']['fav'] == {'espn.com': 'spurs', 'kalshi.com': 'spurs', 'polymarket.com': 'spurs'} and refs['401910022']['abbr']['clippers'] == 'LAC'
    out = capsys.readouterr().out + (ca.dir_of(d) / 'passes.jsonl').read_text() + json.dumps(ca.panel(d, NOW))
    assert MARK not in out and MARK.lower() not in out   # counts only: no page word, no fact, in prints, the log or the panel
    assert ca.panel(d, NOW)['models'] == 0


def test_delta_reading_a_fresh_game_and_page_are_not_read_again(env):
    d, reads = env
    asyncio.run(ca.run_pass(d, http=object(), now=NOW))
    row = asyncio.run(ca.run_pass(d, http=object(), now=NOW + 120))
    assert reads['detail'] == 1 and len(reads['pages']) == 4 and row['fresh'] >= 6 and row['kept'] == 0
    asyncio.run(ca.run_pass(d, http=object(), now=NOW + 40 * 60))   # its line went stale: read again
    assert reads['detail'] == 2


def test_a_final_game_settles_each_sources_favourite(env, monkeypatch):
    d, _ = env
    asyncio.run(ca.run_pass(d, http=object(), now=NOW))
    import proof_tools as pt
    final = {'events': [{'id': '401910022', 'date': '2026-11-20T01:00Z', 'status': {'type': {'state': 'post', 'completed': True}},
                         'competitions': [{'competitors': [{'homeAway': 'away', 'team': {'displayName': 'LA Clippers', 'shortDisplayName': 'Clippers'}, 'winner': True},
                                                           {'homeAway': 'home', 'team': {'displayName': 'San Antonio Spurs', 'shortDisplayName': 'Spurs'}, 'winner': False}]}]}]}

    async def board(http, url, **kw):
        return final if 'scoreboard' in url else None
    monkeypatch.setattr(pt, '_get', board)
    refs = ca.load_refs(d)
    assert asyncio.run(ca.settle_refs(object(), d, refs, ca._iso_ts(GAME['at']) + 4 * 3600)) == 1
    t = {r['host']: r for r in atlas.trust_rows(atlas.root_of(d), 'nba')}
    assert all(t[h]['wrong'] == 1 for h in ('espn.com', 'kalshi.com', 'polymarket.com')) and refs['401910022']['settled']['winner'] == 'clippers'
    assert asyncio.run(ca.settle_refs(object(), d, refs, ca._iso_ts(GAME['at']) + 5 * 3600)) == 0   # once


def test_every_settled_pob_moves_the_trust_of_its_sources_once(tmp_path):
    cats = [{'id': 'h', 'pobFolders': [{'id': 'p1', 'topic': 'Heat vs Bucks', 'graded': 'right', 'gradedBy': 'scoreboard', 'sites': ['espn.com', 'covers.com'], 'games': [{'sport': 'nba'}]},
                                       {'id': 'p2', 'topic': 'Lakers', 'kalshi': {'outcome': 'lost'}, 'graded': 'right', 'read': {'sites': ['espn.com']}},
                                       {'id': 'p3', 'topic': 'open one'}]}]
    assert ca.settle_folders(tmp_path, cats, NOW) == 2 and ca.settle_folders(tmp_path, cats, NOW) == 0
    f1, f2 = cats[0]['pobFolders'][:2]
    assert f1['atlasTrust']['ok'] and not f2['atlasTrust']['ok'] and f2['atlasTrust']['by'] == 'kalshi'   # a real Kalshi result beats the board's grade
    t = {r['host']: r for r in atlas.trust_rows(atlas.root_of(tmp_path), 'nba')}
    assert t['espn.com']['right'] == 1 and t['espn.com']['wrong'] == 1 and t['covers.com']['right'] == 1


# ── filed proofs are reference ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _pob(pid, picks, at=NOW, topic='Clippers vs Spurs tonight', games=None):
    return {'id': pid, 'at': at, 'topic': topic, 'games': games or [], 'calls': [{'name': 'ossy', 'picks': [{'pick': p} if isinstance(p, str) else p for p in picks]}]}


def test_a_new_pob_is_set_beside_every_other_agents_pob_on_the_same_game():
    mine = _pob('m1', ['Spurs to win', 'Over 226.5 total points', 'Clippers +16.5'])
    cats = [{'id': 'sic', 'name': "Sicario's", 'pobFolders': [_pob('own', ['Clippers to win'])]},   # its own agent: never a peer
            {'id': 'hap', 'name': 'Happy', 'pobFolders': [_pob('h1', ['Clippers to win', 'Under 226.5', {'pick': 'Spurs to win', 'kalshi': {'ticker': 'KXNBAGAME-26NOV19LACSA-SA', 'side': 'yes'}}], NOW - 3600),
                                                          _pob('h2', ['Knicks to win'], NOW, 'Knicks vs Timberwolves')]},   # another game
            {'id': 'fee', 'name': 'Fee', 'pobFolders': [_pob('f1', ['San Antonio Spurs moneyline'], NOW - 7200, 'Spurs vs Clippers parlay slip')]}]
    p = pp.compare(mine, 'sic', cats, {}, NOW)
    assert [r['id'] for r in p['peers']] == ['h1', 'f1'] and p['agents'] == 2
    h1 = p['peers'][0]
    assert {(r['ours'], r['theirs']) for r in h1['agree']} == {('Spurs to win', 'Spurs to win')}
    assert ('Spurs to win', 'Clippers to win') in {(r['ours'], r['theirs']) for r in h1['disagree']} and ('Over 226.5 total points', 'Under 226.5') in {(r['ours'], r['theirs']) for r in h1['disagree']}
    assert h1['verdict'] == 'split' and p['peers'][1]['verdict'] == 'agree'
    assert '2 PoBs by 2 other agents' in pp.say(p)


def test_comps_reference_is_compared_too_and_a_game_with_nothing_on_file_says_so():
    ref = ca.reference(GAME, DETAIL, NOW)
    mine = _pob('m1', ['Clippers to win'], games=[{'id': '401910022', 'sport': 'nba'}])
    p = pp.compare(mine, 'sic', [], {'401910022': ref}, NOW)
    assert p['comp']['fav']['kalshi.com'] == 'spurs' and len(p['comp']['disagree']) == 3 and not p['comp']['agree']
    assert "COMP's reference" in pp.say(p) and '0 agree, 3 disagree' in pp.say(p)
    tagged = _pob('m2', [{'pick': 'LAC YES', 'kalshi': {'ticker': 'KXNBAGAME-26NOV19LACSA-LAC', 'side': 'yes'}}], topic='Clippers vs Spurs')
    assert len(pp.compare(tagged, 'sic', [], {'401910022': ref}, NOW)['comp']['disagree']) == 3   # its Kalshi ticker names the team
    none = pp.compare(_pob('m3', ['Bills to win'], topic='Bills vs Dolphins'), 'sic', [], {}, NOW)
    assert not none['peers'] and not none['comp'] and pp.say(none).startswith('no other agent has filed this game')


# ── COMP takes a task ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_an_owner_agents_brain_hands_comp_one_task_per_filing(env):
    d, reads = env
    asyncio.run(ca.run_pass(d, http=object(), now=NOW))
    btok = sb.open_run('read:task1', 'sic', 'pob', NOW)
    text, _ = asyncio.run(ct.handle(object(), {'ownerStaff': True, 'name': "Sicario's"}, 'read:task1', 'Clippers vs Spurs tonight: injuries and the line', btok, d, NOW + 30))
    assert 'COMP did your task' in text and 'SA -16.5' in text and 'Bradley Beal' in text and reads['detail'] == 2   # read fresh for the task
    again, _ = asyncio.run(ct.handle(object(), {'ownerStaff': True}, 'read:task1', 'Knicks too', btok, d, NOW + 40))
    assert again.startswith('COMP refused') and 'one task' in again
    no, _ = asyncio.run(ct.handle(object(), {'name': 'a user agent'}, 'read:task2', 'Clippers', btok, d, NOW))
    assert 'owner' in no and 'read:task2' not in ct._TASKS
    rec = ct.record_for(['read:task1'])
    t = rec['task']
    assert t['status'] == 'done' and t['ask'].startswith('Clippers vs Spurs') and t['read'] == ['Clippers at Spurs'] and len(t['facts']) > 5
    assert {'label', 'what', 'value', 'sources', 'fresh'} <= set(t['facts'][0]) and rec['refused'][0]['ask'] == 'Knicks too'
    assert ct.job_line({'ownerStaff': True}) and ct.job_line({}) == ''


def test_two_minds_at_once_still_get_one_task(env):
    d, _ = env
    btok = sb.open_run('read:t3', 'sic', 'pob', NOW)

    async def both():
        return await asyncio.gather(*(ct.handle(object(), {'ownerStaff': True}, 'read:t3', f'Spurs {i}', btok, d, NOW) for i in range(2)))
    got = [t for t, _ in asyncio.run(both())]
    assert sum(1 for t in got if t.startswith('COMP did your task')) == 1 and sum(1 for t in got if t.startswith('COMP refused')) == 1


# ── wired: filed on the record, shown in its checks ─────────────────────────────────────────────────────────────────────────────────────
def test_a_pob_filing_carries_its_compare_and_comp_task_into_its_checks(monkeypatch):
    import feecat_service as fs
    fs._TEST_ON.clear(); fs._WORK.clear(); ct._TASKS.clear()
    store = {'cats': {'hap': {'id': 'hap', 'name': 'Happy', 'pobFolders': [_pob('h1', ['Clippers to win'], NOW - 600)]}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    ca.save_refs(fs.DATA_DIR, {'401910022': ca.reference(GAME, DETAIL, NOW)}, NOW)
    ct._TASKS['read:tid1'] = {'ask': 'Clippers vs Spurs injuries', 'at': NOW, 'status': 'done', 'read': ['Clippers at Spurs'], 'facts': [{'label': 'x', 'what': 'line', 'value': 'SA -16.5', 'sources': ['espn.com'], 'fresh': True}]}
    cat = {'id': 'sic', 'name': "Sicario's", 'chat': [], 'ownerStaff': True, 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    fs._pob_file(cat, {**_pob('pob9', ['Spurs to win'], NOW, games=[{'id': '401910022', 'sport': 'nba'}]), 'kind': 'PoB', 'readTid': 'tid1'}, 'filed')
    f = cat['pobFolders'][-1]
    assert f['peers']['peers'][0]['id'] == 'h1' and f['peers']['peers'][0]['disagree'] and f['peers']['comp']['agree']
    assert f['compTask']['task']['ask'] == 'Clippers vs Spurs injuries'
    rows = {r['key']: r for r in pr.checks('pob', f, ['local/ossy', 'local/g4'])}
    assert rows['peers']['ok'] and '1 PoB by 1 other agent' in rows['peers']['why'] and rows['comp']['ok'] and '1 facts back' in rows['comp']['why']


def test_the_ahead_check_reads_where_the_stash_hits_came_from():
    rows = {r['key']: r for r in pr.checks('pob', {'stash': {'hits': 2, 'browsed': 1, 'from': ['comp:ahead:1795074000', 'read:x']}}, [])}
    assert rows['ahead']['ok'] and '1 of the stash pages' in rows['ahead']['why']
    assert not {r['key']: r for r in pr.checks('pob', {'stash': {'hits': 0, 'browsed': 3, 'from': []}}, [])}['ahead']['ok']


def test_a_proof_read_or_a_pob_filing_holds_off_a_code_reload(monkeypatch):
    import feecat_service as fs
    from fastapi.testclient import TestClient
    store = {'cats': {'sic': {'id': 'sic', 'pobRead': {'at': fs.time.time()}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); fs._WORK.clear()
    c = TestClient(fs.app)
    assert c.get('/api/cats/health').json()['busy'] == 1
    fs._WORK['sic'] = {'task': {}, 'at': fs.time.time()}
    assert c.get('/api/cats/health').json()['busy'] == 2
    fs._WORK['sic']['done'] = True; store['cats']['sic']['pobRead'] = {'at': fs.time.time() - 3600}   # done, or stuck an hour: never blocks reloads forever
    assert c.get('/api/cats/health').json()['busy'] == 0
    store['cats']['sic']['pobAsk'] = 'Clippers vs Spurs'   # asked, not reading yet
    assert c.get('/api/cats/health').json()['busy'] == 1
    store['cats']['sic'].pop('pobAsk'); fs._TEST_ON[('sic', 'poe')] = {'at': fs.time.time()}   # a TEST claim of any kind
    assert c.get('/api/cats/health').json()['busy'] == 1
    fs._TEST_ON[('sic', 'poe')]['at'] -= 3600; assert c.get('/api/cats/health').json()['busy'] == 0
    fs._TEST_ON.clear()
    fs._WORK.clear()


def test_the_panel_route_gives_counts_only(monkeypatch, env):
    d, _ = env
    import feecat_service as fs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, 'DATA_DIR', d)
    asyncio.run(ca.run_pass(d, http=object(), now=NOW))
    r = TestClient(fs.app).get('/api/cats/proofs/comp-ahead')
    assert r.status_code == 200 and r.json()['atlas']['atoms'] > 10 and r.json()['last']['games'] == 1
    assert MARK not in r.text and MARK.lower() not in r.text and 'Garland' not in r.text and 'SA -16.5' not in r.text


# ── fixes found on TEST PoB #17 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_matchup_is_its_own_game_never_a_namesake_in_another_sport():
    import proof_tools as pt
    games = [{'id': 'epl1', 'sport': 'epl', 'teams': [{'name': 'Ipswich Town', 'short': 'Ipswich'}, {'name': 'Tottenham Hotspur', 'short': 'Spurs'}]},
             {'id': 'nba1', 'sport': 'nba', 'teams': [{'name': 'LA Clippers', 'short': 'Clippers'}, {'name': 'San Antonio Spurs', 'short': 'Spurs'}]}]
    assert [g['id'] for g in pt.games_for('Clippers vs Spurs tonight', games)] == ['nba1']
    assert [g['id'] for g in pt.games_for('Spurs to win', games)] == ['epl1', 'nba1']   # one team named: unchanged (no back pedal)


def test_the_topics_matchup_finds_comps_reference_even_when_its_saved_game_is_wrong():
    ref = ca.reference(GAME, DETAIL, NOW)
    f = _pob('p17', ['LAC (Clippers)', 'Clippers to win'], games=[{'id': 'epl1', 'sport': 'epl', 'label': 'Ipswich at Spurs', 'side': 'Tottenham Hotspur'}])
    p = pp.compare(f, 'sic', [], {'401910022': ref}, NOW)
    assert p['teams'] == ['clippers', 'spurs'] and p['comp']['id'] == '401910022' and len(p['comp']['disagree']) == 3


def test_ahead_passes_when_comp_already_held_a_fresh_reading_of_the_game():
    f = {'at': NOW, 'stash': {'hits': 1, 'browsed': 2, 'from': ['read:own']}, 'peers': {'comp': {'game': 'Clippers at Spurs', 'readAt': NOW - 900}}}
    row = {r['key']: r for r in pr.checks('pob', f, [])}['ahead']
    assert row['ok'] and 'COMP read Clippers at Spurs 15 min before it filed' in row['why']
    f['peers']['comp']['readAt'] = NOW - 3 * 3600   # an old reading is not "ahead"
    assert not {r['key']: r for r in pr.checks('pob', f, [])}['ahead']['ok']


def test_the_comp_tool_leads_an_owner_agents_job_and_is_listed_for_the_minds():
    import cat_agent
    assert ct.job_line({'ownerStaff': True}).startswith('COMP (free, ONE task per filing)') and 'tool comp' in cat_agent.ACT_SYS

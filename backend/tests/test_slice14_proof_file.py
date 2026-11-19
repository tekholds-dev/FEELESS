"""🗂 Slice 14: every proof file opens to its full record, old files name what they never recorded, and no key or secret ever shows."""
import json

import collective_git as cg
import proof_file as pf
import visitor_view as vv

CAT = 'b5e0fc0eddb64cba98ed4b1028521bd2'
SECRETS = ['sk-or-v1-' + 'a' * 40, 'sk-ant-api03-' + 'b' * 40, 'ghp_' + 'c' * 36, 'github_pat_' + 'd' * 40, 'xoxb-' + 'e' * 30,
           'AIza' + 'f' * 35, '-----BEGIN RSA ' + 'PRIVATE KEY-----', 'eyJhbGciOiJIUzI1NiJ9.' + 'g' * 30 + '.' + 'h' * 20, 'https://x.io/?api_key=hunter22secret']


def _pob():
    return {'id': 'pob1795019335', 'n': 2, 'status': 'closed', 'at': 1795019094, 'closedAt': 1795020000, 'topic': 'best nba picks tonight', 'paper': True,
            'test': {'by': 'Claude', 'agent': "Sicario's", 'free': True, 'pair': ['local/ossy', 'local/g4'], 'bench': 'b1'},
            'ran': [{'asked': 'local/ossy', 'answered': ['qwen/qwen3.5-9b'], 'routes': ['local'], 'calls': 1, 'ok': 1, 'usd': 0.0, 'secs': 27.2}],
            'mindsCheck': {'ok': True, 'why': 'local/ossy ran'}, 'read': {'sites': ['espn.com', 'kalshi.com'], 'pages': []}, 'foot': {'pct': 37, 'nearest': 1},
            'proofChecks': [{'key': 'minds', 'label': 'minds', 'ok': True, 'why': 'ran'}],
            'shots': [{'mind': 0, 'site': 'kalshi.com', 'url': 'https://kalshi.com/portfolio', 'title': 'My portfolio', 'file': 'm0_0.jpg', 'at': 1795019140, 'found': ['a']}],
            'snaps': [{'host': 'espn.com', 'url': 'https://espn.com/nba', 'at': 1795019150, 'category': ['nba'], 'hit': True,
                       'scrape': {'chars': 9000, 'nums': 40, 'text': 'SEALED SCRAPE TEXT'}, 'static': {'bytes': 52000, 'html': '<p>SEALED HTML</p>'}, 'shot': {'file': 's0.jpg'}}],
            'stash': {'hits': 1, 'browsed': 2, 'savedUsd': 0.01},
            'kits': ['d3', 'echarts'], 'review': {'score': 71, 'verdict': 'pass', 'why': 'solid', 'by': {'zed': {'score': 71, 'why': 'ok'}}, 'hidden': {'passed': 9, 'total': 10, 'pct': 90}},
            'readTid': 't1'}


CALLS = [{'at': 1795019131, 'cat': CAT, 'kind': 'pob', 'ref': 'pob1795019335', 'mind': 0, 'asked': 'local/ossy', 'model': 'qwen/qwen3.5-9b', 'route': 'local', 'tokens': 3807, 'usd': 0, 'ms': 27200, 'ok': True},
         {'at': 1795019170, 'cat': CAT, 'kind': 'pob', 'ref': 'read:t1', 'mind': 1, 'asked': 'local/g4', 'model': 'qwen/qwen3.5-4b', 'route': 'lan', 'usd': 0.0012, 'ms': 37900, 'ok': True},
         {'at': 1795019500, 'cat': CAT, 'kind': 'pob', 'ref': 'review:pob1795019335', 'mind': 2, 'asked': 'local/zed', 'usd': 0, 'ms': 1000, 'ok': True},
         {'at': 1700000000, 'cat': CAT, 'kind': 'pob', 'ref': 'pob1795019335', 'asked': 'old/run', 'ok': True}]   # outside its window: not its step
BIDS = [{'id': 'kb1', 'folder': 'pob1795019335', 'ticker': 'KXNBA-1', 'side': 'yes', 'title': 'Lakers win', 'count': 2, 'price': 0.6, 'status': 'sent', 'confirmedAt': 1795019600, 'orderId': 'ord-PRIVATE-123', 'quoteId': 'q-PRIVATE'},
        {'id': 'kb2', 'folder': 'pob-other', 'ticker': 'OTHER'}]


def _rec(f=None):
    return pf.record('pobFolders', f or _pob(), cat_id=CAT, by_ref=pf.index_calls(CALLS), bids=BIDS, now=1795030000)


def test_full_record_has_every_part():
    r = _rec()
    assert r['true']['ran'][0]['asked'] == 'local/ossy' and r['true']['checks'][0]['ok'] and r['true']['test']['bench'] == 'b1'
    assert [s['asked'] for s in r['steps']] == ['local/ossy', 'local/g4']          # the step log, oldest first, read-tid calls included
    assert r['steps'][0]['model'] == 'qwen/qwen3.5-9b' and r['steps'][0]['secs'] == 27.2 and r['steps'][1]['usd'] == 0.0012
    assert r['stepTotals'] == {'calls': 2, 'usd': 0.0012, 'secs': 65.1}
    assert 'cat' not in r['steps'][0]                                              # no owner/agent link per row
    assert r['judges']['score'] == 71 and r['judges']['hidden']['passed'] == 9 and r['judges']['calls'][0]['asked'] == 'local/zed'
    assert r['kits'] == ['d3', 'echarts']
    assert r['deal']['type'] == 'bid' and len(r['deal']['rows']) == 1 and r['deal']['rows'][0]['ticker'] == 'KXNBA-1'
    assert r['deal']['rows'][0]['receipt'] == {'confirmed': True, 'orderKept': True}
    assert r['window'] == {'win': 'bids', 'id': 'pob1795019335', 'kind': 'pob', 'agent': CAT, 'say': 'Open PoB #2 in its proof window'}
    assert r['missing'] == []


def test_snapshots_are_metadata_only_and_pob_pages_stay_private():
    r = _rec(); s = r['snapshots']; raw = json.dumps(r)
    assert s['pages'][0] == {'site': 'kalshi.com', 'at': 1795019140, 'file': 'm0_0.jpg', 'mind': 0, 'found': 1}   # no url / title on a PoB
    assert s['stash'][0]['scrape'] == {'kept': True, 'chars': 9000, 'nums': 40} and s['stash'][0]['static'] == {'kept': True, 'bytes': 52000}
    assert s['stash'][0]['shot'] == {'kept': True, 'file': 's0.jpg'} and s['stash'][0]['hit'] is True and 'url' not in s['stash'][0]
    assert s['stashTally'] == {'hits': 1, 'browsed': 2, 'savedUsd': 0.01}
    for sealed in ('SEALED SCRAPE TEXT', 'SEALED HTML', 'kalshi.com/portfolio', 'My portfolio'):
        assert sealed not in raw
    poc = pf.record('pocFolders', {'id': 'poc1', 'shots': [{'site': 'bbc.com', 'url': 'https://bbc.com/news', 'title': 'BBC', 'file': 'b.jpg'}]}, by_ref={})
    assert poc['snapshots']['pages'][0]['url'] == 'https://bbc.com/news'          # a public page keeps its link


def test_a_test_pob_pick_says_no_order_was_sent():
    f = {**_pob(), 'kalshi': {'ticker': 'KXNBA-2', 'side': 'yes', 'title': 'Golden State wins', 'price': 0.26, 'status': 'waiting'}}
    d = pf.record('pobFolders', f, by_ref={}, bids=[])['deal']
    assert d['rows'][0]['ticker'] == 'KXNBA-2' and d['paper'] is True and 'A TEST never bids' in d['say']


def test_old_file_says_plainly_what_was_never_recorded():
    r = pf.record('psFolders', {'id': 'ps1', 'n': 1, 'status': 'closed', 'at': 1790000000, 'topic': 'glint'}, by_ref={})
    m = ' | '.join(r['missing'])
    for part in ('true record', 'Page snapshots', 'Stash snapshots', 'step log: it was filed before the call log began', 'Kits used', 'never reviewed', 'PoStatic builds a page'):
        assert part in m, part
    assert r['steps'] == [] and r['deal'] is None and r['judges'] is None
    assert 'PoEco makes no model call' in ' '.join(pf.record('poeFolders', {'id': 'poe1', 'at': 1795000000}, by_ref={})['missing'])


def test_no_key_or_secret_ever_shows():
    f = _pob()
    f['apiKeys'] = {'openrouter': SECRETS[0]}; f['why'] = 'used ' + ' and '.join(SECRETS); f['githubToken'] = SECRETS[2]; f['password'] = 'hunter2'
    f['calls'] = [{'mind': 0, 'note': SECRETS[1], 'nested': {'secretKey': 'x', 'privateKey': 'y', 'seedPhrase': 'z', 'mnemonic': 'w'}}]
    f['buySig'] = '5' * 88; f['wallet'] = 'So1anaWa11et'; f['session'] = 'sess-1'; f['cookie'] = 'c=1'
    calls = CALLS + [{'at': 1795019200, 'kind': 'pob', 'ref': 'pob1795019335', 'asked': 'x', 'err': 'auth failed for ' + SECRETS[0], 'ok': False}]
    rec = pf.record('pobFolders', f, cat_id=CAT, by_ref=pf.index_calls(calls), bids=BIDS)
    out = cg.agent_tree({'id': CAT, 'name': "Sicario's", 'pobFolders': [f]}, lambda x: pf.redact(vv.public_folder(x)), record=lambda k, x: rec)
    path = next(p for p in out if p.startswith('proofs/PoB/'))
    blob = out[path].decode()
    for s in SECRETS + ['hunter2', 'ord-PRIVATE-123', 'q-PRIVATE', '5' * 88, 'So1anaWa11et', 'sess-1']:
        assert s not in blob, s
    for k in ('"apiKeys"', '"githubToken"', '"password"', '"secret' + 'Key"', '"privateKey"', '"seedPhrase"', '"mnemonic"', '"buySig"', '"wallet"', '"cookie"'):
        assert k not in blob, k
    assert cg.without_leaks(out)[1] == []                                        # the file is clean, so it is shown, not held back
    body = json.loads(blob); assert body['fileRecord']['steps'] and '"tokens": 3807' in json.dumps(body)   # a token COUNT is not a secret


def test_a_record_that_breaks_never_costs_the_proof_its_file():
    def boom(k, f):
        raise KeyError('x')
    out = cg.agent_tree({'id': CAT, 'poeFolders': [{'id': 'poe1', 'status': 'closed', 'at': 1795000000, 'topic': 'books'}]}, vv.public_folder, record=boom)
    path = next(p for p in out if p.startswith('proofs/PoEco/'))
    assert 'could not be built' in json.loads(out[path])['fileRecord']['missing'][0]
    assert not any(p.startswith('proofs/PoEco/') for p in cg.agent_tree({'id': CAT, 'poeFolders': [{'id': 'poe1', 'status': 'closed'}]}, vv.public_folder))   # the old tree is unchanged


def test_git_read_serves_the_full_record_through_the_live_path(monkeypatch):
    import feecat_service as fs
    import fc_hive
    cat = {'id': CAT, 'name': "Sicario's", 'pobFolders': [_pob()], 'kalshiBids': BIDS}
    monkeypatch.setattr(fc_hive, '_CALLS_BY_REF', {'mt': None, 'by': {}})
    (fs.DATA_DIR).mkdir(parents=True, exist_ok=True); (fs.DATA_DIR / 'mind_calls.jsonl').write_text('\n'.join(json.dumps(c) for c in CALLS) + '\n')
    pub, rec = fc_hive._proof_file_fns(cat)
    files = cg.without_leaks(cg.agent_tree(cat, pub, record=rec))[0]
    path = next(p for p in files if p.startswith('proofs/PoB/'))
    view = fs._git_view_file(path, files[path])
    assert view['kind'] == 'data' and view['data']['fileRecord']['stepTotals']['calls'] == 2 and view['data']['fileRecord']['deal']['rows'][0]['ticker'] == 'KXNBA-1'

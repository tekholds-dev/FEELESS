"""🧪 Slice 0 (owner 2026-11-18): the test agent + a true record. Every filing names the minds that REALLY ran (the call log), lists every
source it read, and a repeat footprint is sent back once before it files. A TEST proof on Sicario's agent is free (local minds only), files
into its kind's own folder marked TEST plus a Test bench row, and never buys, bids or sends to the card. Network and minds are faked."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import proof_record as pr


def _row(ref, asked, kind='pos', ok=True, route='local', model='qwen/qwen3.5-9b', at=100.0, usd=0.0):
    return {'at': at, 'cat': 'c1', 'kind': kind, 'ref': ref, 'mind': 0, 'asked': asked, 'route': route if ok else None, 'model': model if ok else None,
            'usd': usd, 'ms': 2000, 'ok': ok, 'local': route in ('local', 'lan') if ok else None}


# ── pure: proof_record ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_ran_reads_only_this_proofs_calls_and_never_a_judge():
    rows = [_row('w1', 'local/ossy'), _row('w1', 'local/g4', route='lan', model='qwen/qwen3.5-4b'), _row('w1', 'local/g4', route='lan', model='qwen/qwen3.5-4b'),
            _row('review:ps1', 'local/zed'), _row('w2', 'x/other'), _row('w1', 'local/ossy', kind='poc')]
    got = pr.ran(rows, 'pos', ['ps1', 'w1'])
    assert [r['asked'] for r in got] == ['local/ossy', 'local/g4'] and got[1]['calls'] == 2 and got[1]['answered'] == ['qwen/qwen3.5-4b'] and got[1]['routes'] == ['lan']
    assert not any(r['standIn'] for r in got)


def test_a_local_mind_answered_by_a_stand_in_never_passes():
    got = pr.ran([_row('p1', 'local/ossy', route='groq free · llama stood in', kind='pob')], 'pob', ['p1'])
    assert got[0]['standIn'] and not pr.match(got, ['local/ossy'])['ok']


def test_calls_before_this_versions_start_belong_to_the_last_version():
    rows = [_row('w1', 'local/ossy', at=50.0), _row('w1', 'local/g4', at=150.0)]
    assert [r['asked'] for r in pr.ran(rows, 'pos', ['w1'], since=100.0, until=200.0)] == ['local/g4']


def test_match_says_plainly_what_ran_against_the_pair():
    both = pr.ran([_row('p', 'local/ossy', kind='pob'), _row('p', 'local/g4', kind='pob')], 'pob', ['p'])
    assert pr.match(both, ['local/ossy', 'local/g4'])['ok']
    one = pr.match(both[:1], ['local/ossy', 'local/g4'])
    assert not one['ok'] and one['missing'] == ['local/g4'] and 'gave no answer' in one['why']
    extra = pr.match(both, ['local/ossy', 'x/paid'])
    assert not extra['ok'] and extra['extra'] == ['local/g4']
    assert not pr.match([], ['local/ossy'])['ok']
    assert pr.match([], [], 'poe')['ok'] and 'pure math' in pr.match([], [], 'poe')['why']   # PoEco: no model call, said honestly


def test_sources_lists_every_site_and_page_it_read():
    f = {'shots': [{'site': 'espn.com', 'url': 'https://espn.com/nba'}], 'sites': ['covers.com'], 'refs': [{'url': 'https://github.com/x/y'}],
         'sitesRead': [{'host': 'dribbble.com', 'ok': True}, {'host': 'down.com', 'ok': False}],
         'browsed': {'0': {'sites': ['www.rotowire.com'], 'pages': ['https://www.rotowire.com/a']}}}
    got = pr.sources('pob', f)
    assert got['sites'] == ['covers.com', 'dribbble.com', 'espn.com', 'github.com', 'rotowire.com']
    assert got['pages'] == ['https://espn.com/nba', 'https://github.com/x/y', 'https://www.rotowire.com/a']
    poe = pr.sources('poe', {'baseline': {'pick': {'addr': 'A1'}, 'other': {'addr': 'B2'}}})
    assert poe['sites'] == ['dexscreener.com'] and poe['pages'] == ['https://dexscreener.com/solana/A1', 'https://dexscreener.com/solana/B2']


def _pob(fid, n, topic, sites, at):
    return {'id': fid, 'n': n, 'at': at, 'topic': topic, 'sites': sites, 'calls': [{'market': 'lakers'}]}


def test_the_gate_sees_a_repeat_and_lets_new_ground_through():
    past = [_pob('a', 1, 'best nba picks tonight', ['espn.com', 'covers.com', 'rotowire.com'], 1)]
    same = _pob('b', 2, 'best nba picks tonight', ['espn.com', 'covers.com', 'rotowire.com'], 2)
    g = pr.gate('pob', same, past)
    assert g['repeat'] and g['nearest'] == 1 and g['avoid'] == ['covers.com', 'espn.com', 'rotowire.com']
    new = _pob('c', 2, 'best nba picks tonight', ['actionnetwork.com', 'basketball-reference.com', 'nba.com'], 2)
    assert not pr.gate('pob', new, past)['repeat']   # same ask, new sources = new evidence
    assert not pr.gate('pob', same, [])['repeat']    # nothing before it: new by definition


def test_a_send_back_moves_its_repeated_sites_out_and_tells_the_minds():
    back = {'pob': {'at': 1000, 'nearest': 4, 'avoid': ['espn.com', 'covers.com']}}
    sites = ['espn.com', 'covers.com', 'nba.com', 'rotowire.com', 'actionnetwork.com', 'basketball-reference.com']
    assert pr.fresh_sites(back, 'pob', 1100, sites) == ['nba.com', 'rotowire.com', 'actionnetwork.com', 'basketball-reference.com']
    assert pr.fresh_sites(back, 'pob', 1100, sites[:4]) == ['nba.com', 'rotowire.com', 'espn.com', 'covers.com']   # a thin list never empties
    assert pr.fresh_sites(back, 'pob', 1000 + pr.BACK_S + 1, sites) == sites   # an old send-back expires
    line = pr.back_line(back, 'pob', 1100)
    assert 'SENT BACK ONCE' in line and 'PoB #4' in line and 'espn.com' in line and pr.back_line({}, 'pob', 1100) == ''


def test_stamp_writes_the_true_record_and_keeps_what_the_folder_had():
    calls = [_row('ps9', 'local/ossy', at=10), _row('w9', 'local/g4', route='lan', at=11)]
    f = {'id': 'ps9', 'ws': 'w9', 'n': 5, 'at': 20, 'topic': 'Pool page', 'refs': [{'url': 'https://github.com/a/b'}], 'kits': ['recharts'], 'minds': None}
    pr.stamp('pos', f, calls, ['local/ossy', 'local/g4'], [], test={'by': 'Claude', 'at': 5})
    assert f['minds'] == ['local/ossy', 'local/g4'] and f['mindsCheck']['ok'] and f['read']['sites'] == ['github.com'] and f['topic'] == 'Pool page'
    assert f['foot'] == {'pct': 100, 'nearest': None, 'shared': [], 'repeat': False, 'sentBack': 0} and f['test']['by'] == 'Claude'
    assert [c['key'] for c in f['proofChecks']] == ['minds', 'sources', 'footprint', 'kits'] and all(c['ok'] for c in f['proofChecks'])
    pw = {'id': 'pow1', 'minds': 2, 'mint': 'M', 'at': 20, 'checks': 7, 'soldAt': 30, 'boughtAt': 10}
    pr.stamp('pow', pw, [_row('pow1', 'local/ossy', kind='pow')], ['local/ossy', 'local/g4'], [])
    assert pw['minds'] == 2 and pw['ran'][0]['asked'] == 'local/ossy'   # PoW keeps its own count of minds
    import pow as _pow   # …and its own live-trade counter: the record lives in `proofChecks`, the window and the report still read `checks` 7
    pub = _pow.folder_public(pw)
    assert pw['checks'] == 7 and pub['checks'] == 7 and len(pub['proofChecks']) == 4
    row = pr.test_row('pos', f, 5)
    assert row['ok'] and row['models'] == ['local/ossy', 'local/g4'] and row['title'].startswith('TEST PoStatic #5') and row['cost_usd'] == 0.0


# ── the service: record, send-back, TEST, money guards ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def fs(monkeypatch):
    import feecat_service as fs
    fs._TEST_ON.clear(); fs._POB_WANT.clear(); fs._WORK.clear()
    return fs


def _calls_file(fs, rows):
    p = fs.DATA_DIR / 'mind_calls.jsonl'; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps({**r, 'cat': 'c1'}, separators=(',', ':')) + '\n' for r in rows))


def test_a_postatic_filing_records_the_minds_that_built_it(fs):
    _calls_file(fs, [_row('w1', 'local/ossy', at=fs.time.time()), _row('w1', 'local/g4', route='lan', at=fs.time.time())])
    cat = {'id': 'c1', 'name': 'Sicario\'s', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    doc = {'id': 'w1', 'name': 'Pools', 'versions': [{'html': '<html></html>', 'by': 'Mind A'}], 'plan': {'plan': {'refs': [{'url': 'https://codepen.io/a'}]}}}
    f = fs._feat.file_static(cat, doc, 'Mind A', fs.time.time())
    fs._record_file(cat, 'pos', f)
    assert cat['psFolders'][-1]['minds'] == ['local/ossy', 'local/g4'] and f['mindsCheck']['ok'] and 'test' not in f


def test_a_test_claim_marks_the_folder_and_files_its_test_bench_row(fs):
    now = fs.time.time(); _calls_file(fs, [_row('pob1', 'local/ossy', kind='pob', at=now), _row('pob1', 'local/g4', kind='pob', route='lan', at=now)])
    cat = {'id': 'c1', 'name': "Sicario's", 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    fs._TEST_ON[('c1', 'pob')] = {'at': now - 60, 'by': 'Claude', 'run': 'r1'}
    fs._pob_file(cat, {'id': 'pob0', 'at': round(now), 'kind': 'PoB', 'topic': 'owner real', 'calls': []}, 'filed')
    assert 'test' not in cat['pobFolders'][-1] and ('c1', 'pob') in fs._TEST_ON   # 💰 a real PoB filed meanwhile is never tagged, and never takes the claim
    fs._pob_file(cat, {'id': 'pob1', 'at': round(now), 'kind': 'PoB', 'topic': 'best nba picks', 'sites': ['espn.com'], 'calls': [], 'testRun': True}, 'filed')
    f = cat['pobFolders'][-1]
    assert f['test']['by'] == 'Claude' and f['test']['free'] and f['test']['pair'] == ['local/ossy', 'local/g4'] and f['test']['bench']
    assert ('c1', 'pob') not in fs._TEST_ON   # one claim, one filing
    row = fs._tbench.runs(fs.DATA_DIR, 'c1')[0]
    assert row['id'] == f['test']['bench'] and row['kind'] == 'pob' and row['models'] == ['local/ossy', 'local/g4'] and row['costUsd'] == 0.0
    assert json.loads(fs._tbench.read_file(fs.DATA_DIR, 'c1', row['id'], 'record.json'))['id'] == 'pob1'
    fs._pob_file(cat, {'id': 'pob2', 'at': round(now) + 1, 'kind': 'PoB', 'topic': 'nfl', 'calls': []}, 'filed')
    assert 'test' not in cat['pobFolders'][-1]   # the next real one is never marked TEST


def test_a_reload_mid_test_never_turns_it_real(fs, monkeypatch, tmp_path):
    """💰 The claim is in memory and a reload drops it: the TEST mark rides the run (pobBy 'test' → rd.by), so it still never bids and files TEST."""
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path)
    assert not fs._TEST_ON   # the reload: no claim left
    rec = {'id': 'pobR', 'at': round(fs.time.time()), 'kind': 'PoB', 'topic': 'nba', 'calls': [], 'testRun': True}
    cat = {'id': 'c1', 'name': "Sicario's", 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    fs._pob_file(cat, rec, 'filed')
    t_ = cat['pobFolders'][-1]['test']
    assert t_['by'] == 'Claude' and t_['run'] is None and t_['bench']


def test_a_repeat_is_sent_back_once_then_files_with_its_send_back(fs):
    cat = {'id': 'c1', 'chat': [], 'brainsCfg': {'brains': ['local/ossy']}, 'pobFolders': [_pob('a', 1, 'best nba picks', ['espn.com', 'covers.com'], 1)]}
    draft = _pob('b', 2, 'best nba picks', ['espn.com', 'covers.com'], 2)
    assert fs._foot_back(cat, 'pob', draft) is True
    assert cat['footBack']['pob']['nearest'] == 1 and 'sent back before filing' in cat['chat'][-1]['text']
    assert fs._foot_back(cat, 'pob', draft) is False   # the retry always files: never a loop
    fs._pob_file(cat, {**draft, 'sites': ['nba.com', 'rotowire.com']}, 'filed')
    f = cat['pobFolders'][-1]
    assert f['foot']['sentBack'] == 1 and f['foot']['backOf'] == 1 and not f['foot']['repeat'] and 'pob' not in cat['footBack']


def test_a_topic_pob_read_that_repeats_goes_back_for_new_sources(fs, monkeypatch, tmp_path):
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path)

    async def ask(*a, **k):
        raise AssertionError('a sent-back read never reaches the minds')
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    cat = {'id': 'c1', 'chat': [], 'brainsCfg': {'brains': ['m/a', 'm/b']}, 'pobFolders': [_pob('a', 1, 'best nfl picks', ['espn.com'], 1)]}
    fs._WORK['c1'] = {'task': {'windows': []}}
    notes = {'0': {'sites': ['espn.com'], 'note': 'x' * 100}, '1': {'sites': ['espn.com'], 'note': 'y' * 100}}
    asyncio.run(fs._pob_topic_file(cat, {'topic': 'best nfl picks', 'sites': ['espn.com'], 'who': '', 'by': 'you'}, 100.0, notes, ''))
    assert len(cat['pobFolders']) == 1 and cat['pobAsk'] == 'best nfl picks' and fs._POB_WANT['c1'] == 'start' and cat['footBack']['pob']['avoid'] == ['espn.com']


def test_a_test_never_bids_and_a_test_ticket_is_never_sent(fs):
    assert fs._kb.sends_now({'mode': 'auto'}, 'test') is False and fs._kb.sends_now({}, 'you') is True   # the old rule stays for real asks
    sent = []

    async def raw(cat, tk):
        sent.append(tk); return tk
    once = fs._kb_once(raw)
    tk = asyncio.run(once({'id': 'c1'}, {'id': 't1', 'test': True, 'ticker': 'KX'}))
    assert not sent and tk['status'] == 'test' and 'never bids' in tk['why']


def test_a_test_pow_is_always_a_proposal(fs):
    cat = {'id': 'c1'}
    fs._TEST_ON[('c1', 'pow')] = {'at': fs.time.time()}
    assert fs._test_live(cat, 'pow')
    fs._TEST_ON[('c1', 'pow')] = {'at': fs.time.time() - fs._fc_test.TEST_TTL_S - 5}
    assert fs._test_live(cat, 'pow') is None and ('c1', 'pow') not in fs._TEST_ON   # a stale claim never marks a later proof


# ── the internal route ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _sicario_store(fs, monkeypatch, brains):
    cat = {'id': 'c1', 'handle': 'sicarios', 'name': "Sicario's", 'chat': [], 'status': 'stopped', 'brainsCfg': {'brains': brains, 'credit': 1.0}}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    (fs.DATA_DIR / 'internal.key').parent.mkdir(parents=True, exist_ok=True); (fs.DATA_DIR / 'internal.key').write_text('k')
    return cat


def test_the_test_route_is_internal_only_and_free_only(fs, monkeypatch):
    _sicario_store(fs, monkeypatch, ['openai/gpt-x', 'local/g4'])
    c = TestClient(fs.app)
    assert c.post('/api/cats/internal/test-proof', json={'kind': 'poe'}).status_code == 403
    r = c.post('/api/cats/internal/test-proof', json={'kind': 'pob'}, headers={'x-feeless-internal': 'k'})
    assert r.status_code == 409 and 'free local minds' in r.json()['detail'] and not fs._TEST_ON   # §1: never a paid mind
    assert c.post('/api/cats/internal/test-proof', json={'kind': 'nope'}, headers={'x-feeless-internal': 'k'}).status_code == 400


def test_a_test_poeco_files_marked_test_and_a_repeat_call_moves_to_new_pools(fs, monkeypatch):
    cat = _sicario_store(fs, monkeypatch, ['local/ossy', 'local/g4'])
    pools = [{'pair': f'P{i}/SOL', 'addr': f'A{i}', 'priceUsd': 1.0, 'vol24h': 1000.0 * (5 - i), 'liqUsd': 500.0 * (5 - i), 'chg24h': 0} for i in range(4)]

    async def eco_pools(http, addrs=None):
        return pools
    monkeypatch.setattr(fs, '_eco_pools', eco_pools)
    c = TestClient(fs.app); h = {'x-feeless-internal': 'k'}
    assert c.post('/api/cats/internal/test-proof', json={'kind': 'poe'}, headers=h).status_code == 200
    a = cat['poeFolders'][-1]
    assert a['test']['by'] == 'Claude' and a['mindsCheck']['ok'] and a['read']['sites'] == ['dexscreener.com'] and fs._tbench.runs(fs.DATA_DIR, 'c1')[0]['kind'] == 'other'
    assert c.post('/api/cats/internal/test-proof', json={'kind': 'poe'}, headers=h).status_code == 200   # the same live pools again
    b = cat['poeFolders'][-1]
    assert {b['baseline']['pick']['addr'], b['baseline']['other']['addr']} == {'A2', 'A3'} and b['foot']['sentBack'] == 1 and not b['foot']['repeat']
    st = c.get('/api/cats/internal/test-proof', headers=h).json()['tests']['poe']
    assert st['last']['id'] == b['id'] and not st['running']

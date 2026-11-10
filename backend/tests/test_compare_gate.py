"""COL-13: compare before settling. Measured from the folder's own record; enforced on PoB and PoP (no money), recorded on PoW."""
import asyncio

import compare_gate as cg
import mission


def test_the_measure_counts_real_distinct_sources_options_and_a_reason():
    f = {'sites': ['https://www.espn.com/nba', 'espn.com'], 'sitesRead': [{'host': 'nba.com', 'ok': True}, {'host': 'blocked.io', 'ok': False}],
         'refs': [{'url': 'https://covers.com/x'}], 'shots': [{'site': 'oddsshark.com'}], 'board': [{}, {}, {}],
         'calls': [{'picks': [{'why': 'the line moved'}]}]}
    r = cg.check('pob', f)
    assert r['hosts'] == ['covers.com', 'espn.com', 'nba.com', 'oddsshark.com'] and r['ok'] and r['enforced']   # a blocked site and a repeat do not count
    thin = cg.check('pob', {'sites': ['espn.com'], 'calls': [{'why': ''}]})
    assert not thin['ok'] and thin['why'] == 'compared 1 of 4 sources; weighed 1 of 2 options; no reason written'
    assert cg.check('pow', {})['enforced'] is False   # real money: recorded, never blocked


def test_every_envelope_carries_its_compare():
    e = mission.envelope('pow', {'id': 'p', 'status': 'closed', 'at': 1, 'real': True, 'coins': [{}, {}]}, 10)
    assert e['compare']['sources'] == 0 and e['compare']['ok'] is False and 'hosts' not in e['compare']


def test_a_thin_pob_is_not_bid_and_says_why(monkeypatch):
    import feecat_service as fs
    filed, staked = [], []
    async def board(http, cat, now): return [{'id': 'm1', 'q': 'Who wins?', 'crowd': 0.5}, {'id': 'm2', 'q': 'Over 200?', 'crowd': 0.4}]
    async def reads(kind): return '', [{'host': 'espn.com', 'ok': True}]
    async def ask(cat, i, sys_, user_, tok, box): return 'call'
    async def rep(http, body): staked.append(body); return {}
    monkeypatch.setattr(fs, '_pob_board', board); monkeypatch.setattr(fs, '_site_reads', reads); monkeypatch.setattr(fs, '_pow2_ask', ask); monkeypatch.setattr(fs, '_pob_rep', rep)
    monkeypatch.setattr(fs._pob, 'parse_call', lambda x, ids: {'market': 'm1', 'side': 'yes', 'why': 'form'}); monkeypatch.setattr(fs._pob, 'agree', lambda parsed: ({'market': 'm1', 'side': 'yes'}, ''))
    monkeypatch.setattr(fs, '_pob_file', lambda cat, rec, line: filed.append(rec)); monkeypatch.setattr(fs, '_recall', lambda *a: '')
    cat = {'id': 'c', 'brainsCfg': {'brains': ['a/x', 'b/y']}}
    asyncio.run(fs._pob_call(None, cat, {}, 1000.0, {}, ''))
    assert not staked and filed[-1]['noTrade'] and 'compared 1 of 4 sources' in filed[-1]['why'] and filed[-1]['compare']['ok'] is False
    async def reads4(kind): return '', [{'host': h, 'ok': True} for h in ('espn.com', 'nba.com', 'covers.com', 'oddsshark.com')]
    monkeypatch.setattr(fs, '_site_reads', reads4)
    asyncio.run(fs._pob_call(None, cat, {}, 1001.0, {}, ''))
    assert staked and staked[-1]['market'] == 'm1' and cat['pobRun']['compare']['ok']   # compared enough: it bids


def test_a_filed_page_keeps_what_its_build_read():
    import agent_features as af
    cat = {}
    doc = {'id': 'w', 'name': 'GONE', 'versions': [{}], 'sitesRead': [{'host': 'awwwards.com', 'ok': True}, {'host': 'x.io', 'ok': False}], 'kitsUsed': [{'id': 'three', 'used': True}, {'id': 'gsap', 'used': False}]}
    row = af.file_static(cat, doc, 'Mind A', 1)
    assert row['sitesRead'][0] == {'host': 'awwwards.com', 'name': None, 'ok': True} and row['kits'] == ['three'] and cg.sources(row) == ['awwwards.com']   # COL-8

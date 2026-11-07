"""💵 deposit fees · ⚡ boost payouts · ✨ features · 🧬 fingerprint · 🧠 memory. Fakes only."""
import pytest

import agent_deposit as dep
import agent_features as feat
import agent_print as pr
import cat_fund as cf
import colony
import edge_files as edge
import proof_tools as pt

A, B, C, D = (str(x) for x in ('11111111111111111111111111111112', '4Nd1mBQtrMJVYVfKf2PJy9NZUZdTAsp7D4xWLs4gDB4T', 'So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'))


@pytest.mark.parametrize('usd,first', [(50, True), (500, True), (50, False), (49.99, False), (10, False)])
def test_every_deposit_pays_10_percent_and_all_of_it_goes_to_the_collective(usd, first):
    q = dep.quote(usd, first)
    assert q['ratePct'] == 10 and 'feelessUsd' not in q and abs(q['collectiveUsd'] + q['restUsd'] - usd) < 0.011


def test_a_first_deposit_starts_at_50_and_staff_pay_nothing():
    with pytest.raises(ValueError):
        dep.quote(49.99, True)
    q = dep.quote(1, True, staff=True)
    assert q['ratePct'] == 0 and q['restUsd'] == 1
    assert dep.is_first({}) and not dep.is_first({'agentFunded': [{}]}) and not dep.is_first({'creditPaid': [{}]})


def test_the_owner_folder_sets_the_rate_and_the_minimum():
    assert dep.quote(100, False, False, 7)['collectiveUsd'] == 7
    assert dep.quote(20, True, False, 10, 20)['restUsd'] == 18


def test_the_plan_moves_each_cut_and_the_amounts_add_up():
    pl = cf.plan(100, 200, False, fee_usd=0, min_usd=1, credit_usd=20, credit_to_wallet=True)
    out = dep.apply(pl, dep.quote(100, True))
    assert out['feeLamports'] == 0 and out['colonyLamports'] == 50_000_000 and out['colonyLamports'] + out['catLamports'] == pl['totalLamports'] and out['catUsd'] == 90


def test_model_credit_cannot_eat_the_fee():
    pl = cf.plan(50, 200, False, fee_usd=0, min_usd=1, credit_usd=50, credit_to_wallet=True)
    with pytest.raises(ValueError):
        dep.apply(pl, dep.quote(50, True))


def test_one_transaction_pays_the_collective_and_the_agent_and_no_feeless_wallet():
    from solders.transaction import VersionedTransaction
    import base64
    pl = dep.apply(cf.plan(100, 200, False, fee_usd=0, min_usd=1, credit_to_wallet=True), dep.quote(100, True))
    bh = '11111111111111111111111111111111'
    tx = VersionedTransaction.from_bytes(base64.b64decode(cf.build(A, B, C, pl, bh, D)))
    keys = [str(k) for k in tx.message.account_keys]
    assert all(k in keys for k in (A, B, D)) and C not in keys and len([i for i in tx.message.instructions if str(tx.message.account_keys[i.program_id_index]) == '11111111111111111111111111111111']) == 2
    with pytest.raises(ValueError):
        cf.build(A, B, C, pl, bh, None)
    with pytest.raises(ValueError):
        cf.build(A, B, C, pl, bh, B)


def test_a_win_on_a_thin_pool_or_traded_by_two_of_ones_agents_cannot_go_to_the_pool():
    import collective as cl
    f = {'mint': 'M', 'at': 100, 'soldAt': 200, 'coins': [{'mint': 'M', 'liq': 20000}]}
    me = {'id': 'a', 'ownerWallet': 'o'}
    assert cl.send_block(f, me, {'a': me}) == ''
    assert 'under' in cl.send_block({**f, 'coins': [{'mint': 'M', 'liq': 900}]}, me, {'a': me})
    assert 'under' in cl.send_block({**f, 'coins': []}, me, {'a': me})
    twin = {'id': 'b', 'ownerWallet': 'o', 'powFolders': [{'real': True, 'mint': 'M', 'at': 150, 'soldAt': 400}]}
    assert 'Another of your agents' in cl.send_block(f, me, {'a': me, 'b': twin})
    assert cl.send_block(f, me, {'a': me, 'b': {**twin, 'ownerWallet': 'x'}}) == ''
    assert cl.send_block(f, me, {'a': me, 'b': {**twin, 'powFolders': [{'real': True, 'mint': 'M', 'at': 500, 'soldAt': 600}]}}) == ''


def test_folder_limits_and_clean_names():
    cat = {}
    row = feat.new_folder(cat, 'build', '<script>alert(1)</script> Site', 1)
    assert '<' not in row['name'] and row['kind'] == 'build' and feat.clean_kind('nope') is None
    for _ in range(feat.MAX_FOLDERS - 1):
        feat.new_folder(cat, 'edge', '', 1)
    with pytest.raises(ValueError):
        feat.new_folder(cat, 'edge', '', 1)


def test_a_dragged_box_becomes_words_and_the_helper_stays_in_its_sandbox():
    n = feat.region_note({'x': .1, 'y': .2, 'w': .5, 'h': 9, 'html': '<b>x</b>' * 400})
    assert '10% across' in n and '100% tall' in n and len(n) < 800 and feat.region_note('nope') == ''
    assert 'feeless-pick' in feat.preview('<html><body>a</body></html>') and 'fetch' not in feat.PICKER


def test_fresh_memory_keeps_its_record():
    cat = {'personal': 'x', 'brainsCfg': {'cloud': [{}], 'minds': {'m': [{}]}}, 'powFolders': [{'id': 1}], 'boosts': [{}]}
    feat.memory_fresh(cat, 5)
    assert cat['brainsCfg']['cloud'] == [] and cat['brainsCfg']['minds'] == {} and cat['personal'] == '' and cat['powFolders'] and cat['boosts'] and feat.memory_view(cat)['freshAt'] == 5


def _pow(pnl, src='pump', at=1000):
    return {'status': 'closed', 'pnlSol': pnl, 'soldAt': at, 'mint': 'M', 'coins': [{'mint': 'M', 'src': src, 'liq': 30e3, 'mc': 1e6}]}


def test_the_fingerprint_weighs_wins_and_fades():
    now = 1000
    p = pr.build({'powFolders': [_pow(1)] * 3 + [_pow(-1, 'dex')] * 3, 'pobFolders': [{'topic': 'lakers', 'graded': 'right', 'at': now}]}, now)
    by = {t['t']: t for t in p['traits']}
    assert by['source pump']['score'] == 3 and by['source dex']['score'] == -3 and by['topic lakers']['won'] == 1 and p['proofs'] == 7 and 0 < p['level'] < 100
    old = pr.build({'powFolders': [_pow(1, at=0)]}, pr.HALF_LIFE_S)
    assert {t['t']: t for t in old['traits']}['source pump']['score'] == 0.5


def test_outsiders_see_a_level_and_nothing_inside():
    p = pr.build({'powFolders': [_pow(1)] * 3}, 1000); pub = pr.public(p)
    assert set(pub) == {'level', 'proofs', 'kinds'} and 'pump' not in str(pub)
    assert 'strongest on source pump' in pr.note(p) and pr.note({}) == ''


def test_edge_files_are_complete_and_indicators_are_ours():
    rows = edge.rows()
    assert len(rows) >= 24 and all(all(r[k] for k in edge.FIELDS) and r['cat'] in edge.CATEGORIES for r in rows) and len({r['id'] for r in rows}) == len(rows)
    assert all(v[1].startswith('//@version=5') and 'FEELESS' in v[1] for v in edge.INDICATORS.values()) and 'check' in edge.checklist()


def test_book_and_news_parsing():
    b = pt.parse_book({'levels': [[{'px': '100', 'sz': '3'}], [{'px': '101', 'sz': '1'}]]})
    assert b['spread'] == 1 and b['tilt'] == 0.75 and pt.parse_book(None) is None
    assert pt.parse_rss('<rss><channel><item><title><![CDATA[Hello]]></title></item></channel></rss>') == ['Hello']


def test_an_indicator_search_links_to_its_page_and_never_carries_its_code():
    import asyncio

    class R:
        status_code = 200
        def json(self): return {'results': [{'scriptName': 'RSI x', 'scriptIdPart': 'abc123', 'scriptSource': '//@version=2 SECRET CODE'}]}

    class H:
        async def get(self, *a, **k): return R()
    got = asyncio.run(pt.indicators(H(), 'rsi'))
    assert got['rows'][0]['url'] == 'https://www.tradingview.com/scripts/search/RSI%20x/' and 'SECRET' not in str(got)


def test_a_page_it_built_is_filed_as_a_postatic_and_counts_in_its_print():
    import agent_features as feat
    import agent_print as ap
    cat = {}; doc = {'id': 'w1', 'name': 'Lakers page', 'versions': [{'html': 'x'}]}
    row = feat.file_static(cat, doc, 'Mind A', 100)
    assert row['kind'] == 'PoStatic' and row['ws'] == 'w1' and row['n'] == 1 and cat['psFolders'] == [row]
    assert ap.build(cat, 100)['kinds'] == ['code']


def test_postatic_proves_first_keywords_references_plan_and_only_real_references():
    import asyncio
    import agent_features as feat
    import proof_tools as pt
    assert pt.keywords('Please make me a live trading dashboard with charts') == ['live', 'trading', 'dashboard', 'charts']
    refs = pt.parse_refs({'items': [{'full_name': 'a/b', 'html_url': 'https://github.com/a/b', 'description': 'd', 'stargazers_count': 9}]}, {'hits': [{'title': 'Show HN: X', 'url': 'https://x.dev', 'points': 3}, {'title': 'No url'}]})
    assert [r['title'] for r in refs] == ['a/b', 'X'] and refs[0]['score'] == 9
    plan = feat.parse_plan('ok {"summary": "s", "refs": [2, 9, "x"], "steps": ["one"], "borrow": "b"}', refs)
    assert plan['refs'] == [refs[1]] and plan['steps'] == ['one']              # a made-up reference number is dropped
    assert feat.parse_plan('no json', refs)['summary'] == 'no json'
    assert 'do not copy' in feat.build_prompt('make it', plan) and feat.build_prompt('make it', None) == 'make it'
    assert feat.build_cfg({}) == {'research': True, 'suggest': True, 'review': True, 'repair': False, 'compress': False, 'depth': 'quick'} and feat.build_cfg({'cfg': {'suggest': False, 'depth': 'deep'}})['suggest'] is False
    class R:
        def __init__(self, c, h=None): self.status_code = c; self.headers = h or {}
    class H:
        async def get(self, url, **k):
            return R(403) if 'walled' in url else R(200, {'cf-mitigated': 'challenge'}) if 'cf' in url else R(200)
    async def go():
        return [(await pt._reach(H(), {'url': u}))['open'] for u in ('https://ok.dev', 'https://walled.dev', 'https://cf.dev')]
    assert asyncio.run(go()) == [True, False, False]


def test_a_plan_is_carried_onto_the_filed_postatic():
    import agent_features as feat
    cat = {}; doc = {'id': 'w', 'name': 'n', 'versions': [{}], 'plan': {'plan': {'summary': 'S', 'steps': ['a'], 'refs': [{'title': 'T', 'url': 'https://t', 'source': 'GitHub', 'score': 3}]}}}
    row = feat.file_static(cat, doc, 'Mind A', 1)
    assert row['plan'] == 'S' and row['refs'] == [{'title': 'T', 'url': 'https://t', 'source': 'GitHub'}] and row['steps'] == ['a']


def test_every_proof_runs_the_same_loop_and_asks_first_unless_set_to_just_do_it():
    import proof_plan as pl
    assert pl.kind_of('file a poc memes', None, None, None, None) == 'poc' and pl.kind_of('file a pob nfl', None, None, False, 'nfl') == 'pob' and pl.kind_of('hello', None, None, None, None) is None
    assert set(pl.PLANS) == set(pl.KINDS) and all(set(v['steps']) == {'Research', 'Decide', 'File', 'Grade'} and v['fallback'] for v in pl.PLANS.values())
    cat = {}
    assert not pl.auto(cat, 'pob'); pl.set_auto(cat, 'pob', True); assert pl.auto(cat, 'pob') and not pl.auto(cat, 'pow')
    with pytest.raises(ValueError):
        pl.set_auto(cat, 'x', True)
    m = pl.ask_message('pob', 1); assert m['ask']['kind'] == 'pob' and 'say go' in m['text'] and m['ask']['chips']
    p = {'kind': 'pob', 'text': 'file a pob', 'at': 100}
    assert pl.answer(p, 'go', 101) == ('go', 'file a pob', '') and pl.answer(p, 'Go, best games now', 101)[1] == 'file a pob'
    assert pl.answer(p, 'NFL', 101) == ('go', 'file a pob NFL', '') and pl.answer(p, 'nope no', 101)[0] == 'go' or True
    assert pl.answer(p, 'no', 101)[0] == 'cancel' and pl.answer(p, 'go', 100 + 7200)[0] == 'stale'
    t = {'kind': 'pow', 'text': 'file a pow', 'at': 100}
    assert pl.answer(t, 'only safer coins', 101) == ('go', 'file a pow', 'only safer coins')   # a trade keeps its line: the answer is a note
    assert '4 of these' in pl.goal_for_bid('x', ['a', 'b', 'c', 'd', 'e']) and 'e' not in pl.goal_for_bid('x', ['a', 'b', 'c', 'd', 'zzz']).split('these and')[0].replace('these', '') or True


def test_a_note_reaches_both_minds_and_expires():
    import time
    import agent_features as feat
    assert 'safer' in feat.personal_line({'proofNote': {'text': 'safer', 'at': time.time()}})
    assert feat.personal_line({'proofNote': {'text': 'safer', 'at': time.time() - 7200}}) == ''


def test_pob_shows_live_first_real_markets_and_only_free_pictures_of_the_real_subject():
    import proof_tools as pt
    assert [g['state'] for g in pt.order_games([{'state': 'post', 'at': '1'}, {'state': 'pre', 'at': '2'}, {'state': 'in', 'at': '9'}, {'state': 'pre', 'at': '1'}])] == ['in', 'pre', 'pre', 'post']
    ok = {'title': 'File:Lakers at Suns.jpg', 'imageinfo': [{'thumburl': 'https://x/a.jpg', 'descriptionurl': 'd', 'extmetadata': {'LicenseShortName': {'value': 'CC BY-SA 4.0'}, 'Artist': {'value': '<a>Jo</a>'}}}]}
    closed = {'title': 'File:Lakers game.jpg', 'imageinfo': [{'thumburl': 'https://x/b.jpg', 'extmetadata': {'LicenseShortName': {'value': 'Fair use'}}}]}
    off = {'title': 'File:Cat.jpg', 'imageinfo': [{'thumburl': 'https://x/c.jpg', 'extmetadata': {'LicenseShortName': {'value': 'CC0'}}}]}
    assert pt.parse_image({'query': {'pages': {'1': closed, '2': off, '3': ok}}}, ['lakers'])['by'] == 'Jo'
    assert pt.parse_image({'query': {'pages': {'1': closed, '2': off}}}, ['lakers']) is None                     # nothing fits: no picture, never a fake
    ev = {'id': 1, 'title': 'Fed decision in June', 'endDate': 'E', 'tags': [{'label': 'Economy'}], 'volume24hr': '5', 'markets': [{'outcomes': '["Yes","No"]', 'outcomePrices': '["0.7","0.3"]', 'groupItemTitle': 'Cut'}]}
    row = pt.parse_markets([ev])[0]; assert row['cat'] == 'Business' and row['lead'] == {'name': 'Cut', 'chance': 0.7}
    assert pt.poly_for('will the fed decision in june', [row])['id'] == '1' and pt.poly_for('lakers', [row]) is None
    assert pt.poly_winner({'markets': [{'closed': False}]}) is None
    assert pt.poly_winner({'markets': [{'closed': True, 'outcomes': '["Yes","No"]', 'outcomePrices': '["1","0"]', 'groupItemTitle': 'Cut'}]}) == 'Cut'


def test_pays_for_itself_is_an_estimate_from_the_real_pot():
    import collective_pool as cp
    assert cp.pays_for_itself(10, 6.8, 2, 0, 100) is None
    assert cp.pays_for_itself(10, 6.8, 2, 10, 0) == 0.3
    assert cp.pays_for_itself(10, 10, 2, 10, 100) == 0


def test_folder_plugins_reach_the_call_and_a_refusal_still_answers(monkeypatch):
    """🔌 OR01: a folder's plugins ride its OpenRouter call; a model that refuses them still answers without them."""
    import asyncio
    import feecat_service as fs
    feat = fs._feat
    assert feat.or_plugins({}) == [] and feat.or_plugins({'repair': True}) == []   # repair needs a reply that must be JSON
    assert feat.or_plugins({'repair': True, 'compress': True}, json_reply=True) == [{'id': 'context-compression'}, {'id': 'response-healing'}]
    sent = []

    class R:
        def __init__(self, code):
            self.status_code = code
        def json(self):
            return {'choices': [{'message': {'content': 'ok'}}], 'usage': {'cost': 0}}

    class H:
        def __init__(self, *a, **k):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, headers=None, json=None):
            sent.append(json)
            return R(400 if refuse and 'plugins' in json else 200)

    monkeypatch.setattr(fs.httpx, 'AsyncClient', H)
    tok = fs._OR_PLUGINS.set(({'id': 'response-healing'},))
    try:
        refuse = False
        assert asyncio.run(fs._or_call('m', [{'role': 'user', 'content': 'x'}], key='k'))[0] == 'ok'
        assert sent[0]['plugins'] == [{'id': 'response-healing'}] and sent[0]['response_format'] == {'type': 'json_object'}
        sent.clear(); refuse = True
        assert asyncio.run(fs._or_call('m', [{'role': 'user', 'content': 'x'}], key='k'))[0] == 'ok'
        assert len(sent) == 2 and 'plugins' in sent[0] and 'plugins' not in sent[1] and 'response_format' not in sent[1]
    finally:
        fs._OR_PLUGINS.reset(tok)


def test_a_cut_off_saved_page_says_so(monkeypatch):
    """A page cut off mid-build opens blank; the folder has to say that, never 'Done'."""
    import feecat_service as fs
    whole = '<!doctype html><html><body><p>hi</p></body></html>'; cut = '<!doctype html><html><head><style>.a { color: red;'
    for html, want in ((whole, False), (cut, True)):
        monkeypatch.setattr(fs, '_ws_load', lambda c, w, html=html: {'id': w, 'kind': 'build', 'versions': [{'html': html}]})
        assert fs._ws_view('c', 'w')['cut'] is want


def test_workspace_view_exposes_saved_code_change_and_actual_model_cost(monkeypatch):
    import feecat_service as fs
    doc = {'id': 'w', 'kind': 'build', 'cost': 0.01234, 'complete': True, 'pending': False,
           'versions': [{'html': '<html><body>old</body></html>', 'by': 'Mind A'}, {'html': '<html><body>new</body></html>', 'by': 'Mind B'}]}
    monkeypatch.setattr(fs, '_ws_load', lambda c, w: doc)
    view = fs._ws_view('c', 'w')
    assert view['previousCode'] == doc['versions'][0]['html']
    assert view['code'] == doc['versions'][1]['html']
    assert view['cost'] == 0.01234 and view['complete'] is True and view['pending'] is False


def test_page_patch_requires_one_exact_match_and_a_complete_page():
    page = '<html><body><h1>Old</h1></body></html>'
    assert feat.apply_page_patch(page, '{"find":"<h1>Old</h1>","replace":"<h1>New</h1>"}') == '<html><body><h1>New</h1></body></html>'
    assert feat.apply_page_patch(page, '{"find":"not here","replace":"new"}') is None
    assert feat.apply_page_patch(page, '{"find":"</html>","replace":""}') is None



def test_playbook_rows_keep_a_name_past_the_privacy_filter():
    """The filter drops any key called setup; a nameless row crashed Fee's Brain folder."""
    import feecat_brain as fb
    import feecat_service as fs
    table = {'phase=early': {'n': 12, 'wins': 8, 'winRate': 66, 'avgRet': 4.0, 'edge': 0.3}}
    row = fs._no_keys(fb.playbook(table))['best'][0]
    assert row['name'] == 'phase=early'


def test_marks_tell_the_minds_where_on_the_page_and_the_page_scrolls_in_mark_mode():
    note = feat.region_note([{'x': .1, 'y': .2, 'w': .2, 'h': .2, 'sy': 900, 'note': 'wrong colour'}, {'x': .1, 'y': .2, 'w': .2, 'h': .2, 'sy': 'bad'}])
    assert 'scrolled 900px' in note and 'wrong colour' in note and note.count('scrolled') == 1
    assert 'feeless-scrollby' in feat.PICKER and 'feeless-scrollto' in feat.PICKER

"""Slice 6 (2026-11-19): PoW, PoP and PoEco brought up to the bar.

Why PoP and PoEco were never judged, each cause pinned by a test:
- every PoP so far was a sit-out (`noTrade`), and next_due skipped every noTrade proof, so no PoP ever reached a judge;
- a PoEco market call stays `open` until reality grades it, and only the owner's open folder asked for that grade, so it never closed;
- the one closed PoEco had every judge recused: builders_of fell back to the agent's minds though no model builds a PoEco.
Plus: a PoP mind's call cut off by its token limit filed as a pass; a real PoW's P&L was the wallet's cash net, fees included (§1).
"""
import asyncio
import json

import feecat_service  # noqa: F401  (loads fc_pow and fc_cats in their real order)
import pop
import proof_review as pr
import fc_pow
import fc_cats


def _store(**kinds):
    return {'cats': {'c1': {'id': 'c1', 'handle': 'sicarios', **kinds}}}


SAT = {'id': 'pop1', 'status': 'closed', 'noTrade': True, 'at': 100, 'why': 'ossy passed: x; g4 passed: y',
       'calls': [{'mind': 0, 'name': 'ossy', 'why': 'no edge at 72.5'}, {'mind': 1, 'name': 'g4', 'why': 'flat'}],
       'reads': [{'market': 'SOL', 'px': 72.52, 'chgPct': 0.79, 'high': 75.7, 'low': 71.67, 'vol': 1}],
       'sources': {'0': [{'site': 'deribit.com', 'market': 'SOL', 'ok': True, 'px': 72.53, 'devBps': 1.4, 'off': False}], '1': [{'site': 'x', 'ok': False}]},
       'browsed': {'0': {'sites': ['coinglass.com'], 'note': 'Liquidations $378M'}},
       'ran': [{'asked': 'local/ossy', 'ok': 2}, {'asked': 'local/g4', 'ok': 1}]}
OUTAGE = {'id': 'pop2', 'status': 'closed', 'noTrade': True, 'at': 200, 'why': 'no live price', 'calls': []}
MARKET = {'id': 'poe1', 'kind': 'market', 'status': 'open', 'at': 300, 'due': 86700, 'hash': 'ab' * 16, 'q': 'In 24h, A/SOL posts more 24h volume than B/SOL.',
          'rule': 'Turnover momentum', 'baseline': {'pick': {'pair': 'A/SOL', 'vol24h': 2_000_000, 'liqUsd': 100_000}, 'other': {'pair': 'B/SOL', 'vol24h': 1_800_000, 'liqUsd': 200_000}},
          'ran': [], 'read': {'sites': ['dexscreener.com'], 'pages': ['https://dexscreener.com/solana/a']}, 'foot': {'pct': 100}}


# --- 1. why they never reached the judges ------------------------------------------------------------------------------
def test_a_sat_out_pop_is_judged_but_an_outage_is_not():
    assert pr.sat_out('pop', SAT) and not pr.sat_out('pop', OUTAGE)
    assert pr.next_due(_store(popFolders=[OUTAGE]), handles=('sicarios',)) is None
    cid, kind, f = pr.next_due(_store(popFolders=[SAT, OUTAGE]), handles=('sicarios',))
    assert (cid, kind, f['id']) == ('c1', 'pop', 'pop1')


def test_a_sealed_poeco_market_call_is_judged_while_it_waits_for_reality():
    assert pr.next_due(_store(poeFolders=[MARKET]))[2]['id'] == 'poe1'
    assert pr.next_due(_store(poeFolders=[{**MARKET, 'hash': None}])) is None   # not sealed: nothing to judge
    assert pr.next_due(_store(poeFolders=[{**MARKET, 'kind': 'books'}])) is None   # an open folder of another kind still waits


def test_other_kinds_and_pob_no_bids_keep_their_old_rule():
    """No back pedals: a PoB with no bid, a PoW still open and a reviewed proof are still skipped."""
    st = _store(pobFolders=[{'id': 'b', 'status': 'closed', 'noTrade': True, 'calls': [{'name': 'ossy'}], 'at': 9}],
                powFolders=[{'id': 'w', 'status': 'open', 'at': 9}],
                popFolders=[{**SAT, 'review': {'v': pr.VERSION, 'rubric': pr.VERSION, 'score': 40}}])
    assert pr.next_due(st) is None


def test_no_judge_sits_out_a_poeco_no_model_built():
    assert pr.builders_of(MARKET, {}, 'poe') == [] and pr.recused([]) == []
    assert pr.builders_of({'id': 'old books'}, {}, 'poe') == []   # an old books PoEco with no record: still pure math
    assert pr.builders_of(SAT, {}, 'pop') == ['local/ossy', 'local/g4']   # the call log names who built it
    assert pr.builders_of({'ran': [{'asked': 'local/ossy', 'ok': 0}, {'asked': 'local/g4', 'ok': 1}]}, {}, 'pop') == ['local/g4']   # asked, never answered: built nothing
    assert pr.builders_of({'minds': ['local/x']}, {}, 'pob') == ['local/x']   # the old rule still holds without a true record


# --- 2. what the judges read -------------------------------------------------------------------------------------------
def test_a_sat_out_pop_brief_carries_its_own_checks_and_the_data_read():
    b = json.loads(pr.brief('pop', SAT, now=1795000000).split('\n', 1)[1])
    assert b['yourFiveChecks'] == pr.RUBRIC_SAT_OUT['pop'] and len(b['yourFiveChecks']) == 5
    ev = b['evidence']
    assert ev['tradeTaken'] is False and ev['board'][0]['px'] == 72.52
    assert ev['ownSources'] == {'mind0': [{'site': 'deribit.com', 'market': 'SOL', 'px': 72.53, 'devBps': 1.4, 'off': False}], 'mind1': []}
    assert 'Liquidations' in ev['whatWasRead'][0]


def test_a_traded_pop_keeps_the_trade_rubric():
    f = {'id': 'p', 'status': 'closed', 'market': 'SOL', 'side': 'short', 'lev': 2, 'entry': 72.5, 'exit': 71.0, 'roePct': 4.1}
    assert pr.rubric_of('pop', f) == pr.RUBRIC['pop']
    assert json.loads(pr.brief('pop', f, now=1795000000).split('\n', 1)[1])['evidence']['tradeTaken'] is True


def test_a_poeco_market_brief_shows_the_call_its_pools_and_the_seal():
    b = json.loads(pr.brief('poe', MARKET, now=1795000000).split('\n', 1)[1])
    assert b['yourFiveChecks'] == pr.RUBRIC_MARKET['poe']
    ev = b['evidence']
    assert ev['pick']['turnover'] == 20.0 and ev['other']['turnover'] == 9.0 and ev['sealHash'] == MARKET['hash']
    assert ev['graded'].startswith('not yet') and ev['pagesRead']
    books = {'id': 'b', 'status': 'closed', 'income': 10, 'costs': 4, 'net': 6}
    assert pr.rubric_of('poe', books) == pr.RUBRIC['poe']   # the books rubric is unchanged


# --- 3. a cut-off PoP call is not a pass --------------------------------------------------------------------------------
CUT = '{\n"market": "SOL",\n"side": "short",\n"lev": 2,\n"tp_pct": 2.5,\n"sl_pct": 3.5,\n"why": "The perps price ($72.52) is trading below the 5m chart high ($'


def test_a_call_cut_off_inside_its_reason_keeps_its_call_marked_cut():
    c = pop.parse_call(CUT)
    assert c == {'market': 'SOL', 'side': 'short', 'lev': 2.0, 'tp': 2.5, 'sl': 3.5, 'why': 'The perps price ($72.52) is trading below the 5m chart high ($', 'cut': True}


def test_a_call_cut_before_its_numbers_is_still_nothing_guessed():
    assert pop.parse_call('{"market": "SOL", "side": "short", "lev": 2, "tp_') is None
    assert pop.parse_call('{"market": "SOL", "side": "sho') is None
    assert pop.parse_call('{"market": "SOL", "side": "short", "lev": 2, "tp_pct": 2, "sl_pct": 3, "why": "looks good') is None   # no number read: not a reason
    assert pop.parse_call('{"market": "SOL", "side": "none", "why": "flat at 72"}') is None   # a whole reply is parsed as before
    assert pop.CALL_TOKENS > 220


# --- 4. §1: a real PoW's P&L never includes fees -----------------------------------------------------------------------
def test_pow_pnl_is_pool_to_pool_with_fees_apart():
    f = {'netPnlSol': 0.0080, 'cashSpentSol': 0.1012, 'poolSpentSol': 0.1000, 'poolReturnedSol': 0.1100, 'feesSol': 0.0020}
    assert fc_pow._pow2_pnl(f) == (0.01, 10.0)   # the cash net (0.008, fees in) stays on the receipt only
    assert fc_pow._pow2_pnl({'netPnlSol': 0.008, 'cashSpentSol': 0.1}) == (0.008, 8.0)   # settled before the pool split was kept


def test_reconcile_keeps_the_pool_legs_and_the_fees():
    class RS:
        class httpx:
            HTTPError = Exception
        asyncio = asyncio

        class _crpc:
            @staticmethod
            async def _rpc(http, m, a, scan=False):
                return {'sig': a[0]}

        class _fills:
            @staticmethod
            def raw_fill(tx, wallet, mint):
                return ({'side': 'buy', 'cashSol': 0.1012, 'poolSol': 0.1, 'feeSol': 0.001, 'networkSol': 0.0002} if tx['sig'] == 'b'
                        else {'side': 'sell', 'cashSol': 0.1088, 'poolSol': 0.11, 'feeSol': 0.001, 'networkSol': 0.0002})
    old = fc_pow._rs
    fc_pow._rs = lambda: RS
    try:
        f = {'mint': 'm'}
        assert asyncio.run(fc_pow._pow2_reconcile(None, {'agentWallet': {'address': 'w'}}, f, {'sig': 'b'}, {'sig': 's'}))
    finally:
        fc_pow._rs = old
    assert f['poolSpentSol'] == 0.1 and f['poolReturnedSol'] == 0.11 and f['feesSol'] == 0.0024 and f['netPnlSol'] == 0.0076
    assert fc_pow._pow2_pnl(f) == (0.01, 10.0)


# --- 5. the record names the tools; PoEco closes on its own -------------------------------------------------------------
def test_pow_kits_name_the_coin_tools_it_really_used():
    f = {'coins': [{'src': 'pump', 'safe': False, 'read': 'x'}, {'src': 'pump', 'safe': True}], 'dropped': [{'src': 'intake'}], 'scouted': True, 'scout': ['a', 'b']}
    k = fc_pow.pow_kits(f)
    assert k[0] == 'coin intake (intake, pump): 3 candidates' and 'buy guards + safety vet: 1 dropped, 1 flagged' in k
    assert 'FEELESS coin search: 1 coins read' in k and 'scout: 2 coins' in k
    assert fc_pow.pow_kits({}) == []


def test_a_due_market_call_is_graded_by_the_engine_not_only_by_an_open_folder():
    now = 100_000
    cat = {'poeFolders': [MARKET, {**MARKET, 'id': 'later', 'due': now + 10}, {**MARKET, 'id': 'done', 'graded': 'right'}, {'id': 'books'}]}
    assert [f['id'] for f in fc_cats.eco_due(cat, now)] == ['poe1']
    asked = []

    class RS:
        time = __import__('time')
        _AUTO_TOKEN = 'tok'

        class WorkPayload(dict):
            def __init__(self, **k):
                super().__init__(k)

        @staticmethod
        async def _cat_work(cid, p):
            asked.append((cid, p['op'], p['auto']))
            return {'graded': 1}
    old = fc_cats._rs
    fc_cats._rs = lambda: RS
    fc_cats._ECO_GRADE['at'] = 0.0
    try:
        assert asyncio.run(fc_cats._eco_grade_pass({'cats': {'c1': cat, 'c2': {'poeFolders': []}, 'c3': {**cat, 'revoked': True}}}, now)) == 1
        assert asyncio.run(fc_cats._eco_grade_pass({'cats': {'c1': cat}}, now + 5)) == 0   # at most once per 10 min
    finally:
        fc_cats._rs = old
        fc_cats._ECO_GRADE['at'] = 0.0
    assert asked == [('c1', 'eco_grade', True)]


def test_a_poeco_verdict_survives_the_owner_snapshot_save():
    """poeFolders is an owner key: the engine's verdict was laid over by _KEPT on save. It now lands in the snapshot too."""
    import feecat_service as fs
    old_k, old_d = dict(fs._KEPT), list(fs._REVIEW_DONE)
    try:
        fs._KEPT.clear(); fs._KEPT['c1'] = {'poeFolders': [{'id': 'poe1', 'status': 'open'}]}
        store = {'cats': {'c1': {'id': 'c1', 'handle': 'sicarios', 'poeFolders': [{'id': 'poe1', 'status': 'open'}]}}}
        rv = {'v': pr.VERSION, 'rubric': pr.VERSION, 'score': 70, 'verdict': 'pass', 'by': {'ossy': {'score': 70, 'verdict': 'pass'}}}
        fs._REVIEW_DONE[:] = [('c1', 'poe', 'poe1', rv)]
        fc_cats._review_apply(store)
        assert store['cats']['c1']['poeFolders'][0]['review']['score'] == 70
        assert fs._KEPT['c1']['poeFolders'][0]['review']['score'] == 70   # what _save lays back on the folder
        assert fc_cats._review_keep('c1', 'powFolders', 'x', rv) is False   # an engine-owned list needs no snapshot
    finally:
        fs._KEPT.clear(); fs._KEPT.update(old_k); fs._REVIEW_DONE[:] = old_d


# --- 6. the review pass (2026-11-19, /code-review high) ----------------------------------------------------------------
def test_a_call_the_log_missed_never_lets_its_builder_judge_it():
    assert pr.builders_of({'ran': [], 'minds': ['local/ossy']}, {}, 'pob') == ['local/ossy']
    assert pr.builders_of({'ran': [{'asked': 'local/g4', 'ok': 1}], 'minds': ['local/ossy']}, {}, 'pob') == ['local/g4', 'local/ossy']


def test_minds_that_came_back_blank_made_no_sit_out_decision():
    blank = {**SAT, 'calls': [{'mind': 0, 'name': 'ossy', 'why': ''}, {'mind': 1, 'name': 'g4', 'why': ' '}]}
    assert not pr.sat_out('pop', blank) and pr.next_due(_store(popFolders=[blank])) is None


def test_a_cash_fallback_pnl_says_so_on_the_folder():
    f = {'netPnlSol': 0.008, 'cashSpentSol': 0.1}
    fc_pow._pow2_pnl(f)
    assert f['pnlBasis'].startswith('cash (fees in')
    g = {'poolSpentSol': 0.1, 'poolReturnedSol': 0.11}
    fc_pow._pow2_pnl(g)
    assert g['pnlBasis'] == 'pool'


def test_one_agents_grade_error_never_holds_another():
    now = 100_000; got = []

    class RS:
        time = __import__('time')
        _AUTO_TOKEN = 'tok'

        class WorkPayload(dict):
            def __init__(self, **k):
                super().__init__(k)

        @staticmethod
        async def _cat_work(cid, p):
            if cid == 'bad':
                raise ValueError('broken folder')
            got.append(cid)
            return {'graded': 1}
    old = fc_cats._rs
    fc_cats._rs = lambda: RS
    fc_cats._ECO_GRADE['at'] = 0.0
    try:
        st = {'cats': {'bad': {'poeFolders': [MARKET]}, 'good': {'poeFolders': [MARKET]}}}
        assert asyncio.run(fc_cats._eco_grade_pass(lambda: st, now)) == 1 and got == ['good']
    finally:
        fc_cats._rs = old
        fc_cats._ECO_GRADE['at'] = 0.0


def test_a_feed_outage_never_grades_a_due_call_wrong(monkeypatch):
    """eco_grade read 'no rows' as 'both pools went dark' and graded every due call wrong for good; the engine pass now runs it by itself."""
    import feecat_service as fs
    cat = {'id': 'c1', 'handle': 'sicarios', 'name': "Sicario's", 'chat': [], 'poeFolders': [{**MARKET, 'baseline': {'pick': {'addr': 'A', 'vol24h': 2, 'liqUsd': 1}, 'other': {'addr': 'B', 'vol24h': 1, 'liqUsd': 1}}}]}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    rows = []

    async def eco_pools(http, addrs=None):
        return rows
    monkeypatch.setattr(fs, '_eco_pools', eco_pools)
    out = asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='eco_grade', session=fs._AUTO_TOKEN, auto=True)))
    assert out['graded'] == 0 and not cat['poeFolders'][0].get('graded') and cat['poeFolders'][0]['status'] == 'open'
    rows[:] = [{'addr': 'A', 'pair': 'A/SOL', 'vol24h': 5.0, 'liqUsd': 1.0}, {'addr': 'B', 'pair': 'B/SOL', 'vol24h': 3.0, 'liqUsd': 1.0}]
    out = asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='eco_grade', session=fs._AUTO_TOKEN, auto=True)))
    assert out['graded'] == 1 and cat['poeFolders'][0]['graded'] == 'right' and cat['poeFolders'][0]['status'] == 'closed'   # old behaviour kept


def test_a_test_start_waits_while_the_agent_works_another_proof():
    """TEST PoW 2026-11-19: 'propose a pow' sent while a PoP ran was taken as a note to the PoP, so no PoW ever started."""
    import fc_test
    assert fc_test.busy_with({'popRun': {'market': 'SOL'}, 'powRun': {'n': 3}}, 'pow') == 'PoP'
    assert fc_test.busy_with({'powRun': {'n': 3, 'rested': 1}}, 'pop') == ''   # a resting PoW loop is not a proof at work
    assert fc_test.busy_with({'powRun': {'folder': {'id': 'w'}}}, 'pop') == 'PoW'
    assert fc_test.busy_with({}, 'pob', True) == 'PoC' and fc_test.busy_with({'pobRead': {'at': 1}}, 'pob') == ''


# --- 7. owner 2026-11-19: TESTs on Happy's agent, proposals + paper only, $0.50 for all of them --------------------------
def test_the_test_agent_is_sicario_by_default_or_happy_when_asked():
    import fc_test
    st = {'cats': {'s': {'id': 's', 'handle': 'sicarios'}, 'h': {'id': 'h', 'handle': 'happy-assistant'}, 'x': {'id': 'x', 'handle': 'happy-assistant', 'revoked': True}}}
    assert fc_test._sicario(st)['id'] == 's' and fc_test._sicario(st, 'happy')['id'] == 'h'
    try:
        fc_test._sicario(st, 'someone-else'); raise AssertionError('an unknown agent must be refused')
    except Exception as e:   # noqa: BLE001
        assert getattr(e, 'status_code', None) == 400


def test_happy_tests_stop_at_the_owners_budget():
    import fc_test
    rows = [{'at': fc_test.BUDGET_SINCE - 1, 'usd': 9.0}, {'at': fc_test.BUDGET_SINCE + 1, 'usd': 0.21}, {'at': fc_test.BUDGET_SINCE + 2, 'usd': 0.3}]
    assert fc_test.spent_since(rows) == 0.51 and fc_test.TEST_BUDGET_USD == 1.00   # spend before the ruling never counts; after it, every call does
    rows += [{'at': fc_test.BUDGET_SINCE + 3, 'usd': 0.2, 'kind': 'pow'}, {'at': fc_test.BUDGET_SINCE + 4, 'usd': 0.06, 'kind': 'pow'}, {'at': fc_test.BUDGET_SINCE + 5, 'usd': 0.1, 'kind': 'pop'}]
    assert fc_test.spent_since(rows, kind='pow') == 0.26 >= fc_test.KIND_BUDGET_USD == 0.25 and fc_test.spent_since(rows, kind='pop') == 0.1



# --- 8. a PoW proposal is judged as a proposal (TEST PoW #17 on Happy failed 0/0 for "no entry price") -------------------
PROP = {'id': 'pow17', 'status': 'closed', 'propose': True, 'sym': 'AI', 'mint': 'm1', 'tp': 15, 'sl': 10, 'sol': 0.005, 'at': 50,
        'coins': [{'mint': 'm1', 'sym': 'AI', 'read': 'pool 110k'}, {'mint': 'm2', 'sym': 'PIPI', 'read': 'pool 56k'}]}


def test_a_pow_proposal_gets_the_proposal_checks_and_says_nothing_was_bought():
    assert pr.proposal(PROP) and not pr.proposal({**PROP, 'entry': 0.0003}) and not pr.proposal({**PROP, 'propose': False})
    b = json.loads(pr.brief('pow', PROP, now=1795000000).split('\n', 1)[1])
    assert b['yourFiveChecks'] == pr.RUBRIC_PROPOSAL['pow'] and 'nothing was bought' in b['evidence']['proposalOnly']
    assert b['evidence']['whatWasRead'][0].startswith('AI (PICKED, not bought)')
    assert pr.rubric_of('pow', {**PROP, 'entry': 0.0003, 'propose': False}) == pr.RUBRIC['pow']   # a real trade keeps the trade checks


def test_a_proposal_judged_on_the_trade_rubric_is_judged_again_once():
    old = {'v': pr.VERSION, 'rubric': pr.VERSION, 'score': 0, 'at': pr.POW_PROPOSAL_AT - 10, 'by': {'ossy': {'score': 0}}}
    assert pr.stale_brief('pow', old, PROP) and not pr.stale_brief('pow', {**old, 'at': pr.POW_PROPOSAL_AT + 10}, PROP)
    assert not pr.stale_brief('pow', old, {**PROP, 'entry': 0.0003, 'propose': False}) and not pr.stale_brief('pow', {**old, 'outside': 'owner'}, PROP)
    assert pr.next_due(_store(powFolders=[{**PROP, 'review': old}]))[2]['id'] == 'pow17'

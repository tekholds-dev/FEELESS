"""Slice 28 carry-over from Slice 27 (TEST #72): a TEST build spent $0.54 of its $0.25 because the cap was checked only at the door, and it
filed a page whose CSS never closed (the body was pasted inside a `.hero{` rule), so it rendered blank. Network faked."""
import asyncio
import time

import feecat_service as rs
import agent_features as feat
import fc_desk
import fc_test

HAPPY = {'id': 'cap-test-happy', 'handle': 'happy-assistant', 'name': 'Happy'}
PRICED = {'id': 'google/gemini-4-carbon', 'inUsd': 2.0, 'outUsd': 8.0}   # $ per 1M tokens: 12,000 reply tokens ≈ $0.10, like #72's calls
CTX = {'kind': 'pos', 'ref': 'wcap', 'minds': [PRICED['id']]}
MSGS = [{'role': 'user', 'content': 'x' * 3000}]

BLANK_72 = ('<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Turnover</title><style>\n'
            ':root{--bg:#000}\nbody{margin:0}\n.hero{position:relative;border-bottom:1px solid var(--line)">\n'
            '<div class="kicker">Solana pool turnover</div><h1>How fast does the money turn over?</h1>'
            '<p>Turnover is 24h volume divided by liquidity, read from the deepest pools.</p></div>\n</body>\n</html>')
GOOD = ('<!DOCTYPE html><html><head><title>Turnover</title><style>body{margin:0}</style></head><body><main><h1>Pool turnover</h1>'
        '<p>Turnover is 24h volume divided by liquidity. One means the pool changed hands once today.</p></main></body></html>')


def _claim(monkeypatch, rows_usd=0.0):
    monkeypatch.setitem(rs._TEST_ON, (HAPPY['id'], 'pos'), {'at': time.time(), 'by': 'Claude', 'run': 'r1'})
    monkeypatch.setitem(rs._MODELS, 'rows', {'models': [PRICED]})
    rows = [{'cat': HAPPY['id'], 'kind': 'pos', 'at': fc_test.BUDGET_SINCE + 10, 'usd': rows_usd, 'asked': PRICED['id']}] if rows_usd else []
    monkeypatch.setattr(rs, '_calls_of', lambda _cid, *a, **k: rows)
    return rs._TEST_ON[(HAPPY['id'], 'pos')]


def test_a_test_build_stops_at_its_cap_before_the_call_that_would_pass_it(monkeypatch):
    claim = _claim(monkeypatch)
    sent = []

    async def routes(cat, model, messages, own_key=None, effort=None, max_tokens=None):
        sent.append(max_tokens)
        return '<html>page</html>', fc_test.call_worst(PRICED, messages, max_tokens), 'openrouter'
    monkeypatch.setattr(rs, '_think_routes', routes)
    monkeypatch.setattr(rs, '_mind_call', lambda *a, **k: None)
    tok = rs._CALL_CTX.set(CTX)
    try:
        spent, refused = 0.0, None
        for _ in range(6):   # #72 made 10 calls like this one; the cap must stop it
            try:
                _t, usd, _v = asyncio.run(rs._think(HAPPY, PRICED['id'], MSGS, max_tokens=12000))
                spent += usd
            except rs._sg.OverCap as e:
                refused = str(e); break
    finally:
        rs._CALL_CTX.reset(tok)
    assert refused and 'TEST cap' in refused and 'before it cost anything' in refused
    assert spent <= fc_test.KIND_BUDGET_USD + 1e-9                   # never past $0.25 for the kind
    assert sent[-1] < 12000                                           # the last call that ran was shortened to fit what was left
    assert claim['used'] == spent and not claim['held']               # every hold let go, every real $ counted


def test_the_cap_counts_what_was_spent_before_this_test_and_refuses_at_zero(monkeypatch):
    _claim(monkeypatch, rows_usd=0.25)                                # this kind already spent its $0.25
    try:
        fc_test.cap_take(HAPPY, CTX, PRICED['id'], MSGS, 2000)
        assert False, 'should refuse'
    except rs._sg.OverCap as e:
        assert '$0.000 is left' in str(e)


def test_calls_in_flight_hold_their_worst_case_so_two_minds_cannot_both_spend_the_last_cents(monkeypatch):
    claim = _claim(monkeypatch, rows_usd=0.15)                        # $0.10 left
    a = fc_test.cap_take(HAPPY, CTX, PRICED['id'], MSGS, 9000)         # holds ~$0.075
    b = fc_test.cap_take(HAPPY, CTX, PRICED['id'], MSGS, 9000)         # the second mind only gets what is left
    assert b[1] < 9000 and sum(claim['held'].values()) <= 0.10 + 1e-9
    try:
        fc_test.cap_take(HAPPY, CTX, PRICED['id'], MSGS, 9000)         # a third: nothing left to hold
        assert False, 'should refuse'
    except rs._sg.OverCap:
        pass
    fc_test.cap_done(HAPPY, CTX, a, 0.01); fc_test.cap_done(HAPPY, CTX, b, 0.0)   # they really cost $0.01
    assert fc_test.cap_take(HAPPY, CTX, PRICED['id'], MSGS, 9000)[1] == 9000      # room again, full reply
    assert round(claim['used'], 4) == 0.01


def test_no_cap_outside_a_happy_test_and_never_on_free_local_minds(monkeypatch):
    _claim(monkeypatch, rows_usd=0.25)
    assert fc_test.cap_take(HAPPY, CTX, 'local/ossy', MSGS, 2000) is None                         # the owner's own LM Studio is $0
    assert fc_test.cap_take({**HAPPY, 'handle': 'sicarios'}, CTX, PRICED['id'], MSGS, 2000) is None
    assert fc_test.cap_take(HAPPY, {'kind': 'pob'}, PRICED['id'], MSGS, 2000) is None             # no TEST of that kind is running
    monkeypatch.delitem(rs._TEST_ON, (HAPPY['id'], 'pos'))
    assert fc_test.cap_take(HAPPY, CTX, PRICED['id'], MSGS, 2000) is None                          # a real (not TEST) build is the owner's own day cap's job


def test_a_page_whose_css_never_closes_is_blank():
    assert 'CSS never closes' in feat.page_blank(BLANK_72)
    assert feat.page_complete(BLANK_72)                               # the old check passed it: that is how #72 filed
    assert feat.page_blank('') and feat.page_blank('<html><body>   </body></html>')
    assert feat.page_blank('<html><body><script>let a = 1;') .startswith('a script never closes')
    assert feat.page_blank(GOOD) == ''
    assert feat.page_blank('<html><body><canvas id="c"></canvas><script>draw()</script></body></html>') == ''   # a drawn page is not blank
    assert feat.page_blank('<html><body><script>var s="<script>";</script><h1>A heading that is long enough</h1><p>and enough words here.</p></body></html>') == ''
    assert feat.page_blank('<html><body><header>THE TRENCH</header><div data-feeless-model="tombstone_01"></div></body></html>') == ''   # his own 3D piece draws it (Slice 2 studio)


def test_a_blank_page_is_taken_back_before_it_files():
    doc = {'id': 'wcap', 'versions': [{'html': GOOD, 'by': 'Mind A', 'at': 1}, {'html': BLANK_72, 'by': 'Mind B', 'at': 2}], 'messages': []}
    asyncio.run(fc_desk._ps_after('cap-test-happy', 'wcap', doc, 1))
    assert len(doc['versions']) == 1 and doc['versions'][0]['html'] == GOOD     # the last good page is safe, nothing new to file
    assert doc['refused'][-1]['blank'] and 'show nothing' in doc['messages'][-1]['text']

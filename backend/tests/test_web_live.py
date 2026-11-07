"""🔥 The webs show folders, features and working agents. Never a site's name to the public, never a private agent."""
import agent_refs as ar


def test_the_sources_web_names_no_site():
    w = ar.sources_web(); text = str({k: w[k] for k in ('folders', 'features', 'dots')}).lower()
    assert w['folders'] and w['features'] and len(w['dots']) >= 20
    for site in ('dexscreener', 'espn', 'polymarket', 'github', 'wikipedia', '.com', 'http'):
        assert site not in text
    assert sum(f['n'] for f in w['folders']) == len(w['dots']) == sum(f['n'] for f in w['features'])


def test_a_private_agent_stays_off_the_public_web():
    import feecat_service as fs
    store = {'cats': {'s': {'id': 's', 'name': "Sicario's", 'handle': 'sicarios', 'powRun': {'n': 1, 'folder': {'id': 'f'}}}, 'h': {'id': 'h', 'name': 'Happy', 'popRun': {'n': 2}}, 'r': {'id': 'r', 'name': 'Rested', 'powRun': {'rested': 1}}}}
    pub = fs._web_live_rows(store, 0.0)
    assert [r['agent'] for r in pub] == ['Happy'] and pub[0]['folder'] == 'Perps'
    assert {r['agent'] for r in fs._web_live_rows(store, 0.0, True)} == {"Sicario's", 'Happy'}


def test_a_mind_on_a_known_site_lands_on_its_feature_and_a_stranger_site_is_never_named():
    import feecat_service as fs
    store = {'cats': {'h': {'id': 'h', 'name': 'Happy'}}}
    fs._WORK['h'] = {'task': {'windows': [{'i': 0, 'status': 'running', 'url': 'https://dexscreener.com/solana', 'goal': 'read'}, {'i': 1, 'status': 'running', 'url': 'https://secret.example/x', 'goal': 'read'}, {'i': 2, 'status': 'idle', 'url': 'https://x.com'}]}}
    rows = fs._web_live_rows(store, 0.0)
    fs._WORK.pop('h')
    assert len(rows) == 2 and rows[0]['feature'].startswith('Trades/') and rows[1]['host'] is None and rows[1]['feature'] is None


def test_a_proof_recalls_wins_first_titles_only_and_no_match_says_nothing(tmp_path):
    import collective_stash as st
    st.put(tmp_path, 'k1', 'Picks', 'espn.com', 'tagA', 'lost', 'Lakers parlay', b'{"secret":"inside"}', 'json', 100.0)
    st.put(tmp_path, 'k2', 'Picks', 'espn.com', 'tagB', 'won', 'Lakers at home', b'{"secret":"inside"}', 'json', 200.0)
    st.put(tmp_path, 'k3', 'Trades', 'x.com', 'tagB', 'won', 'Lakers coin', b'{}', 'json', 300.0)
    rows = st.related(tmp_path, ['lakers'], 'Picks')
    assert [r['outcome'] for r in rows] == ['won', 'lost'] and 'secret' not in str(rows)
    line = ar.recall_line(rows, st.agent_tag('tagA'))
    assert 'the Collective: WON "Lakers at home"' in line and 'your own: LOST "Lakers parlay"' in line
    assert st.related(tmp_path, ['nothing'], 'Picks') == [] and ar.recall_line([]) == ''


def test_a_slow_page_build_is_not_called_dead_and_a_lost_one_is():
    import feecat_service as fs
    class T:
        def __init__(self, d): self.d = d
        def done(self): return self.d
    fs._WS_LIVE[('c', 'w')] = T(False)
    assert not fs._ws_dead('c', 'w', 0, 1000) and fs._ws_dead('c', 'w', 0, fs.WS_MAX_S + 1)
    fs._WS_LIVE[('c', 'w')] = T(True)
    assert fs._ws_dead('c', 'w', 0, fs.WS_ORPHAN_S + 1) and not fs._ws_dead('c', 'w', 0, 1)
    fs._WS_LIVE.clear()
    assert fs._ws_dead('c', 'w', 0, 100)


def test_stop_ends_what_is_writing_and_what_is_queued_and_a_later_ask_still_runs():
    import asyncio, time
    import feecat_service as fs
    calls = []
    async def slow(model, messages, tokens):
        calls.append(model); await asyncio.sleep(30); return 'late', 0.0
    async def quick(model, messages, tokens):
        return 'ok', 0.0
    real = fs._lm_call_one; real_cool = fs._mac_cool
    async def go():
        async def cool(step=5.0):
            return 0.0
        fs._mac_cool = cool; fs._LM_GATE.clear(); fs._LM_STOP['at'] = 0.0; fs._lm_call_one = slow
        a = asyncio.create_task(fs._lm_call('local/ossy', [], 10)); await asyncio.sleep(0.01)
        b = asyncio.create_task(fs._lm_call('local/ossy', [], 10)); await asyncio.sleep(0.01)
        assert fs.lm_stop(time.time()) == 1
        assert await a == ('', 0.0) and await b == ('', 0.0) and calls == ['local/ossy']
        fs._lm_call_one = quick; await asyncio.sleep(0.01)
        fs._LM_STOP['at'] = 0.0
        assert await fs._lm_call('local/ossy', [], 10) == ('ok', 0.0)
    try:
        asyncio.run(go())
    finally:
        fs._lm_call_one = real; fs._mac_cool = real_cool; fs._LM_GATE.clear(); fs._LM_STOP['at'] = 0.0


def test_a_page_never_goes_to_a_local_model():
    import asyncio
    import feecat_service as fs
    seen = []
    async def ask(cat, model, sys_, user_, tokens):
        seen.append(model); return '', 0.0, False
    real = fs._ws_ask; fs._ws_ask = ask
    try:
        asyncio.run(fs._ws_page({}, 'local/ossy', 's', 'u', 10))
        asyncio.run(fs._ws_page({}, 'x/other', 's', 'u', 10))
    finally:
        fs._ws_ask = real
    assert seen == ['local/ossy', 'x/other']   # owner 2026-11-07: OSSY and G4 write their own pages, no paid stand-in


def test_asked_only_is_a_switch_on_the_env():
    import ai_router as air
    assert air.asked_only({'LM_ASKED_ONLY': 'true'}) and not air.asked_only({})
    src = open(air.__file__).read()
    assert 'if asked_only(env) and not own and not only:' in src


def test_a_card_link_takes_only_a_real_address_never_a_card_number():
    import pytest
    import feecat_service as fs
    cat = {}; good = 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P'
    assert fs.card_link(cat, 'solcard', good, 5.0) == {'provider': 'solcard', 'address': good, 'at': 5}
    for provider, bad in (('solcard', '4111111111111111'), ('solcard', ''), ('nope', good)):
        with pytest.raises(ValueError):
            fs.card_link({}, provider, bad, 5.0)


def test_a_page_in_progress_shows_its_parts_and_cost():
    import asyncio
    import feecat_service as fs
    parts = iter([('<!doctype html><html><body>half', 0.01, False), ('rest</body></html>', 0.02, False)])
    async def ask(*a, **k):
        return next(parts)
    seen = []; real = fs._ws_ask; fs._ws_ask = ask
    try:
        raw, usd, _ = asyncio.run(fs._ws_page({}, 'x/m', 's', 'u', 10, on_part=lambda r, u: seen.append((r, u))))
    finally:
        fs._ws_ask = real
    assert seen[0][0].endswith('half') and seen[0][1] == 0.01
    assert seen[-1][0] == raw and raw.endswith('</html>') and abs(seen[-1][1] - 0.03) < 1e-9 and abs(usd - 0.03) < 1e-9

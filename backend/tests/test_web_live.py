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

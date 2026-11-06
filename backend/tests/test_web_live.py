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

"""🔎 Site scan: what it files is only what the site wrote, and a wall is reported as a wall. Fake network and fake browser; nothing reaches a real site."""
import asyncio
import json
import pytest
import site_scan as ss

TERMS = ('You must keep your wallet secure at all times while using this site. You may not use automated bots or scrapers to access the service. '
         'There is a 1% fee on every trade made here on the platform. Withdrawals of USDC reach your wallet within one hour of the request. '
         'Residents of restricted jurisdictions are not permitted to use the service. You could lose all of your funds at your own risk here. ') * 3
HOME = '<title>Acme</title><body>' + 'Welcome to the Acme market where people trade together every day. ' * 8 + '<a href="/tos">Terms</a><a href="https://evil.example/terms">Terms of evil</a><a href="/feed">Feed</a></body>'


class R:
    def __init__(self, code, text='', loc=None):
        self.status_code, self.text, self.headers = code, text, ({'location': loc} if loc else {})


class Http:
    def __init__(self, pages):
        self.pages, self.asked = pages, []

    async def get(self, url, **_):
        self.asked.append(url)
        return self.pages.get(url) or R(404, 'not found')


def test_clean_url_blocks_private_and_junk():
    assert ss.clean_url('pump.fun') == 'https://pump.fun'
    for bad in ('', 'http://localhost:5001', 'http://127.0.0.1', 'https://169.254.169.254/x', 'not a site', 'nodots'):
        with pytest.raises(ValueError):
            ss.clean_url(bad)


def test_read_only_its_own_pages_and_every_redirect_is_checked():
    h = Http({'https://acme.io': R(200, HOME), 'https://acme.io/tos': R(302, '', 'http://localhost/steal')})
    pages = asyncio.run(ss.read_fetch(h, 'https://acme.io', 'acme.io'))
    assert not any('evil.example' in u for u in h.asked) and not any('localhost' in u for u in h.asked)
    assert not any('/feed' in u for u in h.asked)   # the word "feed" is not a fee page
    assert not next(p for p in pages if p['kind'] == 'terms')['ok']


def test_manual_is_filed_from_its_own_sentences():
    h = Http({'https://acme.io': R(200, HOME), 'https://acme.io/tos': R(200, f'<title>Terms</title>{TERMS}')})
    pages = asyncio.run(ss.read_fetch(h, 'https://acme.io', 'acme.io'))
    m = ss.build('acme.io', 'pow', 'https://acme.io', pages, 100.0)
    assert m['state'] == 'caution' and m['botSay'] == 'banned' and m['terms']
    assert m['do'] and m['dont'] and m['withdraw'] and m['fees'] and m['regions'] and m['risk']
    assert all(r['q'] in TERMS for k in ss.SHELVES for r in m[k])
    assert m['withdraw'][0]['src'] == 'https://acme.io/tos'
    json.dumps(m)


def test_wall_is_reported_not_passed():
    h = Http({'https://walled.io': R(403, '<title>Just a moment...</title>Enable JavaScript and cookies to continue')})
    pages = asyncio.run(ss.read_fetch(h, 'https://walled.io', 'walled.io'))
    m = ss.build('walled.io', 'pow', 'https://walled.io', pages, 1.0, wall=ss.wall_of(pages))
    assert m['state'] == 'unread' and 'bot check' in m['wall'] and ss.needs_browser(pages)
    assert ss.commands({'walled.io': m}, {'walled.io'}) == []


class Page:
    url = title = None

    def __init__(self, texts):
        self.texts, self.opened = texts, []

    async def goto(self, u):
        self.url, self.title = u, 'T'; self.opened.append(u)
        return ''

    async def full_text(self, n):
        return self.texts.get(self.url, '')[:n]

    async def shot(self):
        return b'jpg'

    async def links(self):
        return [('https://w.io/terms', 'Terms'), ('https://other.com/terms', 'Terms')]


def test_browser_read_follows_only_its_own_links_and_stops_at_a_wall():
    p = Page({'https://w.io': 'Home page words ' * 30, 'https://w.io/terms': TERMS})
    pages, shot = asyncio.run(ss.read_browser(p, 'https://w.io', 'w.io'))
    assert shot == b'jpg' and p.opened == ['https://w.io', 'https://w.io/terms'] and all(x['via'] == 'browser' for x in pages)
    stuck = Page({'https://w.io': 'Just a moment... checking your browser ' * 10})
    pages, _ = asyncio.run(ss.read_browser(stuck, 'https://w.io', 'w.io'))
    assert stuck.opened == ['https://w.io'] and not pages[0]['ok'] and pages[0]['wall']


def test_model_can_only_reword_a_real_sentence():
    m = ss.build('a.io', 'pow', 'https://a.io', [{'kind': 'terms', 'url': 'https://a.io/t', 'title': '', 'text': TERMS, 'ok': True}], 1.0)
    lines, index = ss.polish_prompt(m)
    q = index[0]['q']; shelf = next(k for k in ('do', 'dont', 'withdraw', 'fees', 'risk') if any(r['q'] == q for r in m[k]))
    out = ss.apply_polish(m, json.dumps({shelf: [{'i': 0, 't': 'Keep it plain'}, {'i': 999, 't': 'A rule the site never wrote'}]}), index, 'x')
    assert [r['t'] for r in out[shelf]] == ['Keep it plain'] and out[shelf][0]['q'] == q and out['model'] == 'x'
    before = json.dumps(m)
    assert json.dumps(ss.apply_polish(m, 'no json here', index)) == before


def test_command_needs_a_manual_and_a_sign_in():
    manuals = {'pump.fun': {'slug': 'pump', 'state': 'read', 'kinds': ['pow'], 'url': 'https://pump.fun', 'site': 'pump.fun'}}
    assert ss.command('file a pump pow', manuals, {'pump.fun'}) == {'site': 'pump.fun', 'kind': 'pow'}
    assert ss.command('File a pump.fun PoW', manuals, {'pump.fun'})['site'] == 'pump.fun'
    assert 'not signed in' in ss.command('file a pump pow', manuals, set())['why']
    assert 'no manual' in ss.command('file a axiom pow', manuals, {'pump.fun'})['why']
    assert ss.command('file a pow', manuals, set()) is None and ss.command('file a perp', manuals, set()) is None and ss.command('file a bid', manuals, set()) is None
    assert ss.commands(manuals, {'pump.fun'})[0][0] == 'file a pump pow' and ss.commands(manuals, set()) == []


def test_note_says_read_only_and_passes_rules_as_data():
    n = ss.note_for({'url': 'https://pump.fun', 'dont': [{'t': 'No bots'}]}, 'pow')
    assert 'Never trade, deposit, withdraw' in n and 'No bots' in n


# The service's doors, on fakes
@pytest.fixture
def fs(monkeypatch):
    import feecat_service as fs
    fs._WORK.clear(); fs._POW_WANT.clear(); fs._POP_WANT.clear(); fs._POB_WANT.clear(); fs._SCAN_DONE.clear(); fs._SCAN_BUSY.clear()
    return fs


def _cat(**kw):
    return {'id': 'c1', 'chat': [], 'brainsCfg': {'brains': ['m/a', 'm/b'], 'credit': 0}, 'siteManuals': {'pump.fun': {'site': 'pump.fun', 'slug': 'pump', 'url': 'https://pump.fun', 'state': 'read', 'kinds': ['pow', 'pob', 'pop'], 'dont': []}}, 'siteSessions': {'pump.fun': {'ctx': 'x'}}, **kw}


def test_site_proof_start_steers_only_that_kind(fs):
    cat = _cat(); ok, say = fs._site_proof_start(cat, 'c1', 'pump.fun', 'pob')
    assert ok and 'Free chips' in say and fs._POB_WANT['c1'] == 'start'
    assert fs._proof_hosts(cat, 'pob') == ['pump.fun'] and fs._proof_hosts(cat, 'pow') == []
    assert 'Never trade' in fs._site_note(cat, 'pob') and fs._site_note(cat, 'pow') == ''
    cat['siteSessions'] = {}   # signed out: it stops going there
    assert fs._proof_hosts(cat, 'pob') == []


def test_a_finished_scan_is_filed_with_its_snapshot_and_no_model_when_no_credit(fs, tmp_path, monkeypatch):
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path)
    cat = _cat(siteManuals={}); store = {'cats': {'c1': cat}}; fs._SCAN_BUSY['c1'] = 'a.io'
    fs._SCAN_DONE.append({'cat': 'c1', 'site': 'a.io', 'url': 'https://a.io', 'kind': 'pob', 'jpg': b'x', 'wall': '', 'pages': [{'kind': 'terms', 'url': 'https://a.io/t', 'title': '', 'text': TERMS, 'ok': True}]})
    asyncio.run(fs._site_pass(store))
    m = cat['siteManuals']['a.io']
    assert m['kinds'] == ['pob'] and m['shot'] == 'a.io.jpg' and (tmp_path / 'sitec1' / 'a.io.jpg').read_bytes() == b'x' and not m['model']
    assert 'c1' not in fs._SCAN_BUSY and 'scanned' in cat['chat'][-1]['text']


def test_public_cat_view_never_carries_manuals(fs):
    assert 'siteManuals' not in fs._no_keys(_cat()) and 'proofSite' not in fs._no_keys(_cat(proofSite={'site': 'x'}))


def test_research_list_opens_only_the_named_site():
    import cat_agent as ca
    assert not ca._on_list({}, 'https://axiom.trade/')
    assert ca._on_list({'alsoHosts': ['axiom.trade']}, 'https://axiom.trade/x') and not ca._on_list({'alsoHosts': ['axiom.trade']}, 'https://evil.io/')

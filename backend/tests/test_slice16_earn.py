"""💼 Slice 16 (owner 2026-11-19): PoEco earns real money with faceless paid work. The finder reads public feeds only (fixtures are trimmed copies
of the real reads made 2026-11-20: Superteam Earn, Freelancer.com, GitHub's Algora bounties), keeps what is faceless and allowed by the platform's
terms, scores fit / pay / deadline / the minds' cost; both minds bid blind and the stronger is kept; nothing moves without the OWNER's approve;
graded on real money paid against the minds' cost, fees on the receipt only. Every network call and every mind is faked here."""
import asyncio
import json
from pathlib import Path

import pytest

import eco_earn as ee
import proof_record as prec

FX = Path(__file__).parent / 'fixtures'
NOW = 1795200000.0   # 2026-11-20


def _fx(name):
    return json.loads((FX / name).read_text())


# ── terms first ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_terms_first_only_platforms_that_allow_our_flow_are_kept_and_the_rest_say_why():
    assert ee.KEPT == ['superteam', 'freelancer', 'algora']
    out = {p['id']: p for p in ee.PLATFORMS if not p['in']}
    assert set(out) == {'upwork', 'fiverr', 'contra', 'gitcoin'} and all(p['why'] and p['src'].startswith('https://') for p in out.values())
    for pid in ee.KEPT:   # every kept one: its terms, how the owner sends from HIS account, a public feed (no login)
        p = ee.PLAT[pid]
        assert p['terms'] and 'own' in p['how'] and all(f.startswith('https://') for f in p['feeds'])
    assert 'never bids' in ee.PLAT['freelancer']['terms'] and 'commenter:app/algora-pbc' in ee.PLAT['algora']['feeds'][0]


def test_superteam_keeps_only_listings_its_sponsor_opened_to_agents():
    kept, out = ee.parse_superteam(_fx('earn_superteam.json'))
    assert [r['access'] for r in kept] == ['AGENT_ALLOWED'] and len(out) == 2
    assert all('no AI agents' in r['outWhy'] for r in out)
    r = kept[0]
    assert r['url'].startswith('https://superteam.fun/earn/listing/') and r['deadline'] and r['rivals'] >= 0
    assert r['payUsd'] is None and 'no USD price' in r['pay']   # paid in its own token with no price: shown, never guessed
    k2, _ = ee.parse_superteam([{**_fx('earn_superteam.json')[0], 'token': 'USDC', 'rewardAmount': 500}])
    assert k2[0]['payUsd'] == 500


def test_freelancer_budget_is_turned_into_usd_by_the_listings_own_rate_and_hourly_counts_ten_hours():
    kept, out = ee.parse_freelancer(_fx('earn_freelancer.json'))
    assert kept and not out
    gbp = next(r for r in kept if 'GBP' in r['pay'])
    rate = next(p['currency']['exchange_rate'] for p in _fx('earn_freelancer.json')['result']['projects'] if p['currency']['code'] == 'GBP')
    assert gbp['payUsd'] == round(175 * rate, 2) and gbp['url'].startswith('https://www.freelancer.com/projects/')
    hr = next(r for r in kept if r.get('hourly'))
    assert '/hr (×10 h)' in hr['pay']


def test_algora_bounties_need_a_dollar_amount_and_a_repo_that_does_not_ban_ai_work():
    j = _fx('earn_github.json')
    kept, out = ee.parse_algora(j, {'UnsafeLabs/Bounty-Hunters': 'ok'})
    assert [r['payUsd'] for r in kept] == [900, 250, 5] and not out   # the $ is the bounty's own label
    assert kept[0]['aiRule'].startswith('ok') and 'label' in kept[0]['aiRule']   # its own "AI Agent friendly" label opens it
    _k, out2 = ee.parse_algora(j, {'PG-AGI/toingg-jarvis': 'banned'})
    assert [r['outWhy'] for r in out2] == ['PG-AGI/toingg-jarvis bans AI-made pull requests in its CONTRIBUTING']
    nod = {'items': [{**j['items'][2], 'labels': [{'name': '💎 Bounty'}]}]}
    assert ee.parse_algora(nod)[1][0]['outWhy'] == 'no $ amount on the issue'
    assert ee.ai_rule('We do not accept AI-generated pull requests.') == 'banned' and ee.ai_rule('Please add tests.') == 'ok' and ee.ai_rule(None) == 'unknown'


# ── the finder: faceless fit, pay, deadline, the minds' cost ──────────────────────────────────────────────────────────────────────────

def test_faceless_fit_keeps_keyboard_work_and_drops_a_face_a_voice_or_a_place():
    assert ee.fit_of('Write a Twitter thread on our launch')[0] == 'writing'
    assert ee.fit_of('Fix reentrancy vulnerability in Staking contract')[0] == 'code'
    assert ee.fit_of('Translate our docs to Spanish')[0] == 'translation'
    assert ee.fit_of('Arkansas PE for Floodproofing Plans')[0] == '' and 'licence' in ee.fit_of('Arkansas PE for Floodproofing Plans')[1]   # first real TEST picked it (2026-11-20)
    assert ee.fit_of('Industrial Stairs and Handrails Design')[0] == '' and ee.fit_of('Growth Marketing Manager for an academy')[0] == ''
    assert ee.fit_of('AI Tutoring: Maths to Models')[0] == ''
    assert ee.fit_of('Real Estate Video Shoot')[0] == '' and 'face or a place' in ee.fit_of('Female Model Required for Photoshoot')[1]


def test_the_score_and_board_show_the_best_with_expected_profit_and_what_was_left_out():
    rows = [ee._row('superteam', 'a', 'Write an article about Solana fees', 'https://superteam.fun/earn/listing/a', 'article', 400.0, '400 USDC', NOW + 5 * 86400, 6),
            ee._row('freelancer', 'b', 'Real Estate Video Shoot', 'https://x', 'video', 900.0, '$900', NOW + 5 * 86400, 0),
            ee._row('algora', 'c', 'Fix a bug in the CLI parser', 'https://github.com/o/r/issues/1', 'bug', 150.0, '$150', None, 30),
            ee._row('superteam', 'd', 'Write a thread', 'https://superteam.fun/earn/listing/d', 'thread', 300.0, '300 USDC', NOW + 3600, 2)]
    b = ee.board(rows, [{'outWhy': "its sponsor set it HUMAN_ONLY: no AI agents"}], 0.003, filed_ids=[], now=NOW)
    assert [r['id'] for r in b['best']] == ['superteam:a', 'algora:c']
    a = b['best'][0]
    assert a['cat'] == 'writing' and a['cost'] == round(ee.CALLS['writing'] * 0.003, 4) and a['expProfit'] == round(400 * a['chance'] - a['cost'], 2) and a['hours'] == 3
    assert set(a['parts']) == {'fit', 'pay', 'deadline', 'profit'} and a['score'] == round(sum(a['parts'].values()))
    whys = {o['why'] for o in b['out']}
    assert 'needs a face or a place' in whys and 'due in under 12 hours' in whys and any('HUMAN_ONLY' in w for w in whys)
    assert [r['id'] for r in ee.board(rows, [], 0.003, filed_ids=['superteam:a'], now=NOW)['best']] == ['algora:c']   # one already bid on: a new footprint


def test_the_minds_cost_comes_from_this_agents_real_calls():
    calls = [{'ok': True, 'usd': 0.001, 'at': 5}, {'ok': True, 'usd': 0.004, 'at': 6}, {'ok': True, 'usd': 0.002, 'at': 7}, {'ok': False, 'usd': 9, 'at': 8}]
    assert ee.per_call(calls) == 0.002 and ee.per_call([]) == 0.002 and ee.mind_cost('code', 0.002) == 0.02


# ── the bid: both minds blind, the stronger kept ─────────────────────────────────────────────────────────────────────────────────────

ROW = {'src': 'superteam', 'id': 'superteam:a', 'title': 'Write an article about Solana priority fees', 'url': 'https://superteam.fun/earn/listing/a', 'pay': '400 USDC', 'payUsd': 400.0,
       'daysLeft': 5.0, 'rivals': 6, 'cat': 'writing', 'desc': 'article', 'deadline': NOW + 5 * 86400, 'cost': 0.012, 'chance': 0.333, 'expProfit': 133.2, 'hours': 3, 'parts': {}, 'score': 70}
GOOD = {'bid': ' '.join(['Your article on Solana priority fees needs real numbers and a clear walk-through for builders.'] * 6), 'plan': ['Read the docs', 'Pull fee data', 'Draft', 'Edit'],
        'price': 380, 'days': 3, 'risks': ['late data'], 'fit': 8}
FACE = {**GOOD, 'bid': GOOD['bid'] + " I'm a real person and happy to jump on a video call."}


def test_the_stronger_blind_bid_is_kept_carries_the_ai_note_and_a_face_claim_loses():
    k, scored = ee.pick([ee.parse_bid(json.dumps(FACE)), ee.parse_bid('```json\n' + json.dumps(GOOD) + '\n```')], ROW)
    assert k == 1 and scored[0][0] < scored[1][0] and any('human' in w for w in scored[0][1])
    assert ee.DISCLOSE in scored[1][2]['bid']
    assert ee.pick([None, None], ROW)[0] is None and ee.parse_bid('no json here') is None


def _folder(test=False):
    k, scored = ee.pick([ee.parse_bid(json.dumps(GOOD)), ee.parse_bid(json.dumps({**GOOD, 'plan': ['x']}))], ROW)
    f = ee.new_folder(3, ROW, k, scored, [], 0.0124, NOW)
    if test:
        f['test'] = {'by': 'Claude'}
    return f


def test_nothing_moves_without_the_owner_and_a_test_needs_his_on_purpose_tick():
    f = _folder(test=True)
    assert f['stage'] == 'bid' and f['kind'] == 'earn' and f['status'] == 'closed'
    for who in ('auto', 'internal', 'claude'):
        assert 'Only its owner' in ee.can_go(f, 'bid_approved', who)
    assert 'TEST filing' in ee.can_go(f, 'bid_approved', 'owner') and ee.can_go(f, 'bid_approved', 'owner', test_ok=True) == ''
    assert "comes after" in ee.can_go(f, 'paid', 'owner') and ee.can_go(f, 'lost', 'owner') == ''


def test_graded_on_real_money_fees_stay_on_the_receipt_and_a_loss_is_graded_with_why():
    f = _folder()
    for st in ('bid_approved', 'sent', 'won'):
        ee.move(f, st, 'owner', NOW)
    f['work'] = {'cost': 0.03}
    ee.move(f, 'work', 'minds', NOW); ee.move(f, 'checked', 'collective', NOW); ee.move(f, 'delivery_approved', 'owner', NOW); ee.move(f, 'paid', 'owner', NOW)
    f['receipt'] = ee.receipt(400, 40, 'USDC', 1, 'tx-ref')
    g = ee.grade(f)
    assert g['paidUsd'] == 400 and g['cost'] == round(0.0124 + 0.03, 5) and g['profit'] == round(400 - 0.0424, 2) and g['feeOnReceipt'] == 40   # §1 style: fees never in the profit
    assert g['hoursSaved'] == 3 and g['perHour'] == round(g['profit'] / 3, 2)
    lost = _folder(); ee.move(lost, 'lost', 'owner', NOW, why='another entry won')
    gl = ee.grade(lost)
    assert gl['result'] == 'lost' and gl['profit'] == -0.0124 and gl['why'] == 'another entry won'
    with pytest.raises(ValueError):
        ee.receipt(-1)


def test_an_earn_filing_carries_every_proof_check_and_its_own():
    f = _folder(); f.update(id='earn1', callRefs=['earn1'], kits=['Bid Desk', 'Faceless Work Check'], sitesRead=[{'host': 'superteam.fun', 'ok': True}])
    calls = [{'kind': 'poe', 'ref': 'earn1', 'asked': m, 'model': m, 'ok': True, 'usd': 0.006, 'at': NOW} for m in ('qwen/a', 'openai/b')]
    prec.stamp('poe', f, calls, ['qwen/a', 'openai/b'], [], 0, None, None, NOW + 1)
    ch = {c['key']: c for c in f['proofChecks']}
    assert {'minds', 'sources', 'footprint', 'kits', 'terms', 'finder', 'bid', 'approve', 'graded'} <= set(ch)
    assert ch['minds']['ok'] and 'qwen/a + openai/b ran' in ch['minds']['why']   # an earn filing's minds are checked from the call log (not "pure math")
    assert ch['kits']['ok'] and ch['sources']['ok'] and ch['terms']['ok'] and ch['finder']['ok'] and ch['bid']['ok'] and ch['approve']['ok']
    nokits = _folder(); nokits.update(id='earn2', callRefs=['earn2'])
    prec.stamp('poe', nokits, [], [], [], 0, None, None, NOW)
    assert not {c['key']: c for c in nokits['proofChecks']}['kits']['ok']   # an earn filing needs its kits (only a market call is pure math)
    mk = {'id': 'm1', 'kind': 'market', 'baseline': {'pick': {'addr': 'x'}, 'other': {'addr': 'y'}}}
    prec.stamp('poe', mk, [], [], [], 0, None, None, NOW)
    assert {c['key']: c for c in mk['proofChecks']}['minds']['ok']   # no back pedal: a market call still passes with no mind


def test_the_collective_judges_an_earn_filing_on_its_own_rubric_with_the_bid_and_the_stages():
    import proof_review as pr
    f = _folder()
    assert pr.rubric_of('poe', f) == pr.RUBRIC_EARN and len(pr.RUBRIC_EARN) == 5
    ev = pr._evidence('poe', f)
    assert ev['bid']['bid'] and ev['listing']['url'] and ev['stages'][0] == {'stage': 'bid', 'by': 'minds'} and 'deliverable' not in ev
    f['work'] = {'text': 'The finished article.'}
    assert pr._evidence('poe', f)['deliverable'] == 'The finished article.'


def test_poeco_has_its_own_kits_for_the_minds():
    import collective_kits as ck
    assert 'poe' in ck.KINDS and {'fl-bid-desk', 'fl-faceless-work'} <= {k['id'] for k in ck._book.BOOK if 'poe' in k['kinds']}
    assert any(s['kind'] == 'poe' for s in ck._book.STACKS)


# ── the service: find → both minds bid → filed, nothing sent; only the owner moves it ────────────────────────────────────────────────

class FakeHttp:
    def __init__(self):
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **k):
        self.urls.append(url)
        assert 'Authorization' not in (k.get('headers') or {}) and 'cookies' not in k   # public reads only
        if 'superteam.fun' in url:
            rows = _fx('earn_superteam.json')
            body = rows + [{**rows[0], 'id': 'w1', 'slug': 'write-solana-fees', 'title': 'Write an article on Solana priority fees', 'token': 'USDC', 'rewardAmount': 500,
                            'deadline': '2026-12-01T00:00:00.000Z', 'agentAccess': 'AGENT_ALLOWED', '_count': {'Submission': 4}}] if 'bounty' in url else []
        elif 'freelancer.com' in url:
            body = _fx('earn_freelancer.json')
        elif 'api.github.com' in url:
            body = _fx('earn_github.json')
        elif 'raw.githubusercontent.com' in url:
            return Resp(404, None, '')
        else:
            body = {'pairs': [{'quoteToken': {'symbol': 'USDC'}, 'priceUsd': '150', 'liquidity': {'usd': 9e6}}]}
        return Resp(200, body)


class Resp:
    def __init__(self, code, body, text=''):
        self.status_code = code; self._b = body; self.text = text

    def json(self):
        return self._b


@pytest.fixture
def svc(monkeypatch):
    import feecat_service as fs
    cat = {'id': 'c1', 'name': "Happy's", 'handle': 'happy-assistant', 'chat': [], 'brainsCfg': {'brains': ['qwen/a', 'openai/b'], 'credit': 1.0}, 'poeFolders': []}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **k: FakeHttp())
    seen, refs = [], []

    async def ask(cat_, m, sys_, user_, tokens):
        seen.append((m, sys_, user_)); refs.append((fs._CALL_CTX.get() or {}).get('ref'))
        assert 'BID DESK' in sys_ or 'Bid Desk' in sys_, 'the minds get PoEco\'s own kits'
        return json.dumps(GOOD if m == 'qwen/a' else {**GOOD, 'plan': ['one step']}), 0.004, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    monkeypatch.setattr(fs, '_calls_of', lambda cid, n=0: [{'kind': 'poe', 'ref': r, 'asked': m, 'model': m, 'ok': True, 'usd': 0.004, 'at': fs.time.time()}
                                                           for r in set(refs) for m in ('qwen/a', 'openai/b')])
    fs._fc_earn._BUSY.clear(); fs._TEST_ON.clear()
    return fs, cat, store, seen


def test_a_real_listing_is_found_scored_both_minds_bid_blind_and_nothing_is_sent(svc, monkeypatch):
    fs, cat, _store, seen = svc
    run = lambda session='s', **kw: asyncio.run(fs._cat_work('c1', fs.WorkPayload(session=session, **kw)))
    v = run(op='earn_find')
    best = v['board']['best']
    assert best[0]['title'] == 'Write an article on Solana priority fees' and best[0]['payUsd'] == 500 and best[0]['expProfit'] > 0
    assert {r['host'] for r in v['board']['reads']} >= {'superteam.fun', 'freelancer.com', 'api.github.com', 'dexscreener.com'}
    assert any('HUMAN_ONLY' in o['why'] for o in v['board']['out'])
    fs._TEST_ON[('c1', 'poe')] = {'at': fs.time.time(), 'by': 'Claude', 'run': 'r1'}
    asyncio.run(fs._fc_earn._bid('c1', ''))
    f = cat['poeFolders'][-1]
    assert f['kind'] == 'earn' and f['stage'] == 'bid' and f['kept'] == 0 and len(f['bids']) == 2 and f['testRun']
    assert len({s for _m, s, _u in seen}) == 2 and all('Solana priority fees' in u for _m, _s, u in seen)   # blind: each mind its own prompt, neither sees the other's bid
    assert f['kits'] and f['listing']['url'].startswith('https://superteam.fun/') and f['test']['by'] == 'Claude'
    ch = {c['key']: c['ok'] for c in f['proofChecks']}
    assert all(ch[k] for k in ('minds', 'sources', 'footprint', 'kits', 'terms', 'finder', 'bid', 'approve', 'graded')), f['proofChecks']
    assert 'Nothing was sent' in cat['chat'][-1]['text']
    # the internal key (auto runs, Claude's TESTs) can never approve, mark or deliver
    for stage in ('bid_approved', 'sent', 'paid'):
        with pytest.raises(fs.HTTPException) as e:
            run(session=fs._AUTO_TOKEN, op='earn_go', job=f['id'], tools={'stage': stage})
        assert e.value.status_code == 403
    with pytest.raises(fs.HTTPException) as e:
        run(session=fs._AUTO_TOKEN, op='earn_work', job=f['id'])
    assert e.value.status_code == 403
    with pytest.raises(fs.HTTPException) as e:   # the owner, but a TEST: only on purpose
        run(op='earn_go', job=f['id'], tools={'stage': 'bid_approved'})
    assert 'TEST filing' in e.value.detail
    out = run(op='earn_go', job=f['id'], tools={'stage': 'bid_approved', 'real': True})
    assert out['send']['url'] == f['listing']['url'] and ee.DISCLOSE in out['send']['bid'] and f['approved']['seal'] == ee.seal(f)
    run(op='earn_go', job=f['id'], tools={'stage': 'lost', 'why': 'not picked'})
    assert f['graded']['result'] == 'lost' and f['graded']['why'] == 'not picked'
    assert [s['by'] for s in f['stages']] == ['minds', 'owner', 'owner']


def test_the_test_door_files_an_earn_filing_and_never_a_market_call(svc, monkeypatch):
    fs, cat, _store, _seen = svc
    monkeypatch.setattr(fs, '_internal', lambda r: None)
    started = []

    async def fake_bid(cid, lid='', wiz=None):
        started.append((cid, lid) if wiz is None else (cid, lid, wiz))   # 🧭 Slice 33: no wizard sent = none passed on
    old = fs._fc_earn._bid; fs._fc_earn._bid = fake_bid
    try:
        cat['handle'] = 'happy-assistant'
        out = asyncio.run(fs._fc_test.test_proof_start(fs._fc_test.TestIn(kind='poe', door='earn', agent='happy'), _Req(fs)))
    finally:
        fs._fc_earn._bid = old; fs._TEST_ON.clear()   # the faked bid never files, so its TEST claim would stay live (health() counts it as busy)
    assert out['ok'] and started == [('c1', '')] and not cat['poeFolders']


class _Req:
    def __init__(self, fs):
        self.headers = {'x-feeless-internal': 'k'}

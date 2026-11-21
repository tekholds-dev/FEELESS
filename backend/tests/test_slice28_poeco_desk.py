"""Slice 28 · the PoEco desk: an earning dashboard; licensed / regulated work filtered out; a bid's price and time realistic for the work;
one-tap "find me work" by skill; a live feed of jobs where AI can really compete; and, before the owner starts a job, what it takes to win
(the minds and models, their expected cost, the time, the competition and the win chance). Network faked."""
import asyncio
import json
import time

import eco_earn as ee
import test_slice16_earn as s16

svc = s16.svc   # the Slice 16 service fixture: fake feeds, fake minds
GOOD = s16.GOOD

NOW = 1795200000.0
STAIR = ee._row('freelancer', 's1', 'Industrial Stairs and handrail drawings', 'https://www.freelancer.com/projects/x',
                'Structural stair + handrail CAD to OSHA / IBC; stamped drawings; work from site dimensions you provide?', 900.0, '$600–1,200 USD', NOW + 5 * 86400, 3)
HUGE = ee._row('freelancer', 'h1', 'Build our whole marketplace web app', 'https://www.freelancer.com/projects/y',
               'Implement the backend and frontend of a marketplace: the full spec is attached, deliver in milestones.', 27500.0, '$20,000–35,000 USD', NOW + 20 * 86400, 4,
               {'payLo': 20000.0, 'payHi': 35000.0})
WRITE = ee._row('superteam', 'w1', 'Write an article on Solana priority fees', 'https://superteam.fun/earn/listing/w1',
                'Deliver one 1,500 words article: must explain priority fees, the format is Markdown, the requirements are in the brief.', 300.0, '300 USDC', NOW + 6 * 86400, 2)
CODE = ee._row('algora', 'c1', 'Fix the callback timestamp bug in the event loop', 'https://github.com/o/r/issues/2',
               'o/r · fix the bug: the callback gets a stale timestamp; must pass the tests; deliver a PR with a test.', 400.0, '$400', None, 1)


def test_licensed_or_regulated_work_is_filtered_out_and_said_why():
    for t in ('Structural stair + handrail CAD to OSHA / IBC; stamped drawings', 'Need a P.E. to sign shop drawings', 'Prepare my tax return', 'Building code compliance report for a permit'):
        cat, why = ee.fit_of(t)
        assert cat == '' and 'licence' in why, t
    assert ee.score(STAIR, 0.003, NOW)['score'] == 0


def test_a_word_inside_another_word_never_drops_a_real_job():
    # the live read 2026-11-21: 'call' matched 'callback', 'stamp' matched 'timestamp', 'event' matched 'event loop', so real code bounties were dropped
    assert ee.fit_of(CODE['title'] + ' ' + CODE['desc'])[0] == 'code'
    assert ee.fit_of('Data model for the analytics API')[0] == 'data'
    assert ee.fit_of('Home model needed for a lifestyle shoot')[0] == ''          # a real face job still drops
    assert ee.fit_of('Hop on a call to discuss')[0] == ''


def test_a_job_too_big_for_a_faceless_one_off_is_out_with_the_hours_it_would_take():
    s = ee.score(HUGE, 0.003, NOW)
    assert s['score'] == 0 and s['real']['tooBig'] and 'too big' in s['fitWhy']
    b = ee.board([HUGE, WRITE], [], 0.003, now=NOW)
    assert [r['id'] for r in b['best']] == ['superteam:w1'] and any(o['why'].startswith('too big') for o in b['out'])


def test_a_bid_that_promises_the_impossible_loses_and_the_kept_one_is_set_to_a_realistic_time():
    row = ee.score({**WRITE, 'payUsd': 1200.0}, 0.003, NOW)      # 1200 / $35 = 34 human hours → at least 2 days
    assert row['real']['minDays'] == 2 and 'at least 2 days' in ee.ask_text(row)
    fast = {**GOOD, 'bid': GOOD['bid'] + ' I will deliver it within 24 hours.', 'price': 1200, 'days': 1}
    slow = {**GOOD, 'price': 1100, 'days': 3}
    k, scored = ee.pick([ee.parse_bid(json.dumps(fast)), ee.parse_bid(json.dumps(slow))], row)
    assert k == 1 and any('not realistic' in w for w in scored[0][1])
    assert scored[1][2]['realistic']['ok']
    k2, sc2 = ee.pick([ee.parse_bid(json.dumps(fast))], row)       # only the fast one came back: kept, flagged, its days set to what is real
    b = sc2[k2][2]
    assert b['realistic']['ok'] is False and b['days'] == 2 and b['daysAsked'] == 1
    assert ee.unreal({'price': 30000, 'days': 1, 'bid': 'within 1 day'}, {**HUGE, 'cat': 'code'})


def test_what_it_takes_to_win_shows_the_minds_models_cost_time_competition_and_chance():
    minds = ['qwen/qwen3.8-max', 'local/ossy']
    s = ee.score({**WRITE, 'avgBid': 250.0}, 0.003, NOW, minds=minds, models={'qwen/qwen3.8-max': 0.005})
    n = s['needs']
    assert [m['model'] for m in n['minds']] == minds and n['minds'][1]['local'] and n['minds'][1]['usd'] == 0.0
    assert n['minds'][0]['usd'] == round(n['minds'][0]['calls'] * 0.005, 4) and n['cost'] == s['cost']   # the board's cost IS the per-model cost
    assert n['days'] >= 1 and n['humanRate'] == ee.RATE['writing'] and n['rivals'] == 2 and n['avgBid'] == 250.0 and 'Bid Desk' in n['kits']
    assert 0 < s['chance'] <= 0.35 and s['expProfit'] == round(300 * s['chance'] - s['cost'], 2)
    assert ee.per_model([{'ok': True, 'usd': 0.001, 'asked': 'a'}, {'ok': True, 'usd': 0.003, 'asked': 'a'}, {'ok': True, 'usd': 0.009, 'asked': 'a'}]) == {'a': 0.003}


def test_the_live_feed_keeps_jobs_where_ai_can_really_compete_and_a_skill_tap_keeps_one_kind():
    crowded = {**WRITE, 'id': 'superteam:w2', 'rivals': 40}
    vague = {**CODE, 'id': 'algora:c2', 'desc': 'o/r'}
    b = ee.board([WRITE, CODE, crowded, vague], [], 0.003, now=NOW)
    assert {r['id'] for r in b['feed']} == {'superteam:w1', 'algora:c1'}             # few bids + a clear scope + fast
    assert b['skills']['writing'] == 2 and b['skills']['code'] == 2
    only = ee.board([WRITE, CODE, crowded, vague], [], 0.003, now=NOW, skill='code')
    assert {r['cat'] for r in only['best']} == {'code'} and only['skill'] == 'code'


def test_a_kept_board_is_read_again_with_todays_rules():
    old = {'at': NOW, 'best': [{**STAIR, 'cat': 'design', 'score': 70}, {**WRITE, 'cat': 'writing', 'score': 60}], 'out': []}   # kept from before the licence rule
    nb = ee.rescore(old, 0.003, now=NOW)
    assert [r['id'] for r in nb['best']] == ['superteam:w1'] and any('licence' in o['why'] for o in nb['out'])


def test_the_dashboard_counts_jobs_bids_work_money_and_market_calls():
    earns = [{'id': 'e1', 'at': 1, 'stage': 'bid', 'cost': 0.01}, {'id': 'e2', 'at': 2, 'stage': 'won', 'cost': 0.02},
             {'id': 'e3', 'at': 3, 'stage': 'paid', 'cost': 0.03, 'work': {'cost': 0.04}, 'graded': {'result': 'paid', 'paidUsd': 120.0}},
             {'id': 'e4', 'at': 4, 'stage': 'lost', 'cost': 0.01}]
    markets = [{'graded': 'right'}, {'graded': 'wrong'}, {}]
    d = ee.dash(earns, markets, {'best': [{'expProfit': 10.0}, {'expProfit': -2}], 'feed': ['x'], 'at': NOW})
    assert d['found'] == 2 and d['expUsd'] == 10.0 and d['waiting'] == 1 and d['inWork'] == 1 and d['paidN'] == 1 and d['lost'] == 1
    assert d['paidUsd'] == 120.0 and d['mindsUsd'] == 0.11 and d['netUsd'] == round(120 - 0.11, 4)   # fees never here: they live on the receipt
    assert d['calls'] == {'n': 3, 'right': 1, 'wrong': 1, 'open': 1} and d['curve'][-1]['net'] == d['netUsd']


# ── wired: click → saved → used by the engine → shown in the record ────────────────────────────────────────────────────────────────

def test_a_skill_tap_is_saved_on_the_board_used_by_the_bid_and_shown_on_the_filing(svc, monkeypatch):
    fs, cat, _store, _seen = svc
    run = lambda **kw: asyncio.run(fs._cat_work('c1', fs.WorkPayload(session='s', **kw)))
    v = run(op='earn_find', tools={'skill': 'writing'})
    assert cat['earnBoard']['skill'] == 'writing' and v['board']['skill'] == 'writing'       # saved
    assert v['board']['best'] and {r['cat'] for r in v['board']['best']} == {'writing'}
    assert v['dash']['found'] == len(v['board']['best']) and 'minds' in v and v['skills'] == list(ee.SKILLS)
    n = v['board']['best'][0]['needs']
    assert [m['model'] for m in n['minds']] == ['qwen/a', 'openai/b'] and n['cost'] > 0     # what it takes, from this agent's own pair and call log
    fs._TEST_ON[('c1', 'poe')] = {'at': time.time(), 'by': 'Claude', 'run': 'r1'}
    asyncio.run(fs._fc_earn._bid('c1', ''))                                                # used: the auto pick keeps to the skill
    f = cat['poeFolders'][-1]
    assert f['listing']['cat'] == 'writing' and f['listing']['needs']['minds'] and f['listing']['real']['minDays'] >= 1   # shown on the filing
    assert 'realistic' in {c['key'] for c in f['proofChecks']} and f['bid']['realistic']
    with __import__('pytest').raises(fs.HTTPException):
        run(op='earn_find', tools={'skill': 'plumbing'})
    fs._TEST_ON.clear()


def test_the_view_drops_a_job_a_newer_rule_rules_out(svc):
    fs, cat, _store, _seen = svc
    cat['earnBoard'] = {'at': time.time(), 'best': [{**STAIR, 'cat': 'design', 'score': 70}], 'out': [], 'perCall': 0.003}
    v = asyncio.run(fs._cat_work('c1', fs.WorkPayload(session='s', op='earn_view')))
    assert v['board']['best'] == [] and v['dash']['found'] == 0 and 'all' not in v['board']

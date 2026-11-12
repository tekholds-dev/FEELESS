"""🧪 Model Lab: the dataset counts what really happened, scrubs every wallet / address / email / phone / key, keeps the owner's grades,
and never turns an open proof into a row until a person or the market settled it."""
import json
import zlib

import pytest

import model_lab as ml

ITEMS = [
    {'key': 'a', 'at': 30, 'category': 'Picks', 'outcome': 'won', 'title': 'NBA: Lakers -3', 'source': 'espn.com'},
    {'key': 'b', 'at': 29, 'category': 'Picks', 'outcome': 'lost', 'title': 'NFL over 44', 'source': 'nfl.com'},
    {'key': 'c', 'at': 28, 'category': 'Trades', 'outcome': 'none', 'title': 'Pump coin 9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin', 'source': 'pump.fun'},
    {'key': 'd', 'at': 27, 'category': 'Code', 'outcome': 'flat', 'title': 'Coffee page', 'source': 'own read'},
    {'key': 'e', 'at': 26, 'category': 'Snapshots', 'outcome': 'none', 'title': 'shot', 'source': 'x.com'},
]


def test_scrub_takes_out_every_private_thing_and_keeps_dates():
    t = ml.scrub('pay 9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin or 0x52908400098527886E0F7030069857D2E4169EE7, mail jo@x.io, '
                 'call +44 20 7946 0958 or (555) 123-4567, key sk-live_abcdefghijklmnop, on 2026-11-11 02:00')
    assert '[wallet]' in t and '[address]' in t and '[email]' in t and t.count('[phone]') == 2 and '[key]' in t
    assert '9xQe' not in t and 'jo@x.io' not in t and '2026-11-11 02:00' in t


def test_summary_counts_real_outcomes_pairs_and_owner_grades():
    s = ml.summary(ITEMS, [], {'c': {'verdict': 'good'}})
    pob = next(k for k in s['kinds'] if k['kind'] == 'PoB'); pow_ = next(k for k in s['kinds'] if k['kind'] == 'PoW')
    assert (pob['rows'], pob['won'], pob['lost'], pob['pairs']) == (2, 1, 1, 1)
    assert (pow_['rows'], pow_['graded'], pow_['open']) == (1, 1, 0) and s['snapshots'] == 1 and s['rows'] == 4 and s['graded'] == 1
    assert s['steps']['data'] == 'have' and s['steps']['sft'] == 'todo' and s['steps']['eval'] == 'todo'   # no calls yet → nothing to beat


def test_minds_record_cost_speed_and_failures_per_model():
    calls = [{'asked': 'tencent/hy4', 'kind': 'poc', 'ok': True, 'usd': 0.002, 'ms': 1000}, {'asked': 'tencent/hy4', 'kind': 'pos', 'ok': False, 'usd': 0.001, 'ms': 3000}]
    m = ml.summary([], calls, {})['minds'][0]
    assert m['model'] == 'hy4' and m['calls'] == 2 and m['failed'] == 1 and m['failRate'] == 0.5 and m['avgMs'] == 2000 and m['usd'] == 0.003 and m['kinds'] == {'poc': 1, 'pos': 1}


def test_the_queue_is_open_ungraded_proofs_only_and_a_grade_must_be_real():
    assert [q['key'] for q in ml.queue(ITEMS, {})] == ['c'] and '[wallet]' in ml.queue(ITEMS, {})[0]['title']
    g = ml.grade({}, 'c', 'skip', '', 5)
    assert ml.queue(ITEMS, g) == [] and ml.summary(ITEMS, [], g)['open'] == 0
    with pytest.raises(ValueError):
        ml.grade({}, 'c', 'great', '', 5)


def test_export_rows_are_settled_or_owner_graded_and_scrubbed():
    raw = {'a': zlib.compress(json.dumps({'plan': 'Read espn, mail me at jo@x.io', 'why': 'injury news'}).encode())}
    rows = [json.loads(x) for x in ml.export_lines(ITEMS, lambda k: raw.get(k), {'c': {'verdict': 'bad', 'note': 'rug'}})]
    assert [r['title'][:3] for r in rows] == ['NBA', 'NFL', 'Pum', 'Cof']
    assert rows[0]['plan'] == 'Read espn, mail me at [email]' and rows[0]['why'] == 'injury news' and rows[0]['outcome'] == 'won'
    assert rows[2]['by'] == 'owner' and rows[2]['outcome'] == 'lost' and '[wallet]' in rows[2]['title']
    assert all('Snapshots' not in json.dumps(r) for r in rows)


def test_the_routes_are_owner_only():
    import rep_model_lab as rml
    src = open(rml.__file__).read()
    assert src.count('@router.') >= 3 and src.count('rs._require_owner(request)') == src.count('@router.')   # every route, the forge's too, is the owner's

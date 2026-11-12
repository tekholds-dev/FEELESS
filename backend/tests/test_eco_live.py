"""🏦 PoEco live books: fees in, model spend out, the real card — summed from the stores, bucketed by day, an honest verdict, owner-only route."""
import json
import time

import eco_live as el

NOW = time.mktime((2026, 11, 12, 12, 0, 0, 0, 0, -1))


def test_books_sum_the_real_stores_by_day_and_say_the_truth():
    ledger = {'w1': [{'t': NOW - 3600, 'feeUsd': 0.5}, {'t': NOW - 10 * 86400, 'feeUsd': 0.25}], 'w2': []}
    calls = [{'at': NOW - 60, 'usd': 0.3, 'model': 'x/hy4', 'kind': 'pos'}, {'at': NOW - 2 * 86400, 'usd': 0.2, 'model': 'claude-sonnet-5.5', 'kind': 'poc'},
             {'at': NOW - 40 * 86400, 'usd': 1.0, 'model': 'old', 'kind': 'pos'}, {'at': NOW, 'usd': 0, 'model': 'local'}]
    audit = {'at': NOW - 100, 'putInUsd': 54.63, 'open': [{'costUsd': 1.5}, {'costUsd': 0.5}], 'windows': {'7d': {'all': {'n': 2, 'netUsd': -0.1}}}, 'verdict': 'NO PROVEN EDGE'}
    b = el.build(ledger, calls, audit, {'w1': 0.05}, now=NOW)
    k = b['kpi']
    assert (k['feesUsd'], k['fees7dUsd'], k['trades'], k['payers']) == (0.75, 0.5, 2, 1)
    assert (k['spendUsd'], k['spend7dUsd'], k['calls']) == (1.5, 0.5, 4)
    assert k['netUsd'] == round(0.75 - 0.05 - 1.5, 4) and k['net7dUsd'] == round(0.5 - 0.5 - 0.1, 4)
    assert len(b['daily']) == 30 and round(sum(x['out'] for x in b['daily']), 4) == 0.5 and b['daily'][-1]['cum'] == round(sum(x['net'] for x in b['daily']), 4)
    assert b['byModel'][0] == {'k': 'old', 'usd': 1.0} and {'k': 'hy4', 'usd': 0.3} in b['byModel']
    assert b['card'] == {'putInUsd': 54.63, 'openCostUsd': 2.0, 'open': 2, 'net7dUsd': -0.1, 'trips7d': 2, 'verdict': 'NO PROVEN EDGE', 'asOf': round(NOW - 100)}
    assert '×' in b['say']
    assert 'No fee income' in el.build({}, calls, None, {}, now=NOW)['say'] and el.build({}, [], None, {}, now=NOW)['card'] is None


def test_read_tolerates_missing_and_broken_files(tmp_path):
    (tmp_path / 'calls.jsonl').write_text('{"at": 1, "usd": 0.1}\nnot json\n')
    (tmp_path / 'ledger.json').write_text('{broken')
    led, calls, audit, fb = el.read({'ledger': tmp_path / 'ledger.json', 'calls': tmp_path / 'calls.jsonl', 'audit': tmp_path / 'none.json', 'feeback': tmp_path / 'x.json'})
    assert (led, len(calls), audit, fb) == ({}, 1, None, {})


def test_the_route_is_owner_only():
    src = open(el.__file__.replace('eco_live.py', 'rep_model_lab.py')).read()
    block = src[src.index("'/api/reputation/admin/eco/live'"):]
    assert 'rs._require_owner(request)' in block[:400]

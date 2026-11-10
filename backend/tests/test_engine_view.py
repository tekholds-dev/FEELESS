"""AGT-12: the Engine folder's numbers come from the real call log and store, counts only."""
import json

import engine_view as ev


def test_routes_reviewer_reads_methods():
    now = 10_000
    lines = [json.dumps({'at': now - 60, 'route': 'local', 'ok': True, 'usd': 0, 'ms': 2000, 'ref': 'review:a', 'asked': 'local/ossy', 'model': 'q9'}).replace(': ', ':').replace(', ', ','),
             json.dumps({'at': now - 30, 'route': 'lan', 'ok': False, 'usd': 0, 'ms': 4000}), json.dumps({'at': now - 9999, 'route': 'singit', 'ok': True, 'usd': 1})]
    r = ev.routes(lines, now)
    assert [x['route'] for x in r] == ['local', 'lan'] and r[1]['okPct'] == 0 and r[0]['avgMs'] == 2000
    cats = [{'handle': 'sicarios', 'powFolders': [{'status': 'closed', 'review': {'v': 4, 'verdict': 'pass', 'at': 5}}, {'status': 'closed'}, {'status': 'closed', 'noTrade': True}]},
            {'handle': 'happy', 'psFolders': [{'status': 'closed'}]}]
    rv = ev.reviewer(cats, 4, lines, 90, ('sicarios',))
    assert (rv['graded'], rv['waiting'], rv['passPct']) == (1, 1, 100) and rv['answered'][0]['who'] == 'OSSY · local · q9'
    rd = ev.reads({'pob': (now - 60, 'x', ['a', 'b'], 3), 'pow': (now - 9999, 'x', [], 1)}, {'nba': {'at': now - 10, 'reused': 2}}, {'pob': 1800, 'pow': 300}, now)
    assert rd['kinds'] == [{'kind': 'pob', 'ageMin': 1, 'freshMin': 30, 'reused': 3, 'sites': 2}] and rd['topicReuses'] == 2
    assert ev.methods({'a': {'kit': 'a', 'state': 'active'}, 'b': {'kit': 'b', 'state': 'quarantined'}})['quarantined'] == 1

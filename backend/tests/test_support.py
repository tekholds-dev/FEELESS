import support as sp


def test_public_board_cleans_titles_and_ranks_by_importance():
    bugs = [{'id': 'a', 'text': '[auto crash] boom · at X (http://x/y.js:1:2)', 'page': '/terminal/fuse?tab=arena', 'kind': 'bug', 'count': 30, 'status': 'open', 'at': 100, 'lastAt': 100},
            {'id': 'b', 'text': 'wallet 9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin leaks', 'page': '/', 'kind': 'security', 'count': 1, 'at': 100},
            {'id': 'c', 'text': 'idea: darker chart', 'page': '/terminal/trade', 'kind': 'idea', 'count': 1, 'status': 'fixed', 'at': 100}]
    rows = sp.board(bugs, {'c': ['w1', 'w2']}, now=200)
    assert rows[0]['id'] in ('a', 'b') and rows[-1]['id'] == 'c'
    a = next(r for r in rows if r['id'] == 'a')
    assert a['title'] == '💥 boom' and a['area'] == 'fuse' and 'http' not in a['title']
    b = next(r for r in rows if r['id'] == 'b')
    assert '9xQe' not in b['title'] and 'Security' in b['title']
    assert sp.importance({'kind': 'bug', 'count': 1, 'at': 0}, plus=4, now=1) > sp.importance({'kind': 'bug', 'count': 1, 'at': 0}, now=1)


def test_polls_climb_the_ladder_and_the_owner_decides():
    q, opts = sp.clean_poll('  Add a dark pink panther?  ', ['yes', 'Yes', 'no', ''])
    assert opts == ['yes', 'no']
    p = {'id': 'p1', 'q': q, 'options': opts, 'votes': {}}
    for i in range(10):
        sp.vote(p, f'w{i}', 0)
    assert sp.stage(p)['key'] == 'hot' and sp.stage(p)['next']['need'] == 15
    sp.vote(p, 'w0', 0)   # same option again = take it back
    assert len(p['votes']) == 9
    p['status'] = 'roadmap'
    assert sp.stage(p)['key'] == 'roadmap'
    assert sp.poll_view(p, 'w1')['tally'] == [9, 0] and sp.poll_view(p, 'w1')['mine'] == 0
    assert sp.can_post([{'by': 'me', 'at': 10}] * 3, 'me', now=20) is False

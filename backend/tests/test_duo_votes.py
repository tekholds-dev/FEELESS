import duo_votes as dv


def test_the_market_grades_the_author_and_every_vote_at_5m_1h_24h():
    st = dv.add({}, 'k1', 'local', 'HOLD', 'M', 1.0, 0)
    st, ok = dv.vote(st, 'k1', 'owner', -1)                    # the owner dislikes OSSY's HOLD …
    assert ok and not dv.vote(st, 'k1', 'local', 1)[1]          # … a model can't vote on its own call
    st = dv.settle(st, lambda m: 1.5, 301)                      # … and it moons 50% in 5 min
    assert st['items']['k1']['res']['300'] == {'move': 50.0, 'ok': 1}
    assert st['score']['local']['pts'] == 2 and st['score']['owner']['pts'] == -1   # OSSY still gains (stake 1 + 1 vote), the owner's 👎 was wrong
    assert dv.confidence(st, 'local') == 1 and '1 call checkpoints' in dv.words(st, 'local')
    st = dv.settle(st, lambda m: 0.5, 3601)                     # by 1h it dumped: the HOLD was wrong at that checkpoint
    assert st['items']['k1']['res']['3600']['ok'] == -1 and st['score']['owner']['voteRight'] == 1
    st = dv.settle(st, lambda m: 1.005, 86401)                  # a flat 24h is a draw
    assert st['items']['k1']['res']['86400']['ok'] == 0
    v = dv.view(st, 'k1')
    assert v['down'] == 1 and v['mine'] == -1 and [r[0] for r in v['res']] == [300, 3600, 86400]


def test_a_wait_or_unpriced_comment_is_not_graded_and_the_boost_is_capped():
    assert dv.add({}, 'w', 'lan', 'WAIT', 'M', 1.0, 0)['items'] == {} and dv.add({}, 'x', 'lan', 'BUY', 'M', 0, 0)['items'] == {}
    st = {'score': {'lan': {'pts': 999}}}
    assert dv.confidence(st, 'lan') == dv.CAP and dv.side_of('TALK', 'SELL') == -1

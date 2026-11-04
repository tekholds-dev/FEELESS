"""🐝 Colony loss shapes + 🧠 best mind per topic: fake folders only."""
import proof_loop as pl


def _coin(mint='m1', src='pump', liq=30_000, mc=200_000, ch=10):
    return {'mint': mint, 'sym': mint.upper(), 'src': src, 'liq': liq, 'mc': mc, 'ch': ch}


def _f(pnl, mint='m1', picks=None, models=None, **kw):
    c = _coin(mint, **kw)
    return {'status': 'closed', 'mint': mint, 'coins': [c], 'pnlSol': pnl, 'pnlPct': pnl * 10, 'picks': picks or {}, 'models': models}


def _cat(fs, share=True, **kw):
    return {'powFolders': fs, 'colonyShare': {'on': share}, **kw}


def test_a_shape_needs_3_losses_from_2_agents():
    assert pl.colony_shapes({'a': _cat([_f(-1), _f(-1), _f(-1)])}) == {}
    assert pl.colony_shapes({'a': _cat([_f(-1), _f(-1)]), 'b': _cat([])}) == {}
    got = pl.colony_shapes({'a': _cat([_f(-1), _f(-1)]), 'b': _cat([_f(-1)])})
    assert list(got.values()) == [{'losses': 3, 'wins': 0, 'agents': 2}]


def test_a_shape_that_also_wins_is_not_blocked():
    assert pl.colony_shapes({'a': _cat([_f(-1), _f(-1), _f(1)]), 'b': _cat([_f(-1), _f(1)])}) == {}


def test_only_a_sharing_agent_gets_them_and_only_sharers_feed_them():
    cats = {'a': _cat([_f(-1), _f(-1)]), 'b': _cat([_f(-1)]), 'free': _cat([], share=False), 'off': _cat([_f(-1)] * 9, share=False)}
    assert pl.colony_shapes(cats, 'free') == {}
    assert len(pl.colony_shapes(cats, 'a')) == 1
    assert list(pl.colony_shapes(cats, 'a').values())[0]['losses'] == 3   # the agent that does not share gave nothing


def test_incognito_agents_never_feed_the_colony():
    assert pl.colony_shapes({'a': _cat([_f(-1), _f(-1)]), 'b': _cat([_f(-1)], incognito=True)}) == {}


def test_nothing_about_another_agent_crosses_over():
    got = pl.colony_shapes({'a': _cat([_f(-1), _f(-1)]), 'b': _cat([_f(-1)])}); row = list(got.values())[0]
    assert set(row) == {'losses', 'wins', 'agents'}


def test_a_coin_of_that_shape_is_like_and_another_is_not():
    got = pl.colony_shapes({'a': _cat([_f(-1), _f(-1)]), 'b': _cat([_f(-1)])})
    assert pl.colony_like(_coin('other'), got)['losses'] == 3
    assert pl.colony_like(_coin('big', liq=900_000), got) is None


def _won(a_won, n=4, topic_src='pump'):
    fs = []
    for k in range(n):
        fs.append(_f(1 if k < a_won else -1, picks={'0': 0}, models=['alpha', 'beta'], src=topic_src))
    return fs


def test_a_mind_is_graded_only_on_the_coin_it_picked():
    f = _f(1, picks={'0': 0, '1': 5}, models=['alpha', 'beta'])
    assert pl.mind_board({'powFolders': [f]}) == {'trenches pump': {'alpha': {'right': 1, 'wrong': 0}}}


def test_lead_needs_3_calls_each_and_a_gap():
    board = {'t': {'a': {'right': 3, 'wrong': 0}, 'b': {'right': 0, 'wrong': 2}}}
    assert pl.lead_of(board, ['t'], ['a', 'b']) is None
    board['t']['b']['wrong'] = 3
    got = pl.lead_of(board, ['t'], ['a', 'b'])
    assert (got['i'], got['right'], got['n'], got['otherRight'], got['otherN']) == (0, 3, 3, 0, 3)
    close = {'t': {'a': {'right': 6, 'wrong': 4}, 'b': {'right': 5, 'wrong': 5}}}
    assert pl.lead_of(close, ['t'], ['a', 'b']) is None


def test_lead_can_be_the_second_mind_and_one_mind_never_leads():
    board = {'t': {'a': {'right': 0, 'wrong': 3}, 'b': {'right': 3, 'wrong': 0}}}
    assert pl.lead_of(board, ['t'], ['a', 'b'])['i'] == 1
    assert pl.lead_of(board, ['t'], ['a']) is None


def test_pop_and_pob_records():
    cat = {'popFolders': [{'status': 'closed', 'market': 'BTC', 'side': 'long', 'roePct': 5, 'calls': [{'name': 'a', 'market': 'BTC', 'side': 'long'}, {'name': 'b', 'market': 'BTC', 'side': 'short'}]}],
           'pobFolders': [{'topic': 'lakers parlays', 'graded': 'wrong', 'calls': [{'name': 'a'}, {'name': 'b'}]}, {'topic': 'lakers', 'calls': [{'name': 'a'}]}]}
    b = pl.mind_board(cat)
    assert b['perps BTC'] == {'a': {'right': 1, 'wrong': 0}}
    assert b['lakers'] == {'a': {'right': 0, 'wrong': 1}, 'b': {'right': 0, 'wrong': 1}}   # an unmarked folder grades nobody


def test_a_proposal_or_an_open_proof_grades_nobody():
    fs = [{**_f(1, picks={'0': 0}), 'propose': True}, {**_f(1, picks={'0': 0}), 'status': 'open'}]
    assert pl.mind_board({'powFolders': fs}) == {}


def test_the_note_says_the_record():
    assert 'alpha has called 5 of 6' in pl.lead_note({'name': 'alpha', 'right': 5, 'n': 6, 'otherRight': 1, 'otherN': 6})
    assert pl.lead_note(None) == ''

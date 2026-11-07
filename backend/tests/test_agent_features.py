import agent_features as af


PAGE_ = '<!doctype html><html><head><style>a{color:red}</style></head><body><h1>One</h1><p>Two</p><script>var a=1;</script></body></html>'


def test_several_exact_edits_land_and_a_bad_one_is_dropped():
    f = af
    raw = '{"edits":[{"find":"<h1>One</h1>","replace":"<h1>Won</h1>"},{"find":"not there","replace":"x"},{"find":"<p>Two</p>","replace":"<p>Too</p>"}],"left":"the chart"}'
    page, n, left = f.apply_page_edits(PAGE_, raw)
    assert n == 2 and '<h1>Won</h1>' in page and '<p>Too</p>' in page and left == 'the chart'
    assert f.apply_page_edits(PAGE_, 'no json') == (None, 0, '') and f.apply_page_edits(PAGE_, '{"edits":[{"find":"zzz","replace":"y"}]}')[0] is None
    assert f.apply_page_edits(PAGE_, '{"find":"<p>Two</p>","replace":"<p>x</p>"}')[1] == 1   # the old one-change shape still works
    assert f.apply_page_edits(PAGE_, '{"edits":[{"find":"</html>","replace":""}]}')[0] is None   # a change that breaks the page never lands


def test_a_grown_page_is_edited_and_only_a_rebuild_is_written_whole():
    f = af
    big = 'x' * 40996
    assert not f.wants_rewrite(big, 'buttons dont work') and f.wants_rewrite(big, 'rbuild from scratch with a serious look') and f.wants_rewrite('small', 'buttons dont work')


def test_a_stopped_round_is_known_and_a_waiting_plan_is_not():
    f = af
    old = {'kind': 'build', 'pending': True, 'stage': 'review', 'busy': None, 'messages': [{'by': 'you', 'text': 'fix the buttons'}, {'by': 'Mind A', 'text': 'no'}]}
    assert f.unfinished_of(old)['ask'] == 'fix the buttons'
    assert f.unfinished_of({**old, 'busy': {'at': 1}}) is None and f.unfinished_of({**old, 'stage': 'approve'}) is None and f.unfinished_of({**old, 'pending': False, 'stage': 'filed'}) is None
    assert f.unfinished_of({'kind': 'build', 'unfinished': {'ask': 'a', 'why': 'b'}})['ask'] == 'a' and f.unfinished_of({'kind': 'content', 'pending': True, 'stage': 'build'}) is None


def test_try_again_means_the_last_ask():
    f = af
    for said in ('try last request again', 'try again', 'again', 'finish it', 'Retry', 'keep going'):
        assert f.is_retry(said), said
    for said in ('try a darker chart', 'make the buttons work again please now', 'continue the chart to the right'):
        assert not f.is_retry(said), said

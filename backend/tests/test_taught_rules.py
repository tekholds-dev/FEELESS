import opportunity as opp
import coach as co
import taught_rules as tr
import teach


def chart(up, seq, n=20, ohlc=True, lo=0.2):
    return {'state': 'UPTREND', 'f': {'n': n, 'ohlc': ohlc, 'up': up, 'seq': seq, 'loWick': lo}}


def test_fake_candles_needs_a_straight_green_run_on_real_candles():
    assert tr.fake_candles(chart(9, 'GGGGGGGG'), 8).startswith('9 green candles in a row')
    assert tr.fake_candles(chart(9, 'GGGGGGGG', lo=0.0), 8).endswith('no lower wicks')
    assert tr.fake_candles(chart(4, 'GRGGGGGG'), 8) is None                    # a red candle in the run = a real chart
    assert tr.fake_candles(chart(12, 'GGGGGGGG', ohlc=False), 8) is None       # a closes-only tape is never judged
    assert tr.fake_candles({'f': {'n': 4, 'ohlc': True, 'early': {'n': 5, 'green': 5}}}, 8) == 'all 5 candles since launch green'
    assert tr.fake_candles(None) is None


def test_same_narrative_matches_theme_name_or_ticker_stem_not_itself():
    seen = tr.recent([{'symbol': 'PUMPE', 'name': 'Pump Everything'}], [{'sym': 'GROK', 'closedAt': 900}, {'sym': 'OLD', 'closedAt': 0}], 1000, 6 / 3600 * 1000)
    assert 'PUMPE' in tr.same_narrative({'symbol': 'PUMPER', 'name': 'pumper'}, seen)
    assert 'ai narrative' in tr.same_narrative({'symbol': 'BOT', 'name': 'agent bot'}, seen)
    assert tr.same_narrative({'symbol': 'PUMPE', 'name': 'Pump Everything'}, seen) is None   # the coin itself
    assert tr.same_narrative({'symbol': 'ZZZ', 'name': 'zebra'}, seen) is None


def test_modes_drive_rank_skip_and_grading():
    rules = tr.patch(None, 'fake candles', {'mode': 'skip', 'strength': 'hard', 'run': 10})
    assert rules['fake candles'] == {'mode': 'skip', 'strength': 'hard', 'run': 10}
    assert tr.patch(rules, 'fake candles', {'run': 7})['fake candles']['run'] == 10        # not an option → unchanged
    row = {'mint': 'M', 'symbol': 'X', 'chart': chart(11, 'GGGGGGGG')}
    h = tr.hits(row, rules)
    assert list(h) == ['fake candles'] and tr.skips(rules, {'M': h}) == {'M'}
    assert tr.pens(rules)['fake candles'] == -20.0 and 'copycat' not in tr.pens(rules)    # copycat is flag-only by default
    assert 'copycat' in tr.flagged(rules)
    off = tr.patch(rules, 'fake candles', {'mode': 'off'})
    assert tr.hits(row, off) == {} and tr.skips(off, {'M': h}) == set()


def test_kernel_and_grading_read_the_stamped_row():
    row = {'taught': {'fake candles': '9 green'}}
    assert opp.judge_hits(row, {'fake candles': -12.0}) == [('lesson: fake candles', -12.0)]
    assert opp.judge_hits({}, {'fake candles': -12.0}) == []
    assert set(tr.RULES) <= set(co.CAUSES)                                                 # graded like every directive


def test_lessons_wire_rules_and_never_become_ticker_words():
    assert tr.from_text('Bought/Same narra, Stop buying fake candles.') == ['fake candles', 'same narrative']
    assert tr.from_text('Copycat narratives need to be in and out') == []                 # a scalp lesson, not an avoid
    assert tr.from_text('avoid copycats') == ['copycat']
    assert teach.words('Stop buying fake candles') == []
    st = teach.add({'rules': {'x': 1}}, {'kind': 'note', 'text': 'hello there'}, now=1)
    assert st['rules'] == {'x': 1} and teach.remove(st, 'nope')['rules'] == {'x': 1}       # the rules survive teaching


def test_view_is_plain_words():
    v = tr.view(None, {'fake candles': {'n': 12, 'med': -9.0, 'up': 3, 'verdict': 'right'}}, {'fake candles': 4}, {'fake candles': [{'sym': 'A'}]})
    r = v['rules'][0]
    assert r['label'] == 'Fake candles' and r['now'] == 4 and r['record']['verdict'] == 'right' and r['knob']['options']
    assert 'record' not in tr.view(None)['rules'][0] and 'now' not in tr.view(None)['rules'][0]           # nothing to say = nothing sent


def test_socials_report_grades_the_proof_in_plain_words():
    import social_research as sr
    assert sr.report(None)['grade'] == 'UNREAD'
    p = {'at': 900, 'website': {'url': 'https://a.fun', 'reachable': True, 'mintMatch': 'yes', 'title': 'A', 'tg': ['agroup']},
         'x': {'url': 'https://x.com/a', 'available': True, 'followers': 1200, 'lastPostAt': 1000 - 1800, 'mintMentioned': True}, 'cross': {'siteLinksX': True}}
    r = sr.report(p, now=1000)
    assert r['grade'] == 'STRONG' and [c['state'] for c in r['ch']] == ['MATCH', 'MATCH', 'FOUND']
    assert '1,200 followers' in r['ch'][1]['word'] and 'last post 30m ago' in r['ch'][1]['word'] and r['ch'][2]['url'] == 'https://t.me/agroup'
    assert sr.report({'website': {'url': 'https://b', 'reachable': True, 'mintMatch': 'no', 'mints': ['XYZabc']}, 'x': {}, 'cross': {}})['grade'] == 'CONFLICT'
    assert sr.report({'website': {}, 'x': {'url': 'https://x.com/b', 'available': False}, 'cross': {}})['grade'] == 'THIN'
    assert sr.report({'website': {}, 'x': {}, 'cross': {}})['grade'] == 'NONE'


def test_kernel_candidate_carries_the_vitals_the_panel_draws():
    from trench_kernel.kernel import vit
    v = vit({'vitals': {'top10': 33, 'bundledN': 1, 'organic': None}, 'nums': {'d5': 4.2, 'buy': 61}, 'chart': {'state': 'CHOP', 'entry': ['SKIP', 'E1', 'CHOP: no long thesis']},
             'taught': {'copycat': 'copy of a wave'}, 'waveRole': 'copy'})
    assert v['top10'] == 33 and v['entry'] == 'SKIP' and v['entryWhy'].startswith('CHOP') and v['taught'] == {'copycat': 'copy of a wave'} and v['wave'] == 'copy'
    assert 'organic' not in v and 'soc' not in v                                             # unknown stays absent, never 0

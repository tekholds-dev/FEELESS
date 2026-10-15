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
    assert tr.pens(rules)['fake candles'] == -20.0 and 'copycat' in tr.pens(rules)    # copycat is LOCKED to ✋ skip (owner, 2026-10-15)
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


def test_clone_ticker_blocks_the_fifth_mrbeast():
    rules = tr.clean(None)
    assert rules['clone']['mode'] == 'skip'                                                   # on by default: a clone is never an agent buy
    row = {'mint': 'NEW', 'symbol': 'MrBeast', 'cap': 40_000}
    assert 'already traded' in tr.hits(row, rules, traded=[('MRBEAST', 'OLD')])['clone']
    assert tr.hits(row, rules, traded=[('MrBeast', 'NEW')]) == {}                             # the same coin is not its own clone
    assert 'bigger $mr beast' in tr.clone(row, board=[{'mint': 'BIG', 'symbol': 'mr beast', 'cap': 900_000}])
    assert tr.clone(row, board=[{'mint': 'SMALL', 'symbol': 'MrBeast', 'cap': 1_000}]) is None    # it IS the original
    assert tr.skips(rules, {'NEW': {'clone': 'x'}}) == {'NEW'}
    assert tr.from_text('no way it bought mrbeast for the 8th time') == ['clone']


def test_one_bad_print_never_stops_a_seat_the_next_read_confirms():
    import office as of
    legs = [{'mint': 'A', 'pairAddress': 'PA', 'real': True, 'units': 5, 'entry': 1.0, 'at': 0, 'bought': {'tag': '🤖 agents'}}]
    pos = {'A': {'stopNow': 15}}
    prev = {'A': (997.0, 1.02)}
    assert of.fast_reap(legs, {'A': 0.5}, pos, 1000.0, prev=prev) == []                  # +2% → −50% in one read: held
    assert of.fast_reap(legs, {'A': 0.5}, pos, 1003.0, prev={'A': (1000.0, 0.5)})        # still there 3s later: a real dump, out
    assert of.fast_reap(legs, {'A': 0.8}, pos, 1000.0, prev={'A': (997.0, 0.88)})        # an ordinary step through the stop: out at once


def test_socials_report_reads_domain_age_x_age_latest_post_and_the_registry():
    import social_research as sr
    assert sr.reg_domain('https://www.app.playrex.fun/x') == 'playrex.fun' and sr.reg_domain('https://coin.co.uk') == 'coin.co.uk' and sr.reg_domain('https://x.vercel.app') is None
    d = sr.domain_read({'events': [{'eventAction': 'registration', 'eventDate': '2026-10-09T03:28:18Z'}], 'entities': [{'roles': ['registrar'], 'vcardArray': ['vcard', [['fn', {}, 'text', 'NameCheap']]]}]},
                       now=sr._iso('2026-10-14T03:28:18Z'))
    assert d == {'created': sr._iso('2026-10-09T03:28:18Z'), 'ageDays': 5.0, 'registrar': 'NameCheap'}
    p = {'website': {'url': 'https://a.fun', 'reachable': True, 'mintMatch': 'yes', 'domain': d}, 'x': {'url': 'https://x.com/a', 'available': True, 'joined': 1000 - 86400 * 400,
         'posts': [{'text': 'we are live, CA below'}], 'postUrl': 'https://x.com/a/status/1'}, 'cross': {}, 'legal': {'level': 'WEAK', 'labels': ['TERMS FOUND'], 'sources': [{'url': 'https://a.fun/terms'}]}}
    r = sr.report(p, now=1000)
    site, x, legal = r['ch'][0], r['ch'][1], r['ch'][3]
    assert site['age'] == 'domain 5d old' and site['young'] and r['flags'][0] == '⚠ website domain is only 5d old' and 'launch-week' in r['line']
    assert x['age'] == 'account 13mo old' and not x['young'] and x['post'] == 'we are live, CA below' and x['postUrl'].endswith('/1')
    assert legal['k'] == 'legal' and 'WEAK' in legal['word'] and legal['url'] == 'https://a.fun/terms'
    assert r['links'] == {'site': 'https://a.fun', 'x': 'https://x.com/a'}
    assert sr.x_read('<meta property="og:title" content="A"><div>Joined March 2025</div>', 'https://x.com/a', 'M')['joined'] > 0


def test_the_overnight_repeat_tickers_are_all_clones_of_what_the_card_traded():
    # ledger 2026-10-13/14: 18 different FOMO mints, 7 CocaCola, 5 GTA6 — every one a NEW launch wearing a ticker the card had just traded
    import taught_rules as trl
    traded = [('FOMO', 'm1'), ('CocaCola', 'm2'), ('GTA6', 'm3'), ('PEDO', 'm4'), ('MrBeast', 'm5')]
    for sym in ('FOMO', 'fomoney', 'Coca Cola', 'COCACOLA', 'GTA6 Coin', 'gta6', 'PEDO', 'MrBeast'):
        assert trl.clone({'symbol': sym, 'mint': 'new'}, traded), sym
    assert trl.clone({'symbol': 'FOMO', 'mint': 'm1'}, traded) is None        # the same coin is not its own clone
    assert trl.clone({'symbol': 'BONKERS', 'mint': 'x'}, traded) is None
    assert trl.skips(None, {'new': {'clone': 'same ticker'}}) == {'new'}      # default mode = ✋ skip


def test_copycats_are_blocked_period_sequels_and_long_memory():
    import taught_rules as tr
    assert tr.family('GTA 6', 'GT IV') and tr.family('GTA6', 'GTA5') and tr.family('FOMO', 'FOMO') and tr.family('SPACEXAI', 'SPACEX')
    assert not tr.family('AI', 'AIM') and not tr.family('DOG', 'DOGE') and not tr.family('PEPE', 'WIF')
    assert tr.clone({'symbol': 'GT IV', 'mint': 'B'}, [('GTA 6', 'A')]) is not None
    r = tr.clean({'clone': {'mode': 'off', 'hours': 24}, 'copycat': {'mode': 'flag'}})
    assert r['clone']['mode'] == 'skip' and r['clone']['hours'] == 720 and r['copycat']['mode'] == 'skip'   # locked on, a month of memory


def test_a_plain_ticker_and_its_sequel_are_one_family():
    import taught_rules as tr
    assert tr.family('GTA', 'GTA6') and tr.family('GTA6 Coin'.split()[0], 'GTA') and tr.family('GT', 'GT IV')
    assert tr.clone({'symbol': 'GTA', 'mint': 'B'}, [('GTA6', 'A')]) is not None      # 2026-10-15: $GTA bought after $GTA6
    assert not tr.family('AI', 'AIX') and not tr.family('DOG', 'DOGE')

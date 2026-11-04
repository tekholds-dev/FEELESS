"""🎲 PoB: free chips only, never its own trade, graded by the market's recorded result."""
import time
import colony
import pob


def _m(i, **kw):
    return {'id': i, 'q': f'q{i}', 'sym': i, 'crowd': 50, 'n': 1, 'locksAt': 2000, 'state': 'open', 'src': None, **kw}


def test_only_exact_words_start_it():
    for t in ('file a bid', 'PoB', '/pob', 'place a bid', 'proof of bid', 'run the pob'):
        assert pob.command(t) == 'start'
    for t in ('find best bids', 'what is a bid', 'file a bid on $BONK now'):
        assert pob.command(t) is None


def test_asking_twice_cannot_bid_twice():
    assert pob.reply(None)[0] is True
    assert pob.reply({'q': 'x'})[0] is False
    assert pob.reply(None, True)[0] is False


def test_it_never_bids_on_its_own_trade_or_a_market_about_to_lock():
    cat = {'popRun': {'id': 'p1'}, 'powFolders': [{'id': 'w1'}]}
    board = {'live': [_m('a', src='agent:p1'), _m('b', src='agent:w1'), _m('c', locksAt=1050), _m('d', mine={'side': 'yes'}), _m('e')]}
    assert [m['id'] for m in pob.choices(board, cat, 1000)] == ['e']


def test_a_call_must_name_a_listed_market():
    assert pob.parse_call('{"market":"e","side":"YES","why":"up 40%"}', {'e'}) == {'market': 'e', 'side': 'yes', 'why': 'up 40%'}
    assert pob.parse_call('{"market":"z","side":"yes"}', {'e'}) is None
    assert pob.parse_call('{"market":"e","side":"none"}', {'e'}) is None
    assert pob.parse_call('garbage', {'e'}) is None


def test_both_minds_must_agree():
    a, b = {'market': 'e', 'side': 'yes'}, {'market': 'e', 'side': 'no'}
    assert pob.agree([a, dict(a)])[0] == {'market': 'e', 'side': 'yes'}
    assert pob.agree([a, b])[0] is None
    assert pob.agree([a, None])[0] is None
    assert pob.agree([a])[0] == {'market': 'e', 'side': 'yes'}


def test_the_market_grades_it():
    run = {'id': 'x', 'side': 'yes', 'chips': 50, 'checkedAt': 1}
    assert pob.settle(run, {'state': 'open'}, 5) is None
    assert pob.settle(run, None, 5) is None
    won = pob.settle(run, {'state': 'settled', 'result': 'yes', 'mine': {'paid': 90}}, 5)
    assert won['won'] is True and won['net'] == 40 and 'checkedAt' not in won and pob.report(won)['grade'] == 'GOOD BID'
    lost = pob.settle(run, {'state': 'settled', 'result': 'no', 'mine': {'paid': 0}}, 5)
    assert lost['won'] is False and lost['net'] == -50 and pob.report(lost)['grade'] == 'BAD BID'
    void = pob.settle(run, {'state': 'settled', 'result': 'void', 'mine': {'paid': 50}}, 5)
    assert void['void'] is True and 'won' not in void and pob.report(void)['grade'] == 'VOID'


def test_a_placed_pob_can_go_with_honey_once():
    cat = {'id': 'c', 'pobFolders': [{'id': 'b1', 'n': 1, 'status': 'closed', 'won': True, 'at': 5}, {'id': 'b2', 'noTrade': True}, {'id': 'b3', 'void': True}]}
    assert [r['id'] for r in colony.proofs_of(cat, [])] == ['b1']
    assert colony.attach_of(cat, [], 'b1', '')['proof']['kind'] == 'PoB'
    assert colony.proofs_of(cat, [{'cat': 'c', 'proof': {'id': 'b1'}}])[0]['used'] is True


def test_the_board_stake_never_earns_points_and_stays_chips():
    import rep_markets as repm
    now = time.time(); st = {}
    m = repm.make('up', 'mint', 'SOL', 1.0, now); st['markets'] = [m]
    repm.stake(st, 'agent:c', m['id'], 'yes', pob.STAKE, now, 50)
    assert repm.bank(st, 'agent:c', now)['chips'] == repm.CHIPS_WEEK - pob.STAKE
    assert repm.view(m, now, 'agent:c')['mine']['chips'] == pob.STAKE



def test_topic_words():
    from pob import topic_of, sites_for
    assert topic_of('file a pob best choices for nfl bidding') == 'best choices for nfl bidding'
    assert topic_of('file a nfl bid') == 'nfl'
    assert topic_of('file a bid on who wins the election?') == 'who wins the election'
    assert topic_of('file a bid') is None and topic_of('file a pob') is None and topic_of('what is a bid') is None
    assert 'espn.com' in sites_for('nfl') and 'kalshi.com' in sites_for('nfl') and 'apnews.com' in sites_for('election') and 'reuters.com' in sites_for('weather')


def test_picks_are_parsed_and_only_real_overlap_counts():
    from pob import parse_picks, agreed
    a = parse_picks('{"picks":[{"pick":"Chiefs -3","confidence":70,"why":"espn"},{"pick":"Over 44","confidence":250,"why":"x"}]}')
    b = parse_picks('{"picks":[{"pick":"chiefs -3","confidence":60,"why":"covers"}]}')
    assert a['picks'][1]['confidence'] == 100 and agreed([a, b]) == ['Chiefs -3'] and agreed([a]) == []
    assert parse_picks('no json') == {'picks': [], 'pass': 'no usable answer'}


def test_a_topic_report_says_nothing_was_staked_and_the_owner_marks_it():
    from pob import report
    r = report({'status': 'closed', 'topic': 'nfl', 'agreed': ['a']})
    assert r['grade'] == 'RESEARCH' and 'No chips staked' in r['lesson'] and report({'status': 'closed', 'topic': 'nfl', 'graded': 'right'})['grade'] == 'GOOD CALL'

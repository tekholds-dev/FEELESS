"""🛒 Trading on its own site account, and 🔁 the Proof Loop. No network, no money."""
import agent_site_trade as st
import proof_loop as pl

SIGNED = {'pump.fun', 'stake.us'}
NOW = 2_000_000_000
GOOD = {'mint': 'M' * 44, 'sym': 'BONK', 'pool': 80_000.0, 'ageS': 90_000, 'run1h': 4.0}


def test_order_words():
    assert st.parse('buy $1 of $BONK on pump', SIGNED) == {'side': 'buy', 'usd': 1.0, 'coin': '$BONK', 'site': 'pump.fun'}
    assert st.parse('buy $1.50 worth of BONK on pump.fun', SIGNED)['usd'] == 1.5
    assert st.parse('sell all $BONK on pump', SIGNED)['pct'] == 100
    assert st.parse('sell 50% of $BONK on pump', SIGNED)['pct'] == 50
    assert st.parse('sell $BONK on pump', SIGNED)['pct'] == 100


def test_only_a_signed_in_site_and_only_order_words():
    assert st.parse('buy $1 of $BONK on axiom', SIGNED) is None
    assert st.parse('buy 0.01 SOL of $JUP', SIGNED) is None      # that door is FEELESS's own
    assert st.parse('what should I buy on pump', SIGNED) is None
    assert st.parse('buy 1 of BONK on pump', SIGNED) is None     # dollars only: a slip never means a coin count


def test_buy_guards_stop_and_a_sell_always_gets_out():
    o = {'side': 'buy', 'usd': 1.0, 'coin': 'BONK', 'site': 'pump.fun'}
    assert st.why_not(o, GOOD, [], NOW) == ''
    assert 'pool' in st.why_not(o, {**GOOD, 'pool': 500.0}, [], NOW)
    assert 'minutes old' in st.why_not(o, {**GOOD, 'ageS': 30}, [], NOW)
    assert 'minutes old' in st.why_not(o, {**GOOD, 'ageS': None}, [], NOW)
    assert 'already ran' in st.why_not(o, {**GOOD, 'run1h': 900.0}, [], NOW)
    assert '$0.50' in st.why_not({**o, 'usd': 26.0}, GOOD, [], NOW)
    assert 'find' in st.why_not(o, {**GOOD, 'mint': ''}, [], NOW)
    assert st.why_not({'side': 'sell', 'pct': 100, 'coin': 'BONK', 'site': 'pump.fun'}, {**GOOD, 'pool': 1.0, 'ageS': 1, 'run1h': 9000.0}, [], NOW) == ''


def test_day_caps():
    o = {'side': 'buy', 'usd': 5.0, 'coin': 'BONK', 'site': 'pump.fun'}
    many = [{'side': 'buy', 'usd': 1.0, 'at': NOW - 60, 'state': 'confirmed'}] * st.DAY_BUYS
    assert 'cap' in st.why_not(o, GOOD, many, NOW)
    big = [{'side': 'buy', 'usd': 24.0, 'at': NOW - 60, 'state': 'confirmed'}] * 2
    assert 'cap' in st.why_not({**o, 'usd': 5.0}, GOOD, big, NOW)
    old = [{'side': 'buy', 'usd': 24.0, 'at': NOW - 90_000, 'state': 'confirmed'}] * 9
    assert st.why_not(o, GOOD, old, NOW) == ''
    failed = [{'side': 'buy', 'usd': 24.0, 'at': NOW - 60, 'state': 'failed'}] * 9
    assert st.why_not(o, GOOD, failed, NOW) == ''


def test_goal_is_one_order_and_forbids_the_rest():
    c = st.card({'side': 'buy', 'usd': 1.0, 'coin': 'BONK', 'site': 'pump.fun'}, GOOD, NOW)
    g = st.goal(c, 'W' * 44)
    assert GOOD['mint'] in g and '$1.00' in g and 'no withdrawal' in g and 'no export' in g and 'wallet address' not in g
    assert 'wallet address' in st.goal(c, '')


def test_the_chain_settles_it_and_silence_is_not_success():
    c = st.card({'side': 'buy', 'usd': 1.0, 'coin': 'BONK', 'site': 'pump.fun'}, GOOD, NOW)
    r = st.row(c, 'W' * 44, 0.0, 'Bought', NOW)
    assert r['state'] == 'checking'
    assert st.settle(dict(r), 0.0, NOW + 30)['state'] == 'checking'
    assert st.settle(dict(r), 120.0, NOW + 30)['state'] == 'confirmed'
    assert st.settle(dict(r), 0.0, NOW + st.GIVE_UP_S)['state'] == 'failed'
    assert st.settle(dict(r), None, NOW + st.GIVE_UP_S)['state'] == 'failed'
    sold = st.row(st.card({'side': 'sell', 'pct': 100, 'coin': 'BONK', 'site': 'pump.fun'}, GOOD, NOW), 'W' * 44, 120.0, 'Sold', NOW)
    assert st.settle(dict(sold), 0.0, NOW + 30)['state'] == 'confirmed'
    assert st.settle(dict(sold), 500.0, NOW + st.GIVE_UP_S)['state'] == 'failed'
    assert st.row(c, '', None, 'Bought', NOW)['state'] == 'unverified'
    assert 'chain confirms' in st.saying({**r, 'state': 'confirmed', 'after': 120.0})
    assert "can't check" in st.saying({**r, 'state': 'unverified'})


COIN = {'mint': 'A', 'src': 'pump', 'liq': 30_000, 'mc': 200_000, 'ch': 40}
FOLDER = {'status': 'closed', 'n': 4, 'sym': 'DOG', 'mint': 'A', 'pnlSol': -0.01, 'pnlPct': -18.0, 'why': 'stop', 'coins': [COIN]}


def test_a_new_coin_shaped_like_a_loss_is_caught():
    lost = pl.losers([FOLDER])
    same_shape = {'mint': 'B', 'src': 'pump', 'liq': 35_000, 'mc': 300_000, 'ch': 90}
    assert pl.repeat_of(same_shape, lost)['n'] == 4
    assert pl.repeat_of({**same_shape, 'liq': 300_000}, lost) is None
    assert pl.repeat_of({**same_shape, 'src': 'dex'}, lost) is None
    assert pl.repeat_of({**same_shape, 'ch': -30}, lost) is None


def test_a_win_or_an_unbought_proposal_is_no_loss():
    assert pl.losers([{**FOLDER, 'pnlSol': 0.01}]) == {}
    assert pl.losers([{**FOLDER, 'propose': True}]) == {}
    assert pl.losers([{**FOLDER, 'status': 'open'}]) == {}
    assert pl.losers([{**FOLDER, 'pnlSol': None}]) == {}


def test_pow_loop_counts_and_note():
    loop = pl.pow_loop([FOLDER, {**FOLDER, 'n': 5, 'pnlSol': 0.02, 'pnlPct': 30.0}], [{'sym': 'X', 'like': '#4 $DOG'}, {'sym': 'Y'}])
    assert (loop['n'], loop['wins'], loop['losses']) == (3, 1, 1)
    assert loop['past'][0]['n'] == 5 and loop['skipped'] == [{'sym': 'X', 'like': '#4 $DOG'}]
    assert '$DOG -18.0%' in pl.pow_note([FOLDER])
    assert pl.pow_note([]) == ''


def test_one_topic_keeps_one_series():
    assert pl.same_topic('lakers parlays', 'best lakers picks tonight')
    assert not pl.same_topic('lakers parlays', 'best nfl picks')
    assert not pl.same_topic('best picks', 'best parlays tonight')   # generic betting words name nothing
    rows = [{'topic': 'lakers parlays', 'n': 1, 'agreed': ['Lakers ML'], 'graded': 'wrong'}, {'topic': 'nfl week 9', 'n': 2, 'agreed': ['Chiefs']}, {'topic': 'lakers tonight', 'n': 3, 'noTrade': True}]
    loop = pl.bid_loop(rows, 'keep bidding lakers parlays')
    assert (loop['n'], loop['wrong'], loop['right']) == (2, 1, 0) and loop['past'][0]['picks'] == ['Lakers ML']
    note = pl.bid_note(loop)
    assert 'loop 2' in note and 'marked it wrong' in note and 'new evidence' in note
    assert pl.bid_note(pl.bid_loop(rows, 'mma')) == ''


def test_perp_loop():
    rows = [{'status': 'closed', 'n': 1, 'market': 'SOL', 'side': 'long', 'roePct': -12.0, 'why': 'stop'}, {'status': 'closed', 'noTrade': True}, {'status': 'closed', 'n': 2, 'market': 'BTC', 'side': 'short', 'roePct': 8.0}]
    loop = pl.perp_loop(rows)
    assert (loop['n'], loop['wins'], loop['losses']) == (3, 1, 1)
    assert 'SOL long -12.0%' in pl.perp_note(loop)

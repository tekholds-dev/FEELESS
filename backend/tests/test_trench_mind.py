import trench_mind as tm
import agents as ag


def test_slang_words_and_narratives():
    assert 'early' in tm.words('Early tek 🫵 $QI #81 https://x.com/a') and 'qi' not in tm.words('$QI')   # tickers / links / numbers out
    assert 'paperhands' in tm.words('paper hands everywhere')                                         # "paper hands" → the slang key
    assert tm.narrative({'name': 'Grok Agent', 'symbol': 'GAGENT'})[0] == 'ai'
    assert tm.narrative({'symbol': 'Pumpoween'})[0] == 'holiday' and tm.narrative({'symbol': 'XYZQ'}) == (None, None)
    assert tm.narrative({'symbol': 'GTA6', 'name': 'GTA 6'})[0] == 'game'
    assert not {'good', 'like', 'because', 'coins'} & set(tm.words('good coins because like'))   # plain English is never "slang"
    hot = tm.hot_narratives([{'symbol': 'DOGX', 'name': 'doge two', 'vol1h': 5e4}, {'symbol': 'AIX', 'name': 'ai agent', 'vol1h': 2e5}])
    assert list(hot)[0] == 'ai'


def test_a_copy_paste_swarm_is_not_a_crowd():
    bots = [f'BOTS TAKEOVER is live. you are on our page now. $BOTS #{8100 + i}' for i in range(8)] + ['Sums it up']
    sw, share = tm.swarm(bots)
    assert sw and share >= 0.8
    real = ['early tek', 'dev is based, cto incoming', 'chart is cooking', 'send it', 'gem before the bond']
    assert not tm.swarm(real)[0]
    c = tm.crowd([{'user': f'u{i}', 'thesis': t} for i, t in enumerate(real)])
    assert c['callers'] == 5 and not c['swarm'] and c['hype'] >= 3 and {'early', 'tek'} & set(c['slang'])


def test_botted_launch_and_dip_tuggers():
    s, why = tm.bots({'vital': {'organicPct': 2}, 'bundledN': 5, 'txns1h': 4000, 'vol1h': 20000})
    assert s >= 70 and any('organic' in w for w in why) and any('micro-buys' in w for w in why)
    assert tm.bots({'vital': {'organicPct': 40}, 'bundledN': 0})[0] == 0
    assert tm.dip_tug({'chg1h': -40, 'buyShare': 58})[0] and not tm.dip_tug({'chg1h': -40, 'buyShare': 40})[0]


def test_it_learns_new_slang_from_humans_and_ignores_swarm_copies():
    st = {}
    for day in range(3):
        st = tm.learn_lingo(st, ['this is so zoinked', 'zoinked again lol', 'zoinked'] + ['BOTS TAKEOVER blorp $BOTS #1', 'BOTS TAKEOVER blorp $BOTS #2'] * 20, day * 86400)
    assert 'zoinked' in st['learned'] and 'blorp' not in st['learned']                 # 40 bot copies count once a day → never "slang"
    assert 'early' not in st['learned']                                                # dictionary words are known, not learned


def test_the_desk_reads_humans_in_its_drivers_its_argument_and_a_real_analysis_with_humor():
    swarm_calls = [{'user': f'b{i}', 'thesis': f'the bots are here. every page. $BOTS #{i}'} for i in range(8)]
    row = {'mint': 'B', 'symbol': 'BOTS', 'pairAddress': 'PB', 'price': 1.0, 'vol5m': 20_000, 'vol1h': 80_000, 'buyShare': 64, 'liq': 60_000, 'ageH': 8,
           'chg1h': 30, 'safe': True, 'tv': {'call': ['🔥', 'SEND IT', 'good'], 'rug': 10}, 'bundledN': 4, 'vital': {'organicPct': 2}, 'name': 'bot army ai'}
    row['mind'] = tm.read(row, swarm_calls, {'ai': {}})
    assert set(row['mind']['drivers']) >= {'narr:ai', 'narr_hot', 'swarm', 'botted'}
    st = {}
    for t in (0, 60, 120):
        st, table = ag.desk(st, [row], t)
    x = table[0]
    assert x['trigger'][0] != 'enter' or x['devil'][0] == 'object'                     # a botted swarm never gets a clean GO
    assert not x['go']
    a = x['analysis']
    assert 'AI' in a['text'] and 'swarm' in a['text'] and 'Botted launch' in a['text']
    assert set(a['jokes']) == {'tally', 'sherlock', 'trigger', 'devil'} and all(a['jokes'].values())
    assert any(l['who'] == 'desk' and l['text'].startswith('✍') for l in st['feed'])
    assert tm.quip('devil', 'object', 'X') == tm.quip('devil', 'object', 'X')         # stable per coin — no flicker

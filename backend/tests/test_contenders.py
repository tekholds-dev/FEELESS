"""🏁 Arena contenders: every pick list is a division, coins are scored on live facts, the best coin not on a card is next up."""
import contenders as ct

RUN = lambda m, age, chg, sc=80, bs=65, vol=40_000: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m.upper(), 'price': 1, 'ageH': age, 'chg1h': chg, 'score': sc, 'buyShare': bs, 'vol1h': vol, 'liq': 30_000}
POOL = lambda m, liq, vol, chg=5, apr=200: {'baseAddress': m, 'pairAddress': 'P' + m, 'symbol': m.upper(), 'priceUsd': 1, 'liquidityUsd': liq, 'volume24h': vol, 'change24h': chg, 'aprEst': apr, 'buyShare': 55}


def test_runners_split_by_age_and_must_be_pumping():
    lg = ct.league({'fresh': [RUN('a', 2, 120), RUN('b', 3, -5), RUN('c', 20, 60)], 'proven': [RUN('a', 2, 120), RUN('c', 20, 60), RUN('d', 30, 40, bs=50)]})
    by = {d['key']: [r['mint'] for r in d['rows']] for d in lg['divisions']}
    assert by['fresh'] == ['a']        # b is red over the hour · c is too old for the fresh division
    assert by['proven'] == ['c']       # a is too young · d has no buyers in control


def test_best_coin_not_on_a_card_is_next_up_and_a_coin_takes_one_seat_only():
    src = {'popular': [POOL('x', 2e6, 9e6), POOL('y', 1e6, 4e6), POOL('z', 5e5, 1e6)], 'deep': [POOL('y', 1e6, 4e6), POOL('x', 2e6, 9e6)]}
    lg = ct.league(src, on_card={'x'})
    pop = next(d for d in lg['divisions'] if d['key'] == 'popular'); deep = next(d for d in lg['divisions'] if d['key'] == 'deep')
    # 🌊 deep is seated first: y takes ITS next-up seat there, so popular's next seat goes to the next coin down (z) — one seat per coin
    assert deep['nextUp'] == 'y' and [(r['mint'], r['seat']) for r in pop['rows']] == [('x', 'card'), ('y', ''), ('z', 'next')]
    assert lg['nextUp'] == {'y': 'deep', 'z': 'popular'}
    assert all(0 <= r['score'] <= 100 and r['parts'] for r in pop['rows'])   # every point is cited


def test_rank_moves_and_top_streak_come_from_the_league_before():
    first = ct.league({'popular': [POOL('x', 2e6, 9e6), POOL('y', 1e6, 4e6)]})
    second = ct.league({'popular': [POOL('x', 2e6, 9e6), POOL('y', 1e6, 4e6), POOL('n', 3e6, 2e7)]}, prev=first)
    rows = {r['mint']: r for r in next(d for d in second['divisions'] if d['key'] == 'popular')['rows']}
    assert rows['n']['move'] == 'new' and rows['n']['rank'] == 1 and rows['n']['streak'] == 1
    assert rows['x']['move'] == 'down' and rows['x']['streak'] == 0
    third = ct.league({'popular': [POOL('n', 3e6, 2e7), POOL('x', 2e6, 9e6)]}, prev=second)
    assert next(d for d in third['divisions'] if d['key'] == 'popular')['rows'][0]['streak'] == 2


def test_thin_or_priceless_pools_never_enter_and_anchors_rank_by_volume():
    lg = ct.league({'yield': [POOL('thin', 10_000, 5e6, apr=9000), POOL('ok', 80_000, 2e6, apr=900)],
                    'majors': [POOL('sol', 3e7, 4e8), POOL('btc', 2e6, 5e6)], 'popular': [{**POOL('dead', 1e6, 1e6), 'priceUsd': 0}]})
    by = {d['key']: [r['mint'] for r in d['rows']] for d in lg['divisions']}
    assert by['yield'] == ['ok'] and by['majors'] == ['sol', 'btc'] and by['popular'] == []
    assert ct.league({'deep': [{**POOL('u', 9e7, 9e7), 'symbol': 'ERC20-USDC'}]})['divisions'][3]['rows'] == []   # dollar coins never compete

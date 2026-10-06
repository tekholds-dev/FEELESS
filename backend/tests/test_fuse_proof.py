import fuse_proof as fp

NOW = 2_000_000.0
row = lambda side, sym, at, **k: {'card': 'degen', 'side': side, 'symbol': sym, 'mint': 'M' + sym, 'pair': 'P' + sym, 'at': at, 'sig': f'sig{sym}{int(at)}', 'status': 'filled', 'usd': 1.0, **k}
LEDGER = [row('buy', 'SK', NOW - 5000),
          row('sell', 'SK', NOW - 3000, costUsd=0.5, realizedPnlUsd=0.25, why=fp.TRIM),          # a profit take: +50%
          row('sell', 'SK', NOW - 2000, costUsd=0.5, realizedPnlUsd=0.05, why=fp.TRIM),
          row('sell', 'DOG', NOW - 1000, costUsd=1.0, realizedPnlUsd=-0.2, why=fp.EXIT),         # a full exit: −20%
          {**row('sell', 'BAD', NOW - 900), 'status': 'failed'},                                 # never landed → never shown
          {**row('buy', 'NOSIG', NOW - 800), 'sig': None},
          {**row('sell', 'OLD', NOW - 90_000, costUsd=1, realizedPnlUsd=1)},                     # older than the feed's 24h
          {**row('buy', 'PAPER', NOW - 100), 'card': 'gold'}]                                    # not a real card
CARD = {'tpl': 'degen', 'label': '🔥 Prime Blaze', 'real': True, 'math': {'putIn': 10.0, 'nowUsd': 9.0, 'pnlUsd': -0.8, 'feesUsd': 0.2},
        'events': [{'at': NOW - 3010, 'kind': 'skim', 'symbol': 'SK', 'why': '💰 profit of $SK taken, its stake keeps riding'},
                   {'at': NOW - 1005, 'kind': 'sl', 'symbol': 'DOG', 'why': '-20% ≤ −15%', 'to': ['CAT']}]}


def test_the_feed_is_only_confirmed_swaps_of_real_cards_with_the_engines_reason_and_the_tx():
    f = fp.feed([CARD, {'tpl': 'gold', 'label': 'Gold'}], LEDGER, NOW)
    assert [x['symbol'] for x in f] == ['DOG', 'SK', 'SK', 'SK']                    # newest first; failed / unsigned / paper / day-old rows are out
    assert f[0]['pct'] == -20.0 and f[0]['why'] == '-20% ≤ −15%' and f[0]['sig'] == 'sigDOG1999000'
    assert f[2]['pct'] == 50.0 and 'stake keeps riding' in f[2]['why']             # the card's own words, matched by coin + time
    cat = fp.feed([CARD], [row('buy', 'CAT', NOW - 1000)], NOW)[0]
    assert cat['why'] == 'in for $DOG: -20% ≤ −15%'                               # a buy is explained by the swap that brought it in
    assert f[1]['why'] == fp.TRIM and f[3]['pct'] is None                           # no event near → the keeper's reason; a buy has no result


def test_a_real_cards_record_is_counted_from_its_own_ledger_and_shows_a_loss_as_a_loss():
    r = fp.record(CARD, LEDGER, NOW)
    assert r['putIn'] == 10.0 and r['nowUsd'] == 9.0 and r['pct'] == -8.0 and r['swaps'] == 5
    assert r['closed'] == 4 and r['wonPct'] == 75
    assert r['takes'] == {'n': 2, 'usd': 0.3, 'wonPct': 100} and r['exits']['n'] == 2 and r['exits']['wonPct'] == 50
    assert r['best'] == {'symbol': 'OLD', 'pct': 100}
    s = fp.setups([{'key': 'rhunt', 'name': '🚀 Runner hunt', 'why': 'w', 'profitable': True, 'windows': 11, 'medPct': 6.7, 'upPct': 82, 'worstPct': -9.9, 'hours': 6},
                   {'key': 'x', 'name': 'X', 'medPct': 9.0, 'profitable': False}], [r], {'degen': {'sl': 15}})
    assert [x['key'] for x in s] == ['rhunt', 'x', 'real:degen']                    # proven first; the losing real card is NOT proven and sits last
    assert s[0]['source'] == 'replay' and s[2]['source'] == 'real' and s[2]['proven'] is False and s[2]['cfg'] == {'sl': 15} and s[2]['medPct'] == -8.0


def test_why_bought_keeps_what_the_coin_looked_like_at_the_buy():
    w = fp.why_bought({'chg1h': 31.26, 'vol1h': 82000, 'ageH': 14.04, 'buyShare': 63, 'liquidity': {'usd': 51000}}, '🧲 dip bought, trend up')
    assert w == {'tag': '🧲 dip bought, trend up', 'chg1h': 31.3, 'vol1h': 82000.0, 'ageH': 14.0, 'buyShare': 63.0, 'liq': 51000}
    assert fp.why_bought({})['chg1h'] is None


def test_a_real_card_duels_the_best_other_card_for_24h_on_percent_only():
    vals = {'prime:degen': 10.0, 'prime:gold': 20.0, 'prime:next': 20.0}
    st = fp.duel_step({}, vals, {'prime:degen': 'Blaze', 'prime:gold': 'Gold'}, ['prime:degen'], ['prime:gold', 'prime:next'], NOW)
    assert len(st['live']) == 1 and st['live'][0]['b'] == 'prime:gold' and st['live'][0]['aStart'] == 10.0
    assert fp.duel_step(st, vals, {}, ['prime:degen'], ['prime:next'], NOW + 3600)['live'] == st['live']        # one duel at a time; it runs its 24h
    v = fp.duel_view(st, {'prime:degen': 11.0, 'prime:gold': 21.0}, NOW + 3600)
    assert v['live'][0]['aPct'] == 10.0 and v['live'][0]['bPct'] == 5.0 and v['live'][0]['leader'] == 'prime:degen' and v['hours'] == 24
    end = fp.duel_step(st, {'prime:degen': 11.0, 'prime:gold': 21.0, 'prime:next': 20.0}, {}, ['prime:degen'], ['prime:gold'], NOW + fp.DUEL_SEC + 1)
    assert end['log'][-1]['winner'] == 'prime:degen' and end['rec']['prime:degen'] == {'w': 1, 'l': 0, 'd': 0} and end['rec']['prime:gold']['l'] == 1
    assert len(end['live']) == 1 and end['live'][0]['at'] == NOW + fp.DUEL_SEC + 1                                # the next duel opens at once
    off = fp.duel_step(st, vals, {}, ['prime:degen'], ['prime:gold'], NOW + 60, pick={'prime:degen': 'prime:next'})   # the owner picks the challenger
    assert off['live'][0]['b'] == 'prime:next' and off['log'] == [] and off['rec'] == {}                         # the old duel is called off with no result
    gone = fp.duel_step(st, {'prime:degen': 10.0, 'prime:gold': 0.0, 'prime:next': 5.0}, {}, ['prime:degen'], ['prime:gold', 'prime:next'], NOW + 99)
    assert gone['live'][0]['b'] == 'prime:next' and gone['rec'] == {}                                             # a closed card = no result either
    draw = fp.duel_step(st, {'prime:degen': 10.5, 'prime:gold': 21.05}, {}, [], [], NOW + fp.DUEL_SEC + 1)
    assert draw['log'][-1]['winner'] is None and draw['rec']['prime:degen']['d'] == 1

import whos_in as wi


def _t(side, tokens, pool, ts, token='M'):
    return {'side': side, 'tokens': tokens, 'poolUsd': pool, 'fillPrice': pool / tokens, 'ts': ts, 'token': token, 'tx': f'x{ts}'}


def test_feeless_traders_rank_by_first_verified_buy_with_in_out_and_result():
    tr = {'W1': [_t('buy', 100, 1, 100), _t('sell', 100, 3, 200)],      # early, out, +200%
          'W2': [_t('buy', 100, 1, 50)],                                  # earliest, still in
          'W3': [_t('buy', 100, 1, 10, token='OTHER')]}                   # a different coin: not here
    rows = wi.feeless_traders(tr, 'M')
    assert [(r['address'], r['rank'], r['in']) for r in rows] == [('W2', 1, True), ('W1', 2, False)]
    assert rows[1]['ret'] == 2.0 and rows[1]['usd'] == 2.0 and rows[0]['ret'] is None          # no closed piece → no result invented


def test_holders_are_tagged_from_the_coins_own_forensics():
    top = [{'owner': 'POOL', 'pct': 40, 'kind': 'program'}, {'owner': 'DEV', 'pct': 6, 'kind': 'wallet'}, {'owner': 'SNP', 'pct': 3}, {'owner': 'B1', 'pct': 2}, {'owner': 'OK', 'pct': 1}, {'pct': 1}]
    rows = wi.tag_holders(top, creator='DEV', snipers=['SNP'], bundled=['B1', 'SNP'], flagged=['OK'], names={'OK': 'alice'})
    assert [(r['name'] if r['address'] == 'OK' else r['address'], r['tags']) for r in rows] == [('POOL', ['pool']), ('DEV', ['dev']), ('SNP', ['sniper', 'bundled']), ('B1', ['bundled']), ('alice', ['flagged'])]
    assert wi.verdict(rows) == {'risky': 4, 'wallets': 4}


def test_badge_art_only_for_quest_badges():
    assert wi.badge_art('q-trader') == '/assets/badges/feeless/trader' and wi.badge_art('frsv-x') == '/assets/badges/frsv/x'
    assert wi.badge_art('fee-whale') is None and wi.badge_art(None) is None

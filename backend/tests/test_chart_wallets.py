import chart_wallets as cw


def test_every_trade_is_tagged_from_records_we_hold_never_a_guess():
    trades = [{'ts': '2026-10-18T16:00:00Z', 'kind': 'buy', 'usd': 40, 'price': 1, 'wallet': 'SNIPE'},
              {'ts': '2026-10-18T16:01:00Z', 'kind': 'sell', 'usd': 900, 'price': 1, 'wallet': 'WHALE'},
              {'ts': '2026-10-18T16:02:00Z', 'kind': 'buy', 'usd': 20, 'price': 1, 'wallet': 'DEV'}] + \
             [{'ts': '2026-10-18T16:03:00Z', 'kind': 'buy', 'usd': 10, 'price': 1, 'wallet': f'R{i}'} for i in range(6)]
    out = cw.tag_trades(trades, {'sniperWallets': ['SNIPE'], 'bundledWallets': [], 'creator': 'DEV', 'topHolders': [{'owner': 'WHALE'}]})
    by = {t['w']: t['tags'] for t in out['trades']}
    assert 'sniper' in by['SNIPE'] and 'dev' in by['DEV'] and {'whale', 'holder', 'top'} <= set(by['WHALE'])
    assert out['counts']['whale'] == 1 and out['top'][0]['w'] == 'WHALE'
    assert cw.tag_trades([], None) == {'trades': [], 'counts': {}, 'top': []}
    assert all('sniper' not in t['tags'] for t in cw.tag_trades(trades, None)['trades'])   # no launch read → no sniper tags

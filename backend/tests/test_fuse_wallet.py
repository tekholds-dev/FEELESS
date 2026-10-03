import fuse_wallet as fw

SOL = fw.SOL_MINT
CFG = {**fw.DEFAULT_CFG, 'walletId': 'w1', 'address': 'OWNER', 'armed': True}


def card(legs, **kw):
    return {'id': 'prime-degen', 'tpl': 'degen', 'legs': legs, 'cash': 0.0, 'events': [], 'startUsd': 100.0, **kw}


def leg(mint, pair, units, entry, role='runner'):
    return {'mint': mint, 'pairAddress': pair, 'symbol': mint[:4], 'units': units, 'entry': entry, 'role': role}


def test_clean_cfg_clamps_and_defaults_off():
    c = fw.clean_cfg({'maxSwapUsd': 99999, 'slippageBps': 5, 'armed': 1, 'walletId': ' abc '})
    assert c['maxSwapUsd'] == 10000 and c['slippageBps'] == 10 and c['armed'] is True and c['walletId'] == 'abc'
    assert fw.clean_cfg({})['armed'] is False and fw.clean_cfg({})['paused'] is False


def test_orders_buy_the_card_from_sol_and_skip_the_sol_anchor():
    book = fw.new_book(100, 200.0, 0)          # 0.5 SOL
    c = card([leg(SOL, 'solpair', 0.1, 200, 'anchor'), leg('MINTA', 'pa', 40, 1.0), leg('MINTB', 'pb', 400, 0.1)])
    o = fw.orders('degen', c, book, {'solpair': 200, 'pa': 1.0, 'pb': 0.1}, 200.0, CFG, 10)
    assert [x['side'] for x in o] == ['buy', 'buy'] and {x['mint'] for x in o} == {'MINTA', 'MINTB'}
    assert all(x['usd'] <= CFG['maxSwapUsd'] for x in o)
    # never spends the SOL the anchor needs: 0.5 SOL − 0.1 anchor = 0.4 SOL = $80 for buys
    assert sum(x['usd'] for x in o) <= 80.01


def test_orders_sell_coins_that_left_the_card_first():
    book = {'sol': 0.0, 'legs': {'OLD': {'atoms': 5_000_000, 'decimals': 6, 'pair': 'po', 'symbol': 'OLD', 'entryPx': 1.0}}}
    c = card([leg('NEW', 'pn', 5, 1.0)])
    o = fw.orders('degen', c, book, {'po': 1.0, 'pn': 1.0}, 200.0, CFG, 10)
    assert o[0]['side'] == 'sell' and o[0]['atoms'] == 5_000_000 and o[0]['why'] == 'not on the card any more'


def test_sell_is_capped_per_swap():
    book = {'sol': 0.0, 'legs': {'BIG': {'atoms': 200_000_000, 'decimals': 6, 'pair': 'pb', 'symbol': 'BIG', 'entryPx': 1.0}}}
    o = fw.orders('degen', card([]), book, {'pb': 1.0}, 200.0, {**CFG, 'maxSwapUsd': 50}, 1)
    assert o[0]['atoms'] == 50_000_000 and o[0]['usd'] == 50


def test_check_blocks_unarmed_paused_over_caps_and_impact():
    o = {'usd': 10}
    assert fw.check(o, {**CFG, 'armed': False}, [], 0)[0] is False
    assert fw.check(o, {**CFG, 'paused': True}, [], 0)[0] is False
    assert fw.check({'usd': 60}, CFG, [], 0)[0] is False
    led = [{'status': 'filled', 'usd': 295, 'at': 0}]
    assert 'daily cap' in fw.check(o, CFG, led, 100)[1]
    assert fw.check(o, CFG, led, 90000)[0] is True            # yesterday's spend rolled off
    assert 'impact' in fw.check(o, CFG, [], 0, quote_impact_pct=5)[1]


def tx(owner, mint, pre, post, sol_pre, sol_post, fee=5000, err=None):
    return {'meta': {'err': err, 'fee': fee, 'preBalances': [sol_pre], 'postBalances': [sol_post],
                     'preTokenBalances': [{'owner': owner, 'mint': mint, 'uiTokenAmount': {'amount': str(pre), 'decimals': 6}}] if pre is not None else [],
                     'postTokenBalances': [{'owner': owner, 'mint': mint, 'uiTokenAmount': {'amount': str(post), 'decimals': 6}}]},
            'transaction': {'message': {'accountKeys': [{'pubkey': owner, 'signer': True}]}}}


def test_fill_from_meta_reads_the_true_fill_and_network_fee():
    f = fw.fill_from_meta(tx('OWNER', 'M', None, 2_000_000, 1_000_000_000, 899_995_000), 'OWNER', 'M')
    assert f['atoms'] == 2_000_000 and f['decimals'] == 6 and abs(f['sol'] + 0.1) < 1e-9 and f['feeSol'] == 5e-06
    assert fw.fill_from_meta(tx('OWNER', 'M', 0, 1, 1, 1, err={'x': 1}), 'OWNER', 'M') is None
    assert fw.fill_from_meta(tx('OTHER', 'M', 0, 1, 1, 1), 'OWNER', 'M') is None   # owner didn't sign


def test_apply_fill_books_entry_and_fees_apart():
    book = fw.new_book(100, 100.0, 0)    # 1 SOL
    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M'}
    b, r = fw.apply_fill(book, order, {'atoms': 20_000_000, 'decimals': 6, 'sol': -0.2, 'feeSol': 0.00001}, 100.0)
    assert b['legs']['M']['atoms'] == 20_000_000 and abs(b['legs']['M']['entryPx'] - 1.0) < 1e-9 and abs(b['sol'] - 0.8) < 1e-9
    assert b['feesUsd'] == 0.001 and r['px'] == 1.0
    b2, _ = fw.apply_fill(b, {**order, 'side': 'sell'}, {'atoms': -20_000_000, 'decimals': 6, 'sol': 0.25, 'feeSol': 0.00001}, 100.0)
    assert 'M' not in b2['legs'] and abs(b2['sol'] - 1.05) < 1e-9


def test_sync_card_shows_true_units_entries_and_cash():
    book = {'sol': 0.5, 'legs': {'M': {'atoms': 10_000_000, 'decimals': 6, 'entryPx': 1.1, 'costUsd': 11}}, 'feesUsd': 0.02}
    c = card([leg(SOL, 'sp', 0.2, 100, 'anchor'), leg('M', 'pm', 12, 1.0), leg('N', 'pn', 5, 1.0)])
    s = fw.sync_card(c, book, {}, 100.0)
    m = next(l for l in s['legs'] if l['mint'] == 'M'); n = next(l for l in s['legs'] if l['mint'] == 'N')
    assert m['units'] == 10 and m['entry'] == 1.1 and m['real'] and n['units'] == 0 and not n['real']
    assert abs(s['cash'] - 30.0) < 1e-6 and s['feesUsd'] == 0.02 and s['real']


def test_bank_moves_payouts_out_of_play():
    b = fw.bank({'sol': 1.0, 'bankUsd': 0}, 25, 100.0)
    assert b['sol'] == 0.75 and b['bankSol'] == 0.25 and fw.bank(b, 25, 100.0) == b


def test_free_sol_keeps_reserve_and_card_books():
    assert fw.free_sol(2.0, {'a': {'sol': 0.5, 'bankSol': 0.1}}, 0.03) == 1.37


def test_reconcile_flags_missing_coins():
    books = {'a': {'legs': {'M': {'atoms': 100}}}, 'b': {'legs': {'M': {'atoms': 50}}}}
    assert fw.reconcile({'M': 150}, books) == []
    assert fw.reconcile({'M': 100}, books)[0]['mint'] == 'M'


def test_calibrate_learns_impact_and_fee_from_real_fills():
    led = [{'status': 'filled', 'side': 'buy', 'midPx': 1.0, 'px': 1.02, 'liq': 1000, 'usd': 5, 'feeUsd': 0.002}] * 3   # model 1%, real 2%
    c = fw.calibrate(led)
    assert c['impactMult'] == 2.0 and c['feeUsd'] == 0.002 and c['n'] == 3
    assert fw.calibrate(led[:2])['impactMult'] == 1.0


def test_totals_and_topup_resets_a_new_run():
    led = [{'card': 'degen', 'side': 'buy', 'status': 'filled', 'usd': 10, 'feeUsd': 0.01}, {'card': 'degen', 'side': 'topup', 'usd': 50},
           {'card': 'safe', 'side': 'sell', 'status': 'failed', 'usd': 3}]
    t = fw.totals(led, 'degen'); assert t['bought'] == 10 and t['topups'] == 50 and t['swaps'] == 1
    assert fw.totals(led)['failed'] == 1
    c = card([leg('M', 'pm', 10, 1.0)], startUsd=10, real=True)
    up = fw.topup_card(c, 10, {'pm': 2.0}, 100)
    assert up['startUsd'] == 30 and up['legs'][0]['units'] == 15 and up['runs'][-1]['pct'] == 100.0 and up['events'][-1]['kind'] == 'topup'
    first = fw.topup_card(card([leg('M', 'pm', 50, 1.0), leg('N', 'pn', 25, 2.0)], takenUsd=9, rounds=40, phase='degen', lastRotateAt=7), 20, {'pm': 1.0, 'pn': 2.0}, 100, first=True)
    assert [l['mint'] for l in first['legs']] == ['M', 'N'] and first['phase'] == 'degen' and first['lastRotateAt'] == 7   # same coins + mechanics
    assert abs(sum(l['units'] * {'pm': 1, 'pn': 2}[l['pairAddress']] for l in first['legs']) - 20) < 1e-9                  # scaled to the $
    assert first['startUsd'] == 20 and first['takenUsd'] == 0 and first['rounds'] == 0 and first['real'] and first['runs'][-1]['paper']   # time + P&L restart


def test_paper_status_shows_each_coin_at_the_funded_amount():
    st = fw.paper_status(card([leg('M', 'pm', 30, 1.0), leg('N', 'pn', 10, 1.0)], cash=10, walletUsd=5, startUsd=40), {'pm': 1.5, 'pn': 1.0}, 100)
    assert st['paperUsd'] == 70 and st['paperPct'] == 75.0
    m = st['coins'][0]
    assert m['weightPct'] == round(45 / 65 * 100, 2) and m['usd'] == round(100 * 45 / 65, 4) and m['pricePct'] == 50.0


def test_quote_audit_rows_measure_paper_vs_real_and_feed_calibration():
    r = fw.quote_row('WIF', 10, 1.0, 1000, 1.01, 9.7, 5)     # paper: 9.90 coins, real quote: 9.70
    assert r['devPct'] == round((9.7 / (10 / 1.01) - 1) * 100, 3) and r['devPct'] < 0
    m = fw.paper_match([r, fw.quote_row('A', 10, 1.0, 1e6, 1.0, 10.0, 6)])
    assert m['n'] == 2 and m['within2Pct'] == 50.0 and m['worstDevPct'] == r['devPct']
    c = fw.calibrate([fw.quote_row('X', 5, 1.0, 1000, 1.01, 5 / 1.02, i) for i in range(3)])   # model 1% impact, real 2%
    assert c['impactMult'] == 2.0
    assert fw.paper_match([])['n'] == 0


def test_price_source_gaps_never_teach_the_impact_model():
    gap = [fw.quote_row('X', 5, 1.0, 1000, 1.01, 6.5, i) for i in range(5)]      # real gives +29% more: a stale price, not impact
    assert fw.calibrate(gap)['n'] == 0 and fw.calibrate(gap)['impactMult'] == 1.0


def test_rent_and_network_fees_never_come_out_of_the_card():
    book = fw.new_book(100, 100.0, 0)                                   # 1 SOL in the card
    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M', 'lamports': 200_000_000}
    b, r = fw.apply_fill(book, order, {'atoms': 20_000_000, 'decimals': 6, 'sol': -0.20204, 'feeSol': 0.00001}, 100.0)   # 0.2 swap + 0.00204 rent
    assert abs(b['sol'] - 0.8) < 1e-9 and abs(b['rentSol'] - 0.00204) < 1e-9 and r['usd'] == 20.0   # card paid exactly the swap


def test_wallet_fronts_fees_for_5_rounds_then_the_card_pays():
    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M', 'lamports': 200_000_000}
    fill = {'atoms': 20_000_000, 'decimals': 6, 'sol': -0.20204, 'feeSol': 0.00001}
    early, _ = fw.apply_fill(fw.new_book(100, 100.0, 0), order, fill, 100.0)
    late, _ = fw.apply_fill(fw.new_book(100, 100.0, 0), {**order, 'cardPays': True}, fill, 100.0)
    assert abs(early['sol'] - 0.8) < 1e-9 and abs(late['sol'] - (0.8 - 0.00001 - 0.00204)) < 1e-9
    assert fw.DEFAULT_CFG['minOrderUsd'] == 0.75

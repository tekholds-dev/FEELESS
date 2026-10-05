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


def test_off_card_sell_is_not_blocked_by_buy_liquidity_floor():
    order = {'side': 'sell', 'mint': 'OLD', 'usd': 1.0, 'liq': 0}
    assert fw.check(order, CFG, [], 10) == (True, '')


def test_sell_all_dead_marks_only_confirmed_off_card_holdings_as_card_cash():
    book = {'sol': 0.01, 'legs': {
        'LIVE': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'pl', 'symbol': 'LIVE'},
        'DEAD': {'atoms': 2_000_000, 'decimals': 6, 'pair': 'pd', 'symbol': 'DEAD'},
        'FAILED_BUY': {'atoms': 0, 'decimals': 6, 'pair': 'pf', 'symbol': 'FAIL'},
    }}
    out, marked = fw.mark_off_card_cash(book, card([leg('LIVE', 'pl', 1, 1)]))
    assert marked == ['DEAD']
    assert out['legs']['DEAD']['manualCash'] and out['legs']['DEAD']['atoms'] == 2_000_000
    assert not out['legs']['LIVE'].get('manualCash')
    assert not out['legs']['FAILED_BUY'].get('manualCash')


def test_sell_is_capped_per_swap():
    book = {'sol': 0.0, 'legs': {'BIG': {'atoms': 200_000_000, 'decimals': 6, 'pair': 'pb', 'symbol': 'BIG', 'entryPx': 1.0}}}
    o = fw.orders('degen', card([]), book, {'pb': 1.0}, 200.0, {**CFG, 'maxSwapUsd': 50}, 1)
    assert o[0]['atoms'] == 50_000_000 and o[0]['usd'] == 50


def test_check_blocks_unarmed_paused_over_caps_and_impact():
    o = {'usd': 10, 'side': 'buy', 'liq': 1e9}
    assert fw.check(o, {**CFG, 'armed': False}, [], 0)[0] is False
    assert fw.check(o, {**CFG, 'paused': True}, [], 0)[0] is False
    assert fw.check({'usd': 60}, CFG, [], 0)[0] is False
    led = [{'status': 'filled', 'side': 'buy', 'usd': 295, 'at': 0}]
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


def test_confirmed_fill_must_match_the_order_before_it_can_touch_holdings():
    book = {'legs': {'M': {'atoms': 100, 'decimals': 0}}}
    assert not fw.fill_error({'side': 'buy', 'lamports': 100_000_000}, {'atoms': 10, 'decimals': 0, 'sol': -0.1}, book)
    assert 'wrong direction' in fw.fill_error({'side': 'buy', 'lamports': 100_000_000}, {'atoms': 10, 'decimals': 0, 'sol': 0.1}, book)
    assert 'exact-input' in fw.fill_error({'side': 'buy', 'lamports': 100_000_000}, {'atoms': 10, 'decimals': 0, 'sol': -0.09}, book)
    assert not fw.fill_error({'side': 'sell', 'mint': 'M', 'atoms': 50}, {'atoms': -50, 'sol': 0.1}, book)
    assert 'exact-input' in fw.fill_error({'side': 'sell', 'mint': 'M', 'atoms': 50}, {'atoms': -40, 'decimals': 0, 'sol': 0.1}, book)
    assert 'exact-input' in fw.fill_error({'side': 'sell', 'mint': 'M', 'atoms': 50}, {'atoms': -60, 'decimals': 0, 'sol': 0.1}, book)
    assert 'decimals' in fw.fill_error({'side': 'sell', 'mint': 'M', 'atoms': 50}, {'atoms': -50, 'decimals': 6, 'sol': 0.1}, book)


def test_confirmed_wallet_shortages_are_detected_before_more_trading():
    books = {'a': {'sol': 0.2, 'bankSol': 0.1}, 'b': {'sol': 0.3, 'bankSol': 0}}
    assert fw.reconcile_sol(books={'a': books['a']}, wallet_sol=0.3) is None
    assert fw.reconcile_sol(0.59, books) == {'booked': 0.6, 'held': 0.59}


def test_apply_fill_books_entry_and_fees_apart():
    book = fw.new_book(100, 100.0, 0)    # 1 SOL
    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M'}
    b, r = fw.apply_fill(book, order, {'atoms': 20_000_000, 'decimals': 6, 'sol': -0.2, 'feeSol': 0.00001}, 100.0)
    assert b['legs']['M']['atoms'] == 20_000_000 and abs(b['legs']['M']['entryPx'] - 1.0) < 1e-9 and abs(b['sol'] - 0.8) < 1e-9
    assert b['feesUsd'] == 0.001 and r['px'] == 1.0
    b2, sold = fw.apply_fill(b, {**order, 'side': 'sell'}, {'atoms': -20_000_000, 'decimals': 6, 'sol': 0.25, 'feeSol': 0.00001}, 100.0)
    assert 'M' not in b2['legs'] and abs(b2['sol'] - 1.05) < 1e-9
    assert sold['sol'] == 0.25


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


def test_reinvest_paid_out_moves_only_banked_sol_and_never_inflates_put_in():
    book = {'sol': 0.01, 'bankSol': 0.019, 'bankUsd': 1.90, 'fundedUsd': 6.0, 'legs': {}, 'feesUsd': 0}
    before = fw.book_value(book, {}, 100.0)
    out, moved = fw.reinvest_bank(book)
    assert moved == 0.019
    assert out['sol'] == 0.029 and out['bankSol'] == 0.0
    assert out['fundedUsd'] == 6.0 and out['bankUsd'] == 0.0
    assert fw.book_value(out, {}, 100.0) == before
    # Current paid-out balance is consumed by reinvest; lifetime payout history is kept separately in the confirmed ledger.


def test_bank_marks_only_proceeds_actually_segregated_then_finishes_after_the_sell():
    before_sell = fw.bank({'sol': 0.01, 'bankSol': 0, 'bankUsd': 0}, 5, 100)
    assert before_sell == {'sol': 0.0, 'bankSol': 0.01, 'bankUsd': 1.0, 'payoutSeenUsd': 1.0}
    after_sell = fw.bank({**before_sell, 'sol': 0.04}, 5, 100)
    assert after_sell == {'sol': 0.0, 'bankSol': 0.05, 'bankUsd': 5.0, 'payoutSeenUsd': 5.0}


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


def test_real_topup_run_baseline_uses_confirmed_book_value_not_stale_card_value():
    stale = card([leg('M', 'pm', 0.1, 1.0)], startUsd=1.39, real=True, walletUsd=0)
    up = fw.topup_card(stale, 1.0, {'pm': 1.0}, 100, current_usd=6.91)
    assert up['startUsd'] == 7.91 and up['runs'][-1]['endUsd'] == 6.91 and up['realBaselineAt'] == 100


def test_legacy_real_card_never_reports_its_old_paper_start_as_live_money_return():
    assert fw.real_run_start({'startUsd': 1.39, 'real': True}, {'fundedUsd': 6}) == 6
    assert fw.real_run_start({'startUsd': 7.91, 'realBaselineAt': 100}, {'fundedUsd': 7}) == 7.91


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
    assert abs(early['sol'] - 0.8) < 1e-9 and abs(late['sol'] - (0.8 - 0.00001)) < 1e-9   # card pays the fee, never the rent deposit
    assert fw.DEFAULT_CFG['minOrderUsd'] == 0.5


def test_failed_buy_is_retried_and_never_shows_minus_100():
    import fuse_wallet as fw
    card = {'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'symbol': 'SOL', 'units': 0.01, 'entry': 100},
                     {'mint': 'RUN', 'pairAddress': 'R', 'symbol': 'RUN', 'units': 1000.0, 'entry': 0.002, 'costUsd': 2.0}]}
    book = {'sol': 0.03, 'legs': {}}
    c = fw.sync_card(card, book, {'S': 100, 'R': 0.002}, 100)
    leg = c['legs'][1]
    assert leg['units'] == 0 and leg['costUsd'] == 0 and leg['buying'] and leg['wantUnits'] == 1000.0
    c2 = fw.sync_card(c, book, {'S': 100, 'R': 0.002}, 100)   # next tick: still wanted
    assert c2['legs'][1]['wantUnits'] == 1000.0
    cfg = {**fw.DEFAULT_CFG, 'armed': True}
    buys = [o for o in fw.orders('t', c2, book, {'S': 100, 'R': 0.002}, 100, cfg, 1) if o['side'] == 'buy']
    assert buys and buys[0]['mint'] == 'RUN'   # the keeper tries again
    book2 = {'sol': 0.01, 'legs': {'RUN': {'atoms': 1000_000000, 'decimals': 6, 'entryPx': 0.002, 'costUsd': 2.0, 'pair': 'R'}}}
    c3 = fw.sync_card(c2, book2, {'S': 100, 'R': 0.002}, 100)
    assert c3['legs'][1]['real'] and 'buying' not in c3['legs'][1]


def test_defund_returns_the_paper_card_from_before_real_money():
    import fuse_wallet as fw
    paper = {'legs': [{'mint': 'A', 'pairAddress': 'A', 'symbol': 'A', 'units': 50.0, 'entry': 2.0, 'costUsd': 100.0}], 'cash': 0.0, 'startUsd': 100.0, 'real': False}
    real = fw.topup_card(paper, 4.0, {'A': 2.0}, 10, first=True)
    assert real['startUsd'] == 4.0 and real['paperBefore']['startUsd'] == 100.0
    back = fw.back_to_paper({**real, 'legs': [{**real['legs'][0], 'units': 0.0, 'buying': True}]}, 4.2, 20)
    assert not back['real'] and back['startUsd'] == 100.0 and back['legs'][0]['units'] == 50.0 and 'buying' not in back['legs'][0]
    assert back['runs'][-1]['paper'] is False and back['runs'][-1]['endUsd'] == 4.2


def test_legacy_card_snapshot_scales_back_to_paper_value():
    import fuse_wallet as fw
    card = {'legs': [{'mint': 'A', 'pairAddress': 'A', 'units': 2.0, 'costUsd': 4.0}], 'cash': 0.0, 'startUsd': 4.0,
            'runs': [{'startUsd': 100.0, 'endUsd': 200.0, 'paper': True}]}
    snap = fw.paper_snapshot(card)
    assert snap['legs'][0]['units'] == 100.0 and snap['startUsd'] == 100.0


def test_new_round_rebuys_an_empty_coin_from_spare_sol():
    import fuse_wallet as fw
    card = {'rounds': 3, 'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'symbol': 'SOL', 'units': 0.03, 'entry': 100},
                                  {'mint': 'RUN', 'pairAddress': 'R', 'symbol': 'RUN', 'units': 0.0, 'entry': 0.002}]}
    book = {'sol': 0.03, 'legs': {}}
    c = fw.sync_card(card, book, {'S': 100, 'R': 0.002}, 100)
    run = c['legs'][1]
    assert run['buying'] and abs(run['wantUnits'] * 0.002 - 1.5) < 0.01 and abs(c['legs'][0]['units'] - 0.015) < 1e-9
    assert c['rebuyRound'] == 3
    buys = [o for o in fw.orders('t', c, book, {'S': 100, 'R': 0.002}, 100, {**fw.DEFAULT_CFG, 'armed': True}, 1) if o['side'] == 'buy']
    assert buys and buys[0]['mint'] == 'RUN' and buys[0]['usd'] <= 1.51
    c['legs'][1].pop('buying'); c['legs'][1]['wantUnits'] = 0
    again = fw.sync_card(c, book, {'S': 100, 'R': 0.002}, 100)   # same round: no second try
    assert not again['legs'][1].get('buying')


def test_trimmed_sol_anchor_keeps_its_true_cost():
    import fuse_wallet as fw
    card = {'rounds': 1, 'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'symbol': 'SOL', 'units': 0.03, 'entry': 100, 'costUsd': 3.0},
                                  {'mint': 'RUN', 'pairAddress': 'R', 'symbol': 'RUN', 'units': 0.0, 'entry': 0.002}]}
    c = fw.sync_card(card, {'sol': 0.03, 'legs': {}}, {'S': 100, 'R': 0.002}, 100)
    sol = c['legs'][0]
    assert abs(sol['costUsd'] - 1.5) < 1e-6   # half the SOL left → half the cost, so SOL reads ~0%, never −50%


def test_zeroed_sol_anchor_restores_from_confirmed_card_cash_without_a_swap():
    card = {'rounds': 40, 'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'symbol': 'SOL', 'units': 0.0, 'entry': 100, 'costUsd': 0},
                                    {'mint': 'A', 'pairAddress': 'A', 'symbol': 'A', 'units': 1, 'entry': 1},
                                    {'mint': 'B', 'pairAddress': 'B', 'symbol': 'B', 'units': 1, 'entry': 1},
                                    {'mint': 'C', 'pairAddress': 'C', 'symbol': 'C', 'units': 1, 'entry': 1}]}
    out = fw.sync_card(card, {'sol': 0.04, 'legs': {}}, {'S': 100, 'A': 1, 'B': 1, 'C': 1}, 100)
    sol = out['legs'][0]
    assert sol['units'] == 0.01 and out['cash'] == 3.0 and not sol.get('buying') and not sol.get('wantUnits')
    orders = fw.orders(
        'safe', out, {'sol': 0.04, 'legs': {}},
        {'S': 100, 'A': 1, 'B': 1, 'C': 1}, 100,
        {**fw.DEFAULT_CFG, 'armed': True}, 1,
    )
    assert not [order for order in orders if order['mint'] == fw.SOL_MINT]


def test_real_buys_skip_thin_pools_but_sells_pass():
    import fuse_wallet as fw
    cfg = {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'a', 'maxSwapUsd': 5, 'dailyUsd': 30}
    ok, why = fw.check({'side': 'buy', 'usd': 1, 'liq': 5000}, cfg, [], 1)
    assert not ok and 'too thin' in why
    assert fw.check({'side': 'buy', 'usd': 1, 'liq': 50000}, cfg, [], 1)[0]
    assert fw.check({'side': 'sell', 'usd': 1, 'liq': 0}, cfg, [], 1)[0]


def test_secure_buy_checks_price_gap_and_sell_back():
    import fuse_wallet as fw
    o = {'usd': 1.0, 'midPx': 0.001, 'lamports': 10_000_000}
    assert fw.buy_safety(o, 1000 * 10**6, 6, 9_700_000)[0]                      # fair price, sells back −3%
    assert 'above market' in fw.buy_safety(o, 900 * 10**6, 6, 9_700_000)[1]     # 11% worse than market
    assert 'sell it back' in fw.buy_safety(o, 1000 * 10**6, 6, None)[1]         # honeypot / no route
    assert 'less' in fw.buy_safety(o, 1000 * 10**6, 6, 8_000_000)[1]            # 20% round-trip loss (tax / one-way)


def test_leftover_cash_under_min_order_still_buys_the_waiting_coin():
    import fuse_wallet as fw
    card = {'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'units': 0.0065, 'entry': 120},
                     {'mint': 'W', 'pairAddress': 'W', 'symbol': 'WETH', 'units': 0.0, 'wantUnits': 0.00029, 'buying': True, 'entry': 2680}]}
    book = {'sol': 0.0101, 'legs': {}}
    buys = [o for o in fw.orders('t', card, book, {'S': 120, 'W': 2680}, 120, {**fw.DEFAULT_CFG, 'armed': True}, 1) if o['side'] == 'buy']
    assert buys and buys[0]['mint'] == 'W' and 0.15 <= buys[0]['usd'] < 0.5


def test_close_empty_accounts_only_and_builds_close_ix():
    import base64, fuse_wallet as fw
    from solders.transaction import Transaction
    from solders.keypair import Keypair
    owner, acct = str(Keypair().pubkey()), str(Keypair().pubkey())
    rows = [{'pubkey': acct, 'program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'info': {'mint': 'M1', 'tokenAmount': {'amount': '0'}}},
            {'pubkey': str(Keypair().pubkey()), 'program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'info': {'mint': 'M2', 'tokenAmount': {'amount': '5'}}},
            {'pubkey': str(Keypair().pubkey()), 'program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'info': {'mint': 'HELD', 'tokenAmount': {'amount': '0'}}}]
    empty = fw.empty_accounts(rows, keep_mints=['HELD'])
    assert [e['mint'] for e in empty] == ['M1']
    tx = Transaction.from_bytes(base64.b64decode(fw.close_tx(owner, empty, '11111111111111111111111111111111')))
    ix = tx.message.instructions[0]
    assert bytes(ix.data) == bytes([9]) and str(tx.message.account_keys[0]) == owner


def test_coin_failing_buys_3x_in_10min_is_benched_for_an_hour():
    import fuse_wallet as fw
    b = {}
    for t in (0, 60):
        b, out = fw.note_miss(b, 'M', t, 'price impact 5% > 3.5%')
    assert out and fw.benched(b, 200) == {'M'} and fw.benched(b, 60 + 3601) == set()
    b2, out2 = fw.note_miss({}, 'X', 0, 'x'); b2, out2 = fw.note_miss(b2, 'X', 700, 'x')   # outside the window → count restarts
    assert not out2 and b2['misses']['X']['n'] == 1


def test_cap_skip_is_logged_once_per_quiet_window():
    """🚦 a daily-cap skip is booked once per 15 min per card·coin·side — the keeper no longer re-quotes + re-logs every tick."""
    row = {'card': 'safe', 'mint': 'M1', 'side': 'buy', 'status': 'skipped', 'err': 'daily cap $30 reached', 'at': 1000.0}
    assert not fw.logged_recently([], row, 1000.0)
    assert fw.logged_recently([row], {**row, 'at': 1040.0}, 1040.0)                       # next tick: quiet
    assert not fw.logged_recently([row], {**row, 'at': 1000.0 + fw.QUIET_SEC + 1}, 1000.0 + fw.QUIET_SEC + 1)   # window over: log again
    assert not fw.logged_recently([row], {**row, 'side': 'sell'}, 1040.0)                 # other side / coin / card / reason still logs
    assert not fw.logged_recently([row], {**row, 'mint': 'M2'}, 1040.0)
    assert not fw.logged_recently([row], {**row, 'err': 'Fuse wallet is paused'}, 1040.0)


def test_cap_blocks_before_any_quote():
    """check() with no impact = the pre-quote gate: a capped order is refused without needing a Jupiter quote."""
    cfg = {'armed': True, 'walletId': 'w', 'address': 'a', 'dailyUsd': 30, 'maxSwapUsd': 10}
    led = [{'status': 'filled', 'side': 'buy', 'usd': 29.9, 'at': 100.0}, {'status': 'filled', 'side': 'sell', 'usd': 50.0, 'at': 100.0}]
    ok, why = fw.check({'side': 'buy', 'usd': 0.69, 'liq': 1e6}, cfg, led[:1], 200.0)
    assert not ok and why.startswith('daily cap')
    assert fw.check({'side': 'buy', 'usd': 0.69, 'liq': 1e6}, cfg, led, 200.0)[0]   # 🔁 rebuying with SOL the card just sold is NOT new money
    assert fw.check({'side': 'sell', 'usd': 0.69}, cfg, led, 200.0)[0]            # a sell always passes the cap
    assert fw.spent_24h(led, 200.0) == 0.0                                          # bought 29.9, sold 50 → no NEW money spent
    assert fw.spent_24h(led[:1], 200.0) == 29.9


def test_dealt_coin_keeps_its_depth_and_new_major_tag():
    import arena_prime as ap
    l = ap._leg({'mint': 'M', 'pairAddress': 'P', 'symbol': 'NM', 'price': 1.0, 'liquidity': 150_000, 'newMajor': True}, 5.0, 0, 'runner')
    assert l['liq'] == 150_000 and l['newMajor']
    r = ap._leg({'mint': 'R', 'pairAddress': 'Q', 'symbol': 'RN', 'price': 1.0, 'liq': 40_000}, 5.0, 0, 'runner')
    assert r['liq'] == 40_000 and 'newMajor' not in r


def test_kept_coin_is_not_churned_on_a_reshape():
    """🔁 a coin that stays on the card is not sold / rebought for a small re-weigh (that churn ate the daily cap)."""
    book = {'sol': 1.0, 'legs': {'M1': {'atoms': 1_100_000, 'decimals': 6, 'pair': 'P1', 'symbol': 'A', 'entryPx': 1.0}}}
    card = {'legs': [{'mint': 'M1', 'pairAddress': 'P1', 'symbol': 'A', 'units': 1.0, 'role': 'anchor'}], 'cash': 0.0}
    out = fw.orders('safe', card, book, {'P1': 1.0}, 100.0, {**CFG, 'minOrderUsd': 0.05}, 0)
    assert not [o for o in out if o['mint'] == 'M1']                     # 1.1 held vs 1.0 wanted: inside the band
    far = fw.orders('safe', card, {**book, 'legs': {'M1': {**book['legs']['M1'], 'atoms': 3_000_000}}}, {'P1': 1.0}, 100.0, {**CFG, 'minOrderUsd': 0.05}, 0)
    assert any(o['side'] == 'sell' and o['mint'] == 'M1' for o in far)   # 3× over target: trimmed


def test_sell_safety_blocks_a_route_far_under_market_but_lets_a_real_dump_sell():
    o = {'atoms': 887_360_813, 'decimals': 6}                        # 887 HOTBOT
    ok, why = fw.sell_safety(o, 7_088_954, 68.6, 0.000967)            # route pays $0.49 for $0.86 of coins → refused
    assert not ok and 'under market' in why
    assert fw.sell_safety(o, 7_088_954, 68.6, 0.00055)[0]             # the coin really fell to that price → it sells
    assert fw.sell_safety(o, 0, 68.6, 0.0)[0]                         # no price: never strand a coin


def test_cost_of_sold_part():
    book = {'legs': {'M': {'atoms': 1000, 'costUsd': 0.8}}}
    assert fw.cost_of(book, 'M', 500) == 0.4 and fw.cost_of(book, 'M', 5000) == 0.8 and fw.cost_of(book, 'X', 1) == 0.0


def test_priority_rises_after_txs_that_did_not_land():
    led = [{'card': 'safe', 'err': 'not confirmed in 2 min', 'at': 900.0}, {'card': 'safe', 'err': 'not confirmed in 2 min', 'at': 950.0},
           {'card': 'other', 'err': 'not confirmed in 2 min', 'at': 950.0}, {'card': 'safe', 'err': 'not confirmed in 2 min', 'at': 10.0}]
    assert fw.landing_boost(led, 'safe', 1000.0) == 2
    assert fw.priority_cap(0, 0) == 50_000 and fw.priority_cap(0, 2) == 150_000 and fw.priority_cap(2, 4) == 300_000


def test_first_try_swap_costs_under_a_penny_retries_pay_to_land():
    for px in (100.0, 150.0, 200.0, 400.0):
        cap = fw.priority_cap(0, 0, px)
        assert (cap + fw.BASE_LAMPORTS) / 1e9 * px < 0.01 or cap == 10_000
    assert fw.priority_cap(0, 0, 200.0) == 40_000
    assert fw.priority_cap(1, 0, 200.0) == 100_000 and fw.priority_cap(0, 1, 200.0) == 100_000   # trouble landing → pay to land


def test_gas_tank_and_landing_rate():
    books = {'safe': {'sol': 0.01}}
    assert fw.gas_tank(0.0104, books, 0.03)['state'] == 'empty'          # 0.0004 SOL free: not even one new-coin rent
    g = fw.gas_tank(0.03, books, 0.03)
    assert g['state'] == 'low' and g['newCoins'] == 9
    assert fw.gas_tank(0.05, books, 0.03)['state'] == 'ok'
    led = [{'card': 'safe', 'side': 'buy', 'status': 'filled', 'sig': 'a', 'at': 100}, {'card': 'safe', 'side': 'buy', 'status': 'filled', 'sig': 'a', 'at': 100},
           {'card': 'safe', 'side': 'buy', 'status': 'failed', 'err': 'not confirmed in 2 min', 'at': 100},
           {'card': 'safe', 'side': 'buy', 'status': 'skipped', 'err': 'buy price 5.9% above market (> 5%)', 'at': 100},
           {'card': 'safe', 'side': 'buy', 'status': 'failed', 'err': 'not confirmed in 2 min', 'at': 100}, {'card': 'safe', 'side': 'topup', 'at': 100}]
    L = fw.landing(led, 'safe', 200)
    assert L == {'tried': 4, 'filled': 1, 'pct': 25, 'top': 'not confirmed in 2 min', 'topN': 2}


def test_circle_balances_fallback_never_shows_an_empty_wallet():
    ws = [{'address': 'A', 'balances': [{'symbol': 'SOL', 'amount': '0.0746'}, {'symbol': 'SPEC', 'amount': '650.5'}, {'symbol': 'X', 'amount': '0'}]}]
    b = fw.circle_balances(ws, 'A')
    assert b['sol'] == 0.0746 and b['tokens'] == {'SPEC': 650.5} and b['source'] == 'circle'
    assert fw.circle_balances(ws, 'B') is None


def test_strays_only_adopts_keeper_coins_no_card_books():
    books = {'safe': {'legs': {'BOOKED': {'atoms': 5}}}}
    led = [{'card': 'safe', 'mint': 'WDYT', 'pair': 'PW', 'symbol': 'WDYT', 'decimals': 6, 'at': 100.0}]
    toks = {'WDYT': 733_227_546, 'BOOKED': 5, 'MINE': 99, fw.SOL_MINT: 1}
    out = fw.strays(toks, {'WDYT': 6}, books, led, 1000.0)
    assert out == [{'card': 'safe', 'mint': 'WDYT', 'atoms': 733_227_546, 'decimals': 6, 'pair': 'PW', 'symbol': 'WDYT'}]   # owner's own MINE untouched
    assert fw.strays(toks, {}, books, led, 200.0) == []                                          # still settling
    assert fw.strays(toks, {}, {'safe': {**books['safe'], 'pending': {'id': 1}}}, led, 1000.0) == []   # an order in flight
    b = fw.adopt(books['safe'], out[0])
    assert b['legs']['WDYT']['costUsd'] == 0.0 and b['legs']['WDYT']['recovered'] and b['legs']['BOOKED'] == {'atoms': 5}


def test_repeat_bench_doubles_up_to_a_day():
    b, n = {}, fw.MISS_LIMIT
    for t in range(n):
        b, out = fw.note_miss(b, 'P', 0.0 + t, 'buy price 6% above market')
    assert out and b['benched']['P']['until'] == n - 1 + fw.BENCH_SEC and b['benched']['P']['times'] == 1
    for t in range(n):
        b, out = fw.note_miss(b, 'P', 5000.0 + t, 'again')
    assert b['benched']['P']['times'] == 2 and b['benched']['P']['until'] == 5000 + n - 1 + 2 * fw.BENCH_SEC


def test_unconfirmed_keeper_transaction_keeps_the_pending_lock(monkeypatch):
    import asyncio
    import reputation_service as rs
    class Http:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
    async def absent(*a, **k): return None
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Http)
    monkeypatch.setattr(rs, '_rpc', absent)
    pending = {'side': 'sell', 'mint': 'M', 'atoms': 100, 'sig': 'late', 'sentAt': 1, 'usd': 1}
    book = {'pending': pending, 'legs': {'M': {'atoms': 100, 'decimals': 0}}}
    out = asyncio.run(rs._fw_resolve('safe', book, {'address': 'OWNER'}, 100, wait=0))
    assert out == book and out['pending']['sig'] == 'late' and out['legs']['M']['atoms'] == 100


def test_execute_never_overwrites_an_existing_pending_signature(monkeypatch):
    import asyncio
    import reputation_service as rs
    async def forbidden(*a, **k):
        raise AssertionError('an in-flight card must not quote or submit another order')
    monkeypatch.setattr(rs, '_fw_quote', forbidden)
    book = {'pending': {'sig': 'first'}}
    out = asyncio.run(rs._fw_execute('safe', {'side': 'buy', 'mint': 'M'}, book, {}, 100, 1e6))
    assert out is book and out['pending']['sig'] == 'first'


def test_secure_quote_refusals_are_attributed_to_the_card_for_benching():
    import inspect
    import reputation_service as rs
    src = inspect.getsource(rs._fw_execute)
    assert "'card': tid" in src


def test_sync_card_rebases_legacy_real_run_on_confirmed_funding():
    import fuse_wallet as fw
    card = {'real': True, 'startUsd': 1.389, 'roundStartUsd': 1.389, 'dayStartUsd': 1.389, 'legs': [], 'cash': 0.0}
    book = {'fundedUsd': 6.0, 'since': 100.0, 'sol': 0.0, 'legs': {}}
    c = fw.sync_card(card, book, {}, 120.0)
    assert c['startUsd'] == 6.0 and c['dayStartUsd'] == 6.0 and c['realBaselineAt'] == 100.0
    c['startUsd'] = 7.0   # a later confirmed top-up baseline is never overwritten again
    assert fw.sync_card(c, book, {}, 120.0)['startUsd'] == 7.0


def test_arena_coins_have_their_own_real_buy_floor():
    import fuse_wallet as fw
    cfg = {**fw.DEFAULT_CFG, 'minLiqUsd': 100000.0, 'arenaMinLiqUsd': 30000.0}
    assert fw.liq_floor(cfg) == 100000.0 and fw.liq_floor(cfg, arena=True) == 30000.0
    assert fw.liq_floor({**cfg, 'arenaMinLiqUsd': 500000.0}, arena=True) == 100000.0   # never stricter-by-accident than the general floor
    card = {'legs': [{'mint': 'M1', 'pairAddress': 'p1', 'symbol': 'ARN', 'role': 'runner', 'entry': 1.0, 'units': 2.0, 'arena': True}]}
    tgt = fw.target(card, {'p1': 1.0})
    assert tgt['M1']['arena'] is True


def test_empty_real_slot_can_recover_from_overweight_unprotected_anchor_without_external_money():
    card = {'rounds': 8, 'rebuyRound': 7, 'rebuyAt': 0, 'legs': [
        {'mint': 'BTC', 'pairAddress': 'PBTC', 'symbol': 'cbBTC', 'role': 'anchor', 'units': 2.25, 'costUsd': 2.25, 'entry': 1.0},
        {'mint': 'RUN', 'pairAddress': 'PRUN', 'symbol': 'RUN', 'role': 'runner', 'units': 0.0, 'costUsd': 0.0, 'entry': 1.0},
        {'mint': 'WIN', 'pairAddress': 'PWIN', 'symbol': 'WIN', 'role': 'runner', 'units': 1.5, 'costUsd': 1.5, 'entry': 1.0, 'ride': True},
        {'mint': 'KEEP', 'pairAddress': 'PKEEP', 'symbol': 'KEEP', 'role': 'runner', 'units': 0.45, 'costUsd': 0.45, 'entry': 1.0, 'frozen': True},
    ]}
    book = {'sol': 0.0, 'bankSol': 0.019, 'bankUsd': 1.90, 'fundedUsd': 6.0, 'legs': {
        'BTC': {'atoms': 2250000, 'decimals': 6, 'pair': 'PBTC', 'symbol': 'cbBTC', 'costUsd': 2.25, 'entryPx': 1.0},
        'WIN': {'atoms': 1500000, 'decimals': 6, 'pair': 'PWIN', 'symbol': 'WIN', 'costUsd': 1.5, 'entryPx': 1.0},
        'KEEP': {'atoms': 450000, 'decimals': 6, 'pair': 'PKEEP', 'symbol': 'KEEP', 'costUsd': 0.45, 'entryPx': 1.0},
    }}
    prices = {'PBTC': 1.0, 'PRUN': 1.0, 'PWIN': 1.0, 'PKEEP': 1.0}
    out = fw.sync_card(card, book, prices, 100.0)
    run = next(l for l in out['legs'] if l['mint'] == 'RUN')
    btc = next(l for l in out['legs'] if l['mint'] == 'BTC')
    win = next(l for l in out['legs'] if l['mint'] == 'WIN')
    keep = next(l for l in out['legs'] if l['mint'] == 'KEEP')
    assert run['buying'] and run['wantUnits'] > 0
    assert btc['units'] < 2.25
    assert win['units'] == 1.5 and keep['units'] == 0.45
    assert book['bankSol'] == 0.019 and out['cash'] == 0.0
    planned = fw.orders('prime-safe', out, book, prices, 100.0, {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'a'}, 10)
    assert planned and planned[0]['side'] == 'sell' and planned[0]['mint'] == 'BTC'
    # The planner may show the buy using estimated proceeds, but the keeper's real BUY pass always reruns with count_sells=False.
    # Before the sell is confirmed into book.sol, that real pass must have nothing it can spend.
    real_buy_pass = fw.orders('prime-safe', out, book, prices, 100.0, {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'a'}, 10, count_sells=False)
    assert not [o for o in real_buy_pass if o['side'] == 'buy']
    assert book['fundedUsd'] == 6.0 and book['bankUsd'] == 1.90 and book['bankSol'] == 0.019


def test_empty_slot_repair_never_trims_frozen_or_riding_anchor():
    for flag in ('frozen', 'ride'):
        card = {'rounds': 8, 'rebuyRound': 7, 'rebuyAt': 0, 'legs': [
            {'mint': 'BTC', 'pairAddress': 'PBTC', 'symbol': 'cbBTC', 'role': 'anchor', 'units': 2.0, 'costUsd': 2.0, 'entry': 1.0, flag: True},
            {'mint': 'RUN', 'pairAddress': 'PRUN', 'symbol': 'RUN', 'role': 'runner', 'units': 0.0, 'costUsd': 0.0, 'entry': 1.0},
        ]}
        book = {'sol': 0.0, 'bankSol': 0.02, 'bankUsd': 2.0, 'fundedUsd': 4.0, 'legs': {
            'BTC': {'atoms': 2000000, 'decimals': 6, 'pair': 'PBTC', 'symbol': 'cbBTC', 'costUsd': 2.0, 'entryPx': 1.0},
        }}
        out = fw.sync_card(card, book, {'PBTC': 1.0, 'PRUN': 1.0}, 100.0)
        run = next(l for l in out['legs'] if l['mint'] == 'RUN')
        btc = next(l for l in out['legs'] if l['mint'] == 'BTC')
        assert not run['buying'] and btc['units'] == 2.0 and book['bankSol'] == 0.02


def test_reinvested_payout_is_not_banked_again_from_same_cumulative_target():
    book = {'sol': 0.03, 'bankSol': 0.0, 'bankUsd': 0.0, 'fundedUsd': 6.0, 'legs': {}}
    paid = fw.bank(book, 1.90, 100.0)
    assert paid['bankSol'] == 0.019 and paid['payoutSeenUsd'] == 1.90
    reinvested, moved = fw.reinvest_bank(paid)
    assert moved == 0.019 and reinvested['bankSol'] == 0.0 and reinvested['bankUsd'] == 0.0
    assert reinvested['fundedUsd'] == 6.0 and reinvested['payoutSeenUsd'] == 1.90
    again = fw.bank(reinvested, 1.90, 100.0)
    assert again['bankSol'] == 0.0
    assert again['sol'] == reinvested['sol']
    # Only a genuinely NEW cumulative payout delta may be segregated after reinvest.
    newer = fw.bank(again, 2.10, 100.0)
    assert round(newer['bankUsd'], 2) == 0.20
    assert round(newer['payoutSeenUsd'], 2) == 2.10


def test_fresh_market_gate_rejects_stale_high_liquidity_candidate_before_real_buy():
    cfg = {**CFG, 'minLiqUsd': 100000, 'arenaMinLiqUsd': 20000}
    order = {'side': 'buy', 'mint': 'HIVE', 'pair': 'PAIR', 'usd': 1.0, 'liq': 250000}
    live = {'pairAddress': 'PAIR', 'baseToken': {'address': 'HIVE'}, 'priceUsd': '0.0000034', 'liquidity': {'usd': 4850}}
    ok, why, snap = fw.live_buy_market(order, live, cfg)
    assert not ok and 'live pool too thin' in why
    assert snap['liq'] == 4850
    arena_ok, arena_why, _ = fw.live_buy_market({**order, 'arena': True}, live, cfg)
    assert not arena_ok and '20,000' in arena_why
    good = {'pairAddress': 'PAIR', 'baseToken': {'address': 'HIVE'}, 'priceUsd': '0.0000034', 'liquidity': {'usd': 125000}}
    assert fw.live_buy_market(order, good, cfg)[0]
    assert not fw.live_buy_market(order, {**good, 'baseToken': {'address': 'OTHER'}}, cfg)[0]


def test_manual_sell_to_cash_keeps_proceeds_in_card_and_does_not_rebuy():
    import arena_prime as ap
    c = {'tpl': 'safe', 'legs': [{'mint': 'M', 'pairAddress': 'pm', 'symbol': 'M', 'units': 2.0, 'entry': 1.0,
                                  'costUsd': 2.0, 'role': 'runner'}], 'cash': 0.0, 'events': [], 'feesUsd': 0.0}
    sold = ap.sell_leg_to_cash(c, 'pm', {'pm': 1.25}, 10)
    leg = sold['legs'][0]
    assert leg['manualCash'] and leg['placeholder'] and leg['units'] == 0 and sold['cash'] == 2.5
    assert sold['events'][-1]['kind'] == 'manual-sell'

    book = {'sol': 0.025, 'legs': {}, 'fundedUsd': 2.5, 'feesUsd': 0.0}
    synced = fw.sync_card(sold, book, {'pm': 1.25}, 100.0)
    assert synced['legs'][0]['manualCash'] and not synced['legs'][0].get('buying')
    assert synced['cash'] == 2.5
    assert not [o for o in fw.orders('safe', synced, book, {'pm': 1.25}, 100.0,
                                      {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'A'}, 20)
                if o['side'] == 'buy']


def test_manual_cash_is_not_swept_into_payout_and_is_consumed_by_later_buy():
    book = {'sol': 0.05, 'bankSol': 0.0, 'bankUsd': 0.0, 'payoutSeenUsd': 0.0, 'manualCashSol': 0.03, 'legs': {}}
    kept = fw.bank(book, 10.0, 100.0)
    assert kept['sol'] == 0.03 and kept['bankSol'] == 0.02 and kept['manualCashSol'] == 0.03

    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M', 'lamports': 10_000_000}
    bought, _ = fw.apply_fill(kept, order, {'atoms': 1_000_000, 'decimals': 6, 'sol': -0.01, 'feeSol': 0.0}, 100.0)
    assert bought['manualCashSol'] == 0.02


def test_recovered_old_keeper_coin_force_sell_is_marked_card_cash():
    book = {'sol': 0.0, 'legs': {'OLD': {'atoms': 2_000_000, 'decimals': 6, 'pair': 'pold', 'symbol': 'AGENTCAT',
                                          'entryPx': 0.5, 'costUsd': 1.0, 'manualCash': True, 'recovered': True}}}
    card = {'legs': [], 'cash': 0.0}
    cfg = {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'A', 'minOrderUsd': 0.25}
    sells = [o for o in fw.orders('safe', card, book, {'pold': 0.5}, 100.0, cfg, 10) if o['side'] == 'sell']
    assert sells and sells[0]['mint'] == 'OLD' and sells[0]['manualCash']
    assert sells[0]['why'] == 'sold by owner to card cash'

    filled, _ = fw.apply_fill(book, sells[0], {'atoms': -2_000_000, 'decimals': 6, 'sol': 0.01, 'feeSol': 0.0}, 100.0)
    assert not filled['legs'] and filled['sol'] == 0.01 and filled['manualCashSol'] == 0.01


def test_recovered_coin_below_normal_dust_floor_still_gets_a_sell_attempt():
    book = {'sol': 0.0, 'legs': {'DEAD': {'atoms': 10_000, 'decimals': 6, 'pair': 'pd', 'symbol': 'DEAD',
                                           'entryPx': 1.0, 'costUsd': 1.0, 'manualCash': True, 'recovered': True}}}
    cfg = {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'A', 'minOrderUsd': 0.25}
    sells = fw.orders('safe', {'legs': []}, book, {'pd': 0.001}, 100.0, cfg, 10)
    assert len(sells) == 1
    assert sells[0]['side'] == 'sell' and sells[0]['mint'] == 'DEAD' and sells[0]['manualCash']

def test_profit_available_never_touches_funded_principal():
    book = {'fundedUsd': 7.0, 'sol': 0.02, 'bankSol': 0.001}
    assert fw.profit_available(book, 6.99, 100.0) == 0.0
    assert fw.profit_available(book, 7.50, 100.0) == 0.4


def test_bank_waits_until_whole_card_is_above_put_in():
    book = {'fundedUsd': 7.0, 'sol': 0.03, 'bankSol': 0.0, 'bankUsd': 0.0, 'payoutSeenUsd': 0.0}
    held = fw.bank(book, 1.0, 100.0, equity_usd=6.5)
    assert held['sol'] == 0.03 and held.get('bankSol', 0) == 0
    assert held.get('payoutSeenUsd', 0) == 0
    paid = fw.bank(book, 1.0, 100.0, equity_usd=7.5)
    assert paid['bankSol'] == 0.005 and paid['sol'] == 0.025
    assert paid['payoutSeenUsd'] == 0.5


def test_manual_profit_payout_is_limited_to_profit_and_card_cash():
    book = {'fundedUsd': 7.0, 'sol': 0.01, 'bankSol': 0.0, 'bankUsd': 0.0, 'manualCashSol': 0.002}
    out, paid = fw.payout_profit_cash(book, equity_usd=8.0, sol_px=100.0)
    assert paid == 0.8
    assert out['bankSol'] == 0.008 and out['sol'] == 0.002
    out2, paid2 = fw.payout_profit_cash(book, equity_usd=6.0, sol_px=100.0)
    assert paid2 == 0.0 and out2 == book

def test_principal_floor_reinvests_old_paid_out_money_when_card_is_underfunded():
    book = {'fundedUsd': 7.0, 'sol': 0.01, 'bankSol': 0.001, 'bankUsd': 0.1}
    out, moved = fw.enforce_principal_floor(book, equity_usd=5.5, sol_px=100.0)
    assert moved == 0.001
    assert out['bankSol'] == 0.0 and out['sol'] == 0.011 and out['bankUsd'] == 0.0


def test_principal_floor_keeps_only_profit_in_paid_out_now():
    book = {'fundedUsd': 7.0, 'sol': 0.01, 'bankSol': 0.02, 'bankUsd': 2.0}
    out, moved = fw.enforce_principal_floor(book, equity_usd=8.0, sol_px=100.0)
    assert moved == 0.01
    assert out['bankSol'] == 0.01 and out['sol'] == 0.02 and out['bankUsd'] == 1.0


def test_rebuy_never_spends_cash_the_owner_sold_out_by_hand():
    card = {'rounds': 3, 'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'symbol': 'SOL', 'units': 0.0, 'entry': 100},
                                  {'mint': 'RUN', 'pairAddress': 'R', 'symbol': 'RUN', 'units': 0.0, 'entry': 0.002}]}
    book = {'sol': 0.03, 'manualCashSol': 0.03, 'legs': {}}   # every SOL in the card is the owner's ✂ cash
    c = fw.sync_card(card, book, {'S': 100, 'R': 0.002}, 100)
    assert not c['legs'][1].get('buying')
    assert not [o for o in fw.orders('t', c, book, {'S': 100, 'R': 0.002}, 100, {**fw.DEFAULT_CFG, 'armed': True}, 1) if o['side'] == 'buy' and o['mint'] == 'RUN']


def test_run_report_reads_flaws_from_the_ledger():
    L = [{'card': 'c', 'side': 'topup', 'usd': 10, 'at': 0, 'status': 'done'}]
    t = 60
    for i in range(6):   # 6 round trips: bought, sold 5 min later for less
        L.append({'card': 'c', 'side': 'buy', 'mint': f'M{i}', 'symbol': f'M{i}', 'usd': 2.0, 'feeUsd': 0.05, 'px': 1.02, 'midPx': 1.0, 'status': 'filled', 'sig': f'b{i}', 'at': t})
        L.append({'card': 'c', 'side': 'sell', 'mint': f'M{i}', 'symbol': f'M{i}', 'usd': 1.9, 'feeUsd': 0.05, 'px': 0.98, 'midPx': 1.0, 'status': 'filled', 'sig': f's{i}', 'at': t + 300})
        t += 600
    L += [{'card': 'c', 'side': 'buy', 'mint': 'X', 'status': 'failed', 'err': 'expired — never landed', 'at': t}] * 3
    L += [{'card': 'other', 'side': 'buy', 'mint': 'Z', 'usd': 99, 'status': 'filled', 'sig': 'z', 'at': 1}]
    r = fw.run_report(L, 'c', 3600, funded_usd=10, equity_usd=9.0, hold_sol_pct=2.0)
    assert r['swaps'] == 12 and r['trips'] == 6 and r['feesUsd'] == 0.6 and r['feesPct'] == 6.0
    assert r['slipPct'] == 2.0 and r['failed'] == 3 and r['pnlPct'] == -10.0
    kinds = ' '.join(f['what'] for f in r['flaws'])
    assert 'Network fees' in kinds and 'round trips' in kinds and 'overtrading' in kinds and 'holding SOL' in kinds
    assert r['verdict'] == 'fix'
    clean = fw.run_report([{'card': 'c', 'side': 'topup', 'usd': 50, 'at': 0}], 'c', 7200, funded_usd=50)
    assert clean['flaws'] == [] and clean['verdict'] == 'clean'


def test_buys_never_dip_into_cash_the_owner_sold_out():
    card = {'legs': [{'mint': 'M', 'pairAddress': 'pm', 'symbol': 'M', 'units': 10.0, 'entry': 1.0}]}   # target wants $10 of M
    book = {'sol': 0.1, 'manualCashSol': 0.08, 'legs': {}}                                              # $10 SOL, $8 of it is ✂ cash
    buys = [o for o in fw.orders('t', card, book, {'pm': 1.0}, 100.0, {**fw.DEFAULT_CFG, 'armed': True, 'minOrderUsd': 0.1}, 1) if o['side'] == 'buy']
    assert buys and buys[0]['usd'] <= 2.0 + 1e-9


def test_rent_sweep_runs_every_two_rounds_of_the_real_clock():
    assert fw.close_every(5 / 60) == 600 and fw.close_every(0.25) == 1800 and fw.close_every(0) == 1800 and fw.close_every(0.1) == 720

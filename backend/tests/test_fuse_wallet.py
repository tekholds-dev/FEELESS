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


def test_rent_is_a_card_deposit_and_network_fees_never_come_out_of_the_card():
    book = fw.new_book(100, 100.0, 0)                                   # 1 SOL in the card
    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M', 'lamports': 200_000_000}
    b, r = fw.apply_fill(book, {**order, 'rentDeposit': 0.00204}, {'atoms': 20_000_000, 'decimals': 6, 'sol': -0.20204, 'feeSol': 0.00001}, 100.0)   # 0.2 swap + 0.00204 rent
    assert abs(b['sol'] - 0.79796) < 1e-9 and abs(b['rentHeldSol'] - 0.00204) < 1e-9 and r['usd'] == 20.0   # swap + its rent DEPOSIT
    assert abs(fw.book_value(b, {}, 100.0) - 100.0) < 1e-6   # the deposit is still the card's money (no P&L move)


def test_wallet_fronts_fees_for_5_rounds_then_the_card_pays():
    order = {'side': 'buy', 'mint': 'M', 'pair': 'pm', 'symbol': 'M', 'lamports': 200_000_000, 'rentDeposit': 0.00204}
    fill = {'atoms': 20_000_000, 'decimals': 6, 'sol': -0.20204, 'feeSol': 0.00001}
    early, _ = fw.apply_fill(fw.new_book(100, 100.0, 0), order, fill, 100.0)
    late, _ = fw.apply_fill(fw.new_book(100, 100.0, 0), {**order, 'cardPays': True}, fill, 100.0)
    assert abs(early['sol'] - 0.79796) < 1e-9 and abs(late['sol'] - (0.79796 - 0.00001)) < 1e-9   # card pays the fee from round 5 (rent = its deposit)
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
    assert run['buying'] and abs(run['wantUnits'] * 0.002 - (1.5 - fw.GAS_RENT_SOL * 100)) < 0.01 and abs(c['legs'][0]['units'] - 0.015) < 1e-9
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
    b2, out2 = fw.note_miss({}, 'X', 0, 'x'); b2, out2 = fw.note_miss(b2, 'X', 1900, 'x')   # outside the window → count restarts
    assert not out2 and b2['misses']['X']['n'] == 1


def test_quietly_relogged_skip_still_benches_and_thin_pool_benches_at_once():
    import fuse_wallet as fw
    # a skip re-logged once per QUIET_SEC must still reach the bench (it never did when the window was shorter than the quiet gap)
    assert fw.MISS_WINDOW >= 2 * fw.QUIET_SEC
    b, out = fw.note_miss({}, 'Q', 0, 'price 6% above market'); b, out = fw.note_miss(b, 'Q', fw.QUIET_SEC + 1, 'price 6% above market')
    assert out and fw.benched(b, fw.QUIET_SEC + 2) == {'Q'}
    # 💧 a thin pool won't deepen in minutes: the FIRST refusal benches it so the engine swaps the coin now (both refusal wordings)
    for why in ('pool too thin: $9,000 liquidity < $20,000 (real buys)', 'live pool too thin: $9,000 liquidity < $20,000'):
        b, out = fw.note_miss({}, 'T', 0, why)
        assert out and fw.benched(b, 10) == {'T'}


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
    book = {'sol': 0.0, 'legs': {'M1': {'atoms': 1_100_000, 'decimals': 6, 'pair': 'P1', 'symbol': 'A', 'entryPx': 1.0}}}   # no idle SOL: this is about the band
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
    assert fw.priority_cap(0, 0) == 10_000 and fw.priority_cap(0, 2) == 30_000 and fw.priority_cap(2, 4) == 70_000   # no SOL price: small steps, capped


def test_every_keeper_swap_costs_way_under_a_penny_even_a_retry():
    cost = lambda a, b, px: (fw.priority_cap(a, b, px) + fw.BASE_LAMPORTS) / 1e9 * px
    for px in (60.0, 119.0, 200.0, 400.0):
        assert cost(0, 0, px) <= 0.0025                                                  # first try (the 5,000-lamport signature fee is most of it when SOL is dear)
        assert cost(1, 0, px) <= 0.0033 and cost(0, 1, px) <= 0.0033                     # one retry / one recent miss
        assert all(cost(a, b, px) <= 0.0051 for a in range(4) for b in range(5))         # never over half a cent, whatever happens
        assert fw.priority_cap(1, 0, px) > fw.priority_cap(0, 0, px)                     # a retry still pays a little more to land
    assert fw.priority_cap(0, 0, 119.0) == 3_403 and round(cost(0, 0, 119.0), 4) == 0.001   # a tenth of a cent at today's SOL


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


def test_recovered_old_keeper_coin_force_sell_goes_back_into_the_card():
    book = {'sol': 0.0, 'legs': {'OLD': {'atoms': 2_000_000, 'decimals': 6, 'pair': 'pold', 'symbol': 'AGENTCAT',
                                          'entryPx': 0.5, 'costUsd': 1.0, 'manualCash': True, 'recovered': True}}}
    card = {'legs': [], 'cash': 0.0}
    cfg = {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'A', 'minOrderUsd': 0.25}
    sells = [o for o in fw.orders('safe', card, book, {'pold': 0.5}, 100.0, cfg, 10) if o['side'] == 'sell']
    assert sells and sells[0]['mint'] == 'OLD' and not sells[0].get('manualCash')     # owner: recovered cash goes back to work
    assert sells[0]['why'] == 'recovered coin sold back into the card'

    filled, _ = fw.apply_fill(book, sells[0], {'atoms': -2_000_000, 'decimals': 6, 'sol': 0.01, 'feeSol': 0.0}, 100.0)
    assert not filled['legs'] and filled['sol'] == 0.01 and not filled.get('manualCashSol')


def test_recovered_coin_below_normal_dust_floor_still_gets_a_sell_attempt():
    book = {'sol': 0.0, 'legs': {'DEAD': {'atoms': 10_000, 'decimals': 6, 'pair': 'pd', 'symbol': 'DEAD',
                                           'entryPx': 1.0, 'costUsd': 1.0, 'manualCash': True, 'recovered': True}}}
    cfg = {**fw.DEFAULT_CFG, 'armed': True, 'walletId': 'w', 'address': 'A', 'minOrderUsd': 0.25}
    sells = fw.orders('safe', {'legs': []}, book, {'pd': 0.001}, 100.0, cfg, 10)
    assert len(sells) == 1
    assert sells[0]['side'] == 'sell' and sells[0]['mint'] == 'DEAD'

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


def test_card_paid_network_fees_are_tracked_so_pnl_can_leave_them_out():
    b = {'sol': 0.1, 'legs': {}}
    order = {'side': 'sell', 'mint': 'M', 'cardPays': True, 'pair': 'P', 'symbol': 'M'}
    b2, _ = fw.apply_fill({**b, 'legs': {'M': {'atoms': 1000, 'costUsd': 1.0, 'entryPx': 0.001, 'decimals': 6}}}, order, {'atoms': -1000, 'decimals': 6, 'sol': 0.0099, 'feeSol': 0.00001}, 100.0)
    assert b2['cardFeesSol'] == 0.00001 and abs(b2['sol'] - (0.1 + 0.0099 - 0.00001)) < 1e-9     # paid from card SOL, and remembered
    b3, _ = fw.apply_fill(b2, {**order, 'cardPays': False}, {'atoms': 0, 'decimals': 6, 'sol': 0.0, 'feeSol': 0.00002}, 100.0)
    assert b3['cardFeesSol'] == 0.00001                                                              # reserve-paid fees never count as the card's


def test_money_trail_accounts_for_every_dollar():
    import fuse_wallet as fw
    rows = [{'id': 't', 'card': 'degen', 'side': 'topup', 'usd': 10.0, 'at': 0, 'status': 'done'},
            {'id': 'b1', 'card': 'degen', 'side': 'buy', 'mint': 'A', 'symbol': 'AAA', 'usd': 4.0, 'at': 100, 'status': 'filled', 'feeUsd': 0.01},
            {'id': 'b1', 'card': 'degen', 'side': 'buy', 'mint': 'A', 'symbol': 'AAA', 'usd': 4.0, 'at': 100, 'status': 'filled', 'feeUsd': 0.01},   # dup row
            {'id': 's1', 'card': 'degen', 'side': 'sell', 'mint': 'A', 'symbol': 'AAA', 'usd': 3.0, 'at': 200, 'status': 'filled', 'realizedPnlUsd': -1.0, 'feeUsd': 0.01},
            {'id': 'b2', 'card': 'degen', 'side': 'buy', 'mint': 'B', 'symbol': 'BBB', 'usd': 2.0, 'at': 300, 'status': 'filled'},
            {'id': 'k', 'card': 'degen', 'side': 'buy', 'mint': 'C', 'at': 400, 'status': 'skipped', 'err': 'live pool too thin: $9,000 liquidity < $20,000'}]
    # cash: 10 − 4 + 3 − 2 = 7 SOL-$ less 0.05 the card paid in fees; B held: 2 units at $1 cost, now $1.50 each
    book = {'fundedUsd': 10.0, 'sol': 6.95 / 100, 'cardFeesSol': 0.05 / 100, 'legs': {'B': {'atoms': 2_000_000, 'decimals': 6, 'symbol': 'BBB', 'costUsd': 2.0}}}
    t = fw.money_trail(rows, book, 0, 1000, 100.0, {'B': 1.5})
    assert t['swaps'] == 3 and t['heldNowUsd'] == 3.0 and t['cashUsd'] == 6.95 and t['nowUsd'] == 9.95
    assert t['realizedAllUsd'] == -1.0 and t['unrealizedUsd'] == 1.0 and t['cardFeesUsd'] == 0.05
    assert t['resultUsd'] == 0.0 and t['unexplainedUsd'] == 0.0            # −$1 realized + $1 still-held move; fees apart
    assert t['problems'][0]['why'].startswith('skipped: live pool too thin') and t['coins'][0]['symbol'] == 'AAA'


def test_rent_is_the_cards_own_deposit_and_comes_back_into_the_card():
    import fuse_wallet as fw
    book = {'sol': 0.01, 'fundedUsd': 1.0, 'legs': {}}
    # a buy that opened a new coin account: the card pays its 0.005 swap AND the 0.002 rent deposit from its own SOL
    b, _ = fw.apply_fill(book, {'side': 'buy', 'mint': 'M', 'lamports': 5_000_000, 'symbol': 'M', 'rentDeposit': 0.002}, {'atoms': 10, 'decimals': 0, 'sol': -0.007, 'feeSol': 0.0}, 100.0)
    assert round(b['sol'], 6) == 0.003 and round(b['rentHeldSol'], 6) == 0.002 and not b.get('rentSol')
    assert round(fw.book_value(b, {}, 100.0), 4) == round(0.005 * 100 + 0.5, 4)        # deposit counted → value (and P&L) unchanged
    books, cr = fw.rent_back({'blaze': b, 'gold': {'sol': 0}}, [{'mint': 'M', 'lamports': 2_039_280}, {'mint': 'Z', 'lamports': 2_000_000}], 100.0)
    g = books['blaze']
    assert cr == {'blaze': 0.002} and round(g['sol'], 6) == 0.005 and g['rentHeldSol'] == 0.0 and g['fundedUsd'] == 1.0   # never > the deposit
    assert books['gold']['sol'] == 0                                                   # rent no card paid stays on the reserve
    assert fw.rent_back(books, [{'mint': 'M', 'lamports': 2_039_280}], 100.0)[1] == {}  # each deposit comes back once
    # a card with too little SOL: the reserve fronts the part it can't cover (and gets that part back)
    b2, _ = fw.apply_fill({'sol': 0.006, 'legs': {}}, {'side': 'buy', 'mint': 'N', 'lamports': 5_000_000, 'rentDeposit': 0.002}, {'atoms': 1, 'decimals': 0, 'sol': -0.007, 'feeSol': 0.0}, 100.0)
    assert round(b2['rentHeldSol'], 6) == 0.001 and round(b2['rentSol'], 6) == 0.001 and round(b2['sol'], 6) == 0.0
    b3, _ = fw.apply_fill({'sol': 0.01, 'legs': {}}, {'side': 'buy', 'mint': 'N', 'lamports': 5_000_000}, {'atoms': 1, 'decimals': 0, 'sol': -0.007, 'feeSol': 0.0}, 100.0)
    assert round(b3['sol'], 6) == 0.005 and round(b3['rentSol'], 6) == 0.002          # no deposit set aside by `orders` → the reserve fronts it


def test_phantom_rent_credits_are_undone_once():
    import fuse_wallet as fw
    ledger = [{'side': 'close', 'status': 'credited', 'credits': {'blaze': 0.1}}, {'side': 'close', 'status': 'credited', 'credits': {'blaze': 0.09}},
              {'side': 'close', 'status': 'sent', 'sol': 0.5}]
    books, gone = fw.undo_rent_credits({'blaze': {'sol': 0.23, 'fundedUsd': 33.06, 'rentMints': {'x': 1}}}, ledger, 120.0)
    assert gone == {'blaze': 0.19} and round(books['blaze']['sol'], 6) == 0.04 and books['blaze']['fundedUsd'] == 10.26 and 'rentMints' not in books['blaze']
    assert not fw.reconcile_sol(0.0573, books)                                           # books fit the wallet again → no halt


def test_a_buy_that_never_lands_is_flagged_stuck():
    import fuse_wallet as fw
    card = {'legs': [{'mint': 'A', 'pairAddress': 'Pa', 'buying': True, 'buyingSince': 0},
                     {'mint': 'B', 'pairAddress': 'Pb', 'buying': True, 'buyingSince': 500},
                     {'mint': 'C', 'pairAddress': 'Pc', 'buying': True, 'buyingSince': 590},
                     {'mint': 'D', 'pairAddress': 'Pd', 'units': 3}]}
    assert fw.stuck_buys(card, 610) == ['Pa'] and fw.stuck_buys(card, 610, {'C'}) == ['Pa', 'Pc']   # benched = at once
    # ⏱ a REFUSED buy is re-picked 15s after the refusal (not a tick later) — but never while its transaction is still in flight
    assert fw.stuck_buys(card, 610, missed={'B': {'first': 600, 'last': 600}}) == ['Pa']
    assert fw.stuck_buys(card, 616, missed={'B': {'first': 600, 'last': 600}}) == ['Pa', 'Pb']
    assert fw.stuck_buys(card, 616, missed={'B': {'first': 600, 'last': 600}}, pending_mint='B') == ['Pa']
    # sync_card stamps when the wait started, and clears it when the coin lands
    c = fw.sync_card({'legs': [{'mint': 'A', 'pairAddress': 'Pa', 'role': 'runner', 'units': 2.0, 'entry': 1.0}], 'rounds': 1, 'rebuyRound': 1, 'rebuyAt': 9e12},
                     {'sol': 0.0, 'legs': {}}, {}, 100.0)
    assert c['legs'][0]['buying'] and c['legs'][0]['buyingSince'] > 0
    c2 = fw.sync_card(c, {'sol': 0.0, 'legs': {'A': {'atoms': 2, 'decimals': 0, 'costUsd': 2.0, 'entryPx': 1.0}}}, {}, 100.0)
    assert 'buyingSince' not in c2['legs'][0] and not c2['legs'][0].get('buying')


def test_coins_waiting_on_a_buy_are_funded_from_the_sol_anchor():
    import fuse_wallet as fw
    SOL = fw.SOL_MINT
    # the screenshot: SOL anchor $2.31, ORCA $1.35, $0.32 free, Ash + GOMO "buying" forever (no SOL ever reached them)
    card = {'rounds': 102, 'rebuyRound': 101, 'rebuyAt': 0, 'legs': [
        {'mint': SOL, 'pairAddress': 'Psol', 'role': 'anchor', 'units': 0.0154, 'entry': 150.0},
        {'mint': 'ORCA', 'pairAddress': 'Porca', 'role': 'anchor', 'units': 1.35, 'entry': 1.0},
        {'mint': 'ASH', 'pairAddress': 'Pash', 'role': 'runner', 'units': 0.0, 'buying': True, 'wantUnits': 1.0, 'entry': 1.0},
        {'mint': 'GOMO', 'pairAddress': 'Pgomo', 'role': 'runner', 'units': 0.0, 'buying': True, 'wantUnits': 1.0, 'entry': 1.0}]}
    book = {'sol': (2.31 + 0.32) / 150, 'legs': {'ORCA': {'atoms': 135, 'decimals': 2, 'costUsd': 1.35, 'entryPx': 1.0}}}
    prices = {'Psol': 150.0, 'Porca': 1.0, 'Pash': 1.0, 'Pgomo': 1.0}
    c = fw.sync_card(card, book, prices, 150.0)
    sol = next(l for l in c['legs'] if l['mint'] == SOL)
    assert sol['units'] * 150 < 1.2                                                    # SOL trimmed to ~an equal share
    o = fw.orders('blaze', c, book, prices, 150.0, {'minOrderUsd': 0.1, 'maxSwapUsd': 50, 'armed': True}, 0)
    buys = {x['mint']: x['usd'] for x in o if x['side'] == 'buy'}
    assert set(buys) == {'ASH', 'GOMO'} and all(v >= 0.4 for v in buys.values())        # both buys are really sent now (rent deposit set aside)


def test_auto_halt_lifts_itself_and_a_halted_card_still_sells():
    import fuse_wallet as fw
    sol_halt = {'halt': True, 'haltWhy': 'confirmed wallet SOL is below card books', 'legs': {'A': {}}}
    assert fw.halt_cleared(sol_halt, None, []) and not fw.halt_cleared(sol_halt, {'booked': 1, 'held': 0.5}, [])
    tok = {'halt': True, 'haltWhy': 'confirmed wallet token balance is below card books', 'legs': {'A': {}}}
    assert fw.halt_cleared(tok, None, ['B']) and not fw.halt_cleared(tok, None, ['A'])
    assert not fw.halt_cleared({'halt': True}, None, [])                                # the owner's own ⏸ Pause never auto-lifts
    assert not fw.halt_cleared({'halt': True, 'haltWhy': 'fill mismatch'}, None, [])
    assert fw.halt_allows_sells(sol_halt) and fw.halt_allows_sells({'halt': True}) and not fw.halt_allows_sells(tok)


def test_put_in_rebuilt_from_the_audit_trail():
    import fuse_wallet as fw
    ledger = [{'card': 'blaze', 'side': 'topup', 'usd': 3.0, 'at': 5, 'status': 'done'},          # an older run of this card
              {'card': 'blaze', 'side': 'topup', 'usd': 5.0, 'at': 100, 'status': 'done'},
              {'card': 'blaze', 'side': 'topup', 'usd': 2.0, 'at': 200, 'status': 'done'},
              {'card': 'blaze', 'side': 'withdraw', 'usd': 1.5, 'at': 300, 'status': 'done'},
              {'card': 'gold', 'side': 'topup', 'usd': 9.0, 'at': 150, 'status': 'done'}]
    assert fw.funded_from_ledger({'since': 100}, ledger, 'blaze') == 5.5


def test_a_recovery_sell_puts_its_sol_back_to_work_but_owner_cut_cash_stays_held():
    import fuse_wallet as fw
    card = {'legs': [{'mint': fw.SOL_MINT, 'pairAddress': 'S', 'units': 0.0, 'entry': 100}]}
    leg = {'atoms': 1_000_000, 'decimals': 6, 'pair': 'pb', 'symbol': 'BATON', 'entryPx': 1.0}
    rec = fw.orders('b', card, {'sol': 0.0, 'legs': {'B': {**leg, 'manualCash': True, 'recovered': True}}}, {'pb': 1.4}, 100.0, {'minOrderUsd': 0.1, 'maxSwapUsd': 5}, 0)
    cut = fw.orders('b', card, {'sol': 0.0, 'legs': {'B': {**leg, 'manualCash': True}}}, {'pb': 1.4}, 100.0, {'minOrderUsd': 0.1, 'maxSwapUsd': 5}, 0)
    assert rec[0]['side'] == 'sell' and not rec[0].get('manualCash') and 'recovered' in rec[0]['why']
    assert cut[0].get('manualCash')                                                       # ✂ owner's cash is still held apart
    b, _ = fw.apply_fill({'sol': 0.0, 'legs': {'B': dict(leg)}}, rec[0], {'atoms': -1_000_000, 'decimals': 6, 'sol': 0.014, 'feeSol': 0.0}, 100.0)
    assert not b.get('manualCashSol')                                                     # → spendable card cash


def test_the_owners_pick_is_held_to_the_floor_the_picker_promised():
    cfg = {**CFG, 'minLiqUsd': 80000, 'arenaMinLiqUsd': 25000, 'pickMinLiqUsd': 25000}
    o = {'side': 'buy', 'usd': 0.7, 'liq': 42080, 'mint': 'ORE', 'pair': 'P'}
    assert not fw.check(o, cfg, [], 0)[0]                                                # a coin the engine chose: the general $80K floor
    assert fw.check({**o, 'picked': True}, cfg, [], 0)[0]                                # the owner's own pick: the $25K floor it was accepted at
    pair = {'baseToken': {'address': 'ORE'}, 'priceUsd': '1', 'liquidity': {'usd': 42080}}
    assert not fw.live_buy_market(o, pair, cfg)[0] and fw.live_buy_market({**o, 'picked': True}, pair, cfg)[0]
    assert not fw.check({**o, 'picked': True, 'liq': 20000}, cfg, [], 0)[0]              # still a floor — never any pool
    c = card([{'mint': 'ORE', 'pairAddress': 'P', 'symbol': 'ore', 'units': 5.0, 'entry': 1.0, 'picked': True}])
    assert fw.target(c, {'P': 1.0})['ORE']['picked']
    assert [x.get('picked') for x in fw.orders('t', c, {'sol': 1.0, 'legs': {}}, {'P': 1.0}, 100.0, cfg, 0) if x['side'] == 'buy'] == [True]


def test_a_swap_keeps_the_old_coin_while_its_replacement_cannot_be_bought():
    book, c = {'sol': 0.0, 'legs': {}}, {'events': [{'kind': 'rotate', 'at': 990}]}
    b, hold = fw.hold_sells(book, c, {'NEW'}, 1000)
    assert hold and b['sellHoldAt'] == 1000
    assert fw.hold_sells(b, c, {'NEW'}, 1030)[1]                                         # still inside the 45s window
    assert not fw.hold_sells(b, c, {'NEW'}, 1046)[1]                                     # never longer: the sell goes through
    b2, hold2 = fw.hold_sells(b, c, set(), 1010)
    assert not hold2 and 'sellHoldAt' not in b2                                          # replacement is buyable again → window cleared
    # protective exits and sell-alls never wait
    assert not fw.hold_sells(book, {'events': [{'kind': 'sl', 'at': 995}]}, {'NEW'}, 1000)[1]
    assert not fw.hold_sells(book, {'events': [{'kind': 'rug', 'at': 995}]}, {'NEW'}, 1000)[1]
    assert not fw.hold_sells({**book, 'defund': True}, c, {'NEW'}, 1000)[1]
    assert not fw.hold_sells({**book, 'halt': True}, c, {'NEW'}, 1000)[1]


def test_swap_steps_show_done_sending_next_in_order_and_nothing_when_idle():
    ledger = [{'card': 't', 'side': 'sell', 'symbol': 'OLD', 'mint': 'O', 'status': 'filled', 'usd': 0.6, 'at': 990},
              {'card': 't', 'side': 'buy', 'symbol': 'BAD', 'mint': 'B', 'status': 'skipped', 'usd': 0.6, 'at': 992, 'err': 'live pool too thin: $42,080 liquidity < $80,000'},
              {'card': 'x', 'side': 'buy', 'symbol': 'OTHER', 'mint': 'Z', 'status': 'filled', 'usd': 1, 'at': 995},
              {'card': 't', 'side': 'buy', 'symbol': 'ANCIENT', 'mint': 'A', 'status': 'filled', 'usd': 1, 'at': 10}]
    book = {'pending': {'side': 'buy', 'mint': 'N', 'symbol': 'NEW', 'usd': 0.59, 'sentAt': 998}}
    plan = [{'side': 'buy', 'mint': 'N', 'symbol': 'NEW', 'usd': 0.59}, {'side': 'buy', 'mint': 'M', 'symbol': 'MORE', 'usd': 0.4}]
    f = fw.swap_flow(book, ledger, 't', plan, 1000)
    assert [(x['side'], x['symbol'], x['state']) for x in f] == [('sell', 'OLD', 'done'), ('buy', 'BAD', 'failed'), ('buy', 'NEW', 'sending'), ('buy', 'MORE', 'next')]
    assert f[1]['err'] == 'live pool too thin: $42,080 liquidity < $80,000'
    assert fw.swap_flow({}, ledger, 't', [], 1000) == []                                 # nothing in flight, nothing queued → no strip


def test_a_bench_is_short_so_a_coin_can_come_back_the_same_hour():
    b, out = fw.note_miss({}, 'M', 100, 'live pool too thin: $1 liquidity < $2')
    assert out and b['benched']['M']['until'] == 100 + fw.BENCH_SEC == 1000
    for i in range(8):
        b, _ = fw.note_miss(b, 'M', 100, 'pool too thin')
    assert b['benched']['M']['until'] == 100 + fw.BENCH_MAX                              # doubling stops at 2h


def _sell_tx(owner_delta, fee, opened=(), token_delta=-50):
    keys = [{'pubkey': 'OWNER', 'signer': True}] + [{'pubkey': f'NEW{i}', 'signer': False} for i in range(len(opened))] + [{'pubkey': 'POOL', 'signer': False}]
    return {'transaction': {'message': {'accountKeys': keys}},
            'meta': {'err': None, 'fee': fee, 'preBalances': [10_000_000] + [0] * len(opened) + [5_000_000_000],
                     'postBalances': [10_000_000 + owner_delta] + list(opened) + [5_000_000_000 - 1],
                     'preTokenBalances': [{'owner': 'OWNER', 'mint': 'M', 'uiTokenAmount': {'amount': '100', 'decimals': 0}}],
                     'postTokenBalances': [{'owner': 'OWNER', 'mint': 'M', 'uiTokenAmount': {'amount': str(100 + token_delta), 'decimals': 0}}]}}


def test_rent_a_sell_route_parks_in_new_accounts_is_never_booked_as_a_price_loss():
    """The real case: baton sold for 0.00351 SOL, but the 2-hop route opened two accounts (0.00303 SOL) → the wallet only rose 0.00044."""
    tx = _sell_tx(owner_delta=386_687, fee=55_000, opened=(1_488_440, 1_539_240))
    fill = fw.fill_from_meta(tx, 'OWNER', 'M')
    assert fill['atoms'] == -50 and fill['openedSol'] == 0.00302768 and fill['sol'] == 0.000441687
    book = {'sol': 0.0, 'legs': {'M': {'atoms': 100, 'decimals': 0, 'pair': 'P', 'symbol': 'baton', 'costUsd': 0.84, 'entryPx': 0.0084}}}
    order = {'side': 'sell', 'mint': 'M', 'atoms': 50, 'usd': 0.42}
    assert fw.fill_error(order, fill, book) == ''
    b, f = fw.apply_fill(book, order, fill, 120.0)
    assert round(f['usd'], 3) == 0.416 and round(b['sol'], 9) == 0.003469367            # the card gets the swap's full price (≈ its cost)
    assert b['rentSol'] == 0.00302768                                                    # the parked rent is the reserve's to front
    assert b['legs']['M']['atoms'] == 50 and b['legs']['M']['costUsd'] == 0.42
    # a one-hop sell opens nothing → booked exactly as before
    plain = fw.fill_from_meta(_sell_tx(owner_delta=3_400_000, fee=5_000), 'OWNER', 'M')
    b2, f2 = fw.apply_fill(book, order, plain, 120.0)
    assert plain['openedSol'] == 0 and round(b2['sol'], 9) == 0.003405 and not b2.get('rentSol')
    # absurd "rent" is capped — it is never a way to invent proceeds
    assert fw.opened_sol(_sell_tx(1, 0, opened=(5_000_000_000,)), 'OWNER') == fw.OPENED_MAX_SOL


def test_route_rent_repair_checks_only_suspicious_sells_and_never_credits_more_than_the_wallet_has_free():
    ledger = [{'side': 'sell', 'status': 'filled', 'sig': 'a', 'at': 10, 'usd': 0.05, 'costUsd': 0.42, 'card': 't'},     # −87% → look
              {'side': 'sell', 'status': 'filled', 'sig': 'b', 'at': 10, 'usd': 0.40, 'costUsd': 0.42, 'card': 't'},     # normal
              {'side': 'sell', 'status': 'filled', 'sig': 'c', 'at': 10, 'usd': 0.05, 'costUsd': 0.42, 'card': 't', 'openedSol': 0.0},   # already checked
              {'side': 'buy', 'status': 'filled', 'sig': 'd', 'at': 10, 'usd': 0.05, 'costUsd': 0.42, 'card': 't'},
              {'side': 'sell', 'status': 'failed', 'sig': 'e', 'at': 10, 'usd': 0.05, 'costUsd': 0.42, 'card': 't'}]
    assert [r['sig'] for r in fw.route_fix_rows(ledger)] == ['a']
    books, credits = fw.route_fix({'t': {'sol': 0.001}}, {'t': 0.0045}, 0.01, 120.0)
    assert credits == {'t': 0.0045} and books['t']['sol'] == 0.0055
    books, credits = fw.route_fix({'t': {'sol': 0.001}}, {'t': 0.0045}, 0.002, 120.0)
    assert credits == {'t': 0.002} and books['t']['sol'] == 0.003                        # only SOL the wallet really has unassigned
    assert fw.route_fix({'t': {'sol': 0.001}}, {'t': 0.0045}, 0.0, 120.0)[1] == {}


def _swap_tx(out_atoms=-100, in_atoms=250, owner_delta=-2_044_280, fee=5_000, err=None):
    tok = lambda mint, amt: {'owner': 'OWNER', 'mint': mint, 'uiTokenAmount': {'amount': str(amt), 'decimals': 0}}
    return {'transaction': {'message': {'accountKeys': [{'pubkey': 'OWNER', 'signer': True}, {'pubkey': 'ATA', 'signer': False}]}},
            'meta': {'err': err, 'fee': fee, 'preBalances': [50_000_000, 0], 'postBalances': [50_000_000 + owner_delta, 2_039_280],
                     'preTokenBalances': [tok('OLD', 100)], 'postTokenBalances': [tok('OLD', 100 + out_atoms), tok('NEW', in_atoms)]}}


def test_one_transaction_swap_is_only_used_when_it_pays_at_least_as_much_and_its_impact_is_small():
    assert fw.c2c_ok(1000, 990, 0.4)[0] and 'more coins' in fw.c2c_ok(1000, 990, 0.4)[1]
    assert fw.c2c_ok(1000, 1000, 0.0)[0]                                                 # equal coins → still one fee less
    assert not fw.c2c_ok(980, 1000, 0.2)[0]                                              # two swaps pay more → do two swaps
    assert not fw.c2c_ok(1000, 990, 4.1)[0] and fw.c2c_ok(1000, 990, 4.0)[0]             # impact no worse than 4%
    assert not fw.c2c_ok(0, 990, 0.1)[0]
    assert fw.clean_cfg({})['coinToCoin'] is False and fw.clean_cfg({'coinToCoin': 1})['coinToCoin'] is True   # OFF until the owner flips it
    book = {'sol': 0.01, 'legs': {'OLD': {'atoms': 100, 'decimals': 0}, 'STAY': {'atoms': 5, 'decimals': 0}}}
    plan = [{'side': 'sell', 'mint': 'OLD', 'atoms': 100, 'why': 'not on the card any more'},
            {'side': 'sell', 'mint': 'STAY', 'atoms': 2, 'why': 'trimmed to the card'},
            {'side': 'sell', 'mint': 'CASH', 'atoms': 9, 'why': 'not on the card any more', 'manualCash': True},
            {'side': 'buy', 'mint': 'NEW', 'lamports': 5}, {'side': 'buy', 'mint': 'STAY', 'lamports': 5}]
    assert [(s_['mint'], b_['mint']) for s_, b_ in fw.swap_pairs(plan, book)] == [('OLD', 'NEW')]   # only a coin leaving for good ↔ a coin not held
    assert fw.swap_pairs([{**plan[0], 'atoms': 60}, plan[3]], book) == []                # a partial sell is never a swap


def test_one_transaction_swap_is_booked_from_the_chain_value_moves_coin_to_coin_and_rent_is_the_reserves():
    order = {'side': 'swap', 'mint': 'OLD', 'atoms': 100, 'toMint': 'NEW', 'toPair': 'Pn', 'toSymbol': 'NEW', 'minIn': 240}
    book = {'sol': 0.002, 'legs': {'OLD': {'atoms': 100, 'decimals': 0, 'costUsd': 0.60, 'pair': 'Po', 'symbol': 'OLD'}}}
    fill = fw.swap_fill_from_meta(_swap_tx(), 'OWNER', 'OLD', 'NEW')
    assert (fill['outAtoms'], fill['inAtoms'], fill['feeSol']) == (-100, 250, 0.000005) and round(fill['sol'], 9) == -0.00203928
    assert fw.swap_fill_error(order, fill, book) == ''
    b, f = fw.apply_swap(book, order, fill, 120.0, 0.0022)
    assert 'OLD' not in b['legs'] and b['legs']['NEW']['atoms'] == 250 and b['legs']['NEW']['costUsd'] == 0.55 and b['legs']['NEW']['pair'] == 'Pn'
    assert (f['usd'], f['costUsd'], f['realizedPnlUsd']) == (0.55, 0.60, -0.05)          # the old coin's result = what its money is worth now − its cost
    assert b['sol'] == 0.002 and b['rentSol'] == 0.00203928                              # no SOL changes hands; the new account's rent is the reserve's
    assert round(b['feesSol'], 9) == 0.000005
    paid = fw.apply_swap(book, {**order, 'cardPays': True}, fill, 120.0, 0.0022)[0]
    assert round(paid['sol'], 9) == 0.001995 and round(paid['cardFeesSol'], 9) == 0.000005   # after round 5 the card pays its own network fee
    # anything that is not exactly our swap halts instead of being booked
    assert 'exact coins' in fw.swap_fill_error(order, fw.swap_fill_from_meta(_swap_tx(out_atoms=-60), 'OWNER', 'OLD', 'NEW'), book)
    assert 'fewer coins' in fw.swap_fill_error(order, fw.swap_fill_from_meta(_swap_tx(in_atoms=200), 'OWNER', 'OLD', 'NEW'), book)
    assert 'moved SOL' in fw.swap_fill_error(order, fw.swap_fill_from_meta(_swap_tx(owner_delta=-50_000_000 + 1), 'OWNER', 'OLD', 'NEW'), book)
    assert 'moved SOL' in fw.swap_fill_error(order, fw.swap_fill_from_meta(_swap_tx(owner_delta=5_000_000), 'OWNER', 'OLD', 'NEW'), book)
    assert fw.swap_fill_from_meta(_swap_tx(err={'x': 1}), 'OWNER', 'OLD', 'NEW') is None
    flow = fw.swap_flow({'pending': {'side': 'swap', 'mint': 'OLD', 'symbol': 'OLD', 'toMint': 'NEW', 'toSymbol': 'NEW', 'usd': 0.55}}, [], 't',
                        [{'side': 'sell', 'mint': 'OLD', 'symbol': 'OLD'}, {'side': 'buy', 'mint': 'NEW', 'symbol': 'NEW'}], 1000)
    assert [(x['side'], x['symbol'], x['state']) for x in flow] == [('swap', 'OLD → $NEW', 'sending')]   # one step, not two


def test_the_card_never_pays_rent_the_reserve_carries_it_and_old_deposits_go_back_to_work():
    c = card([{'mint': 'NEW', 'pairAddress': 'P', 'symbol': 'NEW', 'units': 5.0, 'entry': 1.0}])
    plan = fw.orders('t', c, {'sol': 1.0, 'legs': {}}, {'P': 1.0}, 100.0, CFG, 0)
    assert plan and all('rentDeposit' not in o for o in plan)                             # nothing set aside from the card
    b, f = fw.apply_fill({'sol': 1.0, 'legs': {}}, plan[0], {'atoms': 5_000_000, 'decimals': 6, 'sol': -(plan[0]['lamports'] / 1e9) - 0.00204, 'feeSol': 0.000005}, 100.0)
    assert round(b['sol'], 9) == round(1.0 - plan[0]['lamports'] / 1e9, 9)                # the card paid ONLY what went into the swap
    assert round(b['rentSol'], 9) == 0.00204 and not b.get('rentHeldSol')                 # the new account's rent is on the reserve's tab
    books = {'a': {'sol': 0.001, 'rentHeldSol': 0.006, 'rentDeposits': {'M': 0.002, 'N': 0.004}, 'rentSol': 0.001}, 'b': {'sol': 0.5}}
    out, freed = fw.release_rent_deposits(books, 0.01)
    assert freed == {'a': 0.006} and out['a']['sol'] == 0.007 and out['a']['rentHeldSol'] == 0.0 and out['a']['rentDeposits'] == {} and out['a']['rentSol'] == 0.007
    assert fw.book_value(out['a'], {}, 100.0) == fw.book_value(books['a'], {}, 100.0)     # value unchanged: the money only starts working
    part, freed2 = fw.release_rent_deposits(books, 0.004)                                 # never more than the wallet has free
    assert freed2 == {'a': 0.004} and part['a']['rentHeldSol'] == 0.002 and part['a']['rentDeposits']
    assert fw.release_rent_deposits(books, 0.0)[1] == {}


def test_a_coin_with_an_order_in_flight_is_never_called_missing_and_lookalikes_are_out():
    books = {'t': {'legs': {'BP': {'atoms': 457883501}, 'K': {'atoms': 10}}, 'pending': {'side': 'sell', 'mint': 'BP'}}}
    assert fw.reconcile({'K': 10}, books) == []                                           # BP's sale landed before it was booked → not "missing"
    assert fw.reconcile({'K': 10}, {'t': {**books['t'], 'pending': None}}) == [{'mint': 'BP', 'booked': 457883501, 'held': 0}]
    majors = {'So111': ('SOL', 'Solana'), 'JUPmint': ('JUP', 'Jupiter')}
    assert fw.lookalike('SOL', 'DsjKE4', majors) and fw.lookalike('sol', 'X', majors) and fw.lookalike('JUP', 'fake', majors)
    assert not fw.lookalike('SOL', 'So111', majors) and not fw.lookalike('SOLBORN', 'X', majors) and not fw.lookalike('', 'X', majors)


def test_an_engine_cut_survives_the_sync_until_it_is_sold_or_ten_minutes_pass():
    import time
    book = {'sol': 0.0, 'legs': {'W': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'PW', 'symbol': 'WIN', 'costUsd': 0.60, 'entryPx': 0.6}}}
    leg = {'mint': 'W', 'pairAddress': 'PW', 'symbol': 'WIN', 'role': 'runner', 'units': 0.67, 'entry': 0.6, 'costUsd': 0.40, 'ride': True}
    kept = fw.sync_card({'legs': [{**leg, 'trimAt': time.time() - 30}], 'rounds': 9}, book, {'PW': 1.2}, 100.0)['legs'][0]
    assert kept['units'] == 0.67 and round(kept['costUsd'], 3) == 0.402                  # the cut stays wanted → the keeper keeps selling it
    cut_sells = [o['atoms'] for o in fw.orders('t', {'legs': [kept]}, book, {'PW': 1.2}, 100.0, {**CFG, 'minOrderUsd': 0.1}, time.time()) if o['side'] == 'sell']
    assert len(cut_sells) == 1 and abs(cut_sells[0] - 330000) <= 1
    gone = fw.sync_card({'legs': [{**leg, 'trimAt': time.time() - 700}], 'rounds': 9}, book, {'PW': 1.2}, 100.0)['legs'][0]
    assert gone['units'] == 1.0 and gone['costUsd'] == 0.60                              # 10 min on and still unsold → back to what the wallet holds
    plain = fw.sync_card({'legs': [leg], 'rounds': 9}, book, {'PW': 1.2}, 100.0)['legs'][0]
    assert plain['units'] == 1.0                                                         # no cut flag → the wallet's truth, as always
    sold = fw.sync_card({'legs': [{**leg, 'trimAt': time.time() - 30}], 'rounds': 9}, {'sol': 0.0, 'legs': {'W': {**book['legs']['W'], 'atoms': 670_000, 'costUsd': 0.402}}}, {'PW': 1.2}, 100.0)['legs'][0]
    assert sold['units'] == 0.67 and sold['costUsd'] == 0.402                            # once it sold, card and wallet simply agree


def test_the_owners_pick_floor_is_their_own_setting_and_never_under_5k():
    cfg = {**CFG, 'minLiqUsd': 80000, 'arenaMinLiqUsd': 25000}
    assert fw.clean_cfg(cfg)['pickMinLiqUsd'] == 10000 and fw.liq_floor(cfg, picked=True) == 10000   # default: a $23.8K pool is pickable
    assert fw.liq_floor(cfg) == 80000 and fw.liq_floor(cfg, arena=True) == 25000                     # the engine's own floors do not move
    assert fw.liq_floor({**cfg, 'pickMinLiqUsd': 100}, picked=True) == 5000                          # never any pool
    assert fw.liq_floor({**cfg, 'pickMinLiqUsd': 500000}, picked=True) == 25000                      # never stricter than the Arena floor
    o = {'side': 'buy', 'usd': 0.7, 'liq': 23815, 'mint': 'SIR', 'pair': 'P'}
    assert not fw.check(o, cfg, [], 0)[0] and fw.check({**o, 'picked': True}, cfg, [], 0)[0]


def test_the_owners_pick_may_use_their_own_sell_back_limit_but_never_over_10():
    o = {'usd': 1.0, 'lamports': 1_000_000, 'midPx': 0.0}
    back = lambda loss: 1_000_000 * (1 - loss / 100)
    assert not fw.buy_safety(o, 1_000_000, None, back(6.8))[0]                                          # the engine's coin: 6%
    assert not fw.buy_safety({**o, 'maxRoundtripPct': 8}, 1_000_000, None, back(6.8))[0]                # the setting only counts for a pick
    assert fw.buy_safety({**o, 'picked': True, 'maxRoundtripPct': 8}, 1_000_000, None, back(6.8))[0]
    assert not fw.buy_safety({**o, 'picked': True, 'maxRoundtripPct': 50}, 1_000_000, None, back(10.5))[0]   # capped at 10%
    assert not fw.buy_safety({**o, 'picked': True}, 1_000_000, None, back(6.8))[0] and fw.clean_cfg({})['pickSellBackPct'] == 6


def test_idle_card_cash_is_swept_into_the_coin_furthest_under_its_share_when_nothing_else_is_due():
    cfg = {**CFG, 'minOrderUsd': 0.25, 'minLiqUsd': 0, 'arenaMinLiqUsd': 0}
    bl = lambda units: {'atoms': int(units * 1e6), 'decimals': 6, 'costUsd': units, 'entryPx': 1.0}
    c = card([leg('A', 'PA', 0.30, 1.0), leg('B', 'PB', 0.60, 1.0), leg('C', 'PC', 0.60, 1.0)])
    book = {'sol': 0.0075, 'legs': {'A': bl(0.30), 'B': bl(0.60), 'C': bl(0.60)}}                 # $0.75 idle at $100 SOL
    px = {'PA': 1.0, 'PB': 1.0, 'PC': 1.0}
    o = fw.orders('t', c, book, px, 100.0, cfg, 1000)
    assert [(x['side'], x['mint'], x['why']) for x in o] == [('buy', 'A', 'idle card cash back into its coin')]
    assert abs(o[0]['usd'] - 0.45) < 0.01                                                         # up to its equal share ($0.75), not the whole pot
    locked = card([{**leg('A', 'PA', 0.30, 1.0), 'ride': True}, leg('B', 'PB', 0.60, 1.0), leg('C', 'PC', 0.60, 1.0)])
    assert fw.orders('t', locked, book, px, 100.0, cfg, 1000)[0]['mint'] in ('B', 'C')            # never a locked rider
    cut = card([{**leg('A', 'PA', 0.30, 1.0), 'trimAt': 900}, leg('B', 'PB', 0.60, 1.0), leg('C', 'PC', 0.60, 1.0)])
    o2 = fw.orders('t', cut, book, px, 100.0, cfg, 1000)                                          # nor a coin cut minutes ago …
    assert o2[0]['mint'] in ('B', 'C') and abs(o2[0]['usd'] - 0.25) < 0.01                        # … and B only up to the CARD's equal share (min order)
    two = card([{**leg('A', 'PA', 0.30, 1.0), 'trimAt': 900}, leg('B', 'PB', 0.90, 1.0)])
    assert fw.orders('t', two, {'sol': 0.005, 'legs': {'A': bl(0.30), 'B': bl(0.90)}}, px, 100.0, cfg, 1000) == []   # B is over its share: the cash waits for A
    assert fw.orders('t', c, {**book, 'manualCashSol': 0.0075}, px, 100.0, cfg, 1000) == []       # the owner's ✂ cash is never spent
    assert fw.orders('t', {**c, 'holdCashUsd': 0.75}, book, px, 100.0, cfg, 1000) == []           # nor cash held for them
    hold = card([leg('A', 'PA', 0.30, 1.0), leg('B', 'PB', 0.60, 1.0), {**leg('S', 'PS', 0.0, 1.0), 'placeholder': True, 'reserveUsd': 0.6}])
    assert fw.orders('t', hold, {'sol': 0.0075, 'legs': {'A': bl(0.30), 'B': bl(0.60)}}, px, 100.0, cfg, 1000) == []   # a reserved seat keeps its money ($0.15 left < min)
    assert fw.orders('t', c, {**book, 'sol': 0.001}, px, 100.0, cfg, 1000) == []                  # dust stays
    # 🔁 no buy-then-trim loop: cash waits 5 min after a failed / refused buy (the engine is re-picking that seat) …
    assert fw.orders('t', c, {**book, 'misses': {'X': {'n': 1, 'last': 900}}}, px, 100.0, cfg, 1000) == []
    assert fw.orders('t', c, {**book, 'misses': {'X': {'n': 1, 'last': 600}}}, px, 100.0, cfg, 1000)[0]['mint'] == 'A'
    # … and a coin SOLD minutes ago (trimmed for a new seat, any reason) is never bought straight back
    sold = fw.apply_fill({**book, 'legs': {**book['legs'], 'A': bl(0.60)}}, {'side': 'sell', 'mint': 'A', 'pair': 'PA', 'symbol': 'A', 'at': 950, 'usd': 0.3},
                         {'atoms': -300000, 'decimals': 6, 'sol': 0.0, 'feeSol': 0.0}, 100.0)
    sold = sold[0] if isinstance(sold, tuple) else sold
    assert sold['soldAt'] == {'A': 950} and fw.held_units(sold, 'A') == 0.30
    assert fw.orders('t', c, sold, px, 100.0, cfg, 1000)[0]['mint'] in ('B', 'C')
    assert fw.orders('t', c, sold, px, 100.0, cfg, 950 + fw.TRIM_SEC + 1)[0]['mint'] == 'A'


def test_a_small_token_shortage_is_fitted_to_the_wallet_and_a_big_one_still_halts():
    books = {'t': {'legs': {'W': {'atoms': 21_735_673, 'decimals': 6, 'symbol': 'WAIF', 'costUsd': 0.63}, 'B': {'atoms': 1000, 'decimals': 0, 'symbol': 'BIG'}}}}
    miss = fw.reconcile({'W': 21_647_820, 'B': 500}, books)
    assert {m['mint'] for m in miss} == {'W', 'B'}
    out, fits = fw.fit_small_shortage(books, miss)
    assert out['t']['legs']['W']['atoms'] == 21_647_820 and out['t']['legs']['W']['costUsd'] == 0.63 and [f['symbol'] for f in fits] == ['WAIF']
    assert out['t']['legs']['B']['atoms'] == 1000                                               # 50% short: not fitted …
    assert [m['mint'] for m in fw.reconcile({'W': 21_647_820, 'B': 500}, out)] == ['B']          # … it still halts
    two = {'a': {'legs': {'W': {'atoms': 100}}}, 'b': {'legs': {'W': {'atoms': 100}}}}
    assert fw.fit_small_shortage(two, [{'mint': 'W', 'booked': 200, 'held': 199}])[1] == []      # two cards hold it: left to the halt
    assert fw.fit_small_shortage(books, [{'mint': 'W', 'booked': 21_735_673, 'held': 0}])[1] == []


def test_only_one_process_can_hold_the_keeper_lock(tmp_path):
    import single, subprocess, sys, os
    p = tmp_path / 'keeper.lock'
    assert single.acquire(p) and single.acquire(p)                                               # ours, and asking again is fine
    code = f"import sys; sys.path.insert(0, {os.path.dirname(single.__file__)!r}); import single; print(single.acquire({str(p)!r}))"
    assert subprocess.run([sys.executable, '-c', code], capture_output=True, text=True).stdout.strip() == 'False'   # a second process: refused
    single.release(p)
    assert subprocess.run([sys.executable, '-c', code], capture_output=True, text=True).stdout.strip() == 'True'    # free again once released


def test_a_safety_refusal_stands_for_two_minutes_but_a_busy_route_is_retried():
    cfg = {**CFG, 'minLiqUsd': 0, 'arenaMinLiqUsd': 0}
    c = card([leg('A', 'PA', 1.0, 1.0)])
    book = lambda why, last: {'sol': 1.0, 'legs': {}, 'misses': {'A': {'n': 1, 'first': last, 'last': last, 'why': why}}}
    buys = lambda b, now: [o for o in fw.orders('t', c, b, {'PA': 1.0}, 100.0, cfg, now) if o['side'] == 'buy']
    assert buys(book('sells back for 12.7% less (> 6%)', 1000), 1060) == []            # refused a minute ago: not asked again
    assert buys(book('sells back for 12.7% less (> 6%)', 1000), 1130)                  # two minutes later: a fresh look
    assert buys(book('Jupiter route unavailable (HTTP 429)', 1000), 1010)              # a busy route is not a verdict on the coin


def test_the_owners_pick_of_a_pump_curve_coin_is_judged_on_the_curves_depth_the_engine_never_is():
    cfg = fw.clean_cfg({'minLiqUsd': 80000, 'pickMinLiqUsd': 10000})
    pair = {'dexId': 'pumpfun', 'priceUsd': '0.00003739', 'marketCap': 37393, 'baseToken': {'address': 'M'}}
    ok, why, snap = fw.live_buy_market({'side': 'buy', 'mint': 'M', 'picked': True}, pair, cfg)
    assert ok and 21000 < snap['liq'] < 23000
    ok2, why2, _ = fw.live_buy_market({'side': 'buy', 'mint': 'M'}, pair, cfg)             # not a pick → no pool = refused, as before
    assert not ok2 and 'too thin' in why2
    tiny = {**pair, 'marketCap': 4000}                                                    # a curve barely started is under the pick floor
    assert not fw.live_buy_market({'side': 'buy', 'mint': 'M', 'picked': True}, tiny, cfg)[0]


def test_money_that_is_not_the_cards_is_off_its_value_at_once_never_spent_and_leaves_as_cash_appears():
    bl = lambda units: {'atoms': int(units * 1e6), 'decimals': 6, 'costUsd': units, 'entryPx': 1.0, 'pair': 'PA'}
    book = {'sol': 0.002, 'owedOutSol': 0.0125, 'fundedUsd': 5.0, 'legs': {'A': bl(2.0)}}
    assert fw.book_value(book, {'PA': 1.0}, 100.0) == round(2.0 + 0.2 - 1.25, 6)            # true value now, before any SOL moved
    b1, out = fw.settle_owed(book)
    assert out == 0.002 and b1['sol'] == 0 and abs(b1['owedOutSol'] - 0.0105) < 1e-9 and b1['fundedUsd'] == 5.0   # PUT IN never changes
    assert fw.book_value(b1, {'PA': 1.0}, 100.0) == fw.book_value(book, {'PA': 1.0}, 100.0)  # moving it out changes nothing
    b2, out2 = fw.settle_owed({**b1, 'sol': 0.02})                                          # a sale landed → the rest leaves, the surplus stays
    assert abs(out2 - 0.0105) < 1e-9 and b2['owedOutSol'] == 0 and abs(b2['sol'] - 0.0095) < 1e-9 and fw.settle_owed(b2)[1] == 0.0
    assert fw.settle_owed({'sol': 0.01, 'manualCashSol': 0.01, 'owedOutSol': 0.005})[1] == 0.0   # the owner's ✂ cash is not touched
    # the keeper never spends owed SOL: $0.75 idle, $0.60 of it owed → nothing to sweep
    cfg = {**CFG, 'minOrderUsd': 0.25, 'minLiqUsd': 0, 'arenaMinLiqUsd': 0}
    c = card([leg('A', 'PA', 0.30, 1.0), leg('B', 'PB', 0.60, 1.0)])
    bk = {'sol': 0.0075, 'legs': {'A': {**bl(0.30)}, 'B': {**bl(0.60), 'pair': 'PB'}}}
    assert fw.orders('t', c, bk, {'PA': 1.0, 'PB': 1.0}, 100.0, cfg, 1000) and fw.orders('t', c, {**bk, 'owedOutSol': 0.006}, {'PA': 1.0, 'PB': 1.0}, 100.0, cfg, 1000) == []
    assert fw.sync_card(c, {**bk, 'owedOutSol': 0.006}, {'PA': 1.0, 'PB': 1.0}, 100.0)['cash'] == 0.15


def test_the_smallest_order_is_sized_to_the_cards_seats_so_a_tiny_card_can_still_fill_them():
    cfg = fw.clean_cfg({'minOrderUsd': 0.25})
    assert fw.min_order(cfg) == 0.25 and fw.min_order(cfg, 5.0, 4) == 0.25           # $1.25 seats: the owner's minimum stands
    assert fw.min_order(cfg, 0.99, 4) == 0.1 and fw.min_order(cfg, 1.6, 4) == 0.16   # $0.25 / $0.40 seats: 40% of a seat, never under $0.10
    assert fw.min_order(fw.clean_cfg({'minOrderUsd': 0.1}), 20, 4) == 0.1            # never ABOVE the owner's setting
    # a $0.99 card, 4 seats, three coins held + $0.20 cash: the 4th coin's $0.20 buy is sent (it was skipped at a flat $0.25 minimum)
    bl = lambda units, pair: {'atoms': int(units * 1e6), 'decimals': 6, 'costUsd': units, 'entryPx': 1.0, 'pair': pair}
    c = {**card([leg('A', 'PA', 0.26, 1.0), leg('B', 'PB', 0.27, 1.0), leg('C', 'PC', 0.26, 1.0), {**leg('D', 'PD', 0.0, 1.0), 'buying': True, 'wantUnits': 0.20}]), 'seats': 4}
    book = {'sol': 0.0021, 'legs': {'A': bl(0.26, 'PA'), 'B': bl(0.27, 'PB'), 'C': bl(0.26, 'PC')}}
    o = fw.orders('t', c, book, {'PA': 1.0, 'PB': 1.0, 'PC': 1.0, 'PD': 1.0}, 100.0, {**CFG, 'minOrderUsd': 0.25, 'minLiqUsd': 0, 'arenaMinLiqUsd': 0}, 1000)
    assert [(x['side'], x['mint']) for x in o] == [('buy', 'D')] and abs(o[0]['usd'] - 0.20) < 0.011


def test_a_small_card_holds_only_the_seats_it_can_really_fill():
    assert fw.fit_seats(0.39, 4) == 3            # $0.0975 a seat could never be sent → 3 seats at $0.13
    assert fw.fit_seats(0.50, 4) == 4 and fw.fit_seats(5.0, 4) == 4 and fw.fit_seats(5.0, 6) == 6
    assert fw.fit_seats(0.30, 6) == 2 and fw.fit_seats(0.20, 4) == 1 and fw.fit_seats(0.0, 4) == 4 and fw.fit_seats(1.0, 0) == 0
    assert fw.min_order({}, 0.39, fw.fit_seats(0.39, 4)) <= 0.39 / 3


def test_a_top_up_lifts_every_seat_toward_an_equal_share_not_the_one_coin_that_is_held():
    L = lambda sym, units=0.0, **kw: {'symbol': sym, 'mint': sym, 'pairAddress': sym, 'role': 'runner', 'units': units, 'entry': 1.0, 'costUsd': units, **kw}
    card = {'legs': [L('HELD', 0.10), L('W1', buying=True, wantUnits=0.10), L('W2', buying=True, wantUnits=0.10), L('W3', buying=True, wantUnits=0.10)], 'cash': 0.0, 'startUsd': 0.4}
    out = fw.topup_card(card, 2.0, {k: 1.0 for k in ('HELD', 'W1', 'W2', 'W3')}, 100.0, current_usd=0.4)
    by = {l['symbol']: l for l in out['legs']}
    assert abs(by['HELD']['units'] - 0.6) < 1e-6                                  # $0.60, not $2.10
    assert all(abs(by[k]['wantUnits'] - 0.6) < 1e-6 and by[k]['buying'] for k in ('W1', 'W2', 'W3'))
    ride = fw.topup_card({'legs': [L('RIDE', 1.0, ride=True), L('A', 0.5), L('B', 0.5)], 'cash': 0.0, 'startUsd': 2.0}, 1.0, {'RIDE': 1.0, 'A': 1.0, 'B': 1.0}, 100.0, current_usd=2.0)
    assert [round(l['units'], 6) for l in ride['legs']] == [1.0, 1.0, 1.0]         # a rider is never topped up


def test_an_exit_that_keeps_failing_gets_more_slippage_and_any_route_a_buy_never_does():
    F = lambda at, side='sell', st='failed', mint='M': {'card': 'c', 'mint': mint, 'side': side, 'status': st, 'at': at}
    assert fw.sell_escalation([], 'c', 'M', 1000.0, 100) == (100, 300, False)
    assert fw.sell_escalation([F(900)], 'c', 'M', 1000.0, 100) == (300, 500, True)
    assert fw.sell_escalation([F(800), F(900), F(950)], 'c', 'M', 1000.0, 100) == (700, 800, True)
    assert fw.sell_escalation([F(900)] * 9, 'c', 'M', 1000.0, 100)[0] == 800                       # never past 8%
    assert fw.sell_escalation([F(10)], 'c', 'M', 1000.0, 100)[2] is False                            # an old failure is forgotten
    assert fw.sell_escalation([F(900, 'buy'), F(900, st='filled'), F(900, mint='X')], 'c', 'M', 1000.0, 100)[2] is False


def test_dollar_named_tickers_are_never_the_engines_choice():
    for sym in ('USDF', 'USDP', 'USDD', 'usd1', '$USDC', 'FDUSD', 'PYUSD', 'EURC', 'USDT'):
        assert fw.dollar_named(sym), sym
    for sym in ('GOMO', 'Frank', 'SNARKSTR', 'USELESS', 'SI', 'UDR', 'JUP', '', None):
        assert not fw.dollar_named(sym), sym


def test_a_new_coin_opens_its_seat_even_under_the_top_up_minimum():
    card = {'legs': [{'mint': 'NEW', 'pairAddress': 'pN', 'symbol': 'NEW', 'role': 'runner', 'units': 0.0, 'wantUnits': 0.09, 'buying': True, 'entry': 1.0, 'picked': True},
                     {'mint': 'OLD', 'pairAddress': 'pO', 'symbol': 'OLD', 'role': 'runner', 'units': 1.0, 'entry': 1.0}], 'seats': 4}
    book = {'sol': 0.01, 'legs': {'OLD': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'pO', 'symbol': 'OLD', 'costUsd': 1.0}}}
    cfg = fw.clean_cfg({'minOrderUsd': 0.25, 'maxSwapUsd': 5})
    plan = fw.orders('c', card, book, {'pN': 1.0, 'pO': 1.0}, 100.0, cfg, 1000.0)
    buy = [o for o in plan if o['side'] == 'buy' and o['mint'] == 'NEW']
    assert buy and abs(buy[0]['usd'] - 0.09) < 0.01                     # $0.09 opens the seat (it used to be dropped without a word)
    card['legs'][0]['wantUnits'] = 0.03
    assert not [o for o in fw.orders('c', card, book, {'pN': 1.0, 'pO': 1.0}, 100.0, cfg, 1000.0) if o['side'] == 'buy' and o['mint'] == 'NEW']   # dust still is not sent


def test_rent_story_counts_what_came_back_and_what_is_parked():
    L = [{'side': 'close', 'status': 'credited', 'sol': 0.004, 'n': 2, 'sig': 's2', 'at': 1000.0 - 90000}, {'side': 'close', 'status': 'sent', 'sol': 0.006, 'at': 900.0},
         {'side': 'close', 'status': 'credited', 'sol': 0.006, 'n': 3, 'sig': 's1', 'at': 1000.0}, {'side': 'buy', 'status': 'filled', 'sol': 9, 'at': 1000.0}]   # oldest first, like the ledger
    r = fw.rent_story(L, 1100.0, {'sol': 0.015, 'accounts': 10, 'empty': 4}, 120.0)
    assert r['back24Sol'] == 0.006 and r['sweeps24'] == 1 and r['lastAt'] == 1000.0 and r['parkedSol'] == 0.015 and r['parkedUsd'] == 1.8 and r['accounts'] == 10
    assert r['rows'][0]['sig'] == 's1' and len(r['rows']) == 2 and r['back24Usd'] == 0.72
    assert fw.rent_story([], 1100.0)['parkedSol'] is None and fw.rent_story([], 1100.0)['back24Sol'] == 0


def test_a_stopped_coins_reserved_seat_is_never_bought_back():
    import fuse_wallet as fw
    SOL = fw.SOL_MINT
    # $TikPad hit its stop with no replacement ready: the seat is a placeholder that still carries TikPad's mint (and, from an
    # earlier sync, even its units). The wallet has already sold it — its SOL is card cash.
    card = {'rounds': 400, 'rebuyRound': 399, 'rebuyAt': 0, 'legs': [
        {'mint': 'SK', 'pairAddress': 'Psk', 'role': 'runner', 'units': 2.0, 'entry': 1.0},
        {'mint': 'TIK', 'pairAddress': 'Ptik', 'role': 'runner', 'units': 1.64, 'costUsd': 1.64, 'wantUnits': 1.64, 'entry': 1.0, 'placeholder': True, 'reserveUsd': 1.64}]}
    book = {'sol': 1.64 / 150, 'legs': {'SK': {'atoms': 200, 'decimals': 2, 'costUsd': 2.0, 'entryPx': 1.0}}}
    prices = {'Psk': 1.0, 'Ptik': 0.4}
    c = fw.sync_card(card, book, prices, 150.0)
    tik = next(l for l in c['legs'] if l['mint'] == 'TIK')
    assert tik['units'] == 0 and not tik.get('buying') and 'wantUnits' not in tik and tik['placeholder']
    o = fw.orders('degen', c, book, prices, 150.0, {'minOrderUsd': 0.1, 'maxSwapUsd': 50, 'armed': True}, 0)
    assert not [x for x in o if x['side'] == 'buy' and x['mint'] == 'TIK']             # the stopped coin is NOT bought back
    # … and if the wallet still holds some of it (its sell has not landed), that is sold, not kept
    book2 = {**book, 'legs': {**book['legs'], 'TIK': {'atoms': 164, 'decimals': 2, 'costUsd': 1.64, 'entryPx': 1.0}}}
    c2 = fw.sync_card(card, book2, prices, 150.0)
    assert next(l for l in c2['legs'] if l['mint'] == 'TIK')['units'] == 0
    o2 = fw.orders('degen', c2, book2, prices, 150.0, {'minOrderUsd': 0.1, 'maxSwapUsd': 50, 'armed': True}, 0)
    assert [x for x in o2 if x['side'] == 'sell' and x['mint'] == 'TIK'] and not [x for x in o2 if x['side'] == 'buy' and x['mint'] == 'TIK']

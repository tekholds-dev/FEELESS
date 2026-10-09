def test_card_totals_read_every_ledger_row_not_the_trimmed_copy():
    # 2026-10-09: the KV doc keeps the newest 2,000 rows → the real card showed fees $1.33 of $2.18 and top-ups $15.50 of $22.50
    import reputation_service as rs
    import store
    import fuse_wallet as fw
    lg = store.Ledger(rs.FUSE_WALLET_PATH)
    lg.append({'at': 1, 'card': 'degen', 'side': 'topup', 'usd': 5.0, 'status': 'done', 'id': 't0'})
    for i in range(2100):
        lg.append({'at': 10 + i, 'card': 'degen', 'side': 'buy' if i % 2 else 'sell', 'status': 'filled', 'sig': f's{i}', 'usd': 1.0, 'feeUsd': 0.001})
    rs._fw_full_cache.update(n=-1, rows=[])
    rows = rs._fw_full_ledger()
    assert len(rows) == 2101 and rows[0]['id'] == 't0'                 # every row, oldest first
    t = fw.totals(rows, 'degen')
    assert t['topups'] == 5.0 and t['swaps'] == 2100 and abs(t['feesUsd'] - 2.1) < 1e-6
    trimmed = fw.totals(rows[-2000:], 'degen')
    assert trimmed['topups'] == 0 and trimmed['feesUsd'] < t['feesUsd']   # what the card used to read
    lg.append({'at': 9999, 'card': 'degen', 'side': 'buy', 'status': 'filled', 'sig': 'new', 'usd': 1.0, 'feeUsd': 0.001})
    assert len(rs._fw_full_ledger()) == 2102                           # the cache re-reads when the table grows
    rs._fw_full_cache.update(n=-1, rows=[])


def test_card_fees_are_valued_at_each_fills_sol_price_not_todays():
    import fuse_wallet as fw
    book = {'feesSol': 0.0186, 'feesUsd': 2.18, 'cardFeesSol': 0.0183}
    assert abs(fw.card_fees_usd(book, 110.0) - 0.0183 * 2.18 / 0.0186) < 1e-3   # ≈ $2.14, not 0.0183 × $110 = $2.01
    assert fw.card_fees_usd({'cardFeesSol': 0.01}, 120.0) == 1.2                  # no history yet: today's price
    assert fw.card_fees_usd({}, 120.0) == 0.0

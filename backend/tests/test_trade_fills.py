"""On-chain fills → exact position (fake transactions; nothing leaves the process)."""
import trade_fills as tf

W = 'Wa11et1111111111111111111111111111111111111'
MINT = 'Paid111111111111111111111111111111111111111'
SOL = tf.SOL_MINT


def tb(idx, mint, amount, dec=6, owner=W):
    return {'accountIndex': idx, 'mint': mint, 'owner': owner, 'uiTokenAmount': {'amount': str(amount), 'decimals': dec}}


def tx(sig, pre_lamports, post_lamports, pre_t, post_t, t=1_700_000_000, fee=5000, err=None):
    return {'blockTime': t, 'transaction': {'signatures': [sig], 'message': {'accountKeys': [{'pubkey': W}, {'pubkey': 'Other'}]}},
            'meta': {'err': err, 'fee': fee, 'preBalances': [pre_lamports, 0], 'postBalances': [post_lamports, 0], 'preTokenBalances': pre_t, 'postTokenBalances': post_t}}


def test_first_buy_counts_sol_spent_without_the_refundable_account_rent():
    # 0.1 SOL swap + 0.00203928 rent for the new token account + 5000 lamports network fee
    spent = int((0.1 + tf.ATA_RENT_SOL) * 1e9) + 5000
    f = tf.fill_from_tx(tx('b1', 1_000_000_000, 1_000_000_000 - spent, [], [tb(2, MINT, 5_000_000_000)]), W, MINT, 150)
    assert f['side'] == 'buy' and f['tokens'] == 5000 and f['tx'] == 'b1'
    assert abs(f['usd'] - (0.1 + 5000 / 1e9) * 150) < 1e-3          # real cost incl. network fee, rent excluded
    assert abs(f['price'] - f['usd'] / 5000) < 1e-7 and f['balanceAfter'] == 5000


def test_sell_through_wsol_and_transfers_are_not_trades():
    sell = tx('s1', 500_000_000, 500_000_000 - 5000, [tb(2, MINT, 5_000_000_000), tb(3, SOL, 0, 9)], [tb(2, MINT, 2_500_000_000), tb(3, SOL, 60_000_000, 9)])
    f = tf.fill_from_tx(sell, W, MINT, 150)
    assert f['side'] == 'sell' and f['tokens'] == 2500 and abs(f['usd'] - (0.06 - 5000 / 1e9) * 150) < 1e-3
    gift = tx('g1', 10**9, 10**9 - 5000, [], [tb(2, MINT, 10**6)])   # tokens arrived, only the network fee left: not a buy
    assert tf.fill_from_tx(gift, W, MINT, 150) is None
    assert tf.fill_from_tx(tx('x', 10**9, 9 * 10**8, [], [tb(2, MINT, 10**6)], err={'x': 1}), W, MINT, 150) is None


def test_position_uses_real_balance_fees_and_per_sell_pnl():
    rows = tf.merge(
        [{'ts': 2, 'side': 'buy', 'usd': 15.0, 'price': 0.003, 'tokens': 5000, 'tx': 'b1', 'via': 'chain'},
         {'ts': 3, 'side': 'sell', 'usd': 9.0, 'price': 0.0036, 'tokens': 2500, 'tx': 's1', 'via': 'chain'}],
        [{'ts': 2, 'side': 'buy', 'usd': 14.0, 'price': 0.0028, 'tx': 'b1', 'via': 'feeless'}],   # same tx: chain wins
    )
    p = tf.position(rows, held_chain=2400.0, fees_by_sig={'b1': 0.15})
    assert p['avgEntry'] == 0.003 and p['tokensHeld'] == 2400.0 and p['exact'] is True
    assert p['realizedUsd'] == 1.5 and p['feesUsd'] == 0.15 and p['buys'] == 1 and p['sells'] == 1
    assert p['trades'][1]['pnlUsd'] == 1.5 and p['trades'][0]['feeUsd'] == 0.15
    assert tf.position([r for r in rows if r['side'] == 'sell']) is None


def test_trade_cards_endpoint_prices_each_sell_against_average_entry(tmp_path, monkeypatch):
    import asyncio
    import reputation_service as rs
    monkeypatch.setattr(rs, 'FEELESS_TRADES_PATH', tmp_path / 'ft.json'); monkeypatch.setattr(rs, 'FEE_LEDGER_PATH', tmp_path / 'fl.json')
    rs._json_save(rs.FEELESS_TRADES_PATH, {W: [{'ts': 1, 'side': 'buy', 'usd': 10.0, 'price': 0.002, 'token': MINT, 'tx': 'b'},
                                              {'ts': 2, 'side': 'sell', 'usd': 6.0, 'price': 0.003, 'token': MINT, 'tx': 's'}]})

    async def no_fills(_):
        return []
    monkeypatch.setattr(rs, '_feeless_fills', no_fills)
    out = asyncio.run(rs.trade_cards(W))
    sell = out['cards'][0]
    assert sell['tx'] == 's' and sell['pnlUsd'] == 2.0 and sell['pnlPct'] == 50.0 and sell['token'] == MINT

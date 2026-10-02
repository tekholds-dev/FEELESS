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
    # entry = break-even: all $15 that left the wallet over 5000 coins; fill price = $14.85 (fee out) over 5000
    assert p['avgEntry'] == 0.003 and abs(p['fillPrice'] - 14.85 / 5000) < 1e-12 and p['tokensHeld'] == 2400.0 and p['exact'] is True
    assert p['realizedUsd'] == 1.5 and p['feesUsd'] == 0.15 and p['buys'] == 1 and p['sells'] == 1
    assert p['trades'][1]['pnlUsd'] == 1.5 and p['trades'][0]['feeUsd'] == 0.15
    assert tf.position([r for r in rows if r['side'] == 'sell']) is None



def test_break_even_includes_fees_so_pnl_is_real_money():
    buy = {'ts': 1, 'side': 'buy', 'usd': 10.0, 'sol': 0.1, 'networkSol': 0.001, 'price': 0.01, 'tokens': 1000, 'tx': 'b', 'via': 'chain'}
    p = tf.position([buy], fees_by_sig={'b': 0.1})
    assert p['avgEntry'] == 0.01 and abs(p['fillPrice'] - (10 - 0.1 - 0.1) / 1000) < 1e-12 and abs(p['feesUsd'] - 0.2) < 1e-9   # $100/SOL network fee
    # price back exactly at the pool fill: you're down by the fees, never shown as up
    assert (p['fillPrice'] - p['avgEntry']) * p['tokensHeld'] < 0


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


def test_old_quote_estimates_self_heal_to_the_exact_fill(tmp_path, monkeypatch):
    import asyncio
    import reputation_service as rs
    monkeypatch.setattr(rs, 'FEELESS_TRADES_PATH', tmp_path / 'ft.json'); monkeypatch.setattr(rs, '_internal_key', lambda: 'k')
    rs._repair_tried.clear()
    rs._json_save(rs.FEELESS_TRADES_PATH, {W: [{'ts': 1, 'side': 'buy', 'usd': 1.0, 'price': 0.0096, 'token': MINT, 'tx': 'paid', 'via': 'feeless'}]})

    class Http:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None):
            assert url.endswith('/internal/exact-fill/paid')
            return type('R', (), {'status_code': 200, 'json': lambda self: {'fill': {'side': 'buy', 'tokens': 103.9455, 'sol': 0.0077, 'usd': 1.15, 'networkSol': 0.00001}}})()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', lambda **k: Http())
    asyncio.run(rs._repair_estimates(W, MINT))
    row = rs._json_load(rs.FEELESS_TRADES_PATH, {})[W][0]
    assert row['via'] == 'chain' and row['usd'] == 1.15 and abs(row['price'] - 1.15 / 103.9455) < 1e-12
    asyncio.run(rs._repair_estimates(W, MINT))   # exact now: nothing left to repair, no second read


def test_owner_paid_trade_reads_down_not_up():
    """Regression (owner's real trade): $1.15 left the wallet for 103.9455 PAID, $0.135 of it FEELESS fee; worth $1.13 now.
    Exact fill and quote-only estimate must both say DOWN — the old code showed +14.8% (entry built from the quote)."""
    held, now_value = 103.9455, 1.13
    live = now_value / held
    exact = tf.position([{'ts': 1, 'side': 'buy', 'usd': 1.15, 'sol': 0.00766, 'networkSol': 0.00002, 'price': 1.15 / held, 'tokens': held, 'tx': 'paid', 'via': 'chain'}],
                        held_chain=held, fees_by_sig={'paid': 0.135})
    assert (live - exact['avgEntry']) * exact['tokensHeld'] < 0 and exact['exact'] is True
    assert abs((live / exact['avgEntry'] - 1) * 100 - (-1.74)) < 0.05       # −1.7%, matching the wallet


def test_quote_only_estimate_uses_the_fee_actually_charged(tmp_path, monkeypatch):
    import reputation_service as rs
    p = rs.TradeLanded(wallet=W, signature='paid', inUsd=1.0, feeBps=50, inputMint=rs.WSOL, outputMint=MINT, inAmount=0.0067, outAmount=103.9455)
    rec = rs._trade_record(p, MINT, 103.9455, 'buy', 150.0, fee_usd=0.135)   # flat fee from the ledger, not 0.5% of $1
    assert rec['via'] == 'estimate' and rec['usd'] == 1.135
    live = 1.13 / 103.9455
    assert live < rec['price']   # still reads down



def test_each_trade_carries_its_own_fill_and_break_even():
    rows = [{'ts': 1, 'side': 'buy', 'usd': 1.15, 'sol': 0.00766, 'networkSol': 0.0, 'price': 1.15 / 100, 'tokens': 100.0, 'tx': 'b1', 'via': 'chain'},
            {'ts': 2, 'side': 'buy', 'usd': 2.0, 'price': 0.02 / 1, 'tokens': 100.0, 'tx': 'b2', 'via': 'chain', 'sol': 0.013}]
    p = tf.position(rows, fees_by_sig={'b1': 0.15})
    b1, b2 = p['trades']
    assert abs(b1['fillPrice'] - 0.01) < 1e-12 and abs(b1['breakEven'] - 0.0115) < 1e-12    # $1.00 at the pool, $1.15 all-in
    assert abs(b2['fillPrice'] - 0.02) < 1e-12 and abs(p['avgEntry'] - 3.15 / 200) < 1e-12  # blended break-even across both buys


def test_fill_is_what_went_into_the_pool_read_from_the_tx():
    """Real buy shape: wallet pays 0.0070 SOL into the pool, 0.00007 SOL FEELESS fee into FEELESS's wSOL account,
    0.00060 SOL network (priority) fee, and opens a Token-2022 account (0.00207408 SOL refundable rent)."""
    FEEACC, POOL, ATA = 'FeeWso1Acc111111111111111111111111111111111', 'Poo1Vau1t11111111111111111111111111111111111', 'Ata11111111111111111111111111111111111111111'
    lam = lambda sol: int(round(sol * 1e9))
    pool, fee, net, rent = 0.0070, 0.00007, 0.0006, 0.00207408
    tx = {'blockTime': 9, 'transaction': {'signatures': ['real'], 'message': {
        'accountKeys': [{'pubkey': W}, {'pubkey': FEEACC}, {'pubkey': ATA}, {'pubkey': POOL}],
        'instructions': [{'program': 'system', 'parsed': {'type': 'transfer', 'info': {'source': W, 'destination': FEEACC, 'lamports': lam(fee)}}}]}},
        'meta': {'err': None, 'fee': lam(net), 'innerInstructions': [],
                 'preBalances': [lam(1.0), lam(5), 0, lam(100)], 'postBalances': [lam(1.0 - pool - fee - net - rent), lam(5 + fee), lam(rent), lam(100 + pool)],
                 'preTokenBalances': [{'accountIndex': 1, 'mint': tf.SOL_MINT, 'owner': 'FeelessTreasury', 'uiTokenAmount': {'amount': '5000000000', 'decimals': 9}}],
                 'postTokenBalances': [{'accountIndex': 1, 'mint': tf.SOL_MINT, 'owner': 'FeelessTreasury', 'uiTokenAmount': {'amount': str(lam(5 + fee)), 'decimals': 9}},
                                       {'accountIndex': 2, 'mint': MINT, 'owner': W, 'uiTokenAmount': {'amount': '103945500', 'decimals': 6}}]}}
    f = tf.fill_from_tx(tx, W, MINT, 150.0)
    assert f['side'] == 'buy' and f['tokens'] == 103.9455
    assert abs(f['usd'] - (pool + fee + net) * 150) < 1e-3               # all-in: what left the wallet, rent excluded
    assert abs(f['poolUsd'] - pool * 150) < 1e-6                           # exactly what the pool got
    assert abs(f['feelessFeeUsd'] - fee * 150) < 1e-6 and abs(f['networkUsd'] - net * 150) < 1e-6
    p = tf.position([f], held_chain=103.9455)
    t = p['trades'][0]
    assert abs(t['fillPrice'] - pool * 150 / 103.9455) < 1e-12 and abs(t['breakEven'] - f['usd'] / 103.9455) < 1e-12
    assert abs(p['feesUsd'] - (fee + net) * 150) < 1e-3


def test_pnl_never_includes_fees_pool_side_money():
    """Owner rule: P&L = the coin's performance. A $5.00 buy where $0.25 was fees: invested at the pool = $4.75."""
    import trade_fills as tf
    rows = [{'tx': 'b', 'side': 'buy', 'usd': 5.0, 'poolUsd': 4.75, 'tokens': 1000, 'price': 0.005, 'via': 'chain', 'ts': 1},
            {'tx': 's', 'side': 'sell', 'usd': 2.9, 'poolUsd': 3.0, 'tokens': 500, 'price': 0.0058, 'via': 'chain', 'ts': 2}]
    p = tf.position(rows)
    assert p['fillPrice'] == 0.00475 and p['investedPoolUsd'] == 4.75
    assert abs(p['realizedPoolUsd'] - (3.0 - 500 * 0.00475)) < 1e-9                       # sold at the pool vs the pool entry
    assert p['investedUsd'] == 5.0 and p['feesUsd'] > 0                                     # fees still reported — apart

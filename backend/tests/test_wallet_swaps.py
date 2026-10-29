"""🔁 N07: a wallet's swaps read from plain Solana RPC when Helius is out of quota — from the wallet's OWN balance changes."""
import wallet_swaps as ws

W, M, USDC = 'WALLET1111111111111111111111111111111111111', 'COINmint11111111111111111111111111111111111', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


def tx(pre_sol, post_sol, pre_tok, post_tok, fee=5000, err=None, payer=True, sig='SIG'):
    keys = [W, 'POOL'] if payer else ['OTHER', W]
    i = keys.index(W)
    pre, post = [0, 0], [0, 0]
    pre[i], post[i] = pre_sol, post_sol
    tb = lambda d: [{'accountIndex': 2 + n, 'mint': m, 'owner': W, 'uiTokenAmount': {'uiAmount': a}} for n, (m, a) in enumerate(d.items())]
    return {'blockTime': 1700, 'transaction': {'signatures': [sig], 'message': {'accountKeys': [{'pubkey': k} for k in keys]}},
            'meta': {'err': err, 'fee': fee, 'preBalances': pre, 'postBalances': post, 'preTokenBalances': tb(pre_tok), 'postTokenBalances': tb(post_tok)}}


def test_a_sol_buy_and_sell_are_read_from_the_wallets_own_balances_fee_added_back():
    b = ws.parse(tx(2_000_000_000, 1_499_995_000, {}, {M: 1000.0}), W, 200)          # paid 0.5 SOL + a 5000-lamport fee
    assert b['side'] == 'buy' and b['usd'] == 100.0 and b['token'] == M and b['price'] == 0.1 and b['tx'] == 'SIG' and b['source'] == 'rpc'
    s = ws.parse(tx(1_000_000_000, 1_249_995_000, {M: 1000.0}, {M: 0.0}), W, 200)
    assert s['side'] == 'sell' and s['usd'] == 50.0


def test_stable_and_wrapped_sol_legs_count_and_non_swaps_are_left_out():
    st = ws.parse(tx(1_000_000_000, 999_995_000, {USDC: 10.0}, {USDC: 0.0, M: 50.0}), W, 200)
    assert st['side'] == 'buy' and st['usd'] == 10.0
    wsol = ws.parse(tx(1_000_000_000, 999_995_000, {ws.WSOL: 0.25}, {ws.WSOL: 0.0, M: 7.0}), W, 200)
    assert wsol['usd'] == 50.0
    assert ws.parse(tx(1_000_000_000, 999_995_000, {}, {M: 5.0}), W, 200) is None                    # an airdrop: no money moved
    assert ws.parse(tx(1_000_000_000, 500_000_000, {}, {}), W, 200) is None                           # a plain SOL transfer
    assert ws.parse(tx(2_000_000_000, 1_500_000_000, {}, {M: 9.0}, err={'x': 1}), W, 200) is None    # failed on-chain
    assert ws.parse(tx(1_000_000_000, 999_995_000, {'A' * 43: 5.0}, {M: 3.0}), W, 200) is None        # token-for-token
    assert ws.parse(tx(2_000_000_000, 1_500_000_000, {}, {M: 9.0}, payer=False, fee=0), W, 200)['side'] == 'buy'   # someone else paid the fee

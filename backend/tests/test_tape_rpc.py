"""Trade tape fallback: a jsonParsed Solana swap becomes a tape row (buy/sell, $ from the SOL leg, payer wallet)."""
import pytest

cs = pytest.importorskip('candles_service')
COIN, W = 'Coin1111111111111111111111111111111111111111', 'Wa11et11111111111111111111111111111111111111'


def tx(pre_tok, post_tok, pre_sol, post_sol, err=None):
    tb = lambda amt: [{'mint': COIN, 'owner': W, 'uiTokenAmount': {'uiAmount': amt}}]
    return {'blockTime': 1_700_000_000, 'meta': {'err': err, 'fee': 5000, 'preTokenBalances': tb(pre_tok), 'postTokenBalances': tb(post_tok),
            'preBalances': [pre_sol], 'postBalances': [post_sol]},
            'transaction': {'signatures': ['sig1'], 'message': {'accountKeys': [{'pubkey': W}]}}}


def test_buy_and_sell_rows_priced_from_sol_leg():
    buy = cs.parse_rpc_swap(tx(0, 1000, 2_000_000_000, 1_000_005_000), COIN, 0.15, 150.0)  # paid 1 SOL (+fee) for 1000
    assert buy['kind'] == 'buy' and buy['wallet'] == W and buy['tx'] == 'sig1' and buy['usd'] == 150.0
    sell = cs.parse_rpc_swap(tx(1000, 0, 1_000_000_000, 1_999_995_000), COIN, 0.15, 150.0)
    assert sell['kind'] == 'sell' and sell['usd'] == 150.0


def test_failed_or_unrelated_tx_is_skipped():
    assert cs.parse_rpc_swap(tx(0, 1000, 1, 1, err={'x': 1}), COIN, 0.15, 150.0) is None
    assert cs.parse_rpc_swap(tx(5, 5, 1, 1), COIN, 0.15, 150.0) is None


def test_dust_spam_without_a_sol_leg_is_not_a_trade():
    assert cs.parse_rpc_swap(tx(1.0374, 1.03805, 1_000_000_000, 999_994_816), COIN, 0.00036, 150.0) is None

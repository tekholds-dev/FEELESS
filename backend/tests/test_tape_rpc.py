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


def test_the_tape_walks_every_rpc_lane_and_keeps_the_keepers_first_lane_for_last():
    """One fixed key used to feed the tape; when its plan ran out every coin read 'waiting for trades…'."""
    import candles_service as cs
    assert cs.tape_lanes(['k1', 'k2', 'k3', 'pub1', 'pub2'], ['k1', 'k2', 'k3']) == ['k2', 'k3', 'pub1', 'pub2', 'k1']
    assert cs.tape_lanes(['pub1'], []) == ['pub1']


def test_per_trade_ticks_use_only_the_swaps_own_fill_price_in_time_order():
    """🕯 the chart moves on every swap — priced by the swap's own SOL leg; a fallback valuation or a 20× jump is never a tick."""
    import candles_service as cs
    buy = cs.parse_rpc_swap(tx(0, 1000, 2_000_000_000, 1_000_005_000), COIN, 0.15, 150.0)
    assert buy['priced'] is True and abs(buy['price'] - 0.15) < 1e-4 and buy['at'] == 1_700_000_000
    odd = cs.parse_rpc_swap(tx(0, 1000, 2_000_000_000, 1_000_005_000), COIN, 0.5, 150.0)   # its SOL leg disagrees 3× with the live price
    assert odd['priced'] is False                                                          # valued at the live price — never a chart tick
    rows = [{'priced': True, 'price': 0.15, 'at': 1, 'kind': 'buy', 'usd': 150}, odd, None, {'priced': True, 'price': 9.0, 'at': 2},
            {'priced': True, 'price': 0.16, 'at': 3, 'kind': 'sell', 'usd': 20}]
    assert cs.swap_ticks(rows, 0.14) == [{'p': 0.15, 't': 1, 'k': 'buy', 'u': 150}, {'p': 0.16, 't': 3, 'k': 'sell', 'u': 20}]
    assert cs.swap_ticks([], 1.0) == []


def test_a_log_notification_gives_its_signature_failed_swaps_and_the_ack_give_none():
    import candles_service as cs
    note = {'jsonrpc': '2.0', 'method': 'logsNotification', 'params': {'result': {'context': {'slot': 1}, 'value': {'signature': 'S1', 'err': None, 'logs': []}}}}
    assert cs.swap_sig(note) == 'S1'
    assert cs.swap_sig({'params': {'result': {'value': {'signature': 'S2', 'err': {'x': 1}}}}}) is None
    assert cs.swap_sig({'jsonrpc': '2.0', 'result': 7, 'id': 1}) is None and cs.swap_sig(None) is None
    assert cs._rpc_http('wss://mainnet.helius-rpc.com/?api-key=k') == 'https://mainnet.helius-rpc.com/?api-key=k'


def test_while_swap_fills_flow_the_aggregate_price_stays_quiet(monkeypatch):
    """ONE feed per forming candle: a Jupiter read must not land between swap fills (the candle jumped between two sources)."""
    import asyncio, time as _t
    import candles_service as cs
    sent = []
    async def fake_bcast(key, msg): sent.append(msg)
    async def fake_px(mint, age=5.0): return 0.2
    monkeypatch.setattr(cs, '_broadcast', fake_bcast); monkeypatch.setattr(cs, '_stream_price', fake_px)
    cs._streams['solana:P'] = {'clients': set(), 'task': None, 'last': 0.0, 'price': 0.15, 'sigs': [], 'retry': set(), 'swapAt': _t.time(), 'jup': None, 'saved': _t.time()}
    try:
        asyncio.run(cs._push_price('solana:P', 'solana', 'P', 'M'))
        assert sent == []                                            # a swap fill 0s ago: quiet
        cs._streams['solana:P'].update(swapAt=_t.time() - cs.SWAP_QUIET - 1, last=0.0)
        asyncio.run(cs._push_price('solana:P', 'solana', 'P', 'M'))
        assert len(sent) == 1 and cs._streams['solana:P']['jup'] == 0.2   # quiet coin: the aggregate keeps it live
    finally:
        cs._streams.pop('solana:P', None)

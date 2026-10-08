import time
import feecat_service as fs


def _pair(age_h, now):
    return {'quoteToken': {'symbol': 'SOL'}, 'liquidity': {'usd': 90_000}, 'volume': {'h24': 400_000},
            'marketCap': 2_000_000, 'priceChange': {'m5': 1, 'h1': 10, 'h6': 30, 'h24': 40},
            'txns': {'h1': {'buys': 300, 'sells': 150}}, 'pairCreatedAt': (now - age_h * 3600) * 1000}


def test_core_lane_skips_coins_younger_than_three_days():
    now = time.time()
    # her record: under 6h avg -36%, 1-3d avg -60%, 3d+ +16% — pulled pools were all young
    assert fs._qualifies(_pair(30, now), now)[0] is None
    assert fs._qualifies(_pair(30, now), now)[1] == 'too new'
    assert fs._qualifies(_pair(80, now), now)[0] is not None


def test_proof_gate_sits_out_only_when_both_windows_are_red():
    import feecat_brain as b
    now = time.time()
    red = [{'pnlSol': -0.1, 'changeAtExit': -5, 'exitAt': now - 3600 * i} for i in range(1, 12)]
    assert b.proof_gate(red, now)['sit_out'] is True
    mixed = red + [{'pnlSol': 5.0, 'changeAtExit': 50, 'exitAt': now - 3600 * 30}]
    assert b.proof_gate(mixed, now)['sit_out'] is False   # 72h net positive
    assert b.proof_gate([], now)['sit_out'] is False      # no record = not gated

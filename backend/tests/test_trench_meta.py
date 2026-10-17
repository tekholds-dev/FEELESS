"""🧬 TRENCH META: a launch too young for a chart is judged on its tape — a real crowd vs a bot loop / one-wallet pump / dump."""
import flow

NOW = 10_000.0


def tr(i, kind='buy', usd=10.0, wallet=None, px=1.0):
    return {'ts': NOW - 200 + i * 10, 'kind': kind, 'usd': usd, 'wallet': wallet or f'W{i}', 'price': px}


def test_a_real_crowd_reads_organic():
    t = [tr(i, usd=5 + i * 1.3, px=1 + i * 0.01) for i in range(12)] + [tr(20, 'sell', 8.0, 'S1')]
    m = flow.trench_meta(t, NOW)
    assert m['verdict'] == 'ORGANIC' and m['wallets'] == 13 and m['buyers'] == 12 and m['topBuyerPct'] < 45


def test_bot_loop_one_wallet_dump_and_thin_are_caught():
    assert flow.trench_meta([tr(i, usd=3.33) for i in range(12)], NOW)['verdict'] == 'BOT'
    assert flow.trench_meta([tr(0, usd=500, wallet='WHALE')] + [tr(i, usd=5 + i) for i in range(1, 10)], NOW)['verdict'] == 'ONE WALLET'
    assert flow.trench_meta([tr(i, usd=4 + i) for i in range(6)] + [tr(10 + i, 'sell', 30 + i, f'S{i}') for i in range(5)], NOW)['verdict'] == 'DUMPING'
    assert flow.trench_meta([tr(i) for i in range(4)], NOW)['verdict'] == 'THIN'
    assert flow.trench_meta([{**tr(i, usd=5 + i), 'ts': NOW - 900} for i in range(20)], NOW)['verdict'] == 'THIN'   # older than 5 min = not counted



"""Fee's setup memory: learns which setups win, sizes up/down, vetoes proven losers, never overreacts to luck."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feecat_brain as fb  # noqa: E402

NOW = time.time()
PAIR = {'priceChange': {'h1': 22, 'm5': 2}, 'txns': {'h1': {'buys': 300, 'sells': 100}}, 'liquidity': {'usd': 60_000}, 'marketCap': 600_000, 'pairCreatedAt': (NOW - 10 * 3600) * 1000}


def test_features_bucket_the_setup():
    f = fb.setup_features(PAIR, NOW, gap=True)
    assert f == {'h1': '15-30%', 'flow': '2x+', 'depth': '10%+', 'age': '6-24h', 'm5': '1-3%', 'mc': '250K-1M', 'lane': 'core', 'gap': 'fvg'}


def test_new_setups_trade_at_default_size_and_luck_does_not_rewrite_the_playbook():
    setup = fb.setup_features(PAIR, NOW)
    assert fb.setup_edge(setup, {})['mult'] == 1.0
    lucky = fb.edge_table([{'setup': setup, 'ret': 80, 'win': True, 'at': NOW}] * 3)   # 3 trades < MIN_N
    assert fb.setup_edge(setup, lucky)['mult'] == 1.0


def test_proven_winner_sizes_up_proven_loser_is_vetoed():
    win = fb.setup_features(PAIR, NOW)
    lose = fb.setup_features({**PAIR, 'priceChange': {'h1': 45, 'm5': 6}}, NOW)
    mem = []
    for i in range(8):
        mem = fb.remember(mem, win, 35 if i % 4 else -10, 0.1 if i % 4 else -0.02, NOW)
        mem = fb.remember(mem, lose, -18, -0.05, NOW)
    table = fb.edge_table(mem)
    up = fb.setup_edge(win, table)
    assert up['mult'] > 1.0 and not up['veto']
    down = fb.setup_edge(lose, table)
    assert down['veto'] and 'lost 8/8' in down['why']
    book = fb.playbook(table)
    assert book['best'][0]['edge'] > 0 and book['worst'][0]['setup'] in ('h1=30%+', 'm5=3%+')


def test_memory_is_bounded():
    mem = []
    for _ in range(fb.MEMORY + 50):
        mem = fb.remember(mem, {'h1': '<5%'}, 1, 0.01, NOW)
    assert len(mem) == fb.MEMORY

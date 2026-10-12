"""🧠 Real-money memory: learns from every confirmed real exit, vetoes entries that lost, only while it beats its own skips walk-forward."""
import real_memory as rm
import fuse_wallet as fw


def pos(i, res, struct='UPTREND', rule='E12 trend in hand', tag='🤖 agents · A-tier', age=3.0):
    return {'confirmed': True, 'realPct': res, 'closedAt': i, 'thesis': {'structure': struct, 'triggerRule': rule}, 'tag': tag, 'launch': {'ageH': age}}


def book():
    out = []
    for i in range(80):   # parabolic E2 chases lose; uptrend E12 entries win a little — the same in old and new trades
        out.append(pos(i, -15.0 - i % 5, 'PARABOLIC', 'E2 no chasing', '🤖 agents · C-tier') if i % 2 else pos(i, 2.0 + i % 3))
    return out


def test_it_learns_the_losing_entries_and_proves_itself_on_unseen_trades():
    m = rm.build(book())
    assert m['proof']['ok'] and m['proof']['take']['avg'] > m['proof']['skip']['avg']
    bad = rm.feats('PARABOLIC', 'E2 no chasing', '🤖 agents · C-tier', None, None, 2.0)
    good = rm.feats('UPTREND', 'E12 trend in hand', '🤖 agents · A-tier', None, None, 2.0)
    assert 'not bought' in rm.judge(m, bad) and rm.judge(m, good) is None


def test_unproven_memory_never_blocks_and_a_drained_pool_outlier_is_capped():
    m = rm.build(book()[:20])
    assert not m['proof']['ok'] and rm.judge(m, rm.feats('PARABOLIC', 'E2', 'C-tier')) is None
    t = rm.learn([pos(0, 68_986_873.0)] + [pos(i, -2.0) for i in range(1, 6)])
    assert t['cells']['struct:UPTREND']['med'] <= rm.CAP


def test_an_agent_buy_must_cost_less_than_a_normal_one():
    o = {'usd': 1.0, 'midPx': 1.0, 'lamports': 1_000_000}
    assert fw.buy_safety(o, 0.97 * 1e6, 6, 980_000)[0]                                   # 3% over mid, 2% round trip: fine for the engine
    ok, why = fw.buy_safety({**o, 'agent': True}, 0.97 * 1e6, 6, 980_000)
    assert not ok and 'above market' in why                                                 # an agent scalp: max 2.5% over mid
    ok, why = fw.buy_safety({**o, 'agent': True}, 0.99 * 1e6, 6, 950_000)
    assert not ok and 'sells back' in why                                                   # … and ≤ 3.5% round trip
    assert fw.target({'legs': [{'mint': 'M', 'pairAddress': 'P', 'units': 1, 'bought': {'tag': '🤖 agents'}}]}, {})['M']['agent']

"""FeeCat learns from users: only verified buys ≥ 24h old score a trader; elites need a real record; flow = recent elite buys."""
import crowd

NOW = 10_000_000


def buy(tok, price, age_h, usd=10, side='buy'):
    return {'side': side, 'token': tok, 'fillPrice': price, 'usd': usd, 'tokens': usd / price, 'ts': NOW - age_h * 3600}


def test_skill_scores_only_old_enough_real_buys():
    trades = [buy('A', 1, 30), buy('B', 1, 30), buy('C', 1, 30), buy('D', 1, 2), buy('E', 1, 30, usd=0.5), buy('A', 1, 30, side='sell')]
    s = crowd.trader_skill(trades, {'A': 1.5, 'B': 1.05, 'C': 0.5, 'D': 9}, NOW)
    assert s == {'n': 3, 'winRate': 33.3, 'avgPct': round((50 + 5 - 50) / 3, 2)}


def test_elites_need_a_record_and_flow_counts_distinct_recent_elite_buys():
    skills = {'pro': {'n': 8, 'winRate': 62, 'avgPct': 25}, 'lucky': {'n': 3, 'winRate': 100, 'avgPct': 300}, 'meh': {'n': 20, 'winRate': 40, 'avgPct': 5}, 'staff': {'n': 9, 'winRate': 70, 'avgPct': 30}}
    el = crowd.elites(skills, exclude={'staff'})
    assert el == {'pro'}
    flow = crowd.elite_flow({'pro': [buy('X', 1, 1, usd=50), buy('X', 1, 2, usd=20), buy('Y', 1, 9)], 'meh': [buy('X', 1, 1)]}, el, NOW)
    assert flow == {'X': {'n': 1, 'usd': 70.0}}

"""Lag catcher aggregation names slow routes and janky pages with a fix."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import perf  # noqa: E402


def test_route_key_groups_ids():
    assert perf.route_key('/api/market/pair/solana/So11111111111111111111111111111111111111112?x=1') == '/api/market/pair/solana/:id'
    assert perf.route_key('/api/reputation/case/0x' + 'a' * 40) == '/api/reputation/case/:id'


def test_summary_flags_slow_routes_and_low_fps():
    samples = [{'page': '/terminal/profile', 'api': {'/api/reputation/case/' + 'A' * 40: [3000, 3200, 2900]}, 'longTasks': 9, 'longMs': 900, 'fps': 31, 'lite': True},
               {'page': '/terminal/chat', 'api': {'/api/market/feed?kind=new': [200, 250]}, 'longTasks': 0, 'longMs': 0, 'fps': 60}]
    out = perf.summarize(samples)
    assert out['routes'][0]['route'] == '/api/reputation/case/:id' and out['routes'][0]['p95'] >= 2900
    whats = ' '.join(f['what'] for f in out['fixes'])
    assert 'case/:id' in whats and '31 fps' in whats and 'feed' not in whats
    assert out['pages'][0]['page'] == '/terminal/profile' and out['pages'][0]['autoLite'] == 1 and out['score'] < 100

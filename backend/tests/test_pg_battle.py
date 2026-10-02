import pg_battle as pb

SC = {'id': 'tp200_sl40', 'vName': '🚀 Moon Mission v.03', 'dial': 'degen', 'tp': 200, 'sl': 40,
      'legs': [{'pairAddress': 'SOLP', 'symbol': 'SOL', 'role': 'anchor', 'weight': 35}, {'pairAddress': 'R1', 'symbol': 'A', 'role': 'runner', 'weight': 65}]}
LIQ = {'SOLP': 1e8, 'R1': 2e5, 'N1': 3e5}


def test_deal_fills_like_a_wallet_and_values_back():
    c = pb.deal(SC, {'SOLP': 150, 'R1': 0.01}, LIQ, 0, 100)
    assert [l['symbol'] for l in c['legs']] == ['SOL', 'A'] and c['name'] == '🚀 Moon Mission v.03'
    assert 99 < sum(l['units'] * l['entry'] for l in c['legs']) < 100        # price impact: a bit under $100 of tokens
    assert -1.5 < pb.round_pct(c, {'SOLP': 150, 'R1': 0.01}, LIQ) < 0         # round-trip costs impact, never a free gain


def test_tick_swaps_on_tp_stop_and_dead_coins():
    cfg = pb.clean_cfg({})
    c = pb.deal(SC, {'SOLP': 150, 'R1': 0.01}, LIQ, 0, 100)
    cand = [{'pairAddress': 'N1', 'symbol': 'NEW', 'price': 1.0}]
    up = pb.tick(c, {'SOLP': 150, 'R1': 0.031, 'N1': 1.0}, LIQ, {}, cand, cfg, 60)              # +210% ≥ TP 200
    assert up['legs'][1]['symbol'] == 'NEW' and up['swaps'][-1]['why'] == 'tp' and up['legs'][0]['symbol'] == 'SOL'   # anchor never swapped
    q = pb.tick(c, {'SOLP': 150, 'R1': 0.01, 'N1': 1.0}, LIQ, {'R1': True}, cand, cfg, 60)     # quiet starts the dead clock
    assert q['legs'][1]['symbol'] == 'A' and q['legs'][1]['quietSince'] == 60
    dead = pb.tick(q, {'SOLP': 150, 'R1': 0.01, 'N1': 1.0}, LIQ, {'R1': True}, cand, cfg, 60 + 10 * 60)
    assert dead['swaps'][-1]['why'] == 'dead'


def test_bell_pairs_and_records():
    assert pb.pair_up(['a', 'b', 'c']) == [{'a': 'a', 'b': 'b'}]
    res, rec, losers = pb.settle([{'a': 'a', 'b': 'b'}], {'a': 3.0, 'b': -1.0}, {}, 9)
    assert res[0]['winner'] == 'a' and rec == {'a': {'w': 1, 'l': 0, 'd': 0}, 'b': {'w': 0, 'l': 1, 'd': 0}} and losers == {'b'}
    assert pb.clean_cfg({'roundMins': 7, 'cards': 6})['roundMins'] == 5 and pb.clean_cfg({'cards': 6})['cards'] == 6


def test_service_round_deals_settles_and_rebreeds(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    sc = lambda i, sym: {'id': f's{i}', 'vName': f'Card {i}', 'tp': 200, 'sl': 40, 'legs': [{'pairAddress': f'P{i}', 'symbol': sym, 'role': 'runner', 'weight': 100}]}
    async def cards(rd, scen=None, now=None, losers_ok=False): return [sc(1, 'A'), sc(2, 'B')]
    async def live(): return {'passing': [], 'dropped': []}
    px = {'P1': 1.0, 'P2': 1.0}
    async def pairs(legs): return {k: {'priceUsd': v, 'liquidity': {'usd': 1e6}, 'txns': {'m5': {'buys': 5, 'sells': 3}}, 'volume': {'m5': 100}} for k, v in px.items()}
    monkeypatch.setattr(rs, '_pg_scenario_cards', cards); monkeypatch.setattr(rs, '_runner_live', live); monkeypatch.setattr(rs, '_fuse_pairs', pairs)
    asyncio.run(rs._pg_battle_tick(1000))                              # first call: deal + pair (bell at 0 → settles nothing)
    v = rs._pg_battle_view(rs._json_load(rs.RUNNERS_PATH, {}))
    assert len(v['pairs']) == 1 and v['pairs'][0]['a']['name'] == 'Card 1' and v['endsAt'] == 1000 + 300
    px['P1'] = 1.2; px['P2'] = 0.9
    asyncio.run(rs._pg_battle_tick(1400))                              # bell → s1 wins, s2 re-bred
    v = rs._pg_battle_view(rs._json_load(rs.RUNNERS_PATH, {}))
    assert v['record']['s1']['w'] == 1 and v['record']['s2']['l'] == 1 and v['log'][0]['winner'] == 's1'

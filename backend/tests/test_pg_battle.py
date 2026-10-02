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


def test_creator_pick_puts_only_picked_runner_ups_on_the_arena(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'admin')
    async def majors(): return [{'symbol': 'SOL', 'pairAddress': 'SOLP', 'baseAddress': 'So1'}]
    async def px(legs): return {l['pairAddress']: 1.0 for l in legs}
    monkeypatch.setattr(rs, '_majors_rows', majors); monkeypatch.setattr(rs, '_hq_prices', px)
    scen = [{'id': 'tp200_sl40', 'kind': 'exits', 'label': 'TP +200%', 'window': '24h', 'tp': 200, 'sl': 40, 'rounds': 9, 'avgPct': -2},
            {'id': 'safe_6h', 'kind': 'dial', 'label': 'safe dial', 'window': '6h', 'tp': 30, 'sl': 15, 'rounds': 9, 'avgPct': 3}]
    monkeypatch.setattr(rs._rn, 'scenarios', lambda *a, **k: scen)
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [{'id': 'r1', 'at': 1, 'picks': [{'pairAddress': 'P1', 'mint': 'M1', 'symbol': 'A'}]}], 'paths': {}})
    class Req: pass
    out = asyncio.run(rs.scenario_pick(Req(), {'id': 'tp200_sl40', 'on': True}))
    st = rs._json_load(rs.RUNNERS_PATH, {})['scenarioStage']
    assert out['creatorPicks'] == ['tp200_sl40'] and [x['src'] for x in st] == ['tp200_sl40']      # picked (even a loser) — never the auto top-N
    asyncio.run(rs.scenario_pick(Req(), {'id': 'tp200_sl40', 'on': False}))
    assert rs._json_load(rs.RUNNERS_PATH, {})['scenarioStage'] == []


def test_engine_champion_and_ready_rows():
    rec = {'a': {'w': 3, 'l': 1}, 'b': {'w': 4, 'l': 3}, 'c': {'w': 1, 'l': 0}, 'gone': {'w': 9, 'l': 0}}
    assert pb.champion(rec, {'a': {}, 'b': {}, 'c': {}}) == 'a'            # best W−L among cards still fighting, ≥2 wins
    assert pb.champion({'c': {'w': 1, 'l': 0}}, {'c': {}}) is None
    rows = dict((r['id'], ok) for ok, r in pb.ready_rows(rec, {'a': 'Moon'}))
    assert rows['a'] is True and rows['gone'] is True and rows['b'] is False and rows['c'] is False


def test_dna_plays_out_in_battle_ticks():
    cfg = pb.clean_cfg({})
    c = pb.deal(SC, {'SOLP': 150, 'R1': 0.01}, LIQ, 0, 100)
    cand = [{'pairAddress': 'N1', 'symbol': 'NEW', 'price': 1.0}]
    up = pb.tick(c, {'SOLP': 150, 'R1': 0.031, 'N1': 1.0}, LIQ, {}, cand, cfg, 60, {'payoutPct': 50, 'compound': 'smart'})
    assert up['cash'] > 0                                                                  # half the gain banked on the take
    keep_all = pb.tick(c, {'SOLP': 150, 'R1': 0.031, 'N1': 1.0}, LIQ, {}, cand, cfg, 60, {'payoutPct': 0, 'compound': 'off'})
    assert keep_all['cash'] > up['cash']                                                   # compound off = the whole gain stays as cash
    held = pb.tick(c, {'SOLP': 150, 'R1': 0.004, 'N1': 1.0}, LIQ, {}, cand, cfg, 60, {'stop': 'hold'})   # −60% but DNA says hold
    assert held['legs'][1]['symbol'] == 'A'


def test_service_battles_learn_dna(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    sc = lambda i, sym: {'id': f's{i}', 'vName': f'Card {i}', 'tp': 200, 'sl': 40, 'dial': 'degen', 'legs': [{'pairAddress': f'P{i}', 'symbol': sym, 'role': 'runner', 'weight': 100}]}
    async def cards(rd, scen=None, now=None, losers_ok=False): return [sc(1, 'A'), sc(2, 'B')]
    async def live(): return {'passing': [], 'dropped': []}
    px = {'P1': 1.0, 'P2': 1.0}
    async def pairs(legs): return {k: {'priceUsd': v, 'liquidity': {'usd': 1e6}, 'txns': {'m5': {'buys': 5}}, 'volume': {'m5': 9}} for k, v in px.items()}
    monkeypatch.setattr(rs, '_pg_scenario_cards', cards); monkeypatch.setattr(rs, '_runner_live', live); monkeypatch.setattr(rs, '_fuse_pairs', pairs)
    asyncio.run(rs._pg_battle_tick(1000))
    v = rs._pg_battle_view(rs._json_load(rs.RUNNERS_PATH, {}))
    a, b = v['pairs'][0]['a'], v['pairs'][0]['b']
    assert a['dna'] and b['dna'] and dn_sig(a['dna']) != dn_sig(b['dna'])                    # two cards, two DNAs
    px['P1'] = 1.3
    asyncio.run(rs._pg_battle_tick(1400))
    v = rs._pg_battle_view(rs._json_load(rs.RUNNERS_PATH, {}))
    assert v['brain']['scores'] and v['brain']['label']                                      # the engine learned from the bell


def dn_sig(d):
    import card_dna
    return card_dna.sig(d)


def test_engine_doctor_applies_the_winning_pick_filter(monkeypatch):
    import asyncio
    import time as _t
    import pytest
    rs = pytest.importorskip('reputation_service')
    async def nothing(*a, **k): return None
    monkeypatch.setattr(rs, '_scenario_stage', nothing); monkeypatch.setattr(rs, 'notify', lambda *a, **k: None)
    now = _t.time()
    rounds = [{'id': f'r{i}', 'at': now - 3600 + i, 'picks': [{'mint': f'w{i}', 'entry': 1.0, 'lane': 'runner', 'score': 80, 'chg5m': 3},
                                                              {'mint': f'l{i}', 'entry': 1.0, 'lane': 'runner', 'score': 40, 'chg5m': -2}]} for i in range(8)]
    paths = {**{f'w{i}': [(now - 1000, 1.6), (now - 900, 2.1)] for i in range(8)}, **{f'l{i}': [(now - 1000, 0.6)] for i in range(8)}}
    rs._json_save(rs.RUNNERS_PATH, {'rounds': rounds, 'paths': paths})
    asyncio.run(rs._engine_auto(now))
    d = rs._json_load(rs.RUNNERS_PATH, {})
    assert d['pickFilter'] in ('score70', 'green5m') and d['sitOut'] is False and 'every pick' in d['doctorWhy']


def test_battle_rug_shield_swaps_a_drained_coin():
    c = pb.deal(SC, {'SOLP': 150, 'R1': 0.01}, LIQ, 0, 100)
    out = pb.tick(c, {'SOLP': 150, 'R1': 0.01, 'N1': 1.0}, {**LIQ, 'R1': 50_000}, {}, [{'pairAddress': 'N1', 'symbol': 'NEW', 'price': 1.0}], pb.clean_cfg({}), 60)
    assert out['swaps'][-1]['why'] == 'rug' and out['legs'][1]['symbol'] == 'NEW'


def test_dna_cycle_reshapes_a_winning_card_each_bell():
    c = pb.deal(SC, {'SOLP': 150, 'R1': 0.01}, LIQ, 0, 100)
    px = {'SOLP': 150, 'R1': 0.01}
    anchor_share = lambda card: sum(l['units'] * px[l['pairAddress']] for l in card['legs'] if l['role'] == 'anchor') / pb.value(card, px, LIQ)
    a = pb.cycle_rebalance(c, {'cycle': 'adaptive'}, -3.0, px, LIQ)                           # lost → rest in majors
    assert a['phase'] == 'anchor' and 0.65 < anchor_share(a) < 0.75
    d = pb.cycle_rebalance(c, {'cycle': 'adaptive'}, 9.0, px, LIQ)                            # won big → press with runners
    assert d['phase'] == 'degen' and anchor_share(d) < 0.2
    assert pb.value(a, px, LIQ) < pb.value(c, px, LIQ)                                        # re-entry pays real impact
    off = pb.cycle_rebalance(c, {'cycle': 'off'}, 9.0, px, LIQ)
    assert off['legs'] == c['legs'] and off['rounds'] == 1


def test_arena_paper_book_deals_true_fills_marks_and_audits():
    card = {'name': 'Ape', 'legs': [{'pairAddress': 'A', 'symbol': 'A', 'baseAddress': 'mA', 'weight': 50, 'runner': True}, {'pairAddress': 'B', 'symbol': 'B', 'weight': 50}]}
    px, lq = {'A': 1.0, 'B': 2.0}, {'A': 10000, 'B': 1e9}
    b = pb.paper_book('user:1', card, px, lq, 100, size=100, fee_per_coin=0.1)
    assert b['feesUsd'] == 0.2 and len(b['legs']) == 2 and b['events'][0]['kind'] == 'deal'
    a = next(l for l in b['legs'] if l['pairAddress'] == 'A')
    assert a['entry'] > a['mid'] == 1.0                        # thin pool → paid above mid (true fill)
    assert b['valueUsd'] < 100                                 # selling right away costs the impact both ways
    m = pb.paper_mark(b, {'A': 1.5, 'B': 2.0}, lq, 200)
    assert m['pct'] > 0 and m['hiPct'] == m['pct'] and m['loPct'] <= 0
    v = pb.paper_view(m, {'A': 1.5, 'B': 2.0}, lq)
    assert v['legs'][0]['entry'] == a['entry'] and v['pnlUsd'] == round(v['valueUsd'] - 100, 4) and v['feesUsd'] == 0.2
    assert pb.paper_book('k', {'legs': []}, px, lq, 1) is None

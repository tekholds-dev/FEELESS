"""⚡ Copy cards (the original owner earns copyPct of the copier's FEELESS fee; never a self-copy) and swap streaks
(Survivor / Phoenix / Immortal while the card still wins; activity bonus on the Arena)."""
import asyncio
import time

import pytest

import fuse_hq as hq

A, B = 'Aaaa1111111111111111111111111111111111111111', 'Bbbb2222222222222222222222222222222222222222'


def test_swap_streak_tiers_only_while_winning():
    ev = lambda n: [{'kind': 'buy'}] * n + [{'kind': 'sell'}, {'kind': 'topup'}]
    assert hq.swap_streak({'events': ev(0), 'pnlPct': 10})['tier'] is None
    assert hq.swap_streak({'events': ev(1), 'pnlPct': 10})['label'] == '🛡 Survivor'
    assert hq.swap_streak({'events': ev(3), 'pnlPct': 1})['tier'] == 'phoenix'
    s = hq.swap_streak({'events': ev(6), 'pnlPct': 2})
    assert s['tier'] == 'immortal' and s['bonus'] == 15
    assert hq.swap_streak({'events': ev(6), 'pnlPct': -2}) == {'swaps': 6, 'won': False, 'tier': None, 'label': None, 'bonus': 0}


def test_copy_cut_is_a_share_of_the_copiers_fee():
    assert hq.copy_cut(2.0, {'copyPct': 10}) == 0.2 and hq.copy_cut(2.0, {'copyPct': 99}) == 1.0   # capped at 50%


@pytest.fixture
def rs(monkeypatch, request):
    rs = pytest.importorskip('reputation_service')
    if 'feecat_card' not in request.node.name:   # never reach the live FeeCat service from a test
        async def no_cat(): return None
        monkeypatch.setattr(rs, '_feecat_card', no_cat); monkeypatch.setattr(rs, '_feecat_raw', no_cat)
    async def sol(): return 150.0
    monkeypatch.setattr(rs, '_sol_usd_live', sol)
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    async def px(legs): return {'P1': 3.0}
    monkeypatch.setattr(rs, '_hq_prices', px)
    return rs


def test_copy_records_the_owner_pays_them_from_the_fee_book_and_refuses_self_copies(rs):
    now = time.time()
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'orig', 'wallet': A, 'at': now - 100, 'legs': [{'pairAddress': 'P1', 'mint': 'M1', 'usd': 100, 'tokens': 50, 'sig': 'SA'}],
                                                   'events': [{'kind': 'buy'}]}]})
    rs._json_save(rs.FEELESS_TRADES_PATH, {B: [{'tx': 'SB', 'side': 'buy', 'usd': 20.0, 'tokens': 10.0, 'token': 'M1'}],
                                           A: [{'tx': 'SA2', 'side': 'buy', 'usd': 5.0, 'tokens': 2.0, 'token': 'M1'}]})
    rs._json_save(rs.FEE_LEDGER_PATH, {B: [{'sig': 'SB', 'feeUsd': 2.0, 't': now}]})
    asyncio.run(rs.fuse_position(rs.FusePositionIn(address=B, session='s', copyOf='orig', legs=[{'pairAddress': 'P1', 'symbol': 'X', 'signature': 'SB'}])))
    asyncio.run(rs.fuse_position(rs.FusePositionIn(address=A, session='s', copyOf='orig', legs=[{'pairAddress': 'P1', 'symbol': 'X', 'signature': 'SA2'}])))
    pos = {p['wallet']: p for p in rs._json_load(rs.FUSE_HQ_PATH, {})['positions'] if p['id'] != 'orig'}
    assert pos[B]['copyOwner'] == A and 'copyOf' not in pos[A]                                     # self-copy earns nothing
    book = {w['wallet']: w for w in asyncio.run(rs._feeback_book())['rows']}
    assert book[A]['copyUsd'] == 0.2                                                               # 10% of B's $2 fee
    row = next(r for r in asyncio.run(rs.fuse_pnl(A))['rows'] if r['id'] == 'orig')
    assert row['copies'] == 1 and row['copyEarnedUsd'] == 0.2 and row['streak']['tier'] == 'survivor'


def test_arena_user_card_shows_copies_and_streak(rs, monkeypatch):
    now = time.time()
    async def lv(): return {'passing': [], 'dropped': [], 'seen': 0}
    monkeypatch.setattr(rs, '_runner_live', lv)
    rs._arena_mega_cache.update(at=0, data=None)
    rs._json_save(rs.FUSES_PATH, {'fuses': {}}); rs._json_save(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    leg = [{'pairAddress': 'P1', 'usd': 100, 'tokens': 40}]                                       # $120 now = +20%
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'o', 'wallet': A, 'at': now, 'legs': leg, 'events': [{'kind': 'buy'}] * 3},
                                                  {'id': 'c', 'wallet': B, 'at': now, 'legs': leg, 'copyOf': 'o', 'copyOwner': A}]})
    o = next(c for c in asyncio.run(rs.fuse_arena_public())['mega'] if c['id'] == 'o')
    assert o['copies'] == 1 and o['streak']['tier'] == 'phoenix' and o['copyPct'] == 10


def test_season_week_starts_monday_utc_and_ranks_by_real_pnl():
    mon = 1_790_553_600            # Monday 2026-09-28 00:00 UTC
    assert hq.season_start(mon + 3 * 86400 + 5) == mon and hq.season_start(mon - 1) == mon - hq.WEEK
    rows = [{'id': 'a', 'wallet': A, 'at': mon + 10, 'costUsd': 5, 'pnlPct': 12, 'pnlUsd': 0.6},
            {'id': 'b', 'wallet': B, 'at': mon + 20, 'costUsd': 5, 'pnlPct': 40, 'pnlUsd': 2},
            {'id': 'old', 'wallet': B, 'at': mon - 10, 'costUsd': 5, 'pnlPct': 99, 'pnlUsd': 5},            # last week
            {'id': 'dust', 'wallet': B, 'at': mon + 30, 'costUsd': 0.5, 'pnlPct': 500, 'pnlUsd': 2},        # under $1
            {'id': 'bot', 'wallet': 'BOT', 'at': mon + 40, 'costUsd': 5, 'pnlPct': 300, 'pnlUsd': 15}]
    assert [r['id'] for r in hq.season_board(rows, mon, mon + hq.WEEK, bots={'BOT'})] == ['b', 'a']


def test_season_crowns_last_weeks_top3_once_and_boosts_their_feeback(rs, monkeypatch):
    now = time.time(); start = hq.season_start(now); prev = start - hq.WEEK
    async def shield(a): return {'verdict': 'clean'}
    sent = []
    monkeypatch.setattr(rs, '_shield_of', shield); monkeypatch.setattr(rs, 'notify', lambda *a, **k: sent.append((a, k)))
    leg = lambda tok: [{'pairAddress': 'P1', 'usd': 100, 'tokens': tok, 'sig': f'S{tok}'}]
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'w1', 'wallet': A, 'at': prev + 60, 'legs': leg(50)},       # $150 = +50%
                                                  {'id': 'w2', 'wallet': B, 'at': prev + 90, 'legs': leg(40)}]})      # $120 = +20%
    top = asyncio.run(rs._fuse_season_tick(now))
    crowns = [x for x in sent if x[0][1] == 'fuse-guard']
    weekly = [x for x in sent if 'FeeCat' in x[0][2]]
    assert [t['id'] for t in top] == ['w1', 'w2'] and len(crowns) == 2 and '#1' in crowns[0][0][2]
    assert len(weekly) == 2 and all(x[1]['once'].startswith('feecat-week-') for x in weekly)   # 🐱 one weekly note per holder
    assert asyncio.run(rs._fuse_season_tick(now)) is None                                         # once per week
    assert rs._season_wins()['w1']['rank'] == 1
    rs._json_save(rs.FEE_LEDGER_PATH, {A: [{'sig': 'S50', 'feeUsd': 1.0, 't': now}]})
    row = next(r for r in asyncio.run(rs.fuse_pnl(A))['rows'] if r['id'] == 'w1')
    assert row['seasonWin']['rank'] == 1 and row['feeback']['season'] and row['feeback']['pct'] == 40   # 20 + loyalty 10 (7d+) + season 10


def test_live_season_board_endpoint(rs, monkeypatch):
    async def shield(a): return {'verdict': 'clean'}
    monkeypatch.setattr(rs, '_shield_of', shield)
    rs._fuse_season_cache.update(at=0, data=None)
    now = time.time()
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'c1', 'wallet': A, 'at': now - 5, 'legs': [{'pairAddress': 'P1', 'usd': 10, 'tokens': 5}]}]})
    out = asyncio.run(rs.fuse_season())
    assert out['board'][0]['id'] == 'c1' and out['board'][0]['pnlPct'] == 50 and out['endsAt'] - out['week'] == hq.WEEK


def test_background_warm_rebuilds_while_viewers_read_the_last_copy(rs, monkeypatch):
    calls = []
    async def board(days=30): return {'rows': []}
    async def lv():
        calls.append(1); return {'passing': [], 'dropped': [], 'seen': len(calls)}
    monkeypatch.setattr(rs, 'caller_board', board)
    rs._runner_disc_cache.update(at=time.time(), data={'cached': True})
    assert asyncio.run(rs.runners_discover()) == {'cached': True}                                # viewer: fresh cache, no work
    monkeypatch.setattr(rs, '_runner_live', lv)
    async def warm():
        rs._FUSE_FORCE.set(True)
        return await rs.runners_discover()
    out = asyncio.run(warm())                                                                      # warmer task: forced rebuild
    assert 'runners' in out and calls == [1] and rs._FUSE_FORCE.get() is False                    # the flag never leaks


def test_compound_streak_counts_topup_bursts_only_while_winning():
    ev = [{'kind': 'topup', 'at': 0}, {'kind': 'topup', 'at': 60}, {'kind': 'topup', 'at': 4000}, {'kind': 'topup', 'at': 9000}, {'kind': 'buy', 'at': 1}]
    s = hq.compound_streak({'events': ev, 'pnlPct': 4})
    assert s['compounds'] == 3 and s['tier'] == 'snowball' and s['bonus'] == 15
    assert hq.compound_streak({'events': ev, 'pnlPct': -1})['tier'] is None


def test_fuse_score_cites_every_point_and_ties_to_rep_without_a_loop():
    rows = [{'costUsd': 10, 'valueUsd': 14, 'heldS': 90000, 'streak': {'tier': 'phoenix'}, 'compound': {'tier': 'compounder'}}]
    s = hq.fuse_score(rows, [{'rank': 1}], copies=2, trust=80)
    assert s['perf'] == 24 + 15 + 6 + 12 + 2 and s['rep'] == 20 and s['score'] == 79 and len(s['parts']) == 6
    assert hq.fuse_score(rows, [], 0, 80, bot=True)['score'] == 0
    assert hq.trust_from_fuse(59, 3) == 4 and hq.trust_from_fuse(59, 1) == 0 and hq.trust_from_fuse(0, 5) == -3


def test_season_race_moves():
    prev = {'a': 1, 'b': 2}
    board = [{'id': 'b', 'rank': 1}, {'id': 'a', 'rank': 2}, {'id': 'c', 'rank': 3}]
    assert [(m['id'], m['kind']) for m in hq.rank_moves(prev, board)] == [('b', 'up'), ('a', 'down'), ('c', 'new')]


def test_fuse_score_feeds_trust_from_cache(rs, monkeypatch):
    async def shield(a): return {'verdict': 'clean'}
    monkeypatch.setattr(rs, '_shield_of', shield)
    now = time.time()
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': f'c{i}', 'wallet': A, 'at': now - 2 * 86400, 'legs': [{'pairAddress': 'P1', 'usd': 10, 'tokens': 5}]} for i in range(2)]})
    s = asyncio.run(rs._fuse_score(A, fresh=True))                                                 # $30 vs $20 = +50%
    assert s['cards'] == 2 and s['perf'] >= 30
    parts = asyncio.run(rs.trust_score(A))['parts']
    assert any(p['label'].startswith('Fuse score') and p['points'] > 0 for p in parts)


def test_feecat_card_on_the_arena_is_her_sim_book(rs, monkeypatch):
    class R:
        def json(self): return {'name': 'Fee', 'winRate': 61, 'wins': 11, 'losses': 7, 'realizedPnlSol': 0.31, 'discipline': {'lives': 8},
                                'positions': [{'pairAddress': 'P1', 'symbol': 'UDR', 'mint': 'M', 'entryPriceUsd': '0.0074', 'costSol': 0.1, 'currentChange': -8, 'entryVolH1': 1000, 'openedAt': 5},
                                              {'pairAddress': 'P2', 'symbol': 'X', 'mint': 'N', 'entryPriceUsd': '1', 'costSol': 0.3, 'currentChange': 20, 'entryVolH1': 1000, 'openedAt': 6}]}
    class C:
        def __init__(self, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k): return R()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', C)
    c = asyncio.run(rs._feecat_card())
    assert c['kind'] == 'feecat' and c['index'] == 113.0 and c['record']['winRate'] == 61 and c['legs'][0]['entry'] == 0.0074
    assert c['legs'][1]['weight'] == 75.0 and c['grade'] == 'A'


def test_replay_returns_each_coins_24h_path_and_the_cards_moments(rs, monkeypatch):
    now = time.time()
    async def series(pair): return [[int(now - 3600), 1.0], [int(now - 60), 1.5]]
    monkeypatch.setattr(rs, '_series_24h', series)
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'c1', 'wallet': A, 'at': now - 7200, 'legs': [{'pairAddress': 'P1', 'symbol': 'X', 'usd': 10, 'tokens': 10, 'addedAt': now - 7200}],
                                                   'events': [{'kind': 'topup', 'symbol': 'X', 'at': now - 1800}, {'kind': 'sell', 'symbol': 'X', 'at': now - 90000}]}]})
    out = asyncio.run(rs.fuse_replay('user', 'c1'))
    assert out['legs'][0]['entry'] == 1.0 and len(out['legs'][0]['series']) == 2
    assert [m['kind'] for m in out['markers']] == ['open', 'topup']                                 # older than 24h dropped
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_replay('nope', 'x'))


def test_payout_plan_skips_dust_and_excluded_and_credits_only_what_moved():
    plan = hq.payout_plan([{'wallet': 'A', 'owedUsd': 3.0}, {'wallet': 'B', 'owedUsd': 0.01}, {'wallet': 'FEELESS', 'owedUsd': 9}], 150, exclude={'FEELESS'})
    assert [r['wallet'] for r in plan['rows']] == ['A'] and plan['rows'][0]['sol'] == 0.02 and plan['totalUsd'] == 3.0
    assert hq.credit_paid({'A': 0.03, 'X': 1}, plan) == {'A': 3.0}                                 # never above owed; unknown ignored
    assert hq.credit_paid({'A': 0.01}, plan) == {'A': 1.5}
    assert hq.payout_plan([{'wallet': 'A', 'owedUsd': 3}], 0)['rows'] == []


def test_feecat_week_and_who_beat_her():
    ex = [{'exitAt': 10, 'changeAtExit': 20}, {'exitAt': 11, 'changeAtExit': -10}, {'exitAt': 1, 'changeAtExit': 99}]
    assert hq.feecat_week_pct(ex, [{'openedAt': 12, 'currentChange': 5}], 5, 100) == 5.0
    assert hq.feecat_week_pct([], [], 5, 100) is None
    assert hq.beats_cat([{'id': 'a', 'pnlPct': 6}, {'id': 'b', 'pnlPct': 4}], 5.0) == ['a'] and hq.beats_cat([{'id': 'a', 'pnlPct': 6}], None) == []
    s = hq.fuse_score([], [], 0, None, cat_wins=3)
    assert any('Beat FeeCat 3×' in p['label'] and p['points'] == 16 for p in s['parts'])


def test_battle_tick_settles_records_and_repairs(rs, monkeypatch):
    now = time.time()
    rs._arena_mega_cache.update(at=now, data=[{'kind': 'user', 'id': 'x', 'name': 'X', 'index': 110, 'activity': {'score': 80}},
                                              {'kind': 'lit', 'id': 'y', 'name': 'Y', 'index': 104, 'activity': {'score': 60}}])
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'x', 'wallet': A, 'legs': []}],
                                    'battles': {'endsAt': now - 1, 'pairs': [{'a': {'key': 'user:x', 'name': 'X', 'start': 2.0}, 'b': {'key': 'lit:y', 'name': 'Y', 'start': 1.0}}]}})
    res = asyncio.run(rs._battle_tick(now))
    assert res[0]['winner'] == 'X' and res[0]['aMove'] == 8.0
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    assert d['battleRecord'] == {'user:x': {'w': 1, 'l': 0, 'd': 0}, 'lit:y': {'w': 0, 'l': 1, 'd': 0}}
    assert d['battles']['pairs'][0]['a']['key'] == 'user:x' and d['battles']['endsAt'] > now
    assert asyncio.run(rs._battle_tick(now + 5)) is None                                          # bell hasn't rung
    view = rs._battle_view(rs._arena_mega_cache['data'], now)
    assert view['pairs'][0]['a']['now'] == 0.0 and view['log'][0]['winner'] == 'X'



def test_an_empty_battlefield_pairs_as_soon_as_two_cards_arrive(rs):
    now = time.time()
    rs._json_save(rs.FUSE_HQ_PATH, {'battles': {'endsAt': now + 3000, 'pairs': []}})
    rs._arena_mega_cache.update(at=now, data=[{'kind': 'auto', 'id': 'a', 'name': 'A', 'index': 100, 'activity': {'score': 5}}])
    assert asyncio.run(rs._battle_tick(now)) is None                                              # one card: nothing to fight
    rs._arena_mega_cache.update(at=now, data=[{'kind': 'auto', 'id': 'a', 'name': 'A', 'index': 100, 'activity': {'score': 5}},
                                              {'kind': 'lit', 'id': 'b', 'name': 'B', 'index': 101, 'activity': {'score': 9}}])
    asyncio.run(rs._battle_tick(now))
    assert len(rs._json_load(rs.FUSE_HQ_PATH, {})['battles']['pairs']) == 1


def test_trader_record_medals_battles_cat_wins(rs, monkeypatch):
    async def shield(a): return {'verdict': 'clean'}
    monkeypatch.setattr(rs, '_shield_of', shield)
    now = time.time()
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'k1', 'wallet': A, 'at': now - 86400, 'legs': [{'pairAddress': 'P1', 'usd': 10, 'tokens': 5}]},
                                                  {'id': 'k2', 'wallet': A, 'at': now - 86400, 'closedAt': now, 'legs': [{'pairAddress': 'P1', 'usd': 10, 'tokens': 5, 'soldUsd': 14}]}],
                                    'seasons': [{'week': 1, 'top': [{'id': 'k1', 'rank': 1, 'wallet': A}, {'id': 'zz', 'rank': 2, 'wallet': 'other'}]}],
                                    'battleRecord': {'user:k1': {'w': 3, 'l': 1, 'd': 0}, 'user:k2': {'w': 1, 'l': 0, 'd': 2}, 'user:other': {'w': 9}},
                                    'catChallenge': [{'week': 1, 'ids': ['k1']}]})
    t = asyncio.run(rs._fuse_score(A, fresh=True))['trader']
    assert t['medals'] == {'1': 1, '2': 0, '3': 0} and t['battles'] == {'w': 4, 'l': 1, 'd': 2} and t['catWins'] == 1
    assert t['held'] == 1 and t['closed'] == 1 and t['bestPct'] >= 40


def test_buying_a_card_to_back_counts_on_the_paid_bar_only(rs):
    rs._json_save(rs.FUSE_HQ_PATH, {'battles': {'endsAt': 9e12, 'pairs': [{'a': {'key': 'auto:1', 'name': 'A', 'start': 0}, 'b': {'key': 'mega:2', 'name': 'B', 'start': 0}}],
                                                'backs': {A: 'mega:2'}}})
    rs._json_save(rs.FEELESS_TRADES_PATH, {B: [{'tx': 'SB', 'side': 'buy', 'usd': 20.0, 'tokens': 10.0, 'token': 'M1'}]})
    asyncio.run(rs.fuse_position(rs.FusePositionIn(address=B, session='s', back='auto:1', legs=[{'pairAddress': 'P1', 'symbol': 'X', 'signature': 'SB'}])))
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    assert list(d['battles']['paid'].values())[0]['key'] == 'auto:1' and d['positions'][0]['backKey'] == 'auto:1'
    v = rs._battle_view([{'kind': 'auto', 'id': '1', 'index': 100}, {'kind': 'mega', 'id': '2', 'index': 100}], 0)['pairs'][0]
    assert v['a']['paidN'] == 1 and v['a']['paidUsd'] > 0 and v['a']['backers'] == 0     # paid never touches the free bar
    assert v['b']['backers'] == 1 and v['b']['paidN'] == 0


def test_rounds_compound_pays_then_paying_needs_a_signature(rs):
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'c1', 'wallet': A, 'at': 1, 'legs': [], 'roundsLeft': 0}]})
    r = asyncio.run(rs.fuse_rounds(rs.RoundsIn(address=A, session='s', id='c1', mode='compound')))
    assert r['roundsLeft'] == 5 and r['roundsOwedUsd'] == rs._rounds_cfg()['per5Usd']
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_rounds(rs.RoundsIn(address=A, session='s', id='c1', mode='pay')))          # no payment signature
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_rounds(rs.RoundsIn(address=B, session='s', id='c1', mode='compound')))     # not your card


def test_my_battles_lists_live_and_past_for_my_cards_only(rs):
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'c1', 'wallet': A, 'name': 'Mine', 'at': 1, 'legs': []}],
        'battles': {'endsAt': 9e12, 'pairs': [{'a': {'key': 'user:c1', 'name': 'Mine', 'start': 0}, 'b': {'key': 'auto:9', 'name': 'Arena Pick', 'start': 0}}]},
        'battleLog': [{'at': 1, 'a': 'Mine', 'b': 'X', 'aKey': 'user:c1', 'bKey': 'auto:1', 'winnerKey': 'user:c1', 'aMove': 2, 'bMove': 1},
                      {'at': 2, 'a': 'Z', 'b': 'Y', 'aKey': 'auto:2', 'bKey': 'auto:3', 'winnerKey': 'auto:2'}]})
    r = asyncio.run(rs.fuse_my_battles(A))
    assert len(r['live']) == 1 and r['live'][0]['mine'] == 'a' and len(r['past']) == 1 and r['record']['w'] == 1
    assert asyncio.run(rs.fuse_my_battles(B))['live'] == []


def test_bracket_crowns_the_last_card_standing_and_restarts(rs, monkeypatch):
    now = time.time()
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: None); monkeypatch.setattr(rs, '_fuse_chat', lambda *a, **k: None)
    rs._arena_mega_cache.update(at=now, data=[{'kind': 'user', 'id': 'x', 'name': 'X', 'index': 110, 'activity': {'score': 80}},
                                              {'kind': 'lit', 'id': 'y', 'name': 'Y', 'index': 104, 'activity': {'score': 60}}])
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'x', 'wallet': A, 'legs': []}], 'bracket': {'cards': {'lit:y': {'w': 1, 'l': 1}}, 'season': 3},
                                    'battles': {'endsAt': now - 1, 'pairs': [{'a': {'key': 'user:x', 'name': 'X', 'start': 2.0}, 'b': {'key': 'lit:y', 'name': 'Y', 'start': 1.0}}]}})
    asyncio.run(rs._battle_tick(now))                                    # Y's 2nd loss → out → X crowned, bracket #4 starts fresh
    br = rs._json_load(rs.FUSE_HQ_PATH, {})['bracket']
    assert br['champions'][-1]['key'] == 'user:x' and br['season'] == 4 and br['cards'] == {}
    v = rs._battle_view(rs._arena_mega_cache['data'], now)
    assert v['bracket']['champions'][0]['name'] == 'X' and {b['status'] for b in v['bracket']['board']} == {'winners'}


def test_bracket_call_once_and_the_right_call_earns_xp(rs, monkeypatch):
    now = time.time()
    sent = []; monkeypatch.setattr(rs, 'notify', lambda *a, **k: sent.append(a)); monkeypatch.setattr(rs, '_fuse_chat', lambda *a, **k: None)
    rs._arena_mega_cache.update(at=now, data=[{'kind': 'user', 'id': 'x', 'name': 'X', 'index': 110, 'activity': {'score': 80}, 'legs': [{'pairAddress': 'PX'}]},
                                              {'kind': 'lit', 'id': 'y', 'name': 'Y', 'index': 104, 'activity': {'score': 60}, 'legs': [{'pairAddress': 'PY'}]}])
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [], 'bracket': {'cards': {'lit:y': {'w': 1, 'l': 1}}, 'season': 2},
                                    'battles': {'endsAt': now - 1, 'pairs': [{'a': {'key': 'user:x', 'name': 'X', 'start': 2.0}, 'b': {'key': 'lit:y', 'name': 'Y', 'start': 1.0}}]}})
    assert asyncio.run(rs.bracket_pick(rs.BracketPick(address=A, session='s', key='user:x')))['ok']
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.bracket_pick(rs.BracketPick(address=A, session='s', key='lit:y')))          # one call per bracket
    asyncio.run(rs._battle_tick(now))                                                             # X crowned
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    assert len(d['bracketWins'][A]) == 1 and d['bracket']['picks'] == {} and d['bracket']['champions'][-1]['legs'][0]['pairAddress'] == 'PX'
    assert any('You called it' in a[2] for a in sent)
    assert len(rs._fuse_quest_stats({A})['events']['bracket_win']) == 1


def test_comeback_is_tracked_and_crowned(rs, monkeypatch):
    now = time.time()
    chat = []; monkeypatch.setattr(rs, 'notify', lambda *a, **k: None); monkeypatch.setattr(rs, '_fuse_chat', lambda room, txt, *a, **k: chat.append(txt))
    mega = [{'kind': 'user', 'id': 'x', 'name': 'X', 'index': 100, 'activity': {'score': 80}, 'legs': [{'pairAddress': 'PX'}]},
            {'kind': 'lit', 'id': 'y', 'name': 'Y', 'index': 115, 'activity': {'score': 60}, 'legs': [{'pairAddress': 'PY'}]}]
    rs._arena_mega_cache.update(at=now, data=mega)
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [], 'battles': {'at': 1, 'endsAt': now + 60, 'pairs': [{'a': {'key': 'user:x', 'name': 'X', 'start': 0.0}, 'b': {'key': 'lit:y', 'name': 'Y', 'start': 0.0}}]}})
    asyncio.run(rs._battle_tick(now))                                                 # X trails by 15 → low tracked
    assert rs._json_load(rs.FUSE_HQ_PATH, {})['battles']['low']['user:x'] == 15.0
    mega[0]['index'] = 130; rs._json_save(rs.FUSE_HQ_PATH, {**rs._json_load(rs.FUSE_HQ_PATH, {}), 'battles': {**rs._json_load(rs.FUSE_HQ_PATH, {})['battles'], 'endsAt': now - 1}})
    res = asyncio.run(rs._battle_tick(now + 1))                                         # X wins from −15
    assert res[0]['comeback'] and rs._json_load(rs.FUSE_HQ_PATH, {})['comebacks']['user:x'] == 1 and any('COMEBACK' in t for t in chat)


def test_champions_share_doubles_the_copy_cut():
    assert hq.copy_cut(2.0, {'copyPct': 10}, champ=True) == 0.4 and hq.copy_cut(2.0, {'copyPct': 40}, champ=True) == 1.0   # capped at 50%

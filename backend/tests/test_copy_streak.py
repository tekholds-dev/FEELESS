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
def rs(monkeypatch):
    rs = pytest.importorskip('reputation_service')
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
    assert [t['id'] for t in top] == ['w1', 'w2'] and len(sent) == 2 and '#1' in sent[0][0][2]
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

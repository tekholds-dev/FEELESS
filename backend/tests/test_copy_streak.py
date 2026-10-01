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

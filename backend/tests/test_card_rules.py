"""Card rules: auto-profit levels set by Cmd Ctr (net of fees, entry = confirmed buy + its fee), hold/swap mode per card,
Fuse Fee-Back (unlock, loyalty, Arena bonus, cap), held-cards P&L and traders' cards on the Arena until withdrawn."""
import asyncio
import time

import pytest

import fuse_hq as hq


def test_rules_are_clamped_and_levels_validated():
    r = hq.clean_rules({'yieldLevels': [5, 30, 30, 2000, 'x', 100], 'yieldDefault': 90, 'fbCapPct': 500})
    assert r['yieldLevels'] == [30.0, 100.0] and r['yieldDefault'] == 100.0 and r['fbCapPct'] == 100


def test_exit_fee_uses_bundle_price_for_2_plus_legs_and_percent_for_one():
    b = {'on': True, 'perLegUsd': 0.1, 'maxPct': 5, 'maxLegUsd': 50}
    two = {'legs': [{'heldUsd': 20}, {'heldUsd': 20}]}
    assert hq.exit_fee_usd(two, b, 100, 0.01) == pytest.approx(0.22)
    assert hq.exit_fee_usd({'legs': [{'heldUsd': 20}]}, b, 100, 0.01) == pytest.approx(0.21)


def test_swap_mode_picks_the_weakest_leg_and_a_new_gated_runner():
    r = {'legs': [{'pairAddress': 'pA', 'mint': 'A', 'symbol': 'A', 'pnlPct': -30}, {'pairAddress': 'pB', 'mint': 'B', 'symbol': 'B', 'pnlPct': 5},
                  {'pairAddress': 'pC', 'mint': 'C', 'symbol': 'C', 'pnlPct': 2}]}
    passing = [{'mint': 'B', 'score': 99, 'pairAddress': 'pB'}, {'mint': 'N', 'symbol': 'N', 'score': 80, 'pairAddress': 'pN'}]
    s = hq.swap_suggest(r, {'C': ['dev now holds 18%']}, passing, 25)
    assert s['out']['mint'] == 'C' and 'fails a gate' in s['why'] and s['in']['mint'] == 'N'     # a failing gate beats a drop
    assert hq.swap_suggest(r, {}, passing, 25)['out']['mint'] == 'A'
    assert hq.swap_suggest(r, {}, passing, 40) is None                                             # nothing weak enough


def test_feeback_unlocks_then_grows_with_loyalty_and_arena_capped():
    rl = {'fbHolderPct': 20, 'fbHoldHours': 24, 'fbLoyaltyPct': 10, 'fbLoyaltyDays': 7, 'fbArenaPct': 10, 'fbCapPct': 35}
    assert hq.card_feeback(1, 3600, False, rl)['usd'] == 0 and 'unlocks in 23h' in hq.card_feeback(1, 3600, False, rl)['next']
    assert hq.card_feeback(1, 30 * 3600, False, rl)['pct'] == 20
    assert hq.card_feeback(1, 8 * 86400, True, rl)['pct'] == 35                                   # 20+10+10 capped at 35


@pytest.fixture
def rs(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    async def px(legs): return {'P1': 3.0, 'P2': 1.0}
    monkeypatch.setattr(rs, '_hq_prices', px)
    return rs


def test_auto_profit_only_at_cmd_ctr_levels_and_base_includes_the_buy_fee(rs, monkeypatch):
    me = 'Aaaa1111111111111111111111111111111111111111'
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: me)
    rs._json_save(rs.FUSE_HQ_PATH, {'cardRules': {'yieldLevels': [50, 100]}, 'positions': [{'id': 'y1', 'wallet': me, 'at': 1, 'legs': [{'pairAddress': 'P1', 'mint': 'M', 'usd': 100, 'tokens': 50, 'sig': 'S1'}]}]})
    rs._json_save(rs.FEE_LEDGER_PATH, {me: [{'sig': 'S1', 'feeUsd': 0.5, 't': 1}]})
    with pytest.raises(rs.HTTPException, match='levels'):
        asyncio.run(rs.fuse_auto_yield(rs.FuseYieldIn(address=me, session='s', id='y1', at=75)))
    y = asyncio.run(rs.fuse_auto_yield(rs.FuseYieldIn(address=me, session='s', id='y1', at=100)))['autoYield']
    assert y['base'] == 100.5                                                                      # confirmed buy + its fee


def test_mode_feeback_and_held_pnl_in_card_rows(rs, monkeypatch):
    me = 'Aaaa1111111111111111111111111111111111111111'
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: me)
    now = time.time()
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'c1', 'wallet': me, 'at': now - 30 * 3600, 'legs': [{'pairAddress': 'P1', 'mint': 'M', 'usd': 100, 'tokens': 50, 'sig': 'S1'}]}]})
    rs._json_save(rs.FEE_LEDGER_PATH, {me: [{'sig': 'S1', 'feeUsd': 1.0, 't': now}]})
    assert asyncio.run(rs.fuse_mode(rs.FuseModeIn(address=me, session='s', id='c1', mode='swap')))['mode'] == 'swap'
    out = asyncio.run(rs.fuse_pnl(me))
    row = out['rows'][0]
    assert row['mode'] == 'swap' and row['feeback']['pct'] == 20 and row['feeback']['usd'] == 0.2
    assert out['held'] == {'cards': 1, 'costUsd': 100, 'valueUsd': 150, 'pnlUsd': 50, 'pnlPct': 50.0} and row['exitFeeUsd'] > 0


def test_traders_cards_show_on_the_arena_and_winners_take_the_top_tier(rs, monkeypatch):
    now = time.time()
    async def lv(): return {'passing': [], 'dropped': [], 'seen': 0}
    monkeypatch.setattr(rs, '_runner_live', lv)
    rs._arena_mega_cache.update(at=0, data=None)
    rs._json_save(rs.FUSES_PATH, {'fuses': {}})
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [
        {'id': 'win', 'wallet': 'W1', 'at': now, 'legs': [{'pairAddress': 'P1', 'usd': 100, 'tokens': 50}]},                 # +50%
        {'id': 'meh', 'wallet': 'W2', 'at': now, 'legs': [{'pairAddress': 'P2', 'usd': 100, 'tokens': 100}]},                # flat
        {'id': 'gone', 'wallet': 'W3', 'at': now, 'closedAt': now, 'legs': [{'pairAddress': 'P2', 'usd': 1, 'tokens': 1}]}]})
    cards = {c['id']: c for c in asyncio.run(rs.fuse_arena_public())['mega']}
    assert set(cards) == {'win', 'meh'} and cards['win']['activity']['tier'] == 'blazing' and cards['win']['kind'] == 'user'


def test_round_move_is_none_when_the_feed_lost_the_coin(rs):
    live = {'passing': [{'mint': 'A', 'price': 1.5}], 'dropped': []}
    assert rs._round_move({'mint': 'A', 'entry': 1.0}, live) == 50.0
    assert rs._round_move({'mint': 'Z', 'entry': 1.0}, live) is None

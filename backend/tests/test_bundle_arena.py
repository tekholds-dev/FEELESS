"""Bundle pricing (flat $ per coin for cards bought all at once; Cmd Ctr free), 12-leg Cmd Ctr cards, Arena activity tiers,
and a Runners tab that is never dead (every passing coin + watch-only failures)."""
import asyncio
import time

import pytest

import fuse_hq as hq

MEME = 'Meme1111111111111111111111111111111111111111'


def test_bundle_bps_flat_per_coin_capped_and_bounded():
    b = {'on': True, 'perLegUsd': 0.10, 'maxPct': 5, 'maxLegUsd': 50}
    assert hq.bundle_bps(20, b) == 50            # 10c on a $20 leg = 0.5%
    assert hq.bundle_bps(0.5, b) == 500          # 10c on 50c would be 20% → capped at 5%
    assert hq.bundle_bps(80, b) is None          # big legs pay the normal % (no flat-fee loophole)
    assert hq.bundle_bps(0, b) is None and hq.bundle_bps(20, {**b, 'on': False}) is None
    assert hq.clean_bundle({'perLegUsd': 99, 'maxPct': 'x'}) == {'on': True, 'perLegUsd': 5.0, 'maxPct': 5.0, 'maxLegUsd': 50.0}


def test_leg_mix_traders_3_plus_3_cmd_ctr_12_any_mix():
    assert hq.legs_ok(3, 3) and not hq.legs_ok(4, 0) and not hq.legs_ok(0, 4)
    assert hq.legs_ok(6, 6, admin=True) and hq.legs_ok(0, 12, admin=True) and hq.legs_ok(12, 0, admin=True)
    assert not hq.legs_ok(7, 6, admin=True)


def test_activity_tiers_are_hard_coded_from_real_activity():
    assert hq.activity()['tier'] == 'calm'
    hot = hq.activity(buys24h=6, buyers=4, flow_usd=250_000, move_pct=12)
    assert hot['tier'] in ('hot', 'blazing') and 0 <= hot['score'] <= 100
    assert hq.activity(buys24h=99, buyers=99, flow_usd=1e12, move_pct=999) == {'score': 100, 'tier': 'blazing'}


@pytest.fixture
def rs(monkeypatch, request):
    rs = pytest.importorskip('reputation_service')
    if 'feecat_card' not in request.node.name:   # never reach the live FeeCat service from a test
        async def no_cat(): return None
        monkeypatch.setattr(rs, '_feecat_card', no_cat); monkeypatch.setattr(rs, '_feecat_raw', no_cat)
    async def sol(): return 150.0
    monkeypatch.setattr(rs, '_sol_usd_live', sol)
    cfg = {**rs.FEE_DEFAULTS, 'platformFeeBps': 100, 'feeAccountSol': 'SolAcct', 'feeAccountUsdc': 'UsdcAcct', 'tierDiscountPct': {'0': 0},
           'bundle': {'on': True, 'perLegUsd': 0.10, 'maxPct': 5, 'maxLegUsd': 50}}
    monkeypatch.setattr(rs, '_fee_cfg', lambda: cfg)
    async def tier(_w): return (0, 0)
    async def sol(): return 200.0
    monkeypatch.setattr(rs, '_perk_tier', tier); monkeypatch.setattr(rs, '_sol_usd_live', sol)
    return rs


def test_bundle_leg_pays_flat_and_cmd_ctr_pays_nothing(rs, monkeypatch):
    normal = asyncio.run(rs.effective_fee('Wa11et', rs.WSOL_MINT, MEME, 0, 0.1))
    leg = asyncio.run(rs.effective_fee('Wa11et', rs.WSOL_MINT, MEME, 3, 0.1))      # 0.1 SOL = $20 leg
    assert normal['bps'] == 100 and leg['bps'] == 50 and any('Bundle pricing' in n for n in leg['notes'])
    monkeypatch.setattr(rs, '_is_staff', lambda a: a == 'Staff1')
    staff = asyncio.run(rs.effective_fee('Staff1', rs.WSOL_MINT, MEME, 3, 0.1))
    assert staff['bps'] == 0 and 'Cmd Ctr' in staff['notes'][0]
    assert asyncio.run(rs.effective_fee('Staff1', rs.WSOL_MINT, MEME, 0, 0.1))['bps'] == 100   # single swaps still pay


def pick(m, **kw):
    return {'mint': m, 'symbol': m, 'price': 1.0, 'score': 80, 'stage': 'graduated', 'curve': 100, 'chg1h': 10, 'ageH': 5, 'pairAddress': f'p{m}', 'vol1h': 9000, **kw}


def test_discover_lists_every_passing_coin_and_watch_only_failures(rs, monkeypatch):
    live = {'passing': [pick('A'), pick('B')], 'dropped': [{**pick('Z'), 'gates': ['top10 41% > 30%']}], 'seen': 3}
    async def lv(): return live
    async def board(days=30): return {'rows': []}
    monkeypatch.setattr(rs, '_runner_live', lv); monkeypatch.setattr(rs, 'caller_board', board)
    rs._runner_disc_cache.update(at=0, data=None)
    out = asyncio.run(rs.runners_discover())
    assert {r['mint'] for r in out['runners']} == {'A', 'B'}
    assert out['watching'][0]['mint'] == 'Z' and out['watching'][0]['gates'] == ['top10 41% > 30%']


def test_arena_stages_cmd_ctr_mega_cards_and_lit_cards_with_activity(rs, monkeypatch):
    now = time.time()
    async def lv(): return {'passing': [pick('A')], 'dropped': [], 'seen': 1}
    async def view(fid, f, store):
        return {'id': fid, 'name': f['name'], 'emoji': '⚛️', 'legs': f['legs'], 'index': 112.0, 'score': {'grade': 'A'}, 'volume24h': 500000, 'trust': {'buyers': 3}}
    monkeypatch.setattr(rs, '_runner_live', lv); monkeypatch.setattr(rs, '_fuse_view', view)
    rs._arena_mega_cache.update(at=0, data=None)
    legs = [{'chainId': 'solana', 'pairAddress': f'P{i}', 'weight': 1} for i in range(12)]
    rs._json_save(rs.FUSES_PATH, {'fuses': {'f1': {'name': 'Mega', 'legs': legs, 'arena': True}, 'f2': {'name': 'Off', 'legs': legs}},
                                  'buys': [{'fuse': 'f1', 'wallet': f'W{i}', 'usd': 5, 'at': now} for i in range(4)]})
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [], 'paths': {'A': [[now, 1.3]]}, 'litCards': [{'id': 'L1', 'at': now - 60, 'picks': [{'mint': 'A', 'symbol': 'A', 'entry': 1.0, 'lane': 'runner'}], 'proof': {}}]})
    out = asyncio.run(rs.fuse_arena_public())['mega']
    kinds = {c['kind']: c for c in out}
    assert set(kinds) == {'mega', 'lit'} and len(kinds['mega']['legs']) == 12
    assert kinds['mega']['activity']['tier'] in ('hot', 'blazing')
    assert [c['activity']['score'] for c in out] == sorted((c['activity']['score'] for c in out), reverse=True)


def test_fuse_fees_count_only_card_legs_from_the_ledger():
    now = 10_000_000
    pos = [{'id': 'c1', 'legs': [{'sig': 's1'}, {'sig': 's2', 'sellSigs': ['s3']}]}]
    led = [{'sig': 's1', 'feeUsd': 0.1, 't': now - 60}, {'sig': 's2', 'feeUsd': 0.1, 't': now - 90000}, {'sig': 's3', 'feeUsd': 0.05, 't': now - 30},
           {'sig': 'swap', 'feeUsd': 9, 't': now}]                                       # a plain swap is not a Fuse fee
    f = hq.fuse_fees(pos, led, now)
    assert f == {'hour': 0.15, 'day': 0.15, 'week': 0.25, 'all': 0.25, 'legs': 3, 'cards': 1}


def test_vault_fee_wallet_is_saved_and_bundle_kept(rs, monkeypatch):
    import json
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Admin1')
    store = {'audit': [], 'fees': {'bundle': {'on': True, 'perLegUsd': 0.2, 'maxPct': 5, 'maxLegUsd': 50}}}
    monkeypatch.setattr(rs, '_admin_load', lambda: store); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    w = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'
    body = rs.FeeCfg(platformFeeBps=0, vaultFeeWallet=w)
    asyncio.run(rs.admin_fees_set(None, body))
    assert store['fees']['vaultFeeWallet'] == w and store['fees']['bundle']['perLegUsd'] == 0.2


def test_empty_stage_shows_the_live_round_as_a_proving_card(rs, monkeypatch):
    now = time.time()
    async def lv(): return {'passing': [pick('A', price=1.2)], 'dropped': [], 'seen': 1}
    monkeypatch.setattr(rs, '_runner_live', lv)
    rs._arena_mega_cache.update(at=0, data=None)
    rs._json_save(rs.FUSES_PATH, {'fuses': {}})
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [{'id': 'r9', 'at': now, 'picks': [{'mint': 'A', 'symbol': 'A', 'entry': 1.0, 'lane': 'runner'}]}], 'paths': {}})
    [c] = asyncio.run(rs.fuse_arena_public())['mega']
    assert c['kind'] == 'round' and c['index'] == 120.0 and c['activity']['score'] > 0

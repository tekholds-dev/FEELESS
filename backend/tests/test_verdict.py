"""🧾 What's working / what's not: one verdict over every engine's own record."""
import verdict as v


def test_judge_needs_samples_and_both_average_and_median():
    assert v.judge(2, 9, 9, 5)[0] == 'watch'                    # too few to call
    assert v.judge(10, 4, 1.5, 5)[0] == 'keep'
    assert v.judge(10, -3, -1, 5)[0] == 'scrap'
    assert v.judge(10, 12, -2, 5)[0] == 'watch'                 # one moonshot lifts the average, the typical run still loses


def test_build_ranks_losers_first_and_says_nothing_is_proven_when_nothing_wins():
    out = v.build(tiers={'degen': {'label': '🔥 Prime Blaze', 'pcts': [-8, -3, -12, 2, -5, -6]}},
                  strategies=[{'style': 'dip', 'runs': 4, 'avgPct': -2.0, 'medPct': -1.0, 'winRate': 25}],
                  lanes={'scalp': {'n': 3, 'avgPct': 5, 'winRate': 66}},
                  sim_score={'clock': {'5': {'n': 60, 'medPct': -4.0, 'avgPct': -2.0, 'upPct': 30.0}}},
                  real=[{'label': '🔥 Prime Blaze', 'pnlPct': -12.5, 'feesPct': 4.2, 'perHour': 9, 'swaps': 120, 'holdSolPct': 1.0}])
    assert out['keep'] == 0 and out['rows'][0]['verdict'] == 'scrap' and 'Nothing is proven' in out['headline']
    names = {(r['area'], r['name']): r['verdict'] for r in out['rows']}
    assert names[('🏃 Runner lane', 'scalp')] == 'watch'                              # 3 rounds isn't proof
    assert names[('🧠 Sim config', 'round length (min) = 5')] == 'scrap'
    real = next(r for r in out['rows'] if r['area'] == '💵 Real run')
    assert real['verdict'] == 'scrap' and 'fees 4.2%' in real['why'] and 'SOL did +1.0%' in real['why']


def test_build_names_the_strongest_working_thing():
    out = v.build(tiers={'safe': {'label': '💎 Prime Diamond', 'pcts': [3, 5, 2, 8, 1]}}, clocks={'60': {'bells': 6, 'avgPct': 1.2}, '5': {'bells': 9, 'avgPct': -0.8}})
    assert out['keep'] == 2 and out['scrap'] == 1 and 'Prime Diamond' in out['headline']


def test_verdict_endpoint_reads_the_records_without_touching_anything(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs').append({'card': 'safe', 'pct': 4.0, 'at': 1.0, 'real': False})
    rs._json_save(rs.PG_SIM_PATH, {'score': {'clock': {'60': {'n': 40, 'medPct': 1.0, 'avgPct': 2.0, 'upPct': 60.0}}}})
    out = asyncio.run(rs.fuse_verdict(None))
    by = {(r['area'], r['name']): r for r in out['rows']}
    assert by[('⭐ Tier card', '💎 Prime Diamond')]['n'] == 1 and by[('🧠 Sim config', 'round length (min) = 60')]['verdict'] == 'keep'


def test_one_click_verdict_actions_apply_to_one_card_or_the_real_card_and_scrap_strategies(monkeypatch):
    import asyncio
    import pytest
    import arena_prime as ap
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {}, 'cards': {}}})
    act = lambda **k: asyncio.run(rs.fuse_verdict_act(None, rs.VerdictActIn(**k)))
    act(area='🧠 Sim config', name='freeze a runner at = 25', act='apply-one', tier='degen')
    cfg = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']['cfg']
    assert ap.tier_cfg(cfg, 'degen')['rideAt'] == 25 and ap.tier_cfg(cfg, 'safe')['rideAt'] == 50
    with pytest.raises(rs.HTTPException):
        act(area='🧠 Sim config', name='sell off its peak = 8', act='apply')                  # never all cards at once — each keeps its own
    act(area='🧠 Sim config', name='losing rounds before a swap = 2', act='apply-real')
    pr = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    assert pr['realCfg']['rotateConfirm'] == 2 and 'rotateConfirm' in pr['realOwnerSet']   # the owner's — the self-fix won't move it
    with pytest.raises(rs.HTTPException):
        act(area='🧠 Sim config', name='freeze a runner at = 7', act='apply')                 # not an option
    act(area='🏟 Strategy', name='degen', act='scrap')
    assert 'degen' in rs._retired([])
    act(area='🏟 Strategy', name='degen', act='keep')
    assert 'degen' not in rs._retired([{'style': 'degen', 'runs': 9, 'avgPct': -3, 'medPct': -2}])   # HQ kept it on the rails


def test_a_strategy_the_verdict_scraps_leaves_the_rails_by_itself_unless_the_owner_keeps_it(monkeypatch):
    import asyncio, reputation_service as rs
    rows = [{'area': '🏟 Strategy', 'name': 'bad', 'verdict': 'scrap', 'why': 'w'}, {'area': '🏟 Strategy', 'name': 'pinned', 'verdict': 'scrap', 'why': 'w'},
            {'area': '🏟 Strategy', 'name': 'good', 'verdict': 'keep', 'why': 'w'}, {'area': '⭐ Tier', 'name': 'bad', 'verdict': 'scrap', 'why': 'w'}]
    async def build(real=False):
        return {'rows': rows, 'keep': 1, 'scrap': 3, 'watch': 0}
    monkeypatch.setattr(rs, '_verdict_build', build); monkeypatch.setattr(rs, '_owner_wallets', lambda: [])
    rs._json_save(rs.FUSE_HQ_PATH, {'keptStyles': ['pinned'], 'scrappedStyles': ['good'], 'autoScrapped': ['good']})
    asyncio.run(rs._verdict_tick(1000.0))
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    assert d['scrappedStyles'] == ['bad'] and d['autoScrapped'] == ['bad']          # scrapped by itself · the pinned one untouched · the recovered one back on
    rs._json_save(rs.FUSE_HQ_PATH, {'autoScrap': False})
    asyncio.run(rs._verdict_tick(2000.0))
    assert not rs._json_load(rs.FUSE_HQ_PATH, {}).get('scrappedStyles')             # switched off = the owner's click only

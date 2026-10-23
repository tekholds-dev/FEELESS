import asyncio

import pytest


def test_house_fees_default_save_and_feed_every_reader(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_require_admin', lambda req: 'ADMIN')
    monkeypatch.setattr(rs, '_audit', lambda *a, **k: None)
    sent = []

    class _R:
        status_code = 200

    class _H:
        async def post(self, url, **kw):
            sent.append((url, kw.get('json')))
            return _R()
    monkeypatch.setattr(rs, '_ai_http', lambda: _H())
    assert rs._house() == rs.HOUSE_DEFAULTS                                                         # nothing saved → today's numbers
    out = asyncio.run(rs.admin_fees_house(None, rs.HouseFees(fuseCreatorMaxBps=2500, feecatFeePct=0.5, redeemMp=500_000, redeemFeecat=20_000)))
    assert out['feecatSynced'] and sent[-1] == ('http://127.0.0.1:5088/api/cats/internal/rules', {'rules': {'feePerSidePct': 0.5}})   # FeeCat gets her fee
    assert rs._house()['fuseCreatorMaxBps'] == 2500 and rs._world_feecat_rate() == (500_000, 20_000)
    got = asyncio.run(rs.admin_fees_get(None))
    assert got['fees']['house']['feecatFeePct'] == 0.5
    with pytest.raises(Exception):
        rs.HouseFees(fuseCreatorMaxBps=20_000)                                                      # never past 100 % of the fee
    with pytest.raises(Exception):
        rs.HouseFees(feecatFeePct=9)


def test_saving_the_main_fee_panel_keeps_the_house_fees():
    import reputation_service as rs
    src = open(rs.__file__).read()
    i = src.index('async def admin_fees_set(')
    assert "'crews', 'house')" in src[i:src.index('\n\n\n', i)]


def test_feecat_paper_fee_is_tunable_and_clamped():
    import feecat_service as fs
    assert fs.TUNABLE['feePerSidePct'] == (0.0, 5.0) and abs(fs.fee_side() - fs.FEE_PER_SIDE) < 1e-12
    was = fs.RULES['feePerSidePct']
    try:
        fs.RULES['feePerSidePct'] = 0.5
        assert fs.fee_side() == 0.005
    finally:
        fs.RULES['feePerSidePct'] = was

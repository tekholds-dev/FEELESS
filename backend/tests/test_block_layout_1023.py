"""🏝 The family town expands (owner, 2026-10-23): a saved layout per family — move buildings, pick lots, beauty plots, MY POOLS, islands by 15
(a new island costs the family bank MP; the creator wallet expands for free)."""
import block_markets as bm


def _fam():
    return {'owner': 'DON', 'block': [{'key': 'jito'}, {'key': 'orca'}], 'town': ['tt', 'perps']}


def test_the_layout_keeps_every_building_and_drops_junk():
    c = _fam()
    assert bm.layout_of(c) == ['blk:jito', 'blk:orca', 'town:tt', 'town:perps']                                 # never saved = buildings then the town
    c['layout'] = {'cells': ['town:perps', 'open', 'stand:park', 'pools', 'pools', 'stand:nope', 'blk:ghost', 'gap', 'blk:orca']}
    assert bm.layout_of(c) == ['town:perps', 'open', 'stand:park', 'pools', 'gap', 'blk:orca', 'blk:jito', 'town:tt']   # moved · one MY POOLS · missing appended


def test_only_the_don_underboss_or_creator_arranges_and_stands_are_capped():
    c = _fam()
    for who, staff, rank in (('X', False, None), ('U', False, {'U': 'soldier'})):
        try:
            bm.layout_set(c, ['open'], who, staff, rank); assert False
        except ValueError as e:
            assert 'Don or the Underboss' in str(e)
    assert bm.layout_set(c, ['stand:fountain', 'blk:orca'], 'DON')[:2] == ['stand:fountain', 'blk:orca'] and c['islands'] == 1
    try:
        bm.layout_set(c, ['stand:park'] * (bm.STANDS_MAX + 1), 'DON'); assert False
    except ValueError as e:
        assert 'stands' in str(e)


def test_a_new_island_costs_mp_and_the_creator_pays_nothing():
    c = _fam()
    cells = bm.layout_of(c) + ['open'] * 14                                                                        # 18 cells = 2 islands
    assert bm.expand_cost(c, cells) == (2, bm.ISLAND_MP) and bm.expand_cost(c, cells, staff=True) == (2, 0)
    bm.layout_set(c, cells, 'DON')
    assert c['islands'] == 2 and bm.expand_cost(c, cells) == (2, 0)                                                # paid once, kept


def test_the_layout_endpoint_charges_the_bank_only_after_every_check(monkeypatch):
    import asyncio
    import reputation_service as rs
    import family_city as fcy
    st = {'crews': {'c1': {'id': 'c1', 'owner': 'DON', 'members': ['DON'], 'block': [{'key': 'jito'}], 'town': ['tt']}}}
    saved = {}
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    monkeypatch.setattr(rs, '_json_load', lambda p, d=None: st)
    monkeypatch.setattr(rs, '_json_save', lambda p, o: saved.update(o=o))
    monkeypatch.setattr(rs, '_seat_of', lambda s, me: me)
    monkeypatch.setattr(rs, '_city_ctx', lambda c, me, now: (1.0, {}))
    monkeypatch.setattr(rs, '_is_staff', lambda me: me == 'CREATOR')

    async def view(c, *a, **k):
        return {'layout': bm.layout_of(c), 'bank': fcy.city_of(c, 0)['bank']}
    monkeypatch.setattr(rs, '_fblock_view', view)
    import crews
    monkeypatch.setattr(crews, 'crew_of', lambda s, me: s['crews']['c1'] if me in ('DON', 'CREATOR') else None)
    c = st['crews']['c1']; fcy.city_of(c, 0)['bank'] = 20_000; bank0 = 20_000
    two = ['blk:jito', 'town:tt'] + ['open'] * 16
    out = asyncio.run(rs.familia_block_layout(rs.BlockLayout(address='DON', session='s', cells=two)))
    assert out['bank'] == bank0 - bm.ISLAND_MP and c['islands'] == 2                                               # the Don pays MP for island 2
    three = two + ['gap'] * 12 + ['open']
    asyncio.run(rs.familia_block_layout(rs.BlockLayout(address='CREATOR', session='s', cells=three)))
    assert c['islands'] == 3 and fcy.city_of(c, 0)['bank'] == bank0 - bm.ISLAND_MP                                 # the creator: free

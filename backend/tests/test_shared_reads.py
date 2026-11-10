"""COL-9: never the same research twice. One proof's site reads serve the next proof of its kind while fresh; a stale or failed read is redone."""
import asyncio


def test_a_fresh_read_is_reused_a_stale_one_redone(monkeypatch):
    import feecat_service as fs
    opened = []
    async def read_first(http, kind, rows):
        opened.append(kind); return f'read {len(opened)}', [{'host': 'espn.com', 'ok': True}]
    monkeypatch.setattr(fs._feat._sources, 'read_first', read_first); monkeypatch.setattr(fs._stash, 'trust_rows', lambda *a: [])
    monkeypatch.setattr(fs, '_src_note', lambda *a: None); fs._READS.clear()
    clock = [1000.0]; monkeypatch.setattr(fs.time, 'time', lambda: clock[0])
    assert asyncio.run(fs._site_reads('pob'))[0] == 'read 1'
    clock[0] += 60
    assert asyncio.run(fs._site_reads('pob'))[0] == 'read 1' and opened == ['pob'] and fs._READS['pob'][3] == 1   # reused, counted
    clock[0] += fs.READ_FRESH_S['pob']
    assert asyncio.run(fs._site_reads('pob'))[0] == 'read 2'   # stale: read again
    assert asyncio.run(fs._site_reads('pow'))[0] == 'read 3'   # another kind never borrows
    async def none_ok(http, kind, rows):
        opened.append(kind); return 'x', [{'host': 'down.io', 'ok': False}]
    monkeypatch.setattr(fs._feat._sources, 'read_first', none_ok); fs._READS.clear()
    asyncio.run(fs._site_reads('poc')); asyncio.run(fs._site_reads('poc'))
    assert opened[-2:] == ['poc', 'poc']   # a read where nothing opened is never reused

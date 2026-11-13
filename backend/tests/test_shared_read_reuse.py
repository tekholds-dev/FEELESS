"""COL-9: one agent's fresh read is reused by the next agent's proof of that kind, and the reusing folder says whose read and how old.
Fake site reads; no network."""
import asyncio

import feecat_service as fs


def test_the_second_agent_reuses_the_first_agents_fresh_read_and_says_so(monkeypatch):
    opened = []
    async def read_first(http, kind, trust):
        opened.append(kind); return 'LINE', [{'host': 'espn.com', 'name': 'ESPN', 'ok': True}]
    monkeypatch.setattr(fs._feat._sources, 'read_first', read_first); monkeypatch.setattr(fs._stash, 'trust_rows', lambda *a: [])
    monkeypatch.setattr(fs, '_src_note', lambda *a: None); monkeypatch.setattr(fs, '_READS', {})
    line1, rows1 = asyncio.run(fs._site_reads('pob', ('a1', 'Happy')))
    line2, rows2 = asyncio.run(fs._site_reads('pob', ('a2', 'Sicario')))
    line3, rows3 = asyncio.run(fs._site_reads('pob', ('a1', 'Happy')))
    assert opened == ['pob'] and line1 == line2 == 'LINE'                      # opened once, read twice
    assert 'sharedBy' not in rows1[0] and rows2[0]['sharedBy'] == 'Happy' and rows2[0]['sharedAgo'] >= 0
    assert 'sharedBy' not in rows3[0]                                          # its own read is not "shared"
    assert fs._READS['pob'][3] == 2

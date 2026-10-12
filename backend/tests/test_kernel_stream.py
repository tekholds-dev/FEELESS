"""📡 The kernel's delta stream: only what changed is sent, a subscriber that fell behind resyncs once, the endpoint is HQ-only and runs nothing."""
import asyncio
import json
from pathlib import Path

import pytest

import trench_kernel.events as ev

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def test_an_unchanged_thing_sends_nothing_and_a_changed_one_sends_one_delta():
    h = ev.Hub()
    a = h.publish('candidate_update', 'M', {'status': 'CONTENDING', 'rank': 110}, 1.0)
    assert a['seq'] == 1 and h.publish('candidate_update', 'M', {'rank': 110, 'status': 'CONTENDING'}, 2.0) is None     # same content (key order aside): nothing
    b = h.publish('candidate_update', 'M', {'status': 'READY', 'rank': 131}, 3.0)
    assert b['seq'] == 2 and h.stats()['skippedUnchanged'] == 1 and h.stats()['sent']['candidate_update'] == 2
    with pytest.raises(AssertionError):
        h.publish('made_up_kind', 'x', {}, 4.0)


def test_sync_sends_changes_and_a_null_for_what_is_gone():
    h = ev.Hub()
    assert len(h.sync('position_update', {'A': {'pct': 1.0}, 'B': {'pct': 2.0}}, 1.0)) == 2
    out = h.sync('position_update', {'A': {'pct': 1.5}}, 2.0)                       # A moved, B left the card
    assert [(e['key'], e['data']) for e in out] == [('A', {'pct': 1.5}), ('B', None)]
    assert h.sync('position_update', {'A': {'pct': 1.5}}, 3.0) == []                # nothing changed: nothing sent


def test_a_subscriber_gets_only_what_is_newer_and_resyncs_when_it_fell_behind():
    h = ev.Hub(keep=5)
    for i in range(3):
        h.publish('metric_update', 'm', {'i': i}, float(i))
    evs, gap = h.since(1)
    assert [e['seq'] for e in evs] == [2, 3] and not gap
    for i in range(3, 12):
        h.publish('metric_update', 'm', {'i': i}, float(i))
    assert h.since(1) == ([], True)                                                 # older than the log: reload the snapshot ONCE
    assert h.since(999) == ([], True)                                               # a sequence from before a restart
    assert [e['seq'] for e in h.since(h.seq - 1)[0]] == [h.seq]


def test_waiting_wakes_on_a_delta_and_times_out_quietly():
    async def go():
        h = ev.Hub()
        assert await h.wait(0, 0.02) is False
        t = asyncio.ensure_future(h.wait(0, 2.0))
        await asyncio.sleep(0.01)
        h.publish('hunter_update', 'lanes', [1], 1.0)
        return await t, len(h.subs)
    assert asyncio.run(go()) == (True, 0)


def test_the_sse_frame_carries_the_sequence_the_kind_and_the_data():
    f = ev.sse({'seq': 7, 'kind': 'position_update', 'key': 'M', 'at': 12.5, 'data': {'pct': 3.2}})
    assert f.startswith('id: 7\nevent: position_update\ndata: ') and f.endswith('\n\n')
    assert json.loads(f.split('data: ')[1]) == {'key': 'M', 'at': 12.5, 'data': {'pct': 3.2}}


def test_the_service_publishes_deltas_per_pass_per_tick_and_per_live_price(monkeypatch):
    import reputation_service as rs
    h = ev.Hub()
    monkeypatch.setattr(ev, 'HUB', h)
    cand = lambda m, st, rank: {'mint': m, 'symbol': m, 'status': st, 'rank': rank, 'ages': {'price': 3.0}, 'decidedAgo': 4.0, 'times': {'price': 100.0}, 'decidedAt': 99.0}
    payload = {'at': 100.0, 'positions': [{'mint': 'H', 'pct': 2.0, 'bars': [[1, 2, 3]] * 40}], 'agents': [{'key': 'tally', 'task': 't', 'decision': 'd', 'card': {'status': 'active'}}],
               'generations': [{'role': 'tally', 'generation': 1, 'status': 'ACTIVE'}], 'kernel': {'candidates': [cand('A', 'READY', 130), cand('B', 'CONTENDING', 90)], 'lanes': [{'lane': 1, 'state': 'ARMED', 'mint': 'A'}], 'metrics': {'mints': 2}},
               'mission': {}, 'enrich': {'queueDepth': 0}, 'rpcStats': {'logical': 0}}
    monkeypatch.setitem(rs._office, 'payload', payload)
    rs._hub_publish(100.0)
    kinds = [e['kind'] for e in h.log]
    assert set(kinds) >= {'position_update', 'execution_update', 'candidate_update', 'hunter_update', 'agent_update', 'lifecycle_update', 'metric_update', 'snapshot'}
    c = next(e for e in h.log if e['kind'] == 'candidate_update' and e['key'] == 'A')['data']
    assert 'ages' not in c and 'decidedAgo' not in c and c['times'] == {'price': 100.0} and c['decidedAt'] == 99.0       # absolute times only: freshness stays explicit
    assert 'bars' not in next(e for e in h.log if e['kind'] == 'position_update')['data']
    n = h.seq
    payload['kernel']['candidates'][0]['ages'] = {'price': 21.0}; payload['kernel']['candidates'][0]['decidedAgo'] = 22.0   # a later pass, nothing really changed
    rs._hub_publish(118.0)
    assert [e['kind'] for e in h.log[n:]] == ['metric_update', 'snapshot'][-len(h.log[n:]):] and all(e['kind'] in ('metric_update', 'snapshot') for e in h.log[n:])
    n = h.seq
    payload['positions'][0]['pct'] = 3.5
    rs._hub_publish(119.0, light=True)                                              # a tier tick: only the position moved
    assert [(e['kind'], e['key']) for e in h.log[n:]] == [('position_update', 'H')]
    assert "_tke.HUB.publish('mint_update', m_," in SRC and "_hub_publish(now, light=True)" in SRC and "    _hub_publish(now)   # 📡 this pass as DELTAS" in SRC


def test_the_stream_is_hq_only_and_runs_nothing():
    from fastapi.testclient import TestClient
    import reputation_service as rs
    r = TestClient(rs.app).get('/api/reputation/admin/agents/stream')
    assert r.status_code in (401, 403)                                              # no HQ signature, no stream
    body = SRC[SRC.index('async def admin_agents_stream('):SRC.index('def _office_light(tid, cur, now):')]
    assert '_require_admin(request)' in body
    for forbidden in ('_runner_intel', 'token_intel', '_jup_prices', '_fw_', '_prime_tick', '_agents_tick', '_rpc(', '_krpc('):
        assert forbidden not in body, forbidden

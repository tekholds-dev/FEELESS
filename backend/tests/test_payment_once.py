"""💳 Audit 2026-11-12 #5: one payment signature buys ONE thing. Parallel requests with the same signature used to each pass the used-check
(it ran before a slow on-chain read) and each add rounds; a crew payment could also buy rounds."""
import asyncio
import json

import pytest

SIG = '5' * 88


@pytest.fixture()
def rs(monkeypatch, tmp_path):
    import reputation_service as rs
    monkeypatch.setattr(rs, 'FUSE_HQ_PATH', tmp_path / 'fuse_hq.json'); monkeypatch.setattr(rs, 'CREWS_PATH', tmp_path / 'crews.json')
    rs._PAY_HELD.clear()
    return rs


def test_parallel_buys_with_one_payment_spend_it_once(rs, monkeypatch):
    calls = {'read': 0}

    async def slow_read(p):   # stands in for the on-chain lookup: every request waits here at the same time
        calls['read'] += 1; await asyncio.sleep(0.05)
        raise rs.HTTPException(400, 'stop after the read')
    monkeypatch.setattr(rs, '_fuse_rounds', slow_read)
    p = rs.RoundsIn(**{k: v for k, v in {'id': 'x', 'mode': 'pay', 'signature': SIG, 'address': 'A', 'session': 's'}.items() if k in rs.RoundsIn.model_fields})

    async def many():
        return await asyncio.gather(*(rs.fuse_rounds(p) for _ in range(5)), return_exceptions=True)
    out = asyncio.run(many())
    assert calls['read'] == 1                                          # only the first request reached the chain read
    assert sum(1 for e in out if getattr(e, 'status_code', 0) == 409) == 4
    assert SIG not in rs._PAY_HELD                                     # it failed, so the payment is free again


def test_a_payment_used_for_a_crew_cannot_buy_rounds(rs):
    (rs.CREWS_PATH).write_text(json.dumps({'sigs': [SIG]}))
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs._pay_hold(SIG))
    assert e.value.status_code == 409

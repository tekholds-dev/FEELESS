"""✗ Staff strike of an agent desk line that claims a withdraw which never landed (owner's $1 Happy test 2026-11-14: 2WWDzeQGRn… logged
"sent back", the chain had nothing). The chain decides — the network is faked here."""
import asyncio

import pytest

import reputation_service as rs  # noqa: I001 — the service first: it loads its route modules at its end
import rep_money_routes as rm

NOW = 1_800_000_000.0


def _ev(**k):
    return {'id': 'e1', 'catId': 'c1', 'type': 'WITHDRAW', 'ts': (NOW - 600) * 1000,
            'detail': "0.01 SOL sent back to its owner's wallet (2WWDzeQGRn…).", **k}


def _proof(monkeypatch, ev, answers):
    async def rpc(_h, method, _p):
        return answers[method]
    monkeypatch.setattr(rs, '_krpc', rpc)
    return asyncio.run(rm.void_proof(rs, None, ev, 'WALLET', now=NOW))


def test_an_old_line_whose_prefix_is_not_on_chain_can_be_struck(monkeypatch):
    rows = [{'signature': '2SWmxiRH43abc', 'blockTime': NOW - 300}, {'signature': 'tdnz7gZm7xabc', 'blockTime': NOW - 900}]
    assert _proof(monkeypatch, _ev(), {'getSignaturesForAddress': rows}) is None


def test_a_line_that_did_land_is_never_struck(monkeypatch):
    rows = [{'signature': '2WWDzeQGRnFULL', 'blockTime': NOW - 590}]
    assert 'landed' in _proof(monkeypatch, _ev(), {'getSignaturesForAddress': rows})
    landed = {'getSignatureStatuses': {'value': [{'confirmationStatus': 'finalized', 'err': None}]}}
    assert 'landed' in _proof(monkeypatch, _ev(sig='FULLSIG'), landed)
    assert _proof(monkeypatch, _ev(sig='FULLSIG'), {'getSignatureStatuses': {'value': [None]}}) is None   # a full sig the chain never saw


def test_too_new_not_a_withdraw_already_struck_or_unprovable_are_refused(monkeypatch):
    assert 'Too new' in _proof(monkeypatch, _ev(ts=(NOW - 30) * 1000), {})
    assert 'Only a withdraw' in _proof(monkeypatch, _ev(type='BUY'), {})
    assert 'already' in _proof(monkeypatch, _ev(voided={'why': 'x'}), {})
    full = [{'signature': f'X{i}', 'blockTime': NOW} for i in range(1000)]   # 1,000 newer rows: the list never reaches back to the line
    assert 'Too many' in _proof(monkeypatch, _ev(), {'getSignaturesForAddress': full})


def test_only_staff_can_strike(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(rs, 'session_address', lambda _s: 'NOTSTAFF'); monkeypatch.setattr(rs, '_is_staff', lambda _a: False)
    with pytest.raises(HTTPException) as e:
        asyncio.run(rm.cat_event_void('c1', 'e1', {'address': 'NOTSTAFF', 'session': 'session-x'}))
    assert e.value.status_code == 403


def test_a_struck_line_is_kept_but_hidden_from_the_feed(monkeypatch):
    import feecat_service as fs
    store = {'cats': {}, 'events': [{'id': 'a', 'catId': 'c1', 'type': 'WITHDRAW', 'voided': {'why': 'never landed'}},
                                    {'id': 'b', 'catId': 'c1', 'type': 'BUY'}]}
    monkeypatch.setattr(fs, '_load', lambda: store)
    got = asyncio.run(fs.activity('c1'))
    ids = [e['id'] for e in (got.get('events') if isinstance(got, dict) else [])]
    assert ids == ['b'] and len(store['events']) == 2

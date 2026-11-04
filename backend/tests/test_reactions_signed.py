"""🔒 A wallet's reaction needs that wallet's signed session; a guest votes only as its own browser id."""
import asyncio

import pytest
from fastapi import HTTPException

import reputation_service as rs

ME = 'A' * 32


def vote(voter, session=None):
    return asyncio.run(rs.react(rs.ReactPayload(room='fee-room', messageId='m1', emoji='🔥', voter=voter, session=session)))


def voters():
    return rs._react_load()['rooms'].get('fee-room', {}).get('m1', {}).get('🔥', [])


def test_nobody_votes_as_a_wallet_without_its_session(monkeypatch):
    monkeypatch.setattr(rs, 'session_address', lambda t: {'mine': ME, 'other': 'B' * 32}.get(t))
    monkeypatch.setattr(rs, 'primary_of', lambda a: a)
    for s in (None, 'bad', 'other'):
        with pytest.raises(HTTPException) as e:
            vote(ME, s)
        assert e.value.status_code == 401
    assert voters() == []
    assert vote(ME, 'mine') == {'ok': True} and voters() == [ME]


def test_a_guest_votes_as_its_browser_with_no_session():
    assert vote('browser-abc123') == {'ok': True} and voters() == ['browser-abc123']

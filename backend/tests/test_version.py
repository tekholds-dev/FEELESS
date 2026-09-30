"""Footer build tag: a machine running stale code says so (git is faked)."""
import asyncio

import reputation_service as rs


def test_version_reports_head_branch_and_how_far_behind(monkeypatch):
    answers = {('rev-parse', '--short', 'HEAD'): 'abc1234', ('rev-parse', '--abbrev-ref', 'HEAD'): 'claude/old-branch',
               ('rev-list', '--count', 'HEAD..origin/main'): '7', ('status', '--porcelain', '--untracked-files=no'): ' M frontend/yarn.lock'}

    async def git(*args, timeout=8):
        return answers.get(args, '')
    monkeypatch.setattr(rs, '_git', git); rs._version_cache.clear()
    v = asyncio.run(rs.version())
    assert v == {'head': 'abc1234', 'branch': 'claude/old-branch', 'behind': 7, 'dirty': ['frontend/yarn.lock'], 'fix': 'bash scripts/update.sh'}


def test_one_click_update_is_refused_from_anywhere_but_localhost():
    import pytest
    from fastapi import HTTPException

    class Req:
        def __init__(self, host, origin=''):
            self.client = type('C', (), {'host': host})(); self.headers = {'origin': origin}
    with pytest.raises(HTTPException) as e:
        asyncio.run(rs.local_update(Req('203.0.113.9')))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException):
        asyncio.run(rs.local_update(Req('127.0.0.1', 'https://evil.example')))   # a page elsewhere can't trigger it via a local proxy

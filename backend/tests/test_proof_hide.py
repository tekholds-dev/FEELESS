"""🗂 A filed proof can leave its owner's folders, but its record stays: hiding never improves an agent."""
import asyncio

import pytest

import feecat_service as fs


def test_hide_and_put_back(monkeypatch):
    store = {'cats': {'c1': {'id': 'c1', 'name': 'A', 'powFolders': [{'id': 'p1', 'n': 1, 'status': 'closed', 'score': 12}]}}}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: 'OWNER')
    run = lambda **k: asyncio.run(fs.cat_work('c1', fs.WorkPayload(op='proof_hide', session='s', **k)))
    assert run(job='powFolders', text='p1') == {'hidden': True, 'id': 'p1'}
    row = store['cats']['c1']['powFolders'][0]
    assert row['hidden'] is True and row['score'] == 12 and row['status'] == 'closed'
    assert run(job='powFolders', text='p1', on=False)['hidden'] is False
    with pytest.raises(fs.HTTPException):
        run(job='wallet', text='p1')
    with pytest.raises(fs.HTTPException):
        run(job='powFolders', text='nope')

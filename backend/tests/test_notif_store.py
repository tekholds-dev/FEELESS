"""🗄 SITE-8: the notification inbox and saved looks live one row per wallet in SQLite, so many workers can write at once and none loses
another's alert (the old notifications.json was rewritten whole — 4 MB — on every alert)."""
import json
import multiprocessing as mp

import pytest

rs = pytest.importorskip('reputation_service')
A = 'Aaaa1111111111111111111111111111111111111111'
B = 'Bbbb1111111111111111111111111111111111111111'


def test_notify_dedupes_by_once_caps_at_200_and_read_marks_all(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'NOTIF_PATH', tmp_path / 'notifications.json')
    monkeypatch.setattr(rs, '_push_load', lambda: {'subs': {}})
    rs.notify(A, 'reward', 'first', once='k1'); rs.notify(A, 'reward', 'again', once='k1'); rs.notify(B, 'follow', 'hi')
    assert [n['text'] for n in rs._notif_box(A)] == ['first'] and rs._notif_box(B)[0]['kind'] == 'follow'
    for i in range(205):
        rs.notify(A, 'mention', f'm{i}', push=False)
    box = rs._notif_box(A); assert len(box) == 200 and box[0]['text'] == 'm204'          # newest first, 200 kept
    rs.notify(A, 'mention', 'self', actor=A); assert rs._notif_box(A)[0]['text'] == 'm204'   # never notified of your own act
    monkeypatch.setattr(rs, 'session_address', lambda t: A if t == 's' else None)
    import asyncio
    asyncio.run(rs.notifications_read({'address': A, 'session': 's'}))
    assert all(n['read'] for n in rs._notif_box(A)) and not rs._notif_box(B)[0]['read']   # only your own inbox


def test_old_file_moves_in_once_and_stays_as_a_read_only_backup(monkeypatch, tmp_path):
    old = tmp_path / 'notifications.json'; old.write_text(json.dumps({A: [{'id': 'x', 'text': 'kept'}]}))
    monkeypatch.setattr(rs, 'NOTIF_PATH', old)
    assert rs._notif_box(A)[0]['text'] == 'kept' and (old.stat().st_mode & 0o777) == 0o400
    th = tmp_path / 'themes.json'; th.write_text(json.dumps({A: {'look': 'obsidian', 'at': 1}}))
    monkeypatch.setattr(rs, 'THEMES_PATH', th)
    assert rs._themes().get(A)['look'] == 'obsidian'


def _hammer(path, wallet, n):
    """A worker writing the inbox the way notify() does (newest first, 200 kept), on sql_store only: a child process never imports the
    service, so it can never reach backend/data outside the conftest sandbox."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
    import sql_store
    d = sql_store.Docs(path)
    for i in range(n):
        d.update(wallet, lambda box, i=i: [{'id': f'{wallet[:4]}-{i}'}, *(box or [])][:200])


def test_four_processes_writing_one_inbox_store_lose_nothing(tmp_path):
    path = str(tmp_path / 'notifications.json')
    ctx = mp.get_context('spawn')
    ps = [ctx.Process(target=_hammer, args=(path, w, 40)) for w in (A, A, B, B)]
    [p.start() for p in ps]; [p.join(120) for p in ps]
    assert all(p.exitcode == 0 for p in ps)
    import sql_store
    d = sql_store.Docs(tmp_path / 'notifications.json')
    assert len(d.get(A)) == 80 and len(d.get(B)) == 80                                      # 4 writers, every alert kept

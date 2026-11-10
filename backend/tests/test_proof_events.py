"""COL-3: the proof event history is append-only, chained with its own key, keeps one copy of each fact, and survives two writers."""
import sqlite3
import threading

import pytest

import proof_events as pe

K = b'k' * 32
DAY = 86400


def _db(tmp_path):
    return tmp_path / pe.DB_NAME


def _three(p):
    pe.append(p, 'pos', 'ws1', 'plan', {'by': 'OSSY'}, cat='c1', key=K, at=100)
    pe.append(p, 'pos', 'ws1', 'build', {'v': 1}, cat='c1', key=K, at=101)
    pe.append(p, 'PoStatic', 'ws1', 'file', {'status': 'closed'}, cat='c1', key=K, at=102)   # a kind's code name reads as the kind


def test_rows_chain_in_order_and_verify(tmp_path):
    p = _db(tmp_path); _three(p)
    v = pe.verify(p, key=K)
    assert v['ok'] and v['count'] == 3 and v['head'] == pe.head(p)
    rows = pe.history(p, 'pos', 'ws1')
    assert [r['event'] for r in rows] == ['plan', 'build', 'file'] and rows[0]['prev'] == pe.GENESIS and rows[1]['prev'] == rows[0]['mac']
    assert pe.verify(p, key=b'x' * 32)['ok'] is False   # another key (the Pool's) cannot vouch for these rows


def test_bad_events_are_refused(tmp_path):
    p = _db(tmp_path)
    for kind, ref, ev, data in (('pox', 'r', 'file', {}), ('pos', 'r', 'deleted', {}), ('pos', '', 'file', {}), ('pos', 'r', 'file', ['x'])):
        with pytest.raises(ValueError):
            pe.append(p, kind, ref, ev, data, key=K)
    assert pe.head(p) is None


@pytest.mark.parametrize('sql,why', [
    ("UPDATE events SET data = '{\"status\":\"won\"}' WHERE n = 2", 'changed after it was written'),
    ('DELETE FROM events WHERE n = 2', 'row 2 is missing'),
    ("UPDATE events SET at = 999 WHERE n = 1", 'changed after it was written'),
    ("UPDATE events SET event = 'grade' WHERE n = 3", 'changed after it was written'),
])
def test_tampering_is_caught(tmp_path, sql, why):
    p = _db(tmp_path); _three(p)
    c = sqlite3.connect(p); c.execute(sql); c.commit(); c.close()
    v = pe.verify(p, key=K)
    assert v['ok'] is False and why in v['why']


def test_a_forged_row_without_the_key_is_caught(tmp_path):
    p = _db(tmp_path); _three(p); n, mac = pe.head(p)
    c = sqlite3.connect(p)
    c.execute('INSERT INTO events VALUES (4, ?, 200, ?, ?, ?, ?, ?, ?, ?)', ('e' * 32, 'pos', 'ws1', 'c1', 'grade', '{"graded":"right"}', mac, 'f' * 64))
    c.commit(); c.close()
    v = pe.verify(p, key=K)
    assert v['ok'] is False and v['brokenAt'] == 4


def test_cutting_the_newest_rows_needs_a_kept_head(tmp_path):
    p = _db(tmp_path); _three(p); kept = pe.head(p)
    c = sqlite3.connect(p); c.execute('DELETE FROM events WHERE n = 3'); c.commit(); c.close()
    assert pe.verify(p, key=K)['ok'] is True   # a shorter chain still links: honest about the limit
    v = pe.verify(p, key=K, expect=kept)
    assert v['ok'] is False and 'cut back' in v['why']


def test_replays_are_kept_once(tmp_path):
    p = _db(tmp_path); _three(p)
    assert pe.append(p, 'pos', 'ws1', 'build', {'v': 1}, cat='c1', key=K, at=500) is None   # the same fact again, later
    assert len(pe.append_many(p, [{'kind': 'pos', 'ref': 'ws2', 'event': 'file'}] * 3, key=K)) == 1
    c = sqlite3.connect(p)   # an old row copied to the end with its own mac and a new id
    r = c.execute('SELECT * FROM events WHERE n = 2').fetchone()
    c.execute('INSERT INTO events VALUES (5, ?, ?, ?, ?, ?, ?, ?, ?, ?)', ('r' * 32, *r[2:]))
    c.commit(); c.close()
    v = pe.verify(p, key=K)
    assert v['ok'] is False and v['brokenAt'] == 5


def test_corrections_point_back_and_never_edit(tmp_path):
    p = _db(tmp_path); _three(p)
    pe.append(p, 'pos', 'ws1', 'grade', {'graded': 'right'}, key=K)
    fix = pe.correct(p, 4, 'the owner re-marked it', {'to': 'wrong'}, key=K)
    rows = pe.history(p, 'pos', 'ws1')
    assert fix['event'] == 'correction' and rows[3]['data'] == {'graded': 'right'} and rows[3]['correctedBy'] == [5]
    pe.append(p, 'pob', 'other', 'file', key=K)
    with pytest.raises(ValueError):
        pe.append(p, 'pob', 'other', 'correction', {'fixes': 4}, key=K)   # a row of another proof
    with pytest.raises(ValueError):
        pe.correct(p, 99, 'nothing there', key=K)
    assert pe.verify(p, key=K)['ok']


def test_two_writers_at_once_keep_one_unbroken_line(tmp_path):
    p = _db(tmp_path); pe.head(p); errs = []
    def writer(w):
        try:
            for i in range(40):
                pe.append(p, 'pow', f'w{w}', 'build', {'i': i}, key=K)   # each call opens its own connection, like 5088 and 5077
        except Exception as e:   # noqa: BLE001
            errs.append(e)
    ts = [threading.Thread(target=writer, args=(w,)) for w in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    v = pe.verify(p, key=K)
    assert not errs and v['ok'] and v['count'] == 160


def _store(**f):
    folder = {'id': 'pob1', 'status': 'closed', 'at': 1000, 'closedAt': 1000, **f}
    return {'cats': {'c1': {'pobFolders': [folder]}}}


def test_the_watcher_files_what_a_save_changed_once(tmp_path):
    p = _db(tmp_path); w = pe.Watcher(p, key=K)
    got = w.watch(pe.states(_store(), 2000), 2000)
    assert [r['event'] for r in got] == ['file'] and w.watch(pe.states(_store(), 2000), 2001) == []
    got = w.watch(pe.states(_store(graded='right', gradedBy='scoreboard'), 2000 + DAY), 2000 + DAY)
    assert [r['event'] for r in got] == ['grade', 'score', 'stamp']
    assert pe.history(p, 'pob', 'pob1')[1]['data'] == {'graded': 'right', 'by': 'scoreboard'}
    again = pe.Watcher(p, key=K)   # a restart: nothing filed twice
    assert again.watch(pe.states(_store(graded='right', gradedBy='scoreboard'), 2000 + DAY), 3000 + DAY) == []
    got = again.watch(pe.states(_store(graded='wrong', sent={'sig': 'abc', 'sol': 0.1, 'at': 5}), 2000 + DAY), 4000 + DAY)
    evs = [(r['event'], r['data'].get('event'), r['data'].get('to')) for r in got]
    assert evs[:3] == [('correction', 'grade', 'wrong'), ('correction', 'score', {'won': False}), ('correction', 'stamp', 'not')] and evs[3][0] == 'send'
    rows = pe.history(p, 'pob', 'pob1')
    assert rows[1]['correctedBy'] == [rows[4]['n']] and pe.verify(p, key=K)['ok']
    back = again.watch(pe.states(_store(graded='right', sent={'sig': 'abc', 'sol': 0.1, 'at': 5}), 2000 + DAY), 5000 + DAY)
    assert [r['data']['fixes'] for r in back][0] == rows[4]['n']   # a flip back corrects the correction, the first row stays


def test_many_pages_from_one_workspace_stay_apart_and_quiet(tmp_path):
    p = _db(tmp_path); w = pe.Watcher(p, key=K)
    pages = [{'id': f'ps{i}', 'ws': 'wsA', 'status': 'closed', 'at': 10, 'graded': g} for i, g in enumerate(('right', 'wrong', None))]
    st = {'cats': {'c1': {'psFolders': pages}}}
    got = w.watch(pe.states(st, 10 + DAY), 10 + DAY)
    assert {r['ref'] for r in got} == {'ps0', 'ps1', 'ps2'} and not [r for r in got if r['event'] == 'correction']
    assert w.watch(pe.states(st, 10 + DAY), 20 + DAY) == [] and pe.Watcher(p, key=K).watch(pe.states(st, 10 + DAY), 30 + DAY) == []   # found by the real-store dry run


def test_the_watcher_reads_builds_and_open_pow_runs(tmp_path):
    p = _db(tmp_path); w = pe.Watcher(p, key=K)
    doc = {'id': 'ws9', 'kind': 'build', 'stage': 'approve', 'plan': {'at': 50, 'by': 'OSSY', 'approved': False}, 'versions': []}
    assert [r['event'] for r in w.watch([pe.ws_state('c1', doc)], 60)] == ['plan']
    doc.update(stage='review', versions=[{'html': '<p>', 'by': 'G4', 'at': 70}]); doc['plan']['approved'] = True
    assert [r['event'] for r in w.watch([pe.ws_state('c1', doc)], 80)] == ['plan', 'review', 'build']   # approving is its own plan row
    assert pe.ws_state('c1', {'id': 'x', 'kind': 'chat'}) is None
    run = {'cats': {'c1': {'powRun': {'folder': {'id': 'pow7', 'phase': 'research'}}}}}
    assert [r['event'] for r in w.watch(pe.states(run, 90), 90)] == ['plan', 'build']
    run['cats']['c1']['powRun']['folder']['phase'] = 'sell'
    got = w.watch(pe.states(run, 95), 95)
    assert [(r['event'], r['data']['phase']) for r in got] == [('build', 'sell')]


def test_a_service_save_files_events_and_a_broken_file_never_stops_it(tmp_path, monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(pe, '_key', lambda: K)
    store = fs._load(); store.setdefault('cats', {})['evCat'] = {'id': 'evCat', 'pocFolders': [{'id': 'poc1', 'ws': 'wsP', 'status': 'closed', 'at': 1}]}
    fs._save(store)
    path = fs.DATA_DIR / pe.DB_NAME
    first = pe.history(path, 'poc', 'poc1')[0]
    assert (first['event'], first['data']['ws']) == ('file', 'wsP') and pe.verify(path, key=K)['ok']
    fs._PEV_W.clear(); path.unlink(); path.mkdir()   # the event file turned into a folder: unreadable
    store['cats']['evCat']['pocFolders'][0]['graded'] = 'right'
    fs._save(store)   # still saves
    assert fs._load()['cats']['evCat']['pocFolders'][0]['graded'] == 'right'

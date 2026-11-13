"""🧪 The test bench ledger: every test on a desk is filed and readable; nothing outside a run's folder can be read."""
import test_bench as tb


def test_file_and_read_runs(tmp_path):
    r1 = tb.file_run(tmp_path, 'cat-1', kind='3d', title='NOVA on G4', ok=False, why='Looped on shader lines and hit its length cap', models=['local/g4'], cost_usd=0, secs=412, files={'g4 reply.js': 'const x = 1;'}, now=100)
    r2 = tb.file_run(tmp_path, 'cat-1', kind='3d', title='NOVA after the fix', ok=True, why='Opened, 61 FPS', now=200)
    rows = tb.runs(tmp_path, 'cat-1')
    assert [r['id'] for r in rows] == [r2['id'], r1['id']]
    assert rows[1]['files'] == [{'name': 'g4-reply.js', 'bytes': 12}]
    assert tb.read_file(tmp_path, 'cat-1', r1['id'], 'g4-reply.js') == 'const x = 1;'
    assert tb.stats(rows) == {'runs': 2, 'passed': 1, 'failed': 1, 'costUsd': 0.0, 'secs': 412.0}
    assert tb.runs(tmp_path, 'someone-else') == []


def test_torn_line_and_path_tricks(tmp_path):
    r = tb.file_run(tmp_path, 'c', kind='ui', title='t', ok=True, why='', files={'a.txt': 'hi'})
    with (tmp_path / 'test_runs' / 'c' / 'runs.jsonl').open('a') as fh:
        fh.write('{"id": "half')
    assert len(tb.runs(tmp_path, 'c')) == 1
    assert tb.read_file(tmp_path, 'c', r['id'], '../runs.jsonl') is None
    assert tb.read_file(tmp_path, 'c', '../../x', 'a.txt') is None
    try:
        tb.file_run(tmp_path, 'c', kind='ui', title=' ', ok=True, why='')
        raise AssertionError('a blank title must be refused')
    except ValueError:
        pass

"""🗂 AGX-2 (owner 2026-11-14): the desk's proof drawer — a grade carries its why, and any two saved versions of a page can be set side by side."""
from test_play_studio import _server


def _build_with_versions(fs, store):
    cat = store['cats']['g']
    row = fs._feat.new_folder(cat, 'build', 'Shop', 1.0)
    doc = fs._feat.new_doc(row)
    doc['versions'] = [{'html': '<html><body><h1>one</h1></body></html>', 'by': 'MIND A', 'at': 10},
                       {'html': '<html><body>\n<h1>two</h1>\n<p>more</p>\n</body></html>', 'by': 'MIND B', 'at': 20}]
    fs._ws_save('g', doc)
    f = fs._feat.file_static(cat, doc, 'MIND B', 20.0)
    return row, f


def test_grade_keeps_its_why_and_a_blank_why_clears_it(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    row, f = _build_with_versions(fs, store)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    j = post('ps_mark', job=f['id'], text='wrong', tools={'why': '  the  buy button   does nothing  '})
    assert j.status_code == 200, j.text
    got = next(x for x in j.json()['psFolders'] if x['id'] == f['id'])
    assert got['graded'] == 'wrong' and got['gradeWhy'] == 'the buy button does nothing'
    j = post('ps_mark', job=f['id'], text='right')   # no why sent: the old one stays
    assert next(x for x in j.json()['psFolders'] if x['id'] == f['id'])['gradeWhy'] == 'the buy button does nothing'
    j = post('ps_mark', job=f['id'], text='right', tools={'why': ''})   # an empty why clears it
    assert 'gradeWhy' not in next(x for x in j.json()['psFolders'] if x['id'] == f['id'])
    assert post('ps_mark', job=f['id'], text='maybe').status_code == 400


def test_any_saved_version_opens_for_compare_and_bad_ones_are_refused(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    row, _ = _build_with_versions(fs, store)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    j = post('ws_version', text=row['id'], i=1)
    assert j.status_code == 200, j.text
    v = j.json()['version']
    assert v['i'] == 1 and v['of'] == 2 and v['by'] == 'MIND A' and '<h1>one</h1>' in v['html'] and v['preview'] and v['lines'] == 1
    assert post('ws_version', text=row['id'], i=2).json()['version']['lines'] == 4
    assert post('ws_version', text=row['id'], i=3).status_code == 400
    assert post('ws_version', text=row['id'], i=0).status_code == 400
    assert post('ws_version', text='wnope', i=1).status_code == 404
    assert c.post('/api/cats/g/work', json={'ownerId': 'x', 'session': 'x', 'op': 'ws_version', 'text': row['id'], 'i': 1}).status_code in (401, 403)   # owner only

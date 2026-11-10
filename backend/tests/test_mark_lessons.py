"""COL-14: the owner's notes on marked parts of a page reach its PoStatic, and notes on pages he marked working teach every agent's next page."""
import agent_features as af


def test_notes_are_kept_filed_and_taught_only_when_the_page_worked():
    import feecat_service as fs
    doc = {'id': 'w', 'name': 'GONE', 'versions': [{}]}
    fs._keep_mark_notes(doc, [{'note': 'make the hero text bigger'}, {'note': ''}, {'sx': 1}])
    fs._keep_mark_notes(doc, {'note': 'the button was under the footer'})
    assert [n['note'] for n in doc['markNotes']] == ['make the hero text bigger', 'the button was under the footer']
    row = af.file_static({}, doc, 'Mind A', 1)
    assert [n['note'] for n in row['markNotes']] == ['make the hero text bigger', 'the button was under the footer']
    store = {'cats': {'a': {'psFolders': [{**row, 'graded': 'right', 'at': 5}, {'markNotes': [{'note': 'never this'}], 'graded': 'wrong', 'at': 9}]},
                      'b': {'psFolders': [{'markNotes': [{'note': 'Make the hero text bigger'}], 'graded': 'right', 'at': 7}]}}}
    line = fs._mark_lessons(store, now=100)
    assert 'make the hero text bigger' in line.lower() and 'button was under the footer' in line and 'never this' not in line
    assert line.lower().count('make the hero text bigger') == 1   # the same lesson once, whoever gave it
    assert fs._mark_lessons({'cats': {}}, now=200) == ''

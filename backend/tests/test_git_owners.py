"""Owner 2026-11-06: nobody cleans another member's files. They get told, and what happens next is their own setting."""
import json

import agent_features as af
import collective_sort as cs


FILES = {'index.json': json.dumps([{'path': 'proofs/a.json', 'agent': 'mine'}, {'path': 'proofs/b.json', 'agent': 'them'}, {'path': 'proofs/c.json', 'agent': 'them'}]).encode()}


def test_the_record_says_whose_file_it_is():
    who = cs.owners(FILES)
    assert who['proofs/b.json'] == 'them' and cs.theirs(['proofs/a.json', 'proofs/b.json', 'README.md'], who, {'mine'}) == ['proofs/b.json']
    assert cs.owners({}) == {} and cs.owners({'index.json': b'not json'}) == {}


def test_only_their_flagged_files_oldest_first_and_kept_ones_never():
    who = cs.owners(FILES); items = {'proofs/b.json': {'status': 'alert', 'at': 9}, 'proofs/c.json': {'status': 'trash_ask', 'at': 3}, 'proofs/a.json': {'status': 'alert', 'at': 1}}
    assert cs.flagged(items, who, 'them') == ['proofs/c.json', 'proofs/b.json']
    items['proofs/c.json']['kept'] = True
    assert cs.flagged(items, who, 'them') == ['proofs/b.json']


def test_their_setting_decides():
    assert cs.clean_view({}) == {'auto': True, 'days': 30}
    cat = {'gitNotice': {'at': 0}, 'gitClean': {'auto': True, 'days': 7}}
    assert not cs.clean_due(cat, 6 * 86400) and cs.clean_due(cat, 7 * 86400)
    assert not cs.clean_due({**cat, 'gitClean': {'auto': False, 'days': 7}}, 99 * 86400) and not cs.clean_due({}, 99 * 86400)


def test_a_mark_keeps_the_scroll_it_was_drawn_at():
    item = cs.owner_set({}, {'marks': [{'x': .1, 'y': .1, 'w': .2, 'h': .2, 'sy': 640}, {'x': .1, 'y': .1, 'w': .2, 'h': .2}]})
    assert item['marks'][0]['sy'] == 640 and 'sy' not in item['marks'][1]


def test_a_page_reports_its_scroll_and_finds_a_quote():
    page = af.preview('<!doctype html><html><head></head><body>hi</body></html>')
    assert 'feeless-scroll' in page and 'feeless-find' in page and 'feeless-picked' in page

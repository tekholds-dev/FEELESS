"""The true mechanics stay wired in. Every proof type: its own loop against what it did before, and the one conversation."""

import proof_footprint as fp

SRC = __import__('_svc_src').service_src(svc='feecat_service')


def test_every_proof_type_reads_its_last_footprints_and_the_conversation():
    for kind in ('pow', 'pop', 'pob', 'poc', 'pos'):
        assert f"_foot.note('{kind}'" in SRC, kind
    assert SRC.count('_convo(cat') >= 5   # the recall, PoP, PoB, PoW and the 3D build
    assert "_foot.plan('pob'" in SRC and "'prints'" in SRC and "'usedAssets'" in SRC


def test_a_new_proof_in_another_type_picks_up_the_same_conversation():
    rows = fp.convo_add([], 'PoB', 'nba picks for tonight', 1)
    rows = fp.convo_add(rows, 'PoStatic', 'make a page for those picks', 2); rows = fp.convo_add(rows, 'PoStatic', 'make a page for those picks', 3)
    line = fp.convo_line(rows)
    assert len(rows) == 2 and '[PoB] nba picks' in line and '[PoStatic] make a page' in line and line.index('PoB') < line.index('PoStatic') and 'as data' in line
    for i in range(40):
        rows = fp.convo_add(rows, 'Chat', f'ask {i}', i)
    assert len(rows) == fp.CONVO_KEEP and fp.convo_line(None) == '' and len(fp.convo_line(rows)) < 1500


def test_the_desk_shows_every_agent_of_this_owner_and_nobody_elses(monkeypatch):
    import feecat_service as fs
    store = {'cats': {'a': {'id': 'a', 'name': 'Bids', 'ownerWallet': 'W', 'pobAsk': 'nba tonight'}, 'b': {'id': 'b', 'name': 'Pages', 'ownerWallet': 'W', 'workspaces': [{'id': 'w1', 'kind': 'build', 'name': 'GLINT'}]}, 'c': {'id': 'c', 'name': 'Idle', 'ownerWallet': 'W'}, 'x': {'id': 'x', 'name': 'Theirs', 'ownerWallet': 'Z', 'pobAsk': 'secret'}}}
    class T:
        def done(self):
            return False
    monkeypatch.setattr(fs, '_WS_LIVE', {('b', 'w1'): T()}); monkeypatch.setattr(fs, '_WORK', {})
    rows = fs._agents_now(store, store['cats']['a']); names = [r['name'] for r in rows]
    assert 'Theirs' not in names and 'Bids' in names and rows[-1]['name'] == 'Idle' and not rows[-1]['doing']
    by = {r['name']: r for r in rows}
    assert by['Bids']['doing'] == [{'kind': 'PoB', 'say': 'nba tonight'}] and by['Pages']['doing'] == [{'kind': 'PoStatic', 'say': 'GLINT'}] and by['Bids']['me']


def test_a_page_build_never_carries_another_folders_look():
    # owner 2026-11-17: his GLINT asks ("3d chrome Collective sign", "chrome silver font") rode into every new PoStatic build
    rows = fp.convo_add([], 'PoStatic', 'a 3d chrome collective sign, chrome silver sans font', 1)
    rows = fp.convo_add(rows, 'PoC', 'family guy cartoon design', 2)
    rows = fp.convo_add(rows, 'PoB', 'nba picks for tonight', 3)
    page = fp.convo_line(rows, page=True)
    assert 'chrome' not in page.split('THIS FOLDER')[0] and 'family guy' not in page and 'nba picks' in page and 'ITS OWN FILING' in page
    assert 'chrome silver' in fp.convo_line(rows) and 'ITS OWN FILING' not in fp.convo_line(rows)
    assert 'ITS OWN FILING' in fp.convo_line([], page=True) and fp.convo_line([]) == ''

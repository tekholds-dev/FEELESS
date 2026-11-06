"""The Trash: 7 days, then gone for good. Only what the owner moved there, and a deleted proof never comes back."""
import collective_git as cg
import collective_sort as cs
import collective_stash as st

DAY = 86400


def test_moving_in_starts_the_clock_and_moving_out_stops_it():
    i = cs.owner_set({}, {'status': 'trash'}, 100.0); assert i['trashedAt'] == 100
    i = cs.owner_set(i, {'note': 'x'}, 500.0); assert i['trashedAt'] == 100   # a note never restarts it
    i = cs.owner_set(i, {'status': 'none'}, 600.0); assert 'trashedAt' not in i
    assert cs.rule_trash({}, True, 7.0)['trashedAt'] == 7 and 'trashedAt' not in cs.rule_trash({'trashedAt': 1}, False, 8.0)


def test_only_what_the_owner_moved_and_only_after_7_days_is_due():
    now = 100 * DAY
    items = {'old': {'status': 'trash', 'trashedAt': now - 7 * DAY}, 'new': {'status': 'trash', 'trashedAt': now - 6 * DAY}, 'asked': {'status': 'trash_ask', 'trashedAt': 1}, 'bad': {'status': 'bad'}, 'dir/': {'status': 'trash', 'trashedAt': 1}, 'legacy': {'status': 'trash'}}
    assert cs.trash_due(items, now) == ['old']
    assert items['legacy']['trashedAt'] == now   # old trash gets its full 7 days, never a surprise


def test_a_deleted_proof_is_gone_for_good_and_ingest_cannot_bring_it_back(tmp_path):
    assert st.put(tmp_path, 'k1', 'Trades', 'a.com', 'x', 'won', 'One', b'same bytes')
    assert st.put(tmp_path, 'k2', 'Trades', 'b.com', 'x', 'won', 'Two', b'same bytes')
    files = list(cg.collective_tree(tmp_path)[0]); paths = [p for p in files if p.startswith('proofs/')]; keys = cg.stash_keys(tmp_path, paths)
    assert sorted(keys.values()) == ['k1', 'k2']
    assert st.drop(tmp_path, 'k1') is True and st.read(tmp_path, 'k1') is None
    assert st.read(tmp_path, 'k2') == b'same bytes'   # shared bytes stay while another item uses them
    assert st.put(tmp_path, 'k1', 'Trades', 'a.com', 'x', 'won', 'One', b'same bytes') is False and st.read(tmp_path, 'k1') is None
    st.drop(tmp_path, 'k2'); assert not [p for p in (tmp_path / 'blobs').rglob('*') if p.is_file()]


def test_a_deleted_path_never_shows_again_and_built_files_cannot_be_blocked(tmp_path):
    d = cs.load(tmp_path); d['items'] = {'a.json': {'status': 'trash'}, 'README.md': {'status': 'trash'}}
    assert cs.forget(d, ['a.json', 'README.md'], 5.0) == ['a.json']; cs.save(tmp_path, d)
    assert cs.without_gone(tmp_path, {'a.json': b'1', 'README.md': b'2', 'b.json': b'3'}) == {'README.md': b'2', 'b.json': b'3'}
    assert cs.load(tmp_path)['items'] == {}


def test_the_hourly_pass_deletes_what_is_due_and_a_bad_file_stays(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'GIT_DIR', tmp_path / 'git'); monkeypatch.setattr(fs, 'STASH_DIR', tmp_path / 'st'); fs._SORT_PURGE_AT[0] = 0.0
    st.put(tmp_path / 'st', 'k', 'Trades', 'a.com', 'x', 'won', 'One', b'x'); st.put(tmp_path / 'st', 'k2', 'Trades', 'a.com', 'x', 'won', 'Two', b'y')
    paths = sorted(p for p in cg.collective_tree(tmp_path / 'st')[0] if p.startswith('proofs/')); now = 100 * DAY
    keys = cg.stash_keys(tmp_path / 'st', paths); old = next(p for p in paths if keys[p] == 'k'); keep = next(p for p in paths if keys[p] == 'k2')
    d = cs.load(tmp_path / 'git'); d['items'] = {old: {'status': 'trash', 'trashedAt': now - 8 * DAY}, keep: {'status': 'bad'}}; cs.save(tmp_path / 'git', d)
    fs._sort_purge(now)
    assert st.read(tmp_path / 'st', 'k') is None and st.read(tmp_path / 'st', 'k2') == b'y'
    after = cs.load(tmp_path / 'git'); assert old in after['gone'] and old not in after['items'] and keep in after['items']
    fs._sort_purge(now + 60)   # once an hour

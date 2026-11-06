"""🔐 Sealed, hashed, unchanged files stay unchanged, and it can be restored. No network."""
import collective_git as cg
import cat_keys as ck


def seal(raw):
    return ck.seal_bytes(raw, 'cat1')


def test_nothing_readable_reaches_the_repo_and_it_restores(tmp_path):
    files = {'proofs/PoB/won/2026-11/my-secret-topic-abc.json': b'{"topic":"my secret topic"}'}
    out, st = cg.vault_tree('tag1', files, seal, tmp_path)
    assert st['files'] == 1 and not st['left'] and all(p.startswith('vault/tag1/') for p in out)
    for path, blob in out.items():
        assert b'secret' not in blob and 'secret' not in path
    name = next(p for p in out if 'index' not in p)
    assert cg.vault_open(out[name], lambda b: ck.unseal_bytes(b, 'cat1')) == files['proofs/PoB/won/2026-11/my-secret-topic-abc.json']
    assert b'my-secret-topic' in cg.vault_open(out['vault/tag1/index.seal'], lambda b: ck.unseal_bytes(b, 'cat1'))


def test_an_unchanged_file_seals_the_same_so_it_is_never_pushed_twice(tmp_path):
    files = {'a.json': b'one', 'b.json': b'two'}
    first, _ = cg.vault_tree('t', files, seal, tmp_path); again, _ = cg.vault_tree('t', files, seal, tmp_path)
    assert first == again
    changed, _ = cg.vault_tree('t', {**files, 'a.json': b'ONE'}, seal, tmp_path)
    assert sum(first[k] != changed[k] for k in first if not k.endswith('index.seal')) == 1


def test_another_agents_key_cannot_open_it(tmp_path):
    import pytest
    out, _ = cg.vault_tree('t', {'a': b'x' * 50}, seal, tmp_path)
    with pytest.raises(Exception):
        cg.vault_open(next(iter(out.values())), lambda b: ck.unseal_bytes(b, 'other-cat'))


def test_over_its_share_the_rest_wait_and_say_so(tmp_path):
    import os
    out, st = cg.vault_tree('t', {f'{i}.bin': os.urandom(2000) for i in range(5)}, seal, tmp_path, cap=5000)
    assert st['left'] >= 1 and st['bytes'] <= 5000 and st['files'] + st['left'] == 5

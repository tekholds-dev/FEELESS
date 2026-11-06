import base64
import json

import collective_git as cg


def test_a_file_holding_a_secret_never_leaves_or_shows():
    clean, held = cg.without_leaks({'a.json': b'{"ok":1}', 'b.json': b'{"k":"sk-or-v1-abcdefghijklmnopqrstuvwxyz"}', 'c.html': b'<b>ghp_abcdefghijklmnopqrstuvwxyz</b>', 'd.json': b'{"mnemonic":"one two"}', 'e.webp': b'sk-or-v1-abcdefghijklmnopqrstuvwxyz'})
    assert sorted(clean) == ['a.json', 'e.webp'] and sorted(held) == ['b.json', 'c.html', 'd.json']


def test_the_collective_repo_gets_only_sealed_blobs_and_hashed_names(tmp_path):
    seal = lambda raw: b'SEALED' + base64.b64encode(raw)
    files = {'proofs/PoW/won/2026-11/secret-coin.json': b'{"sym":"TITLE"}', 'snapshots/rugcheck/a.webp': b'pic'}
    out, stats = cg.sealed_tree(files, seal, tmp_path)
    assert stats['files'] == 2
    for path, raw in out.items():
        assert b'TITLE' not in raw and 'secret-coin' not in path and 'rugcheck' not in path
        assert path == 'README.md' or (path.startswith('vault/collective/') and path.endswith('.seal') and raw.startswith(b'SEALED'))
    assert b'FEELESS' in out['README.md'] and b'PoW' not in out['README.md']


def test_a_saved_page_joins_only_its_own_tree():
    page = lambda ws: ('<html>mine</html>', 'My page') if ws == 'w1' else ('', '')
    mine = cg.agent_tree({'name': 'A', 'savedPages': ['w1']}, lambda f: f, page); other = cg.agent_tree({'name': 'B'}, lambda f: f, page)
    assert any(p.startswith('pages/my-page') for p in mine) and not any(p.startswith('pages/') for p in other)


def test_files_open_as_what_they_are():
    import feecat_service as fs
    img = fs._git_view_file('snapshots/x/a.webp', b'RIFF'); assert img['kind'] == 'image' and img['image'].startswith('data:image/webp;base64,')
    page = fs._git_view_file('pages/a.html', b'<!doctype html><html><body>hi</body></html>'); assert page['kind'] == 'page' and 'hi' in page['preview']
    data = fs._git_view_file('proofs/a.json', json.dumps({'sym': 'X'}).encode()); assert data['kind'] == 'data' and data['data']['sym'] == 'X'
    assert fs._git_view_file('vault/x.seal', b'zz')['kind'] == 'sealed' and 'image' not in fs._git_view_file('a.svg', b'<svg/>')

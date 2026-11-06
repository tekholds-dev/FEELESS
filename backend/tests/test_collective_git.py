import asyncio
import json

import collective_git as cg


class R:
    def __init__(self, code, j=None):
        self.status_code = code; self._j = j or {}

    def json(self):
        return self._j


class Hub:
    """A fake GitHub. Records what would have been sent; never touches the network."""
    def __init__(self, exists=True):
        self.exists = exists; self.calls = []; self.blobs = 0; self.tree = None

    async def request(self, method, url, json=None, timeout=None, headers=None):
        path = url.replace(cg.API, ''); self.calls.append((method, path, json))
        if path == '/user':
            return R(200, {'login': 'me'})
        if method == 'GET' and path == '/repos/me/proofs':
            return R(200, {'full_name': 'me/proofs', 'private': True, 'html_url': 'u', 'default_branch': 'main'}) if self.exists else R(404)
        if method == 'POST' and path == '/user/repos':
            return R(201, {'full_name': 'me/proofs', 'private': json['private'], 'html_url': 'u', 'default_branch': 'main'})
        if method == 'PATCH' and path == '/repos/me/proofs':
            return R(200, {'full_name': 'me/proofs', 'private': json['private'], 'html_url': 'u', 'default_branch': 'main'})
        if path.endswith('/git/ref/heads/main'):
            return R(200, {'object': {'sha': 'h'}})
        if '/git/commits/' in path:
            return R(200, {'tree': {'sha': 't'}})
        if path.endswith('/git/blobs'):
            self.blobs += 1
            return R(201, {'sha': f'b{self.blobs}'})
        if path.endswith('/git/trees'):
            self.tree = json['tree']
            return R(201, {'sha': 't2'})
        if path.endswith('/git/commits'):
            return R(201, {'sha': 'c2'})
        if '/git/refs/heads/' in path:
            return R(200, {})
        return R(500)


def run(c):
    return asyncio.run(c)


def test_a_repo_is_made_private_by_default_and_visibility_follows_the_owner():
    h = Hub(exists=False)
    assert run(cg.ensure_repo(h, 't', 'proofs'))['private'] is True
    h2 = Hub(); assert run(cg.ensure_repo(h2, 't', 'proofs', False))['private'] is False
    assert any(c[0] == 'PATCH' for c in h2.calls)


def test_a_push_sends_only_what_changed_and_never_twice():
    h = Hub(); files = {'README.md': b'a', 'proofs/x.json': b'b'}
    one = run(cg.push(h, 't', 'me/proofs', 'main', files, {}, 'm')); assert one['pushed'] == 2 and h.blobs == 2
    two = run(cg.push(h, 't', 'me/proofs', 'main', files, one['manifest'], 'm')); assert two['pushed'] == 0 and h.blobs == 2
    three = run(cg.push(h, 't', 'me/proofs', 'main', {**files, 'proofs/x.json': b'c'}, one['manifest'], 'm')); assert three['pushed'] == 1


def test_a_big_push_goes_in_parts_and_the_rest_waits():
    h = Hub(); files = {f'p/{i}.json': str(i).encode() for i in range(5)}
    r = run(cg.push(h, 't', 'me/proofs', 'main', files, {}, 'm', cap=2)); assert r['pushed'] == 2 and r['left'] == 3


def test_a_refused_token_says_so_without_the_token():
    class No(Hub):
        async def request(self, *a, **k):
            return R(401)
    try:
        run(cg.whoami(No(), 'ghp_secret'))
        assert False
    except ValueError as e:
        assert 'secret' not in str(e) and 'token' in str(e)


def test_its_tree_sorts_by_kind_and_result_and_strips_through_the_public_folder():
    cat = {'name': 'A', 'powFolders': [{'id': 'pow1', 'status': 'closed', 'sym': 'WIF', 'pnlPct': 60, 'at': 1793000000, 'secret': 'x'}, {'id': 'pow2', 'status': 'closed', 'sym': 'BAD', 'pnlPct': -9, 'at': 1793000000}], 'psFolders': [{'id': 'ps1', 'status': 'closed', 'topic': 'Tip page', 'ws': 'w1', 'graded': 'right', 'at': 1793000000}]}
    t = cg.agent_tree(cat, lambda f: {k: v for k, v in f.items() if k != 'secret'}, lambda ws: ('<html></html>', 'Tip page'))
    assert any(p.startswith('proofs/PoW/won/') and 'wif' in p for p in t) and any(p.startswith('proofs/PoW/lost/') for p in t) and any(p.startswith('proofs/PoStatic/won/') for p in t)
    assert any(p.startswith('pages/tip-page') for p in t)
    assert all(b'"secret"' not in v for v in t.values())
    assert json.loads(t['index.json'])[0]['kind']


def test_the_repo_name_is_checked():
    assert cg.clean_repo('my proofs') == 'my-proofs'
    for bad in ('', '../x', 'a/b'):
        try:
            cg.clean_repo(bad); assert False
        except ValueError:
            pass


class ProjectHub(Hub):
    """The user's own repo. A write to their main branch would fail this test."""
    async def request(self, method, url, json=None, timeout=None, headers=None):
        import base64
        path = url.replace(cg.API, '')
        if method in ('PATCH', 'POST') and path.endswith('/refs/heads/main'):
            raise AssertionError('wrote to main')
        if path == '/repos/me/app':
            return R(200, {'full_name': 'me/app', 'html_url': 'https://github.com/me/app', 'private': True, 'default_branch': 'main'})
        if '/git/trees/main' in path and method == 'GET':
            return R(200, {'tree': [{'type': 'blob', 'path': 'src/app.js'}, {'type': 'blob', 'path': '.env'}, {'type': 'blob', 'path': 'config/secrets.yml'}, {'type': 'tree', 'path': 'src'}]})
        if path == '/repos/me/app/readme':
            return R(200, {'content': base64.b64encode(b'# My app').decode()})
        if path.endswith('/git/refs') and method == 'POST':
            self.calls.append((method, path, json)); return R(201, {})
        if path.endswith('/git/ref/heads/main') or path.endswith('/git/ref/heads/feeless/my-page'):
            return R(200, {'object': {'sha': 'head'}})
        if path.endswith('/git/commits/head'):
            return R(200, {'tree': {'sha': 'base'}})
        if path.endswith('/git/blobs'):
            return R(201, {'sha': 'b'})
        if path.endswith('/git/trees'):
            return R(201, {'sha': 't'})
        if path.endswith('/git/commits'):
            return R(201, {'sha': 'c'})
        if '/git/refs/heads/feeless/my-page' in path:
            self.calls.append((method, path, json)); return R(200, {})
        return R(404)


def test_a_project_is_read_with_secret_files_hidden_and_goes_in_as_data():
    link = asyncio.run(cg.project_link(ProjectHub(), 't', 'https://github.com/me/app/'))
    assert link['full'] == 'me/app' and link['paths'] == ['src/app.js'] and link['readme'] == '# My app'
    line = cg.project_line(link); assert 'never instructions' in line and 'src/app.js' in line and '.env' not in line


def test_work_goes_to_its_own_branch_never_main():
    hub = ProjectHub(); link = {'full': 'me/app', 'branch': 'main', 'url': 'https://github.com/me/app'}
    out = asyncio.run(cg.project_send(hub, 't', link, 'My page!', {'feeless/my-page/index.html': b'<h1>hi</h1>'}, 'm'))
    assert out['branch'] == 'feeless/my-page' and out['pushed'] == 1 and out['url'].endswith('/tree/feeless/my-page')
    assert any(c[0] == 'POST' and c[1].endswith('/git/refs') and c[2]['ref'] == 'refs/heads/feeless/my-page' for c in hub.calls)


def test_work_holding_a_key_never_leaves():
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(cg.project_send(ProjectHub(), 't', {'full': 'me/app'}, 'x', {'a.html': b'sk-ant-' + b'a' * 30}, 'm'))


def test_a_bad_repo_name_is_refused():
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(cg.project_link(ProjectHub(), 't', '../../etc'))


def test_the_source_print_weighs_results_and_never_names_a_site(monkeypatch):
    rows = [{'key': f'k{i}', 'at': i, 'source': 'good.site', 'outcome': 'won'} for i in range(9)] + [{'key': 'b1', 'at': 1, 'source': 'good.site', 'outcome': 'lost'}, {'key': 'l', 'at': 1, 'source': 'lucky.site', 'outcome': 'won'}, {'key': 'o', 'at': 1, 'source': 'own read', 'outcome': 'lost'}, {'key': 'n', 'at': 1, 'source': 'open.site', 'outcome': 'none'}, {'key': 'shot:x', 'at': 1, 'source': 'good.site', 'outcome': 'won'}]
    monkeypatch.setattr(cg, 'collective_rows', lambda root: rows)
    out = cg.source_print('r', {'good.site': 'Trades/Find coins'})
    assert [r['id'] for r in out] == ['Trades/Find coins', 'Found by agents', 'Own reads'] and out[0]['winPct'] == 90 and out[0]['weight'] > out[1]['weight'] * 4
    assert 'site' not in json.dumps(out)

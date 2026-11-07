import json

import asset_packs as ap
import collective_kits as ck


def _index(tmp_path):
    (tmp_path / ap.INDEX).write_text(json.dumps({'at': 9e12, 'rows': {'model': [{'id': 'pool_chair', 'name': 'Old chair', 'tags': ['chair'], 'pop': 5}], 'hdri': [], 'texture': []}}))
    url = 'https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-000/'
    (tmp_path / ap.MORE).write_text(json.dumps({'rows': [{'id': 'ox-1', 'name': 'Throne chair', 'tags': ['chair'], 'pop': 90, 'url': url + 'a.glb', 'lic': 'by', 'by': 'Ana', 'faces': 900}, {'id': 'ox-2', 'name': 'Space Rocket', 'tags': ['rocket', 'space'], 'pop': 3, 'url': url + 'b.glb', 'lic': 'cc0', 'by': 'Bo', 'faces': 900}]}))


def test_the_big_index_is_searched_and_used_assets_come_last(tmp_path):
    _index(tmp_path); ap._MORE.update(mtime=0.0)
    assert ap.model_count(tmp_path) == 3 and ap.best(tmp_path, 'a rocket', 'model')['id'] == 'ox-2'
    first = ap.best(tmp_path, 'chair', 'model')['id']; second = ap.best(tmp_path, 'chair', 'model', avoid=[first])['id']
    assert first != second and ap.best(tmp_path, 'chair', 'model', avoid=[first, second])['id'] in (first, second)
    assert ap.best(tmp_path, 'a submarine', 'model') is None   # nothing is ever swapped for something else


def test_a_cc_by_creator_is_credited_and_only_safe_hosts_pass():
    a = ap.clean_asset({'id': 'ox-1', 'name': 'Throne', 'url': 'https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-000/a.glb', 'lic': 'by', 'by': 'Ana'})
    assert a['by'] == 'Ana' and ap.credits([{'objects': [{'asset': a}]}]) == 'Throne by Ana (CC BY)'
    assert ap.clean_asset({'id': 'x', 'url': 'https://evil.example/a.glb'}) is None
    assert ap.credits([{'objects': [{'asset': {'lic': None, 'name': 'x'}}]}]) == ''


def test_the_stash_steps_in_with_other_kits(tmp_path, monkeypatch):
    rows = [{'id': 'a', 'name': 'Picked', 'what': 'x', 'kinds': ['pos'], 'text': ''}, {'id': 'b', 'name': 'Other', 'what': 'y', 'kinds': ['pos'], 'text': ''}]
    monkeypatch.setattr(ck, 'all_rows', lambda root: rows)
    line, names = ck.stash_line(tmp_path, 'pos', 'anything', ['a'])
    assert names == ['Other'] and 'Other: y' in line and 'Picked' not in line and 'say which' in line


def test_a_failed_registry_read_never_loses_what_it_gave_before(tmp_path, monkeypatch):
    import asyncio
    (tmp_path / ap.INDEX).write_text(json.dumps({'at': 1, 'rows': {'model': [{'id': 'cc0-a', 'name': 'A', 'tags': [], 'pop': 0, 'url': 'https://raw.githubusercontent.com/ToxSam/a.glb'}]}}))
    class R:
        status_code = 200
        def json(self):
            return {'p1': {'name': 'P', 'tags': [], 'categories': [], 'download_count': 1}}
    class H:
        async def get(self, *a, **k):
            return R()
    async def none(_):
        return []
    monkeypatch.setattr(ap, '_registry', none); monkeypatch.setattr(ap, '_nasa', none)
    asyncio.run(ap.refresh(H(), tmp_path, now=5))
    ids = {r['id'] for r in ap._load(tmp_path, ap.INDEX)['rows']['model']}
    assert ids == {'p1', 'cc0-a'}

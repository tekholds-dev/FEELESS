"""🍴 Stash forks (owner 2026-11-10): an agent's own v1.01 of a stash build, in its git folder, offered back; Fee's desk sees every fork, never whose."""
import asyncio
import types

import pytest

import stash_forks as sf

PAGE = '<!doctype html><html><body><h1>Pulse</h1>\n<p>one</p>\n</body></html>'


def test_versions_count_up_and_track_what_changed(tmp_path):
    assert (sf.next_v('1.00'), sf.next_v('1.09'), sf.next_v('1.99')) == ('1.01', '1.10', '2.00')
    d = {'forks': {}}
    f = sf.make(d, tmp_path, 'cat1', 'b1', 'Pulse', PAGE, 100)
    assert f['versions'][0]['v'] == '1.00' and sf.read_html(tmp_path, f['id'], '1.00') == PAGE
    assert sf.make(d, tmp_path, 'cat1', 'b1', 'Pulse', PAGE)['id'] == f['id']   # the same build twice opens the same fork
    row = sf.add_version(d, tmp_path, f['id'], PAGE.replace('<p>one</p>', '<p>two</p>\n<p>three</p>'), 'darker', 'm', 0.012, 200)
    assert row['v'] == '1.01' and (row['added'], row['removed']) == (2, 1) and row['usd'] == 0.012
    with pytest.raises(ValueError):
        sf.add_version(d, tmp_path, f['id'], PAGE.replace('<p>one</p>', '<p>two</p>\n<p>three</p>'), 'again', 'm')   # nothing new, nothing added
    with pytest.raises(ValueError):
        sf.offer(d, f['id'], 'cat1', '1.00')   # v1.00 is the stash's own copy
    with pytest.raises(ValueError):
        sf.offer(d, f['id'], 'someone-else')
    sf.offer(d, f['id'], 'cat1', None, 300)
    assert f['offered']['v'] == '1.01'


def test_git_trees_and_the_board_never_say_whose(tmp_path):
    d = {'forks': {}}
    f = sf.make(d, tmp_path, 'cat1', 'b1', 'Pulse Dash', PAGE, 100); sf.add_version(d, tmp_path, f['id'], PAGE + '<!-- v2 -->', 'bigger', 'm', 0, 200)
    g = sf.make(d, tmp_path, 'cat2', 'b1', 'Pulse Dash', PAGE, 150)
    mine = sf.tree(d, tmp_path, 'cat1')
    assert sorted(k.rsplit('/', 1)[1] for k in mine) == ['FORK.md', 'v1.00.html', 'v1.01.html'] and all(k.startswith('forks/pulse-dash-') for k in mine)
    assert sf.collective_tree(d, tmp_path) == {}   # nothing offered: the Collective sees nothing yet
    sf.offer(d, f['id'], 'cat1', None, 300)
    col = sf.collective_tree(d, tmp_path)
    assert len(col) == 2 and all('cat1' not in k for k in col) and any(k.endswith('/v1.01.html') for k in col)
    b = sf.board(d)
    assert b[0]['id'] == f['id'] and all('cat' not in r for r in b) and b[0]['agent'] == sf.agent_tag('cat1') != sf.agent_tag('cat2')
    sf.take(d, f['id'], 400)
    with pytest.raises(ValueError):
        sf.drop(d, tmp_path, f['id'], 'cat1')   # the stash took it: it stays
    sf.drop(d, tmp_path, g['id'], 'cat2')
    assert g['id'] not in d['forks'] and sf.counts(d) == {'forks': 1, 'agents': 1, 'versions': 2, 'offered': 0, 'taken': 1}


def test_a_brain_answer_is_cut_down_to_the_page():
    assert sf.clean_html('Sure!\n```html\n<!doctype html><html><body>x</body></html>\n```\nEnjoy') == '<!doctype html><html><body>x</body></html>'
    assert sf.clean_html('<think>hmm</think>no page here') == ''


def test_fork_ops_price_first_then_tune_into_v101(tmp_path, monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    store = {'cats': {}}
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setattr(fs, '_popular_builds', lambda st, raw=False: [{'id': 'b1', 'cat': 'src', 'ws': 'w1', 'name': 'Pulse', 'kits': [], 'works': True, 'at': 1}])
    monkeypatch.setattr(fs, '_ws_load', lambda c, w: {'versions': [{'html': PAGE}]})
    monkeypatch.setattr(fs, '_ws_placed', lambda c, h: h)

    async def models():
        return {'models': [{'id': 'x/coder', 'inUsd': 1.0, 'outUsd': 4.0}]}
    monkeypatch.setattr(fs, '_or_models', models)
    asked = []

    async def ask(cat, model, sys_, user_, tokens):
        asked.append((model, tokens)); return '```html\n' + PAGE.replace('Pulse', 'Pulse Night') + '\n```', 0.0021, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    cat = {'id': 'cat1', 'brainsCfg': {'brains': ['x/coder']}}
    run = lambda **k: asyncio.run(fs._fork_op(cat, types.SimpleNamespace(**{'session': '', 'text': None, 'job': None, **k})))
    j = run(op='fork_list')
    assert j['forks'] == [] and j['sources'][0]['id'] == 'b1'
    j = run(op='fork_make', job='b1')
    fid = j['forks'][0]['id']
    assert j['forks'][0]['v'] == '1.00' and j['prices'][fid] > 0 and j['price']['model'] == 'x/coder'   # its price shows before it runs
    j = run(op='fork_tune', job=fid, text='make it a night theme')
    assert j['forks'][0]['v'] == '1.01' and j['forks'][0]['spentUsd'] == 0.0021 and asked[0][0] == 'x/coder'
    assert 'Pulse Night' in run(op='fork_open', job=fid, text='1.01')['preview']
    with pytest.raises(fs.HTTPException):
        run(op='fork_board')   # only Fee's owner sees every fork
    assert run(op='fork_offer', job=fid)['forks'][0]['offered']['v'] == '1.01'
    files, _ = fs._git_files({**cat, 'name': 'A'}, False)
    assert any(k.startswith('forks/pulse-') and k.endswith('v1.01.html') for k in files)

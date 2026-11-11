"""🎨 A General agent makes pictures and pages: paid from its own budget at the real cost, filed in its storage, never run on this origin."""
import asyncio
import base64
import agent_commands as ac

PNG = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'0' * 40).decode()
PAGE = '```html\n<!doctype html><html><body>hi</body></html>\n```'


def test_only_command_words_make_something():
    assert ac.make_job('make an image of a green cat') == {'kind': 'image', 'prompt': 'a green cat'}
    assert ac.make_job('/image a cat')['kind'] == 'image'
    assert ac.make_job('draw a logo for my coin') == {'kind': 'image', 'prompt': 'my coin'}
    assert ac.make_job('build a page for my shop') == {'kind': 'page', 'prompt': 'my shop'}
    assert ac.make_job('make me a landing page with a signup') == {'kind': 'page', 'prompt': 'a signup'}
    for t in ('what does this image show', 'read the page about SOL', 'check $BONK', ''):
        assert ac.make_job(t) is None


def test_a_cut_off_page_is_never_filed_as_finished():
    assert 'hi' in ac.page_in(PAGE)
    assert ac.page_in('<html><body>x</body></html>') is not None
    assert ac.page_in('```html\n<html><body>cut') is None
    assert ac.page_in('sorry, no') is None


def test_each_kind_is_offered_its_own_work():
    gen = [c[0] for c in ac.commands_for('general', [('file a perp', 'x')])]
    assert 'make an image of ' not in gen and 'build a page ' in gen and 'file a perp' not in gen and 'watch a wallet' not in gen and 'trench' in gen
    trade = [c[0] for c in ac.commands_for('trading', [('file a perp', 'x')])]
    assert 'file a perp' in trade and 'watch a wallet' in trade and 'make an image of ' not in trade


def _cat(credit=5.0):
    return {'id': 'c1', 'chat': [], 'brainsCfg': {'brains': ['a/one'], 'credit': credit, 'kind': 'general'}}


def test_it_refuses_with_no_budget_or_while_busy(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_work_live', lambda *_a: True); fs._MADE_BUSY.clear()
    assert fs._made_refusal(_cat(), {'kind': 'image', 'prompt': 'a cat'}) == ''
    assert 'too low' in fs._made_refusal(_cat(fs._lc.CREDIT_RESERVE + .01), {'kind': 'image', 'prompt': 'a cat'})
    fs._MADE_BUSY.add('c1')
    assert 'still making' in fs._made_refusal(_cat(), {'kind': 'image', 'prompt': 'a cat'})
    fs._MADE_BUSY.clear()
    monkeypatch.setattr(fs, '_work_live', lambda *_a: False)
    assert 'off' in fs._made_refusal(_cat(), {'kind': 'page', 'prompt': 'a shop'})


def test_a_picture_is_charged_its_real_cost_and_filed(monkeypatch):
    import feecat_service as fs
    fs._MADE_DONE.clear(); cat = _cat(); store = {'cats': {'c1': cat}}
    fs._MADE_DONE.append({'cat': 'c1', 'job': {'kind': 'image', 'prompt': 'a cat'}, 'usd': 0.04, 'why': '', 'own': False, 'url': PNG})
    fs._made_pass(store)
    assert round(cat['brainsCfg']['credit'], 2) == 4.96 and cat['files'][0]['ext'] == 'png' and cat['chat'][-1]['img'].endswith('.png') and cat['feesDue']


def test_a_failed_make_says_so_and_files_nothing(monkeypatch):
    import feecat_service as fs
    fs._MADE_DONE.clear(); cat = _cat(); store = {'cats': {'c1': cat}}
    fs._MADE_DONE.append({'cat': 'c1', 'job': {'kind': 'page', 'prompt': 'a shop'}, 'usd': 0.01, 'why': 'the model did not finish a whole page', 'own': False})
    fs._made_pass(store)
    assert 'Not made' in cat['chat'][-1]['text'] and not cat.get('files') and not cat.get('feesDue') and round(cat['brainsCfg']['credit'], 2) == 4.99


def test_a_built_page_is_served_so_it_cannot_run_here(monkeypatch):
    import feecat_service as fs
    fs._MADE_DONE.clear(); cat = _cat(); store = {'cats': {'c1': cat}}
    fs._MADE_DONE.append({'cat': 'c1', 'job': {'kind': 'page', 'prompt': 'a shop'}, 'usd': 0.01, 'why': '', 'own': False, 'html': '<html><body>hi</body></html>'})
    fs._made_pass(store)
    fid = cat['files'][0]['id']
    monkeypatch.setattr(fs, '_load', lambda: store)
    r = asyncio.run(fs.cat_file_get('c1', f'{fid}.html'))
    assert r.headers['content-security-policy'] == 'sandbox' and r.headers['content-disposition'] == 'attachment' and b'hi' in r.body


PROJECT_REPLY = """=== FILE: index.html ===
<!doctype html><html><head><link rel="stylesheet" href="css/style.css"></head><body><button id=b>0</button><script src="./js/app.js"></script></body></html>
=== FILE: css/style.css ===
button{color:red}
=== FILE: js/app.js ===
b.onclick=()=>b.textContent=+b.textContent+1;var x="</script>";
=== END ===
"""


def test_project_words_and_its_files():
    assert ac.make_job('build a project counter app')['kind'] == 'project' and ac.make_job('build a page counter')['kind'] == 'page'
    assert ac.make_job('what is a project')is None
    files = ac.project_in(PROJECT_REPLY)
    assert sorted(files) == ['css/style.css', 'index.html', 'js/app.js']
    html = ac.project_preview(files)
    assert 'button{color:red}' in html and 'b.onclick' in html and 'href="css' not in html and 'src=' not in html
    assert html.count('</script>') == 1   # a script's own closing text cannot end the block early


def test_a_cut_off_or_climbing_project_is_never_filed():
    assert ac.project_in(PROJECT_REPLY.replace('=== END ===', '')) is None
    assert ac.project_in(PROJECT_REPLY.replace('css/style.css', '../../secrets.css')) is None
    assert ac.project_in(PROJECT_REPLY.replace('js/app.js', 'run.sh')) is None
    assert ac.project_in('=== FILE: a.css ===\nx\n=== END ===') is None
    assert ac.project_in('nothing') is None


def test_project_saves_a_preview_and_a_real_zip(tmp_path):
    import io
    import zipfile
    import agent_files as af
    cat = {'id': 'c1', 'files': []}; files = ac.project_in(PROJECT_REPLY)
    row = af.save_project(tmp_path, cat, files, ac.project_preview(files), 'My counter', 5.0)
    assert row['ext'] == 'html' and [x['path'] for x in row['project']] == sorted(files)
    z = af.find(cat, row['zip']); assert z['ext'] == 'zip'
    names = zipfile.ZipFile(io.BytesIO(af.read(tmp_path, cat, z['id']))).namelist()
    assert 'My counter/js/app.js' in names and len(names) == 3

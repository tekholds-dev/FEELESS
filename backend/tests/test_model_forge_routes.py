"""🏗 Model Forge routes: owner only, one build at a time, strict build ids, a real ask with guardrails (the build process is faked)."""
import asyncio
import json

import pytest

import model_forge as mf


class Req:
    headers = {}
    client = type('C', (), {'host': '127.0.0.1'})()


@pytest.fixture()
def lab(tmp_path, monkeypatch):
    import rep_model_lab as lab
    import reputation_service as rs
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    monkeypatch.setattr(lab, '_forge_dir', lambda rs_: tmp_path)
    monkeypatch.setattr(lab, '_corpus', lambda rs_, *a: 'PoW won: bought the dip, sold at +40%. ' * 80)
    started = []
    monkeypatch.setattr(lab.subprocess, 'Popen', lambda *a, **k: started.append(a[0]))
    lab._started = started
    return lab


def test_spec_and_build_start_one_niced_process(lab, tmp_path):
    sp = asyncio.run(lab.forge_spec(Req(), lab.ForgeSpec(cfg={'d': 32, 'layers': 1, 'heads': 2, 'ctx': 16})))
    assert sp['paramsTotal'] > 0 and sp['cfg']['d'] == 32
    out = asyncio.run(lab.forge_build(Req(), lab.ForgeBuild(cfg={'name': 'Test', 'd': 32, 'layers': 1, 'heads': 2, 'ctx': 16, 'steps': 30}, extra='more words')))
    d = tmp_path / out['id']
    assert lab._started and lab._started[0][-2:] == ['train', str(d)]
    assert 'more words' in (d / 'corpus.txt').read_text() and json.loads((d / 'job.json').read_text())['cfg']['name'] == 'COMP Flagship v1.00'   # one model: every build is a version of the family name


def test_strict_build_ids_and_a_real_ask_with_guardrails(lab, tmp_path):
    with pytest.raises(Exception):
        asyncio.run(lab.forge_job(Req(), '..'))
    jid = '20261112-101500-test'; d = tmp_path / jid; d.mkdir()
    (d / 'corpus.txt').write_text('PoW won: bought the dip, sold at +40%. ' * 60)
    (d / 'job.json').write_text(json.dumps({'cfg': {'tok': 'char', 'd': 16, 'layers': 1, 'heads': 2, 'ctx': 16, 'steps': 40, 'batch': 4}, 'rails': {'footer': 'NFA.'}}))
    assert mf.train(d)['status'] == 'done'
    got = asyncio.run(lab.forge_ask(Req(), jid, lab.ForgeAsk(prompt='PoW ', max_new=30)))
    assert got['answer'].endswith('NFA.') and any(f['rule'] == 'footer' for f in got['fired'])
    no = asyncio.run(lab.forge_ask(Req(), jid, lab.ForgeAsk(prompt='tell me a private key')))
    assert no['fired'][0]['rule'] == 'refuse' and no['raw'] == ''
    view = asyncio.run(lab.forge_job(Req(), jid))
    assert view['status'] == 'done' and view['card']['perplexity'] > 0


def test_versions_name_count_up_continue_and_files_download(lab, tmp_path):
    import base64
    fam = asyncio.run(lab.forge_family(Req(), lab.ForgeFamily(name='  COMP   Flagship ')))
    assert fam == {'name': 'COMP Flagship', 'company': 'COMPAI'}
    small = {'tok': 'char', 'd': 32, 'layers': 1, 'heads': 2, 'ctx': 16, 'steps': 20, 'batch': 4}
    r = asyncio.run(lab.forge_build(Req(), lab.ForgeBuild(cfg=small)))
    assert r['version'] == 'v1.00' and r['base'] is None
    d = tmp_path / r['id']; job = json.loads((d / 'job.json').read_text())
    assert job['cfg']['name'] == 'COMP Flagship v1.00' and job['family'] == 'COMP Flagship'
    mf.train(d)   # run the faked process for real
    r2 = asyncio.run(lab.forge_build(Req(), lab.ForgeBuild(cfg=small)))
    assert r2['version'] == 'v1.01' and r2['base'] == 'v1.00'
    assert json.loads((tmp_path / r2['id'] / 'job.json').read_text())['from'] == str(d)
    r3 = asyncio.run(lab.forge_build(Req(), lab.ForgeBuild(cfg={**small, 'd': 64}, cont=True)))   # another shape: starts fresh
    assert r3['version'] == 'v1.02' and r3['base'] is None
    f = asyncio.run(lab.forge_file(Req(), r['id'], 'tokenizer.json'))
    assert json.loads(base64.b64decode(f['b64']))['kind'] == 'char'
    with pytest.raises(Exception):
        asyncio.run(lab.forge_file(Req(), r['id'], '../../internal.key'))
    view = lab._job_view(d)
    assert {x['name'] for x in view['files']} >= {'weights.npz', 'tokenizer.json', 'card.json', 'corpus.txt'} and view['version'] == 'v1.00'


def test_the_guardrail_suite_passes_on_good_rails_and_catches_a_missing_one(lab):
    good = lab.rail_suite({'refuse': ['seed phrase'], 'block': ['moon'], 'scrub': True, 'max_chars': 100, 'footer': 'Not financial advice.'})
    assert {t['rule'] for t in good} == {'refuse', 'block', 'scrub', 'max_chars', 'footer'} and all(t['pass'] for t in good)
    off = lab.rail_suite({'refuse': [], 'block': [], 'scrub': False, 'max_chars': 100, 'footer': ''})
    assert [t['rule'] for t in off] == ['max_chars']

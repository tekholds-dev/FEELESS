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
    monkeypatch.setattr(lab, '_corpus', lambda rs_: 'PoW won: bought the dip, sold at +40%. ' * 80)
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
    assert 'more words' in (d / 'corpus.txt').read_text() and json.loads((d / 'job.json').read_text())['cfg']['name'] == 'Test'


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

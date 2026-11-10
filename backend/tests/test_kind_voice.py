"""AGT-3 / AGT-4: a proof kind may carry its own prompt and personality; anything else uses the agent's own."""
from test_play_studio import _server


def test_a_kind_has_its_own_prompt_and_personality(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g']['brainsCfg'].update(persona={'style': 'warm'})
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'kind_voice', **kw})
    assert post(text='nope', tools={'prompt': 'x'}).status_code == 400
    r = post(text='pob', tools={'prompt': 'Bet only on games with a final score source.   Be brief.', 'persona': {'style': 'analyst'}})
    assert r.status_code == 200 and r.json()['promptBy'] == {'pob': 'Bet only on games with a final score source. Be brief.'}
    cat = store['cats']['g']
    tok = fs._CALL_CTX.set({'kind': 'pob'})
    try:
        mind = fs._general_mind(cat)
    finally:
        fs._CALL_CTX.reset(tok)
    import prompt_studio as ps
    assert 'Bet only on games with a final score source' in mind and ps.PERSONAS['analyst'] in mind and ps.PERSONAS['warm'] not in mind
    plain = fs._general_mind(cat)   # no proof running: the agent's own voice, no kind prompt
    assert 'final score source' not in plain
    post(text='pob', tools={'prompt': '', 'persona': None})
    assert store['cats']['g']['brainsCfg']['promptBy'] == {} and store['cats']['g']['brainsCfg']['personaBy'] == {}

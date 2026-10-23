"""✂ P2 #1 (2026-10-23): no fake model labels — the brain list is FEELESS's own models + one honest rule-engine row, and a cat saved under
the old catalog ('GPT-6 Astra' that only ran the rules) reads as the rule engine. Real AI brains (brainsCfg) and NEXA's cat keep theirs."""
import feecat_service as fs


def test_no_catalog_labels_left():
    assert not hasattr(fs, 'BRAIN_CATALOG')
    assert fs.RULE_ENGINE['label'] == 'FEELESS rule engine'


def test_old_cats_read_honest_but_real_brains_stay():
    old = fs.honest_brain({'brain': 'gpt-astra', 'brainLabel': 'GPT-6 Astra', 'brainProfile': {'provider': 'OpenAI'}})
    assert old['brainLabel'] == 'FEELESS rule engine' and old['brainProfile']['provider'] == 'FEELESS'
    real = {'brain': 'x', 'brainLabel': 'kimi + qwen', 'brainsCfg': {'brains': ['a/kimi']}}
    assert fs.honest_brain(dict(real))['brainLabel'] == 'kimi + qwen'
    nexa = {'brain': 'nexa', 'brainLabel': 'NEXA', 'modelBrain': 'nexa'}
    assert fs.honest_brain(dict(nexa))['brainLabel'] == 'NEXA'


def test_internal_model_names_never_reach_users():
    assert fs.public_words('Bought — 🪟 NEXA said YES; OSSY / G4 saying SELL') == 'Bought — 🔮 her AI desk said YES; 🔮 her AI desk / 🔮 her AI desk saying SELL'
    assert 'NEXA' not in fs.public_words('NEXA SICARIO')
    assert fs.public_words('G4X stays, nexapod stays') == 'G4X stays, nexapod stays'   # whole words only
    assert fs.public_words(None) is None

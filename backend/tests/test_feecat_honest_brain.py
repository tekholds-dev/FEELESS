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
    assert fs.public_words('Bought — 🪟 NEXA said YES; OSSY / G4 saying SELL') == 'Bought — 🔮 FeeCat AI said YES; 🔮 FeeCat AI / 🔮 FeeCat AI saying SELL'
    assert 'NEXA' not in fs.public_words('NEXA SICARIO')
    assert fs.public_words('G4X stays, nexapod stays') == 'G4X stays, nexapod stays'   # whole words only
    assert fs.public_words(None) is None


def test_only_the_owner_wallet_switches_fee_real():
    fee, mine = {'isLeader': True}, {'isLeader': False}
    assert fs.fee_owner_real(fee, 'real', 'OWNER', owners=['OWNER']) is True
    assert fs.fee_owner_real(fee, 'proposal', 'OWNER', owners=['OWNER']) is True
    assert fs.fee_owner_real(fee, 'real', 'STRANGER', owners=['OWNER']) is False   # anyone else → the internal key or 403
    assert fs.fee_owner_real(fee, 'run', 'OWNER', owners=['OWNER']) is False       # the owner wallet can't run her engine through this door
    assert fs.fee_owner_real(mine, 'real', 'OWNER', owners=['OWNER']) is False     # users' cats keep their own ownerId check
    assert fs.fee_owner_real(fee, 'real', None, owners=['OWNER']) is False


def test_fee_speaks_in_her_voice_numbers_untouched():
    buy = fs.fee_voice('🐱 Bought 0.1 SOL of $AAA')
    assert buy.split('\n', 1)[1] == '🐱 Bought 0.1 SOL of $AAA' and buy.split('\n')[0] in fs.FEE_OPENERS['buy']
    assert fs.fee_voice('🐱 Fee took profit on $AAA').split('\n')[0] in fs.FEE_OPENERS['win']
    assert fs.fee_voice('🐱 Fee sold $AAA at -12%\nP&L -0.01 SOL').split('\n')[0] in fs.FEE_OPENERS['loss']
    assert fs.fee_voice('🐱 Added 0.1 SOL to winner').split('\n')[0] in fs.FEE_OPENERS['add']
    assert fs.fee_voice('x') == fs.fee_voice('x')   # stable


def test_old_receipts_lose_the_echo_and_the_old_name():
    assert fs.public_words('🔮 FeeCat AI said exit: under 12 words, numbers. P&L') == '🔮 FeeCat AI said exit. P&L'
    assert fs.public_words('🔮 her AI desk said exit') == '🔮 FeeCat AI said exit'

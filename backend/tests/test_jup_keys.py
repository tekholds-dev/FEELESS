"""🔑 the keeper keeps its keys; price reads get the last key once there are three (jup_keys)."""
import jup_keys as jk


def test_three_keys_set_one_aside_for_reads():
    env = {'JUPITER_API_KEY': 'a' * 20, 'JUPITER_API_KEY_2': 'b' * 20, 'JUPITER_API_KEY_3': 'c' * 20}
    assert jk.read_key(env) == 'c' * 20 and jk.keeper_keys(env) == ['a' * 20, 'b' * 20]


def test_fewer_keys_stay_the_keepers_and_reads_go_public():
    env = {'JUPITER_API_KEY': 'a' * 20, 'JUPITER_API_KEY_2': 'b' * 20, 'JUPITER_API_KEY_3': 'a' * 20}   # a repeat is one key
    assert jk.read_key(env) is None and jk.keeper_keys(env) == ['a' * 20, 'b' * 20]
    assert jk.read_key({'JUPITER_API_KEY': 'a' * 20, 'JUPITER_READ_KEY': 'r' * 20}) == 'r' * 20


def test_candles_reads_never_use_the_keepers_key():
    src = open(__file__.replace('tests/test_jup_keys.py', 'candles_service.py')).read()
    i = src.index('async def _px_fetch(')
    assert "os.environ.get('JUPITER_API_KEY'" not in src[i:i + 2500] and '_jk.read_key(os.environ)' in src[i:i + 2500]

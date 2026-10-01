"""The Helius key is found even when SOLANA_RPC_URL points at another provider (trade tape, wallet scans)."""
import pytest

KEY = '0123456789abcdef-0123-4567'


@pytest.mark.parametrize('mod', ['candles_service', 'reputation_service'])
def test_helius_key_sources(monkeypatch, mod):
    m = pytest.importorskip(mod)
    for v in ('HELIUS_API_KEY', 'HELIUS_RPC_URL', 'SOLANA_RPC_URL'):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv('SOLANA_RPC_URL', f'https://solana-mainnet.g.alchemy.com/v2/xyz?api-key={KEY}')
    assert m._helius_key() is None  # an Alchemy key is not a Helius key
    monkeypatch.setenv('HELIUS_RPC_URL', f'https://mainnet.helius-rpc.com/?api-key={KEY}')
    assert m._helius_key() == KEY
    monkeypatch.setenv('HELIUS_API_KEY', 'direct-key')
    assert m._helius_key() == 'direct-key'

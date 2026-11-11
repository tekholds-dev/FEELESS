"""The Helius key is found even when SOLANA_RPC_URL points at another provider (trade tape, wallet scans)."""
import pytest

KEY = '0123456789abcdef-0123-4567'


@pytest.mark.parametrize('mod', ['candles_service', 'reputation_service'])
def test_helius_key_sources(monkeypatch, mod):
    m = pytest.importorskip(mod)
    for v in ('HELIUS_API_KEY', 'HELIUS_RPC_URL', 'SOLANA_RPC_URL', *(f'SOLANA_RPC_URL_{n}' for n in range(2, 7))):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv('SOLANA_RPC_URL', f'https://solana-mainnet.g.alchemy.com/v2/xyz?api-key={KEY}')
    assert m._helius_key() is None  # an Alchemy key is not a Helius key
    monkeypatch.setenv('HELIUS_RPC_URL', f'https://mainnet.helius-rpc.com/?api-key={KEY}')
    assert m._helius_key() == KEY
    monkeypatch.setenv('HELIUS_API_KEY', 'direct-key')
    assert m._helius_key() == 'direct-key'


def test_spent_helius_key_is_skipped(monkeypatch):
    """HELIUS_RPC_URL's plan is spent ('max usage reached') → the working SOLANA_RPC_URL key is used; all spent → still a key."""
    import chain_rpc as c
    for v in ('HELIUS_API_KEY', 'HELIUS_RPC_URL', 'SOLANA_RPC_URL', *(f'SOLANA_RPC_URL_{n}' for n in range(2, 7))):
        monkeypatch.delenv(v, raising=False)
    old, new = 'spentspentspent-0000-1111', 'livelivelivelive-2222-3333'
    hurl, surl = f'https://mainnet.helius-rpc.com/?api-key={old}', f'https://mainnet.helius-rpc.com/?api-key={new}'
    monkeypatch.setenv('HELIUS_RPC_URL', hurl)
    monkeypatch.setenv('SOLANA_RPC_URL', surl)
    assert c.out_of_quota(429, 'max usage reached') > 0
    monkeypatch.setattr(c, '_quota_until', {surl: 0})
    assert c.helius_key() == new
    monkeypatch.setattr(c, '_quota_until', {surl: 9e12})
    assert c.helius_key() == old
    monkeypatch.setattr(c, '_quota_until', {surl: 9e12, hurl: 9e12})
    assert c.helius_key() in (old, new)

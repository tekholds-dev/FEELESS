"""🔒 A phone must prove a wallet before it receives that wallet's alerts, and the frontend must never hold a backend secret."""
import pathlib
import re

import pytest


def test_a_phone_cannot_claim_a_wallet_it_never_proved(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'primary_of', lambda a: a)
    monkeypatch.setattr(rs, 'session_address', lambda s: {'good': 'VICTIM', 'other': 'ATTACKER'}.get(s))
    assert 'address' not in rs._push_prefs({'address': 'VICTIM', 'x': 1}, {}, '')             # no proof: the wallet is dropped, the prefs stay
    assert rs._push_prefs({'address': 'VICTIM', 'x': 1}, {}, '')['x'] == 1
    assert 'address' not in rs._push_prefs({'address': 'VICTIM'}, {}, 'other')                # someone else's session proves nothing
    assert rs._push_prefs({'address': 'VICTIM'}, {}, 'good')['address'] == 'VICTIM'           # its own signed session
    assert rs._push_prefs({'address': 'VICTIM'}, {'address': 'VICTIM'}, '')['address'] == 'VICTIM'   # this phone already held it
    assert 'address' not in rs._push_prefs({'address': 'NEW'}, {'address': 'VICTIM'}, '')     # holding one wallet proves no other
    assert rs._push_prefs({}, {}, '') == {}


def test_no_backend_secret_value_is_in_the_frontend_source():
    root = pathlib.Path(__file__).resolve().parents[2]; env = root / 'backend' / '.env'
    if not env.exists():
        pytest.skip('no local .env to compare with')
    secrets = {}
    for line in env.read_text(errors='ignore').splitlines():
        m = re.match(r'^([A-Z0-9_]+)=(.+)$', line.strip())
        if m and re.search(r'KEY|SECRET|TOKEN|PASS|PRIVATE|SEED', m.group(1)) and len(m.group(2).strip('"\' ')) >= 16:
            secrets[m.group(1)] = m.group(2).strip('"\' ')
    hits = set()
    for base in ('frontend/src', 'frontend/public'):
        for f in (root / base).rglob('*'):
            if f.is_file() and f.suffix in ('.js', '.jsx', '.json', '.html', '.ts', '.tsx') and f.stat().st_size < 3_000_000:
                text = f.read_text(errors='ignore')
                hits |= {k for k, v in secrets.items() if v in text}
    assert not hits, f'secret names found in the frontend: {sorted(hits)}'   # names only: a value never reaches a log

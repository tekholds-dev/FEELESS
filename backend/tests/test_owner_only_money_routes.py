"""🔒 Audit 2026-11-12 #2: a granted "admin" wallet could point every swap fee at itself. Each route that decides where money goes, or marks
money paid, must check the OWNER (the creator wallets), not the lower admin role."""
import re
import pathlib

SRC = (pathlib.Path(__file__).resolve().parents[1] / 'reputation_service.py').read_text().split('\n')
MONEY = ['/api/reputation/admin/fees', '/api/reputation/admin/fees/house', '/api/reputation/admin/fees/bundle', '/api/reputation/admin/treasury/split',
         '/api/reputation/admin/pools/register', '/api/reputation/admin/vaults', '/api/reputation/admin/airdrops', '/api/reputation/admin/badge-pools',
         '/api/reputation/admin/badge-pools/{pid}/paid', '/api/reputation/admin/fuses/payouts/paid', '/api/reputation/admin/reserve/{sid}/paid']


def test_money_destination_routes_check_the_owner_first():
    seen = {}
    for i, l in enumerate(SRC):
        m = re.match(r"@app\.(post|put|delete)\('([^']+)'", l)
        if m and m.group(2) in MONEY:
            guard = next((g for g in SRC[i + 1:i + 14] if '_require_admin(' in g or '_require_owner(' in g), '')
            seen[m.group(2)] = '_require_owner(' in guard
    assert set(seen) == set(MONEY), set(MONEY) - set(seen)
    assert all(seen.values()), [k for k, v in seen.items() if not v]


def test_an_admin_who_is_not_the_owner_is_refused(monkeypatch):
    import pytest
    import reputation_service as rs
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN_NOT_OWNER')
    monkeypatch.setattr(rs, '_owner_wallets', lambda: {'THE_OWNER'})
    with pytest.raises(rs.HTTPException) as e:
        rs._require_owner(object())
    assert e.value.status_code == 403

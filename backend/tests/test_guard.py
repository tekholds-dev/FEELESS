"""🛡 Guard: floods get a breather (never a block), Cmd Ctr brute force cools down, blocks ONLY by admin approval,
internal services never limited, X-Forwarded-For only trusted from our proxy (rightmost hop)."""
import asyncio

import pytest

import guard as g

IP = '8.8.4.4'


def test_flood_breather_then_suspect_never_auto_block():
    s = g.new_state(); now = 1000.0
    for i in range(g.WRITE_PER_MIN):
        assert g.check(s, IP, 'POST', '/api/reputation/chat', now + i * 0.1) is None
    assert g.check(s, IP, 'GET', '/api/reputation/feed', now + 10) is None          # reads always pass
    for k in range(g.SUSPECT_FLOODS):
        assert g.check(s, IP, 'POST', '/x', now + 10 + k)[0] == 429
    assert IP in s['suspects'] and s['suspects'][IP]['rules']['flood'] >= 1 and not s['blocks']
    assert g.check(s, IP, 'POST', '/x', now + 75) is None                             # a minute later: back to normal


def test_admin_brute_force_cools_down_admin_only():
    s = g.new_state(); now = 5000.0
    for i in range(g.ADMIN_FAILS):
        g.after(s, IP, 'GET', '/api/reputation/admin/security', 401, now + i)
    assert g.check(s, IP, 'GET', '/api/reputation/admin/security', now + 20)[0] == 429
    assert g.check(s, IP, 'POST', '/api/reputation/chat', now + 20) is None           # trading/chat still works
    assert 'admin-brute' in s['suspects'][IP]['rules'] and not s['blocks']
    assert g.check(s, IP, 'GET', '/api/reputation/admin/x', now + g.ADMIN_COOL + 30) is None


def test_blocks_only_by_admin_and_reversible():
    s = g.new_state()
    g._flag(s, IP, 1, 'flood', 'evidence')
    g.decide(s, IP, 'block', 'ADMIN', now=2, note='spam')
    assert g.check(s, IP, 'POST', '/x', 3)[0] == 403 and g.check(s, IP, 'GET', '/x', 3) is None
    assert s['blocks'][IP]['evidence'][0]['claim'] == 'evidence' and IP not in s['suspects']
    g.decide(s, IP, 'unblock', 'ADMIN', now=4)
    assert g.check(s, IP, 'POST', '/x', 5) is None and [x['action'] for x in s['log']] == ['block', 'unblock']
    with pytest.raises(ValueError):
        g.decide(s, '127.0.0.1', 'block', 'ADMIN')
    with pytest.raises(ValueError):
        g.decide(s, IP, 'nuke', 'ADMIN')


def test_internal_and_proxy_rules():
    s = g.new_state()
    for i in range(500):
        assert g.check(s, '127.0.0.1', 'POST', '/x', 1 + i * 0.01) is None and g.check(s, '10.0.0.4', 'POST', '/x', 1) is None
    h = {'x-forwarded-for': '1.1.1.1, 198.51.100.7'}
    assert g.client_ip(h, '10.0.0.2', trust_proxy=False) == '10.0.0.2'                 # spoofed header ignored
    assert g.client_ip(h, '10.0.0.2', trust_proxy=True) == '198.51.100.7'               # our proxy's hop, not the typed one
    assert g.client_ip({'x-forwarded-for': 'lol'}, '10.0.0.2', trust_proxy=True) == 'invalid' and not g.is_internal('invalid')


def test_guard_endpoints_admin_only_and_audited(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_guard_state', None)
    monkeypatch.setattr(rs, '_require_admin', lambda r: (_ for _ in ()).throw(rs.HTTPException(403, 'no')))
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_guard(None))
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    g._flag(rs._guard_s(), IP, 1, 'flood', 'x')
    v = asyncio.run(rs.admin_guard_decide(rs.GuardDecision(ip=IP, action='block', note='bot'), None))
    assert v['blocks'][0]['ip'] == IP and v['blocks'][0]['by'] == 'ADMIN' and not v['suspects']
    assert rs._admin_load()['audit'][-1]['action'] == 'guard-block'
    monkeypatch.setattr(rs, '_guard_state', None)                                         # survives a restart
    assert IP in rs._guard_s()['blocks']


def test_roles_scoped_and_grants_need_owner_signature(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    OWNER = rs._owner_wallets()[0]; MOD = 'Mod11111111111111111111111111111111111111111'
    rs._json_save(rs.DATA_DIR / 'roles.json', {'grants': {MOD: {'role': 'moderator'}}})

    class U:
        def __init__(self, p): self.path = p

    class R:
        def __init__(self, p, m='GET'): self.url = U(p); self.method = m
    rs._role_gate(MOD, R('/api/reputation/admin/bugs', 'POST'))                      # own section
    rs._role_gate(MOD, R('/api/reputation/admin/security'))                          # read-only health
    for path, m in (('/api/reputation/admin/fees/bundle', 'POST'), ('/api/reputation/admin/fuses/payouts/paid', 'POST'), ('/api/reputation/admin/security/guard', 'POST'), ('/api/reputation/admin/roles', 'POST')):
        with pytest.raises(rs.HTTPException) as e:
            rs._role_gate(MOD, R(path, m))
        assert e.value.status_code == 403
    rs._role_gate(OWNER, R('/api/reputation/admin/fees/bundle', 'POST'))            # owner reaches everything
    monkeypatch.setattr(rs, '_require_admin', lambda r: OWNER)
    sigs = []
    monkeypatch.setattr(rs, '_verify_wallet', lambda a, msg, sig: sigs.append((a, msg)) or sig == 'GOOD')
    with pytest.raises(rs.HTTPException) as e:                                        # session alone is not enough
        asyncio.run(rs.admin_role_grant(None, rs.RolePayload(address=MOD, role='admin')))
    assert e.value.status_code == 401
    import time as _t
    ts = int(_t.time())
    assert asyncio.run(rs.admin_role_grant(None, rs.RolePayload(address=MOD, role='admin', ts=ts, sig='GOOD')))['ok']
    assert sigs[-1] == (OWNER, rs.grant_message(MOD, 'admin', ts))
    with pytest.raises(rs.HTTPException):                                             # stale signature refused
        asyncio.run(rs.admin_role_grant(None, rs.RolePayload(address=MOD, role='admin', ts=ts - 3600, sig='GOOD')))

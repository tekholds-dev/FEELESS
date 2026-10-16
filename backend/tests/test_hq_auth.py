"""hq_auth.py — the pure HQ auth rules reputation_service.py wraps (session, roles, staff, signatures)."""
import base64

import pytest
from fastapi import HTTPException

import hq_auth as ha


def test_owner_wallets_read_the_env_list_else_the_creator():
    assert ha.owner_wallets(' A , B,') == ['A', 'B']
    assert ha.owner_wallets('') == [ha.FEE_CREATOR_WALLET]
    assert ha.granted_wallets({'X': {'role': 'moderator'}, 'Y': {'role': 'viewer'}, 'Z': None}) == ['X']


def test_check_session_order_of_refusals():
    ok = lambda a, m, s: s == 'GOOD' and m == ha.session_message(a, 100)
    with pytest.raises(HTTPException) as e:
        ha.check_session('NOPE', '100', 'GOOD', ['A'], ok, 100)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        ha.check_session('A', 'x', 'GOOD', ['A'], ok, 100)
    assert e.value.detail == 'Missing HQ signature.'
    with pytest.raises(HTTPException) as e:
        ha.check_session('A', '100', 'GOOD', ['A'], ok, 100 + ha.SESSION_SEC + 1)
    assert 'expired' in e.value.detail
    with pytest.raises(HTTPException) as e:
        ha.check_session('A', '100', 'BAD', ['A'], ok, 100)
    assert e.value.detail == 'HQ signature does not match.'
    assert ha.check_session('A', '100', 'GOOD', ['A'], ok, 100) == 'A'


def test_scoped_roles_reach_only_their_sections():
    assert ha.section_of('/api/reputation/admin/fuses/x') == 'fuses' and ha.section_of('/api/x') == ''
    ha.check_role('owner', '/api/reputation/admin/fuses', 'POST')          # not scoped: passes
    ha.check_role('moderator', '/api/reputation/admin/bugs', 'POST')
    ha.check_role('marketing', '/api/reputation/admin/roles', 'GET')       # read-only section on GET
    with pytest.raises(HTTPException):
        ha.check_role('marketing', '/api/reputation/admin/roles', 'POST')
    with pytest.raises(HTTPException):
        ha.check_role('moderator', '/api/reputation/admin/fuses', 'GET')
    assert ha.role_of('O', ['O'], {}) == 'owner' and ha.role_of('M', ['O'], {'M': {'role': 'moderator'}}) == 'moderator'
    assert ha.role_of('Q', ['O'], {}) == 'none'


def test_staff_includes_linked_wallets():
    prim = {'L': 'A'}.get
    primary_of = lambda a: prim(a, a)
    assert ha.is_staff('L', ['A'], primary_of) and ha.is_staff('A', ['A'], primary_of)
    assert not ha.is_staff('', ['A'], primary_of) and not ha.is_staff('Z', ['A'], primary_of)


def test_solana_signature_accepts_base64_base58_and_hex():
    nacl = pytest.importorskip('nacl.signing')
    base58 = pytest.importorskip('base58')
    key = nacl.SigningKey.generate()
    addr = base58.b58encode(bytes(key.verify_key)).decode()
    raw = key.sign(b'hi').signature
    for enc in (base64.b64encode(raw).decode(), base58.b58encode(raw).decode(), raw.hex(), '0x' + raw.hex()):
        assert ha.verify_wallet(addr, 'hi', enc)
    assert not ha.verify_wallet(addr, 'other', base64.b64encode(raw).decode())
    assert not ha.verify_wallet('not-a-key', 'hi', 'x')
    assert ha.grant_message('W', 'admin', 5.9) == 'FEELESS grant HQ access\nwallet:W\nrole:admin\nts:5'

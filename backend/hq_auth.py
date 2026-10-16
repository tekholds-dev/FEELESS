"""🔐 HQ auth rules — wallet signatures, the signed HQ session, scoped roles, staff. Pure (no I/O, no app state).

reputation_service.py keeps thin wrappers with the old names (`_require_admin`, `_require_owner`, `_role_gate`, `_is_staff`,
`_verify_wallet` …) that read the live wallet lists and hand them in here — so routes, callers and test monkeypatches are unchanged.
Tested through the routes (tests/test_guard.py signs a real Ed25519 HQ session) and tests/test_hq_auth.py.
"""
import base64
import re

from fastapi import HTTPException

# $FEE's creator wallet (fee payer of the mint's first transaction on-chain) is the default owner; FEELESS_ADMIN_WALLETS overrides it.
FEE_CREATOR_WALLET = 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P'
SESSION_SEC = 86400          # an HQ sign-in is good for a day

# Granted roles are SCOPED (hard-coded): a moderator / marketing wallet only reaches its own HQ sections; 'admin'
# grants reach everything except owner-only money (Circle, referrals, NFTs… via _require_owner). Owners reach everything.
ROLE_NAMES = ('admin', 'moderator', 'marketing')
ROLE_SCOPES = {
    'moderator': {'moderate', 'bugs', 'shield', 'chat-guard', 'chat-feed', 'verify', 'coin-verify', 'intel-desk', 'latency', 'perf'},
    'marketing': {'marketing', 'broadcast', 'kols', 'ads', 'ideas', 'traffic', 'numbers'},
}
ROLE_READ = {'security', 'roles', 'whoami', 'is-admin'}      # every role may read these (its own access + health)

_EVM = re.compile(r'^0x[0-9a-fA-F]{40}$')


def owner_wallets(env_value):
    """FEELESS_ADMIN_WALLETS (comma separated) or the $FEE creator wallet."""
    env = [a.strip() for a in (env_value or '').split(',') if a.strip()]
    return env or [FEE_CREATOR_WALLET]


def granted_wallets(grants):
    """Wallets the owner granted an HQ role (roles.json `grants`)."""
    return [a for a, g in (grants or {}).items() if (g or {}).get('role') in ROLE_NAMES]


def session_message(address, ts):
    """What the admin wallet signs to open an HQ session."""
    return f'FEELESS HQ\naddress:{address}\nts:{ts}'


def grant_message(address, role, ts):
    """What the owner wallet signs to grant an HQ role (valid 10 min)."""
    return f'FEELESS grant HQ access\nwallet:{address}\nrole:{role}\nts:{int(ts)}'


def check_session(addr, ts, sig, admins, verify, now):
    """Session proof: the admin wallet signed `session_message` within SESSION_SEC. Returns the address or raises 401 / 403."""
    if addr not in admins:
        raise HTTPException(403, 'This wallet is not a FEELESS HQ wallet.')
    try:
        ts_i = int(ts)
    except ValueError:
        raise HTTPException(401, 'Missing HQ signature.')
    if abs(now - ts_i) > SESSION_SEC:
        raise HTTPException(401, 'HQ session expired — sign in again.')
    if not verify(addr, session_message(addr, ts_i), sig):
        raise HTTPException(401, 'HQ signature does not match.')
    return addr


def role_of(addr, owners, grants):
    if addr in owners:
        return 'owner'
    return ((grants or {}).get(addr) or {}).get('role') or 'none'


def section_of(path):
    """'/api/reputation/admin/fuses/x' → 'fuses' ('' outside /admin/)."""
    path = str(path or '')
    return path.split('/admin/', 1)[1].split('/', 1)[0] if '/admin/' in path else ''


def check_role(role, path, method):
    """A scoped role may reach only its own sections (+ the read-only ones on GET); everyone else passes."""
    if role not in ROLE_SCOPES:
        return
    sec = section_of(path)
    if sec in ROLE_SCOPES[role] or (sec in ROLE_READ and method == 'GET'):
        return
    raise HTTPException(403, f'Your {role} access does not include this section.')


def is_staff(address, admins, primary_of):
    """FEELESS HQ = the admin/creator wallets (any linked wallet of theirs). Staff get every unlock."""
    if not address:
        return False
    return address in admins or primary_of(address) in {primary_of(w) for w in admins}


def verify_evm(address, message, signature_hex):
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        return Account.recover_message(encode_defunct(text=message), signature=signature_hex).lower() == address.lower()
    except Exception:
        return False


def verify_solana(address, message, signature_b64):
    """Ed25519 check. Wallets encode the 64-byte signature differently (base64 from our client,
    base58 or hex from some wallets), so try each decoding that yields exactly 64 bytes."""
    try:
        import base58
        from nacl.signing import VerifyKey
        key = VerifyKey(base58.b58decode(address))
    except Exception:
        return False
    sig = (signature_b64 or '').strip()
    hexsig = sig[2:] if sig.lower().startswith('0x') else sig
    decoders = (lambda: base64.b64decode(sig, validate=True), lambda: base58.b58decode(sig), lambda: bytes.fromhex(hexsig))
    for decode in decoders:
        try:
            raw = decode()
            if len(raw) != 64:
                continue
            key.verify(message.encode(), raw)
            return True
        except Exception:
            continue
    return False


def verify_wallet(address, message, signature):
    if _EVM.match(address or ''):
        return verify_evm(address, message, signature)
    return verify_solana(address, message, signature)

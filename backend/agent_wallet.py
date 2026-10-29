"""👛 AGENT WALLETS — one Crossmint smart wallet per purchased cat / family (owner 2026-10-29: "purchased family and purchased cats can have
a wallet assigned and the user doesn't sign every txn — one trade agent made and funded, that's it, it rides; general can be switched anytime
for the user to approve general AI moves or have them do their thing"). DECISIONS #2 / #4: the owner moved from option A (the user signs
every trade) to agent wallets held by Crossmint (API-key admin signer). FEELESS stores NO key — only the wallet's address and locator.

Pure helpers (tested, tests/test_agent_wallet.py) + three async calls against Crossmint's Wallets API (2025-06-09):
  create(http, key, kind, ref)  POST /wallets            owner `userId:feeless-<kind>-<ref>` → the same wallet again on a repeat (idempotent)
  balances(http, key, address)  GET  /wallets/{a}/balances?tokens=sol,usdc
ASSIGNED (N16, owner 2026-10-29: "Fee's wallet: I wanna assign a wallet I already created — users just get a new wallet"): Fee, the leader, may
take a wallet the owner already has (`lookup` + `assigned`). FEELESS signs only through Crossmint, so: a wallet Crossmint holds for THIS project
(`GET /wallets/{address}` answers) → provider 'crossmint', she trades from it; any other wallet → provider 'watch' (shown, never traded from —
FEELESS never holds a private key).
MODES: a TRADING cat rides ('auto', fixed — funded once, it trades); a GENERAL cat starts on 'approve' (every AI move waits for the
owner's OK) and the owner may switch it to 'auto' any time; a family wallet is 'approve' (raids / payouts go through the payout engine)."""
import re

API = {'production': 'https://www.crossmint.com/api/2025-06-09', 'staging': 'https://staging.crossmint.com/api/2025-06-09'}
KINDS = ('cat', 'family')
MODES = ('approve', 'auto')
_REF = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
_ADDR = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')


def env_of(key):
    """sk_production_… → production; anything else (sk_staging_…) → staging. None = no key."""
    k = str(key or '').strip()
    return None if not k else 'production' if k.startswith(('sk_production_', 'ck_production_')) else 'staging'


def owner_of(kind, ref):
    if kind not in KINDS or not _REF.match(str(ref or '')):
        raise ValueError('Not a cat / family id.')
    return f'userId:feeless-{kind}-{ref}'


def default_mode(kind, brain_kind=None):
    """A trading cat rides on its own; a general cat and a family start on approve."""
    return 'auto' if kind == 'cat' and brain_kind == 'trading' else 'approve'


def set_mode(w, mode, brain_kind=None):
    """The owner's switch. A trading cat cannot be put on approve (it rides); a family never goes auto (the payout engine moves its money)."""
    if mode not in MODES:
        raise ValueError('Mode is approve or auto.')
    if brain_kind == 'trading' and mode != 'auto':
        raise ValueError('A trading cat rides on its own — it has no approve mode.')
    if (w or {}).get('kind') == 'family' and mode != 'approve':
        raise ValueError("A family wallet moves only through the payout engine — it has no auto mode.")
    return {**(w or {}), 'mode': mode}


def record(kind, ref, reply, owner_wallet, now, brain_kind=None):
    """Crossmint's create reply → what we keep (address + locator, never a key)."""
    a = str((reply or {}).get('address') or '')
    if not _ADDR.match(a):
        raise ValueError('Crossmint did not return a wallet address.')
    return {'kind': kind, 'ref': ref, 'address': a, 'locator': (reply or {}).get('locator') or f'{owner_of(kind, ref)}:solana:smart',
            'owner': owner_wallet, 'mode': default_mode(kind, brain_kind), 'provider': 'crossmint', 'at': round(now)}


def balance_view(rows):
    """Crossmint balances → {sol, usdc} (floats, 0 when absent)."""
    out = {'sol': 0.0, 'usdc': 0.0}
    for r in rows or []:
        s = str((r or {}).get('symbol') or '').lower()
        if s in out:
            try:
                out[s] = float(r.get('amount') or 0)
            except (TypeError, ValueError):
                pass
    return out


def _err(r):
    try:
        j = r.json()
        return str(j.get('message') or j.get('error') or r.text)[:200]
    except Exception:
        return r.text[:200]


async def create(http, key, kind, ref):
    """→ Crossmint's wallet reply (address, locator). Raises ValueError with Crossmint's own words on a refusal (a missing scope says so)."""
    env = env_of(key)
    if not env:
        raise ValueError('CROSSMINT_API_KEY is not set in backend/.env.')
    owner = owner_of(kind, ref)
    r = await http.post(f"{API[env]}/wallets", headers={'X-API-KEY': key, 'Content-Type': 'application/json', 'x-idempotency-key': owner},
                        json={'chainType': 'solana', 'type': 'smart', 'owner': owner, 'config': {'adminSigner': {'type': 'api-key'}}}, timeout=20)
    if r.status_code not in (200, 201):
        raise ValueError(f'Crossmint refused the wallet ({r.status_code}): {_err(r)}')
    return r.json()


async def balances(http, key, address):
    env = env_of(key)
    if not env or not _ADDR.match(str(address or '')):
        raise ValueError('No Crossmint key or wallet.')
    r = await http.get(f"{API[env]}/wallets/{address}/balances", params={'tokens': 'sol,usdc', 'chains': 'solana'}, headers={'X-API-KEY': key}, timeout=15)
    if r.status_code != 200:
        raise ValueError(f'Crossmint balance read failed ({r.status_code}): {_err(r)}')
    return balance_view(r.json())


async def lookup(http, key, address):
    """Is `address` a Crossmint wallet of THIS project? → its reply, or None (404 / not ours). Raises ValueError on a key / network failure."""
    env = env_of(key)
    if not env or not _ADDR.match(str(address or '')):
        raise ValueError('No Crossmint key, or not a Solana address.')
    r = await http.get(f"{API[env]}/wallets/{address}", headers={'X-API-KEY': key}, timeout=15)
    if r.status_code == 200:
        return r.json() or {}
    if r.status_code in (400, 404):
        return None
    raise ValueError(f'Crossmint did not answer ({r.status_code}): {_err(r)}')


def assigned(address, reply, owner_wallet, now):
    """An owner-assigned wallet for Fee → the record. Crossmint's own wallet = she trades from it; anything else = watch-only."""
    if not _ADDR.match(str(address or '')):
        raise ValueError('Not a Solana address.')
    return {'kind': 'cat', 'ref': 'leader', 'address': address, 'locator': (reply or {}).get('locator') or (address if reply else None), 'owner': owner_wallet,
            'mode': 'auto', 'provider': 'crossmint' if reply is not None else 'watch', 'assigned': True, 'at': round(now)}

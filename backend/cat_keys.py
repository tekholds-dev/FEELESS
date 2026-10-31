"""🔐 A trading cat's API DRAWER (owner, 2026-10-29: "a lil API etc drawer for users to add for trader agent to use").

The owner of a cat adds their own keys; FEELESS keeps each one SEALED at rest (Fernet, a server-only secret: BROKER_SECRET_KEY, else
data/internal.key) and never sends it back — the page sees the provider, a label and the last 4 characters only.

WIRED today: `openrouter` — the cat's model calls go out on YOUR key (you pay OpenRouter directly; its FEELESS credit is not charged, and the
owner's model-calls switch does not hold it back). The rest are stored for the cat's tools to read (each says so on the page, honestly).
A cat may only ever TRADE on FEELESS rails (VENUES) — a key never opens another exchange.
"""
import base64
import hashlib
import os
from pathlib import Path
import re
import time

# provider → (label, what it does for the cat, wired now?, shape check)
PROVIDERS = {
    'openrouter': ('OpenRouter', 'its models run on YOUR key — you pay OpenRouter, no FEELESS credit used', True, r'^sk-or-[A-Za-z0-9_-]{20,}$'),
    'birdeye': ('Birdeye', 'holder + price reads for its scans', False, r'^[A-Za-z0-9]{16,64}$'),
    'helius': ('Helius', 'its own Solana RPC — faster wallet + tape reads', False, r'^[A-Za-z0-9-]{20,64}$'),
    'x': ('X (Twitter)', 'a bearer token — reads the coin\'s X chatter', False, r'^[A-Za-z0-9%_-]{30,200}$'),
    'telegram': ('Telegram channel', 'a public @channel it reads for calls', False, r'^@?[A-Za-z0-9_]{5,32}$'),
    'webhook': ('Signal webhook', 'your own signal URL (https) it reads before a buy', False, r'^https://[^\s]{6,300}$'),
}
VENUES = {'trench': 'Solana coins on the FEELESS swap', 'perps': 'FEELESS perps desk'}   # the only rails a cat may trade on
VENUES_LIVE = {'trench'}   # perps: the cat proposes, the agent sender for perps is the next build
MAX_KEYS = len(PROVIDERS)


def _fernet(env=None, data_dir=None):
    from cryptography.fernet import Fernet
    env = os.environ if env is None else env
    k = str(env.get('BROKER_SECRET_KEY') or '').strip()
    if not k and data_dir is not None:
        try:
            k = (data_dir / 'internal.key').read_text().strip()
        except OSError:
            k = ''
    if not k:
        raise RuntimeError('No server secret to seal keys with (BROKER_SECRET_KEY) — FEELESS will not keep an API key in the clear.')
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(f'cat-keys:{k}'.encode()).digest()))


# 🔐 THE AGENT VAULT (owner 2026-10-30: "no one can expose another user's agent data"). Every agent's secrets (logins, API keys, its cloud pass)
# are sealed with ITS OWN key, derived from a master that lives OUTSIDE the repo and the data folder (~/.feeless-vault/master.key, 0600 —
# or BROKER_SECRET_KEY): a copied data folder or database decrypts nothing, and one agent's key opens no other agent. 'v2:' marks the new
# seal; an older seal (one key for all, kept beside the data) is still read and re-sealed at startup (`reseal_cat`).
def _master(env=None):
    env = os.environ if env is None else env
    k = str(env.get('BROKER_SECRET_KEY') or '').strip()
    if k:
        return k
    p = Path(env.get('FEELESS_VAULT_KEY_FILE') or os.environ.get('FEELESS_VAULT_KEY_FILE') or (Path.home() / '.feeless-vault' / 'master.key'))
    try:
        return p.read_text().strip()
    except OSError:
        import secrets
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as fh:
            fh.write(secrets.token_urlsafe(48))
        return p.read_text().strip()


def _agent_fernet(cat_id, env=None):
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(f'agent-vault:{cat_id or "-"}:{_master(env)}'.encode()).digest()))


def seal(text, cat_id, env=None):
    return 'v2:' + _agent_fernet(cat_id, env).encrypt(str(text).encode()).decode()


def unseal(token, cat_id, env=None, data_dir=None):
    t = str(token or '')
    if t.startswith('v2:'):
        return _agent_fernet(cat_id, env).decrypt(t[3:].encode()).decode()
    return _fernet(env, data_dir).decrypt(t.encode()).decode()   # an older seal, until reseal_cat runs


def reseal_cat(cat, env=None, data_dir=None):
    """Startup heal: every older seal on this agent → its own v2 key. → how many changed."""
    n, cid = 0, cat.get('id')
    for rows in ((cat.get('apiKeys') or {}).values(), cat.get('logins') or [], [cat['cloudLink']] if cat.get('cloudLink') else []):
        for r in rows:
            if isinstance(r, dict) and r.get('sealed') and not str(r['sealed']).startswith('v2:'):
                try:
                    r['sealed'] = seal(unseal(r['sealed'], cid, env, data_dir), cid, env); n += 1
                except Exception:
                    pass
    return n


def venues(raw):
    """The rails a trading cat may use — FEELESS only; unknown names are refused, empty = the trench."""
    v = [str(x).lower() for x in (raw or ['trench'])]
    bad = [x for x in v if x not in VENUES]
    if bad:
        raise ValueError(f"A cat trades on FEELESS rails only — {', '.join(bad)} isn't one.")
    return sorted(set(v)) or ['trench']


def put(cat, provider, secret, env=None, data_dir=None, now=None):
    """Seal one key into the cat's drawer (replaces that provider's old one)."""
    if provider not in PROVIDERS:
        raise ValueError('unknown provider')
    s = str(secret or '').strip()
    if not re.match(PROVIDERS[provider][3], s):
        raise ValueError(f"That doesn't look like a {PROVIDERS[provider][0]} key.")
    drawer = cat.setdefault('apiKeys', {})
    drawer[provider] = {'sealed': seal(s, cat.get('id'), env), 'last4': s[-4:], 'at': now or time.time()}
    return public(cat)


def drop(cat, provider):
    (cat.get('apiKeys') or {}).pop(provider, None)
    return public(cat)


def key_for(cat, provider, env=None, data_dir=None):
    """The clear key for the server's own call — never returned to a page."""
    row = (cat.get('apiKeys') or {}).get(provider)
    if not row:
        return None
    try:
        return unseal(row['sealed'], cat.get('id'), env, data_dir)
    except Exception:
        return None


def public(cat):
    """What the page may see: every provider, whether one is saved (last 4 only), and whether the cat uses it yet."""
    drawer = cat.get('apiKeys') or {}
    return [{'provider': p, 'label': lab, 'use': use, 'wired': wired, 'saved': p in drawer, 'last4': (drawer.get(p) or {}).get('last4'),
             'at': (drawer.get(p) or {}).get('at')} for p, (lab, use, wired, _) in PROVIDERS.items()]

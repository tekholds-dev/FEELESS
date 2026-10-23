"""🔑 WHICH JUPITER KEY IS FOR WHAT (pure, tested `tests/test_jup_keys.py`).

Keys live in backend/.env as `JUPITER_API_KEY`, `_2` … `_6` (env_loader keeps the FIRST value of a repeated name, so each key needs its
own name). The KEEPER's quotes (real buys and sells) own the keys; price READS (charts, result graders, the candles service) must
never take their quota. 2026-10-13: the candles service read every chart price with key 1, one coin per call — the keeper's own lane
— while the public lane answered 429 almost every time, so the graders recorded rate limits as rugs and real sells waited on quotes.

With three or more different keys the LAST one is the READ key (or `JUPITER_READ_KEY`, when set); the keeper uses the others. With
fewer, reads get no key at all (public lane, then other sources) and every key stays the keeper's.
"""
ENVS = ('JUPITER_API_KEY', 'JUPITER_API_KEY_2', 'JUPITER_API_KEY_3', 'JUPITER_API_KEY_4', 'JUPITER_API_KEY_5', 'JUPITER_API_KEY_6')
READ_ENV = 'JUPITER_READ_KEY'
READ_FROM = 3   # distinct keys before one is set aside for reads


def keys(env):
    """Every key set, in order, no repeats, blanks dropped."""
    out = []
    for name in ENVS:
        k = str((env or {}).get(name) or '').strip()
        if k and k not in out:
            out.append(k)
    return out


def read_key(env):
    """The key price reads may use, or None (reads then go public)."""
    own = str((env or {}).get(READ_ENV) or '').strip()
    if own:
        return own
    ks = keys(env)
    return ks[-1] if len(ks) >= READ_FROM else None


def keeper_keys(env):
    """The keeper's lanes: every key except the read key."""
    rk = read_key(env)
    return [k for k in keys(env) if k != rk]


def lend_keys(env):
    """Jupiter Lend builds (a user's own deposit / borrow, rare): the read key first, then the keeper's lanes from the last — one key at
    its rate limit (429) never blocks a user's transaction while another key is free."""
    rk = read_key(env)
    return ([rk] if rk else []) + [k for k in reversed(keeper_keys(env))]

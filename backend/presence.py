"""🟢 ONLINE STATUS (owner, 2026-10-21: "profile settings — online status etc."). Pure; the service keeps the state IN MEMORY only (presence is
never written to disk — nothing to hoard). A signed-in tab beats every BEAT_SEC while visible with the owner's chosen mode:
  online → shown ONLINE · away → shown AWAY · invisible → shown OFFLINE to everyone (the beat still proves the session, nothing more).
No beat for STALE_SEC → OFFLINE. At most MAX_ROWS wallets are kept (the oldest beats drop first)."""
MODES = ('online', 'away', 'invisible')
BEAT_SEC, STALE_SEC, MAX_ROWS = 60, 180, 20000


def beat(state, address, mode, now):
    mode = mode if mode in MODES else 'online'
    state[address] = (mode, now)
    if len(state) > MAX_ROWS:
        for a in sorted(state, key=lambda k: state[k][1])[:len(state) - MAX_ROWS]:
            state.pop(a, None)
    return mode


def status(state, address, now):
    row = state.get(address)
    if not row or now - row[1] > STALE_SEC or row[0] == 'invisible':
        return 'offline'
    return row[0]

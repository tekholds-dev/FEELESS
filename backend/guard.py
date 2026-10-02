"""🛡 Guard: brute-force + flood protection for every write and every admin sign-in — WITHOUT auto-blocking people.

Rules (pure, tested; the service feeds it requests):
  • Every POST/PUT/DELETE is counted per IP in a sliding minute. Over `WRITE_PER_MIN` → that request gets 429 (a short
    breather, the same for everyone). Reads are never limited here (pages must never break for a real trader).
  • Admin (HQ) sign-in failures (401/403 on /admin/) are counted per IP. `ADMIN_FAILS` in 10 min → admin requests
    from that IP cool down for `ADMIN_COOL` seconds (brute protection) — normal trading still works.
  • Anything that trips a rule becomes a SUSPECT with cited evidence. Nobody is ever blocked automatically: a block only
    exists after an admin approves it in HQ › Security (and an admin can lift it). Approved blocks get 403 on writes.
  • Local / private addresses (the services talking to each other) are never limited or flagged.
"""
import ipaddress
import time

WRITE_PER_MIN = 90          # writes per IP per minute before a breather
ADMIN_FAILS = 8             # failed HQ signatures per IP in ADMIN_WINDOW → cool down
ADMIN_WINDOW = 600
ADMIN_COOL = 900
SUSPECT_FLOODS = 3          # breathers in 10 min → suspect (for review, not a block)


def _valid(ip):
    try:
        return ipaddress.ip_address((ip or '').strip())
    except ValueError:
        return None


def is_internal(ip):
    """Loopback / private = our own services. A non-IP peer only exists in-process (test client), never from the internet."""
    if ip == 'invalid':
        return False
    a = _valid(ip)
    return a is None or a.is_loopback or a.is_private


def client_ip(headers, peer, trust_proxy=False):
    """The caller's IP. X-Forwarded-For is spoofable, so it's only read behind our own proxy — and then the RIGHTMOST entry
    (the one our proxy wrote), never the client-typed left side. A garbage value lands in one shared 'invalid' bucket."""
    if trust_proxy:
        fwd = (headers.get('x-forwarded-for') or '').split(',')[-1].strip()
        if fwd:
            return fwd if _valid(fwd) else 'invalid'
    return peer or '?'


def new_state():
    return {'writes': {}, 'fails': {}, 'cool': {}, 'floods': {}, 'suspects': {}, 'blocks': {}, 'log': []}


def _trim(xs, now, win):
    return [t for t in xs if now - t < win]


def _flag(s, ip, now, rule, claim):
    sp = s['suspects'].setdefault(ip, {'ip': ip, 'first': now, 'rules': {}, 'evidence': []})
    sp['last'] = now
    sp['rules'][rule] = sp['rules'].get(rule, 0) + 1
    if not sp['evidence'] or sp['evidence'][-1]['claim'] != claim:
        sp['evidence'] = (sp['evidence'] + [{'at': now, 'rule': rule, 'claim': claim}])[-12:]


def check(s, ip, method, path, now=None):
    """Before a request runs. Returns None (go) or (status, message)."""
    now = now or time.time()
    if is_internal(ip):
        return None
    b = s['blocks'].get(ip)
    if b and method != 'GET':
        return 403, 'This address was blocked by FEELESS staff. Contact support if this is a mistake.'
    if '/admin/' in path and s['cool'].get(ip, 0) > now:
        return 429, f"Too many failed HQ sign-ins — try again in {int((s['cool'][ip] - now) // 60) + 1} min."
    if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        w = _trim(s['writes'].get(ip, []), now, 60)
        if len(w) >= WRITE_PER_MIN:
            f = _trim(s['floods'].get(ip, []), now, 600) + [now]
            s['floods'][ip] = f
            if len(f) >= SUSPECT_FLOODS:
                _flag(s, ip, now, 'flood', f'{len(w)}+ writes a minute, {len(f)} times in 10 min')
            return 429, 'Slow down — too many actions a minute.'
        s['writes'][ip] = w + [now]
    return None


def after(s, ip, method, path, status, now=None):
    """After a request: counts failed HQ sign-ins (brute force)."""
    now = now or time.time()
    if is_internal(ip) or '/admin/' not in path or status not in (401, 403):
        return
    f = _trim(s['fails'].get(ip, []), now, ADMIN_WINDOW) + [now]
    s['fails'][ip] = f
    if len(f) >= ADMIN_FAILS:
        s['cool'][ip] = now + ADMIN_COOL
        s['fails'][ip] = []
        _flag(s, ip, now, 'admin-brute', f'{len(f)} failed HQ signatures in {ADMIN_WINDOW // 60} min')


def decide(s, ip, action, admin, now=None, note=''):
    """Admin approvals: 'block' (only a flagged suspect or an explicit IP), 'dismiss' (clear the suspect), 'unblock'."""
    now = now or time.time()
    if action not in ('block', 'dismiss', 'unblock'):
        raise ValueError('action must be block, dismiss or unblock')
    if is_internal(ip):
        raise ValueError('internal addresses are never blocked')
    if action == 'block':
        ev = (s['suspects'].get(ip) or {}).get('evidence', [])
        s['blocks'][ip] = {'ip': ip, 'at': now, 'by': admin, 'note': note[:200], 'evidence': ev}
        s['suspects'].pop(ip, None)
    elif action == 'dismiss':
        s['suspects'].pop(ip, None); s['cool'].pop(ip, None)
    else:
        s['blocks'].pop(ip, None); s['cool'].pop(ip, None)
    s['log'] = (s['log'] + [{'at': now, 'by': admin, 'action': action, 'ip': ip, 'note': note[:200]}])[-100:]


def view(s, now=None):
    now = now or time.time()
    live = {ip: len(_trim(w, now, 60)) for ip, w in s['writes'].items()}
    return {'rules': {'writesPerMin': WRITE_PER_MIN, 'adminFails': ADMIN_FAILS, 'adminWindowMin': ADMIN_WINDOW // 60, 'adminCoolMin': ADMIN_COOL // 60},
            'busiest': sorted(({'ip': ip, 'writes1m': n} for ip, n in live.items() if n), key=lambda x: -x['writes1m'])[:10],
            'cooling': [{'ip': ip, 'until': t} for ip, t in s['cool'].items() if t > now],
            'suspects': sorted(s['suspects'].values(), key=lambda x: -x['last']),
            'blocks': sorted(s['blocks'].values(), key=lambda x: -x['at']), 'log': s['log'][-25:][::-1]}

"""🛡 DEFENCE THAT LEARNS (owner, 2026-10-21: "real web3 defence … that LEARNS from each attack (fingerprint → auto-block rules, honeypots).
Hard limit: FEELESS never attacks anyone back — trace, block, rate-limit, tarpit, report"). Pure + tested; the service feeds it requests.

guard.py stays the gentle layer (flood breathers, HQ brute cool-downs, suspects for review — never an automatic block of a person). This layer only
acts on what no real trader ever does:
  · HONEYPOTS — decoy paths a scanner tries (/.env, /wp-login.php, a fake key export…). One hit → that FINGERPRINT (ip + user-agent) is
    blocked for BLOCK_SEC; every repeat doubles it (≤ BLOCK_MAX). The decoy answers a plain 404, so the scanner learns nothing.
  · LEARNED RULES — when SHARED_HITS different IPs with the SAME non-browser user-agent (curl, python-requests, a scanner) hit honeypots,
    that user-agent itself becomes a rule (a botnet rotating IPs is still one tool). A browser's string never becomes a rule. Every rule counts its hits; it expires on its own (RULE_SEC) unless it keeps catching.
  · SCRAPERS — more than SCRAPE_PER_MIN reads a minute across SCRAPE_PATHS different paths → a TARPIT (each request waits TARPIT_S) for
    TARPIT_SEC; never a block (a busy page can look like that).
  · REPLAY — the same HQ signature from a second fingerprint → flagged + tarpitted (the signature is a day-long session; a stolen one shows up
    from somewhere new).
Every incident keeps its EVIDENCE (times, paths, user-agent, the rule) — `report` turns it into the plain text the owner can send to an abuse
contact. Nothing here ever sends a request anywhere. Everything is capped (incidents, rules, per-fingerprint memory) — the defence never hoards.
"""
import hashlib
import time

HONEYPOTS = ('/.env', '/.git/config', '/wp-login.php', '/wp-admin', '/phpmyadmin', '/server-status', '/config.json', '/backup.zip', '/admin.php',
             '/xmlrpc.php', '/.aws/credentials', '/actuator/env', '/admin/export-keys', '/admin/wallet-backup', '/debug/vars', '/private-key')
BLOCK_SEC, BLOCK_MAX = 24 * 3600, 30 * 86400
RULE_SEC = 7 * 86400
SHARED_HITS = 3
SCRAPE_PER_MIN, SCRAPE_PATHS = 240, 60
TARPIT_S, TARPIT_SEC = 3.0, 600
INCIDENTS_MAX, RULES_MAX, FPS_MAX, EVIDENCE_MAX = 300, 200, 5000, 12


def new_state():
    return {'blocks': {}, 'rules': {}, 'tarpit': {}, 'incidents': [], 'reads': {}, 'sigs': {}, 'uaHits': {}}


def fingerprint(ip, ua):
    return hashlib.sha256(f"{ip}|{(ua or '')[:200]}".encode()).hexdigest()[:16]


def ua_key(ua):
    return hashlib.sha256((ua or '').strip()[:200].encode()).hexdigest()[:12]


def browserish(ua):
    """A real browser's agent string (Mozilla/… with an engine) — never turned into a shared rule: thousands of real traders share it."""
    u = (ua or '').lower()
    return u.startswith('mozilla/') and any(e in u for e in ('applewebkit', 'gecko', 'chrome', 'safari', 'firefox')) and not any(
        t in u for t in ('bot', 'crawl', 'spider', 'scan', 'curl', 'python', 'go-http', 'headless', 'zgrab', 'nuclei', 'sqlmap', 'nikto', 'masscan'))


def honeypot(path):
    """Is this a decoy? Matches the decoy anywhere under the API (/api/reputation/.env, /api/.env …)."""
    p = (path or '').rstrip('/').lower()
    return any(p.endswith(h) or f'{h}/' in p for h in HONEYPOTS)


def _incident(s, kind, fp, ip, ua, path, now, action):
    inc = next((x for x in s['incidents'] if x['fp'] == fp and x['kind'] == kind), None)
    if not inc:
        inc = {'fp': fp, 'kind': kind, 'ip': ip, 'ua': (ua or '')[:160], 'first': now, 'evidence': [], 'n': 0}
        s['incidents'].append(inc)
        del s['incidents'][:-INCIDENTS_MAX]
    inc.update(last=now, n=inc['n'] + 1, action=action)
    inc['evidence'] = (inc['evidence'] + [[round(now), (path or '')[:120]]])[-EVIDENCE_MAX:]
    return inc


def _block(s, fp, now, why):
    b = s['blocks'].get(fp) or {'n': 0}
    n = b['n'] + 1
    s['blocks'][fp] = {'n': n, 'until': now + min(BLOCK_MAX, BLOCK_SEC * 2 ** (n - 1)), 'why': why, 'at': now}
    if len(s['blocks']) > FPS_MAX:
        for k in sorted(s['blocks'], key=lambda k: s['blocks'][k]['until'])[:len(s['blocks']) - FPS_MAX]:
            s['blocks'].pop(k)


def prune(s, now):
    """Drop what has expired: blocks, tarpits, rules nobody hit for RULE_SEC, old read counters and signatures."""
    s['blocks'] = {k: v for k, v in s['blocks'].items() if v['until'] > now}
    s['tarpit'] = {k: v for k, v in s['tarpit'].items() if v > now}
    s['rules'] = {k: v for k, v in s['rules'].items() if now - v['last'] < RULE_SEC}
    s['reads'] = {k: v for k, v in s['reads'].items() if now - v['t0'] < 120}
    s['sigs'] = {k: v for k, v in s['sigs'].items() if now - v['at'] < 86400}
    s['uaHits'] = {k: v for k, v in s['uaHits'].items() if now - v['at'] < RULE_SEC}
    if len(s['rules']) > RULES_MAX:
        for k in sorted(s['rules'], key=lambda k: s['rules'][k]['last'])[:len(s['rules']) - RULES_MAX]:
            s['rules'].pop(k)


def check(s, ip, ua, method, path, now=None, internal=False):
    """Before a request → ('block', why) · ('honeypot', None) · ('tarpit', seconds) · None. Learns as it goes."""
    now = time.time() if now is None else now
    if internal:
        return None
    fp = fingerprint(ip, ua); uk = ua_key(ua)
    b = s['blocks'].get(fp)
    if b and b['until'] > now:
        return 'block', b['why']
    r = s['rules'].get(uk)
    if r and ua:
        r.update(hits=r['hits'] + 1, last=now)
        return 'block', r['why']
    if honeypot(path):
        _block(s, fp, now, f'probed a decoy ({path[:60]})')
        _incident(s, 'honeypot', fp, ip, ua, path, now, 'blocked')
        u = s['uaHits'].setdefault(uk, {'ips': [], 'at': now, 'ua': (ua or '')[:160]})
        if ip not in u['ips']:
            u['ips'] = (u['ips'] + [ip])[-20:]
        u['at'] = now
        if ua and not browserish(ua) and len(u['ips']) >= SHARED_HITS and uk not in s['rules']:   # 🧠 learned: one TOOL behind many IPs (never a browser string)
            s['rules'][uk] = {'ua': (ua or '')[:160], 'why': f'a scanner seen from {len(u["ips"])} IPs', 'hits': 0, 'at': now, 'last': now}
        return 'honeypot', None
    if method == 'GET':
        rd = s['reads'].get(fp)
        if not rd or now - rd['t0'] > 60:
            rd = s['reads'][fp] = {'t0': now, 'n': 0, 'paths': []}
        rd['n'] += 1
        if len(rd['paths']) < SCRAPE_PATHS + 1 and path not in rd['paths']:
            rd['paths'].append(path[:80])
        if rd['n'] > SCRAPE_PER_MIN and len(rd['paths']) > SCRAPE_PATHS and s['tarpit'].get(fp, 0) <= now:
            s['tarpit'][fp] = now + TARPIT_SEC
            _incident(s, 'scraper', fp, ip, ua, path, now, 'tarpit')
    if s['tarpit'].get(fp, 0) > now:
        return 'tarpit', TARPIT_S
    return None


def seen_sig(s, sig, ip, ua, path='', now=None):
    """An HQ signature seen again: from the SAME fingerprint = fine; from a NEW one = a replay (flag + tarpit). → True if a replay."""
    now = time.time() if now is None else now
    if not sig:
        return False
    k = hashlib.sha256(sig.encode()).hexdigest()[:20]; fp = fingerprint(ip, ua)
    v = s['sigs'].get(k)
    if not v:
        s['sigs'][k] = {'fp': fp, 'at': now}
        return False
    if v['fp'] == fp:
        v['at'] = now
        return False
    s['tarpit'][fp] = now + TARPIT_SEC
    _incident(s, 'replay', fp, ip, ua, path, now, 'tarpit + flagged')
    return True


def lift(s, fp=None, ua=None):
    """The owner lifts a block or a learned rule."""
    if fp:
        s['blocks'].pop(fp, None); s['tarpit'].pop(fp, None)
    if ua:
        s['rules'].pop(ua, None)


def report(inc):
    """Plain evidence for an abuse contact. FEELESS reports — it never attacks back."""
    rows = '\n'.join(f"  {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))} UTC  {p}" for t, p in inc.get('evidence') or [])
    return (f"Abuse report — {inc['kind']}\nSource IP: {inc['ip']}\nUser-agent: {inc['ua'] or '(none)'}\nRequests: {inc['n']} between "
            f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(inc['first']))} and {time.strftime('%Y-%m-%d %H:%M', time.gmtime(inc['last']))} UTC\n"
            f"What we did: {inc.get('action')} (no counter-action).\nEvidence:\n{rows}\n")


def view(s, now=None):
    now = time.time() if now is None else now
    prune(s, now)
    return {'blocks': [{'fp': k, **v, 'left': int(v['until'] - now)} for k, v in sorted(s['blocks'].items(), key=lambda kv: -kv[1]['at'])][:60],
            'rules': [{'ua': k, **v} for k, v in sorted(s['rules'].items(), key=lambda kv: -kv[1]['hits'])],
            'tarpit': len(s['tarpit']), 'incidents': [{**x, 'report': report(x)} for x in s['incidents'][-40:][::-1]],
            'honeypots': list(HONEYPOTS), 'limits': {'blockH': BLOCK_SEC // 3600, 'scrapePerMin': SCRAPE_PER_MIN, 'sharedHits': SHARED_HITS}}

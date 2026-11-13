"""SEC-1 War Room: a read model over defence.py for one owner-only security dashboard. Pure + tested.

It never contacts an attacker, runs code elsewhere, or sends traffic out. It only organises what FEELESS already observes on its own server:
  - FEED: probes / blocks / decoy hits / tarpits / replays / hardening moves as one event ring, plus per-hour counts for the timeline.
  - DECOYS: a decoy path returns a static fake page (a login form, a fake config, a fake export) instead of a bare 404, and the request
    is recorded (method, path, query, a short header set, body <= 4 KB) so the owner can study it. Slow responses are capped in count + time.
  - CANARIES: each fake page carries a unique token (a plain tracking URL and fake key strings). If that URL is later requested, or a fake
    key is presented to our API, we note it with the caller's IP / UA. The token is just a string; it executes nothing anywhere.
  - TRACE: summarises a wallet's recent outbound transfers (from read-only RPC the caller supplies) and builds a plain-text evidence pack
    for an exchange compliance desk or IC3.
  - HARDEN: on a pattern (many fingerprints from one /24 into decoys; an HQ signature reused from a different device; a fake key presented),
    record a defensive move (ban the subnet, revoke the session, block the fingerprint). The move is data the service acts on.
"""
import hashlib
import ipaddress
import re
import secrets
import time

EVENTS_MAX, CAPTURES_MAX, CANARIES_MAX, HITS_MAX, REPORTS_MAX, MOVES_MAX = 600, 120, 400, 200, 200, 200
BODY_MAX = 4096
NET_FPS, NET_WIN, NET_BAN = 3, 3600, 7 * 86400
SIG_REVOKE_S = 2 * 86400
CANARY_PATH = '/api/reputation/c/'
_TOK = re.compile(r'[0-9a-f]{32}')
KEEP_HEADERS = ('user-agent', 'accept', 'accept-language', 'referer', 'origin', 'content-type', 'content-length', 'x-forwarded-for', 'host',
                'authorization', 'x-api-key', 'cookie')
PAGE_KIND = {'/wp-login.php': 'panel', '/wp-admin': 'panel', '/phpmyadmin': 'panel', '/admin.php': 'panel', '/.env': 'env',
             '/.aws/credentials': 'env', '/config.json': 'env', '/actuator/env': 'env', '/admin/export-keys': 'keys',
             '/admin/wallet-backup': 'keys', '/private-key': 'keys'}


def new_state():
    return {'seq': 0, 'events': [], 'captures': [], 'canaries': {}, 'hits': [], 'nets': {}, 'netSeen': {}, 'sigs': {}, 'revoked': {},
            'reports': [], 'moves': []}


def net_of(ip):
    """The /24 (IPv4) or /48 (IPv6) a source address sits in; None for an unparseable value."""
    try:
        a = ipaddress.ip_address(str(ip))
    except ValueError:
        return None
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return str(ipaddress.ip_network(f'{a}/{24 if a.version == 4 else 48}', strict=False))


def log(s, kind, ip='', ua='', path='', method='', action='', detail='', now=None):
    """Append one feed event. kind: probe/block/decoy/tarpit/replay/canary/canary-key/harden/guard/report."""
    now = time.time() if now is None else now
    s['seq'] += 1
    ev = {'seq': s['seq'], 'at': round(now, 2), 'kind': kind, 'ip': str(ip)[:64], 'net': net_of(ip), 'ua': (ua or '')[:160],
          'path': (path or '')[:160], 'method': (method or '')[:8], 'action': (action or '')[:80], 'detail': (detail or '')[:240]}
    s['events'].append(ev)
    del s['events'][:-EVENTS_MAX]
    return ev


def since(s, seq):
    return [e for e in s['events'] if e['seq'] > int(seq or 0)]


def hourly(s, now=None, hours=24):
    """Per-hour event counts by kind over the last `hours` hours (the timeline strip)."""
    now = time.time() if now is None else now
    top = int(now // 3600) * 3600
    rows = {top - 3600 * i: {'h': top - 3600 * i} for i in range(hours)}
    for e in s['events']:
        h = int(e['at'] // 3600) * 3600
        if h in rows:
            rows[h][e['kind']] = rows[h].get(e['kind'], 0) + 1
    return [rows[k] for k in sorted(rows)]


def capture(s, ip, ua, method, path, query='', headers=None, body='', now=None):
    """Record a decoy request for study. Returns the capture row. Headers are filtered to a known set; body is truncated."""
    now = time.time() if now is None else now
    hd = {k.lower(): str(v)[:300] for k, v in (headers or {}).items() if k.lower() in KEEP_HEADERS}
    row = {'at': round(now, 2), 'ip': str(ip)[:64], 'net': net_of(ip), 'ua': (ua or '')[:200], 'method': (method or '')[:8],
           'path': (path or '')[:200], 'query': (query or '')[:300], 'headers': hd, 'body': (body or '')[:BODY_MAX]}
    s['captures'].append(row)
    del s['captures'][:-CAPTURES_MAX]
    log(s, 'decoy', ip, ua, path, method, 'served a decoy + captured', f'{len(body or "")} byte body', now)
    return row


def mint_canary(s, origin='decoy', note='', now=None):
    """Create a canary token: a tracking URL + a fake key string planted in a decoy. Returns (token, url, fake_key)."""
    now = time.time() if now is None else now
    tok = secrets.token_hex(16)
    fake_key = 'sk_live_' + secrets.token_hex(20)
    s['canaries'][tok] = {'tok': tok, 'origin': origin, 'note': (note or '')[:120], 'at': round(now, 2), 'opens': 0, 'keyUses': 0, 'fakeKey': fake_key}
    if len(s['canaries']) > CANARIES_MAX:
        for k in sorted(s['canaries'], key=lambda k: s['canaries'][k]['at'])[:len(s['canaries']) - CANARIES_MAX]:
            s['canaries'].pop(k)
    return tok, CANARY_PATH + tok, fake_key


def canary_open(s, tok, ip, ua, headers=None, now=None):
    """Someone requested a canary URL. Log the opener. Returns the canary row, or None if the token is unknown."""
    now = time.time() if now is None else now
    c = s['canaries'].get(tok)
    if not c:
        return None
    c['opens'] += 1
    c['lastAt'] = round(now, 2)
    hd = {k.lower(): str(v)[:200] for k, v in (headers or {}).items() if k.lower() in ('referer', 'accept-language', 'user-agent')}
    hit = {'at': round(now, 2), 'tok': tok, 'origin': c['origin'], 'ip': str(ip)[:64], 'net': net_of(ip), 'ua': (ua or '')[:200], 'ref': hd.get('referer', ''), 'lang': hd.get('accept-language', '')}
    s['hits'].append(hit)
    del s['hits'][:-HITS_MAX]
    log(s, 'canary', ip, ua, CANARY_PATH + tok, 'GET', 'canary opened', f'origin {c["origin"]}', now)
    return hit


def canary_key_hit(s, token_text, ip, ua, path='', now=None):
    """A fake key string from a decoy was presented to our API: strong signal the decoy dump was used. Returns the canary, or None."""
    now = time.time() if now is None else now
    for tok, c in s['canaries'].items():
        fk = c.get('fakeKey') or ''
        if fk and fk in str(token_text or ''):
            c['keyUses'] = c.get('keyUses', 0) + 1
            c['lastAt'] = round(now, 2)
            log(s, 'canary-key', ip, ua, path, '', 'a planted fake key was used against us', f'token {tok}', now)
            return c
    return None


def note_net(s, ip, fp, now=None):
    """A fingerprint hit a decoy from this subnet. Returns a harden move dict when the subnet crosses NET_FPS in NET_WIN, else None."""
    now = time.time() if now is None else now
    net = net_of(ip)
    if not net:
        return None
    seen = s['netSeen'].setdefault(net, {'fps': {}, 'at': now})
    seen['fps'] = {f: t for f, t in seen['fps'].items() if now - t < NET_WIN}
    seen['fps'][fp] = now
    seen['at'] = now
    if len(seen['fps']) >= NET_FPS and net not in s['nets']:
        s['nets'][net] = {'net': net, 'until': now + NET_BAN, 'at': now, 'fps': len(seen['fps']), 'why': f'{len(seen["fps"])} scanners from one subnet probed decoys'}
        m = {'kind': 'ban-net', 'net': net, 'at': round(now, 2), 'why': s['nets'][net]['why']}
        s['moves'].append(m); del s['moves'][:-MOVES_MAX]
        log(s, 'harden', ip, '', '', '', 'banned a subnet', s['nets'][net]['why'], now)
        return m
    return None


def net_banned(s, ip, now=None):
    now = time.time() if now is None else now
    n = s['nets'].get(net_of(ip))
    return bool(n and n['until'] > now)


def note_sig(s, sig, ip, ua, now=None):
    """Track an HQ signature's device (ua). Reused from a DIFFERENT device -> a revoke move (owner re-signs). Returns the move, or None."""
    now = time.time() if now is None else now
    if not sig:
        return None
    k = hashlib.sha256(sig.encode()).hexdigest()[:20]
    dev = hashlib.sha256((ua or '').encode()).hexdigest()[:12]
    v = s['sigs'].get(k)
    if not v:
        s['sigs'][k] = {'dev': dev, 'ip': str(ip)[:64], 'at': now}
        return None
    v['at'] = now
    if v['dev'] != dev and k not in s['revoked']:
        s['revoked'][k] = {'until': now + SIG_REVOKE_S, 'at': now, 'why': 'the session signature appeared from a second device'}
        m = {'kind': 'revoke-session', 'at': round(now, 2), 'why': s['revoked'][k]['why']}
        s['moves'].append(m); del s['moves'][:-MOVES_MAX]
        log(s, 'harden', ip, ua, '', '', 'revoked a reused session', s['revoked'][k]['why'], now)
        return m
    return None


def sig_revoked(s, sig, now=None):
    now = time.time() if now is None else now
    if not sig:
        return False
    r = s['revoked'].get(hashlib.sha256(sig.encode()).hexdigest()[:20])
    return bool(r and r['until'] > now)


def add_report(s, wallet='', url='', detail='', reward='', now=None):
    """An inbound responsible-disclosure report (owner triages). Sanitised + capped; guard rate-limits upstream."""
    now = time.time() if now is None else now
    r = {'at': round(now, 2), 'wallet': str(wallet or '')[:64], 'url': str(url or '')[:300], 'detail': str(detail or '')[:2000],
         'reward': str(reward or '')[:40], 'state': 'new'}
    s['reports'].append(r); del s['reports'][:-REPORTS_MAX]
    log(s, 'report', '', '', '', '', 'bounty report filed', r['wallet'] or r['url'], now)
    return r


def trace_summary(transfers, suspect):
    """Summarise read-only RPC transfers (list of {sig, from, to, amount, token, at}) for a suspect wallet: outbound hops + counterparties."""
    out = [t for t in (transfers or []) if str(t.get('from')) == str(suspect)]
    byto = {}
    for t in out:
        to = str(t.get('to') or '?')
        d = byto.setdefault(to, {'to': to, 'n': 0, 'amount': 0.0, 'tokens': set()})
        d['n'] += 1
        try:
            d['amount'] += float(t.get('amount') or 0)
        except (TypeError, ValueError):
            pass
        if t.get('token'):
            d['tokens'].add(str(t['token'])[:12])
    hops = sorted(({'to': d['to'], 'n': d['n'], 'amount': round(d['amount'], 6), 'tokens': sorted(d['tokens'])} for d in byto.values()), key=lambda d: -d['amount'])
    return {'suspect': str(suspect), 'outCount': len(out), 'counterparties': len(byto), 'hops': hops[:40]}


def evidence_pack(s, suspect='', trace=None, now=None):
    """Plain-text evidence pack for an exchange compliance desk / IC3. FEELESS reports; it never acts against the attacker."""
    now = time.time() if now is None else now
    L = [f"FEELESS security evidence pack  ({time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))} UTC)", '']
    recent = s['events'][-40:]
    L.append(f"Observed events (last {len(recent)}):")
    for e in recent:
        L.append(f"  {time.strftime('%Y-%m-%d %H:%M', time.gmtime(e['at']))}  {e['kind']:10} {e['ip']:>15}  {e['method']:4} {e['path']}  {e['action']}")
    if s['captures']:
        L += ['', f"Captured decoy requests: {len(s['captures'])} (payloads stored for study)."]
    if s['hits']:
        L += ['', 'Canary openers (they opened a planted token -> their real IP/UA):']
        for h in s['hits'][-20:]:
            L.append(f"  {time.strftime('%Y-%m-%d %H:%M', time.gmtime(h['at']))}  {h['ip']:>15}  {h['ua'][:80]}")
    if suspect and trace:
        L += ['', f"On-chain trace of suspect {suspect}: {trace.get('outCount', 0)} outbound transfers to {trace.get('counterparties', 0)} counterparties."]
        for hop in (trace.get('hops') or [])[:20]:
            L.append(f"  -> {hop['to']}  {hop['amount']} ({hop['n']} transfers)")
    L += ['', 'All data was observed on FEELESS infrastructure. Requesting: flag/freeze on cash-out and investigation. No counter-action was taken.']
    return '\n'.join(L)


def prune(s, now=None):
    now = time.time() if now is None else now
    s['nets'] = {k: v for k, v in s['nets'].items() if v['until'] > now}
    s['revoked'] = {k: v for k, v in s['revoked'].items() if v['until'] > now}
    s['netSeen'] = {k: v for k, v in s['netSeen'].items() if now - v['at'] < NET_WIN}
    s['sigs'] = {k: v for k, v in s['sigs'].items() if now - v['at'] < 86400}


def view(s, now=None):
    now = time.time() if now is None else now
    prune(s, now)
    kinds = {}
    for e in s['events']:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    return {
        'at': round(now, 2), 'seq': s['seq'],
        'counts': {'events': len(s['events']), 'captures': len(s['captures']), 'canaries': len(s['canaries']),
                   'opens': sum(c.get('opens', 0) for c in s['canaries'].values()), 'keyUses': sum(c.get('keyUses', 0) for c in s['canaries'].values()),
                   'nets': len(s['nets']), 'revoked': len(s['revoked']), 'reports': len(s['reports']), 'byKind': kinds},
        'feed': s['events'][-80:][::-1],
        'timeline': hourly(s, now),
        'captures': [{k: v for k, v in c.items() if k != 'body'} | {'bodyLen': len(c.get('body') or '')} for c in s['captures'][-40:][::-1]],
        'canaries': [{k: v for k, v in c.items() if k != 'fakeKey'} for c in sorted(s['canaries'].values(), key=lambda c: -(c.get('opens', 0) + c.get('keyUses', 0)))[:30]],
        'hits': s['hits'][-40:][::-1],
        'nets': [dict(v, left=int(v['until'] - now)) for v in sorted(s['nets'].values(), key=lambda v: -v['at'])][:40],
        'moves': s['moves'][-40:][::-1],
        'reports': s['reports'][-40:][::-1],
    }


def decoy_page(kind, canary_url, fake_key):
    """A static fake response for a decoy path, with a canary URL + fake key planted in it. Pure text; runs nothing anywhere."""
    beacon = f'<img src="{canary_url}" width="1" height="1" alt="">'
    if kind == 'panel':
        return ('text/html', f'<!doctype html><title>Admin</title><form method="post">'
                f'<input name="user"><input name="pass" type="password"><button>Sign in</button></form>'
                f'<!-- internal: {canary_url} -->{beacon}')
    if kind == 'env':
        return ('text/plain', f'# config\nAPP_ENV=production\nAPI_KEY={fake_key}\nADMIN_URL={canary_url}\nDB_PASSWORD={fake_key[:24]}\n')
    if kind == 'keys':
        return ('application/json', '{"keys":[{"name":"admin","secret":"%s"}],"backup":"%s"}' % (fake_key, canary_url))
    return ('text/plain', 'Not Found')


def page_kind(path):
    p = (path or '').rstrip('/').lower()
    for suffix, kind in PAGE_KIND.items():
        if p.endswith(suffix):
            return kind
    return None

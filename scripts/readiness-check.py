#!/usr/bin/env python3
"""✅ The FREE readiness check (RULINGS: "finish the whole build order, then run the free readiness check"). Read-only, no money, no paid
model: every ask goes to the owner's own LM Studio. Prints one ✅ / ❌ / ⏭ line per piece and exits 1 when any ❌.

  .venv/bin/python scripts/readiness-check.py

  · services up (5001 server · 5077 reputation · 5088 FeeCat · 5099 candles · 51367 the site)
  · OSSY (this Mac) and G4 (the desktop, LAN) each answer one basic ask; ZED's Gemma is optional (⏭ when absent — COL-20)
  · FeeCat AI's public brain answers and never says OSSY / G4 / ZED to visitors
  · each proof type's record (missions per $ by kind) reads, and the daily record check holds
  · a PoC picture serves from the site's own origin (so the playground can edit and save it)
Keys are read from backend/.env and never printed. G4 needs the LAN: from Claude's shell it says ⏭ — run this from your own Terminal."""
import json
import re
import socket
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAD = []


def env():
    out = {}
    p = ROOT / 'backend' / '.env'
    for line in (p.read_text().splitlines() if p.exists() else []):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            out[k.strip().removeprefix('export ').strip()] = v.strip().strip('"').strip("'")
    return out


def say(ok, text):
    print(f"  {'✅' if ok is True else '⏭' if ok is None else '❌'} {text}")
    if ok is False:
        BAD.append(text)


def get(url, headers=None, body=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw[:1] in (b'{', b'[') else raw)


def port(p):
    try:
        socket.create_connection(('127.0.0.1', p), timeout=2).close(); return True
    except OSError:
        return False


def mind(name, base, key, want_gemma=False):
    if not base:
        say(False, f'{name}: no LM Studio address in backend/.env'); return
    h = {'Authorization': f'Bearer {key or "lm-studio"}'}
    try:
        _, models = get(f'{base.rstrip("/")}/models', h, timeout=6)
    except OSError as e:
        lan = not base.startswith(('http://127.', 'http://localhost'))
        say(None if lan else False, f'{name}: LM Studio not reachable ({type(e).__name__})' + (' — run this from your own Terminal (LAN)' if lan else ''))
        return
    ids = [m.get('id') for m in models.get('data') or [] if 'embed' not in str(m.get('id'))]
    if want_gemma:
        g = [i for i in ids if 'gemma' in str(i).lower()]
        # owner 2026-11-14 (COL-20 closed): no Gemma needed — an outside judge grades a proof every model judge built, so ZED is optional
        say(True if g else None, f'{name}: ' + (f'Gemma loaded ({g[0]})' if g else 'no Gemma loaded — optional (COL-20: outside judge, no Gemma needed)'))
        return
    if not ids:
        say(False, f'{name}: no chat model loaded'); return
    t0 = time.time()
    try:
        _, j = get(f'{base.rstrip("/")}/chat/completions', h, {'model': ids[0], 'max_tokens': 400, 'temperature': 0,
                   'messages': [{'role': 'user', 'content': 'Reply with exactly one word: READY'}]}, timeout=180)
        text = ((j.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        say('READY' in text.upper(), f'{name}: basic ask answered in {time.time() - t0:.0f}s ({ids[0]})')
    except OSError as e:
        say(False, f'{name}: the ask failed ({type(e).__name__})')


def main():
    e = env()
    print('— Services —')
    for p, what in ((5001, 'server'), (5077, 'reputation'), (5088, 'FeeCat'), (5099, 'candles'), (51367, 'the site')):
        say(port(p), f'{p} {what}')
    print('— The minds (free, your own LM Studio) —')
    mind('OSSY', e.get('LOCAL_LLM_BASE_URL') or 'http://127.0.0.1:1234/v1', e.get('LOCAL_LLM_API_KEY'))
    mind('G4', e.get('LAN_LLM_BASE_URL'), e.get('LAN_LLM_API_KEY'))
    mind('ZED', e.get('ZED_LLM_BASE_URL') or e.get('LOCAL_LLM_BASE_URL') or 'http://127.0.0.1:1234/v1', e.get('ZED_LLM_API_KEY') or e.get('LOCAL_LLM_API_KEY'), want_gemma=True)
    print('— FeeCat AI (public) —')
    try:
        s, j = get('http://127.0.0.1:5088/api/cats/leader')
        leak = re.findall(r'\b(OSSY|G4|ZED|NEXA)\b', json.dumps(j))
        say(s == 200 and not leak, 'leader answers' + (f' but names {sorted(set(leak))} to visitors' if leak else ', speaks as FeeCat AI'))
    except OSError as x:
        say(False, f'leader did not answer ({type(x).__name__})')
    print('— Proof types —')
    try:
        _, v = get('http://127.0.0.1:5088/api/cats/proofs/value')
        kinds = v.get('byKind') or {}
        say(bool(kinds), 'record by kind: ' + ', '.join(f"{k} {x.get('proved', 0)}/{x.get('settled', 0)}" for k, x in sorted(kinds.items())))
        a = v.get('anchor') or {}
        say(a.get('ok') is not False, f"daily record check: {a.get('why') or 'holds'}")
    except OSError as x:
        say(False, f'proof record did not read ({type(x).__name__})')
    print('— PoC media (playground) —')
    media = sorted((ROOT / 'backend' / 'data' / 'media').glob('*/m*.*'), key=lambda f: f.stat().st_mtime)
    if not media:
        say(None, 'no PoC picture or video made yet')
    else:
        f = media[-1]; path = f'/api/cats/media/{f.parent.name}/{f.name}'
        try:
            s, _ = get(f'http://127.0.0.1:51367{path}')
            say(s == 200, f'newest {f.suffix[1:]} serves from the site origin (the playground can edit + save it)')
        except OSError as x:
            say(False, f'newest PoC file did not serve ({type(x).__name__})')
    print('\n' + ('✅ READY — free checks pass.' if not BAD else f'❌ {len(BAD)} to fix: ' + ' · '.join(BAD)))
    return 1 if BAD else 0


if __name__ == '__main__':
    sys.exit(main())

"""🧠 NEXA'S DISCOVERY BASE (owner, 2026-10-20: "a huge discovery database that only holds KBs but contains massive vital data, so she can retain
and not search the internet for small vital info — she may still DYOR on coins"). Pure. Short facts (≤ FACT_LEN chars) filed by category and key,
each category capped, the least used + oldest fact out first — the whole base stays a few hundred KB however long she runs.
  categories: coin · creator · wallet · narrative · site · x · rug · lesson · fact
  in:  her own answers (`remember`: [[cat, key, fact]]) + what FEELESS already knows (`auto`: coins she read, their crews, how her calls ended)
  out: `recall(kb, keys, words)` = the lines that fit THIS read (her packet's coins / creators / narratives first) → she searches the web only
       for coins it knows nothing fresh about (`need_web`)."""
import re
import time

CAPS = {'coin': 600, 'creator': 400, 'wallet': 300, 'narrative': 150, 'site': 250, 'x': 250, 'rug': 400, 'lesson': 250, 'fact': 400}
FACT_LEN = 160
KEY_LEN = 48
FRESH_SEC = 6 * 3600   # a coin fact younger than this = no web search needed for it


def _clean(t, n):
    return ' '.join(re.sub(r'[\x00-\x1f]', ' ', str(t or '')).split())[:n]


def put(kb, cat, key, fact, now=None, src='nexa'):
    """File one fact (dedupe by key: newer text wins, hits kept). → the base (same object)."""
    now = time.time() if now is None else now
    if cat not in CAPS:
        return kb
    key, fact = _clean(key, KEY_LEN).lower(), _clean(fact, FACT_LEN)
    if not key or not fact:
        return kb
    box = kb.setdefault(cat, {})
    old = box.get(key) or {}
    box[key] = {'f': fact, 'at': round(now), 'hits': int(old.get('hits') or 0), 'src': src}
    if len(box) > CAPS[cat]:
        for k in sorted(box, key=lambda k: (box[k].get('hits') or 0, box[k].get('at') or 0))[:len(box) - CAPS[cat]]:
            box.pop(k, None)
    return kb


def remember(kb, rows, now=None):
    """Her answer's `remember` list → filed (≤ 6 a read, unknown categories dropped)."""
    for r in (rows or [])[:6]:
        if isinstance(r, (list, tuple)) and len(r) == 3:
            put(kb, str(r[0]).lower(), r[1], r[2], now, 'nexa')
        elif isinstance(r, dict):
            put(kb, str(r.get('cat') or '').lower(), r.get('key'), r.get('fact'), now, 'nexa')
    return kb


def auto(kb, coins, now=None):
    """What FEELESS already knows about the coins she reads → filed (src 'feeless'): ticker · cap · age · setups / read · creator crew."""
    for c in coins or []:
        sym, mint = c.get('symbol'), c.get('mint')
        if not mint:
            continue
        bits = [f"${sym}" if sym else None, f"cap ${float(c['cap']) / 1000:.0f}K" if c.get('cap') else None,
                f"{float(c['ageMin']):.0f}m old" if c.get('ageMin') is not None else None,
                ('setups ' + '/'.join(c['setups'])) if c.get('setups') else None, c.get('read') if isinstance(c.get('read'), str) else None,
                f"crew {c['crew']}" if c.get('crew') else None]
        put(kb, 'coin', mint, ' · '.join(b for b in bits if b), now, 'feeless')
        if sym:
            put(kb, 'coin', f"${sym}", f"{sym} = {mint}", now, 'feeless')
        if c.get('creator') and c.get('crew'):
            put(kb, 'creator', c['creator'], f"crew {c['crew']} (seen on ${sym})", now, 'feeless')
    return kb


def rug(kb, mint, sym, pct, now=None):
    """A coin she called that fell ≥ 50% in the hour → a rug fact (it never gets re-learned from the web)."""
    if pct is not None and float(pct) <= -50:
        put(kb, 'rug', mint, f"${sym or '?'} fell {float(pct):.0f}% within an hour of being read", now, 'feeless')
    return kb


def recall(kb, keys=(), words=(), n=24, now=None):
    """→ up to n lines that fit: exact keys first (her packet's mints / $tickers / creators), then facts sharing a word, then her lessons.
    Each recalled fact gets a hit (the most useful survive eviction)."""
    out, seen = [], set()

    def take(cat, k):
        f = (kb.get(cat) or {}).get(k)
        if f and (cat, k) not in seen and len(out) < n:
            seen.add((cat, k))
            f['hits'] = int(f.get('hits') or 0) + 1
            out.append(f"[{cat}] {k[:14]}: {f['f']}")
    for k in keys or ():
        k = str(k or '').lower()
        for cat in ('coin', 'rug', 'creator', 'wallet', 'site', 'x'):
            take(cat, k)
    ws = {w.lower() for w in words or () if len(str(w)) >= 3}
    if ws:
        for cat in ('narrative', 'fact', 'site', 'x'):
            for k, f in (kb.get(cat) or {}).items():
                if ws & set(re.findall(r'[a-z0-9$]{3,}', (k + ' ' + f['f']).lower())):
                    take(cat, k)
    for k in sorted(kb.get('lesson') or {}, key=lambda k: -(kb['lesson'][k].get('at') or 0))[:5]:
        take('lesson', k)
    return out


def need_web(kb, mints, now=None):
    """The mints with NO fresh coin fact — the only ones worth a web search this read."""
    now = time.time() if now is None else now
    box = kb.get('coin') or {}
    return [m for m in mints or () if m and not (box.get(str(m).lower()) and now - (box[str(m).lower()].get('at') or 0) < FRESH_SEC)]


def stats(kb):
    import json
    return {'n': {c: len(kb.get(c) or {}) for c in CAPS}, 'total': sum(len(kb.get(c) or {}) for c in CAPS), 'kb': round(len(json.dumps(kb)) / 1024, 1),
            'caps': dict(CAPS)}


def latest(kb, n=30):
    rows = [(c, k, f) for c in CAPS for k, f in (kb.get(c) or {}).items()]
    return [{'cat': c, 'key': k, 'fact': f['f'], 'at': f.get('at'), 'hits': f.get('hits'), 'src': f.get('src')} for c, k, f in sorted(rows, key=lambda r: -(r[2].get('at') or 0))[:n]]

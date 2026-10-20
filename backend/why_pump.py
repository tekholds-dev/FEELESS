"""❓ WHY DID IT PUMP? (owner, 2026-10-19: "can this be in rep and bring the words to life"). Pure. A pasted coin → what moved it, with sources.
The service gathers: FEELESS's own read of the coin (coin-read: moves, volume, buyers, callers, socials, holders), web + X search results
for the CA / ticker, and the text of the two best pages. This module turns that into (1) the ENGINE's own drivers — every one a number
we measured, never a guess — and (2) the packet + prompt a model reads to write the story. A model line that names no source is dropped.
A read, never advice."""
import re

WHY_ASK = (
    "You are FEELESS's pump detective. The CASE has the coin's MEASURED numbers (NUMBERS), the drivers the engine already proved from those "
    "numbers (ENGINE), Pump callers, and web / X results with their URLs (WEB, PAGES). Say WHY the price moved. Answer ONLY JSON: "
    '{"headline": "one punchy line, ≤ 90 chars, with the main number", "drivers": [{"why": "one sentence", "source": "a URL from WEB / PAGES, or ENGINE"}], '
    '"verdict": "ORGANIC | NEWS | CALLERS | WHALES | BOTTED | UNCLEAR", "risk": "one sentence on what could undo it"}. '
    "Up to 4 drivers, strongest first. Every driver cites a source from the CASE — never invent a URL, a tweet or a number. "
    "If the web says nothing about it, say so and lean on ENGINE. Trench voice, no fluff."
)
VERDICTS = ('ORGANIC', 'NEWS', 'CALLERS', 'WHALES', 'BOTTED', 'UNCLEAR')


def _f(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _pct(v):
    return f"{v:+.0f}%" if abs(v) < 1000 else f"{v / 100 + 1:.1f}x"


def _usd(v):
    v = abs(v)
    return f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1e3:.1f}K" if v >= 1e3 else f"${v:.0f}"


def numbers(read):
    """The coin-read answer → the flat numbers the page + the model see (missing = not there, never 0)."""
    r = (read or {}).get('row') or {}
    v = (read or {}).get('vital') or {}
    pick = lambda *ks: next((x for x in (_f(r.get(k)) for k in ks) if x is not None), None)
    out = {'symbol': r.get('symbol') or (read or {}).get('symbol'), 'cap': pick('mcap', 'cap', 'marketCap'), 'liq': pick('liq', 'liquidityUsd'),
           'chg5m': pick('chg5m'), 'chg1h': pick('chg1h'), 'chg6h': pick('chg6h'), 'chg24h': pick('chg24h'),
           'vol5m': pick('vol5m'), 'vol1h': pick('vol1h'), 'vol24h': pick('vol24h'), 'buyShare': pick('buyShare'), 'txns1h': pick('txns1h'),
           'ageH': pick('ageH'), 'holders': pick('holders'), 'top10': pick('top10', 'top10Pct'), 'organic': _f(v.get('organicPct')),
           'grade': v.get('grade'), 'ptrend': r.get('pumpTrend') or r.get('ptrend')}
    pc = (read or {}).get('pc') or r.get('pc') or {}
    out['callers'] = int(pc.get('n') or pc.get('callers') or 0) if isinstance(pc, dict) else 0
    out['pros'] = int(pc.get('pros') or 0) if isinstance(pc, dict) else 0
    tape = (read or {}).get('tape') or {}
    out['tape'] = tape.get('read') if isinstance(tape, dict) else None
    return {k: v for k, v in out.items() if v is not None}


def from_pair(pair, n=None, now=None):
    """A DexScreener-shaped pair (DexScreener or Jupiter) fills what coin-read did not have — never overwrites a reading we own."""
    import time
    p, out = pair or {}, dict(n or {})
    pc, vol, tx = p.get('priceChange') or {}, p.get('volume') or {}, p.get('txns') or {}
    h1 = tx.get('h1') or {}
    b, s_ = _f(h1.get('buys'), 0), _f(h1.get('sells'), 0)
    created = _f(p.get('pairCreatedAt'))
    fill = {'symbol': (p.get('baseToken') or {}).get('symbol'), 'cap': _f(p.get('marketCap')) or _f(p.get('fdv')), 'liq': _f((p.get('liquidity') or {}).get('usd')),
            'chg5m': _f(pc.get('m5')), 'chg1h': _f(pc.get('h1')), 'chg6h': _f(pc.get('h6')), 'chg24h': _f(pc.get('h24')),
            'vol5m': _f(vol.get('m5')), 'vol1h': _f(vol.get('h1')), 'vol24h': _f(vol.get('h24')),
            'buyShare': round(100 * b / (b + s_), 1) if b + s_ > 0 else None, 'txns1h': (b + s_) or None, 'holders': _f(p.get('holders')),
            'ageH': round(((now or time.time()) - created / 1000) / 3600, 2) if created else None, 'img': (p.get('info') or {}).get('imageUrl')}
    for k, v in fill.items():
        if out.get(k) is None and v is not None:
            out[k] = v
    return out


def socials_of(pair):
    """The coin's own links from its pair (site · X · Telegram), http(s) only."""
    inf = (pair or {}).get('info') or {}
    out = {}
    for w in inf.get('websites') or []:
        u = str((w or {}).get('url') or '')
        if u.startswith('http') and 'site' not in out:
            out['site'] = u
    for s in inf.get('socials') or []:
        u, t = str((s or {}).get('url') or ''), str((s or {}).get('type') or '').lower()
        if not u.startswith('http'):
            continue
        if t in ('twitter', 'x') or 'x.com/' in u or 'twitter.com/' in u:
            out.setdefault('x', u)
        elif t == 'telegram' or 't.me/' in u:
            out.setdefault('tg', u)
    return out


def biggest_move(n):
    """The window that moved most, as (label, pct)."""
    best = None
    for k, lbl in (('chg5m', '5 min'), ('chg1h', '1 hour'), ('chg6h', '6 hours'), ('chg24h', '24 hours')):
        v = n.get(k)
        if v is not None and (best is None or abs(v) > abs(best[1])):
            best = (lbl, v)
    return best


def engine_drivers(n):
    """What OUR numbers prove about the move — each a sentence with the number, source ENGINE. Strongest first."""
    out = []
    v1, v24, cap = n.get('vol1h'), n.get('vol24h'), n.get('cap')
    if v1 and v24 and v24 > 0 and v1 / v24 >= 0.25:
        out.append((90, f"{_usd(v1)} traded in the last hour — {v1 / v24 * 100:.0f}% of the whole day's volume, a fresh wave of money"))
    elif v1 and cap and cap > 0 and v1 / cap >= 0.3:
        out.append((80, f"{_usd(v1)} traded in an hour on a {_usd(cap)} cap — the coin turned over {v1 / cap * 100:.0f}% of its value"))
    bs = n.get('buyShare')
    if bs is not None and bs >= 60:
        out.append((70 + (bs - 60), f"{bs:.0f}% of trades are buys — buyers are in control"))
    elif bs is not None and bs <= 40:
        out.append((60, f"only {bs:.0f}% of trades are buys — sellers are taking profit into the move"))
    if n.get('callers', 0) >= 2:
        out.append((75 + 3 * min(n['callers'], 6), f"{n['callers']} Pump callers on it" + (f" ({n['pros']} with a proven record)" if n.get('pros') else '') + " — the crowd was told"))
    if n.get('ptrend'):
        out.append((72, f"on Pump's own trending tab (#{n['ptrend']}) — every Pump visitor sees it" if isinstance(n['ptrend'], (int, float)) else "on Pump's own trending tab"))
    org = n.get('organic')
    if org is not None and org < 5:
        out.append((65, f"only {org:.0f}% of the volume reads organic — much of the move is bots"))
    elif org is not None and org >= 25:
        out.append((55, f"{org:.0f}% organic volume — real wallets, not a bot loop"))
    t10 = n.get('top10')
    if t10 is not None and t10 >= 35:
        out.append((58, f"the top 10 wallets hold {t10:.0f}% — a few hands can move (and dump) it"))
    if n.get('tape') in ('burst', 'climax'):
        out.append((62, 'the live tape shows a buying ' + ('burst' if n['tape'] == 'burst' else 'climax') + ' right now'))
    age = n.get('ageH')
    if age is not None and age < 6:
        out.append((50, f"launched {age * 60:.0f} min ago — a fresh launch running its first wave" if age < 1 else f"launched {age:.1f}h ago — still in its first day"))
    return [{'why': w, 'source': 'ENGINE'} for _s, w in sorted(out, key=lambda t: -t[0])]


def verdict_of(n):
    """The engine's own one-word call when no model answers."""
    if n.get('organic') is not None and n['organic'] < 5:
        return 'BOTTED'
    if n.get('callers', 0) >= 3:
        return 'CALLERS'
    if n.get('top10') is not None and n['top10'] >= 45:
        return 'WHALES'
    if n.get('buyShare') is not None and n['buyShare'] >= 55:
        return 'ORGANIC'
    return 'UNCLEAR'


def headline_of(n):
    b = biggest_move(n)
    sym = f"${n.get('symbol')}" if n.get('symbol') else 'It'
    if not b:
        return f"{sym}: no move on record yet"
    word = 'pumped' if b[1] > 0 else 'dumped'
    v1 = n.get('vol1h')
    return f"{sym} {word} {_pct(b[1])} in {b[0]}" + (f" on {_usd(v1)} of hourly volume" if v1 else '')


def packet(n, drivers, web, pages):
    """What the model reads: the numbers, the engine's proven drivers, web rows (title · url · snippet) and page excerpts (url · text)."""
    return {'NUMBERS': n, 'ENGINE': [d['why'] for d in drivers[:6]],
            'WEB': [{'title': (w.get('title') or '')[:120], 'url': w.get('url'), 'snippet': (w.get('snippet') or '')[:220]} for w in (web or [])[:10]],
            'PAGES': [{'url': u, 'title': (t or '')[:100], 'text': re.sub(r'\s+', ' ', x or '')[:900]} for u, t, x in (pages or [])[:2]]}


def _json(text):
    t = str(text or '')
    a, b = t.find('{'), t.rfind('}')
    if a < 0 or b <= a:
        return None
    import json
    try:
        return json.loads(t[a:b + 1])
    except ValueError:
        return None


def parse(text, urls):
    """The model's answer → {headline, drivers, verdict, risk}; a driver citing a URL that is not in the case becomes ENGINE-less and is dropped."""
    d = _json(text)
    if not isinstance(d, dict):
        return None
    ok = set(urls or ())
    drv = []
    for x in (d.get('drivers') or [])[:4]:
        if not isinstance(x, dict):
            continue
        why, src = ' '.join(str(x.get('why') or '').split())[:240], str(x.get('source') or '').strip()
        if not why:
            continue
        if src != 'ENGINE' and src not in ok:
            continue   # never an invented source
        drv.append({'why': why, 'source': src})
    v = str(d.get('verdict') or '').upper().strip()
    return {'headline': ' '.join(str(d.get('headline') or '').split())[:120] or None, 'drivers': drv,
            'verdict': v if v in VERDICTS else None, 'risk': ' '.join(str(d.get('risk') or '').split())[:200] or None}


def answer(n, engine, model, web):
    """The final card: the model's story when it gave one, else the engine's own — every driver with its source."""
    m = model or {}
    drv = m.get('drivers') or []
    said = ' '.join(d['why'] for d in drv)
    nums = lambda t: set(re.findall(r'\d+(?:\.\d+)?%?', t))
    drv = (drv + [d for d in engine if d['why'] not in said and not (nums(d['why']) & nums(said))])[:5]   # the model restating our number = one driver
    return {'headline': m.get('headline') or headline_of(n), 'verdict': m.get('verdict') or verdict_of(n), 'risk': m.get('risk'),
            'drivers': drv, 'move': biggest_move(n), 'numbers': n,
            'sources': [{'title': w.get('title'), 'url': w.get('url'), 'via': w.get('via')} for w in (web or []) if w.get('url')][:8],
            'by': 'model' if m.get('drivers') or m.get('headline') else 'engine'}

"""🧪 MODEL LAB (owner 2026-11-11: "a full AI and human setup to build / learn how to be a new kind of artificial intel"). Pure.

FEELESS's own model would learn from what the site already keeps, and from nothing else:
  · the Collective stash: every proof an agent filed, with how it really ended (won / lost / flat), or still open,
  · the model-call log: which rented mind did which proof, at what cost and speed, and where it failed,
  · the owner's own grades on open proofs nothing could settle (the HUMAN half: a person decides what good looks like).
It turns them into a live dataset view, clean training rows (wallets, addresses, emails, phones and keys scrubbed) and a review queue.
Nothing here trains a model, spends money or sends anything anywhere: the export is a file for the owner."""
import json
import re
import zlib

KINDS = {'Trades': 'PoW', 'Perps': 'PoP', 'Picks': 'PoB', 'Content': 'PoC', 'Code': 'PoStatic'}   # Snapshots are pictures: evidence, not rows
SETTLED = ('won', 'lost', 'flat')
FIELDS = ('ask', 'topic', 'plan', 'why', 'summary', 'report', 'angle', 'result', 'verdict')
PAIRS_GOAL = 200      # graded right-vs-wrong pairs per proof type before preference training is worth a run (a planning number, not a law)
ROWS_GOAL = 1000      # settled rows per proof type before a fine-tune is worth renting a GPU for
VERDICTS = ('good', 'bad', 'skip')
DUELS = 'Duels'       # ⚔ AGX-4: the owner tapped the better of two minds' answers to one ask — a right-vs-wrong pair by a person's hand

_SCRUB = (
    (re.compile(r'\b0x[a-fA-F0-9]{40}\b'), '[address]'),
    (re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'), '[wallet]'),
    (re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+'), '[email]'),
    (re.compile(r'\b(?:sk|pk|rk|ghp|gho|xox[abp]|key|tok)[-_][A-Za-z0-9_-]{12,}\b', re.I), '[key]'),
    (re.compile(r'\b[a-fA-F0-9]{48,}\b'), '[key]'),
    (re.compile(r'\+\d[\d ()-]{8,}\d\b|\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b'), '[phone]'),   # +44 20 7946 0958 · (555) 123-4567 — never a date
)


def scrub(text):
    """No wallet, address, email, phone or key ever reaches a training row."""
    out = str(text or '')
    for pat, mark in _SCRUB:
        out = pat.sub(mark, out)
    return out


def row_of(item, raw):
    """One training row from a kept proof: what it was asked, what it did, how it really ended. → dict, or None when it has no result yet."""
    kind = KINDS.get(item.get('category'))
    if not kind or item.get('outcome') not in SETTLED:
        return None
    try:
        d = json.loads(zlib.decompress(raw) if raw[:1] == b'x' else raw) if raw else {}
    except (ValueError, zlib.error, TypeError):
        d = {}
    parts = {k: scrub(' '.join(d[k].split()))[:600] for k in FIELDS if isinstance(d, dict) and isinstance(d.get(k), str) and d[k].strip()}
    return {'kind': kind, 'title': scrub(item.get('title'))[:160], **parts, 'source': item.get('source') or '', 'outcome': item['outcome'], 'at': round(item.get('at') or 0)}


def text_of(item, raw):
    """🏗 Everything a kept proof says, as plain text for the owner's own language model (open proofs too: it learns how the agents write,
    not whether they were right — the grades are for the fine-tune rows). Scrubbed the same way; None when it says nothing."""
    kind = KINDS.get(item.get('category'))
    if not kind:
        return None
    try:
        d = json.loads(zlib.decompress(raw) if raw[:1] == b'x' else raw) if raw else {}
    except (ValueError, zlib.error, TypeError):
        d = {}
    body = [f'{k}: {scrub(" ".join(d[k].split()))[:1500]}' for k in FIELDS if isinstance(d, dict) and isinstance(d.get(k), str) and d[k].strip()]
    title = scrub(item.get('title'))[:160]
    if not body and not title:
        return None
    return f"### {kind} · {item.get('outcome') or 'open'} · {title}\n" + '\n'.join(body) + '\n'


def graded_row(item, grade):
    """An open proof the owner graded becomes a row too: the human label stands where the market could not settle it."""
    kind = KINDS.get(item.get('category'))
    if not kind or (grade or {}).get('verdict') not in ('good', 'bad'):
        return None
    return {'kind': kind, 'title': scrub(item.get('title'))[:160], 'source': item.get('source') or '', 'outcome': 'won' if grade['verdict'] == 'good' else 'lost',
            'by': 'owner', 'note': scrub(grade.get('note'))[:300], 'at': round(item.get('at') or 0)}


def duel_row(item, raw):
    """⚔ One duel the owner judged → a preference row (prompt, chosen, rejected), scrubbed. None when it will not open."""
    if item.get('category') != DUELS:
        return None
    try:
        d = json.loads(zlib.decompress(raw) if raw[:1] == b'x' else raw) if raw else {}
    except (ValueError, zlib.error, TypeError):
        return None
    if not isinstance(d, dict) or not all(isinstance(d.get(k), str) and d[k].strip() for k in ('prompt', 'chosen', 'rejected')):
        return None
    return {'kind': 'Duel', 'prompt': scrub(d['prompt'])[:1500], 'chosen': scrub(d['chosen'])[:3000], 'rejected': scrub(d['rejected'])[:3000],
            'chosenModel': str(d.get('chosenModel') or '')[:60], 'rejectedModel': str(d.get('rejectedModel') or '')[:60], 'by': 'owner', 'at': round(item.get('at') or 0)}


def _minds(calls):
    out = {}
    for c in calls or []:
        m = str(c.get('asked') or c.get('model') or '?').split('/')[-1][:40]
        r = out.setdefault(m, {'model': m, 'calls': 0, 'failed': 0, 'usd': 0.0, 'ms': 0, 'local': bool(c.get('local')), 'kinds': {}})
        r['calls'] += 1; r['failed'] += 0 if c.get('ok') else 1; r['usd'] += float(c.get('usd') or 0); r['ms'] += int(c.get('ms') or 0)
        k = str(c.get('kind') or '?'); r['kinds'][k] = r['kinds'].get(k, 0) + 1
    rows = [{**r, 'usd': round(r['usd'], 4), 'avgMs': round(r['ms'] / r['calls']) if r['calls'] else 0, 'failRate': round(r['failed'] / r['calls'], 3) if r['calls'] else 0}
            for r in out.values()]
    for r in rows:
        r.pop('ms')
    return sorted(rows, key=lambda r: -r['calls'])


def summary(items, calls, grades):
    """→ the live dataset: per proof type its settled rows, open ones, owner grades and right-vs-wrong pairs; the rented minds' record; each
    plan step's real state. Numbers only, never a proof's content."""
    kinds = {k: {'kind': k, 'rows': 0, 'won': 0, 'lost': 0, 'flat': 0, 'open': 0, 'graded': 0} for k in KINDS.values()}
    shots = 0; duels = 0
    for it in items or []:
        k = KINDS.get(it.get('category'))
        if it.get('category') == DUELS:
            duels += 1
            continue
        if not k:
            shots += it.get('category') == 'Snapshots'
            continue
        r = kinds[k]; o = it.get('outcome')
        if o in SETTLED:
            r['rows'] += 1; r[o] += 1
        else:
            g = (grades or {}).get(it.get('key'), {}).get('verdict')
            if g in ('good', 'bad'):
                r['graded'] += 1; r['rows'] += 1; r['won' if g == 'good' else 'lost'] += 1
            elif g != 'skip':
                r['open'] += 1
    for r in kinds.values():
        r['pairs'] = min(r['won'], r['lost'])
        r['rowsPct'] = round(min(1.0, r['rows'] / ROWS_GOAL), 3); r['pairsPct'] = round(min(1.0, r['pairs'] / PAIRS_GOAL), 3)
    rows = sum(r['rows'] for r in kinds.values()); pairs = sum(r['pairs'] for r in kinds.values()) + duels; graded = sum(1 for g in (grades or {}).values() if g.get('verdict') in ('good', 'bad'))
    minds = _minds(calls)
    steps = {
        'data': 'have' if rows else 'todo',
        'clean': 'ready' if rows else 'todo',                       # the export below is the clean step, run on demand
        'base': 'todo', 'sft': 'todo',
        'pref': 'have' if pairs else 'todo',
        'eval': 'have' if minds else 'todo',                         # the rented minds' real record is the bar to beat
        'serve': 'todo',
    }
    return {'kinds': list(kinds.values()), 'rows': rows, 'pairs': pairs, 'graded': graded, 'open': sum(r['open'] for r in kinds.values()), 'snapshots': shots, 'duels': duels,
            'minds': minds, 'spentUsd': round(sum(m['usd'] for m in minds), 4), 'steps': steps, 'goals': {'rows': ROWS_GOAL, 'pairs': PAIRS_GOAL}}


def queue(items, grades, limit=8):
    """The human half: open proofs nothing has settled and the owner has not graded, newest first. Titles only."""
    out = []
    for it in items or []:
        if KINDS.get(it.get('category')) and it.get('outcome') not in SETTLED and it.get('key') not in (grades or {}):
            out.append({'key': it['key'], 'kind': KINDS[it['category']], 'title': scrub(it.get('title'))[:160], 'source': it.get('source') or '', 'at': round(it.get('at') or 0)})
            if len(out) >= limit:
                break
    return out


def grade(grades, key, verdict, note, now):
    """→ the grades with this one set. A verdict outside good / bad / skip is refused."""
    if verdict not in VERDICTS:
        raise ValueError('A grade is good, bad or skip.')
    return {**(grades or {}), str(key)[:120]: {'verdict': verdict, 'note': str(note or '')[:300], 'at': round(now)}}


def export_lines(items, read_raw, grades):
    """→ JSONL training rows: every settled proof, then every one the owner graded. `read_raw(key)` opens one kept proof; one that will not
    open still gives its title and result."""
    for it in items or []:
        if it.get('category') == DUELS:
            try:
                r = duel_row(it, read_raw(it['key']) or b'')
            except Exception:   # noqa: BLE001 — a duel that will not open is skipped, never guessed
                r = None
        elif it.get('outcome') in SETTLED:
            try:
                raw = read_raw(it['key']) or b''
            except Exception:   # noqa: BLE001 — a sealed item that will not open still counts by its title
                raw = b''
            r = row_of(it, raw)
        else:
            r = graded_row(it, (grades or {}).get(it.get('key')))
        if r:
            yield json.dumps(r, ensure_ascii=False) + '\n'

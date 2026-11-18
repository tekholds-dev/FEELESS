"""💵 The owner's day cap (owner 2026-11-17: "DO WHATEVER EXCEPT USE MY MONEY TO WASTE ON BULLSHIT" / "assure real money readyness").

One cap per owner, across all of his agents: every paid image, video, swap and page-build call on HIS keys is checked against what his
agents already spent today (the receipt ledger, data/model_receipts.jsonl: provider-reported where the provider says it, list price
otherwise) plus what is still making. Over the cap → it refuses before anything is sent, in plain words. FEELESS's own key has its own
cap (media_gen.HOUSE_DAILY_USD) and is not counted here. Pure, except `read_rows` / the caps file helpers.
"""
import json
import time

DAILY_CAP_USD = 10.0      # until the owner names his own (1 to 500 dollars a day)
CAP_MIN, CAP_MAX = 1.0, 500.0
HOUSE = 'FEELESS key'
SHOW_ROWS = 40


class OverCap(Exception):
    """A paid call refused before it was sent: the day's cap is reached."""


def day_start(now=None):
    """Local midnight, as a unix time."""
    t = time.localtime(now or time.time())
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def read_rows(path, since):
    """The ledger rows written since `since` (a bad line is skipped)."""
    out = []
    try:
        with open(path) as f_:
            for line in f_:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and float(r.get('at') or 0) >= since:
                    out.append(r)
    except OSError:
        pass
    return out


def own_rows(rows, cat_ids, since):
    """His agents' paid rows since `since`, on his own keys (FEELESS's key is not his money)."""
    ids = set(cat_ids or ())
    return [r for r in rows or () if r.get('cat') in ids and float(r.get('at') or 0) >= since and r.get('funding') != HOUSE and float(r.get('usd') or 0) > 0]


def spent(rows, cat_ids, since):
    return round(sum(float(r.get('usd') or 0) for r in own_rows(rows, cat_ids, since)), 4)


def clean_cap(v):
    """→ the cap as a float, or ValueError in plain words."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError('Say the day cap in dollars, e.g. 10.')
    if not CAP_MIN <= v <= CAP_MAX:
        raise ValueError(f'The day cap goes from ${CAP_MIN:.0f} to ${CAP_MAX:.0f}.')
    return round(v, 2)


def check(done_usd, making_usd, est_usd, cap):
    """Raises OverCap when this call would take the day past the cap. `est_usd` 0 = a call whose price is only known after (a model
    reply): it runs while anything is left."""
    used = float(done_usd or 0) + float(making_usd or 0); est = max(0.0, float(est_usd or 0)); cap = float(cap)
    if used >= cap - 1e-9 or (est and used + est > cap + 1e-9):
        left = max(0.0, cap - used)
        raise OverCap(f'Stopped before it cost anything: your ${cap:.2f} day cap. Today ${used:.2f} is spent or making'
                      + (f', this one is about ${est:.2f} and only ${left:.2f} is left' if est and left else '')
                      + '. Raise the day cap, or try tomorrow.')


def label(r):
    m = str(r.get('model') or '')
    return m.split('/')[-1][:40] or str(r.get('provider') or 'call')


def view(rows, cat_ids, names, cap, making_usd, now=None):
    """The receipt the page shows: today's total, the cap, what is left, and today's rows newest first (whose agent, what, $)."""
    since = day_start(now); mine = own_rows(rows, cat_ids, since); done = round(sum(float(r.get('usd') or 0) for r in mine), 4)
    used = done + float(making_usd or 0)
    by = {}
    for r in mine:
        k = str(r.get('provider') or 'other'); by[k] = round(by.get(k, 0) + float(r.get('usd') or 0), 4)
    return {'capUsd': float(cap), 'spentUsd': round(done, 2), 'makingUsd': round(float(making_usd or 0), 2), 'leftUsd': round(max(0.0, float(cap) - used), 2),
            'calls': len(mine), 'byProvider': by, 'over': used >= float(cap) - 1e-9,
            'rows': [{'at': round(float(r.get('at') or 0)), 'agent': (names or {}).get(r.get('cat'), 'agent'), 'what': label(r), 'provider': r.get('provider'),
                      'usd': round(float(r.get('usd') or 0), 4), 'how': r.get('status') or ''} for r in sorted(mine, key=lambda x: -float(x.get('at') or 0))[:SHOW_ROWS]]}


def caps_read(path):
    try:
        d = json.loads(open(path).read())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def caps_write(path, caps):
    with open(path, 'w') as f_:
        f_.write(json.dumps(caps))

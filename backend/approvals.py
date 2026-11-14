"""✅ AGX-10 · THE APPROVE INBOX + POT ALERTS THAT TEACH (owner 2026-11-14).

A proof that went into the pot under 1x (score under 100) gets one line in its agent's chat: what to fix first (the part of its score that would
lift it most if perfect — the same rule as Its pot's "Fix first"), and, for work an agent can rebuild (a PoStatic page or a PoC), a redo.
The redo SPENDS MODEL USAGE, so it never runs on its own: it waits in the agent's Approve inbox — what runs, which models, about what it costs —
and runs only when the owner taps Approve (the work route, owner-gated; the auto loop's token is refused). A trade or a bid (PoW / PoP / PoB /
PoEco) is never re-run by an agent: money. Writing the alert costs nothing: no model is called. Pure functions; the service does the I/O."""
import secrets
import time

UNDER = 100                         # a score under 100 carries less than 1x into the pot
KEEP = 40                           # inbox rows kept per agent (newest)
ALERTED_KEEP = 400
REDO_KINDS = {'pos': 'PoStatic', 'poc': 'PoC'}   # work an agent can rebuild; never a trade or a bid
CODE = {'pow': 'PoW', 'pop': 'PoP', 'pob': 'PoB', 'poc': 'PoC', 'pos': 'PoStatic', 'poe': 'PoEco'}
STATES = ('waiting', 'approved', 'declined', 'ran', 'failed')


def biggest_lift(parts):
    """The one part that would lift the score most if it were perfect (weight × what is missing). None with nothing to lift."""
    rows = [p for p in parts or [] if isinstance(p, dict) and p.get('value') is not None]
    best = max(rows, key=lambda p: float(p.get('weight') or 0) * (1 - float(p['value'])), default=None)
    if not best or float(best.get('weight') or 0) * (1 - float(best['value'])) <= 0:
        return None
    return {**best, 'gain': float(best.get('weight') or 0) * (1 - float(best['value']))}


def due(rows, since, done=()):
    """[(kind, folder, view)] → the closed proofs filed since `since` that scored under 1x and were not alerted yet, oldest first."""
    out = []
    for kind, f, v in rows:
        if not isinstance(f, dict) or f.get('status') != 'closed' or f.get('id') in done or not v or v.get('score') is None:
            continue
        t = float(f.get('closedAt') or f.get('soldAt') or f.get('at') or 0)
        if t >= float(since) and float(v['score']) < UNDER:
            out.append((t, kind, f, v))
    return [(k, f, v) for _t, k, f, v in sorted(out, key=lambda r: r[0])]


def alert_text(kind, f, v, lift, redo):
    name = f"{CODE.get(kind, 'Proof')} #{f.get('n') or '?'}"
    top = float(v.get('top') or 300)
    head = f"⚠ {name} went into the pot under 1x (score {round(float(v['score']))} of {round(top)})."
    fix = f" Fix first: {lift['label']}{(' — ' + str(lift['note'])) if lift.get('note') else ''}. Perfect there adds up to {round(lift['gain'] / 100 * top)} points." if lift else ''
    tail = ' A redo is waiting in your Approve inbox: it runs only when you tap Approve.' if redo else ' Your next one should start there.'
    return head + fix + tail


def redo_item(kind, f, lift, brains, now=None):
    """The inbox row for a redo: exactly what runs (the op), which models, about what it costs (what this proof cost to make). None when it can't be redone."""
    if kind not in REDO_KINDS or not lift:
        return None
    fix = f"{lift['label']}{(': ' + str(lift['note'])) if lift.get('note') else ''}"
    if kind == 'pos':
        if not f.get('ws'):
            return None
        op = {'op': 'ws_build', 'job': str(f['ws']), 'text': f'Run it again and fix this first: {fix}. Keep everything else that works.', 'to': 'both'}
    else:
        op = {'op': 'poc', 'text': str(f.get('topic') or '')[:100], 'job': None}
    ms = [str(m).split('/')[-1] for m in (brains or []) if m][:2]
    cost = f.get('cost')   # what this proof cost to make; a recorded $0 is 'not known', never a free redo
    return {'id': 'ap' + secrets.token_hex(5), 'kind': 'redo', 'proof': {'kind': kind, 'id': f.get('id'), 'n': f.get('n')},
            'what': f"Redo {REDO_KINDS[kind]} #{f.get('n') or '?'} with both minds, fixing {lift['label']}", 'models': ms,
            'estUsd': round(float(cost), 4) if cost not in (None, '') and float(cost) > 0 else None, 'op': op, 'at': round(now if now is not None else time.time()), 'state': 'waiting'}


def add(cat, item):
    """File a row (one waiting row per proof). → the row kept, or None when one is already waiting for that proof."""
    rows = list(cat.get('approvals') or [])
    pid = (item.get('proof') or {}).get('id')
    if pid and any(r.get('state') == 'waiting' and (r.get('proof') or {}).get('id') == pid for r in rows):
        return None
    cat['approvals'] = (rows + [item])[-KEEP:]
    return item


def decide(cat, aid, yes, now=None):
    """The owner's tap. Only a waiting row can be decided, once. → the row (approved / declined). KeyError: no such row · ValueError: already decided."""
    row = next((r for r in cat.get('approvals') or [] if r.get('id') == aid), None)
    if row is None:
        raise KeyError(aid)
    if row.get('state') != 'waiting':
        raise ValueError(f"Already {row.get('state')}.")
    row['state'] = 'approved' if yes else 'declined'; row['decidedAt'] = round(now if now is not None else time.time())
    return row


def finish(row, ok, say=''):
    row['state'] = 'ran' if ok else 'failed'
    if say:
        row['say'] = str(say)[:200]
    return row


def view(cat):
    """The inbox, newest first: waiting rows on top."""
    rows = list(cat.get('approvals') or [])[::-1]
    return sorted(rows, key=lambda r: r.get('state') != 'waiting')

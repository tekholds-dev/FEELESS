"""🎓 Slice 7 · COMP learns from real, judged proofs only (owner 2026-11-19: "I'm not confident in COMP"). Pure.

A training row is ONE real proof an agent filed (never a TEST, never an internet market snapshot, never a teacher's text, never the same
proof twice), whose pass / fail came from what really happened, never from the judges COMP is examined against:
  · PoW / PoP: the trade's own P&L (sign of pnlPct / roePct),
  · PoB: the scoreboard, Polymarket or Kalshi settling it (or the owner's mark on a topic-only ask with no game),
  · PoC: its reach at 7 days, or the owner's mark,
  · PoStatic: the owner's mark (only he knows if the page works).
Each row carries its pass / fail evidence (`settledBy` + `proofOf`: the facts that settled it) and what the proof did BEFORE it settled
(`evidence`: the minds' calls and reasons, the bid and its legs, the coin's numbers at entry, the build plan). Anything written after the
result (exit, P&L, final score, the watcher's sell reason, judge reviews, owner notes) never reaches COMP's question.
Everything else is dropped and counted by reason, so the report says what COMP did NOT learn from.
"""
import hashlib
import json
import zlib

import model_lab as _ml

FOLDERS = {'powFolders': 'PoW', 'popFolders': 'PoP', 'pobFolders': 'PoB', 'pocFolders': 'PoC', 'psFolders': 'PoStatic'}
CATEGORY = {'Trades': 'powFolders', 'Perps': 'popFolders', 'Picks': 'pobFolders', 'Content': 'pocFolders', 'Code': 'psFolders'}
RESULTS = ('scoreboard', 'polymarket', 'kalshi', 'reach at 7 d')   # a proof's own result, set by code that read the real outcome
TEST_PCT, VALID_PCT = 25, 10     # the held-out folds, by a hash of the proof's id: a proof never changes fold, so no version trains on its exam
CAP = 1800

# Why a row was dropped (plain words for the report). Every reason is counted, never silently skipped.
WHY = {
    'test': 'a TEST proof (Claude\'s test runs never teach COMP)',
    'open': 'not settled yet: no real pass / fail',
    'flat': 'settled flat: neither pass nor fail',
    'judge_only': 'only the judges graded it: that is the exam, not a lesson',
    'hand_mark_on_game': 'a hand mark on a scored game (the scoreboard settles it, a hand mark never does)',
    'no_evidence': 'says nothing it did before it settled',
    'duplicate': 'the same proof again (kept once)',
    'source_marker': 'a per-site index entry, not a proof',
    'unreadable': 'its stash copy would not open',
    'market_row': 'an internet market snapshot, not a proof',
    'teacher_lesson': 'a teacher model\'s text, not a proof',
    'kalshi_lesson': 'a Kalshi bid lesson with no proof record (its PoB folder carries the bid)',
}


def _s(v, n):
    return _ml._s(v, n)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def label(key, f):
    """→ (outcome 'won' | 'lost', settledBy, proofOf lines) or (None, drop reason, []). Never reads the judges' review."""
    kind = FOLDERS.get(key)
    if key in ('powFolders', 'popFolders'):
        field = 'pnlPct' if key == 'powFolders' else 'roePct'
        v = _num(f.get(field))
        if v is None:
            return None, 'open', []
        if v == 0:
            return None, 'flat', []
        side = f"{_s(f.get('side'), 6)} " if f.get('side') else ''
        return ('won' if v > 0 else 'lost'), ('pnl' if kind == 'PoW' else 'roe'), [
            f"{kind} closed {side}${_s(f.get('sym') or f.get('market'), 16)} at {v:+.2f}% (entry {f.get('entry', '?')} → exit {f.get('exit', '?')})".replace('  ', ' ')]
    k = f.get('kalshi') if isinstance(f.get('kalshi'), dict) else None
    if key == 'pobFolders' and k and k.get('outcome') in ('won', 'lost'):   # 💵 a real-money bid Kalshi settled: the strongest result there is
        return k['outcome'], 'kalshi', [f"PoB's Kalshi bid {_s(k.get('title') or k.get('ticker'), 80)} settled {k['outcome']} on Kalshi"]
    g = f.get('graded')
    if g not in ('right', 'wrong'):
        return None, 'open', []
    by = f.get('gradedBy')
    if key == 'pobFolders' and (f.get('games') or f.get('poly')) and by not in RESULTS:
        return None, 'hand_mark_on_game', []
    settled = by if by in RESULTS else 'owner mark'
    out = 'won' if g == 'right' else 'lost'
    proof = [f"{kind} graded {g} by {settled}"]
    for gm in (f.get('games') or [])[:3]:
        if isinstance(gm, dict) and gm.get('final'):
            proof.append(f"game final: {_s(gm.get('label'), 60)} · score {_s(gm.get('score'), 16)} · "
                         f"{ {True: 'side won', False: 'side lost'}.get(gm.get('won'), 'side ?') }")
    r = f.get('result') if isinstance(f.get('result'), dict) else None
    if kind == 'PoC' and r:
        proof.append(f"reach: {_s(r.get('views') or r.get('earnedUsd') or r.get('link'), 60)}")
    if settled == 'owner mark' and f.get('gradeWhy'):
        proof.append(f"owner's reason: {_s(f.get('gradeWhy'), 200)}")
    return out, settled, proof


def evidence(key, f, cap=CAP):
    """🧾 What the proof DID before it settled (the minds' calls and reasons, the bid, the coin at entry, the build). Nothing written after
    the result: no exit, P&L, final score, sell reason, review or owner note. Scrubbed and capped. Pure."""
    out = []
    for c in (f.get('calls') or [])[:4]:
        if not isinstance(c, dict):
            continue
        who = f"mind {c.get('mind', '?')}"
        picks = [p for p in (c.get('picks') or []) if isinstance(p, dict)][:3]
        if picks:
            out += [f"call {who}: {_s(p.get('pick'), 80)} · {p.get('confidence', '?')}% · {_s(p.get('why'), 220)}" for p in picks]
        elif c.get('pass'):
            out.append(f"call {who}: PASS · {_s(c.get('pass'), 220)}")
        elif c.get('angle') or c.get('post'):
            out.append(f"call {who}: angle {_s(c.get('angle'), 80)} · post {_s(c.get('post'), 200)}")
        elif c.get('side') or c.get('why'):
            lev = f" {c['lev']}x" if c.get('lev') else ''
            out.append(f"call {who}: {_s(c.get('side'), 12)} {_s(c.get('market'), 20)}{lev} · {_s(c.get('why'), 220)}".replace('  ', ' '))
    if f.get('agreed'):
        out.append('both minds agreed: ' + '; '.join(_s(a, 80) for a in (f.get('agreed') or [])[:3]))
    k = f.get('kalshi') if isinstance(f.get('kalshi'), dict) else None
    if k:
        out.append(f"bid: {_s(k.get('title'), 90)} · {_s(k.get('side'), 4)} @ {k.get('price', '?')} × {k.get('count', '?')}")
        out += [f"leg: {_s(g.get('title'), 80)} · {_s(g.get('side'), 4)} @ {g.get('price', '?')}" for g in (k.get('legs') or [])[:4] if isinstance(g, dict)]
    for g in (f.get('games') or [])[:3]:
        if isinstance(g, dict):
            out.append(f"game: {_s(g.get('label'), 60)} · backing {_s(g.get('short') or g.get('side'), 30)}")
    if key == 'powFolders':
        p = f.get('pick') if isinstance(f.get('pick'), dict) else {}
        if p:
            nums = ' · '.join(f"{n} {p[n]}" for n in ('liq', 'cap', 'mcap', 'vol', 'vol24h', 'change', 'age', 'holders') if p.get(n) is not None)
            out.append(f"coin at pick: ${_s(p.get('sym'), 16)} from {_s(p.get('src'), 16)} · {_s(nums, 200)}")
        whys = f.get('whys')
        for w in (list(whys.values()) if isinstance(whys, dict) else whys if isinstance(whys, list) else [])[:2]:
            out.append(f"mind's reason: {_s(w, 220)}")
        for r in (f.get('research') or [])[:5]:
            if isinstance(r, dict):
                out.append(f"read: {_s(r.get('site'), 24)} {_s(r.get('label'), 24)} = {_s(r.get('value'), 60)}")
        if f.get('entry') is not None:
            out.append(f"entry {f.get('entry')} · take-profit {f.get('tp', '?')} · stop {f.get('sl', '?')} · size {f.get('sol', '?')} SOL")
    if key == 'pocFolders':
        tr = f.get('trends') if isinstance(f.get('trends'), dict) else {}
        for src, items in list(tr.items())[:2]:
            out.append(f"trend {_s(src, 20)}: " + '; '.join(_s(x, 70) for x in (items or [])[:2]))
    if key == 'psFolders':
        for st in (f.get('steps') or [])[:4]:
            out.append(f"build step: {_s(st, 160)}")
        kits = f.get('kits')
        if kits:
            out.append('kits: ' + ', '.join(_s(x.get('id') if isinstance(x, dict) else x, 24) for x in kits[:8]))
        if f.get('refs'):
            out.append(f"read {len(f['refs'])} reference pages")
    txt, total = [], 0
    for ln in out:
        if total + len(ln) > cap:
            break
        txt.append(ln); total += len(ln) + 1
    return txt


def before_fields(key, f):
    """The words the proof wrote before it settled. A PoW's `why` is the watcher's SELL reason, written after: never here."""
    allow = ('topic', 'plan', 'angle', 'ask') + (() if key in ('powFolders', 'popFolders') else ('why',))
    return {k: _s(f[k], 600) for k in allow if isinstance(f.get(k), str) and f[k].strip()}


def title_of(key, f):
    return _s(f.get('name') or f.get('topic') or f.get('title') or f.get('id'), 160)


def row_of(key, f, source='', grade=None):
    """One real proof → (row, None) or (None, drop reason). `grade` = the owner's Model Lab grade on it (good / bad), used only when nothing
    else settled it: a person's judgement, never a judge model's."""
    if f.get('test'):
        return None, 'test'
    out, by, proof = label(key, f)
    if out is None and by == 'open' and (grade or {}).get('verdict') in ('good', 'bad'):
        out, by = ('won' if grade['verdict'] == 'good' else 'lost'), 'owner grade'
        proof = [f"{FOLDERS[key]} graded {grade['verdict']} by the owner in Model Lab" + (f": {_s(grade.get('note'), 200)}" if grade.get('note') else '')]
    if out is None and by == 'open' and ((f.get('review') or {}).get('by') if isinstance(f.get('review'), dict) else None):
        return None, 'judge_only'
    if out is None:
        return None, by
    ev = evidence(key, f); words = before_fields(key, f)
    if not ev and not words.get('plan') and not words.get('angle'):
        return None, 'no_evidence'
    return {'id': str(f.get('id')), 'kind': FOLDERS[key], 'title': title_of(key, f), 'source': source, **words, 'evidence': ev,
            'outcome': out, 'settledBy': by, 'proofOf': proof, 'at': round(float(f.get('closedAt') or f.get('soldAt') or f.get('at') or 0))}, None


def _stash_label(key, item, d):
    """A stash copy is kept when the proof closed, before many settled: its index row holds the result it got later."""
    if key in ('powFolders', 'popFolders'):
        return label(key, d)
    o = item.get('outcome')
    if o == 'flat':
        return None, 'flat', []
    if o not in ('won', 'lost'):
        return None, 'open', []
    by = d.get('gradedBy') if d.get('gradedBy') in RESULTS else ('scoreboard' if key == 'pobFolders' and (d.get('games') or d.get('poly')) else 'owner mark')
    return o, by, [f"{FOLDERS[key]} settled {o} by {by} (the stash index)"]


def collect(cats, stash_items=(), read_raw=None, extra=None, grades=None):
    """→ {'rows', 'kept': {kind: n}, 'dropped': {reason: n}, 'why': WHY}. The agents' live folders first (they carry the latest result),
    then stash copies of proofs whose folder is gone. `extra` = counts of the non-proof sources left out (market rows, teacher lessons …)."""
    rows, seen, dropped = [], set(), {}

    def drop(r, n=1):
        if n:
            dropped[r] = dropped.get(r, 0) + n

    for cat in (cats or {}).values() if isinstance(cats, dict) else cats or []:
        for key in FOLDERS:
            for f in (cat or {}).get(key) or []:
                if not isinstance(f, dict) or not f.get('id') or f.get('status') not in ('closed', None):
                    continue
                if f['id'] in seen:
                    drop('duplicate'); continue
                seen.add(f['id'])
                r, why = row_of(key, f, (cat or {}).get('source') or '', (grades or {}).get(f'{key}:{f["id"]}'))
                rows.append(r) if r else drop(why)
    for it in stash_items or ():
        key = CATEGORY.get(it.get('category'))
        if not key:
            continue
        parts = str(it.get('key') or '').split(':')
        if len(parts) > 2:
            drop('source_marker'); continue
        pid = parts[1] if len(parts) > 1 else ''
        if pid in seen:
            drop('duplicate'); continue
        seen.add(pid)
        try:
            raw = read_raw(it['key']) if read_raw else None
            d = json.loads(zlib.decompress(raw) if raw[:1] == b'x' else raw) if raw else None
        except Exception:   # noqa: BLE001 — a copy that will not open is counted, never guessed
            d = None
        if not isinstance(d, dict):
            drop('unreadable'); continue
        if d.get('test'):
            drop('test'); continue
        out, by, proof = _stash_label(key, it, d)
        if out is None:
            drop(by); continue
        ev = evidence(key, d); words = before_fields(key, d)
        if not ev and not words.get('plan') and not words.get('angle'):
            drop('no_evidence'); continue
        rows.append({'id': pid or str(d.get('id')), 'kind': FOLDERS[key], 'title': title_of(key, d), 'source': it.get('source') or '', **words,
                     'evidence': ev, 'outcome': out, 'settledBy': by, 'proofOf': proof, 'at': round(float(it.get('at') or 0))})
    for k, n in (extra or {}).items():
        drop(k, int(n or 0))
    kept = {}
    for r in rows:
        kept[r['kind']] = kept.get(r['kind'], 0) + 1
    return {'rows': rows, 'kept': kept, 'dropped': dropped, 'why': {k: WHY[k] for k in dropped if k in WHY}}


def fold(pid):
    """test / valid / train, by a hash of the proof's id. Fixed forever: a proof examined once is never trained on by a later COMP."""
    h = int(hashlib.sha256(str(pid).encode()).hexdigest()[:8], 16) % 100
    return 'test' if h < TEST_PCT else 'valid' if h < TEST_PCT + VALID_PCT else 'train'


def split(rows):
    tr, va, te = [], [], []
    for r in sorted(rows, key=lambda r: (r.get('at') or 0, r.get('id') or '')):
        {'train': tr, 'valid': va, 'test': te}[fold(r['id'])].append(r)
    return tr, va, te

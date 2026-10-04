"""🧹 Sitewide data cleaner (pure, tested). Rules only ever drop DERIVED or STALE data — never money records (ledgers, fees, positions,
receipts), never a message's text, never who said it. Each rule returns (data, stats) so HQ can show exactly what was freed.

Rule 1 — chat token snapshots: every coin posted in chat stored its full market snapshot; the live `signals` block alone is ~3 KB per
coin and is meaningless minutes later (cards re-read live data). One FeeCat wall was 3.3 MB of a 4 MB chat file, rewritten on every
message. Messages older than `fresh_secs` keep the coin (ids, symbol, price at post time, logo) and lose the stale signal blocks.
"""
import json

STALE_PAIR_KEYS = ('signals', 'quality', 'observedAt')   # recomputed live wherever they are shown
FRESH_SECS = 3600


def _size(v):
    return len(json.dumps(v, separators=(',', ':')))


def slim_chat(doc, now, fresh_secs=FRESH_SECS):
    """→ (doc, {'messages': n slimmed, 'bytes': freed}). Idempotent: a second pass frees 0."""
    out, n, freed = {**doc, 'rooms': {}}, 0, 0
    for room, msgs in (doc.get('rooms') or {}).items():
        new = []
        for m in msgs if isinstance(msgs, list) else []:
            ts = float(m.get('ts') or 0) / 1000.0
            toks = m.get('tokens')
            if not isinstance(toks, list) or not toks or now - ts < fresh_secs or not any(isinstance(t.get('pair'), dict) and any(k in t['pair'] for k in STALE_PAIR_KEYS) for t in toks if isinstance(t, dict)):
                new.append(m); continue
            slim = [({**t, 'pair': {k: v for k, v in t['pair'].items() if k not in STALE_PAIR_KEYS}} if isinstance(t, dict) and isinstance(t.get('pair'), dict) else t) for t in toks]
            freed += _size(toks) - _size(slim); n += 1
            new.append({**m, 'tokens': slim})
        out['rooms'][room] = new if isinstance(msgs, list) else msgs
    return out, {'messages': n, 'bytes': max(0, freed)}

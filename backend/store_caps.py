"""🗄 NO HOARDING (owner, 2026-10-21: "the site and the AI must not hoard data — caps / TTLs on every store, logs and model memory"). Pure.

Every file under backend/data gets a CLASS and a CAP:
  · money   — ledgers, books, receipts: the record of real money. Never trimmed, never capped (they are small and must stay whole).
  · snapshot— one-off backups a fix left behind (`*_before_*`, `.bak`): stale after SNAP_DAYS → listed to archive (the owner decides).
  · cache   — re-buildable reads (candles, social, launch facts, logos …): capped; anything past its cap is rebuilt smaller, never needed whole.
  · log     — chat, notifications, bugs, guard / defence, AI calls: capped by size; their own code keeps the newest rows.
  · memory  — the models' notebooks (NEXA, OSSY / G4 memory, the discovery base): capped short facts.
  · other   — everything else: the default cap.
`audit` turns (name, bytes, mtime) rows into {class, capMb, pct, state: ok · watch (≥ 75 %) · over · stale}. Nothing here deletes anything.
"""
import re

MB = 1024 * 1024
SNAP_DAYS = 14
MONEY = ('fuse_wallet', 'fee_ledger', 'fees', 'proof', 'trade_fills', 'payouts', 'receipts', 'fuse_hq', 'realcfg', 'feeback')
CLASSES = (   # (class, cap MB, name patterns) — first match wins
    ('snapshot', None, (r'_before_', r'\.bak$', r'backup', r'_old\.', r'_\d{10}\.json$')),
    ('money', None, tuple(rf'^{m}' for m in MONEY)),
    ('memory', 4, (r'^nexa', r'^ai_memory', r'^ai_learn', r'^g4', r'^ossy', r'kb\.json$')),
    ('log', 8, (r'^chat', r'^notifications', r'^bugs', r'^guard', r'^defence', r'^ai_calls', r'^audit', r'log', r'^push')),
    ('cache', 12, (r'cache', r'^candle', r'^launch_facts', r'^meme_terms', r'^pump_callers', r'^intel', r'^social', r'^runner_paths', r'^hygiene',
                   r'_view\.json$', r'^logos', r'^uploads', r'^funders', r'^smart_wallets', r'^blocklist', r'^trench_lingo')),
)
DEFAULT_MB = 6


def classify(name):
    n = name.lower()
    for cls, cap, pats in CLASSES:
        if any(re.search(p, n) for p in pats):
            return cls, cap
    return 'other', DEFAULT_MB


def audit(rows, now):
    """rows = [(name, bytes, mtime)] → the store list, the biggest offenders first, + totals per class."""
    out, tot = [], {}
    for name, size, mtime in rows:
        cls, cap = classify(name)
        age_d = max(0.0, (now - float(mtime or now)) / 86400)
        pct = round(size / (cap * MB) * 100, 1) if cap else None
        state = ('stale' if cls == 'snapshot' and age_d >= SNAP_DAYS else 'keep' if cls == 'money' else
                 'over' if pct is not None and pct >= 100 else 'watch' if pct is not None and pct >= 75 else 'ok')
        out.append({'name': name, 'mb': round(size / MB, 2), 'class': cls, 'capMb': cap, 'pct': pct, 'ageD': round(age_d, 1), 'state': state})
        t = tot.setdefault(cls, {'mb': 0.0, 'n': 0}); t['mb'] = round(t['mb'] + size / MB, 2); t['n'] += 1
    rank = {'over': 0, 'stale': 1, 'watch': 2, 'ok': 3, 'keep': 4}
    out.sort(key=lambda r: (rank[r['state']], -r['mb']))
    return {'stores': out, 'byClass': tot, 'totalMb': round(sum(t['mb'] for t in tot.values()), 1),
            'over': sum(1 for r in out if r['state'] == 'over'), 'stale': sum(1 for r in out if r['state'] == 'stale'),
            'staleMb': round(sum(r['mb'] for r in out if r['state'] == 'stale'), 1)}

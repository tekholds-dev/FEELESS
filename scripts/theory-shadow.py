#!/usr/bin/env python3
"""The trench theory, tested before any deterministic agent may use it (owner: "only after a shadow test"). Read only: it trades nothing and changes nothing.

Takes every launch coin the brain watched for an hour since prices were clean, scores each with trench_theory.verdict using only the bands known at first sight, and compares the hour that followed on the newest 40% of coins. A round trip costs COST_PCT; a coin that vanished counts as -100%. Run: .venv/bin/python scripts/theory-shadow.py"""
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import trench_theory as tt  # noqa: E402

COST_PCT = tt.COST_PCT
AGE = {'age:<15m': 5, 'age:15-60m': 30, 'age:1-3h': 120, 'age:3-12h': 360, 'age:12h+': 900}


def case_of(tags):
    """The brain's bands → the case verdict reads. A cap band counts by its low end, so 'under 30K' is only claimed when the whole band is under."""
    tags = list(tags or []); out = {}
    for t in tags:
        if t in AGE:
            out['ageMin'] = AGE[t]
        elif t.startswith('stage:'):
            out['status'] = t.split(':', 1)[1]
        elif t.startswith('cap:'):
            m = re.fullmatch(r'cap:<?(\d+(?:\.\d+)?)([KM])?(?:-(\d+(?:\.\d+)?)([KM])?)?\+?', t)
            if m:
                unit = {'K': 1e3, 'M': 1e6, None: 1}
                top = float(m.group(3)) * unit[m.group(4) or m.group(2)] if m.group(3) else float(m.group(1)) * unit[m.group(2)]
                out['cap'] = top - 1 if ('<' in t or m.group(3)) else top
    return out


def outcome(c):
    return -100.0 if c.get('gone') else (float(c['end']) - COST_PCT if c.get('end') is not None else None)


def shadow(coins, holdout=0.4):
    """→ [{score, n, medianPct, upPct}] per theory score on the newest part only, after costs."""
    rows = sorted((c for c in coins if isinstance(c, dict) and outcome(c) is not None), key=lambda c: c.get('at') or 0)
    rows = rows[int(len(rows) * (1 - holdout)):]; by = {}
    for c in rows:
        by.setdefault(tt.verdict(case_of(c.get('f')))['score'], []).append(outcome(c))
    return [{'score': k, 'n': len(v), 'medianPct': round(statistics.median(v), 1), 'upPct': round(100 * sum(1 for x in v if x > 0) / len(v))} for k, v in sorted(by.items())]


if __name__ == '__main__':
    d = json.load(open(ROOT / 'backend' / 'data' / 'trench_brain.json')); since = float(d.get('cleanFrom') or 0)
    coins = [x for x in d.get('done') or [] if x.get('at', 0) >= since]
    print(f'{len(coins)} coins, testing the newest 40%, {COST_PCT:g}% round trip')
    for r in shadow(coins):
        print(f"theory score {r['score']:+d}: n {r['n']:5} · typical {r['medianPct']:+7.1f}% · {r['upPct']:3}% up")

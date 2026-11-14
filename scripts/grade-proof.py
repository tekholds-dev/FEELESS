#!/usr/bin/env python3
"""🧑‍⚖️ Claude's outside review of one proof (owner 2026-11-14: "I or you can grade the proof"). Used when the model judges built the proof
(recused) — no extra model to download. Files judge `claude` through feecat's internal route (internal key, this machine only).

  .venv/bin/python scripts/grade-proof.py <cat id> <kind> <folder id> pass|fail <score 0-100> "why" ["✓ check" "✗ check" …]
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv):
    if len(argv) < 6:
        print(__doc__); return 2
    cat, kind, fid, verdict, score, why, *checks = argv
    key = (ROOT / 'backend' / 'data' / 'internal.key').read_text().strip()
    body = json.dumps({'cat': cat, 'kind': kind, 'fid': fid, 'verdict': verdict, 'score': int(score), 'why': why, 'checks': checks}).encode()
    req = urllib.request.Request('http://127.0.0.1:5088/api/cats/internal/review-outside', body, {'content-type': 'application/json', 'x-feeless-internal': key})
    try:
        rv = json.load(urllib.request.urlopen(req, timeout=15))['review']
    except urllib.error.HTTPError as e:
        print(f'refused: {e.code} {e.read().decode()[:200]}'); return 1
    print(f"filed: {rv['verdict']} {rv['score']} · judges {', '.join(k for k, v in rv['by'].items() if v)} · recused {', '.join(rv.get('recused') or []) or 'none'}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Run the code-health scan and write backend/data/code_health.json (HQ › Lag catcher › Code health reads it)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import code_health  # noqa: E402
out = code_health.scan(ROOT)
dst = ROOT / 'backend' / 'data' / 'code_health.json'
dst.parent.mkdir(exist_ok=True)
dst.write_text(json.dumps(out))
print(json.dumps({'counts': out['counts'], 'totals': out['totals'], 'scanSec': out['scanSec']}))

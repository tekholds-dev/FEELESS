#!/usr/bin/env python3
"""🏁 Rebuild COMP as ONE Flagship version (owner 2026-11-14): old builds move to backend/data/model_forge/_archive/<stamp>/ (kept), the new
v0.01 starts from the best version's weights, reads every source and trains for N seconds (default 150) on this Mac. Nothing is spent.
Run: PYTHONPATH=backend:. .venv/bin/python scripts/comp-flagship.py [seconds]"""
import json
import sys

import rep_model_lab as lab
import reputation_service as rs

out = lab.flagship_rebuild(rs, int(sys.argv[1]) if len(sys.argv) > 1 else lab.FLAGSHIP_SECONDS)
print(json.dumps({k: out[k] for k in ('id', 'version', 'from', 'fromVal', 'seconds', 'archived')}, indent=1))

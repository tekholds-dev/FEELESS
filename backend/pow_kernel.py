"""🧱 THE EVOLUTION KERNEL (SUPREME_INTELLIGENCE_REQUEST §3): every hard limit the research, PoI and PoP engines run under, in one versioned, read-only place.
The numbers stay where the code enforces them; this reads them, so it can never disagree with what really runs. tests/test_pow_kernel.py pins the fingerprint:
changing a limit fails the suite until VERSION and the pin are changed on purpose. Models cannot reach any of it. Each PoW round files the fingerprint it ran under.
"""
import hashlib
import json

import cat_agent as _ca
import colony as _colony
import poi as _poi
import pop as _pop
import pow as _pow

VERSION = '2026.11.04.2'


def limits():
    return {
        'Research budget': {'Dollars a coin, each mind': _pow.ROUND_USD, 'Seconds a round': _pow.RESEARCH_S, 'Sites a round': _pow.SITES_MAX, 'Moves a site': list(_pow.STEPS_RANGE)},
        'Evidence': {'Saved pulls a site': _pow.SITE_PULLS, 'Snapshots a site': _ca.SNAPS_PER_SITE, 'Recent folders skipped': _pow.RECENT_FOLDERS, 'Manual bot-check seconds': 45},
        'Learning': {'Visits before promotion': _poi.PROMOTE_AFTER, 'Visits before retirement': _poi.RETIRE_AFTER, 'Useful revisits to roll back': _poi.ROLLBACK_AFTER},
        'Trade limits': {'Default stop %': _pow.STOP_PCT, 'Default take profit %': _pow.TAKE_PCT, 'Watch checks, seconds': list(_pow.CHECKS)},
        'Proof of Perps': {'Leverage': [_pop.LEV_MIN, _pop.LEV_MAX], 'Longest hold, seconds': _pop.HOLD_MAX_S, 'Paper stake $': _pop.COLLATERAL_USD, 'Proposal window, seconds': _pop.PROPOSE_WINDOW_S, 'Stale after this share of its room': _pop.DRIFT_MAX, 'Real orders': False},
        'Colony': {'Share choices %': list(_colony.SHARE_PCTS), 'PoI can move treasury funds': False},
    }


def fingerprint():
    return hashlib.sha256(json.dumps(limits(), sort_keys=True).encode()).hexdigest()[:12]


def view():
    return {'v': VERSION, 'hash': fingerprint(), 'groups': [{'name': k, 'rows': [[a, b] for a, b in v.items()]} for k, v in limits().items()]}

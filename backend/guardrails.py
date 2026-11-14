"""🛡 AGX-7 · THE OWNER'S GUARDRAIL SWITCHES (owner 2026-11-14). Pure, plus one small file reader.

Every limit COMP and the agents run under, each a switch (+ a value where it has one), set ONLY by the owner (`_require_owner` on
/api/reputation/admin/guardrails). No agent reads or writes this: the server enforces it at each chokepoint, a model never sees it.
RESTRICT-ONLY: every switch starts at today's behaviour and can only make things stricter — a value is clamped between its floor and
today's number, so this panel can never loosen a trading rule or raise a spend cap. CLAUDE.md §1 hard limits are listed LOCKED, read-only.
"""
import json
import time
from pathlib import Path

# key: (label, what it governs, default on, value default (= today's number) or None, value floor, unit)
SWITCHES = {
    'agentsWork': ('Agents work on their own', "Colonize: each agent's PoW loop files folders and buys on FEELESS without being asked. Off = they only work when you ask", True, None, None, ''),
    'autoCollect': ('Auto-collect wins to the Pool', "A +50% win's owed share goes from the agent's wallet to the Pool by itself (owner-signed). Off = nothing sends; shares wait", True, None, None, ''),
    'taskCap': ('Most one task may spend', "The highest $ cap an owner can give one general-agent task", True, 2.0, 0.005, '$'),
    'compRuns': ('COMP may train and sit the exam', "MLX training and the exam on this Mac (free, heavy). Off = Train / Run the exam are refused", True, None, None, ''),
    'compFlagships': ('Paid flagships sit the exam', "Claude / GPT / Grok answer COMP's exam when their key is saved (paid). Off = they are listed as off, never called", True, 40, 0, 'questions each'),
}
HARD = (   # CLAUDE.md §1 — shown, never switchable here
    ('Money', 'Claude never moves funds or hits mainnet in tests; the owner does all real-money tests.'),
    ('Keys + privacy', 'Keys, the owner\'s email and wallet secrets are never printed, committed or sent.'),
    ('Signing', 'The wallet signs everything; the server verifies signed = quoted; no resubmits.'),
    ('P&L', 'P&L never includes fees. New real-money auto-buys ship with age / pool / already-ran guards.'),
    ('Market data', 'No GeckoTerminal, ever: DexScreener + our own indexes.'),
    ('Legal', 'Nothing that makes FEELESS a custodian, broker or betting house without the owner\'s dated ruling.'),
)


def defaults():
    return {k: {'on': d, **({'value': v} if v is not None else {})} for k, (_, _, d, v, _, _) in SWITCHES.items()}


def clean(body, prev=None):
    """The owner's edit → the stored switches. Unknown keys dropped; a value clamped to [floor, today's number] — never looser than today."""
    out = {**defaults(), **{k: v for k, v in (prev or {}).items() if k in SWITCHES and isinstance(v, dict)}}   # a malformed saved row = today's default
    for k, row in (body or {}).items():
        if k not in SWITCHES or not isinstance(row, dict):
            continue
        _, _, _, top, floor, _ = SWITCHES[k]
        cur = dict(out[k])
        if 'on' in row:
            if not isinstance(row['on'], bool):
                raise ValueError(f'{SWITCHES[k][0]}: on is true or false.')
            cur['on'] = row['on']
        if top is not None and row.get('value') is not None:
            try:
                cur['value'] = round(max(floor, min(top, float(row['value']))), 4)
            except (TypeError, ValueError):
                raise ValueError(f'{SWITCHES[k][0]}: a number, please.')
        out[k] = cur
    return out


def view(g, by=None, at=None):
    """→ what the owner's panel shows: each switch with its words, today's number (the most it may be) and its floor, + the locked hard limits."""
    g = clean({}, g)
    return {'switches': [{'key': k, 'label': lab, 'say': say, 'on': g[k]['on'], 'value': g[k].get('value'), 'max': top, 'min': floor, 'unit': unit}
                         for k, (lab, say, _, top, floor, unit) in SWITCHES.items()],
            'hard': [{'t': t, 'say': s} for t, s in HARD], 'by': by, 'at': at}


_CACHE = {}


def read(path):
    """→ (switches, by, at) straight from the file. Defaults when none / unreadable / malformed — never raises."""
    try:
        d = json.loads(Path(path).read_text())
        return clean({}, d.get('switches') if isinstance(d.get('switches'), dict) else {}), d.get('by'), d.get('at')
    except (OSError, ValueError, AttributeError, TypeError):
        return defaults(), None, None


def load(path, fresh=False):
    """The saved switches, re-read at most every 2 s (so a flip lands within seconds in every service); fresh=True skips the cache."""
    now = time.time(); p = str(path); c = _CACHE.get(p)
    if c and not fresh and now - c[0] < 2:
        return c[1]
    g = read(p)[0]
    _CACHE[p] = (now, g)
    return g


def save(path, g, by, now):
    Path(path).write_text(json.dumps({'switches': g, 'by': by, 'at': round(now)}))
    _CACHE.pop(str(path), None)


def on(g, key):
    return bool((g.get(key) or {}).get('on', SWITCHES[key][2]))


def value(g, key):
    """The switch's number: today's number when unset; 0 when the switch is off (a cap that is off allows nothing)."""
    if not on(g, key):
        return 0
    v = (g.get(key) or {}).get('value'); top = SWITCHES[key][3]
    return top if v is None else min(top, v)

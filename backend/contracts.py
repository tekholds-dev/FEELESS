"""📜 COL-20 DATA CONTRACTS: the Collective's shared records each have one versioned shape, one owner and a check. A record that breaks its
contract is caught where it is made (tests run every contract on real data), so a change to a shape is a deliberate version bump, never drift.

Contracts: the mission envelope (mission.py, read-only view of a proof), a model call row (mission.call_row → data/mind_calls.jsonl), a proof
event (proof_events.py → data/proof_events.db), a part (collective_parts.py → data/parts.db). Pure."""

KINDS = ('pow', 'pop', 'pob', 'poc', 'pos', 'poe')
NUM = (int, float)
OPT = type(None)

CONTRACTS = {
    'envelope': {'v': 1, 'owner': 'mission.py', 'fields': {
        'v': int, 'id': (str, OPT), 'kind': str, 'code': str, 'agent': dict, 'minds': list, 'attribution': str, 'cost': dict, 'sources': list,
        'artifacts': dict, 'recordSha': str, 'quality': dict, 'outcome': dict, 'improvement': dict, 'evidence': dict, 'record': dict, 'compare': dict,
        'sent': dict}, 'enums': {'kind': KINDS}},
    'call': {'v': 1, 'owner': 'mission.call_row', 'fields': {
        'at': NUM, 'cat': (str, OPT), 'kind': (str, OPT), 'ref': (str, OPT), 'mind': (int, OPT), 'asked': (str, OPT), 'route': (str, OPT),
        'model': (str, OPT), 'usd': NUM, 'ms': NUM, 'ok': bool, 'local': bool}},
    'event': {'v': 1, 'owner': 'proof_events.py', 'fields': {
        'n': int, 'eid': str, 'at': NUM, 'kind': str, 'ref': str, 'cat': (str, OPT), 'event': str, 'data': dict, 'prev': str, 'mac': str},
        'enums': {'kind': KINDS}},
    'part': {'v': 1, 'owner': 'collective_parts.py', 'fields': {
        'id': str, 'cat': (str, OPT), 'kind': str, 'title': str, 'tag': str, 'bytes': int, 'licenses': list, 'kits': list, 'at': NUM, 'uses': int}},
}


def check(name, row):
    """→ [problem in words]; empty = the row keeps its contract."""
    c = CONTRACTS[name]; bad = []
    if not isinstance(row, dict):
        return [f'{name}: not a record']
    for k, t in c['fields'].items():
        if k not in row:
            bad.append(f'{name}: missing {k}')
        elif not isinstance(row[k], t) or (t is int and isinstance(row[k], bool)):
            bad.append(f'{name}: {k} is {type(row[k]).__name__}')
    for k, allowed in (c.get('enums') or {}).items():
        if k in row and row[k] not in allowed:
            bad.append(f'{name}: {k}={row[k]!r} is not one of {allowed}')
    if name == 'envelope' and row.get('v') != c['v']:
        bad.append(f"envelope: version {row.get('v')} but the contract is {c['v']}")
    return bad

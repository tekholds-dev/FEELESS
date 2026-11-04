"""Model-independent Proof of Intelligence research history.

Only verified page facts enter Research DNA. Each mind has a private, authenticated,
append-only generation chain; model text and trade outcomes cannot alter it.
"""
import hashlib
import json
import os
from pathlib import Path
import fcntl
from cryptography.fernet import InvalidToken

import cat_keys

VERSION = 1
MAX_FACTS = 64


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _path(data_dir, cat_id, mind):
    safe = hashlib.sha256(str(cat_id).encode()).hexdigest()
    return Path(data_dir) / 'poi' / f'{safe}.mind{int(mind)}.jsonl'


def _identity(cat_id, mind):
    return f'{cat_id}:mind:{int(mind)}'


def _read_locked(fh, cat_id, mind):
    fh.seek(0)
    rows = []
    prev = None
    for line in fh:
        if not line.strip():
            continue
        try:
            envelope = json.loads(line)
            if envelope.get('v') != VERSION or not str(envelope.get('sealed', '')).startswith('v2:'):
                raise ValueError('unknown Research DNA version or seal')
            row = json.loads(cat_keys.unseal(envelope['sealed'], _identity(cat_id, mind)))
            proof = row.pop('integrity', None)
            if proof != _digest(row) or row.get('generation') != len(rows) + 1 or row.get('prev') != prev:
                raise ValueError('Research DNA chain mismatch')
            row['integrity'] = proof
            rows.append(row)
            prev = proof
        except (KeyError, TypeError, json.JSONDecodeError, ValueError, InvalidToken) as exc:
            raise ValueError('Research DNA is unreadable or altered') from exc
    return rows


def load(data_dir, cat_id, mind):
    """Verify every encrypted generation before any is used by the kernel."""
    path = _path(data_dir, cat_id, mind)
    if not path.exists():
        return []
    with path.open('r') as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            return _read_locked(fh, cat_id, mind)
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def evidence(pulls):
    """Canonical, deduplicated page evidence; conclusions and unsupported pulls stay out."""
    out = []
    seen = set()
    for fact in pulls or []:
        if not fact.get('verified') or not fact.get('support') or not fact.get('site'):
            continue
        original = {k: fact.get(k) for k in ('label', 'value', 'site', 'url', 'at', 'support')}
        item = {'label': original['label'], 'site': original['site'], 'ref': _digest(original)}
        key = (original['label'], str(original['value']).casefold(), original['site'])
        if key not in seen:
            out.append(item)
            seen.add(key)
        if len(out) >= MAX_FACTS:
            break
    return out


def append(data_dir, cat_id, mind, folder, mint, at, pulls, metrics, steps=(), visited=()):
    """File one immutable research generation. A retried filing returns the prior row."""
    if not cat_id or mind not in (0, 1):
        raise ValueError('Research DNA requires an agent and mind')
    facts = evidence(pulls)
    path = _path(data_dir, cat_id, mind)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, 'r+') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            rows = _read_locked(fh, cat_id, mind)
            ident = _digest({'folder': folder, 'mint': mint, 'mind': mind})
            prior = next((r for r in rows if r['id'] == ident), None)
            if prior:
                return prior
            sites = sorted({x['site'] for x in facts})
            labels = sorted({x['label'] for x in facts})
            route = list(dict.fromkeys(str(x)[:64] for x in steps or []))[:80]
            row = {'v': VERSION, 'id': ident, 'generation': len(rows) + 1, 'prev': rows[-1]['integrity'] if rows else None,
                   'at': int(at), 'folder': str(folder), 'mint': str(mint), 'mind': mind, 'sites': sites, 'labels': labels,
                   'visited': list(dict.fromkeys(visited or sites)), 'route': route, 'facts': facts, 'metrics': {k: (metrics or {}).get(k) for k in
                   ('durationSec', 'visits', 'verified', 'factsPerVisit', 'factsPerUsd', 'costUsd', 'gaps')}}
            policy = evolution(rows + [row])
            row['policy'] = {'v': 1, 'states': policy['states'],
                             'events': [event for event in policy['events'] if event['generation'] == row['generation']]}
            row['integrity'] = _digest(row)
            sealed = cat_keys.seal(_json(row), _identity(cat_id, mind))
            fh.seek(0, os.SEEK_END)
            fh.write(_json({'v': VERSION, 'sealed': sealed}) + '\n')
            fh.flush()
            os.fsync(fh.fileno())
            return row
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def fingerprint(rows, mind):
    """Evidence yield per source for one mind; trade P/L and model identity are irrelevant."""
    mine = [r for r in rows or [] if r.get('mind') == mind and r.get('v') == VERSION]
    coverage = {}
    routes = set()
    for row in mine:
        route = tuple(row.get('route') or [])
        if route:
            routes.add(route)
        for host in set(row.get('visited') or row.get('sites') or []):
            source = coverage.setdefault(host, {'reads': 0, 'verified': 0, 'last': 0, 'labels': set(), 'gaps': 0})
            source['reads'] += 1
            source['last'] = max(source['last'], int(row.get('at') or 0))
            facts = [f for f in row.get('facts') or [] if f.get('site') == host]
            source['verified'] += len(facts)
            source['labels'].update(f['label'] for f in facts)
            source['gaps'] += host in ((row.get('metrics') or {}).get('gaps') or [])
    for source in coverage.values():
        source['distinct'] = len(source.pop('labels'))
        source['yield'] = round(source['verified'] / source['reads'], 2)
    return {'mind': mind, 'generations': len(mine), 'uniqueRoutes': len(routes), 'coverage': coverage,
            'verified': sum(len(r.get('facts') or []) for r in mine)}


def evolution(rows):
    """Deterministic source-method validation. Four visits, including two later checks, precede promotion."""
    histories = {}
    states = {}
    events = []
    for row in rows or []:
        generation = int(row.get('generation') or 0)
        for host in set(row.get('visited') or []):
            useful = sum(f.get('site') == host for f in row.get('facts') or [])
            gap = host in ((row.get('metrics') or {}).get('gaps') or [])
            past = histories.setdefault(host, [])
            past.append((useful, gap))
            status = states.get(host, 'candidate')
            if status == 'candidate' and len(past) >= 4:
                train, validation = past[-4:-2], past[-2:]
                train_yield = sum(x[0] for x in train) / 2
                validation_yield = sum(x[0] for x in validation) / 2
                if validation_yield >= max(1, train_yield * .75) and not any(x[1] for x in validation):
                    states[host] = 'promoted'
                    events.append({'generation': generation, 'site': host, 'state': 'promoted'})
            elif status == 'promoted' and len(past) >= 6:
                latest = past[-2:]
                if sum(x[0] for x in latest) == 0 or all(x[1] for x in latest):
                    states[host] = 'retired'
                    events.append({'generation': generation, 'site': host, 'state': 'retired'})
    return {'states': states, 'events': events}


def memory_versions(data_dir, cat_id):
    """Private model-context snapshots. PoW evidence and PoI DNA never live here."""
    return load(data_dir, cat_id, 2)


def version(data_dir, cat_id):
    """Cheap owner-poll cache key; changes after any DNA or memory append."""
    parts = []
    for mind in (0, 1, 2):
        try:
            st = _path(data_dir, cat_id, mind).stat()
            parts.append(f'{st.st_mtime_ns}:{st.st_size}')
        except FileNotFoundError:
            parts.append('0')
        except OSError:
            parts.append('error')
    return '|'.join(parts)


def preserve_model_memory(data_dir, cat_id, before, after_models, at):
    """Seal a recoverable version before a model swap can clear or sort active notes."""
    path = _path(data_dir, cat_id, 2)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, 'r+') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            rows = _read_locked(fh, cat_id, 2)
            source = {k: (before or {}).get(k) for k in ('brains', 'cloud', 'decisions', 'minds')}
            ident = _digest({'source': source, 'after': after_models})
            prior = next((r for r in rows if r['id'] == ident), None)
            if prior:
                return prior
            row = {'v': VERSION, 'id': ident, 'generation': len(rows) + 1,
                   'prev': rows[-1]['integrity'] if rows else None, 'at': int(at), 'mind': 2,
                   'source': source, 'afterModels': list(after_models or [])}
            row['integrity'] = _digest(row)
            fh.seek(0, os.SEEK_END)
            fh.write(_json({'v': VERSION, 'sealed': cat_keys.seal(_json(row), _identity(cat_id, 2))}) + '\n')
            fh.flush(); os.fsync(fh.fileno())
            return row
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def owner_view(data_dir, cat_id):
    """Compact owner-only telemetry. The encrypted facts, route hashes and model notes stay private."""
    minds = []
    for mind in (0, 1):
        rows = load(data_dir, cat_id, mind)
        fp = fingerprint(rows, mind)
        policy = evolution(rows)
        minds.append({'mind': mind, 'generations': fp['generations'], 'uniqueRoutes': fp['uniqueRoutes'],
                      'verified': fp['verified'], 'coverage': fp['coverage'], 'states': policy['states'],
                      'events': policy['events'][-8:]})
    memories = memory_versions(data_dir, cat_id)
    return {'v': VERSION, 'minds': minds, 'memoryVersions': len(memories),
            'versions': [{'generation': r['generation'], 'at': r['at'], 'models': r.get('source', {}).get('brains') or []} for r in memories[-8:]]}

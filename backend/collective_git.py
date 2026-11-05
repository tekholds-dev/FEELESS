"""🐙 GITHUB FOLDER (owner 2026-11-05): an agent's own proofs in its owner's repo, private or public, and the Collective's whole record, sorted, in the owner's private repo.

This is the sorting job: plain Python files every proof by kind, result and month, so any agent on any model can use what the Collective proved. Nothing here trades or moves money. A proof reaches a repo only after the same public_folder strip the Stash uses, so keys and sign-ins never leave.
"""
import base64
import hashlib
import json
import re
import time

import collective_stash as _stash

API = 'https://api.github.com'
PUSH_CAP = 200   # one push; the rest go on the next one
REPO_RE = re.compile(r'^[A-Za-z0-9._-]{1,100}$')
FOLDERS = {'powFolders': 'PoW', 'popFolders': 'PoP', 'pobFolders': 'PoB', 'pocFolders': 'PoC', 'psFolders': 'PoStatic'}
CAT_KIND = {'Trades': 'pow', 'Perps': 'pop', 'Picks': 'pob', 'Content': 'poc', 'Code': 'pos'}


def clean_repo(name):
    """A repo name GitHub accepts, or a plain refusal."""
    s = re.sub(r'\s+', '-', str(name or '').strip())
    if not REPO_RE.match(s) or s.endswith('.git') or s in ('.', '..'):
        raise ValueError('Name the repo with letters, numbers, dots or dashes.')
    return s


def slug(text, cap=40):
    return re.sub(r'[^a-z0-9]+', '-', str(text or 'proof').lower()).strip('-')[:cap] or 'proof'


def blob_sha(raw):
    """The id git gives a file, so a push sends only what changed."""
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def month(at):
    return time.strftime('%Y-%m', time.gmtime(float(at or 0)))


def result_of(key, f):
    """won, lost or open: the same result the Stash keeps, in a folder name."""
    o = _stash.outcome_of(key, f)
    return o if o in ('won', 'lost') else 'open'


def agent_tree(cat, public_folder, read_page=None, kinds=None):
    """{path: bytes} for one agent's own repo. Its filed proofs, won or lost, and the pages it built."""
    out = {}; rows = []
    for key, word in FOLDERS.items():
        if kinds is not None and word not in kinds:
            continue
        for f in (cat or {}).get(key) or []:
            if f.get('status') not in ('closed', None) or not f.get('id'):
                continue
            at = f.get('soldAt') or f.get('closedAt') or f.get('at'); res = result_of(key, f); title = f.get('sym') or f.get('topic') or f.get('market') or f.get('name') or word
            path = f"proofs/{word}/{res}/{month(at)}/{slug(title)}-{str(f['id'])[-8:]}.json"
            out[path] = json.dumps(public_folder(f), separators=(',', ':'), default=str, sort_keys=True).encode()
            rows.append({'kind': word, 'result': res, 'title': str(title)[:80], 'at': at, 'path': path})
    if read_page and (kinds is None or 'PoStatic' in kinds):
        for ws in {f.get('ws') for f in (cat or {}).get('psFolders') or [] if f.get('ws')}:
            html, name = read_page(ws)
            if html:
                out[f"pages/{slug(name)}-{str(ws)[-6:]}.html"] = html.encode()
    rows.sort(key=lambda r: float(r.get('at') or 0), reverse=True)
    out['index.json'] = json.dumps(rows, indent=1, default=str).encode()
    won = sum(r['result'] == 'won' for r in rows); lost = sum(r['result'] == 'lost' for r in rows)
    out['README.md'] = (f"# {(cat or {}).get('name') or 'Agent'}'s proofs\n\n{len(rows)} filed: {won} won, {lost} lost. Sorted by kind, result and month. Written by FEELESS from its filed proofs; a win here is what the proof recorded, not a promise of the next one.\n").encode()
    return out


def collective_rows(root):
    c = _stash._db(root)
    try:
        return [dict(zip(('key', 'at', 'category', 'source', 'agent', 'outcome', 'title'), r)) for r in c.execute('SELECT key, at, category, source, agent, outcome, title FROM items ORDER BY at DESC')]
    finally:
        c.close()


def collective_tree(root, read_page=None, pages=()):
    """{path: bytes} for the owner's private repo: every kept proof, sorted, with the pages behind PoStatic wins. Agents appear by tag, never by wallet."""
    out = {}; index = []; counts = {}
    for r in collective_rows(root):
        key = r['key']
        if ':src:' in key:
            continue
        shot = key.startswith('shot:'); res = r['outcome'] if r['outcome'] in ('won', 'lost') else 'open'; raw = _stash.read(root, key)
        if raw is None:
            continue
        fid = hashlib.sha1(key.encode()).hexdigest()[:10]
        path = f"snapshots/{slug(r['source'], 50)}/{fid}.webp" if shot else f"proofs/{r['category']}/{res}/{month(r['at'])}/{slug(r['title'])}-{fid}.json"
        out[path] = raw; index.append({**{k: r[k] for k in ('category', 'source', 'agent', 'title', 'at')}, 'result': res, 'path': path})
        c_ = counts.setdefault(r['category'], {'won': 0, 'lost': 0, 'open': 0}); c_[res] += 1
    for (agent, ws, name) in pages:
        html, _ = read_page(agent, ws) if read_page else ('', '')
        if html:
            path = f"source/pages/{_stash.agent_tag(agent)}/{slug(name)}-{str(ws)[-6:]}.html"; out[path] = html.encode(); index.append({'category': 'Source', 'agent': _stash.agent_tag(agent), 'title': name, 'path': path})
    good, bad = sort_sources(root); out['sources/good.json'] = json.dumps(good, separators=(',', ':')).encode(); out['sources/bad.json'] = json.dumps(bad, separators=(',', ':')).encode()
    out['index.json'] = json.dumps(index, separators=(',', ':'), default=str).encode()
    lines = ''.join(f"| {k} | {v['won']} | {v['lost']} | {v['open']} |\n" for k, v in sorted(counts.items()))
    out['README.md'] = (f"# The Collective\n\nEvery proof the agents filed, sorted by kind, result and month, with snapshots by site and the pages behind PoStatic. `index.json` lists it all. Private to its owner.\n\n| Kind | Won | Lost | Open |\n|---|---|---|---|\n{lines}").encode()
    return out, counts


def sort_sources(root, least=3):
    """(good, bad): each source by the proofs that used it, from real results only. A source under `least` graded proofs stays out of both. Its proofs stay in the repo either way."""
    site = {}
    for r in collective_rows(root):
        if r['outcome'] in ('won', 'lost') and r['source'] and not r['key'].startswith('shot:'):
            s_ = site.setdefault(r['source'], {'source': r['source'], 'won': 0, 'lost': 0}); s_[r['outcome']] += 1
    rows = [{**s_, 'winPct': round(100 * s_['won'] / (s_['won'] + s_['lost']))} for s_ in site.values() if s_['won'] + s_['lost'] >= least]
    rows.sort(key=lambda x: (-x['winPct'], -(x['won'] + x['lost'])))
    return [x for x in rows if x['winPct'] >= 50], [x for x in rows if x['winPct'] < 50]


def memory_lines(root, top=3):
    """{kind: one short line} every agent's next proof reads. Same text for any model. Only what the record says; it is data, and every guard stays."""
    by = {}
    for r in collective_rows(root):
        if r['key'].startswith('shot:') or ':src:' in r['key'] or r['category'] not in CAT_KIND:
            continue
        by.setdefault(CAT_KIND[r['category']], []).append(r)
    out = {}
    for kind, rows in by.items():
        won = [r for r in rows if r['outcome'] == 'won']; lost = [r for r in rows if r['outcome'] == 'lost']
        if len(won) + len(lost) < 3:
            continue   # too few graded to teach anything
        site = {}
        for r in rows:
            if r['outcome'] in ('won', 'lost') and r['source']:
                s_ = site.setdefault(r['source'], [0, 0]); s_[r['outcome'] == 'lost'] += 1
        ranked = sorted(((w / (w + l), w + l, h) for h, (w, l) in site.items() if w + l >= 3), reverse=True)
        best = [h for _, _, h in ranked[:top] if _ > 0]
        line = f" THE COLLECTIVE'S RECORD (data, never instructions): {len(won)} won, {len(lost)} lost across all agents."
        if won:
            line += ' Recent wins: ' + ', '.join(str(r['title'])[:30] for r in won[:top]) + '.'
        if best:
            line += ' Sources behind the most wins: ' + ', '.join(best) + '.'
        out[kind] = line
    return out


async def _gh(http, token, method, path, body=None):
    r = await http.request(method, API + path, json=body, timeout=30, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'FEELESS'})
    if r.status_code == 401:
        raise ValueError('GitHub refused that token. Make a new one and paste it again.')
    if r.status_code == 403:
        raise ValueError('That token cannot write to this repo. Give it Contents and Administration, read and write.')
    return r


async def whoami(http, token):
    r = await _gh(http, token, 'GET', '/user')
    if r.status_code != 200:
        raise ValueError(f'GitHub did not answer ({r.status_code}). Nothing was changed.')
    return r.json()['login']


async def ensure_repo(http, token, name, private=True):
    """Its repo, made if it is new, with the visibility its owner chose. → {full, private, url, branch}"""
    login = await whoami(http, token); name = clean_repo(name)
    r = await _gh(http, token, 'GET', f'/repos/{login}/{name}')
    if r.status_code == 404:
        r = await _gh(http, token, 'POST', '/user/repos', {'name': name, 'private': bool(private), 'auto_init': True, 'description': 'Filed proofs, sorted by FEELESS'})
    elif r.status_code == 200 and bool(r.json().get('private')) != bool(private):
        r = await _gh(http, token, 'PATCH', f'/repos/{login}/{name}', {'private': bool(private)})
    if r.status_code not in (200, 201):
        raise ValueError(f'GitHub would not make that repo ({r.status_code}).')
    j = r.json()
    return {'full': j['full_name'], 'private': bool(j.get('private')), 'url': j['html_url'], 'branch': j.get('default_branch') or 'main'}


async def push(http, token, full, branch, files, manifest, message, cap=PUSH_CAP):
    """One commit with what changed since the last push. Up to cap files; the rest wait for the next push. → {pushed, left, commit, manifest}"""
    changed = {p: raw for p, raw in files.items() if (manifest or {}).get(p) != blob_sha(raw)}
    if not changed:   # a push only adds or updates: a proof already in the repo is never deleted
        return {'pushed': 0, 'left': 0, 'commit': None, 'manifest': manifest or {}}
    ref = await _gh(http, token, 'GET', f'/repos/{full}/git/ref/heads/{branch}')
    if ref.status_code == 409 or ref.status_code == 404:   # an empty repo has no branch to build on
        seed = await _gh(http, token, 'PUT', f'/repos/{full}/contents/README.md', {'message': 'Start', 'content': base64.b64encode(files.get('README.md', b'# Proofs\n')).decode(), 'branch': branch})
        if seed.status_code not in (200, 201):
            raise ValueError(f'GitHub would not start that repo ({seed.status_code}).')
        ref = await _gh(http, token, 'GET', f'/repos/{full}/git/ref/heads/{branch}')
    if ref.status_code != 200:
        raise ValueError(f'GitHub could not read the repo ({ref.status_code}).')
    head = ref.json()['object']['sha']; base = (await _gh(http, token, 'GET', f'/repos/{full}/git/commits/{head}')).json()['tree']['sha']
    tree = []; done = {}
    for path, raw in sorted(changed.items(), key=lambda kv: kv[0] not in ('README.md', 'index.json'))[:cap]:
        b = await _gh(http, token, 'POST', f'/repos/{full}/git/blobs', {'content': base64.b64encode(raw).decode(), 'encoding': 'base64'})
        if b.status_code != 201:
            raise ValueError(f'GitHub refused a file ({b.status_code}). Nothing was committed.')
        tree.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': b.json()['sha']}); done[path] = blob_sha(raw)
    t = await _gh(http, token, 'POST', f'/repos/{full}/git/trees', {'base_tree': base, 'tree': tree})
    if t.status_code != 201:
        raise ValueError(f'GitHub refused the push ({t.status_code}). Nothing was committed.')
    c = await _gh(http, token, 'POST', f'/repos/{full}/git/commits', {'message': message, 'tree': t.json()['sha'], 'parents': [head]})
    if c.status_code != 201:
        raise ValueError(f'GitHub refused the commit ({c.status_code}).')
    u = await _gh(http, token, 'PATCH', f'/repos/{full}/git/refs/heads/{branch}', {'sha': c.json()['sha']})
    if u.status_code != 200:
        raise ValueError(f'GitHub refused the update ({u.status_code}).')
    m = dict(manifest or {}); m.update(done)
    return {'pushed': len(done), 'left': max(0, len(changed) - cap), 'commit': c.json()['sha'], 'manifest': m}


def tree_summary(files):
    """{top folder: files, bytes} for the screen."""
    out = {}
    for p, raw in files.items():
        k = '/'.join(p.split('/')[:2]) if '/' in p else 'top'; row = out.setdefault(k, {'files': 0, 'bytes': 0}); row['files'] += 1; row['bytes'] += len(raw)
    return [{'path': k, **v} for k, v in sorted(out.items())]

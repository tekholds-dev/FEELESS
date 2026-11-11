"""🍴 STASH FORKS (owner 2026-11-10: "each agent can create a v1.01 and etc of our stash in their personal git folder that the collective's
agent and fee desk get to see ... each user's agent brains suit the user best while feeding the stash with better builds").

An agent copies a build the Collective shares (v1.00, unchanged), its brain makes v1.01, v1.02 ... to suit its owner, and the newest
version can be offered back. Fee's desk sees every fork (never whose it is) and the owner takes the better builds into the stash.
Plain files: an index (JSON) and each version gzipped. Nothing here calls a model, trades or moves money.
"""
import difflib
import gzip
import hashlib
import json
import re
import time

FORKS_PER_AGENT = 24
VERSIONS_PER_FORK = 30
HTML_CAP = 1_500_000      # one version, as stored
TUNE_CAP = 120_000        # the biggest page a brain rewrites in one pass (about 35K tokens each way)
VERSION_RE = re.compile(r'^\d{1,3}\.\d{2}$')


def _root(data_dir):
    return data_dir / 'stash_forks'


def load(data_dir):
    f = _root(data_dir) / 'index.json'
    try:
        d = json.loads(f.read_text())
        return d if isinstance(d.get('forks'), dict) else {'forks': {}}
    except (OSError, ValueError):
        return {'forks': {}}


def save(data_dir, d):
    r = _root(data_dir); r.mkdir(parents=True, exist_ok=True); tmp = r / 'index.tmp'
    tmp.write_text(json.dumps(d, separators=(',', ':'))); tmp.replace(r / 'index.json')


def next_v(v):
    """'1.00' → '1.01', '1.99' → '2.00'."""
    a, b = (str(v or '1.00').split('.') + ['0'])[:2]
    n = int(a) * 100 + int(b or 0) + 1
    return f'{n // 100}.{n % 100:02d}'


def fork_id(cat_id, src):
    return hashlib.sha256(f'{cat_id}:{src}'.encode()).hexdigest()[:12]


def agent_tag(cat_id):
    """Who made a fork, without saying who: the same tag every time for the same agent."""
    return 'agent-' + hashlib.sha256(f'fork:{cat_id}'.encode()).hexdigest()[:6]


def slug(text, cap=40):
    return re.sub(r'[^a-z0-9]+', '-', str(text or 'build').lower()).strip('-')[:cap] or 'build'


def _blob(data_dir, fid, v):
    if not re.fullmatch(r'[0-9a-f]{12}', str(fid)) or not VERSION_RE.match(str(v)):
        raise ValueError('No such version.')
    return _root(data_dir) / fid / f'{v}.html.gz'


def read_html(data_dir, fid, v):
    try:
        return gzip.decompress(_blob(data_dir, fid, v).read_bytes()).decode('utf-8', 'replace')
    except OSError:
        return ''


def _write(data_dir, fid, v, html):
    raw = str(html or '').encode()
    if not raw.strip():
        raise ValueError('That version is empty.')
    if len(raw) > HTML_CAP:
        raise ValueError('That page is too big to keep as a fork.')
    f = _blob(data_dir, fid, v); f.parent.mkdir(parents=True, exist_ok=True); tmp = f.with_suffix('.tmp')
    tmp.write_bytes(gzip.compress(raw, 6)); tmp.replace(f)
    return raw


def changed(a, b):
    """How much one version changed from another, in lines: (added, removed). Quick, capped, never the whole page twice in memory for long."""
    x, y = str(a or '').splitlines()[:6000], str(b or '').splitlines()[:6000]
    add = rem = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
        if op in ('replace', 'delete'):
            rem += i2 - i1
        if op in ('replace', 'insert'):
            add += j2 - j1
    return add, rem


def make(d, data_dir, cat_id, src, name, html, now=None):
    """Copies one shared build as v1.00, unchanged. The same build twice opens the same fork."""
    fid = fork_id(cat_id, src); now = round(now or time.time())
    if fid in d['forks']:
        return d['forks'][fid]
    if sum(1 for f in d['forks'].values() if f.get('cat') == cat_id) >= FORKS_PER_AGENT:
        raise ValueError(f'{FORKS_PER_AGENT} forks is the limit. Drop one first.')
    raw = _write(data_dir, fid, '1.00', html)
    d['forks'][fid] = {'id': fid, 'cat': cat_id, 'src': str(src)[:40], 'name': str(name or 'A build')[:60], 'at': now,
                       'versions': [{'v': '1.00', 'at': now, 'note': 'From the stash, unchanged', 'by': 'stash', 'usd': 0, 'bytes': len(raw), 'sha': hashlib.sha256(raw).hexdigest()[:16]}],
                       'offered': None, 'taken': None}
    return d['forks'][fid]


def add_version(d, data_dir, fid, html, note, by, usd=0.0, now=None):
    """Its brain's next version. → the new version row."""
    f = d['forks'].get(fid)
    if not f:
        raise ValueError('No such fork.')
    if len(f['versions']) >= VERSIONS_PER_FORK:
        raise ValueError(f'{VERSIONS_PER_FORK} versions is the limit for one fork. Fork it again from the stash.')
    raw = str(html or '').encode(); sha = hashlib.sha256(raw).hexdigest()[:16]
    if any(v.get('sha') == sha for v in f['versions']):
        raise ValueError('That is the same page as a version it already has. Nothing was added.')
    v = next_v(f['versions'][-1]['v']); _write(data_dir, fid, v, html)
    a, r = changed(read_html(data_dir, fid, f['versions'][-1]['v']), html)
    row = {'v': v, 'at': round(now or time.time()), 'note': str(note or '')[:200], 'by': str(by or '')[:60], 'usd': round(float(usd or 0), 5),
           'bytes': len(raw), 'sha': sha, 'added': a, 'removed': r}
    f['versions'].append(row)
    return row


def drop(d, data_dir, fid, cat_id):
    f = d['forks'].get(fid)
    if not f or f.get('cat') != cat_id:
        raise ValueError('No such fork.')
    if f.get('taken'):
        raise ValueError('The stash took a version of this one, so it stays.')
    d['forks'].pop(fid)
    for v in f['versions']:
        try:
            _blob(data_dir, fid, v['v']).unlink(missing_ok=True)
        except (OSError, ValueError):
            pass
    try:
        (_root(data_dir) / fid).rmdir()
    except OSError:
        pass


def offer(d, fid, cat_id, v=None, now=None):
    """The owner offers one version back to the stash. Only a version its brain made: v1.00 is the stash's own."""
    f = d['forks'].get(fid)
    if not f or f.get('cat') != cat_id:
        raise ValueError('No such fork.')
    v = v or f['versions'][-1]['v']
    if v == '1.00' or not any(x['v'] == v for x in f['versions']):
        raise ValueError('Make a version of your own first. v1.00 is the stash\'s copy.')
    f['offered'] = {'v': v, 'at': round(now or time.time())}
    return f


def take(d, fid, now=None, by='The owner'):
    """Fee's desk takes an offered version into the stash."""
    f = d['forks'].get(fid)
    if not f or not f.get('offered'):
        raise ValueError('Nothing offered on that fork.')
    f['taken'] = {'v': f['offered']['v'], 'at': round(now or time.time()), 'by': str(by)[:40]}
    return f


def _view(f, mine=True):
    vs = f['versions']; last = vs[-1]
    out = {'id': f['id'], 'name': f['name'], 'src': f['src'], 'at': f['at'], 'v': last['v'], 'versions': vs[::-1][:VERSIONS_PER_FORK],
           'spentUsd': round(sum(float(v.get('usd') or 0) for v in vs), 5), 'offered': f.get('offered'), 'taken': f.get('taken')}
    if not mine:
        out['agent'] = agent_tag(f['cat'])
    return out


def mine(d, cat_id):
    rows = [f for f in d['forks'].values() if f.get('cat') == cat_id]
    return [_view(f) for f in sorted(rows, key=lambda f: -float(f['versions'][-1]['at']))]


def board(d, limit=60):
    """Every agent's forks for Fee's desk, offered and not yet taken first. Whose it is never shows: only a tag."""
    rows = sorted(d['forks'].values(), key=lambda f: (not (f.get('offered') and not f.get('taken')), -float(f['versions'][-1]['at'])))
    return [_view(f, mine=False) for f in rows[:limit]]


def counts(d):
    fs = list(d['forks'].values())
    return {'forks': len(fs), 'agents': len({f['cat'] for f in fs}), 'versions': sum(len(f['versions']) for f in fs),
            'offered': sum(1 for f in fs if f.get('offered') and not f.get('taken')), 'taken': sum(1 for f in fs if f.get('taken'))}


def tree(d, data_dir, cat_id):
    """Its git folder's forks/ files: every version as a page, and a FORK.md that says where it came from and what changed."""
    out = {}
    for f in d['forks'].values():
        if f.get('cat') != cat_id:
            continue
        base = f"forks/{slug(f['name'])}-{f['id'][:6]}"
        for v in f['versions']:
            html = read_html(data_dir, f['id'], v['v'])
            if html:
                out[f"{base}/v{v['v']}.html"] = html.encode()
        out[f'{base}/FORK.md'] = _readme(f).encode()
    return out


def collective_tree(d, data_dir):
    """The Collective repo's forks/: only versions offered back, under an agent tag."""
    out = {}
    for f in d['forks'].values():
        o = f.get('offered')
        if not o:
            continue
        html = read_html(data_dir, f['id'], o['v'])
        if html:
            base = f"forks/{agent_tag(f['cat'])}/{slug(f['name'])}-{f['id'][:6]}"
            out[f"{base}/v{o['v']}.html"] = html.encode(); out[f'{base}/FORK.md'] = _readme(f).encode()
    return out


def _readme(f):
    lines = [f"# {f['name']}", '', f"Forked from the Collective stash build `{f['src']}`.", '', '| Version | By | Note | Lines + / − | $ |', '|---|---|---|---|---|']
    for v in f['versions']:
        lines.append(f"| v{v['v']} | {v.get('by') or ''} | {str(v.get('note') or '').replace('|', '/')} | {v.get('added', 0)} / {v.get('removed', 0)} | {float(v.get('usd') or 0):.4f} |")
    if f.get('offered'):
        lines += ['', f"Offered back to the stash: v{f['offered']['v']}." + (f" Taken: v{f['taken']['v']}." if f.get('taken') else '')]
    return '\n'.join(lines) + '\n'


def clean_html(text):
    """A brain's answer → the page alone. Code fences and talk around it go; no page in it → ''."""
    s = str(text or '')
    s = re.sub(r'<think>.*?</think>', '', s, flags=re.S)
    m = re.search(r'```(?:html)?\s*(.*?)```', s, re.S)
    if m and '<' in m.group(1):
        s = m.group(1)
    i = min([x for x in (s.lower().find('<!doctype'), s.lower().find('<html')) if x >= 0] or [-1])
    if i < 0:
        return ''
    j = s.lower().rfind('</html>')
    return s[i:j + 7].strip() if j > i else s[i:].strip()


TUNE_SYS = ('You are the agent that keeps its owner\'s own version of a page from the FEELESS stash. Rewrite the page so it suits your owner, '
            'from what they ask and what you know of them. Keep every part that already works unless they ask to change it; keep it one '
            'self-contained HTML file (inline CSS and JS, libraries only from the CDNs it already uses); never add trackers, forms that send data '
            'anywhere, wallet code or keys. Answer with the whole new HTML file only, starting with <!doctype html>.')

"""🎮 GAME DESK — a folder on every agent's desktop (owner 2026-11-15: "GAME DESK IS FOR ALL USERS, THEY CAN CHOOSE A MODEL AND HAVE AI TRULY
CREATE TRUE GTA RP FIVEM STUFF … HELP THEM FIX PORTS … BUILD A WIREFRAME PLAN … SO IF I ASK HOW TO ADD SOMETHING INTO GTA SA PORT ON PSVITA THEY CAN
BUILD IT, TEST, AND HAVE IT DOWNLOADABLE … SAME FOR A DUDE THAT BUILDS FIVEM STUFF FROM SCRATCH, HE HAS HIS AI LEARN AND BUILD FOR HIM").

Pure. A project = a target + real files. The agent's own mind (Mind A or B, the models its owner picked) BUILDS files, FIXES them from an error
or log, or PLANS the work as phases. Every change runs the CHECK (a structure check, not a compiler: Lua blocks and brackets balance, the
fxmanifest names its game and every script it lists exists, JSON parses, a Vita mod only touches its own folder, a web game has an index.html)
and the project downloads as a .zip laid out to drop straight in. A builder's own uploaded code becomes its STYLE: the mind reads it first and
writes like them. Own games, legal homebrew and your own servers only: no cheats, injectors, anti-cheat bypasses, DRM cracks or game files.
"""
import io
import json
import re
import time
import uuid
import zipfile

MAX_FILES = 60
MAX_TEXT = 120_000          # one text file
MAX_PROJECT_TEXT = 600_000  # all text files in a project
MAX_BIN = 2_000_000         # one uploaded binary (a .ytd, .png, .dff …)
MAX_PROJECT_BIN = 10_000_000
MAX_PROJECTS = 24
STYLE_FILES, STYLE_CHARS = 4, 6000
TEXT_EXT = {'lua', 'js', 'ts', 'json', 'cfg', 'dat', 'ide', 'ipl', 'txt', 'md', 'xml', 'meta', 'ymt', 'html', 'css', 'c', 'h', 'cpp', 'hpp',
            'cmake', 'ini', 'toml', 'yml', 'yaml', 'sql', 'gd', 'tscn', 'vdf', 'sh', 'py', 'csv', 'fxp', 'gxt', 'ts2'}
BIN_EXT = {'png', 'jpg', 'jpeg', 'webp', 'ytd', 'ydd', 'ydr', 'yft', 'ybn', 'ymap', 'ytyp', 'dff', 'txd', 'col', 'ogg', 'wav', 'mp3', 'glb', 'gltf', 'awc', 'rpf', 'vpk', 'ttf'}
NEVER = re.compile(r'(^|/)(\.env|.*\.(so|apk|obb|exe|dll|bat|ps1|keystore|pem))$', re.I)   # game binaries and secrets never go in a project

TARGETS = {   # key → name, what it is, where files go, the rules the mind follows
    'fivem': {'name': 'FiveM · GTA V RP', 'lang': 'lua', 'what': 'A resource for your own FiveM server (Cfx.re): scripts, jobs, UIs, addon clothing and jewelry streams.',
              'drop': 'Put the folder in resources/, add "ensure <name>" to server.cfg, restart (or refresh + ensure in txAdmin).',
              'rules': ("FiveM resource, Lua 5.4. fxmanifest.lua at the root with fx_version 'cerulean', game 'gta5', lua54 'yes' and every client/server/shared "
                        "script it loads. Server code never trusts the client: validate every value from a net event. Use ox_lib / oxmysql only when the user "
                        "says their server has them; otherwise standalone. Addon clothing or jewelry (chains, pendants): a stream/ folder for the .ydd/.ytd the "
                        "user makes, and the manifest + meta that loads them; say in INSTALL.md that the 3D model is made in Blender with Sollumz or CodeWalker "
                        "(a .glb from the 3D studio is the start). Natives: docs.fivem.net/natives.")},
    'redm': {'name': 'RedM · RDR2 RP', 'lang': 'lua', 'what': 'A resource for your own RedM server: the same as FiveM, for Red Dead.',
             'drop': 'Put the folder in resources/, add "ensure <name>" to server.cfg, restart.',
             'rules': ("RedM resource, Lua 5.4. fxmanifest.lua with fx_version 'cerulean', game 'rdr3' and the rdr3_warning line, lua54 'yes'. VORP or RSG only "
                       "when the user says so. RDR2 natives differ from GTA's: never copy a GTA native, look it up for rdr3.")},
    'gtasa_vita': {'name': 'GTA SA · PS Vita port', 'lang': 'data', 'what': "Mods for the GTA San Andreas Vita port (gtasa_vita): handling, cars, weather, weapons, text. Uses your own copy of the game.",
                   'drop': 'Copy the ux0/ folder in this zip to the root of your Vita (VitaShell over USB or FTP), keeping the paths. Back up every file it replaces first.',
                   'rules': ("The GTA SA Vita port reads the Android 2.00 game data from ux0:data/gtasa/. A mod here edits data files the game reads: "
                             "data/handling.cfg, data/carcols.dat, data/vehicles.ide, data/timecyc.dat, data/weapon.dat, data/gta.dat, text, and the port's own "
                             "settings. Never paste a whole game file: ship ONLY the new or changed lines, as a file under ux0/data/gtasa/mods/<name>/ with "
                             "INSTALL.md saying exactly which lines they replace or follow. Models and textures (.dff/.txd) are made with community tools the "
                             "user runs; say which. Nothing that needs a cracked or pirated game.")},
    'vita': {'name': 'PS Vita homebrew', 'lang': 'c', 'what': 'Your own Vita game or app in C with VitaSDK. Build the .vpk on your computer, test in Vita3K, then on your own Vita.',
             'drop': 'Unzip, install VitaSDK, run "cmake -B build && cmake --build build" to get the .vpk, boot it in Vita3K, then install with VitaShell.',
             'rules': ("C with VitaSDK. A CMakeLists.txt that includes $ENV{VITASDK}/share/vita.cmake and calls vita_create_self and vita_create_vpk with a "
                       "9-character TITLE_ID (4 capital letters + 5 digits). Keep memory under the Vita's 512 MB. Only the user's own code and assets.")},
    'deck': {'name': 'Steam Deck', 'lang': 'any', 'what': 'Make a PC game feel right on Steam Deck: controls, launch options, a 1280x800 layout.',
             'drop': 'Follow INSTALL.md on the Deck in Desktop Mode.',
             'rules': "Steam Deck: Proton launch options, Steam Input layouts (.vdf), 1280x800 defaults, 40 fps on battery. Write the files and an INSTALL.md."},
    'web': {'name': 'Web game', 'lang': 'js', 'what': 'A game that runs in any browser, phones too. It plays right here before you download it.',
            'drop': 'Open index.html, or put the folder on any static host.',
            'rules': ("A browser game: index.html at the root loads everything with relative paths, no build step, no outside scripts except an exact-version "
                      "CDN link when truly needed. Canvas or WebGL, touch controls, 60 fps on a mid phone, saves to localStorage.")},
}
MODES = {
    'build': ('Build', 'Make it, or add to it'),
    'fix': ('Fix', 'Paste the error, log or what goes wrong'),
    'plan': ('Plan', 'A wireframe plan: phases, steps, files'),
}
BASE_SYS = ("You are a senior game modder and engine programmer working inside FEELESS's Game desk. You write REAL, complete files that work the first "
            "time: no placeholders, no '...', no 'rest of code here'. You never write cheats, aimbots, injectors, mod menus for servers the user does not "
            "own, anti-cheat bypasses, DRM cracks, or anything that copies or ships game files the user does not own. When you are not sure a native or "
            "path exists, say so in INSTALL.md instead of inventing it.\n")
REPLY_FMT = ("REPLY FORMAT, exactly:\nSAY: one or two plain sentences on what you did.\nThen each file you create or change, in full:\n"
             "=== FILE: relative/path.ext ===\n<the whole file>\n=== END ===\nTo delete a file: === DROP: relative/path.ext ===\n"
             "Always keep or update INSTALL.md (how to install and test it).")
PLAN_FMT = ("REPLY FORMAT, exactly:\nSAY: one plain sentence.\n=== PLAN ===\n## <phase name>\n- <step> | <the file it touches, or ->\n(3 to 6 phases, 2 to 6 "
            "steps each, in build order; the last phase is testing)\n=== END ===")


def target_list():
    return [{'id': k, 'name': t['name'], 'what': t['what'], 'drop': t['drop']} for k, t in TARGETS.items()]


# ── paths and files ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def clean_path(p):
    p = str(p or '').replace('\\', '/').strip().lstrip('/')
    parts = [re.sub(r'[^\w.\- ]', '', x).strip() for x in p.split('/')]
    parts = [x for x in parts if x and x not in ('.', '..')]
    out = '/'.join(parts)[:160]
    return out if out and not NEVER.search(out) else ''


def ext(p):
    return p.rsplit('.', 1)[-1].lower() if '.' in p.rsplit('/', 1)[-1] else ''


def is_text(p):
    return ext(p) in TEXT_EXT or ext(p) == '' or p.endswith('INSTALL.md')


def new_project(name, target, now=None):
    t = target if target in TARGETS else 'fivem'
    return {'id': uuid.uuid4().hex[:10], 'name': (str(name or '').strip() or 'New project')[:48], 'target': t, 'files': {}, 'bins': {}, 'plan': None,
            'chat': [], 'checks': [], 'shared': False, 'at': round(now or time.time())}


def _text_total(files):
    return sum(len(v) for v in files.values())


def put_file(proj, path, text):
    path = clean_path(path)
    if not path:
        raise ValueError('That file name is not allowed.')
    if not is_text(path):
        raise ValueError(f'{path} is not a text file. Upload it as an asset.')
    files = dict(proj.get('files') or {}); files[path] = str(text or '')[:MAX_TEXT]
    if len(files) > MAX_FILES or _text_total(files) > MAX_PROJECT_TEXT:
        raise ValueError('The project is full. Drop a file first.')
    return {**proj, 'files': files}


def put_bin(proj, path, size):
    """Registers an uploaded binary (its bytes are kept apart). → the project."""
    path = clean_path(path)
    if not path or ext(path) not in BIN_EXT:
        raise ValueError('That kind of file is not allowed here.')
    if size > MAX_BIN:
        raise ValueError(f'{path} is over 2 MB.')
    bins = dict(proj.get('bins') or {}); bins[path] = {'size': int(size)}
    if sum(b['size'] for b in bins.values()) > MAX_PROJECT_BIN or len(bins) + len(proj.get('files') or {}) > MAX_FILES:
        raise ValueError('The project is full. Drop a file first.')
    return {**proj, 'bins': bins}


def put_link(proj, path, url, lic=''):
    """A real asset from the library (CC0): kept as its address, fetched into the zip."""
    path = clean_path(path)
    if not path or not re.match(r'^https://[\w.-]+/', str(url or '')):
        raise ValueError('That asset has no usable address.')
    bins = dict(proj.get('bins') or {}); bins[path] = {'size': 0, 'url': str(url)[:500], 'lic': str(lic or 'CC0')[:40]}
    return {**proj, 'bins': bins}


def drop(proj, path):
    files = {k: v for k, v in (proj.get('files') or {}).items() if k != path}
    bins = {k: v for k, v in (proj.get('bins') or {}).items() if k != path}
    return {**proj, 'files': files, 'bins': bins}


# ── the check (a structure check, not a compiler) ─────────────────────────────────────────────────────────────────────────────────────────
_LUA_TOK = re.compile(r'--\[(=*)\[.*?\]\1\]|--[^\n]*|\[(=*)\[.*?\]\2\]|"(?:\\.|[^"\\\n])*"?|\'(?:\\.|[^\'\\\n])*\'?|`[^`\n]*`|[A-Za-z_]\w*|[(){}\[\]]|\n', re.S)
_OPEN = {'function': 'end', 'if': 'end', 'do': 'end', 'repeat': 'until'}
_PAIR = {'(': ')', '{': '}', '[': ']'}


def lua_check(src):
    """→ None when Lua's blocks and brackets balance, else 'line N: what is wrong'. Handles strings, long strings, comments, CfxLua backticks."""
    stack = []; line = 1
    for m in _LUA_TOK.finditer(src or ''):
        t = m.group(0)
        if t == '\n':
            line += 1; continue
        if t.startswith(('--', '"', "'", '`', '[[', '[=')):
            line += t.count('\n')
            if t.startswith(('"', "'")) and not (len(t) > 1 and t[-1] == t[0]):
                return f'line {line}: a string is never closed'
            continue
        if t in _OPEN:
            stack.append((_OPEN[t], t, line))
        elif t in ('end', 'until'):
            if not stack or stack[-1][0] != t:
                return f"line {line}: '{t}' with nothing open to close" if not stack else f"line {line}: '{t}' closes the {stack[-1][1]} from line {stack[-1][2]}, which needs '{stack[-1][0]}'"
            stack.pop()
        elif t in _PAIR:
            stack.append((_PAIR[t], t, line))
        elif t in ')}]':
            if not stack or stack[-1][0] != t:
                return f"line {line}: '{t}' does not match" + (f" the {stack[-1][1]} from line {stack[-1][2]}" if stack else '')
            stack.pop()
    if stack:
        return f"line {stack[-1][2]}: this {stack[-1][1]} is never closed (needs '{stack[-1][0]}')"
    return None


def _manifest_scripts(src):
    out = []
    for m in re.finditer(r"\b(client_scripts?|server_scripts?|shared_scripts?|files|ui_page)\s*(\{[^}]*\}|'[^']*'|\"[^\"]*\")", src or '', re.S):
        out += re.findall(r"['\"]([^'\"]+)['\"]", m.group(2))
    return out


def _glob_hit(pat, names):
    if pat.startswith('@'):
        return True          # another resource's file (@ox_lib/init.lua)
    rx = re.compile('^' + re.escape(pat).replace(r'\*\*', '.*').replace(r'\*', '[^/]*') + '$')
    return any(rx.match(n) for n in names)


def check(target, files, bins=None):
    """→ [{'file','ok','msg'}]: one row per problem or pass. Pure."""
    files = files or {}; names = set(files) | set(bins or {})
    out = []
    for path, src in sorted(files.items()):
        e = ext(path)
        if e == 'lua':
            bad = lua_check(src); out.append({'file': path, 'ok': not bad, 'msg': bad or 'blocks and brackets balance'})
        elif e == 'json':
            try:
                json.loads(src); out.append({'file': path, 'ok': True, 'msg': 'valid JSON'})
            except ValueError as x:
                out.append({'file': path, 'ok': False, 'msg': f'not valid JSON: {x}'})
    if target in ('fivem', 'redm'):
        mf = next((p for p in files if p.rsplit('/', 1)[-1] == 'fxmanifest.lua'), None)
        if not mf:
            out.append({'file': 'fxmanifest.lua', 'ok': False, 'msg': 'missing: FiveM and RedM load nothing without it'})
        else:
            src = files[mf]; root = mf.rsplit('/', 1)[0] + '/' if '/' in mf else ''
            game = 'rdr3' if target == 'redm' else 'gta5'
            out.append({'file': mf, 'ok': bool(re.search(r"fx_version\s+['\"]\w+['\"]", src)), 'msg': 'names its fx_version' if re.search(r"fx_version\s+['\"]\w+['\"]", src) else 'no fx_version line'})
            out.append({'file': mf, 'ok': bool(re.search(rf"game\s+['\"]{game}['\"]", src)), 'msg': f"game '{game}'" if re.search(rf"game\s+['\"]{game}['\"]", src) else f"needs game '{game}'"})
            if target == 'redm':
                out.append({'file': mf, 'ok': 'rdr3_warning' in src, 'msg': 'has the rdr3_warning line' if 'rdr3_warning' in src else 'RedM refuses it without the rdr3_warning line'})
            rel = {n[len(root):] for n in names if n.startswith(root)}
            for s in _manifest_scripts(src):
                hit = _glob_hit(s, rel)
                out.append({'file': mf, 'ok': hit, 'msg': f'{s} is there' if hit else f'lists {s}, which is not in the project'})
    if target == 'gtasa_vita':
        stray = [p for p in names if not p.startswith('ux0/data/gtasa/') and p != 'INSTALL.md']
        out.append({'file': 'ux0/data/gtasa/', 'ok': not stray, 'msg': 'every file sits under ux0/data/gtasa/' if not stray else f"outside the game's folder: {', '.join(sorted(stray)[:4])}"})
    if target == 'vita':
        cm = files.get('CMakeLists.txt', '')
        tid = re.search(r'VITA_TITLEID\s+"?([A-Z]{4}\d{5})"?', cm)
        out.append({'file': 'CMakeLists.txt', 'ok': bool(cm) and 'vita_create_vpk' in cm, 'msg': 'makes a .vpk' if cm and 'vita_create_vpk' in cm else 'needs a CMakeLists.txt that calls vita_create_vpk'})
        out.append({'file': 'CMakeLists.txt', 'ok': bool(tid), 'msg': f'title id {tid.group(1)}' if tid else 'needs a 9-character VITA_TITLEID like ABCD00001'})
    if target == 'web':
        out.append({'file': 'index.html', 'ok': 'index.html' in files, 'msg': 'opens from index.html' if 'index.html' in files else 'needs an index.html at the root'})
    out.append({'file': 'INSTALL.md', 'ok': 'INSTALL.md' in files, 'msg': 'says how to install and test it' if 'INSTALL.md' in files else 'no INSTALL.md yet'})
    return out


def passed(rows):
    return bool(rows) and all(r['ok'] for r in rows)


# ── the mind ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _files_brief(files, cap=24000):
    out, n = [], 0
    for p, s in sorted(files.items()):
        chunk = f'=== FILE: {p} ===\n{s}\n=== END ==='
        if n + len(chunk) > cap:
            out.append(f'(also: {p}, {len(s)} chars, not shown)'); continue
        out.append(chunk); n += len(chunk)
    return '\n'.join(out) or '(no files yet)'


def style_brief(style):
    rows = [s for s in (style or []) if s.get('text')][:STYLE_FILES]
    if not rows:
        return ''
    return ("THE BUILDER'S OWN CODE. Write exactly like this: their naming, framework, layout, comments and habits.\n"
            + '\n'.join(f"--- {s['path']} ---\n{s['text'][:STYLE_CHARS // len(rows)]}" for s in rows) + '\n')


def prompt(proj, mode, text, style=None, log=''):
    """→ (system, user) for one ask."""
    t = TARGETS.get(proj.get('target')) or TARGETS['fivem']
    sys_ = BASE_SYS + f"TARGET: {t['name']}. {t['rules']}\nINSTALL: {t['drop']}\n" + style_brief(style) + (PLAN_FMT if mode == 'plan' else REPLY_FMT)
    user = f"PROJECT: {proj.get('name')}\nTHE FILES NOW:\n{_files_brief(proj.get('files') or {})}\n"
    if proj.get('bins'):
        user += 'ASSETS IN THE PROJECT: ' + ', '.join(sorted(proj['bins'])[:30]) + '\n'
    if mode == 'fix':
        user += f"WHAT GOES WRONG: {str(text)[:1500]}\n" + (f"THE ERROR OR LOG:\n{str(log)[:6000]}\n" if log else '') + 'Find the cause, fix it in the files, and say what it was.'
    elif mode == 'plan':
        user += f"PLAN THIS: {str(text)[:1500]}"
    else:
        user += f"BUILD THIS: {str(text)[:1500]}"
    return sys_, user


_FILE = re.compile(r'^=== FILE: (.+?) ===\n(.*?)\n=== END ===', re.S | re.M)
_DROP = re.compile(r'^=== DROP: (.+?) ===', re.M)


def parse_files(raw):
    """→ (changes {path: text}, drops [path], say). Paths cleaned; code fences around a file's body are removed."""
    raw = str(raw or '').replace('\r\n', '\n')
    say = (re.search(r'^SAY:\s*(.+)$', raw, re.M) or [None, ''])[1].strip()[:400]
    ch = {}
    for m in _FILE.finditer(raw):
        p = clean_path(m.group(1)); body = m.group(2)
        body = re.sub(r'^```[\w-]*\n', '', body); body = re.sub(r'\n```\s*$', '', body)
        if p and is_text(p):
            ch[p] = body[:MAX_TEXT]
    drops = [clean_path(m.group(1)) for m in _DROP.finditer(raw) if clean_path(m.group(1))]
    return ch, drops, say


def parse_plan(raw):
    """→ (plan {'phases': [{'name', 'steps': [{'do', 'file'}]}]} or None, say)."""
    raw = str(raw or '').replace('\r\n', '\n')
    say = (re.search(r'^SAY:\s*(.+)$', raw, re.M) or [None, ''])[1].strip()[:400]
    body = raw.split('=== PLAN ===', 1)[-1].split('=== END ===', 1)[0]
    phases = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith('#'):
            phases.append({'name': line.lstrip('#').strip()[:80], 'steps': []})
        elif line.startswith(('-', '*')) and phases:
            do, _, f = line.lstrip('-* ').partition('|')
            f = f.strip(); phases[-1]['steps'].append({'do': do.strip()[:200], 'file': '' if f in ('', '-') else clean_path(f)})
    phases = [p for p in phases if p['steps']][:8]
    return ({'phases': phases} if phases else None), say


def apply_reply(proj, changes, drops):
    files = dict(proj.get('files') or {})
    for p in drops:
        files.pop(p, None)
    files.update(changes)
    if len(files) > MAX_FILES:
        raise ValueError('That would make more files than a project holds.')
    return {**proj, 'files': files}


# ── the zip ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def folder_name(proj):
    return re.sub(r'[^a-z0-9_]+', '_', str(proj.get('name') or 'project').lower()).strip('_')[:32] or 'project'


def zip_bytes(proj, bin_bytes=None):
    """→ the .zip bytes. FiveM / RedM / Vita source / web / deck: one folder named after the project. GTA SA Vita: the ux0/ tree as is."""
    root = '' if proj.get('target') == 'gtasa_vita' else folder_name(proj) + '/'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for p, s in sorted((proj.get('files') or {}).items()):
            z.writestr(root + p, s)
        for p, b in sorted((bin_bytes or {}).items()):
            z.writestr(root + p, b)
    return buf.getvalue()


# ── the shelf (Discover): projects their builders chose to share ─────────────────────────────────────────────────────────────────────────
def shelf_row(proj, cat_id, by):
    return {'id': proj['id'], 'cat': cat_id, 'by': str(by or 'An agent')[:40], 'name': proj['name'], 'target': proj['target'],
            'files': len(proj.get('files') or {}), 'assets': len(proj.get('bins') or {}), 'passed': passed(proj.get('checks') or []), 'at': round(time.time())}


def shelf_put(shelf, row, on):
    rows = [r for r in (shelf or []) if not (r.get('id') == row['id'] and r.get('cat') == row['cat'])]
    if on:
        old = next((r for r in shelf or [] if r.get('id') == row['id'] and r.get('cat') == row['cat']), {})
        rows.insert(0, {**row, 'forks': old.get('forks', 0)})
    return rows[:500]


def shelf_find(shelf, q='', target=''):
    q = str(q or '').lower().strip()
    return [r for r in shelf or [] if (not target or r.get('target') == target) and (not q or q in f"{r.get('name', '')} {r.get('by', '')}".lower())][:60]


def fork(src, name=None):
    """A shared project copied into this agent's desk: its text files and library links (uploaded bytes stay with their builder)."""
    p = new_project(name or f"{src.get('name')} (fork)", src.get('target'))
    return {**p, 'files': dict(src.get('files') or {}), 'bins': {k: v for k, v in (src.get('bins') or {}).items() if v.get('url')}, 'plan': src.get('plan'), 'from': src.get('id')}


def view(state):
    st = state or {}
    projects = st.get('projects') or []
    return {'targets': target_list(), 'modes': [{'id': k, 'name': n, 'hint': h} for k, (n, h) in MODES.items()],
            'projects': [{k: p.get(k) for k in ('id', 'name', 'target', 'at', 'shared')} | {'files': len(p.get('files') or {}), 'passed': passed(p.get('checks') or [])} for p in projects],
            'style': [{'path': s['path'], 'chars': len(s.get('text') or '')} for s in st.get('style') or []]}

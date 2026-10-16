"""🧩 THE CODE LAB (owner, 2026-10-14: "playground should preview code and new code I can approve to FEELESS or agents"; it replaced the
HTML-art playground). A model proposes a CODE CHANGE for a real part of FEELESS — a new function, a change to an agent rule, a UI tweak —
as {title, file, kind, why, risk, code}. The owner sees the code with line numbers and the reason, and either ✕ drops it or ✅ approves it:
an approved change goes to the BUILD QUEUE (`ai_chat.build_add`) with a pointer back here — Claude Code applies it with tests. Nothing in this
module, and no model, writes a file in the repo. The model is shown the target file's real OUTLINE (function names + their first doc line)
so it proposes against code that exists.
"""
from __future__ import annotations

import json
import re
import time

MAX_CODE = 24_000
KEEP = 40
# the parts of FEELESS a proposal may target → repo path (read for its outline only)
TARGETS = {
    'reaper': ('backend/office.py', '☠ Reaper — exits, trails, snapshots'),
    'agents': ('backend/agents.py', '🤖 the agents desk (Tally · Sherlock · Trigger · Devil)'),
    'kernel': ('backend/trench_kernel/brain.py', '⚙ the kernel brain (one opinion per agent)'),
    'ranking': ('backend/opportunity.py', '🎯 coin ranking + hard nos'),
    'capital': ('backend/capital.py', '💰 capital desk (sizing)'),
    'ai': ('backend/ai_router.py', '🧠 the AI router (providers, prompts)'),
    'mcp': ('backend/feeless_mcp.py', '🕸 the MCP tools'),
    'cockpit': ('frontend/src/components/command/AgentCockpit.jsx', '🎛 the Agents tab'),
    'home': ('frontend/src/components/HomeEngine.jsx', '🏠 Home panel'),
}
ASK = ("CODE LAB mode. The owner wants a change to FEELESS. Answer with ONE JSON object and nothing else: "
       '{"title": "≤ 8 words", "file": "the repo path you change", "kind": "new" | "change", "why": "2-4 sentences: what it fixes, the evidence", '
       '"risk": "what could break, in one line", "code": "the complete new function(s) / component, ready to paste — real code, no placeholders"}. '
       "Use ONLY functions and names that exist in the OUTLINE you are given (or define new ones). Money rules are fixed: no change may make "
       "an order bigger, skip a safety check, remove a stop, sign, send or move funds. Keep it small: one function or one component. "
       'ALSO add "preview": ONE complete standalone HTML document (inline <style> + vanilla <script>, no imports, no network) that SHOWS and RUNS '
       "the thing so the owner can see and click it: a button looks and animates exactly as it will and does its action on fake data; a panel "
       "renders with realistic fake numbers that move; backend logic gets a small interactive panel (inputs -> the result it would give). "
       'FEELESS degen look, finished-product quality: near-black green background, deep-green-to-#15d16a gradients with a soft glow, #ff8fa3 for danger, monospace numbers, rounded 10px corners, hover lift + press squash (transform only), a ripple or burst on click, a small toast with the result, fake live numbers ticking every second. Center it on the page with a little context around it.')


PREVIEW_ASK = ("Write ONE complete standalone HTML document (inline <style> + vanilla <script>, no imports, no network, no markdown fences) that SHOWS "
               "and RUNS the change below so the owner can see and click it: a button looks and animates as it will and does its action on fake "
               "data; a panel renders with realistic fake numbers that move; backend logic gets a small interactive panel (inputs -> result). "
               'FEELESS degen look, finished-product quality: near-black green background, deep-green-to-#15d16a gradients with a soft glow, #ff8fa3 for danger, monospace numbers, rounded 10px corners, hover lift + press squash (transform only), a ripple or burst on click, a small toast with the result, fake live numbers ticking every second. Center it on the page with a little context around it. Answer with the HTML only.')


def html_of(text):
    """A raw model answer -> the HTML document inside it (fences / prose dropped), locked; None when it holds no markup."""
    t = re.sub(r'```(?:html)?', '', str(text or ''))
    m = re.search(r'(<!doctype html.*|<html.*|<(?:div|style|body|svg|button)\b.*)', t, re.I | re.S)
    return lock_html(m.group(1).strip()) if m else None

def outline(text, path=''):
    """A file → its outline: `def name(args)` / `class` / `export function name` lines + the first line of each docstring (Python) — capped."""
    out, lines = [], str(text or '').split('\n')
    py = str(path).endswith('.py')
    for i, ln in enumerate(lines):
        m = re.match(r'^(?:async )?def (\w+)\(([^)]{0,90})', ln) or re.match(r'^class (\w+)()', ln) if py else re.match(r'^export (?:const|function) (\w+)\s*(?:=|\()([^)]{0,60})', ln)
        if not m:
            continue
        doc = ''
        if py and i + 1 < len(lines):
            d = re.match(r'\s+"""(.{0,110})', lines[i + 1])
            doc = d.group(1).split('"""')[0].strip() if d else ''
        out.append(f"{m.group(1)}({m.group(2).strip()}){' — ' + doc if doc else ''}")
    return '\n'.join(out[:160])


def parse(text):
    """The model's answer → a clean proposal {title, file, kind, why, risk, code} or None."""
    t = re.sub(r'```(?:json)?', '', str(text or '')).strip()
    m = re.search(r'\{.*\}', t, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    code = str(d.get('code') or '').strip()
    if len(code) < 10:
        return None
    pv = str(d.get('preview') or '').strip()
    return {'title': str(d.get('title') or 'code change')[:80], 'file': str(d.get('file') or '')[:120], 'kind': 'new' if d.get('kind') == 'new' else 'change',
            'why': str(d.get('why') or '')[:700], 'risk': str(d.get('risk') or '')[:240], 'code': code[:MAX_CODE],
            **({'preview': lock_html(pv)} if re.search(r'<(html|body|div|svg|style)', pv, re.I) else {}),
            **({'examples': [{'call': str(e.get('call') or '')[:200], 'expect': e.get('expect')} for e in d['examples'][:4] if isinstance(e, dict) and e.get('call')]} if isinstance(d.get('examples'), list) else {})}


def prompt(ask, target_key, outline_text, prev=None):
    """What the model reads: the owner's ask, the target and its real outline (+ its own earlier proposal when changing it)."""
    path, label = TARGETS.get(target_key, TARGETS['agents'])
    out = f"OWNER ASKS: {str(ask)[:900]}\nTARGET: {label} — {path}\nOUTLINE of {path} (real functions):\n{outline_text[:6000]}"
    if prev:
        out += f"\n\nYOUR EARLIER PROPOSAL (change it as asked):\n{str(prev.get('code') or '')[:8000]}"
    return out


def add(items, ask, prop, target, by, now=None):
    it = {'id': f"c{int((now or time.time()) * 1000) % 10**10}", 'ask': str(ask or '')[:300], 'target': target, **prop, 'by': str(by or '')[:40],
          'status': 'proposed', 'at': round(now or time.time(), 1)}
    return ([it] + [x for x in (items or []) if x.get('id') != it['id']])[:KEEP], it


def decide(items, pid, approve, now=None):
    """✅ / ✕ on a proposal → (items, item). Approving only marks it — the service files it to the build queue."""
    out, hit = [], None
    for x in items or []:
        if x.get('id') == pid and x.get('status') == 'proposed':
            x = {**x, 'status': 'approved' if approve else 'dropped', 'decidedAt': round(now or time.time(), 1)}
            hit = x
        out.append(x)
    return out, hit


CSP = ("<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; "
       "script-src 'unsafe-inline'; font-src data:\">")


def lock_html(html):
    """A preview document with a network-blocking CSP first in <head> (whatever the model wrote) — shown in a no-same-origin sandbox."""
    h = re.sub(r'<meta[^>]+http-equiv=["\']?content-security-policy[^>]*>', '', str(html or '')[:60_000], flags=re.I)
    if not re.search(r'<html', h, re.I):
        h = f'<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#05100b;color:#e9fff3">{h}</body></html>'
    return re.sub(r'(<head[^>]*>)', lambda m: m.group(1) + CSP, h, count=1, flags=re.I) if re.search(r'<head[^>]*>', h, re.I) else CSP + h


def _names(code, py):
    pat = r'^(?:async )?def (\w+)\(|^class (\w+)' if py else r'^export (?:const|function) (\w+)|^(?:const|function) (\w+)'
    return [a or b for a, b in re.findall(pat, code, re.M)]


def current_of(src, name, py):
    """The CURRENT text of `name` in the file (to the next top-level definition), or None when it does not exist yet."""
    lines = str(src or '').split('\n')
    start = next((i for i, l in enumerate(lines) if re.match(rf'^(?:async )?def {name}\(|^class {name}\b' if py else rf'^(?:export )?(?:const|function) {name}\b', l)), None)
    if start is None:
        return None
    end = next((j for j in range(start + 1, len(lines)) if lines[j] and not lines[j][0].isspace() and not lines[j].startswith((')', ']', '}'))), len(lines))
    return '\n'.join(lines[start:end]).rstrip()


def preview_diff(src, code, path):
    """🔍 THE PREVIEW BEFORE ANY CHANGE: for each function / component the proposal writes, the file's current version vs the proposed one
    as a unified diff (a name the file does not have = NEW). → {diff, changed: [names], new: [names]}"""
    import difflib
    py = str(path).endswith('.py')
    out, changed, new = [], [], []
    for n in _names(code, py)[:6]:
        new_t = current_of(code, n, py) or ''
        old_t = current_of(src, n, py)
        if old_t is None:
            new.append(n)
            out += [f'+++ NEW {n}'] + ['+' + l for l in new_t.split('\n')]
            continue
        changed.append(n)
        out += list(difflib.unified_diff(old_t.split('\n'), new_t.split('\n'), f'{path} · {n} (now)', f'{path} · {n} (proposed)', lineterm='', n=2))
    return {'diff': '\n'.join(out)[:MAX_CODE], 'changed': changed, 'new': new}


# ▶ THE TEST RUN (owner, 2026-10-15: "the code lab should show a preview of the code WORKING, not just code"). A Python proposal's examples are
# RUN — but only after an AST check proves the code is a pure function (no imports outside SAFE_MODULES, no file / network / process / eval /
# dunder access) and every example is `name(literal, …)` of a function it defines. Then it runs in a separate `python -I` with no env, a temp
# cwd, CPU / memory / file limits, a 4s timeout and (on macOS) a sandbox profile that denies the network and file writes. A proposal that
# leans on the file's own helpers says so instead of running.
SAFE_MODULES = {'math', 'statistics', 're', 'json', 'time', 'datetime', 'random', 'itertools', 'functools', 'collections', 'bisect', 'heapq'}
BAD_NAMES = {'open', 'exec', 'eval', 'compile', '__import__', 'globals', 'locals', 'getattr', 'setattr', 'delattr', 'input', 'breakpoint', 'vars', 'dir',
             'memoryview', 'exit', 'quit', 'help', 'print'}
SANDBOX = '(version 1)(allow default)(deny network*)(deny file-write*)'


def safe_code(code):
    """→ None when the code is a pure function set we may run, else why not (plain words)."""
    import ast
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f'it does not parse: {e.msg} (line {e.lineno})'
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name.split('.')[0] for a in n.names] if isinstance(n, ast.Import) else [str(n.module or '').split('.')[0]]
            if any(m not in SAFE_MODULES for m in mods):
                return f"it imports {', '.join(mods)} — only pure-math modules run in the test"
        elif isinstance(n, ast.Name) and n.id in BAD_NAMES:
            return f'it calls {n.id}() — not allowed in the test run'
        elif isinstance(n, ast.Attribute) and n.attr.startswith('__'):
            return 'it touches a dunder attribute — not allowed in the test run'
        elif isinstance(n, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Await)):
            return 'async / global code does not run in the test'
    return None


def safe_call(call, names):
    """`fn(1, 'a', [2])` of a function the code defines, literal args only → (fn, args, kwargs) or None."""
    import ast
    try:
        node = ast.parse(str(call or ''), mode='eval').body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id not in names:
        return None
    try:
        return node.func.id, [ast.literal_eval(a) for a in node.args], {k.arg: ast.literal_eval(k.value) for k in node.keywords if k.arg}
    except (ValueError, SyntaxError):
        return None


def test_run(code, examples, timeout=4.0):
    """▶ Run the proposal's examples → {ran, why, results: [{call, got, expect, ok, err}]}. Never runs code that fails `safe_code`."""
    import json as _json
    import os
    import subprocess
    import sys
    import tempfile
    why = safe_code(code)
    if why:
        return {'ran': False, 'why': why, 'results': []}
    names = set(_names(code, True))
    calls = [(e, safe_call(e.get('call'), names)) for e in (examples or [])[:4]]
    calls = [(e, c) for e, c in calls if c]
    if not calls:
        return {'ran': False, 'why': 'no runnable example (each must call a function it defines, with plain values)', 'results': []}
    prog = (code + '\n\nimport json as _j\n_out = []\n'
            + ''.join(f"try:\n    _out.append({{'got': repr({fn}(*{args!r}, **{kw!r}))[:300]}})\nexcept Exception as _e:\n    _out.append({{'err': type(_e).__name__ + ': ' + str(_e)[:200]}})\n"
                      for _e_, (fn, args, kw) in calls)
            + "print('@@RESULT@@' + _j.dumps(_out))\n")

    def limits():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        except Exception:
            pass
    cmd = [sys.executable, '-I', '-c', prog]
    if os.path.exists('/usr/bin/sandbox-exec'):
        cmd = ['/usr/bin/sandbox-exec', '-p', SANDBOX] + cmd
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmp, env={}, preexec_fn=limits)
        except subprocess.TimeoutExpired:
            return {'ran': False, 'why': f'it did not finish in {timeout:g}s', 'results': []}
    line = next((l for l in r.stdout.split('\n') if l.startswith('@@RESULT@@')), None)
    if not line:
        err = (r.stderr or '').strip().split('\n')[-1][:200] or 'no output'
        return {'ran': False, 'why': ('it uses something the file defines elsewhere — ' if 'NameError' in err else '') + err, 'results': []}
    outs = _json.loads(line[len('@@RESULT@@'):])
    res = []
    for (e, _c), o in zip(calls, outs):
        got = o.get('got')
        exp = e.get('expect')
        ok = None if exp is None or got is None else (got == repr(exp) or str(got).strip("'\"") == str(exp))
        err = o.get('err')
        m = re.match(r"NameError: name '(\w+)' is not defined", str(err or ''))
        if m:
            err = f"uses {m.group(1)}() from the file — it only runs inside FEELESS"
        res.append({'call': e.get('call'), 'got': got, 'expect': exp, 'ok': ok, 'err': err})
    return {'ran': True, 'why': None, 'results': res}

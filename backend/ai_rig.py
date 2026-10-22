"""🎛 MODEL RIG (owner, 2026-10-20: "tweak Nexa, OSSY and G4's LM and llama context, concurrency, all that"). Pure.
One owner-set row per local model — G4 (`lan`, desktop LM Studio) · OSSY (`local`, this Mac's LM Studio) · NEXA (`win`, the Windows llamafile):
  ctx      = the prompt budget FEELESS fits each call into (0 = read what the model is loaded with)
  parallel = calls sent at once (each fits ctx ÷ parallel when the model shares one context across slots)
  timeout  = seconds a call may take before it is a miss
  perMin   = background calls a minute (a model's own trade call / your chat are never capped)
  every    = Nexa only: seconds between her FeeCat reads
FEELESS only changes what IT sends. The context and slots a model is LOADED with are set where it loads (LM Studio / llamafile) — `load_cmd`
prints the matching command; nothing here reloads a model (the owner's rule: never reload the desktop model)."""

KEYS = ('lan', 'local', 'win')
NAMES = {'lan': 'G4', 'local': 'OSSY', 'win': 'NEXA'}
OPTIONS = {'ctx': (0, 2048, 4096, 8192, 12288, 16384, 32768), 'parallel': (1, 2, 3, 4), 'timeout': (30, 45, 60, 90, 120, 180, 240, 300),
           'perMin': (2, 4, 6, 8, 12), 'every': (180, 300, 600, 900)}
DEFAULTS = {'lan': {'ctx': 0, 'parallel': 2, 'timeout': 90, 'perMin': 4}, 'local': {'ctx': 0, 'parallel': 1, 'timeout': 60, 'perMin': 4},
            'win': {'ctx': 4096, 'parallel': 1, 'timeout': 240, 'perMin': 2, 'every': 900}}


# 🧠 LM STUDIO LOAD (owner, 2026-10-21: "the Brain chat must TRULY change the LM Studio Load / Inference settings"). What a model is LOADED with
# — LM Studio's own REST `POST /api/v1/models/load` (lmstudio.ai/docs/developer/rest/load): context_length + parallel for every engine;
# flash_attention · offload_kv_cache_to_gpu · eval_batch_size only on llama.cpp (GGUF) — MLX ignores them, so they are never sent to an MLX model.
# A wanted load is applied ONLY by the owner (⚡ Reload in Brain › Models, or ✅ on a chat proposal) — never by a timer (owner's 10-17 rule).
LM_KEYS = ('lan', 'local')
LOAD_OPTIONS = {'ctx': (4096, 8192, 12288, 16384, 24576, 32768, 65536), 'par': (1, 2, 3, 4), 'flash': (0, 1), 'kv': (0, 1), 'batch': (256, 512, 1024, 2048)}
GGUF_ONLY = ('flash', 'kv', 'batch')
LOAD_WORD = {'ctx': 'context', 'par': 'max concurrent', 'flash': 'flash attention', 'kv': 'KV cache on GPU', 'batch': 'eval batch'}


def clean_load(d, prev=None):
    """A wanted LM Studio load → listed values only; a field left out keeps the previous wanted value (None = as loaded)."""
    out = {k: v for k, v in (prev or {}).items() if k in LOAD_OPTIONS and v in LOAD_OPTIONS[k]}
    for k, v in (d or {}).items():
        if k not in LOAD_OPTIONS:
            continue
        if v is None:
            out.pop(k, None); continue
        try:
            v = int(v)
        except (TypeError, ValueError):
            continue
        if v in LOAD_OPTIONS[k]:
            out[k] = v
    return out


def load_value(d):
    """{ctx: 16384, par: 1} → 'ctx=16384 par=1' (a proposal's value — readable, parsed back exactly by `parse_load_value`)."""
    return ' '.join(f'{k}={d[k]}' for k in LOAD_OPTIONS if k in (d or {}))


def parse_load_value(s):
    return clean_load({k: v for k, v in (x.split('=', 1) for x in str(s or '').split() if '=' in x)})


def load_words(d):
    """'ctx=16384 par=1' / a dict → '16K context · ×1 at once' (the owner reads this, never the raw keys)."""
    d = parse_load_value(d) if isinstance(d, str) else (d or {})
    out = []
    for k in LOAD_OPTIONS:
        if k not in d:
            continue
        v = d[k]
        out.append(f"{v // 1024}K context" if k == 'ctx' else f"×{v} at once" if k == 'par' else f"eval batch {v}" if k == 'batch'
                   else f"{LOAD_WORD[k]} {'ON' if v else 'OFF'}" if k == 'flash' else f"KV cache on {'GPU' if v else 'RAM'}")
    return ' · '.join(out) or 'as loaded'


def lms_row(data, model):
    """LM Studio's `GET /api/v1/models` → THIS model's row: {model, fmt, maxCtx, sizeGb, quant, loaded: [{id, ctx, par, flash, kv, batch}]}.
    The configured model first; else whatever LLM is loaded (G4's desktop may hold another one); None = not listed at all."""
    rows = [m for m in (data or {}).get('models') or [] if isinstance(m, dict) and m.get('type') in ('llm', 'vlm', None)]
    m = next((x for x in rows if x.get('key') == model), None) or next((x for x in rows if x.get('loaded_instances')), None)
    if not m:
        return None
    def inst(i):
        c = i.get('config') or {}
        out = {'id': i.get('id'), 'ctx': c.get('context_length'), 'par': c.get('parallel')}
        for f, src in (('flash', 'flash_attention'), ('kv', 'offload_kv_cache_to_gpu')):
            if src in c:
                out[f] = int(bool(c[src]))
        if c.get('eval_batch_size'):
            out['batch'] = c['eval_batch_size']
        return out
    q = m.get('quantization') or {}
    return {'model': m.get('key'), 'name': m.get('display_name') or m.get('key'), 'fmt': m.get('format') or '?', 'maxCtx': m.get('max_context_length'),
            'sizeGb': round((m.get('size_bytes') or 0) / 1e9, 1) or None, 'quant': q.get('name'), 'params': m.get('params_string'),
            'loaded': [inst(i) for i in m.get('loaded_instances') or [] if isinstance(i, dict)]}


def load_body(model, want, loaded=None, fmt='gguf'):
    """The `POST /api/v1/models/load` body for a wanted load: what the owner set, else what the model runs now, else LM Studio's default.
    GGUF-only fields never go to an MLX model."""
    cur = (loaded or [{}])[0] if loaded else {}
    pick = lambda k: (want or {}).get(k, cur.get(k))
    body = {'model': model, 'echo_load_config': True}
    if pick('ctx'):
        body['context_length'] = int(pick('ctx'))
    if pick('par'):
        body['parallel'] = int(pick('par'))
    if str(fmt).lower() == 'gguf':
        for k, src in (('flash', 'flash_attention'), ('kv', 'offload_kv_cache_to_gpu')):
            if pick(k) is not None:
                body[src] = bool(pick(k))
        if pick('batch'):
            body['eval_batch_size'] = int(pick('batch'))
    return body


def load_diff(want, loaded):
    """Fields where the wanted load differs from what LM Studio runs now → {field: (now, wanted)}. Empty = nothing to reload."""
    cur = (loaded or [{}])[0] if loaded else {}
    return {k: (cur.get(k), v) for k, v in (want or {}).items() if cur.get(k) != v}


def clean(body, prev=None):
    """Owner input → a rig with listed values only (anything else keeps the previous / default value)."""
    out = {k: dict(DEFAULTS[k], **((prev or {}).get(k) or {})) for k in KEYS}
    for k in LM_KEYS:
        out[k]['load'] = clean_load(out[k].get('load'))
    out['win'].pop('load', None)
    for k, row in (body or {}).items():
        if k not in KEYS or not isinstance(row, dict):
            continue
        for f, v in row.items():
            if f == 'load' and k in LM_KEYS and isinstance(v, dict):
                out[k]['load'] = clean_load(v, out[k]['load']); continue
            if f in OPTIONS and f in DEFAULTS[k]:
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    continue
                if v in OPTIONS[f]:
                    out[k][f] = v
    return out


def load_cmd(key, row, model=None):
    """The command that loads the model to match this rig (the owner runs it where the model lives)."""
    ld = row.get('load') or {}
    if ld.get('ctx') or ld.get('par'):   # 🧠 the wanted LM Studio load wins: the command loads exactly what ⚡ Reload would
        return f"lms load {model or '<model>'} --context-length {ld.get('ctx') or 8192} --parallel {ld.get('par') or 1} -y"
    ctx = row.get('ctx') or 8192
    par = row.get('parallel') or 1
    if key == 'win':
        return f"llamafile.exe --server --host 0.0.0.0 --port 8080 -m {model or 'Ministral-3-3B-Instruct-2512-Q4_K_M.gguf'} -c {ctx * par} -np {par}"
    return f"lms load {model or '<model>'} --context-length {ctx * par if par > 1 else ctx} --parallel {par} -y"


def view(rig, models=None, lms=None):
    """The rig for Brain › Models. `lms` = {key: lms_row(..)} — what each LM Studio REALLY runs, so the view shows LOADED vs WANTED."""
    r = clean({}, rig)
    rows = []
    for k in KEYS:
        row = {'key': k, 'name': NAMES[k], **r[k], 'cmd': load_cmd(k, r[k], (models or {}).get(k))}
        if k in LM_KEYS:
            lm = (lms or {}).get(k)
            row['lms'] = lm
            row['diff'] = {f: list(v) for f, v in load_diff(r[k]['load'], (lm or {}).get('loaded')).items()} if lm else {}
        rows.append(row)
    return {'rows': rows, 'options': {f: list(v) for f, v in OPTIONS.items()}, 'loadOptions': {f: list(v) for f, v in LOAD_OPTIONS.items()},
            'ggufOnly': list(GGUF_ONLY)}


# 💬 A CHAT LINE → RIG CHANGES (owner, 2026-10-21: "a chat line truly changes model settings — proposal → applied"). Pure + deterministic: the
# owner's own words are read here (no model guesses at numbers). Each change becomes a PENDING proposal (ai_chat kind `rig`); nothing applies
# until ✅, and a LOAD change reloads the model only on that ✅. Keys: `<lan|local|win>.<ctx|parallel|timeout|perMin|every>` (what FEELESS
# sends), `<lan|local>.load` (what LM Studio loads), `chat.temp` / `chat.len` (the Brain's inference).
import re as _re

WHO = (('lan', r'g4|gemma|desktop'), ('local', r'ossy|gpt.?oss|this mac'), ('win', r'nexa|llamafile|windows'))
CHAT_TEMPS = (0.1, 0.3, 0.6, 0.9)
CHAT_LENS = {'short': 250, 'normal': 600, 'long': 1200}
_NUM = r'(\d+(?:\.\d+)?)'


def _snap(v, opts):
    return min(opts, key=lambda o: (abs(o - v), -o))


def _ctx_of(m):
    n = float(m.group(1))
    return int(n * 1024) if (m.group(2) or n <= 128) else int(n)


def _segments(t):
    """'ossy context 16k and g4 parallel 1' → [('local', 'context 16k and '), ('lan', 'parallel 1')]; words before any model → (None, ...).
    'both' / 'all models' → G4 + OSSY."""
    pat = '|'.join(f'(?P<{k}>\\b(?:{w})\\b)' for k, w in WHO) + r'|(?P<both>\b(?:both|all (?:the )?models|every model)\b)'
    hits = list(_re.finditer(pat, t))
    out = [(None, t[:hits[0].start()] if hits else t)]
    for i, h in enumerate(hits):
        seg = t[h.end():hits[i + 1].start() if i + 1 < len(hits) else len(t)]
        keys = LM_KEYS if h.lastgroup == 'both' else (h.lastgroup,)
        out += [(k, seg) for k in keys]
    return out


def parse_line(text):
    """The owner's chat line → [{key, value, words, reload}] (empty = not a settings line). Only listed values; a number between options
    snaps to the nearest one (and says so in `words`)."""
    t = str(text or '').lower()
    if not _re.search(r'context|ctx|budget|parallel|concurren|slots?\b|flash|kv|batch|time ?out|calls?\s*(?:/|per|a)\s*min|read every|temp|answer|response|repl', t):
        return []
    out, loads = [], {}
    for key, seg in _segments(t):
        if key is None and not seg.strip():
            continue
        m = _re.search(r'\btemp(?:erature)?\b\D{0,10}?' + r'(\d?\.\d+|\d)', seg)
        if m and key in (None, 'lan', 'local') and float(m.group(1)) <= 2:   # "temp 5 degrees" is weather talk, not a sampling temperature
            v = _snap(float(m.group(1)), CHAT_TEMPS)
            out.append({'key': 'chat.temp', 'value': v, 'words': f'Brain chat temperature {v}', 'reload': False})
        m = _re.search(r'(?:answers?|responses?|repl(?:y|ies))\s*(?:length|size)?\s*(?:to\s*|=\s*)?(short|normal|long)|(short|normal|long)\s*(?:answers|responses|replies)', seg)
        m2 = _re.search(r'max\s*tokens?\D{0,6}?(\d{2,5})', seg)
        if (m or m2) and key in (None, 'lan', 'local'):
            v = (m.group(1) or m.group(2)) if m else min(CHAT_LENS, key=lambda k: abs(CHAT_LENS[k] - int(m2.group(1))))
            out.append({'key': 'chat.len', 'value': v, 'words': f'Brain answer length {v} (≈{CHAT_LENS[v]} tokens)', 'reload': False})
        if key is None:
            continue
        budget = bool(_re.search(r'budget|send', seg))
        m = _re.search(r'\b(?:context(?:\s*(?:length|window|size))?|ctx|budget)\b\D{0,12}?' + _NUM + r'\s*(k)?', seg)
        if m and (m.group(2) or float(m.group(1)) >= 1024):   # "context of 5 trades" is a question — a context size says 16k / 16384
            n = _ctx_of(m)
            if key in LM_KEYS and not budget:
                v = _snap(n, LOAD_OPTIONS['ctx']); loads.setdefault(key, {})['ctx'] = v
            else:
                v = _snap(n, [o for o in OPTIONS['ctx'] if o]); out.append({'key': f'{key}.ctx', 'value': v, 'words': f"{NAMES[key]} prompt budget {v // 1024}K" if key != 'win'
                                                                         else f'NEXA context {v // 1024}K (restarts her llamafile)', 'reload': key == 'win'})
        m = _re.search(r'\b(?:parallel|max\s*concurren\w*|concurren\w*|slots?)\b\D{0,16}?(\d)', seg)
        if m:
            n = int(m.group(1))
            if key in LM_KEYS:
                loads.setdefault(key, {})['par'] = _snap(n, LOAD_OPTIONS['par'])
            else:
                v = _snap(n, OPTIONS['parallel']); out.append({'key': 'win.parallel', 'value': v, 'words': f'NEXA ×{v} slots (restarts her llamafile)', 'reload': True})
        if key in LM_KEYS:
            m = _re.search(r'flash(?:\s*(?:attention|attn))?\s*(?:to\s*)?(on|off|true|false|enabled?|disabled?)|(enable|disable|turn on|turn off|no)\s+flash', seg)
            if m:
                w = m.group(1) or m.group(2)
                loads.setdefault(key, {})['flash'] = 0 if _re.match(r'off|false|disable|turn off|no', w) else 1
            m = _re.search(r'kv(?:\s*cache)?\s*(?:to|on|in|into)?\s*(gpu|vram|ram|cpu|memory)|(offload|keep)\s+(?:the\s+)?kv', seg)
            if m:
                loads.setdefault(key, {})['kv'] = 1 if (m.group(1) in ('gpu', 'vram') or m.group(2)) else 0
            m = _re.search(r'batch(?:\s*size)?\D{0,8}?(\d{3,4})', seg)
            if m:
                loads.setdefault(key, {})['batch'] = _snap(int(m.group(1)), LOAD_OPTIONS['batch'])
        m = _re.search(r'time ?out\D{0,8}?(\d{2,3})', seg)
        if m:
            v = _snap(int(m.group(1)), OPTIONS['timeout']); out.append({'key': f'{key}.timeout', 'value': v, 'words': f'{NAMES[key]} timeout {v}s', 'reload': False})
        m = _re.search(r'(\d{1,2})\s*(?:background\s*)?(?:calls?|reads?)\s*(?:/|per|a)\s*min', seg)
        if m:
            v = _snap(int(m.group(1)), OPTIONS['perMin']); out.append({'key': f'{key}.perMin', 'value': v, 'words': f'{NAMES[key]} {v} background calls a minute', 'reload': False})
        m = _re.search(r'read(?:s)?\s*every\D{0,6}?(\d{1,2})\s*m', seg)
        if m and key == 'win':
            v = _snap(int(m.group(1)) * 60, OPTIONS['every']); out.append({'key': 'win.every', 'value': v, 'words': f'NEXA reads every {v // 60} min', 'reload': False})
    for k, d in loads.items():
        out.append({'key': f'{k}.load', 'value': load_value(d), 'words': f"{NAMES[k]} loads with {load_words(d)} (reloads {NAMES[k]})", 'reload': True})
    seen, uniq = set(), []
    for x in out:
        if x['key'] not in seen:
            seen.add(x['key']); uniq.append(x)
    return uniq


def check_change(key, value):
    """A rig proposal's key + value → the normalized value, or None (refused). The ONE gate for chat- and model-made rig changes."""
    k, _, f = str(key or '').partition('.')
    if k == 'chat':
        if f == 'temp':
            try:
                v = float(value)
            except (TypeError, ValueError):
                return None
            return v if v in CHAT_TEMPS else None
        return value if f == 'len' and value in CHAT_LENS else None
    if k not in KEYS:
        return None
    if f == 'load':
        d = parse_load_value(value)
        return load_value(d) if k in LM_KEYS and d else None
    if f not in OPTIONS or f not in DEFAULTS[k]:
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return v if v in OPTIONS[f] else None


# 🪟 NEXA RUNTIME (owner, 2026-10-21: "the rig's NEXA settings must actually control the Windows llamafile"). The Windows PC runs
# backend/nexa_controller.py (fixed purpose: restart THE configured llamafile with validated ctx / slots). FEELESS saves what the owner wants
# (desired), asks the controller to apply it, then reads llamafile's own /props + /slots (actual). A setting is called ACTIVE only when the
# runtime itself reports it.
CTL_CTX = (2048, 4096, 8192, 12288, 16384, 32768)
CTL_PAR = (1, 2, 3, 4)


def win_target(row):
    """The (ctx, slots) the controller should run for NEXA's rig row, or None when the rig asks for 'auto' context (nothing to apply)."""
    ctx, par = int((row or {}).get('ctx') or 0), int((row or {}).get('parallel') or 1)
    if ctx not in CTL_CTX or par not in CTL_PAR or ctx * par > 32768:
        return None
    return ctx, par


def runtime_view(row, actual, job=None, ctl=None):
    """GET rig → NEXA desired vs actual. state: active (runtime matches) · applying · differs (runtime reachable, not what was asked) ·
    unreachable (NEXA's llamafile did not answer) — plus what the last apply said and whether the controller answers."""
    t = win_target(row)
    want = {'ctx': t[0], 'slots': t[1]} if t else None
    job = job or {}
    if job.get('state') == 'applying':
        state = 'applying'
    elif not actual:
        state = 'unreachable'
    elif want and actual.get('ctx') == want['ctx'] and actual.get('slots') == want['slots']:
        state = 'active'
    else:
        state = 'differs'
    return {'desired': want, 'actual': actual, 'state': state, 'active': state == 'active', 'controller': ctl or {'reachable': False},
            'job': {k: job.get(k) for k in ('state', 'msg', 'at', 'verified') if k in job} or None,
            'auto': t is None}


# 🔖 PRESETS per model (owner, 2026-10-22: "prompt presets per model — save / pick / apply"): a named snapshot of one model's rig (Load + what
# FEELESS sends). Applying one goes through `clean` (listed values only) — G4 / OSSY still reload only on the owner's ⚡ tap.
PRESETS_MAX, PRESET_NAME_MAX = 8, 32


def preset_name(s):
    n = ' '.join(''.join(ch for ch in str(s or '') if ch.isprintable()).split())[:PRESET_NAME_MAX]
    return n or None


def preset_save(store, key, name, row, now):
    """→ the store with `name` saved for `key` (same name = replaced; the newest PRESETS_MAX kept)."""
    n = preset_name(name)
    if key not in KEYS or not n or not isinstance(row, dict):
        raise ValueError('Pick a model and a name.')
    lst = [p for p in (store.get(key) or []) if p.get('name') != n]
    store[key] = ([{'name': n, 'at': int(now), 'row': {f: v for f, v in row.items() if f in DEFAULTS[key] or f == 'load'}}] + lst)[:PRESETS_MAX]
    return store


def preset_get(store, key, name):
    return next((p['row'] for p in store.get(key) or [] if p.get('name') == preset_name(name)), None)


def preset_drop(store, key, name):
    store[key] = [p for p in store.get(key) or [] if p.get('name') != preset_name(name)]
    return store


def presets_view(store):
    return {k: [{'name': p['name'], 'at': p['at'], 'words': load_words(p['row']['load']) if isinstance(p['row'].get('load'), dict) else ''} for p in store.get(k) or []] for k in KEYS}

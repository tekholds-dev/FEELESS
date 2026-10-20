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
            'win': {'ctx': 4096, 'parallel': 1, 'timeout': 240, 'perMin': 2, 'every': 300}}


def clean(body, prev=None):
    """Owner input → a rig with listed values only (anything else keeps the previous / default value)."""
    out = {k: dict(DEFAULTS[k], **((prev or {}).get(k) or {})) for k in KEYS}
    for k, row in (body or {}).items():
        if k not in KEYS or not isinstance(row, dict):
            continue
        for f, v in row.items():
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
    ctx = row.get('ctx') or 8192
    par = row.get('parallel') or 1
    if key == 'win':
        return f"llamafile.exe --server --host 0.0.0.0 --port 8080 -m {model or 'Ministral-3-3B-Instruct-2512-Q4_K_M.gguf'} -c {ctx * par} -np {par}"
    return f"lms load {model or '<model>'} --context-length {ctx * par if par > 1 else ctx} --parallel {par} -y"


def view(rig, models=None):
    r = clean({}, rig)
    return {'rows': [{'key': k, 'name': NAMES[k], **r[k], 'cmd': load_cmd(k, r[k], (models or {}).get(k))} for k in KEYS],
            'options': {f: list(v) for f, v in OPTIONS.items()}}

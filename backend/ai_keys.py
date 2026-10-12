"""🔑 AI API KEYS for the agents (owner, 2026-10-12: "add a way I can add an OpenAI or any kind of AI API key in the Agents tab").

The owner pastes a key in HQ › Agents; it is TESTED against the provider's own list-models endpoint (read-only, no tokens spent), saved to
backend/.env as the one active line of its variable and set in this process — the same rules as the RPC key box:

  · the key is NEVER returned to the page, logged, audited or put in an error message — the page sees only the provider, "set" and the
    last 4 characters (`hint`), like the provider's own dashboard
  · a custom endpoint must be an https:// PUBLIC host (never an IP, localhost or a private name) — the server will not call your network
  · owner only (`_require_owner` on both routes)

WHAT A KEY IS USED FOR: the AI router (ai_router.py) may ask that provider for ADVISORY notes (Sherlock's read, Devil's second opinion,
the Judge's attribution, the owner's review) — shown beside the desk that asked; never a rank, a size, READY, an order or a stop. Pure
except `probe`."""
import re
import time

# key → (label, env var of the key, list-models URL or None for a custom base, auth header style)
PROVIDERS = {
    'openai': ('OpenAI', 'OPENAI_API_KEY', 'https://api.openai.com/v1/models', 'bearer'),
    'anthropic': ('Anthropic', 'ANTHROPIC_API_KEY', 'https://api.anthropic.com/v1/models', 'anthropic'),
    'gemini': ('Google Gemini', 'GEMINI_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/models', 'google'),
    'openrouter': ('OpenRouter', 'OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1/auth/key', 'bearer'),
    'groq': ('Groq', 'GROQ_API_KEY', 'https://api.groq.com/openai/v1/models', 'bearer'),
    'xai': ('xAI (Grok)', 'XAI_API_KEY', 'https://api.x.ai/v1/models', 'bearer'),
    'custom': ('Any OpenAI-compatible', 'AI_API_KEY', None, 'bearer'),
}
ACTIVE_VAR, BASE_VAR, MODEL_VAR = 'AI_PROVIDER', 'AI_BASE_URL', 'AI_MODEL'
# a model typed with a key goes to THAT provider's own model variable (the AI router reads these); others use AI_MODEL
MODEL_VARS = {'groq': 'GROQ_MODEL', 'openrouter': 'OPENROUTER_MODEL', 'openai': 'OPENAI_MODEL', 'xai': 'XAI_MODEL'}
_KEY = re.compile(r'^[A-Za-z0-9_\-.:+/=]{16,300}$')
_MODEL = re.compile(r'^[A-Za-z0-9_.:/\-]{1,80}$')


def clean_key(key):
    k = str(key or '').strip()
    if not _KEY.match(k):
        raise ValueError('That does not look like an API key — paste the whole key (no spaces or quotes).')
    return k


def clean_base(url):
    """A custom endpoint: https, a public host name, ≤ 200 chars, no query → the base without a trailing slash."""
    u = str(url or '').strip().rstrip('/')
    m = re.match(r'^https://([A-Za-z0-9.-]+)(:\d+)?(/[A-Za-z0-9._~/-]*)?$', u)
    if not m or len(u) > 200:
        raise ValueError('Paste the https:// base URL of the API (for example https://api.together.xyz/v1).')
    host = m.group(1).lower()
    if '.' not in host or re.match(r'^[\d.]+$', host) or host.endswith(('.local', '.internal', '.localhost', '.lan')) or host.startswith('localhost'):
        raise ValueError('That is not a public API host.')
    return u


def clean_model(model):
    m = str(model or '').strip()
    if not m:
        return ''
    if not _MODEL.match(m):
        raise ValueError('A model name is letters, numbers and . _ : / - only.')
    return m


def clean(provider, key, base=None, model=None):
    """→ {provider, key, base, model} or raises ValueError with a plain reason."""
    if provider not in PROVIDERS:
        raise ValueError('Pick a provider.')
    return {'provider': provider, 'key': clean_key(key), 'base': clean_base(base) if provider == 'custom' else '', 'model': clean_model(model)}


def hint(key):
    k = str(key or '')
    return f'…{k[-4:]}' if len(k) >= 12 else None


def host_of(url):
    m = re.match(r'^https?://([^/:?]+)', str(url or ''))
    return m.group(1).lower() if m else None


def status(env):
    """What the page may see: per provider set / hint, the active provider, the model and the custom host. Never a key."""
    active = env.get(ACTIVE_VAR) or ''
    rows = [{'key': k, 'label': lab, 'set': bool(env.get(var)), 'hint': hint(env.get(var)), 'active': k == active and bool(env.get(var))}
            for k, (lab, var, _u, _a) in PROVIDERS.items()]
    return {'providers': rows, 'active': active if any(r['active'] for r in rows) else None, 'model': env.get(MODEL_VARS.get(active, MODEL_VAR)) or env.get(MODEL_VAR) or None,
            'base': host_of(env.get(BASE_VAR)) if active == 'custom' else None, 'used': 'advisory',
            'note': 'Advisory only: the AI router may ask a provider for a note beside Sherlock / Devil / the Judge / your review — it never changes a rank, a size, READY, an order or a stop.'}


def env_lines(c):
    """The .env lines to write for a cleaned key: [(var, value)] (the key's own variable, the active provider, the model, a custom base)."""
    lab, var, _u, _a = PROVIDERS[c['provider']]
    out = [(var, c['key']), (ACTIVE_VAR, c['provider'])]
    if c['model']:
        out.append((MODEL_VARS.get(c['provider'], MODEL_VAR), c['model']))
    if c['provider'] == 'custom':
        out.append((BASE_VAR, c['base']))
    return out


def env_without(text, var):
    """The .env text with every active `var=` line commented out (a cleared key stays out of the loader; the line is kept for history)."""
    return '\n'.join(('# ' + raw if raw.strip().startswith(var + '=') else raw) for raw in str(text or '').split('\n'))


def scrub(text, key):
    """An error message with the key (or any long run of it) removed."""
    t = str(text or '')[:160]
    k = str(key or '')
    if k:
        t = t.replace(k, '•••')
        for i in range(0, max(0, len(k) - 12), 6):
            t = t.replace(k[i:i + 12], '•••')
    return t


def _headers(style, key):
    return {'bearer': {'Authorization': f'Bearer {key}'}, 'anthropic': {'x-api-key': key, 'anthropic-version': '2023-06-01'},
            'google': {'x-goog-api-key': key}}[style]


async def probe(http, c):
    """ONE read-only request to the provider's list-models (OpenRouter: key info) endpoint → {ok, ms, models: [≤ 6 ids], err}.
    Spends no tokens. The key never appears in the result."""
    lab, _var, url, style = PROVIDERS[c['provider']]
    url = url or f"{c['base']}/models"
    t0 = time.perf_counter()
    try:
        r = await http.get(url, headers=_headers(style, c['key']))
        ms = round((time.perf_counter() - t0) * 1000)
        if r.status_code in (401, 403):
            return {'ok': False, 'ms': ms, 'err': f'{lab} refused the key ({r.status_code}) — check it was copied whole and is active'}
        if r.status_code >= 400:
            return {'ok': False, 'ms': ms, 'err': scrub(f'{lab} answered {r.status_code}', c['key'])}
        try:
            j = r.json()
        except ValueError:
            j = {}
        items = (j.get('data') or j.get('models') or []) if isinstance(j, dict) else []
        ids = [str(x.get('id') or x.get('name') or '')[:60] for x in items if isinstance(x, dict)][:6]
        return {'ok': True, 'ms': ms, 'models': [i for i in ids if i]}
    except Exception as e:
        return {'ok': False, 'ms': round((time.perf_counter() - t0) * 1000), 'err': scrub(f'{lab} did not answer: {type(e).__name__}', c['key'])}

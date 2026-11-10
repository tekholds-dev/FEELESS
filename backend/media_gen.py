"""🎬 AI images and video for PoC (owner 2026-11-10): runs on the USER'S OWN fal.ai or Replicate key, sealed on the agent like every
API-drawer key. FEELESS never pays for a frame and never sees the key on the page. A job is submitted, polled until done, and its file
is kept by FEELESS so a provider link that expires never breaks a post.

Prices shown are the provider's own, read from its model page on the date noted; None = see the provider (never guessed)."""
import re

PROVIDERS = {
    'fal': {'name': 'fal.ai', 'signup': 'https://fal.ai/login', 'keys': 'https://fal.ai/dashboard/keys', 'billing': 'https://fal.ai/dashboard/billing'},
    'replicate': {'name': 'Replicate', 'signup': 'https://replicate.com/signin', 'keys': 'https://replicate.com/account/api-tokens', 'billing': 'https://replicate.com/account/billing'},
}
# id → (provider, model, kind, label, what it is for, $ per run or None). Checked live 2026-11-10 (fal: Wan 2.2 5B "$0.15 per video", 5 s 720p).
MODELS = {
    'fal-flux-schnell': ('fal', 'fal-ai/flux/schnell', 'image', 'FLUX.1 schnell', 'Fast, cheap stills: thumbnails, post art, a face to test', None),
    'fal-wan22-5b': ('fal', 'fal-ai/wan/v2.2-5b/text-to-video', 'video', 'Wan 2.2 5B', 'The cheap video: 5 s, 720p', 0.15),
    'fal-wan22-a14b': ('fal', 'fal-ai/wan/v2.2-a14b/text-to-video', 'video', 'Wan 2.2 A14B', 'Sharper motion than 5B, still cheap', None),
    'fal-wan25': ('fal', 'fal-ai/wan-25-preview/text-to-video', 'video', 'Wan 2.5', 'Newer Wan, better faces and motion', None),
    'fal-kling25': ('fal', 'fal-ai/kling-video/v2.5-turbo/pro/text-to-video', 'video', 'Kling 2.5 Turbo Pro', 'Top quality for a hero clip', None),
    'rep-flux-schnell': ('replicate', 'black-forest-labs/flux-schnell', 'image', 'FLUX.1 schnell', 'Fast, cheap stills', None),
    'rep-wan22-fast': ('replicate', 'wan-video/wan-2.2-t2v-fast', 'video', 'Wan 2.2 fast', 'The cheap video: 480p, fast', None),
    'rep-wan25': ('replicate', 'wan-video/wan-2.5-t2v', 'video', 'Wan 2.5', 'Newer Wan, better faces and motion', None),
    'rep-seedance-lite': ('replicate', 'bytedance/seedance-1-lite', 'video', 'Seedance 1 Lite', 'Smooth, cheap realistic motion', None),
}
DEFAULT = {('fal', 'image'): 'fal-flux-schnell', ('fal', 'video'): 'fal-wan22-5b', ('replicate', 'image'): 'rep-flux-schnell', ('replicate', 'video'): 'rep-wan22-fast'}
KINDS = ('image', 'video')
MAX_PROMPT = 1500
MAX_BYTES = 120 * 1024 * 1024
POLL_S = 4
GIVE_UP_S = 15 * 60
EXT = {'image': ('png', 'jpg', 'jpeg', 'webp'), 'video': ('mp4', 'webm', 'mov')}


def catalog(linked):
    """The picker: every model, which can run now (its provider is linked), the cheap default per kind. Pure."""
    rows = [{'id': k, 'provider': p, 'providerName': PROVIDERS[p]['name'], 'kind': kd, 'label': lb, 'why': why, 'usd': usd, 'ready': p in linked}
            for k, (p, _m, kd, lb, why, usd) in MODELS.items()]
    pick = {kd: next((DEFAULT[(p, kd)] for p in ('fal', 'replicate') if p in linked), None) for kd in KINDS}
    return {'models': rows, 'linked': sorted(linked), 'pick': pick, 'providers': PROVIDERS}


def choose(model_id, kind, linked):
    """→ (id, provider, model, kind) or ValueError. A model whose provider is not linked is refused, never silently swapped."""
    if kind not in KINDS:
        raise ValueError('Pick image or video.')
    mid = model_id or next((DEFAULT[(p, kind)] for p in ('fal', 'replicate') if p in linked), None)
    if not mid:
        raise ValueError('Link fal.ai or Replicate first: images and video run on your own account.')
    if mid not in MODELS:
        raise ValueError('Unknown model.')
    p, m, kd = MODELS[mid][:3]
    if kd != kind:
        raise ValueError(f'{MODELS[mid][3]} makes {kd}s, not {kind}s.')
    if p not in linked:
        raise ValueError(f'Link {PROVIDERS[p]["name"]} first: this model runs on your own account.')
    return mid, p, m, kd


def clean_prompt(text):
    t = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(t) < 3:
        raise ValueError('Say what to make.')
    return t[:MAX_PROMPT]


def submit_req(provider, model, prompt, key):
    """→ (method, url, headers, json) for the first call. Pure."""
    if provider == 'fal':
        return 'POST', f'https://queue.fal.run/{model}', {'Authorization': f'Key {key}', 'Content-Type': 'application/json'}, {'prompt': prompt}
    return 'POST', f'https://api.replicate.com/v1/models/{model}/predictions', {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, {'input': {'prompt': prompt}}


def handle_of(provider, body):
    """The provider's answer to a submit → what we poll later (no key in it). Pure."""
    body = body or {}
    if provider == 'fal':
        if not body.get('status_url') or not body.get('response_url'):
            raise ValueError(str(body.get('detail') or 'fal.ai did not start the job.')[:200])
        return {'status': body['status_url'], 'result': body['response_url'], 'rid': body.get('request_id')}
    if not (body.get('urls') or {}).get('get'):
        raise ValueError(str(body.get('detail') or body.get('title') or 'Replicate did not start the job.')[:200])
    return {'status': body['urls']['get'], 'result': body['urls']['get'], 'rid': body.get('id')}


def auth(provider, key):
    return {'Authorization': f'Key {key}'} if provider == 'fal' else {'Authorization': f'Bearer {key}'}


def state_of(provider, body):
    """A poll answer → ('running'|'done'|'failed', why). Pure."""
    body = body or {}
    s = str(body.get('status') or '').upper()
    if provider == 'fal':
        if s == 'COMPLETED':
            return ('failed', str(body.get('error'))[:200]) if body.get('error') else ('done', '')
        return ('running', s.lower() or 'queued')
    if s == 'SUCCEEDED':
        return 'done', ''
    if s in ('FAILED', 'CANCELED'):
        return 'failed', str(body.get('error') or s.lower())[:200]
    return 'running', s.lower() or 'starting'


def output_url(provider, kind, body):
    """The finished file's link from the result. Pure."""
    body = body or {}
    if provider == 'fal':
        if kind == 'video':
            return ((body.get('video') or {}).get('url')) or None
        im = (body.get('images') or [{}])[0] if isinstance(body.get('images'), list) else (body.get('image') or {})
        return (im or {}).get('url') or None
    out = body.get('output')
    if isinstance(out, list):
        out = out[0] if out else None
    return out if isinstance(out, str) and out.startswith('https://') else None


def ext_of(kind, url, content_type=''):
    m = re.search(r'\.([a-z0-9]{2,5})(?:\?|$)', str(url or '').lower())
    e = m.group(1) if m else ''
    if e in EXT[kind]:
        return 'jpg' if e == 'jpeg' else e
    ct = str(content_type or '').lower()
    for e in EXT[kind]:
        if e in ct:
            return e
    return 'mp4' if kind == 'video' else 'png'


NAME = re.compile(r'^m[0-9a-f]{12}\.(png|jpg|webp|mp4|webm|mov)$')

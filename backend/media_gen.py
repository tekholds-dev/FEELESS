"""🎬 AI images and video for PoC (owner 2026-11-10): runs on the USER'S OWN OpenRouter, fal.ai or Replicate key (staff agents may use FEELESS's
OpenRouter key, capped at HOUSE_DAILY_USD a day), sealed on the agent like every
API-drawer key. FEELESS never pays for a frame and never sees the key on the page. A job is submitted, polled until done, and its file
is kept by FEELESS so a provider link that expires never breaks a post.

Prices shown are the provider's own, read from its model page on the date noted; None = see the provider (never guessed)."""
import re

PROVIDERS = {
    'fal': {'name': 'fal.ai', 'signup': 'https://fal.ai/login', 'keys': 'https://fal.ai/dashboard/keys', 'billing': 'https://fal.ai/dashboard/billing'},
    'replicate': {'name': 'Replicate', 'signup': 'https://replicate.com/signin', 'keys': 'https://replicate.com/account/api-tokens', 'billing': 'https://replicate.com/account/billing'},
    'openrouter': {'name': 'OpenRouter', 'signup': 'https://openrouter.ai', 'keys': 'https://openrouter.ai/settings/keys', 'billing': 'https://openrouter.ai/settings/credits'},
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
    # 🎬 OpenRouter (owner 2026-11-10): one key for every image + video model. Prices = OpenRouter's own list (2026-11-10) for the settings below.
    'or-nano-banana': ('openrouter', 'google/gemini-nano-banana-2.1', 'image', 'Nano Banana 2.1', 'Memes, captions, split screens: the text comes out right', 0.04),
    'or-flash-image': ('openrouter', 'google/gemini-3.1-flash-image', 'image', 'Gemini 3.1 Flash Image', 'Product-shot look, clean renders', 0.07),
    'or-grok-lite': ('openrouter', 'x-ai/grok-imagine-video-1.5-lite', 'video', 'Grok Imagine 1.5 lite', 'The cheap viral clip: 5 s, 720p, vertical, ~25 s to make', 0.15),
    'or-veo-lite': ('openrouter', 'google/veo-3.1-lite', 'video', 'Veo 3.1 lite', 'With its own sound (music, voice): 4 s, 720p', 0.20),
    'or-wan3': ('openrouter', 'alibaba/wan-3.0', 'video', 'Wan 3.0', 'Smooth camera moves, cinematic: 5 s, 480p', 0.25),
    'or-kling3': ('openrouter', 'kwaivgi/kling-v3.0-std', 'video', 'Kling 3.0', 'Great people and motion: 5 s, 720p (sports footage the others refuse)', 0.63),   # real bill 2026-11-10: $0.63 at 720p 16:9
    # "is this AI?" grade (owner 2026-11-10: "real vids… people questioning every proof"): the three that passed our own look test
    'or-seedance-fast': ('openrouter', 'bytedance/seedance-2.0-fast', 'video', 'Seedance 2.0 fast', 'Looks like real phone footage: street, food, people. 5 s, 720p', 0.46),
    'or-veo-fast': ('openrouter', 'google/veo-3.1-fast', 'video', 'Veo 3.1 fast', 'Real people talking, with their voice and city sound. 4 s', 0.40),
    'or-kling3-pro': ('openrouter', 'kwaivgi/kling-v3.0-pro', 'video', 'Kling 3.0 Pro', 'The hero clip: animals and faces that hold up frame by frame. 5 s', 0.84),
    'or-gpt-image-mini': ('openrouter', 'openai/gpt-5-image-mini', 'image', 'GPT-5 Image mini', 'Coin logos and icons: clean edges, the ticker spelled right', 0.05),
}
# per-model request settings for OpenRouter's /videos, and what we saw when we ran it (2026-11-10, real calls, real files in public/media/samples)
OR_VIDEO = {
    'or-grok-lite': {'duration': 5, 'resolution': '720p', 'aspect_ratio': '9:16'},
    'or-veo-lite': {'duration': 4, 'resolution': '720p', 'aspect_ratio': '9:16', 'generate_audio': True},
    'or-wan3': {'duration': 5, 'resolution': '480p', 'aspect_ratio': '9:16'},
    'or-kling3': {'duration': 5, 'resolution': '720p', 'aspect_ratio': '9:16'},
    'or-seedance-fast': {'duration': 5, 'resolution': '720p', 'aspect_ratio': '9:16'},
    'or-veo-fast': {'duration': 4, 'resolution': '720p', 'aspect_ratio': '9:16', 'generate_audio': True},
    'or-kling3-pro': {'duration': 5, 'resolution': '720p', 'aspect_ratio': '9:16'},
}
TESTED = {'or-seedance-fast': ('/media/samples/street-omelette.mp4', 148), 'or-veo-fast': ('/media/samples/street-interview.mp4', 58), 'or-kling3-pro': ('/media/samples/dog-trader.mp4', 148),
          'or-gpt-image-mini': ('/media/samples/coin-logos.jpg', 20), 'or-veo-lite': ('/media/samples/hotel-lobby.mp4', 25), 'or-wan3': ('/media/samples/faceless-avatar.mp4', 66),
          'or-flash-image': ('/media/samples/ai-vs-handmade.jpg', 9), 'or-nano-banana': ('/media/samples/ai-will-replace-you.jpeg', 12), 'or-kling3': ('/showcase/pob/hoops.mp4', 140)}
# 🔥 what is going viral on TikTok / Reels (Nov 2026 trend charts) as a FEELESS twist: {idea} = the folder's own text
PRESETS = [
    {'id': 'is-this-ai', 'label': 'Is this AI?', 'kind': 'video', 'model': 'or-seedance-fast', 'trend': 'The "is this real?" clips: phone footage nobody can call',
     'prompt': 'Handheld iPhone footage, photorealistic, natural shaky camera, real light and real people in the background, no text: {idea}'},
    {'id': 'street-interview', 'label': 'Street interview', 'kind': 'video', 'model': 'or-veo-fast', 'trend': 'AI street interviews with a punchline, with real voice',
     'prompt': 'Vertical street interview on a busy city sidewalk, handheld mic in frame, real city noise, documentary look. The person answers in one short funny line about: {idea}'},
    {'id': 'pet-reacts', 'label': 'Pet reacts', 'kind': 'video', 'model': 'or-kling3-pro', 'trend': 'Animals doing human jobs: the most shared AI genre',
     'prompt': 'Ultra realistic phone video, real fur detail, natural motion, warm home light: a pet reacts like a person to {idea}'},
    {'id': 'coin-logos', 'label': 'Coin logo ideas', 'kind': 'image', 'model': 'or-gpt-image-mini', 'trend': 'What coin launchers ask for first: four logo routes at once',
     'prompt': 'A 2x2 grid of four distinct professional coin logo concepts (flat vector, bold mascot, neon geometric, gold embossed), each a clean round token emblem with its ticker under it, dark background, crisp edges. The coin: {idea}'},
    {'id': 'hotel-lobby', 'label': 'Hotel lobby booth', 'kind': 'video', 'model': 'or-veo-lite', 'trend': 'TikTok: pets and friends dropped into a lobby booth',
     'prompt': 'Vertical phone video, viral "hotel lobby" format: a cool cat in tiny gold sunglasses sits in a velvet booth of a fancy hotel lobby at night, turns to camera and nods to the beat, lounge music. Theme: {idea}'},
    {'id': 'faceless-avatar', 'label': 'Faceless explainer', 'kind': 'video', 'model': 'or-wan3', 'trend': 'Faceless AI channels: one consistent avatar, no face on camera',
     'prompt': 'Vertical faceless explainer video: a sleek glowing green robot cat in a dark studio points at a floating neon chart, camera pushes in, cinematic. About: {idea}'},
    {'id': 'ai-vs-handmade', 'label': 'AI vs handmade', 'kind': 'image', 'model': 'or-flash-image', 'trend': 'TikTok split screens set to "Dame Hombro"',
     'prompt': 'Vertical 9:16 split screen, viral "AI vs HANDMADE": left a glossy AI render, right the same thing made by hand on a messy desk, bold caption bar. Subject: {idea}'},
    {'id': 'ai-will-replace-you', 'label': 'AI will replace you', 'kind': 'image', 'model': 'or-nano-banana', 'trend': 'Reels: the polished AI demo vs messy real life',
     'prompt': 'Vertical 9:16 meme photo, "AI will replace you": top half a flawless AI demo captioned "AI DEMO", bottom half the messy real version captioned "REAL LIFE". Subject: {idea}'},
]
DEFAULT = {('fal', 'image'): 'fal-flux-schnell', ('fal', 'video'): 'fal-wan22-5b', ('replicate', 'image'): 'rep-flux-schnell', ('replicate', 'video'): 'rep-wan22-fast',
           ('openrouter', 'image'): 'or-gpt-image-mini', ('openrouter', 'video'): 'or-seedance-fast'}
# 👤 image → video ("bring him to life", owner 2026-11-12: a made image becomes a character that moves). The value is the model that takes a start
# image: OpenRouter's /videos takes image_url on the same model; fal and Replicate have an image-to-video twin per family. None here = cannot.
I2V = {
    'or-seedance-fast': 'bytedance/seedance-2.0-fast', 'or-kling3': 'kwaivgi/kling-v3.0-std', 'or-kling3-pro': 'kwaivgi/kling-v3.0-pro',
    'or-veo-fast': 'google/veo-3.1-fast', 'or-veo-lite': 'google/veo-3.1-lite', 'or-wan3': 'alibaba/wan-3.0',
    'fal-wan22-5b': 'fal-ai/wan/v2.2-5b/image-to-video', 'fal-wan22-a14b': 'fal-ai/wan/v2.2-a14b/image-to-video',
    'fal-wan25': 'fal-ai/wan-25-preview/image-to-video', 'fal-kling25': 'fal-ai/kling-video/v2.5-turbo/pro/image-to-video',
    'rep-seedance-lite': 'bytedance/seedance-1-lite', 'rep-wan22-fast': 'wan-video/wan-2.2-i2v-fast', 'rep-wan25': 'wan-video/wan-2.5-i2v',
}


def i2v_model(model_id):
    """The model that runs this pick FROM an image, or ValueError. Pure."""
    m = I2V.get(model_id)
    if not m:
        raise ValueError(f"{(MODELS.get(model_id) or ['', '', '', model_id])[3]} cannot start from an image. Pick Seedance, Kling, Veo or Wan.")
    return m
ORDER = ('fal', 'replicate', 'openrouter')
HOUSE_DAILY_USD = 2.0   # 🔒 staff agents on FEELESS's own OpenRouter key: at most this much a day, then it refuses
KINDS = ('image', 'video')
MAX_PROMPT = 1500
MAX_BYTES = 120 * 1024 * 1024
POLL_S = 4
GIVE_UP_S = 15 * 60
EXT = {'image': ('png', 'jpg', 'jpeg', 'webp'), 'video': ('mp4', 'webm', 'mov')}


def _ready(p, linked, house):
    return p in linked or (p == 'openrouter' and house)


def catalog(linked, house=False):
    """The picker: every model (which can run now, its sample and seconds when we ran it), the viral presets, the default per kind. Pure."""
    rows = [{'id': k, 'provider': p, 'providerName': PROVIDERS[p]['name'], 'kind': kd, 'label': lb, 'why': why, 'usd': usd, 'ready': _ready(p, linked, house),
             'sample': (TESTED.get(k) or (None,))[0], 'secs': (TESTED.get(k) or (None, None))[1]}
            for k, (p, _m, kd, lb, why, usd) in MODELS.items()]
    pick = {kd: next((DEFAULT[(p, kd)] for p in ORDER if _ready(p, linked, house)), None) for kd in KINDS}
    presets = [{**x, 'sample': (TESTED.get(x['model']) or (None,))[0], 'secs': (TESTED.get(x['model']) or (None, None))[1], 'usd': MODELS[x['model']][5], 'modelLabel': MODELS[x['model']][3],
                'ready': _ready(MODELS[x['model']][0], linked, house)} for x in PRESETS]
    return {'models': rows, 'linked': sorted(linked), 'house': bool(house), 'pick': pick, 'providers': PROVIDERS, 'presets': presets}


def choose(model_id, kind, linked, house=False):
    """→ (id, provider, model, kind) or ValueError. A model whose provider is not linked is refused, never silently swapped."""
    if kind not in KINDS:
        raise ValueError('Pick image or video.')
    mid = model_id or next((DEFAULT[(p, kind)] for p in ORDER if _ready(p, linked, house)), None)
    if not mid:
        raise ValueError('Link OpenRouter, fal.ai or Replicate first: images and video run on your own account.')
    if mid not in MODELS:
        raise ValueError('Unknown model.')
    p, m, kd = MODELS[mid][:3]
    if kd != kind:
        raise ValueError(f'{MODELS[mid][3]} makes {kd}s, not {kind}s.')
    if not _ready(p, linked, house):
        raise ValueError(f'Link {PROVIDERS[p]["name"]} first: this model runs on your own account.')
    return mid, p, m, kd


def fill(preset_id, idea):
    """A viral preset's prompt with the folder's own words in it. Pure."""
    x = next((x for x in PRESETS if x['id'] == preset_id), None)
    if not x:
        raise ValueError('Unknown format.')
    return x['prompt'].replace('{idea}', re.sub(r'\s+', ' ', str(idea or '')).strip()[:600] or 'FEELESS, the trader\'s terminal'), x['model'], x['kind']


def clean_prompt(text):
    t = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(t) < 3:
        raise ValueError('Say what to make.')
    return t[:MAX_PROMPT]


def submit_req(provider, model, prompt, key, model_id=None, image=None):
    """→ (method, url, headers, json) for the first call. `image` = a data URL or https URL that becomes the first frame (image → video). Pure."""
    if provider == 'openrouter':
        return 'POST', 'https://openrouter.ai/api/v1/videos', {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, {'model': model, 'prompt': prompt, **({'image_url': image} if image else {}), **OR_VIDEO.get(model_id, {})}
    if provider == 'fal':
        return 'POST', f'https://queue.fal.run/{model}', {'Authorization': f'Key {key}', 'Content-Type': 'application/json'}, {'prompt': prompt, **({'image_url': image} if image else {})}
    return 'POST', f'https://api.replicate.com/v1/models/{model}/predictions', {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, {'input': {'prompt': prompt, **({'image': image} if image else {})}}


def handle_of(provider, body):
    """The provider's answer to a submit → what we poll later (no key in it). Pure."""
    body = body or {}
    if provider == 'openrouter':
        if not body.get('id'):
            raise ValueError(str((body.get('error') or {}).get('message') if isinstance(body.get('error'), dict) else body.get('error') or 'OpenRouter did not start the job.')[:200])
        return {'status': body.get('polling_url') or f"https://openrouter.ai/api/v1/videos/{body['id']}", 'result': f"https://openrouter.ai/api/v1/videos/{body['id']}/content", 'rid': body['id']}
    if provider == 'fal':
        if not body.get('status_url') or not body.get('response_url'):
            raise ValueError(str(body.get('detail') or 'fal.ai did not start the job.')[:200])
        return {'status': body['status_url'], 'result': body['response_url'], 'rid': body.get('request_id')}
    if not (body.get('urls') or {}).get('get'):
        raise ValueError(str(body.get('detail') or body.get('title') or 'Replicate did not start the job.')[:200])
    return {'status': body['urls']['get'], 'result': body['urls']['get'], 'rid': body.get('id')}


def auth(provider, key):
    return {'Authorization': f'Key {key}'} if provider == 'fal' else {'Authorization': f'Bearer {key}'}   # Replicate + OpenRouter: Bearer


def state_of(provider, body):
    """A poll answer → ('running'|'done'|'failed', why). Pure."""
    body = body or {}
    s = str(body.get('status') or '').upper()
    if provider == 'openrouter':
        if s == 'COMPLETED':
            return 'done', ''
        if s in ('FAILED', 'ERROR', 'CANCELLED', 'CANCELED'):
            return 'failed', str(body.get('error') or s.lower())[:200]
        return 'running', s.lower() or 'pending'
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
    """The finished file's link from the result. Pure. (OpenRouter's file is its /content link, fetched with the key: not here.)"""
    body = body or {}
    if provider == 'openrouter':
        return None
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


def made_by_happy():
    """🎬 The real results Happy made on these models (2026-11-10, unedited, public files): every user's editor shelf leads with them. Pure."""
    name_ = {x['model']: x['label'] for x in PRESETS}
    return [{'id': f'happy-{k}', 'type': 'video' if src.endswith('.mp4') else 'image', 'proof': 'AI', 'title': name_.get(k) or MODELS[k][3], 'src': src, 'q': '', 'pub': True,
             'at': 0, 'cat': 'happy', 'agent': 'Happy', 'happy': True, 'from': f"{MODELS[k][3]} · ${MODELS[k][5]:.2f} · {secs}s to make"}
            for k, (src, secs) in TESTED.items() if k in MODELS]

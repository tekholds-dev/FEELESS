"""🎭 PoC VIDEO SWAP (Slice 4, owner 2026-11-18): drop in a video, get back the same video (same motion, timing, camera and sound) with a
realistic AI-made person in place of the original, high quality, no watermark. Filed into the PoC folder with the before / after side by side
and its cost. Pure: engines, prices, request bodies, the filed record. The job itself runs in video_swap_run.py.

Researched 2026-11-18 (web search + real calls the same day):
- PICK: MiniMax H3 Max Recast on fal.ai (`minimax/h3-max/recast`). Built for exactly this: the source clip + one photo per new person → the
  same clip with the people replaced, the source sound kept, 768P or 1080P, 5 to 30 s. fal moves its older Wan 2.2 Animate Replace to it
  (Wan is removed 2027-01-04). Schema read from fal's own queue OpenAPI (a free real call); price from its model page.
- RUNNER-UP: Runway Aleph 2 on OpenRouter (`runway/aleph-2`, live /videos/models read the same day: 28¢ per output second, 56¢ minimum).
  It edits real footage well but makes no sound (we lay the clip's own sound back) and takes the first 10 s.
- Seedance 2.x refuses a clip with a real person (ByteDance's rule, the owner's real run 2026-11-17), so it is not a swap engine for real footage.
Owner 2026-11-18: both keys live in HQ › Core (fal one day, OpenRouter now); only he and staff agents may spend them; the new person is the
folder's own AI-made character, or one made fresh from his words; 768p by default. No watermark: every engine and portrait model here is called
on a tier whose output has none (Seedream: watermark false)."""
import json
import re
from pathlib import Path

import media_gen as _mg

# id → what it is. `env` = the HQ › Core key it spends (provider_ready.PROVIDERS shows it there).
ENGINES = {
    'fal-h3-recast': {'provider': 'fal', 'env': 'FAL_KEY', 'endpoint': 'minimax/h3-max/recast', 'label': 'MiniMax H3 Max · Recast', 'who': 'fal.ai',
                      'why': 'Built to recast people: same clip, same sound, the new person in every shot. 5 to 30 s, up to 1080p',
                      'minS': 5.0, 'maxS': 30.0, 'sound': 'kept by the engine', 'res': ('768P', '1080P')},
    'or-aleph': {'provider': 'openrouter', 'env': 'OPENROUTER_API_KEY', 'endpoint': 'runway/aleph-2', 'label': 'Runway Aleph 2', 'who': 'OpenRouter',
                 'why': "Runner-up. Edits real footage; makes no sound, so your clip's own sound is laid back. First 10 s",
                 'minS': 1.0, 'maxS': 10.0, 'sound': 'laid back from your clip', 'res': ()},
}
PICK, RUNNER_UP = 'fal-h3-recast', 'or-aleph'
RES_DEFAULT = '768P'          # owner 2026-11-18: 768p by default (1080p on ask)
# 💵 fal's H3 Max Recast page (read 2026-11-18): billed by output duration ($0.085/s at 768p, $0.17/s at 1080p, 5 s minimum) plus input video
# tokens ($0.022 per 1,000 after the first 4,096 free; about 6,750 tokens per second). Reference images cost nothing extra.
H3_RATE = {'768P': 0.085, '1080P': 0.17}
H3_MIN_S = 5.0
H3_TOKENS_S = 6750
H3_FREE_TOKENS = 4096
H3_TOKEN_USD = 0.022 / 1000
ALEPH_RATE, ALEPH_MIN = 0.28, 0.56
# 👤 the new person, when the folder has no AI-made character: one portrait first, on the same account as the swap
PORTRAIT = {
    'fal': {'endpoint': 'fal-ai/bytedance/seedream/v5/lite/text-to-image', 'label': 'Seedream 5 Lite', 'usd': 0.035},   # fal page, 2026-11-18
    'openrouter': {'model': 'google/gemini-3.1-flash-image', 'label': 'Gemini 3.1 Flash Image', 'usd': 0.07},           # media_gen.MODELS or-flash-image
}
MADE_BY = ('fal', 'openrouter', 'replicate')   # a character the folder MADE (an uploaded photo is never used as the new person)
DAY_CAP_USD = 10.0            # 💵 FEELESS's own keys: at most this much on swaps a day, across every agent (judgment call until the owner names one)
PER_SWAP_CAP_USD = _mg.SWAP_CAP_USD   # the owner's own cap per swap (cat.swapCapUsd, set under the swap button) wins over this default
MAX_WORDS = 400
STEPS = ('person', 'sending', 'queued', 'running', 'sound', 'side', 'filed', 'failed')

RECAST_RULE = ('Replace the main person in the video with the person in the reference photo: their face, hair, skin, build and outfit, in every '
               'shot, moving exactly as the original person moves, with the same expressions and lip movement. Keep everything else exactly the same: '
               'the scene, background, other people, camera moves, framing, timing, actions and lighting.')
PORTRAIT_RULE = ('Photorealistic full-length photo of a fictional adult person who does not exist, shot on a phone in soft natural daylight, plain '
                 'uncluttered background, standing facing the camera, face, hair, hands and the whole outfit clearly visible, sharp focus, real skin '
                 'texture, no text, no logo. The person: {words}')


def clean_words(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()[:MAX_WORDS]


def engine(eid):
    if eid not in ENGINES:
        raise ValueError('Pick MiniMax H3 Max Recast or Runway Aleph 2.')
    return ENGINES[eid]


def clean_res(eid, res):
    e = engine(eid)
    if not e['res']:
        return None
    r = str(res or RES_DEFAULT).upper().replace('P', '') + 'P'
    return r if r in e['res'] else RES_DEFAULT


def made_secs(eid, secs):
    """How much of the clip the engine makes: H3 the whole clip (5-30 s), Aleph the first 10 s. Pure."""
    e = engine(eid)
    return round(min(float(secs or 0), e['maxS']), 2)


def fits(eid, secs):
    """'' when the clip fits the engine, else what to do (plain words). Pure."""
    e = engine(eid); s = float(secs or 0)
    if s <= 0:
        return 'That clip could not be read. Add it again as an MP4.'
    if s < e['minS'] - 0.05:
        return f"{e['label']} needs a clip of {e['minS']:.0f} s at least. That one is {s:.1f} s: add a longer clip, or pick {ENGINES[RUNNER_UP]['label']}."
    if eid == PICK and s > e['maxS'] + 0.5:
        return f"{e['label']} takes {e['maxS']:.0f} s at most. That clip is {s:.0f} s: add it again with a start."
    return ''


def heads_up(eid, secs):
    """'' or a plain line the panel shows beside the price: MiniMax refuses a single unbroken shot over 15 s (a refusal costs nothing). Pure."""
    if eid == PICK and float(secs or 0) > 15.5:
        return 'MiniMax takes cuts of 15 s at most: a clip that is one unbroken shot over 15 s is refused at the door, and a refusal costs nothing.'
    return ''


def swap_usd(eid, secs, res=None):
    """The list price of the swap itself for this clip. Pure."""
    s = made_secs(eid, secs)
    if eid == PICK:
        r = clean_res(eid, res)
        out = H3_RATE[r] * max(s, H3_MIN_S)
        tokens = max(0.0, H3_TOKENS_S * s - H3_FREE_TOKENS) * H3_TOKEN_USD
        return round(out + tokens, 2)
    return round(max(ALEPH_RATE * s, ALEPH_MIN), 2)


def quote(eid, secs, res=None, make_person=False):
    """→ {'swap', 'person', 'usd', 'lines'}: what one press costs, split so the owner sees each part. Pure."""
    e = engine(eid); sw = swap_usd(eid, secs, res); pp = PORTRAIT[e['provider']]['usd'] if make_person else 0.0
    lines = [{'what': f"{e['label']} · {made_secs(eid, secs):.1f} s" + (f" · {clean_res(eid, res).lower()}" if e['res'] else ''), 'usd': sw}]
    if make_person:
        lines.append({'what': f"New person: {PORTRAIT[e['provider']]['label']} portrait", 'usd': pp})
    return {'swap': sw, 'person': round(pp, 3), 'usd': round(sw + pp, 2), 'lines': lines}


def env_key(name, env, dotenv=None):
    """🔑 A key saved in HQ › Core: this process's env first, else backend/.env (HQ writes it from the other service while this one runs).
    The value never leaves this function except to the caller that sends it to the provider. Pure apart from the read."""
    v = str((env or {}).get(name) or '').strip()
    if v:
        return v
    return _dotenv(dotenv).get(name, '') if dotenv else ''


_DOTENV = {}   # path → (mtime, {name: value}): read again only when HQ › Core saved it


def _dotenv(path):
    try:
        p = Path(path); m = p.stat().st_mtime
        if _DOTENV.get(str(p), (None,))[0] != m:
            vals = {}
            for line in p.read_text().splitlines():
                k, _s, val = line.partition('=')
                if k.strip() and not k.strip().startswith('#'):
                    vals[k.strip()] = val.strip().strip('"').strip("'")
            _DOTENV[str(p)] = (m, vals)
        return _DOTENV[str(p)][1]
    except OSError:
        return {}


def ready(env, dotenv=None):
    """→ {engine id: True when its HQ › Core key is set}. Names only, never a value."""
    return {k: bool(env_key(e['env'], env, dotenv)) for k, e in ENGINES.items()}


def auto_engine(rdy, secs=None):
    """The pick when its key is set and the clip fits it, else the runner-up when its key is set, else None. Pure."""
    for k in (PICK, RUNNER_UP):
        if rdy.get(k) and (secs is None or not fits(k, secs)):
            return k
    return None


def person_of(doc):
    """The folder's AI-made character, or None (an uploaded photo is never the new person). Pure."""
    ch = (doc or {}).get('character') or {}
    m = next(((x.get('media') or {}) for x in (doc or {}).get('messages') or [] if (x.get('media') or {}).get('id') == ch.get('mid')), {})
    if m.get('status') == 'done' and m.get('kind') == 'image' and m.get('provider') in MADE_BY and str(m.get('url') or '').startswith('/api/cats/media/'):
        return {'mid': m['id'], 'url': m['url'], 'prompt': str(m.get('prompt') or '')[:200], 'source': 'character'}
    return None


def clips_of(doc):
    """The folder's clips a swap can start from, newest first. Pure."""
    out = []
    for x in reversed((doc or {}).get('messages') or []):
        m = x.get('media') or {}
        if m.get('clip') and m.get('status') == 'done' and str(m.get('url') or '').startswith('/api/cats/media/'):
            out.append({'mid': m['id'], 'url': m['url'], 'label': m.get('label') or 'Your clip', 'secs': m.get('secs'), 'fps': m.get('fps'), 'w': m.get('w'), 'h': m.get('h')})
    return out


def portrait_prompt(words):
    w = clean_words(words)
    if len(w) < 3:
        raise ValueError('Say who the new person is (for example "a woman in her 30s, short red hair, denim jacket").')
    return PORTRAIT_RULE.format(words=w)


def portrait_req(provider, key, words):
    """→ (method, url, headers, json) for the new person's portrait. Pure."""
    p = portrait_prompt(words)
    if provider == 'fal':
        return 'POST', f"https://queue.fal.run/{PORTRAIT['fal']['endpoint']}", {'Authorization': f'Key {key}', 'Content-Type': 'application/json'}, {
            'prompt': p, 'image_size': 'portrait_4_3', 'output_format': 'jpeg', 'watermark': False, 'sequential_image_generation': 'disabled'}
    return 'POST', 'https://openrouter.ai/api/v1/chat/completions', {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, {
        'model': PORTRAIT['openrouter']['model'], 'modalities': ['image', 'text'], 'messages': [{'role': 'user', 'content': p}]}


def swap_req(eid, key, video_url, image_url, note='', res=None, aspect=None):
    """→ (method, url, headers, json) for the swap itself. `video_url` / `image_url` = https links the provider can fetch. Pure."""
    e = engine(eid); n = clean_words(note)
    if not video_url or not image_url:
        raise ValueError('A swap needs your clip and the new person.')
    if eid == PICK:
        return 'POST', f"https://queue.fal.run/{e['endpoint']}", {'Authorization': f'Key {key}', 'Content-Type': 'application/json'}, {
            'video_url': video_url, 'reference_image_urls': [image_url], 'resolution': clean_res(eid, res), 'enhance_realism': True,
            'prompt': (RECAST_RULE + (f' Also: {n}' if n else ''))[:2000]}
    return _mg.v2v_req('or-aleph-swap', key, image_url, video_url, n, ENGINES['or-aleph']['maxS'], aspect)


def portrait_url(provider, body):
    """The portrait from the provider's answer: fal → its file link; OpenRouter → a data URL in the chat answer. Pure."""
    body = body or {}
    if provider == 'fal':
        im = (body.get('images') or [{}])[0] if isinstance(body.get('images'), list) else {}
        return (im or {}).get('url') or None
    im = ((((body.get('choices') or [{}])[0].get('message') or {}).get('images') or [{}])[0].get('image_url') or {}).get('url', '')
    return im if re.match(r'data:image/(png|jpe?g|webp);base64,', im or '') else None


def side_args(before, after, out, height=720):
    """ffmpeg: the before (left) and after (right) at the same height, one frame rate, the after's sound (= the clip's own), cut to the shorter."""
    h = int(height) // 2 * 2
    vf = (f'[0:v]scale=-2:{h},setsar=1,fps=30[a];[1:v]scale=-2:{h},setsar=1,fps=30[b];[a][b]hstack=inputs=2:shortest=1[v]')
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(before), '-i', str(after), '-filter_complex', vf, '-map', '[v]', '-map', '1:a?',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)]


def ref_args(src, out, max_s=None, short_side=1080):
    """ffmpeg: the clip the engine fetches: the short side at most 1080 px, its sound kept, at most `max_s` s, H.264."""
    s = int(short_side)
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(src), *(['-t', f'{float(max_s):.2f}'] if max_s else []), '-map', '0:v:0', '-map', '0:a?',
            '-vf', f"scale='if(gt(iw,ih),-2,min({s},iw))':'if(gt(iw,ih),min({s},ih),-2)'", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(out)]


def public_job(j):
    """A job as the page sees it (never a key, never a provider link that needs one). Pure."""
    keep = ('id', 'ws', 'engine', 'label', 'res', 'step', 'why', 'at', 'doneAt', 'usd', 'quote', 'before', 'after', 'side', 'person', 'poc', 'secs', 'by', 'paid')
    return {k: j.get(k) for k in keep if j.get(k) is not None}


def record(job, n, now):
    """🧾 The PoC folder row a finished swap files: before / after side by side, its cost and what made it. Pure."""
    e = ENGINES.get(job.get('engine')) or {}
    q = job.get('quote') or {}
    swap = {'engine': e.get('label'), 'engineId': job.get('engine'), 'who': e.get('who'), 'runnerUp': ENGINES[RUNNER_UP]['label'] if job.get('engine') == PICK else ENGINES[PICK]['label'],
            'res': (job.get('res') or '').lower() or None, 'before': job.get('before'), 'after': job.get('after'), 'side': job.get('side'), 'person': job.get('person'),
            'sound': e.get('sound'), 'watermark': 'none', 'secs': job.get('secs'), 'lines': q.get('lines') or [], 'paid': job.get('paid') or 'FEELESS key (HQ › Core)',
            'job': job.get('id'), 'tookS': round(float(now) - float(job.get('at') or now))}
    label = str((job.get('before') or {}).get('label') or 'your clip')[:60]
    return {'id': f"poc{job['id'][1:]}", 'ws': job.get('ws'), 'n': n, 'kind': 'PoC', 'at': round(now), 'status': 'closed', 'paper': True,
            'topic': f'Video swap: {label}'[:120], 'calls': [], 'by': 'Video swap', 'cost': q.get('usd'), 'swap': swap,
            'media': [x for x in ({'id': job['id'], 'kind': 'video', 'url': (job.get('after') or {}).get('url'), 'label': 'After', 'prompt': f"{e.get('label')} swap of {label}"},
                                  {'id': job['id'] + 's', 'kind': 'video', 'url': job.get('side'), 'label': 'Before | after', 'prompt': 'Side by side'}) if x['url']]}


def jobs_read(path):
    try:
        d = json.loads(Path(path).read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def day_spent(jobs, day_start):
    """$ the swaps on FEELESS's own keys started since `day_start` were quoted (a failed one after the provider took it still counts). Pure."""
    return round(sum(float((j.get('quote') or {}).get('usd') or 0) for j in jobs.values() if float(j.get('at') or 0) >= day_start
                     and j.get('keyFrom', 'house') == 'house' and (j.get('step') != 'failed' or j.get('taken'))), 2)

"""✅ Ready for real money? (owner 2026-11-17: "finish all and assure real money readyness")

One $0 check before the owner spends: only free, read-only calls (OpenRouter's key and credit reads, its public model lists), and the
local pieces a paid run needs (ffmpeg, the public https link for a swap's references). It never makes an image, a video or a model reply,
so it can never cost anything. Each row says ok or not, and the one thing to do when not. The judges are pure; `run` makes the calls.
"""
import shutil
from pathlib import Path

import media_gen as mg

OR = 'https://openrouter.ai/api/v1'


def row(rid, ok, what, say):
    return {'id': rid, 'ok': bool(ok), 'what': what, 'say': say}


def judge_key(status, key_j, credits_j):
    """The OpenRouter key works, and how much credit is left on the account."""
    if status in (401, 403):
        return [row('or-key', False, 'OpenRouter key', 'OpenRouter refused your key. Paste a fresh one under Keys.')]
    if status != 200:
        return [row('or-key', False, 'OpenRouter key', f'OpenRouter did not answer ({status}). Try again in a minute.')]
    d = (key_j or {}).get('data') or {}; c = (credits_j or {}).get('data') or {}
    out = [row('or-key', True, 'OpenRouter key', 'Works.' + (' It is a free-tier key: paid models will refuse.' if d.get('is_free_tier') else ''))]
    if c.get('total_credits') is not None:
        left = round(float(c.get('total_credits') or 0) - float(c.get('total_usage') or 0), 2)
        cap_left = d.get('limit_remaining')
        if cap_left is not None:
            left = min(left, round(float(cap_left), 2))
        swap = mg.v2v_cost('or-aleph-swap', mg.swap_max('or-aleph-swap')); hold = mg.swap_hold('or-aleph-swap')
        out.append(row('or-credit', left >= hold, 'OpenRouter credit', f'${left:.2f} left on the account.'
                       + (f' Enough for an Aleph swap (OpenRouter wants ${hold:.2f} on the account first; a 10 s swap costs about ${swap:.2f}).' if left >= hold
                          else f' OpenRouter wants ${hold:.2f} on the account before an Aleph swap starts (a 10 s swap itself is about ${swap:.2f}): top up on openrouter.ai first.')))
    return out


def judge_video(models_j, aspect='9:16'):
    """The swap models we send to still exist, and Aleph 2 still accepts exactly what we send it (its keyframe as passthrough)."""
    items = models_j.get('data') or [] if isinstance(models_j, dict) else models_j if isinstance(models_j, list) else []
    rows_ = {r.get('id'): r for r in items if isinstance(r, dict)}
    out = []
    for mid, v in mg.OR_SWAP.items():
        r = rows_.get(v[0])
        out.append(row(f'video-{mid}', bool(r), v[1], 'Listed on OpenRouter.' if r else f'{v[0]} is gone from OpenRouter. Pick another swap model.'))
    a = rows_.get(mg.ALEPH['or-aleph-swap'][0])
    if a:
        body = mg.v2v_req('or-aleph-swap', 'k', 'https://x/i.jpg', 'https://x/v.mp4', '', 10, aspect)[3]
        sent = set(((body.get('provider') or {}).get('options') or {}).get('runway') or {})
        allowed = set(a.get('allowed_passthrough_parameters') or [])
        ok = sent <= allowed and aspect in (a.get('supported_aspect_ratios') or [aspect])
        out.append(row('aleph-shape', ok, 'Aleph 2 request', 'Takes your character as its keyframe, in 9:16.' if ok
                       else f'Aleph 2 changed what it accepts (allows {sorted(allowed)}, we send {sorted(sent)}). Nothing was sent: this one is ours to fix.'))
    return out


def judge_flagships(models_j, flagships):
    ids = {r.get('id') for r in (models_j or {}).get('data') or [] if isinstance(r, dict)}
    gone = [v for v in flagships.values() if v not in ids]
    return [row('comp-models', not gone, 'COMP exam models', 'Claude, GPT and Grok are all on OpenRouter.' if not gone else f'Gone from OpenRouter: {", ".join(gone)}.')]


def judge_local(ffmpeg, public_site, cloudflared):
    return [row('ffmpeg', bool(ffmpeg), 'ffmpeg', 'Ready to trim your clips and put the sound back.' if ffmpeg else 'Install ffmpeg (brew install ffmpeg): swaps need it.'),
            row('public-link', bool(public_site or cloudflared), 'Public link for swaps',
                f'Your clip goes to OpenRouter through {public_site}.' if public_site else 'Your clip goes through a 2-hour Cloudflare link (cloudflared is installed).' if cloudflared
                else 'OpenRouter only takes https links: install cloudflared (brew install cloudflared), or set PUBLIC_SITE_URL.')]


def judge_cap(view):
    v = view or {}
    return [row('day-cap', not v.get('over'), 'Your day cap', f"${v.get('spentUsd', 0):.2f} of ${v.get('capUsd', 0):.2f} used today, ${v.get('leftUsd', 0):.2f} left."
                + (' Raise it to make more today.' if v.get('over') else ''))]


def ffmpeg_path():
    return shutil.which('ffmpeg') or ('/opt/homebrew/bin/ffmpeg' if Path('/opt/homebrew/bin/ffmpeg').is_file() else '')


def cloudflared_path():
    return shutil.which('cloudflared') or ('/opt/homebrew/bin/cloudflared' if Path('/opt/homebrew/bin/cloudflared').is_file() else '')


async def run(http, key, flagships, public_site='', spend_view=None):
    """→ {'ok': all ok, 'rows': [...]}: free reads only. `key` = the OpenRouter key his agents use (never returned)."""
    out = []
    if key:
        auth = {'Authorization': f'Bearer {key}'}
        try:
            k = await http.get(f'{OR}/key', headers=auth, timeout=20)
            c = await http.get(f'{OR}/credits', headers=auth, timeout=20) if k.status_code == 200 else None
            out += judge_key(k.status_code, k.json() if k.status_code == 200 else {}, c.json() if c is not None and c.status_code == 200 else {})
        except Exception as e:   # noqa: BLE001 — a check that cannot reach OpenRouter says so
            out.append(row('or-key', False, 'OpenRouter key', f'Could not reach OpenRouter ({type(e).__name__}).'))
    else:
        out.append(row('or-key', False, 'OpenRouter key', 'No OpenRouter key on your agents. Paste one under Keys.'))
    try:
        v = await http.get(f'{OR}/videos/models', timeout=20)
        out += judge_video(v.json() if v.status_code == 200 else {})
    except Exception as e:   # noqa: BLE001
        out.append(row('video-list', False, 'Video models', f'Could not read OpenRouter\'s video list ({type(e).__name__}).'))
    try:
        m = await http.get(f'{OR}/models', timeout=20)
        out += judge_flagships(m.json() if m.status_code == 200 else {}, flagships)
    except Exception as e:   # noqa: BLE001
        out.append(row('comp-models', False, 'COMP exam models', f'Could not read OpenRouter\'s model list ({type(e).__name__}).'))
    out += judge_local(ffmpeg_path(), public_site, cloudflared_path())
    if spend_view is not None:
        out += judge_cap(spend_view)
    return {'ok': all(r['ok'] for r in out), 'rows': out}

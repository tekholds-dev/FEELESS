"""✅ The $0 readiness check (owner 2026-11-17: "assure real money readyness"): free reads only, network faked here."""
import asyncio

import media_gen as mg
import money_ready as mr

ALEPH = {'id': 'runway/aleph-2', 'supported_aspect_ratios': ['16:9', '9:16'], 'allowed_passthrough_parameters': ['contentModeration', 'keyframes']}
VIDEOS = {'data': [ALEPH] + [{'id': v[0]} for k, v in mg.OR_SWAP.items() if k != 'or-aleph-swap']}
MODELS = {'data': [{'id': 'anthropic/claude-opus-5.5'}, {'id': 'openai/gpt-4o-mini'}, {'id': 'x-ai/grok-4.7'}]}
FLAG = {'claude': 'anthropic/claude-opus-5.5', 'gpt': 'openai/gpt-4o-mini', 'grok': 'x-ai/grok-4.7'}


class R:
    def __init__(self, code, j):
        self.status_code, self._j = code, j

    def json(self):
        return self._j


class H:
    def __init__(self, key_code=200, credit=(20, 12.07), videos=VIDEOS):
        self.urls, self.key_code, self.credit, self.videos = [], key_code, credit, videos

    async def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        if url.endswith('/key'):
            return R(self.key_code, {'data': {'limit_remaining': None, 'is_free_tier': False}})
        if url.endswith('/credits'):
            return R(200, {'data': {'total_credits': self.credit[0], 'total_usage': self.credit[1]}})
        if url.endswith('/videos/models'):
            return R(200, self.videos)
        return R(200, MODELS)


def test_a_ready_setup_passes_with_reads_only(monkeypatch):
    monkeypatch.setattr(mr.shutil, 'which', lambda n: f'/usr/bin/{n}')
    h = H(); out = asyncio.run(mr.run(h, 'sk-or-x', FLAG, '', {'spentUsd': 1, 'capUsd': 10, 'leftUsd': 9, 'over': False}))
    assert out['ok'], [r for r in out['rows'] if not r['ok']]
    assert all('/videos' not in u or u.endswith('/videos/models') for u in h.urls)   # never POSTs, never makes a video
    credit = next(r for r in out['rows'] if r['id'] == 'or-credit')
    assert '$7.93 left' in credit['say']
    assert 'sk-or-x' not in str(out)


def test_each_gap_says_the_one_thing_to_do(monkeypatch):
    monkeypatch.setattr(mr, 'ffmpeg_path', lambda: ''); monkeypatch.setattr(mr, 'cloudflared_path', lambda: '')
    broken = {'data': [{**ALEPH, 'allowed_passthrough_parameters': ['contentModeration']}]}
    out = asyncio.run(mr.run(H(credit=(5, 4), videos=broken), 'k', FLAG, '', {'spentUsd': 10, 'capUsd': 10, 'leftUsd': 0, 'over': True}))
    bad = {r['id']: r['say'] for r in out['rows'] if not r['ok']}
    assert not out['ok'] and 'top up' in bad['or-credit'] and 'ours to fix' in bad['aleph-shape'] and 'brew install ffmpeg' in bad['ffmpeg']
    assert 'cloudflared' in bad['public-link'] and 'Raise it' in bad['day-cap'] and 'video-or-seedance-swap' in bad
    assert asyncio.run(mr.run(H(key_code=401), 'k', FLAG))['rows'][0]['say'].startswith('OpenRouter refused your key')
    assert 'Paste one' in asyncio.run(mr.run(H(), '', FLAG))['rows'][0]['say']


def test_a_bare_list_of_models_is_judged_too():
    rows = mr.judge_video(VIDEOS['data'])
    assert any(r['id'] == 'aleph-shape' and r['ok'] for r in rows) and mr.judge_video(None) and not mr.judge_video('x')[0]['ok']

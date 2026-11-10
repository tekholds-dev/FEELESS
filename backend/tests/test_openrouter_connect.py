"""Owner 2026-11-10: one-click Connect OpenRouter. The server swaps OpenRouter's sign-in code (plus the tab's verifier) for a key,
seals it on the agent, and never sends it back. A bad or reused code changes nothing."""
from test_play_studio import _server

import cat_keys as ck

GOOD = 'v' * 43   # a real PKCE verifier is 43 to 128 characters


class _R:
    def __init__(self, status, body):
        self.status_code, self._b, self.headers = status, body, {'content-type': 'application/json'}

    def json(self):
        return self._b


def _openrouter(monkeypatch, fs, answer):
    sent = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, json=None, **kw):
            sent.append((url, json)); return answer
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H())
    return sent


def test_connect_seals_the_key_and_never_echoes_it(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    sent = _openrouter(monkeypatch, fs, _R(200, {'key': 'sk-or-v1-made-for-feeless-1234'}))
    r = c.post('/api/cats/g/action', json={'ownerId': 'g', 'session': 'g', 'action': 'openrouter_connect', 'secret': 'the-code', 'text': GOOD})
    assert r.status_code == 200, r.text
    assert sent == [('https://openrouter.ai/api/v1/auth/keys', {'code': 'the-code', 'code_verifier': GOOD, 'code_challenge_method': 'S256'})]
    assert 'made-for-feeless' not in r.text and [x['last4'] for x in r.json()['cat']['apiDrawer'] if x['provider'] == 'openrouter'] == ['1234']
    assert ck.key_for(store['cats']['g'], 'openrouter', data_dir=tmp_path) == 'sk-or-v1-made-for-feeless-1234'   # sealed; its calls now bill the user's OpenRouter


def test_a_bad_code_or_verifier_changes_nothing(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    sent = _openrouter(monkeypatch, fs, _R(400, {'error': {'message': 'Invalid code', 'code': 400}}))
    r = c.post('/api/cats/g/action', json={'ownerId': 'g', 'session': 'g', 'action': 'openrouter_connect', 'secret': 'old-code', 'text': GOOD})
    assert r.status_code == 400 and 'Connect OpenRouter again' in r.json()['detail']
    r = c.post('/api/cats/g/action', json={'ownerId': 'g', 'session': 'g', 'action': 'openrouter_connect', 'secret': 'x', 'text': 'short'})
    assert r.status_code == 400 and len(sent) == 1   # a malformed verifier never reaches OpenRouter
    assert ck.key_for(store['cats']['g'], 'openrouter', data_dir=tmp_path) is None
    r = c.post('/api/cats/g/action', json={'ownerId': 'someone-else', 'session': 'x', 'action': 'openrouter_connect', 'secret': 'c', 'text': GOOD})
    assert r.status_code in (401, 403)   # only the agent's owner can connect it

"""🏁 the Raceway endpoints: practice needs no sign-in, a verified Telegram player lands on the board, a run faster than the server's clock is refused."""
import json
import time


def _client():
    import reputation_service as rs
    from fastapi.testclient import TestClient
    return rs, TestClient(rs.app)


def _honest(rs, c, body):
    r = c.post('/api/reputation/familia-race/start', json=body); assert r.status_code == 200, r.text
    tok, tr = r.json()['token'], r.json()['track']
    ms = tr['par']; rs._race_tokens[tok]['at'] -= ms / 1000 + 1          # the run really took `ms` on the server's clock
    splits = [int(ms * (k + 1) / len(tr['cps'])) for k in range(len(tr['cps']))]
    return c.post('/api/reputation/familia-race/finish', json={**body, 'token': tok, 'ms': ms, 'splits': splits, 'vehicle': 'bike'})


def test_practice_run_needs_no_sign_in_and_the_clock_is_checked():
    rs, c = _client()
    g = c.get('/api/reputation/familia-race').json()
    assert len(g['track']['cps']) == 6 and g['board'] == [] or isinstance(g['board'], list)
    r = _honest(rs, c, {})
    assert r.status_code == 200 and r.json()['practice'] is True
    s = c.post('/api/reputation/familia-race/start', json={}).json()                      # finishing at once = faster than the clock
    tr = s['track']; bad = c.post('/api/reputation/familia-race/finish', json={'token': s['token'], 'ms': tr['par'], 'splits': [int(tr['par'] * (k + 1) / 6) for k in range(6)]})
    assert bad.status_code == 400 and 'clock' in bad.json()['detail']
    again = c.post('/api/reputation/familia-race/finish', json={'token': s['token'], 'ms': tr['par'], 'splits': [1, 2, 3, 4, 5, 6]})
    assert again.status_code == 400                                                         # a token is single-use


def test_a_telegram_player_lands_on_the_day_board(monkeypatch):
    import tg_auth
    rs, c = _client()
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123:TEST')
    init = tg_auth.sign({'auth_date': str(int(time.time())), 'user': json.dumps({'id': 4242, 'first_name': 'Vito'})}, '123:TEST')
    r = _honest(rs, c, {'tg': init})
    assert r.status_code == 200 and r.json()['best'] is True and r.json()['mp'] == 0        # MP needs a family (a wallet) — Telegram races for glory
    assert any(row['name'] == 'Vito' for row in c.get('/api/reputation/familia-race').json()['board'])
    forged = c.post('/api/reputation/familia-race/start', json={'tg': init.replace('Vito', 'Tony')})
    assert forged.status_code == 401

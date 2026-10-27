"""🎯 Strike Zone endpoints: a guest plays but saves nothing, a Telegram player levels up + keeps a loadout, a result faster than the server's clock is
refused, the online room relays one player's moves to the other."""
import json
import time


def _client():
    import reputation_service as rs
    from fastapi.testclient import TestClient
    return rs, TestClient(rs.app)


def test_guest_plays_and_the_clock_is_checked():
    rs, c = _client()
    home = c.get('/api/reputation/arena').json()
    assert 'rifle' in home['guns'] and home['me']['guest'] and home['me']['level'] == 1
    tok = c.post('/api/reputation/arena/start', json={}).json()['token']
    early = c.post('/api/reputation/arena/result', json={'token': tok, 'kills': 3, 'deaths': 1})
    assert early.status_code == 400 and 'short' in early.json()['detail']
    tok = c.post('/api/reputation/arena/start', json={}).json()['token']; rs._arena_tokens[tok]['at'] -= 120
    r = c.post('/api/reputation/arena/result', json={'token': tok, 'kills': 3, 'deaths': 1, 'heads': 1, 'won': True})
    assert r.status_code == 200 and r.json()['guest'] and r.json()['xp'] == 50 + 300 + 50 + 400


def test_a_telegram_player_levels_up_and_keeps_a_loadout(monkeypatch):
    import tg_auth
    rs, c = _client(); monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123:TEST')
    tg = tg_auth.sign({'auth_date': str(int(time.time())), 'user': json.dumps({'id': 77, 'first_name': 'Vito'})}, '123:TEST')
    tok = c.post('/api/reputation/arena/start', json={'tg': tg}).json()['token']; rs._arena_tokens[tok]['at'] -= 300
    r = c.post('/api/reputation/arena/result', json={'tg': tg, 'token': tok, 'kills': 12, 'deaths': 2, 'heads': 5, 'won': True}).json()
    assert r['levelUp'] and r['me']['level'] >= 3 and r['board'][0]['name'] == 'Vito'
    lo = c.post('/api/reputation/arena/loadout', json={'tg': tg, 'loadout': {'gun': 'smg', 'optic': 'dot', 'skin': 'gold'}}).json()
    assert lo['loadout']['gun'] == 'smg' and lo['loadout']['optic'] == 'dot' and lo['loadout']['skin'] == 'green'   # gold is level 15
    assert c.post('/api/reputation/arena/loadout', json={'loadout': {}}).status_code == 401


def test_the_online_room_relays_moves_between_players():
    rs, c = _client()
    with c.websocket_connect('/api/reputation/arena/ws?room=t1&name=A') as a:
        assert a.receive_json()['t'] == 'hello'
        with c.websocket_connect('/api/reputation/arena/ws?room=t1&name=B') as b:
            hello = b.receive_json(); assert hello['t'] == 'hello' and hello['peers'][0]['name'] == 'A'
            assert a.receive_json() == {'t': 'join', 'id': hello['id'], 'name': 'B'}
            b.send_json({'t': 'state', 'p': [1, 0, 2], 'yaw': 0.5})
            got = a.receive_json(); assert got['t'] == 'state' and got['id'] == hello['id'] and got['p'] == [1, 0, 2]

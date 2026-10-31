"""☁ AN AGENT'S CLOUD IS ITS OWNER'S (owner 2026-10-30: "FEELESS will not fund any storage"). The owner connects their own Google Drive or
Dropbox with the provider's sign-in (OAuth): FEELESS never sees that password and keeps only the refresh pass, sealed per agent. Files go to
a `FEELESS/<agent name>` folder in THEIR account (Drive: drive.file scope, so FEELESS sees only what it made). One pooled httpx client is
passed in; every call here is plain HTTP, faked in tests.
Keys (backend/.env): GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET · DROPBOX_APP_KEY / DROPBOX_APP_SECRET. Unset ⇒ that button says so."""
import json
import os
import secrets
import time
from urllib.parse import urlencode

PROVIDERS = {
    'gdrive': {'label': 'Google Drive', 'free': '15 GB free', 'id': 'GOOGLE_OAUTH_CLIENT_ID', 'secret': 'GOOGLE_OAUTH_CLIENT_SECRET',
               'auth': 'https://accounts.google.com/o/oauth2/v2/auth', 'token': 'https://oauth2.googleapis.com/token',
               'extra': {'scope': 'https://www.googleapis.com/auth/drive.file', 'access_type': 'offline', 'prompt': 'consent'}},
    'dropbox': {'label': 'Dropbox', 'free': '2 GB free', 'id': 'DROPBOX_APP_KEY', 'secret': 'DROPBOX_APP_SECRET',
                'auth': 'https://www.dropbox.com/oauth2/authorize', 'token': 'https://api.dropboxapi.com/oauth2/token',
                'extra': {'token_access_type': 'offline'}},
}
STATE_TTL = 600
_STATES: dict = {}   # one-time sign-in states: state → (cat id, provider, expires)


def configured(env=None):
    env = os.environ if env is None else env
    return [k for k, p in PROVIDERS.items() if str(env.get(p['id']) or '').strip() and str(env.get(p['secret']) or '').strip()]


def start(cat_id, provider, redirect_uri, env=None, now=None):
    """The provider's sign-in URL for this agent (a one-time state, 10 min). Raises ValueError when FEELESS has no app keys for it."""
    env = os.environ if env is None else env
    if provider not in configured(env):
        raise ValueError(f"{PROVIDERS.get(provider, {}).get('label', 'That cloud')} is not set up on FEELESS yet.")
    now = now or time.time()
    for k in [k for k, v in _STATES.items() if v[2] < now]:
        _STATES.pop(k, None)
    state = secrets.token_urlsafe(24)
    _STATES[state] = (cat_id, provider, now + STATE_TTL)
    p = PROVIDERS[provider]
    return p['auth'] + '?' + urlencode({'client_id': env[p['id']], 'redirect_uri': redirect_uri, 'response_type': 'code', 'state': state, **p['extra']})


def take_state(state, now=None):
    """(cat id, provider) for a live state — once."""
    row = _STATES.pop(str(state or ''), None)
    return (row[0], row[1]) if row and row[2] >= (now or time.time()) else None


async def exchange(http, provider, code, redirect_uri, env=None):
    """The sign-in code → its refresh pass (the only thing FEELESS keeps)."""
    env = os.environ if env is None else env
    p = PROVIDERS[provider]
    r = await http.post(p['token'], data={'code': code, 'grant_type': 'authorization_code', 'redirect_uri': redirect_uri,
                                          'client_id': env[p['id']], 'client_secret': env[p['secret']]}, timeout=15)
    j = r.json()
    if r.status_code != 200 or not j.get('refresh_token'):
        raise ValueError(str(j.get('error_description') or j.get('error') or 'The cloud sign-in did not finish.')[:120])
    return j['refresh_token']


async def access(http, provider, refresh, env=None):
    env = os.environ if env is None else env
    p = PROVIDERS[provider]
    r = await http.post(p['token'], data={'refresh_token': refresh, 'grant_type': 'refresh_token', 'client_id': env[p['id']], 'client_secret': env[p['secret']]}, timeout=15)
    j = r.json()
    if r.status_code != 200 or not j.get('access_token'):
        raise ValueError('The cloud sign-in expired — connect it again.')
    return j['access_token']


async def _drive_folder(http, tok, name):
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    r = await http.get('https://www.googleapis.com/drive/v3/files', params={'q': q, 'fields': 'files(id)'}, headers={'Authorization': f'Bearer {tok}'}, timeout=15)
    got = (r.json().get('files') or [])
    if got:
        return got[0]['id']
    r = await http.post('https://www.googleapis.com/drive/v3/files', json={'name': name, 'mimeType': 'application/vnd.google-apps.folder'}, headers={'Authorization': f'Bearer {tok}'}, timeout=15)
    return r.json()['id']


def folder_name(cat):
    return 'FEELESS ' + ''.join(ch for ch in str(cat.get('name') or 'agent') if ch.isalnum() or ch in ' -_')[:40].strip()


async def upload(http, provider, tok, cat, name, raw, mime):
    """One file into the owner's FEELESS folder → {'id', 'name'}."""
    if provider == 'gdrive':
        folder = await _drive_folder(http, tok, folder_name(cat))
        meta = json.dumps({'name': name, 'parents': [folder]})
        boundary = 'feeless' + secrets.token_hex(8)
        body = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n').encode() + raw + f'\r\n--{boundary}--'.encode()
        r = await http.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name', content=body,
                            headers={'Authorization': f'Bearer {tok}', 'Content-Type': f'multipart/related; boundary={boundary}'}, timeout=60)
        j = r.json()
        return {'id': j['id'], 'name': j.get('name', name)}
    r = await http.post('https://content.dropboxapi.com/2/files/upload', content=raw, timeout=60, headers={
        'Authorization': f'Bearer {tok}', 'Content-Type': 'application/octet-stream',
        'Dropbox-API-Arg': json.dumps({'path': f'/{folder_name(cat)}/{name}', 'mode': 'add', 'autorename': True})})
    j = r.json()
    return {'id': j['id'], 'name': j.get('name', name)}


async def overview(http, provider, tok, cat, n=5):
    """Space used / total + its newest files in the FEELESS folder → {'used', 'total', 'recent': [{id, name, mime, size, at, link}]}."""
    h = {'Authorization': f'Bearer {tok}'}
    if provider == 'gdrive':
        a = (await http.get('https://www.googleapis.com/drive/v3/about', params={'fields': 'storageQuota'}, headers=h, timeout=15)).json().get('storageQuota') or {}
        folder = await _drive_folder(http, tok, folder_name(cat))
        fs = (await http.get('https://www.googleapis.com/drive/v3/files', headers=h, timeout=15, params={
            'q': f"'{folder}' in parents and trashed = false", 'orderBy': 'createdTime desc', 'pageSize': n,
            'fields': 'files(id,name,mimeType,size,createdTime,webViewLink,thumbnailLink)'})).json().get('files') or []
        return {'used': int(a.get('usage') or 0), 'total': int(a.get('limit') or 0),
                'recent': [{'id': f['id'], 'name': f['name'], 'mime': f.get('mimeType'), 'size': int(f.get('size') or 0), 'at': f.get('createdTime'),
                            'link': f.get('webViewLink'), 'thumb': f.get('thumbnailLink')} for f in fs]}
    a = (await http.post('https://api.dropboxapi.com/2/users/get_space_usage', headers=h, timeout=15)).json()
    fs = (await http.post('https://api.dropboxapi.com/2/files/list_folder', headers={**h, 'Content-Type': 'application/json'}, timeout=15,
                          content=json.dumps({'path': f'/{folder_name(cat)}'}))).json().get('entries') or []
    fs = sorted([f for f in fs if f.get('.tag') == 'file'], key=lambda f: f.get('server_modified') or '', reverse=True)[:n]
    return {'used': int(a.get('used') or 0), 'total': int(((a.get('allocation') or {}).get('allocated')) or 0),
            'recent': [{'id': f['id'], 'name': f['name'], 'mime': None, 'size': int(f.get('size') or 0), 'at': f.get('server_modified'),
                        'link': 'https://www.dropbox.com/home/' + folder_name(cat).replace(' ', '%20'), 'thumb': None} for f in fs]}

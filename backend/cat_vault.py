"""🔐 A general agent's SAVED LOGINS + 🖼 MEDIA DRAWER (owner, 2026-10-30: "content agents create a Proton email and an X account — credentials
saved in a saved-login drawer, inputs auto-blur… and a small auto-cleaned image / video slide drawer for marketing").

Logins: when a task signs up somewhere, the agent asks FEELESS for a strong password (`new_password`); it is sealed at once (Fernet, the same
server-only secret as the API drawer) into the cat's vault, and the agent may type THAT password — and only it — into that site. The page sees
site · username · when; the password itself only on the owner's own reveal (`login_reveal`). CAPTCHAs / phone checks still stop for a human.
Media: links to images / videos the agent produced or picked for a campaign, kept 7 days, then cleaned on their own (max 24).
"""
import base64
import re
import secrets
import string
import time
from pathlib import Path

import cat_keys

LOGIN_MAX = 40
MEDIA_MAX = 24
MEDIA_TTL = 7 * 86400
_ALPHA = string.ascii_letters + string.digits + '!#%*+-_=?'


def new_password(n=20):
    """A strong random password with every character class (secrets, never random)."""
    while True:
        p = ''.join(secrets.choice(_ALPHA) for _ in range(n))
        if any(c.islower() for c in p) and any(c.isupper() for c in p) and any(c.isdigit() for c in p) and any(not c.isalnum() for c in p):
            return p


def site_of(url_or_site):
    s = re.sub(r'^https?://', '', str(url_or_site or '').strip().lower()).split('/')[0].split(':')[0]
    return re.sub(r'^(www|m|login|accounts?|auth)\.(?=[^.]+\.[^.]+)', '', s)[:80]   # www.dropbox.com, login.x.com, x.com → one site


def put_login(cat, site, username, password, env=None, data_dir=None, now=None):
    site = site_of(site)
    if not site or not password:
        raise ValueError('A login needs a site and a password.')
    rows = [r for r in (cat.get('logins') or []) if not (r['site'] == site and r['user'] == str(username or ''))]
    rows.append({'site': site, 'user': str(username or '')[:120], 'sealed': cat_keys.seal(password, cat.get('id'), env), 'at': now or time.time()})
    cat['logins'] = rows[-LOGIN_MAX:]
    return public_logins(cat)


def reveal(cat, site, username, env=None, data_dir=None):
    row = next((r for r in cat.get('logins') or [] if r['site'] == site_of(site) and r['user'] == str(username or '')), None)
    if not row:
        raise ValueError('No saved login for that site.')
    return cat_keys.unseal(row['sealed'], cat.get('id'), env, data_dir)


def saved_for(cat, site, env=None, data_dir=None):
    """🔐 The newest saved login for a site → (username, password), or None. Server-side only: it goes straight into the window's fill."""
    row = next((r for r in reversed(cat.get('logins') or []) if r['site'] == site_of(site)), None)
    return (row['user'], cat_keys.unseal(row['sealed'], cat.get('id'), env, data_dir)) if row else None


def drop_login(cat, site, username):
    cat['logins'] = [r for r in cat.get('logins') or [] if not (r['site'] == site_of(site) and r['user'] == str(username or ''))]
    return public_logins(cat)


def public_logins(cat):
    return [{'site': r['site'], 'user': r['user'], 'at': r.get('at')} for r in cat.get('logins') or []]


def add_media(cat, url, title='', kind='image', now=None):
    u = str(url or '').strip()
    if not re.match(r'^https://[^\s]{6,500}$', u):
        raise ValueError('Media must be an https link.')
    now = now or time.time()
    keep = [m for m in clean_media(cat, now) if m['url'] != u]
    cat['media'] = (keep + [{'url': u, 'title': str(title or '')[:80], 'kind': 'video' if kind == 'video' or re.search(r'\.(mp4|webm|mov)(\?|$)', u) else 'image', 'at': now}])[-MEDIA_MAX:]
    return cat['media']


def clean_media(cat, now=None):
    """🧹 media older than 7 days is dropped (the drawer cleans itself)."""
    now = now or time.time()
    cat['media'] = [m for m in cat.get('media') or [] if now - float(m.get('at') or 0) < MEDIA_TTL]
    return cat['media']


# 🔏 SEALED SECRETS (owner 2026-10-31: "where does a recovery phrase I download go? it should be saved securely in the agent's drawer — or I paste
# it in, and nobody ever sees it"): a note you paste or a file downloaded in a window you used, sealed with this agent's own key (Fernet). The page
# sees label · kind · size · when; the content only on the owner's own open (a fresh wallet signature, like a password reveal).
SECRET_MAX, NOTE_MAX, FILE_MAX = 20, 8000, 5 * 1024 * 1024


def _vault_dir(data_dir, cat_id):
    return Path(data_dir) / 'vault' / re.sub(r'[^A-Za-z0-9_-]', '', str(cat_id or ''))[:64]


def put_secret(cat, label, text=None, data=None, name='', site='', data_dir='.', env=None, now=None):
    """One sealed note (text) or file (data bytes) → the public list. Notes live sealed in the cat; files sealed on disk, one per secret."""
    rows = list(cat.get('secrets') or [])
    if len(rows) >= SECRET_MAX:
        raise ValueError(f'Its sealed drawer holds {SECRET_MAX} items — delete one first.')
    sid = secrets.token_hex(8)
    row = {'id': sid, 'label': str(label or name or 'sealed note').strip()[:80], 'site': site_of(site) if site else '', 'at': now or time.time()}
    if data is None:
        t = str(text or '')
        if not t.strip() or len(t) > NOTE_MAX:
            raise ValueError(f'A sealed note is 1–{NOTE_MAX:,} characters.')
        row.update(kind='note', size=len(t), sealed=cat_keys.seal(t, cat.get('id'), env))
    else:
        if not data or len(data) > FILE_MAX:
            raise ValueError('A sealed file is up to 5 MB.')
        d = _vault_dir(data_dir, cat.get('id'))
        d.mkdir(parents=True, exist_ok=True)
        (d / f'{sid}.seal').write_text(cat_keys.seal(base64.b64encode(data).decode(), cat.get('id'), env))
        row.update(kind='file', size=len(data), name=re.sub(r'[^\w. ()-]', '_', str(name or 'download'))[:100])
    cat['secrets'] = rows + [row]
    return public_secrets(cat)


def open_secret(cat, sid, data_dir='.', env=None):
    """The owner's own open: {kind, label, name, text} for a note, {…, b64} for a file."""
    row = next((r for r in cat.get('secrets') or [] if r.get('id') == sid), None)
    if not row:
        raise ValueError('Nothing sealed under that id.')
    out = {'kind': row['kind'], 'label': row['label'], 'name': row.get('name')}
    if row['kind'] == 'note':
        return {**out, 'text': cat_keys.unseal(row['sealed'], cat.get('id'), env, data_dir)}
    return {**out, 'b64': cat_keys.unseal((_vault_dir(data_dir, cat.get('id')) / f"{sid}.seal").read_text(), cat.get('id'), env, data_dir)}


def drop_secret(cat, sid, data_dir='.'):
    cat['secrets'] = [r for r in cat.get('secrets') or [] if r.get('id') != sid]
    f = _vault_dir(data_dir, cat.get('id')) / f'{re.sub(r"[^0-9a-f]", "", str(sid))}.seal'
    if f.exists():
        f.unlink()
    return public_secrets(cat)


def public_secrets(cat):
    return [{k: r.get(k) for k in ('id', 'label', 'kind', 'size', 'name', 'site', 'at')} for r in cat.get('secrets') or []]

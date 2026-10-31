"""🔐 A general agent's SAVED LOGINS + 🖼 MEDIA DRAWER (owner, 2026-10-30: "content agents create a Proton email and an X account — credentials
saved in a saved-login drawer, inputs auto-blur… and a small auto-cleaned image / video slide drawer for marketing").

Logins: when a task signs up somewhere, the agent asks FEELESS for a strong password (`new_password`); it is sealed at once (Fernet, the same
server-only secret as the API drawer) into the cat's vault, and the agent may type THAT password — and only it — into that site. The page sees
site · username · when; the password itself only on the owner's own reveal (`login_reveal`). CAPTCHAs / phone checks still stop for a human.
Media: links to images / videos the agent produced or picked for a campaign, kept 7 days, then cleaned on their own (max 24).
"""
import re
import secrets
import string
import time

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

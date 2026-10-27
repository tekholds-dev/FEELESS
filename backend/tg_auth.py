"""📲 TELEGRAM MINI APP sign-in (owner 2026-10-27: "family be a telegram game"). Telegram opens FEELESS inside the chat and hands it `initData`
(a query string signed with the bot's token). Verifying it proves WHICH Telegram user is playing — no password, no wallet needed to race.
Telegram's rule (core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app):
  secret = HMAC_SHA256(key="WebAppData", msg=bot_token);  hash == hex(HMAC_SHA256(key=secret, msg=data_check_string))
where data_check_string = every field except `hash`, sorted by key, "k=v" joined by "\n". Pure; the service holds TELEGRAM_BOT_TOKEN.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

MAX_AGE = 24 * 3600


def verify(init_data, bot_token, now=None, max_age=MAX_AGE):
    """→ the Telegram user {id, name, username} when `init_data` is genuine and fresh, else None."""
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(str(init_data), keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    got = pairs.pop('hash', '')
    if not got:
        return None
    dcs = '\n'.join(f'{k}={pairs[k]}' for k in sorted(pairs))
    secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    want = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, got):
        return None
    try:
        if (now or time.time()) - int(pairs.get('auth_date') or 0) > max_age:
            return None
        u = json.loads(pairs.get('user') or '{}')
    except (ValueError, TypeError):
        return None
    if not u.get('id'):
        return None
    name = ' '.join(x for x in (u.get('first_name'), u.get('last_name')) if x).strip() or u.get('username') or f"tg {u['id']}"
    return {'id': int(u['id']), 'name': name[:32], 'username': str(u.get('username') or '')[:32]}


def sign(fields, bot_token):
    """Build a signed initData string (tests + the /dev harness only — real ones come from Telegram)."""
    dcs = '\n'.join(f'{k}={fields[k]}' for k in sorted(fields))
    secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    from urllib.parse import urlencode
    return urlencode({**fields, 'hash': hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()})

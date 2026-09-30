"""Coin launch metadata: the same links, image and banner on every rail (FEELESS / Meteora and pump.fun).

Pure functions. Handles like '@coin' become full links, anything that isn't https is dropped, and the
metadata JSON carries the fields wallets, explorers and DEX screens read (image, external_url, extensions).
"""
import re

_HANDLE = {'twitter': (r'^@?([A-Za-z0-9_]{1,15})$', 'https://x.com/'), 'telegram': (r'^@?([A-Za-z0-9_+]{3,32})$', 'https://t.me/')}


def social_url(kind: str, value: str) -> str:
    v = (value or '').strip()
    if not v:
        return ''
    if v.startswith('https://'):
        return v[:200]
    rule = _HANDLE.get(kind)
    m = rule and re.match(rule[0], v)
    return rule[1] + m.group(1) if m else ''


_UPLOAD = re.compile(r'^(?:https?://[^/]+)?(/api/reputation/uploads/[a-f0-9]{32}\.(?:png|jpg|webp|gif))$')


def upload_path(u: str) -> str:
    """'/api/reputation/uploads/<id>.png' for one of our uploads, even when the browser sent it with its own origin."""
    m = _UPLOAD.match((u or '').strip())
    return m.group(1) if m else ''


def _abs(site: str, u: str) -> str:
    u = (u or '').strip()
    if upload_path(u):
        return (site + upload_path(u))[:300]
    return u[:300] if u.startswith('https://') else ''


def token_metadata(site: str, name: str, symbol: str, description: str = '', image: str = '', banner: str = '',
                   website: str = '', twitter: str = '', telegram: str = '') -> dict:
    img, ban = _abs(site, image), _abs(site, banner)
    links = {'website': social_url('website', website), 'twitter': social_url('twitter', twitter), 'telegram': social_url('telegram', telegram)}
    ext = {k: v for k, v in links.items() if v}
    if ban:
        ext['banner'] = ban
    meta = {'name': name, 'symbol': symbol, 'description': (description or '').strip()[:600], 'image': img,
            'external_url': links['website'], 'extensions': ext,
            'properties': {'files': [{'uri': img, 'type': 'image/webp'}] if img else [], 'category': 'image'}}
    if ban:
        meta['banner'] = meta['header'] = ban
    for k, v in links.items():  # pump.fun-style top-level links, read by most Solana explorers
        if v:
            meta[k] = v
    return meta


def pump_form(name: str, symbol: str, description: str, website: str = '', twitter: str = '', telegram: str = '') -> dict:
    form = {'name': name.strip()[:32], 'symbol': symbol.strip().upper()[:10], 'description': (description or '').strip()[:600], 'showName': 'true'}
    for k, v in (('website', website), ('twitter', twitter), ('telegram', telegram)):
        u = social_url(k, v)
        if u:
            form[k] = u
    return form


TAB_DEFAULT = {'rails': ['feeless', 'pump'], 'devBuy': True, 'maxDevBuySol': 5.0, 'banner': True}


def clean_tab(t: dict) -> dict:
    """Owner's choices for the public Launch tab: which rails show, first buy on/off + cap, banner upload."""
    t = t or {}
    rails = [r for r in (t.get('rails') or []) if r in ('feeless', 'pump')]
    try:
        cap = max(0.0, min(50.0, float(t.get('maxDevBuySol', TAB_DEFAULT['maxDevBuySol']))))
    except (TypeError, ValueError):
        cap = TAB_DEFAULT['maxDevBuySol']
    return {'rails': rails or ['feeless'], 'devBuy': bool(t.get('devBuy', True)), 'maxDevBuySol': cap, 'banner': bool(t.get('banner', True))}


def dev_buy_ok(tab: dict, sol: float) -> bool:
    tab = clean_tab(tab)
    return sol <= 0 or (tab['devBuy'] and sol <= tab['maxDevBuySol'])


# ---- Launch costs (Cmd Ctr › Launch › Costs): what the platform adds on top of the chain's own rent ----------
COSTS_DEFAULT = {'pumpSlippagePct': 1.0, 'pumpPriorityFeeSol': 0.0001, 'feelessPriorityFeeSol': 0.0001}
COSTS_BOUNDS = {'pumpSlippagePct': (0.5, 25.0), 'pumpPriorityFeeSol': (0.0, 0.01), 'feelessPriorityFeeSol': (0.0, 0.01)}


def clean_costs(raw) -> dict:
    """Owner/admin launch-cost settings, clamped so a typo can never make a launch overpay (max 0.01 SOL priority)."""
    out = {}
    for k, d in COSTS_DEFAULT.items():
        try:
            v = float((raw or {}).get(k, d))
        except (TypeError, ValueError):
            v = d
        lo, hi = COSTS_BOUNDS[k]
        out[k] = round(max(lo, min(hi, v)), 6)
    return out

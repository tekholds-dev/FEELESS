"""⏫ SLICE 3 · PROGRESS, NO BACK PEDALS (owner: "a human expects progress and no back pedals"; VISION › PoStatic › Progress).
A new version of a build may never lose a part the last version had working: a section, a working kit (its chart, 3D scene, map, form,
live numbers, wallet button), the owner's studio piece. Code reads the parts from each page; a version that would lose one is sent back
once to keep it, and refused if it still does (the last page stays). Only the owner's own words can take a part out ("remove the map").
Pure: page HTML in, parts out."""
import re

import owner_models as _om
import ps_kits as _pk

REMOVE = re.compile(r'(?i)\b(remove|delete|drop|take (it |them )?(out|off|away)|get rid of|without|no more|lose the|cut the|strip|replace)\b')
_STOP = {'the', 'and', 'for', 'with', 'your', 'our', 'this', 'that', 'how', 'what', 'why', 'you', 'are', 'from', 'all', 'its', 'about'}


def _words(t):
    return [w for w in re.findall(r'[a-z0-9]{3,}', str(t or '').lower()) if w not in _STOP]


def _text(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.I | re.S))).lower()


def parts(html):
    """The parts a page has: its sections (by id or heading), each working kit, the studio pieces it mounts. → [{key, name, kind}]. Pure."""
    h = str(html or ''); out = []
    for m in re.finditer(r'<section\b([^>]*)>(.*?)</section>', h, re.I | re.S):
        sid = re.search(r'\bid\s*=\s*["\']([^"\']+)', m.group(1)); hd = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', m.group(2), re.I | re.S)
        title = ' '.join(re.sub(r'<[^>]+>', ' ', hd.group(1)).split())[:60] if hd else ''
        if sid or title:
            out.append({'key': f"section:{sid.group(1) if sid else title.lower()}", 'name': f'the "{title or sid.group(1)}" section', 'kind': 'section',
                        'id': sid.group(1) if sid else '', 'title': title})
    for kid in _pk.in_page(h):
        out.append({'key': f'kit:{kid}', 'name': f"its {_pk.MENU[kid]['name']} ({_pk._code_did(kid, h)})", 'kind': 'kit', 'id': kid})
    for mid, m in _om.mounted(h).items():
        out.append({'key': f'model:{mid}', 'name': f"the studio piece {m.get('name') or mid}", 'kind': 'model', 'id': mid})
    seen, rows = set(), []
    for p in out:
        if p['key'] not in seen:
            seen.add(p['key']); rows.append(p)
    return rows


def _still(p, h, text):
    """Is this old part still in the new page? A section counts when its id is still there or its heading's words still are."""
    if p['kind'] == 'kit':
        return p['id'] in _pk.in_page(h)
    if p['kind'] == 'model':
        return p['id'] in _om.mounted(h)
    if p.get('id') and re.search(r'\bid\s*=\s*["\']' + re.escape(p['id']) + r'["\']', h):
        return True
    w = _words(p.get('title'))
    return bool(w) and sum(1 for x in w if x in text) >= max(1, (len(w) + 1) // 2)


def _asked_out(p, ask):
    """The owner's own words take this part out: a remove word plus the part's name in the same ask."""
    if not REMOVE.search(str(ask or '')):
        return False
    a = set(_words(ask)); names = set(_words(p.get('title') or p.get('id'))) | set(_words(p.get('name')))
    if p['kind'] == 'kit':
        names |= set(_words(_pk.MENU.get(p['id'], {}).get('name'))) | {p['id']} | ({'chart', 'charts', 'graph'} if p['id'] in ('recharts', 'lwcharts') else set()) | ({'map'} if p['id'] == 'leaflet' else set()) | ({'form'} if p['id'] == 'forms' else set()) | ({'animation', 'animations'} if p['id'] == 'motion' else set())
    return bool(a & names)


def lost(old_html, new_html, ask=''):
    """⏫ The parts the last version had that this one would lose (and the owner did not ask to remove). → [{key, name, kind}]. Pure."""
    if not old_html or not new_html:
        return []
    h = str(new_html); text = _text(h)
    return [p for p in parts(old_html) if not _still(p, h, text) and not _asked_out(p, ask)]


def keep_line(rows):
    """What the minds read when their new version would lose parts: keep each one, working."""
    return ('\nKEEP EVERY PART THAT WORKS. Your new version dropped: ' + '; '.join(p['name'] for p in rows[:8])
            + '. Put each one back, working as it did, and make your change around them. Nothing that worked may be lost.') if rows else ''


def record(old_html, new_html, ask, n_from, refused=None):
    """🧾 The progress row a filed PoStatic carries. → {from, parts, kept, lost, refused}"""
    if not old_html:
        return {'from': None, 'parts': len(parts(new_html)), 'kept': 0, 'lost': [], 'first': True}
    old = parts(old_html); gone = lost(old_html, new_html, ask)
    return {'from': n_from, 'parts': len(parts(new_html)), 'kept': len(old) - len(gone), 'had': len(old), 'lost': [p['name'] for p in gone][:8],
            'asked': [p['name'] for p in old if _asked_out(p, ask) and not _still(p, str(new_html), _text(str(new_html)))][:8],
            **({'refused': refused} if refused else {})}

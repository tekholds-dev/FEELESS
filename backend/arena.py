"""🎯 STRIKE ZONE (owner 2026-10-27: "a cool third-person shooter instead of the raceway — full screen, vs bots or online, real levelling and gun
customisation, pulled from what's already built"). The game runs on three.js's own open-source FPS physics (examples/jsm/math Octree + Capsule)
and its rigged Soldier model; THIS module is the server's truth: the gun + attachment catalog, the level curve and unlocks, loadout checks, match
plausibility and XP. Pure + tested; the service holds the store, the tokens and the online rooms. Points only — XP and a little MP for a family.
"""

GUNS = {   # base stats: damage a hit · rounds a minute · magazine · reload s · range m · spread rad · recoil · move speed ×
    'rifle':   {'name': 'FX-7 RIFLE',    'dmg': 24, 'rpm': 600, 'mag': 30, 'reload': 2.1, 'range': 120, 'spread': 0.012, 'recoil': 0.35, 'speed': 1.00, 'pellets': 1, 'level': 1},
    'smg':     {'name': 'VIPER SMG',     'dmg': 16, 'rpm': 900, 'mag': 32, 'reload': 1.7, 'range': 55,  'spread': 0.024, 'recoil': 0.25, 'speed': 1.08, 'pellets': 1, 'level': 3},
    'shotgun': {'name': 'RUG BREAKER',   'dmg': 13, 'rpm': 80,  'mag': 6,  'reload': 2.6, 'range': 26,  'spread': 0.085, 'recoil': 0.90, 'speed': 0.97, 'pellets': 8, 'level': 6},
    'sniper':  {'name': 'WHALE HUNTER',  'dmg': 95, 'rpm': 45,  'mag': 5,  'reload': 3.0, 'range': 300, 'spread': 0.002, 'recoil': 1.20, 'speed': 0.92, 'pellets': 1, 'level': 10},
}
# slot → [(id, name, level it unlocks at, modifiers: + / − fractions of the base stat; zoom = aim-down-sights ×)]
PARTS = {
    'barrel': [('std', 'STANDARD', 1, {}), ('short', 'SHORT', 2, {'range': -0.25, 'recoil': -0.15, 'speed': 0.03}),
               ('long', 'LONG', 5, {'range': 0.35, 'spread': -0.25, 'speed': -0.03}), ('supp', 'SUPPRESSED', 12, {'range': -0.10, 'recoil': -0.20})],
    'optic':  [('iron', 'IRON SIGHTS', 1, {'zoom': 1.25}), ('dot', 'RED DOT', 2, {'zoom': 1.45, 'spread': -0.10}), ('holo', 'HOLO', 4, {'zoom': 1.7, 'spread': -0.15}),
               ('scope', '4× SCOPE', 8, {'zoom': 3.2, 'spread': -0.30})],
    'mag':    [('std', 'STANDARD', 1, {}), ('ext', 'EXTENDED', 3, {'mag': 0.5, 'reload': 0.15}), ('drum', 'DRUM', 9, {'mag': 1.0, 'reload': 0.35, 'speed': -0.04})],
    'stock':  [('std', 'STANDARD', 1, {}), ('light', 'LIGHT', 4, {'speed': 0.06, 'recoil': 0.15}), ('heavy', 'HEAVY', 7, {'recoil': -0.30, 'speed': -0.04})],
    'skin':   [('green', 'FEELESS GREEN', 1, {}), ('carbon', 'CARBON', 2, {}), ('pink', 'NEON PINK', 6, {}), ('ice', 'ICE', 10, {}), ('gold', 'GOLD', 15, {})],
}
DEFAULT = {'gun': 'rifle', 'barrel': 'std', 'optic': 'iron', 'mag': 'std', 'stock': 'std', 'skin': 'green'}
XP = {'kill': 100, 'head': 50, 'win': 400, 'played': 50}
MAX_LEVEL = 50
KILL_MP, KILL_MP_DAY = 5, 150          # a family member's kills feed the family bank, capped a day


def need(level):
    """XP to go from `level` to the next."""
    return 600 + 250 * (max(1, int(level)) - 1)


def level_of(xp):
    """→ {level, into (XP into this level), need (XP this level takes), total}"""
    xp, lv = max(0, int(xp or 0)), 1
    left = xp
    while lv < MAX_LEVEL and left >= need(lv):
        left -= need(lv); lv += 1
    return {'level': lv, 'into': left, 'need': need(lv), 'total': xp}


def unlocked(level):
    lv = int(level)
    return {'guns': [k for k, g in GUNS.items() if g['level'] <= lv], 'parts': {s: [p[0] for p in ps if p[2] <= lv] for s, ps in PARTS.items()}}


def clean_loadout(raw, level):
    """Whatever the browser sent → a loadout this level owns (anything locked or unknown falls back to the default)."""
    r = raw if isinstance(raw, dict) else {}
    u = unlocked(level); out = dict(DEFAULT)
    if r.get('gun') in u['guns']:
        out['gun'] = r['gun']
    for s in PARTS:
        if r.get(s) in u['parts'][s]:
            out[s] = r[s]
    return out


def stats(loadout):
    """The gun's live stats with its attachments on (the browser shows + fires these)."""
    lo = loadout if isinstance(loadout, dict) else DEFAULT
    g = dict(GUNS.get(lo.get('gun'), GUNS['rifle'])); zoom = 1.25
    for s, ps in PARTS.items():
        part = next((p for p in ps if p[0] == lo.get(s)), ps[0])
        for k, v in part[3].items():
            if k == 'zoom':
                zoom = v
            elif k in g:
                g[k] = g[k] * (1 + v)
    g['mag'] = int(round(g['mag'])); g['zoom'] = zoom
    return g


def check(kills, deaths, heads, secs, mode='bots'):
    """→ None when a match result is plausible, else why not. (Online kills are relayed peer to peer — this caps the obvious lies.)"""
    try:
        kills, deaths, heads, secs = int(kills), int(deaths), int(heads), float(secs)
    except (TypeError, ValueError):
        return 'Bad result.'
    if min(kills, deaths, heads) < 0:
        return 'Bad result.'
    if secs < 20:
        return 'That match was too short to count.'
    if heads > kills:
        return 'More headshots than kills.'
    if kills > secs / 1.5 + 2:
        return 'More kills than the clock allows.'
    if mode not in ('bots', 'online'):
        return 'Unknown mode.'
    return None


def match_xp(kills, heads, won):
    return XP['played'] + XP['kill'] * int(kills) + XP['head'] * int(heads) + (XP['win'] if won else 0)


def board(players, day, n=10):
    """Today's leaders by XP earned today."""
    rows = [{'name': p.get('name') or k[:4] + '…', 'tag': p.get('tag') or '', 'xp': int((p.get('day') or {}).get('xp') or 0), 'kills': int((p.get('day') or {}).get('kills') or 0),
             'level': level_of(p.get('xp'))['level']} for k, p in (players or {}).items() if (p.get('day') or {}).get('date') == day]
    rows = sorted([r for r in rows if r['xp'] > 0], key=lambda r: (-r['xp'], -r['kills']))[:n]
    return [{**r, 'place': i + 1} for i, r in enumerate(rows)]


def level_post(name, tag, level, gun):
    """📲 the Telegram group's post when someone levels up."""
    who = f"[{tag}] {name}" if tag else name
    unlock = [p[1] for ps in PARTS.values() for p in ps if p[2] == level] + [g['name'] for g in GUNS.values() if g['level'] == level]
    return f"🎯 STRIKE ZONE · {who} hit LEVEL {level}" + (f" — unlocked {', '.join(unlock)}" if unlock else '') + f"\nRunning the {GUNS.get(gun, GUNS['rifle'])['name']}. Jump in."

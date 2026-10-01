"""FEELESS cards: every badge and season drop as a collectible card with a front (art) and a back (lore + money).

Pure functions. A card's look (title, glyph, lore, design, colours, art, rarity) lives in one edits store keyed by
card key; its money comes from the payout records: every pool / reserve payout stores what ONE holder of each
badge / tier key received (`perKey`), so "earned so far per card" is a plain sum.

Card keys:  badge:<id>   season:<seasonId>   week:<seasonId>:w<n>
"""
import re

DESIGNS = ('holo', 'circuit', 'obsidian', 'aurora', 'glitch', 'ember')
RARITIES = ('common', 'rare', 'epic', 'legendary', 'mythic')
MOTIONS = ('still', 'alive')
# Live effects OUTSIDE the card (frontend styles/auras.css, MetaCard CARD_AURAS). '' = none.
AURAS = ('fire', 'static', 'lightning', 'frost', 'smoke', 'plasma', 'sparkle', 'halo', 'matrix', 'void', 'gold', 'neon', 'shockwave', 'toxic', 'aurora')   # alive = idle float + foil sweep + crest glow (dies under fx-lite / reduced motion)
TONE_RARITY = {'plain': 'common', 'mint': 'rare', 'gold': 'epic', 'bad': 'common'}
TIER_RARITY = {1: 'common', 2: 'rare', 3: 'epic', 4: 'legendary'}
_HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


def default_badge_card(b: dict) -> dict:
    rarity = TIER_RARITY.get(b.get('tier')) or TONE_RARITY.get(b.get('tone'), 'rare')
    design = {'common': 'circuit', 'rare': 'aurora', 'epic': 'holo', 'legendary': 'obsidian'}.get(rarity, 'holo')
    return {'key': f"badge:{b['id']}", 'kind': 'badge', 'title': b.get('label') or b['id'], 'subtitle': 'FEELESS badge',
            'glyph': b.get('icon') or '⭐', 'lore': b.get('why') or b.get('how') or '', 'how': b.get('how') or b.get('why') or '',
            'design': 'ember' if b.get('tone') == 'bad' else design, 'accent': '#16d67f', 'accent2': '#f5c451', 'art': '', 'rarity': rarity, 'motion': 'still'}


def default_season_card(s: dict) -> dict:
    return {'key': f"season:{s['id']}", 'kind': 'season', 'title': s.get('name') or s['id'], 'subtitle': f"Season {str(s['id']).lstrip('s')} card",
            'glyph': '🏅', 'lore': s.get('theme') or '', 'how': 'Finish the season at Bronze tier or higher.',
            'design': 'obsidian', 'accent': s.get('accent') or '#16d67f', 'accent2': s.get('accent2') or '#f5c451', 'art': s.get('badgeUrl') or '', 'rarity': 'legendary', 'motion': 'alive'}


def default_week_card(s: dict, w: dict) -> dict:
    return {'key': f"week:{s['id']}:w{w['week']}", 'kind': 'weekly', 'title': w.get('name') or f"Week {w['week']}", 'subtitle': f"{s.get('name') or s['id']} · week {w['week']}",
            'glyph': w.get('glyph') or '✦', 'lore': w.get('story') or '', 'how': 'Score 50+ points that week (top 3 = legendary).',
            'design': 'glitch' if w['week'] % 2 else 'circuit', 'accent': s.get('accent') or '#16d67f', 'accent2': s.get('accent2') or '#ff5ad1', 'art': w.get('imageUrl') or '', 'rarity': 'epic', 'motion': 'still'}


def clean_edit(p: dict) -> dict:
    """Owner edits: only known fields, bounded, safe values (colours are #rrggbb, art is https or our upload)."""
    out = {}
    for k, n in (('title', 40), ('subtitle', 60), ('glyph', 8), ('lore', 600)):
        if isinstance(p.get(k), str):
            out[k] = p[k].strip()[:n]
    if p.get('design') in DESIGNS:
        out['design'] = p['design']
    if p.get('rarity') in RARITIES:
        out['rarity'] = p['rarity']
    if p.get('motion') in MOTIONS:
        out['motion'] = p['motion']
    if p.get('aura') == '' or p.get('aura') in AURAS:
        out['aura'] = p['aura']
    for k in ('accent', 'accent2'):
        if isinstance(p.get(k), str) and _HEX.match(p[k]):
            out[k] = p[k].lower()
    art = p.get('art')
    if isinstance(art, str) and (art == '' or art.startswith('https://') or re.match(r'^/api/reputation/uploads/[a-f0-9]{32}\.(png|jpg|webp|gif)$', art)):
        out['art'] = art[:300]
    if 'title' in out and len(out['title']) < 2:
        out.pop('title')
    return out


def merge(defaults: dict, edits: dict) -> dict:
    return {**defaults, **{k: v for k, v in (edits or {}).items() if k in defaults}, 'edited': bool(edits)}


def key_counts(tiers: dict, badges: dict) -> dict:
    """How many wallets hold each pool key ('tier:<T>' / 'badge:<id>')."""
    c = {}
    for t in (tiers or {}).values():
        c[f'tier:{t}'] = c.get(f'tier:{t}', 0) + 1
    for ids in (badges or {}).values():
        for bid in set(ids):
            c[f'badge:{bid}'] = c.get(f'badge:{bid}', 0) + 1
    return c


def per_key_each(mode: str, weights: dict, fixed: dict, counts: dict, pct_pot: float, total_weight: float, fixed_scale: float = 1.0) -> dict:
    """What ONE holder of each key gets from a pool payout (SOL, 6 dp)."""
    out = {}
    for k, v in (weights or {}).items():
        v, n = float(v or 0), counts.get(k, 0)
        if v <= 0 or not n:
            continue
        out[k] = pct_pot * v / 100 / n if mode == 'pct' else (pct_pot * v / total_weight if total_weight else 0)
    for k, v in (fixed or {}).items():
        if counts.get(k) and float(v or 0) > 0:
            out[k] = out.get(k, 0) + float(v) * fixed_scale
    return {k: int(v * 1e6) / 1e6 for k, v in out.items() if v > 0}


def tier_each(rows: list) -> dict:
    """Reserve payouts: average SOL one holder of each tier got ({'tier:Gold': 0.12})."""
    by = {}
    for r in rows or []:
        if r.get('tier'):
            by.setdefault(r['tier'], []).append(float(r.get('sol') or 0))
    return {f'tier:{t}': int(sum(v) / len(v) * 1e6) / 1e6 for t, v in by.items() if v}


def card_money(card_key: str, pools: list, season_payouts: dict, season_pct: dict) -> dict:
    """Back-of-card money for one card: what it earns (per pool) and what one holder has earned so far."""
    earns, earned = [], 0.0
    if card_key.startswith('badge:'):
        for p in pools:
            w = float((p.get('weights') or {}).get(card_key) or 0)
            fx = float((p.get('fixed') or {}).get(card_key) or 0)
            if w > 0 or fx > 0:
                earns.append({'pool': p.get('name') or 'Pool', 'pct': w if p.get('mode') == 'pct' and w else None, 'weight': w if p.get('mode') != 'pct' and w else None, 'fixedSol': fx or None})
            for po in p.get('payouts') or []:
                earned += float((po.get('perKey') or {}).get(card_key) or 0)
    elif card_key.startswith('season:'):
        sid = card_key.split(':', 1)[1]
        if season_pct.get(sid):
            earns.append({'pool': 'Season reserve', 'pct': season_pct[sid], 'tierWeighted': True})
        po = season_payouts.get(sid) or {}
        each = tier_each(po.get('rows'))
        if each:
            earned = max(each.values())
            return {'earns': earns, 'earnedEach': round(earned, 6), 'byTier': each}
        for p in pools:
            if p.get('seasonId') == sid and any(k.startswith('tier:') and float(v or 0) > 0 for k, v in (p.get('weights') or {}).items()):
                earns.append({'pool': p.get('name') or 'Pool', 'tiers': {k[5:]: v for k, v in p['weights'].items() if k.startswith('tier:') and float(v or 0) > 0}})
    return {'earns': earns, 'earnedEach': round(earned, 6)}

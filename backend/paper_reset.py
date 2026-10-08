"""♻ BROKE → RESET WITH A NEW CONFIG (pure): a PAPER tier card that has lost most of what was put in restarts on the full paper size with a NEW config,
and the config it died on is SCRAPPED — never dealt again. The real-money card is never touched, and a tier the owner locked keeps its lock.
New config = the engine's proven strategy that was not tried yet (sim record), else a fresh combination of valid exits + a selection style, always
different from the old one and from every scrapped one. Everything is validated by arena_prime (`clean_exit`, `PICK_STYLES`)."""
import hashlib
import json
import random

import arena_prime as ap

BROKE_PCT = 25.0            # value ≤ 25% of what was put in
MIN_ROUNDS = 5              # …after a real try (a card just dealt is never "broke")
MIN_AGE_SEC = 3600
COOLDOWN_SEC = 6 * 3600     # one reset per tier per 6h
SCRAP_KEEP = 60
EXIT_CHOICES = {'rideAt': (15, 20, 25, 30, 50, 100), 'rideTrail': (8, 10, 15, 20, 30), 'rotateMinDrop': (5, 10, 15, 20), 'rotateConfirm': (2, 3, 4),
                'minHoldMins': (10, 15, 30, 60, 120), 'instantSwapPct': (0, 15, 20), 'tp': (0, 100, 200, 300)}
# one ready-made selection per style (what each tier uses by default)
STYLE_PICK = {'hunt': ap.DEFAULT_TIER_PICK['safe'], 'sniper': ap.DEFAULT_TIER_PICK['balanced'], 'human': ap.DEFAULT_TIER_PICK['next'], 'majors': ap.DEFAULT_TIER_PICK['ever'],
              'engine': ap.DEFAULT_TIER_PICK['degen']}


SIM_EXIT = {'tp': 'tp', 'sl': 'sl', 'minDrop': 'rotateMinDrop', 'rideAt': 'rideAt', 'trail': 'rideTrail', 'confirm': 'rotateConfirm', 'rest': 'minHoldMins'}
SIM_PICK = {'age': 'runnerMinAgeH', 'pool': 'runnerMinLiqK', 'buy': 'runnerMinBuy', 'vol': 'runnerMinVolK', 'mom': 'runnerMinChg1h', 'floor': 'edgeFloor'}


def from_sim(cfg):
    """An engine strategy (pg_sim trait names: tp · sl · minDrop · rideAt · trail · confirm · rest · age · pool · buy · vol · mom · edge · floor) → a candidate
    for fresh_config: exit keys + `pickNum` (selection numbers). Values the engine would not accept are dropped."""
    out, num = {}, {}
    for k, tk in SIM_EXIT.items():
        if k in (cfg or {}):
            v = ap.clean_exit(tk, _f(cfg[k]))
            if v is not None:
                out[tk] = v
    for k, tk in SIM_PICK.items():
        if k in (cfg or {}):
            lo, hi = ap.PICK_NUM_KEYS[tk]
            num[tk] = max(lo, min(hi, _f(cfg[k])))
    if 'edge' in (cfg or {}):
        num['edgeGate'] = str(cfg['edge']) not in ('0', 'False', 'false', '')
    return {**out, 'pickNum': num} if out else {}


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def is_broke(card, value, now, last_reset=0.0):
    """A paper card is broke when it is worth ≤ 25% of what was put in, has played ≥ 5 rounds, is ≥ 1h old and was not reset in the last 6h."""
    if not card or card.get('real'):
        return False
    base = _f(card.get('putInUsd')) or _f(card.get('startUsd'))
    return (base > 0 and _f(value) <= base * BROKE_PCT / 100.0 and int(_f(card.get('rounds'))) >= MIN_ROUNDS
            and now - _f(card.get('at'), now) >= MIN_AGE_SEC and now - _f(last_reset) >= COOLDOWN_SEC)


def sig(cfg):
    """A stable fingerprint of a whole config (exits + selection style): two configs with the same sig are the same config."""
    keys = list(ap.TIER_KEYS) + ['pickStyle']
    return hashlib.md5(json.dumps({k: (round(_f(cfg.get(k)), 3) if k != 'pickStyle' else cfg.get(k)) for k in keys if k in cfg}, sort_keys=True).encode()).hexdigest()[:10]


def describe(cfg):
    st = ap.PICK_STYLES.get(cfg.get('pickStyle'), cfg.get('pickStyle') or '')
    bits = [st, f"lock +{_f(cfg.get('rideAt')):g}% / trail {_f(cfg.get('rideTrail')):g}%" if _f(cfg.get('rideAt')) else '', f"hold {_f(cfg.get('minHoldMins')):g}m",
            f"patience {int(_f(cfg.get('rotateConfirm')))}", f"swap losers ≤ −{_f(cfg.get('rotateMinDrop')):g}%" if _f(cfg.get('rotateMinDrop')) else '',
            f"instant −{_f(cfg.get('instantSwapPct')):g}%" if _f(cfg.get('instantSwapPct')) else '', f"TP +{_f(cfg.get('tp')):g}%" if _f(cfg.get('tp')) else '']
    return ' · '.join(b for b in bits if b)


def current(cfg, tpl):
    """The whole config a tier plays now: its exits + its selection style (what is scrapped when it dies)."""
    t = ap.tier_cfg(cfg, tpl)
    return {**{k: t.get(k) for k in ap.TIER_KEYS if t.get(k) is not None}, 'pickStyle': t.get('pickStyle') or 'engine'}


def fresh_config(old, scrapped, other_styles=(), proven=(), rnd=None):
    """→ {'exits': {TIER_KEYS…}, 'pick': {pickStyle…}, 'source': 'proven'|'fresh'} — different from `old` and from every scrapped sig.
    `proven` = candidate dicts (engine strategies: exit keys, optional pickStyle) tried first; `other_styles` = styles other paper cards use now."""
    rnd = rnd or random.Random()
    taboo = {sig(old)} | {x.get('sig') or sig(x.get('cfg') or {}) for x in scrapped or []}
    styles = [s for s in ap.PICK_STYLES if s != old.get('pickStyle')] or list(ap.PICK_STYLES)
    free = [s for s in styles if s not in set(other_styles)] or styles          # a style no other paper card plays comes first
    def pack(exits, style, source, extra=None):
        extra = extra or {}
        ex = {k: ap.clean_exit(k, v) for k, v in exits.items() if k in ap.TIER_KEYS}
        ex = {k: v for k, v in ex.items() if v is not None}
        full = {**ex, 'pickStyle': style}
        return {'exits': ex, 'pick': {**(STYLE_PICK.get(style) or {'pickStyle': style}), **extra, 'pickStyle': style}, 'source': source, 'cfg': full}
    for cand in proven or []:
        exits = {k: cand.get(k) for k in ap.TIER_KEYS if cand.get(k) is not None}
        style = cand.get('pickStyle') if cand.get('pickStyle') in ap.PICK_STYLES else rnd.choice(free)
        if exits and sig({**exits, 'pickStyle': style}) not in taboo:
            return pack(exits, style, 'proven', cand.get('pickNum'))
    for _ in range(400):
        exits = {k: rnd.choice(v) for k, v in EXIT_CHOICES.items()}
        style = rnd.choice(free)
        if sig({**exits, 'pickStyle': style}) not in taboo:
            return pack(exits, style, 'fresh')
    exits = {k: rnd.choice(v) for k, v in EXIT_CHOICES.items()}                  # every combination scrapped (practically impossible): still change something
    return pack(exits, rnd.choice(list(ap.PICK_STYLES)), 'fresh')


def scrap_row(tpl, card, cfg_old, value, now, why='broke'):
    """The record of a scrapped config: what it was, what it did, when."""
    return {'tpl': tpl, 'at': now, 'label': card.get('label'), 'cfg': cfg_old, 'sig': sig(cfg_old), 'text': describe(cfg_old), 'valueUsd': round(_f(value), 2),
            'putInUsd': round(_f(card.get('putInUsd')) or _f(card.get('startUsd')), 2), 'rounds': int(_f(card.get('rounds'))), 'why': why}


def apply(pr, tpl, new):
    """Write the new config into prime.cfg (tierCfg + tierPick) — mutates and returns pr."""
    cfg = pr.setdefault('cfg', {})
    cfg.setdefault('tierCfg', {})[tpl] = dict(new['exits'])
    cfg.setdefault('tierPick', {})[tpl] = dict(new['pick'])
    return pr

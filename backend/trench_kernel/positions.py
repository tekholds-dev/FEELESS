"""🎮 HELD SEATS — the kernel's position manager (replaces the old four-desk `manage`, 2026-10-12). Pure + tested.

Reaper (office.reap / office.fast_reap) owns every EXIT rule: stops, the catastrophic stop, pool / rug / dump exits, thesis invalidation,
trails, time windows. This module decides the three things that are not an exit rule:
  1. the creator's / the learned TAKE LINE — banked at a line someone chose, READ at the base line (it runs while its live read is healthy);
  2. whether a coin whose live read BROKE gives its seat to a READY challenger (never a green coin, never an accelerating one, never in
     its first minutes, never without a challenger the kernel ranks clearly higher);
  3. whether a coin that is simply not winning after a long hold yields to a much stronger READY challenger.
Everything is read from the kernel: the sensed row of THIS pass (`broken_read`), the kernel's rank for the held coin and for each
challenger, and `KERNEL.ready()` as the only source of challengers. No lean, no Trigger bar, no Devil agreement, no case files, no duty
clock. → [{pair, symbol, action: hold | pull | swap, why, to}] — the same decision shape Reaper's requests are merged into.
"""
import opportunity as _opp

from .universe import CONTROL_HOLD_MIN, is_agent

ROTATE_MIN = 30.0     # a coin that is not winning may yield its seat to a much stronger READY coin only after this long
MARGIN = {'agents': 1.25, 'normal': 1.25, 'conservative': 1.4, 'aggressive': 1.15}   # how much higher the kernel must rank the challenger (× the held coin's rank)
ROTATE_EXTRA = 0.25   # … and a coin whose read is intact needs this much more on top
BROKE_D5, BROKE_BUY = -3.0, 50.0


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def broken_read(row):
    """Is this coin's LIVE read broken? → why, or None. From this pass's measurements only: the live narrative collapsing / distributing
    (opportunity.narrative — price, volume pace, buyers, pool change, chart phase, early wallets), −3% or worse in 5 minutes on Tally's
    tape, or buyers under 50%. A coin the senses did not read this pass has no read to break (the caller handles "off the radar")."""
    if not row:
        return None
    n = row.get('nums') or {}
    nar, why = _opp.narrative(row)
    if nar in _opp.SKIP_NARRATIVES:
        return f'{nar.lower()} — {why}'
    if n.get('d5') is not None and _f(n['d5']) <= BROKE_D5:
        return f"{_f(n['d5']):+.1f}% in 5 min"
    if n.get('buy') is not None and _f(n['buy']) < BROKE_BUY:
        return f"buyers down to {_f(n['buy']):.0f}%"
    return None


def margin_need(mode):
    return MARGIN.get(mode or 'agents', MARGIN['agents'])


def outranks(ch_rank, own_rank, mode, extra=0.0):
    """Does the kernel rank the challenger clearly above the held coin? An unranked held coin (off the board) is outranked by any READY one."""
    if ch_rank is None:
        return False
    if own_rank is None or _f(own_rank) <= 0:
        return True
    return _f(ch_rank) >= _f(own_rank) * (margin_need(mode) + extra)


def manage(legs, table, prices, cfg, scalp=None, control=False, now=0.0, moves_left=None, challengers=None, pol=None, radar=None, reviews=None, live=True, ranks=None, vels=None):
    """One decision per held coin the agents manage (every coin in control, else only their own seats).
    `challengers` = the kernel's READY candidates, best rank first ([{mint, symbol, pair, px, …}]) · `ranks` {mint: kernel rank} ·
    `radar` = mints REALLY off the board (missing past the grace while the office is LIVE; None = unknown → a missing row is our gap) ·
    `reviews` {mint: Reaper's thesis verdict} · `vels` {mint: P/L velocity} · `live` False = the office is refilling after a restart: no
    read-based move at all, a coin at a chosen take line is banked on price alone."""
    import office_edge as _oe
    cfg = cfg or {}
    pol = pol or _oe.policy(cfg)
    take = _f(cfg.get('agentTakePct') or 10)
    mode = cfg.get('agentMode') or 'auto'
    scalping = bool(cfg.get('agentScalp', True) and (scalp or {}).get('tp'))   # a take line LEARNED from graded practice paths (evidence, adopted only while proven)
    if scalping:
        take = _f(scalp['tp'])
    creator_tp = bool(pol.get('tp'))
    if creator_tp:
        take, scalping = _f(pol['tp']), False
    bank_at = scalping or creator_tp
    sw = pol['switch']
    sw_on, sw_mode = bool(sw['on']), sw.get('mode')
    broke_min = CONTROL_HOLD_MIN if sw_mode == 'agents' else max(CONTROL_HOLD_MIN, _f(sw.get('holdMin')))
    by = {x['mint']: x for x in table or []}
    on = {l.get('mint') for l in legs or []}
    ch = [c for c in challengers or [] if c.get('mint') not in on]
    if moves_left is not None:
        ch = ch[:max(0, int(moves_left))]
    ranks = ranks or {}
    off = lambda mint: radar is not None and mint in radar
    out = []
    for l in legs or []:
        if (not control and not is_agent(l)) or l.get('placeholder') or l.get('buying') or l.get('frozen') or _f(l.get('units')) <= 0 or _f(l.get('entry')) <= 0:
            continue
        px = _f((prices or {}).get(l.get('pairAddress')))
        if px <= 0:
            continue
        m, sym = l.get('mint'), l.get('symbol')
        base = {'pair': l['pairAddress'], 'symbol': sym}
        pnl = (px / _f(l['entry']) - 1) * 100
        if pol.get('manual'):
            out.append({**base, 'action': 'hold', 'why': f'{pnl:+.1f}% — creator manual: the agents make no discretionary move'}); continue
        x = by.get(m)
        held_min = (now - _f(l.get('at'))) / 60 if now and l.get('at') else 0.0
        broke = broken_read(x) if x else ('off the board' if off(m) else None)
        verdict = (reviews or {}).get(m)
        vst = ((vels or {}).get(m) or {}).get('state')
        best = ch[0] if ch else None
        if pnl < take:
            can = control and best and sw_on and live and not l.get('ride')
            if can and broke and pnl <= 0 and held_min >= broke_min and vst != 'ACCELERATING' and outranks(ranks.get(best['mint']), ranks.get(m), sw_mode):
                out.append({**base, 'action': 'swap', 'to': best, 'why': f"{pnl:+.1f}%, {broke} → its seat goes to ${best['symbol']} (READY, ranked {_f(ranks.get(best['mint'])):g} vs {_f(ranks.get(m)):g})"})
                ch = ch[1:]; continue
            if (can and not broke and pnl <= 0 and held_min >= max(ROTATE_MIN, broke_min) and vst not in ('ACCELERATING', 'STABLE') and x is not None
                    and outranks(ranks.get(best['mint']), ranks.get(m), sw_mode, ROTATE_EXTRA) and not any(d['action'] == 'swap' for d in out)):
                out.append({**base, 'action': 'swap', 'to': best, 'why': f"{pnl:+.1f}% after {held_min:.0f} min and not winning → ${best['symbol']} is READY and ranked {_f(ranks.get(best['mint'])):g} vs {_f(ranks.get(m)):g}"})
                ch = ch[1:]; continue
            out.append({**base, 'action': 'hold', 'why': f'{pnl:+.1f}% — holding until +{take:g}%' + ('' if live else ' (office warming up: no read-based move)')
                        + (f' · read: {broke}, no clearly stronger READY coin' if broke and control else '')}); continue
        if bank_at or not live:   # a line someone CHOSE (yours, or the learned one) is banked AT the line; while warming up: on price alone
            word = '🎛 your take' if creator_tp else '⚡ learned take' if scalping else '⏳ warming up, take'
            if mode in ('auto', 'swap') and best and live:
                out.append({**base, 'action': 'swap', 'to': best, 'why': f"{word} {pnl:+.1f}% ≥ +{take:g}% → banked into ${best['symbol']}"}); ch = ch[1:]
            else:
                out.append({**base, 'action': 'pull', 'why': f"{word} {pnl:+.1f}% ≥ +{take:g}% → banked to card cash"})
            continue
        if x is None and not off(m):   # at the base line but not read this pass: that is OUR gap — nothing is ruled on it
            out.append({**base, 'action': 'hold', 'why': f'{pnl:+.1f}% — not on the board this pass (refilling): nothing is ruled on a gap'}); continue
        bad = broke or (verdict in ('weak', 'invalid') and f'its thesis reads {verdict}')
        if not bad:
            out.append({**base, 'action': 'hold', 'why': f"{pnl:+.1f}% ≥ +{take:g}% and its live read is healthy{', thesis ' + verdict if verdict else ''} — it runs, the trail protects it"}); continue
        if mode in ('auto', 'swap') and best:
            out.append({**base, 'action': 'swap', 'to': best, 'why': f"{pnl:+.1f}%, {bad} → banked into ${best['symbol']}"}); ch = ch[1:]
        else:
            out.append({**base, 'action': 'pull', 'why': f"{pnl:+.1f}%, {bad} → profit to card cash, seat left open"})
    return mine_held(out, legs)


def mine_held(decisions, legs):
    """👤 YOUR SEAT: a coin you picked (leg `picked`) is never swapped or pulled by the agents — their move becomes a SUGGESTION
    (`would`) on a hold, so you see what they would do and the study can grade it. Your own ✂ / ⇄ / stops still act."""
    picked = {l.get('pairAddress') for l in legs or [] if l.get('picked')}
    out = []
    for d in decisions or []:
        if d.get('pair') in picked and d.get('action') in ('swap', 'pull'):
            to_ = (d.get('to') or {}).get('symbol')
            out.append({'pair': d['pair'], 'symbol': d.get('symbol'), 'action': 'hold', 'mine': True,
                        'would': {'action': d['action'], 'to': to_, 'why': d.get('why')},
                        'why': f"👤 your seat — the agents would {'swap it for $' + to_ if d['action'] == 'swap' and to_ else 'bank it'}: {d.get('why')}"})
        else:
            out.append({**d, 'mine': True} if d.get('pair') in picked else d)
    return out


def switch_view(leg, pnl, held_min, best, ranks, pol, verdict=None, vel=None):
    """The switching evaluation the page shows for one held coin against the best READY challenger — the SAME lines `manage` decides on
    (display only). → {switch, why, edge, need, mode, lines, current, challenger}"""
    sw = (pol or {}).get('switch') or {}
    mode = sw.get('mode')
    own, ch = (ranks or {}).get((leg or {}).get('mint')), (ranks or {}).get((best or {}).get('mint'))
    need = round(_f(own) * (margin_need(mode) - 1), 1) if own else 0.0
    edge = None if ch is None or own is None else round(_f(ch) - _f(own), 1)
    hold_min = CONTROL_HOLD_MIN if mode == 'agents' else max(CONTROL_HOLD_MIN, _f(sw.get('holdMin')))
    lines = [['switching on', bool(sw.get('on')), mode or 'agents'],
             ['a READY challenger', bool(best), 'none this pass' if not best else f"${best.get('symbol')} rank {_f(ch):g}"],
             ['position not frozen / riding', not ((leg or {}).get('frozen') or (leg or {}).get('ride')), 'free'],
             ['position not a winner', not pnl > 0, f'{pnl:+.1f}%'],
             ['held long enough', held_min >= hold_min, f'{held_min:.0f} of {hold_min:.0f} min'],
             ['kernel ranks the challenger clearly higher', bool(best) and outranks(ch, own, mode), '—' if edge is None else f'{edge:+.0f} (needs +{need:.0f})'],
             ['P/L not accelerating', (vel or {}).get('state') != 'ACCELERATING', str((vel or {}).get('state') or 'unknown').lower()]]
    ok = all(l[1] for l in lines)
    return {'switch': ok, 'edge': edge, 'need': need, 'mode': mode, 'lines': lines, 'margin': edge, 'scored': True,
            'why': 'every line holds — the seat may go to the challenger (when its read breaks or it stops winning)' if ok else next(f'{l[0]}: {l[2]}' for l in lines if not l[1]),
            'current': {'symbol': (leg or {}).get('symbol'), 'pnl': round(pnl, 2), 'heldMin': round(held_min, 1), 'thesis': verdict, 'score': own, 'vel': (vel or {}).get('state')},
            'challenger': None if not best else {'symbol': best.get('symbol'), 'cleared': True, 'score': ch, 'structure': ((best.get('chart') or {}).get('state'))}}


TRUST_N = 10   # 🤝 suggestions the creator took and closed before a 2nd seat can be trusted (their typical result must be > 0)


def trusted(real):
    """🤝 Have the suggestions the creator took proven out? (≥ TRUST_N closed, typical result > 0)"""
    sg = (real or {}).get('suggested') or {}
    return int(sg.get('n') or 0) >= TRUST_N and _f(sg.get('med')) > 0


def card_seats(card, decisions=None, prices=None, cfg=None, take=None):
    """🎮 The creator's real card as SEATS, right now: who holds each one (🤖 the agents · 🤝 a coin they suggested and the creator took ·
    👤 the creator's own pick · ⚙ the engine · ▫ open), its live result since entry, and — for an agent seat — what they are doing with
    it (hold / pull / swap) and how far it is to their take line (`take` = the ACTIVE line, office.take_line; else the base setting).
    Display only: nothing here buys or sells."""
    c = cfg or {}
    by = {x.get('pair'): x for x in decisions or []}
    take = _f(take) if take else _f(c.get('agentTakePct') or 10)
    seats = []
    for l in (card or {}).get('legs') or []:
        tag = str((l.get('bought') or {}).get('tag') or '')
        kind = 'open' if l.get('placeholder') else 'agent' if tag.startswith('🤖') else 'suggested' if tag.startswith('🤝') else 'yours' if l.get('picked') else 'engine'
        px, en = _f((prices or {}).get(l.get('pairAddress'))), _f(l.get('entry'))
        d = by.get(l.get('pairAddress')) or {}
        seats.append({'symbol': l.get('symbol'), 'pair': l.get('pairAddress'), 'mint': l.get('mint'), 'kind': kind, 'tag': tag, 'buying': bool(l.get('buying')),
                      'pct': round((px / en - 1) * 100, 1) if px > 0 and en > 0 and kind != 'open' else None,
                      'state': 'ride' if l.get('riding') else 'frozen' if l.get('frozen') else '', **({'take': take, 'action': d.get('action') or 'hold', 'why': d.get('why') or '', 'toSym': d.get('toSym')} if kind == 'agent' else {}),
                      **({'would': d.get('would'), 'why': d.get('why') or ''} if kind in ('yours', 'suggested') and d else {})})   # 👤 your seat: what the agents WOULD do (they never do it)
    for _ in range(max(0, min(6, int(_f(c.get('coins')))) - len(seats))):
        seats.append({'kind': 'open', 'symbol': None, 'pct': None})
    return {'tpl': (card or {}).get('tpl'), 'seats': seats, 'dutyAt': _f((card or {}).get('agentDutyAt'))}

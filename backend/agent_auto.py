"""🤖 AGENT-AUTO (owner 2026-11-13, the answer to old Q2): an agent makes its OWN moves only after the owner says go, through a config the owner
set in three answers and confirmed. Pure and tested; the service holds the store, the clock, the seal and the firing.

  `auto pob` (pow · pop · poc · pos · poeco)  → three questions, one at a time:
        1 · how much per proof     ($ of model credit; for a PoW it is the most one buy may be — every real buy still waits for the wallet)
        2 · how often              (every 30m / 2h / 1d …)
        3 · the total budget + stop ($ total, and/or a number of proofs, and/or a time: "$5, 10 proofs, 24h")
     → a summary → `confirm` → it runs. Nothing runs before confirm.
  `stop auto` / `kill` / `auto off`  → the kill-switch: every auto run on that agent stops at once (its config is kept, switched off).
  `auto status`                       → what is set, what it spent, what is left.

The safe pattern copied from delegated-signing wallets (session keys / spend policies): a spend cap per action, a total cap, a time bound, a
count bound, one kill-switch, and the owner's signature still required for anything that moves real money. The config is stored sealed
(Fernet, per-agent key — cat_keys.seal) and honoured exactly: the next fire is refused the moment any bound would be crossed.
"""
import re

KINDS = {'pow': 'PoW', 'pop': 'PoP', 'pob': 'PoB', 'poc': 'PoC', 'pos': 'PoStatic', 'poeco': 'PoEco'}
LINES = {'pow': 'file a pow', 'pop': 'file a pop', 'pob': 'file a pob', 'poc': 'file a poc', 'pos': 'file a pos', 'poeco': 'file a poeco'}
MONEY = {'pow'}                                  # kinds whose fire can lead to a real buy (each buy still waits for the wallet's signature)
MIN_EVERY_S, MAX_EVERY_S = 15 * 60, 7 * 86400    # never more often than every 15 min, never less than weekly
MAX_PER_USD, MAX_TOTAL_USD, MAX_RUNS = 100.0, 1000.0, 500
ASK_TTL_S = 1800
QUESTIONS = [
    ('perUsd', 'How much per proof? (e.g. "$0.50" — the most one {code} may spend{money})'),
    ('everyS', 'How often? (e.g. "every 30m", "every 2h", "daily" — at least every 15 minutes)'),
    ('stop', 'Total budget and when to stop? (e.g. "$5 total, 10 proofs, 24h" — any one of them is enough; it stops at the first it reaches)'),
]
_AUTO = re.compile(r'(?i)^\s*/?auto\s+(pow|pop|pob|poc|pos|postatic|poeco)\b\s*(.*)$')
_STOP = re.compile(r'(?i)^\s*(?:/?(?:stop|kill)\s+(?:all\s+)?auto(?:\s+\w+)?|/?auto\s+(?:off|stop)|/?kill(?:\s+switch)?)\s*[.!]*\s*$')
_STATUS = re.compile(r'(?i)^\s*/?auto\s+(?:status|\?)\s*$')
_CONFIRM = re.compile(r'(?i)^\s*(confirm|confirmed|yes,?\s*confirm|go)\s*[.!]*\s*$')
_CANCEL = re.compile(r'(?i)^\s*(no|cancel|stop|never ?mind|nah)\b')
_MONEY = re.compile(r'\$?\s*(\d+(?:\.\d+)?)\s*(?:\$|usd|dollars?)?', re.I)
_DUR = re.compile(r'(\d+(?:\.\d+)?)\s*(m|min|mins|minutes?|h|hr|hrs|hours?|d|days?|w|weeks?)\b', re.I)
_UNIT = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}


def command(text):
    """→ ('auto', kind, rest) · ('stop', None, '') · ('status', None, '') · None."""
    t = str(text or '')
    if _STOP.match(t):
        return ('stop', None, '')
    if _STATUS.match(t):
        return ('status', None, '')
    m = _AUTO.match(t)
    if m:
        k = m.group(1).lower()
        return ('auto', 'pos' if k == 'postatic' else k, m.group(2).strip()[:200])
    return None


def _secs(t):
    t = str(t or '').lower()
    if re.search(r'\b(hourly)\b', t):
        return 3600
    if re.search(r'\b(daily|a day|every day)\b', t):
        return 86400
    if re.search(r'\b(weekly)\b', t):
        return 604800
    m = _DUR.search(t)
    if not m:
        return None
    return float(m.group(1)) * _UNIT[m.group(2)[0].lower()]


def parse_per(text):
    m = _MONEY.search(str(text or ''))
    if not m:
        return None, 'Say an amount, like "$0.50".'
    v = float(m.group(1))
    if not 0 < v <= MAX_PER_USD:
        return None, f'Pick an amount above $0 and at most ${MAX_PER_USD:g} per proof.'
    return round(v, 2), ''


def parse_every(text):
    s = _secs(text)
    if s is None:
        return None, 'Say how often, like "every 30m", "every 2h" or "daily".'
    if not MIN_EVERY_S <= s <= MAX_EVERY_S:
        return None, 'Pick between every 15 minutes and once a week.'
    return int(s), ''


def parse_stop(text):
    """'$5 total, 10 proofs, 24h' → {'totalUsd', 'maxRuns', 'forS'}; at least one bound."""
    t = str(text or '').lower(); out = {'totalUsd': None, 'maxRuns': None, 'forS': None}
    m = re.search(r'\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\$|usd|dollars?)', t)
    if m:
        out['totalUsd'] = round(float(m.group(1) or m.group(2)), 2)
    m = re.search(r'(\d+)\s*(?:proofs?|runs?|times?|x)\b', t)
    if m:
        out['maxRuns'] = int(m.group(1))
    d = re.sub(r'\$\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:\$|usd|dollars?)|\d+\s*(?:proofs?|runs?|times?|x)\b', ' ', t)
    out['forS'] = int(_secs(d)) if _secs(d) else None
    if not any(v is not None for v in out.values()):
        return None, 'Give a total, a count or a time, like "$5 total", "10 proofs" or "24h".'
    if out['totalUsd'] is not None and not 0 < out['totalUsd'] <= MAX_TOTAL_USD:
        return None, f'Pick a total above $0 and at most ${MAX_TOTAL_USD:g}.'
    if out['maxRuns'] is not None and not 0 < out['maxRuns'] <= MAX_RUNS:
        return None, f'Pick between 1 and {MAX_RUNS} proofs.'
    return out, ''


PARSE = {'perUsd': parse_per, 'everyS': parse_every, 'stop': parse_stop}


def question(kind, i):
    key, q = QUESTIONS[i]
    return q.format(code=KINDS[kind], money=' on one buy, and every real buy still waits for your wallet to sign' if kind in MONEY else ' in model calls')


def start(kind, now):
    """`auto <kind>` → the pending setup and its first question."""
    if kind not in KINDS:
        raise ValueError('Pick one of the proofs: pow, pop, pob, poc, pos, poeco.')
    return {'kind': kind, 'step': 0, 'answers': {}, 'at': now}, f'🤖 Auto {KINDS[kind]} setup · 1 of 3. ' + question(kind, 0) + ' Say "cancel" to stop.'


def answer(pending, text, now):
    """One reply to the setup. → (pending or None, config or None, what to say). A config comes back only on `confirm`."""
    if not pending or now - float(pending.get('at') or 0) > ASK_TTL_S:
        return None, None, 'That auto setup timed out. Type `auto <proof>` to start again.'
    t = str(text or '').strip(); kind = pending['kind']
    if _CANCEL.match(t) and not _CONFIRM.match(t):
        return None, None, 'Okay, no auto run set. Nothing will run.'
    step = int(pending.get('step') or 0)
    if step >= len(QUESTIONS):   # the summary is out: only confirm runs it
        if _CONFIRM.match(t):
            a = pending['answers']
            cfg = {'kind': kind, 'on': True, 'perUsd': a['perUsd'], 'everyS': a['everyS'], **a['stop'], 'since': now, 'nextAt': now,
                   'runs': 0, 'spentUsd': 0.0, 'stopped': None, 'line': LINES[kind]}
            return None, cfg, f'✅ Auto {KINDS[kind]} is ON. ' + summary(cfg, now) + ' Say `stop auto` any time to kill it.'
        return pending, None, 'Say `confirm` to start it, or `cancel`.'
    key = QUESTIONS[step][0]
    val, why = PARSE[key](t)
    if val is None:
        return pending, None, why + ' ' + question(kind, step)
    p = {**pending, 'answers': {**pending['answers'], key: val}, 'step': step + 1, 'at': now}
    if p['step'] < len(QUESTIONS):
        return p, None, f'{p["step"] + 1} of 3. ' + question(kind, p['step'])
    a = p['answers']; draft = {'kind': kind, 'perUsd': a['perUsd'], 'everyS': a['everyS'], **a['stop'], 'runs': 0, 'spentUsd': 0.0, 'since': now}
    return p, None, '📋 ' + summary(draft, now) + ' Say `confirm` to start it, or `cancel`.'


def _dur(s):
    s = int(s or 0)
    return f'{s // 86400}d' if s >= 86400 and s % 86400 == 0 else f'{s // 3600}h' if s >= 3600 and s % 3600 == 0 else f'{s // 60}m'


def summary(cfg, now):
    b = []
    if cfg.get('totalUsd') is not None:
        b.append(f"${cfg['totalUsd']:g} total (${cfg.get('spentUsd', 0):.2f} spent)")
    if cfg.get('maxRuns') is not None:
        b.append(f"{cfg['maxRuns']} proofs ({cfg.get('runs', 0)} done)")
    if cfg.get('forS') is not None:
        left = max(0, int(cfg['forS'] - (now - float(cfg['since'] if cfg.get('since') is not None else now))))
        b.append(f"{_dur(cfg['forS'])} ({_dur(left)} left)")
    money = ' Every real buy still waits for your wallet to sign.' if cfg['kind'] in MONEY else ''
    return f"{KINDS[cfg['kind']]} every {_dur(cfg['everyS'])}, at most ${cfg['perUsd']:g} each, stops at {' or '.join(b)}.{money}"


def stop_reason(cfg, now):
    """Why the NEXT fire may not happen (None = it may). Checked before every fire, so a bound is never crossed."""
    if not cfg or not cfg.get('on'):
        return cfg.get('stopped') if cfg else 'not set'
    if cfg.get('forS') is not None and now - float(cfg['since'] if cfg.get('since') is not None else now) >= cfg['forS']:
        return 'time is up'
    if cfg.get('maxRuns') is not None and int(cfg.get('runs') or 0) >= cfg['maxRuns']:
        return f"all {cfg['maxRuns']} proofs done"
    if cfg.get('totalUsd') is not None and float(cfg.get('spentUsd') or 0) + float(cfg['perUsd']) > cfg['totalUsd'] + 1e-9:
        return f"the ${cfg['totalUsd']:g} budget would be crossed"
    return None


def due(cfg, now, busy=False):
    """→ (fire?, why). Never fires while the last one of its kind is still running (the already-ran guard)."""
    why = stop_reason(cfg, now)
    if why:
        return False, why
    if busy:
        return False, 'the last one is still running'
    if now < float(cfg.get('nextAt') or 0):
        return False, 'waiting'
    return True, ''


def fired(cfg, now):
    """Book one fire against the bounds BEFORE it runs (a crash never lets it spend twice)."""
    c = {**cfg, 'runs': int(cfg.get('runs') or 0) + 1, 'spentUsd': round(float(cfg.get('spentUsd') or 0) + float(cfg['perUsd']), 4),
         'nextAt': now + int(cfg['everyS']), 'lastAt': now}
    why = stop_reason(c, now + int(cfg['everyS']))
    return {**c, 'on': False, 'stopped': why} if why else c   # that was the last one it may run: it switches itself off


def kill(cfg, now, why='stopped by the owner'):
    return {**(cfg or {}), 'on': False, 'stopped': why, 'stoppedAt': now} if cfg else None

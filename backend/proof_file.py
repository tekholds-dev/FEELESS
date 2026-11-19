"""🗂 PROOF FILES SHOW EVERYTHING (Slice 14, owner 2026-11-18: "no proof should look like this in git: the snapshots and all logs need to
show, plus the wired info from each"; docs/VISION.md "GitHub folder: proof files show everything").

Pure. `record(...)` builds the `fileRecord` block every proof file in an agent's GitHub folder carries next to its own fields:
  · true      — Slice 0's true record: minds that really ran, sources read, footprint, the VISION checks, the TEST stamp
  · snapshots — each page it read (site, time, which picture) and, when Slice 10 recorded them, the stash's scrape / static / screenshot
                rows as METADATA only (sizes and counts). Sealed text is never copied in.
  · steps     — the step log: each mind call with model, route, time and cost, read from data/mind_calls.jsonl
  · kits, judges (the review + each judge's call), deal (the bid or the trade and its receipt), window (a link back to its proof window)
  · missing   — a plain sentence for every part that was never recorded, so an old file says what it has and what it lacks

`redact()` runs over the whole file last: no key, token, seed or password can show, whatever put it there. Nothing here moves money."""
import json
import re
import time

import proof_record as _pr

WORD = {'powFolders': 'PoW', 'popFolders': 'PoP', 'pobFolders': 'PoB', 'pocFolders': 'PoC', 'psFolders': 'PoStatic', 'poeFolders': 'PoEco'}
KIND = {'powFolders': 'pow', 'popFolders': 'pop', 'pobFolders': 'pob', 'pocFolders': 'poc', 'psFolders': 'pos', 'poeFolders': 'poe'}
WIN = {'pow': 'pow', 'pop': 'pop', 'pob': 'bids', 'poc': 'poc', 'pos': 'postatic', 'poe': 'poe'}   # the desk window each kind opens in
LOG_FROM = 1794283505   # the first row of data/mind_calls.jsonl: a proof filed before it has no step log, and the file says so
STEPS_MAX = 200
CALL_KEYS = ('at', 'mind', 'asked', 'model', 'route', 'tokens', 'usd', 'ms', 'ok', 'local', 'effort', 'voice', 'err')

# 🔒 A key name that holds a secret, and a value that looks like one. `tokens` (a count) is not a secret.
SECRET_KEY = re.compile(r'(api_?key|apikeys?|secret|passw|passphrase|mnemonic|seed_?phrase|recovery_?phrase|private_?key|privkey|cookie|session|bearer|authorization|^auth$|^token$|_token$|token_|access_?token|refresh_?token)', re.I)
SECRET_VAL = re.compile(r'sk-or-[A-Za-z0-9_-]{12,}|sk-ant-[A-Za-z0-9_-]{12,}|sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{16,}|gho_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}'
                        r'|xox[bap]-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{30}|BEGIN [A-Z ]*PRIVATE KEY|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
                        r'|(?:api[_-]?key|token|secret|password)=[^&\s"]{6,}', re.I)
SAFE_KEYS = {'tokens', 'tokensIn', 'tokensOut', 'seedsUsed', 'kitsUsed'}


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _rows(v):
    return v if isinstance(v, list) else []


def redact(obj, depth=0):
    """Every secret out: a key named like one is dropped, a value shaped like one becomes 🔒. Deep, and safe on any shape."""
    if depth > 14:
        return None
    if isinstance(obj, dict):
        return {k: redact(v, depth + 1) for k, v in obj.items() if str(k) in SAFE_KEYS or not SECRET_KEY.search(str(k))}
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in obj]
    if isinstance(obj, str):
        return SECRET_VAL.sub('🔒', obj)
    return obj


def read_calls(path, last=20000):
    """The call log's newest rows. A missing or broken log is an empty one."""
    out = []
    try:
        with open(path) as fh:
            lines = fh.readlines()[-last:]
    except OSError:
        return out
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def index_calls(rows):
    """{ref: [rows]} so every proof finds its own calls in one look."""
    by = {}
    for r in rows or []:
        if isinstance(r, dict) and r.get('ref'):
            by.setdefault(str(r['ref']), []).append(r)
    return by


def _window(f):
    """The time this proof ran in. A PoStatic workspace keeps calls from every version, so its window starts a little before it; a call long before the folder was made is another run's."""
    end = _f(f.get('closedAt') or f.get('soldAt') or f.get('settledAt')) or None
    start = _f(f.get('at'))
    return (start - (1800 if f.get('ws') else 900) if start else 0.0), (end + 300 if end else None)


def _call(r):
    out = {k: r.get(k) for k in CALL_KEYS if r.get(k) is not None}
    if 'ms' in out:
        out['secs'] = round(_f(out.pop('ms')) / 1000, 1)
    if 'usd' in out:
        out['usd'] = round(_f(out['usd']), 6)
    return out


def steps_of(kind, f, by_ref):
    """The step log: every mind call made for this proof, oldest first, and the judges' review calls apart."""
    since, until = _window(f); steps = []; judge = []
    for ref in _pr.refs_of(f) + [f"review:{f.get('id')}"]:
        for r in by_ref.get(ref) or []:
            at = _f(r.get('at'))
            if at < since or (until is not None and at > until and not ref.startswith('review:')):
                continue
            if ref.startswith('review:'):
                judge.append(_call(r))
            elif r.get('kind') in (None, kind):
                steps.append(_call(r))
    key = lambda x: _f(x.get('at'))
    steps.sort(key=key); judge.sort(key=key)
    return steps[:STEPS_MAX], judge[:40]


def _shot(s, private):
    out = {k: s.get(k) for k in ('site', 'at', 'file', 'mind', 'round', 'n') if s.get(k) is not None}
    if not private:
        out.update({k: str(s.get(k))[:200] for k in ('url', 'title') if s.get(k)})
    if isinstance(s.get('found'), list):
        out['found'] = len(s['found'])
    if isinstance(s.get('missing'), list):
        out['missed'] = len(s['missing'])
    return out


PIC = ('.jpg', '.jpeg', '.png', '.webp')


def _form(v, size_key, pic=False):
    """One of the three stash forms as metadata: kept or not, and its size. Never its text."""
    if isinstance(v, dict):
        out = {'kept': True, **{k: v.get(k) for k in (size_key, 'nums') if isinstance(v.get(k), (int, float))}}
        if pic and str(v.get('file') or '').lower().endswith(PIC):
            out['file'] = str(v['file'])[:120]
        return out
    if pic and isinstance(v, str) and v.lower().endswith(PIC):
        return {'kept': True, 'file': v[:120]}
    return {'kept': bool(v)}


def stash_of(f, private):
    """🗄 Slice 10's stash rows for this proof, metadata only: what page, when, which of scrape / static / screenshot were kept, hit or browsed."""
    st = f.get('stash') if isinstance(f.get('stash'), dict) else {}
    rows = _rows(f.get('snaps')) or _rows(st.get('pages'))
    out = []
    for r in rows[:60]:
        if not isinstance(r, dict):
            continue
        one = {'site': str(r.get('host') or r.get('site') or _pr._host(r.get('url')) or '?')[:80], 'at': r.get('at'),
               'category': r.get('category') or r.get('cats'), 'hit': bool(r.get('hit')),
               'scrape': _form(r.get('scrape'), 'chars'), 'static': _form(r.get('static'), 'bytes'), 'shot': _form(r.get('shot'), 'bytes', pic=True)}
        if r.get('url') and not private:
            one['url'] = str(r['url'])[:200]
        out.append(one)
    tally = {k: st.get(k) for k in ('hits', 'browsed', 'savedSecs', 'savedUsd') if st.get(k) is not None}
    return out, tally


def _review(rv):
    if not isinstance(rv, dict):
        return None
    out = {k: rv.get(k) for k in ('score', 'verdict', 'agree', 'why', 'independent', 'recused', 'missing', 'builders', 'at') if rv.get(k) not in (None, [], '')}
    by = rv.get('by') if isinstance(rv.get('by'), dict) else {}
    out['judges'] = [{'judge': k, **({kk: v.get(kk) for kk in ('score', 'verdict', 'why', 'model', 'pass') if v.get(kk) is not None} if isinstance(v, dict) else {'score': v})} for k, v in by.items()]
    h = rv.get('hidden') if isinstance(rv.get('hidden'), dict) else None
    if h:
        out['hidden'] = {k: h.get(k) for k in ('passed', 'total', 'pct') if h.get(k) is not None}
    return out


BID_KEYS = ('ticker', 'title', 'side', 'count', 'price', 'maxPx', 'usd', 'budgetUsd', 'status', 'kalshiStatus', 'filled', 'sentFilled', 'outcome', 'result', 'at', 'confirmedAt', 'settledAt', 'why', 'warn', 'confirmErr')
TRADE_KEYS = ('sym', 'name', 'sol', 'cashSpentSol', 'cashReturnedSol', 'poolSpentSol', 'poolReturnedSol', 'feesSol', 'pnlBasis', 'entry', 'entryUsd', 'exit', 'pnlPct', 'pnlSol', 'netPnlSol', 'roePct', 'boughtAt', 'soldAt', 'settlementVerified', 'real', 'tp', 'sl')


def deal_of(kind, f, bids):
    """💲 The bid or the trade, and its receipt. Order ids and transaction signatures stay off the file (they lead back to the owner); the file says one was kept."""
    if kind == 'pob':
        mine = [b for b in bids or [] if isinstance(b, dict) and b.get('folder') == f.get('id')]
        rows = [{**{k: b.get(k) for k in BID_KEYS if b.get(k) not in (None, '')}, 'legs': [{k: x.get(k) for k in ('ticker', 'title', 'side', 'price') if isinstance(x, dict) and x.get(k) is not None} for x in _rows(b.get('legs'))][:12],
                 'receipt': {'confirmed': bool(b.get('confirmedAt')), 'orderKept': bool(b.get('orderId'))}} for b in mine]
        k = f.get('kalshi') if isinstance(f.get('kalshi'), dict) else None
        picked = not rows and bool(k)
        if picked:
            rows = [{kk: k.get(kk) for kk in BID_KEYS if k.get(kk) not in (None, '')}]
        if rows:
            say = ('The minds\' pick on Kalshi. A TEST never bids: no order was sent.' if f.get('test') else 'The minds\' pick on Kalshi; no order was sent for it.') if picked else ''
            return {'type': 'bid', 'venue': 'Kalshi', 'paper': bool(f.get('paper')) or picked, 'rows': rows, 'say': say}
        return {'type': 'bid', 'paper': True, 'rows': [], 'say': 'Paper only: no bid was sent for this filing.' if f.get('paper') or f.get('test') else ''} if f.get('paper') or f.get('test') else None
    if kind == 'pow':
        t = {k: f.get(k) for k in TRADE_KEYS if f.get(k) is not None}
        if f.get('boughtAt') or f.get('buySig') or f.get('soldAt') and f.get('entry'):
            t['receipt'] = {'buyKept': bool(f.get('buySig')), 'sellKept': bool(f.get('sellSig')), 'settled': bool(f.get('settlementVerified'))}
            return {'type': 'trade', 'venue': 'Solana', 'paper': False, 'rows': [t], 'feesApart': True}
        if f.get('propose') or f.get('proposed') or f.get('test'):
            return {'type': 'trade', 'paper': True, 'rows': [], 'say': 'A proposal: nothing was bought.'}
        return None
    if kind == 'pop':
        calls = [{k: c.get(k) for k in ('market', 'side', 'lev', 'entry', 'exit', 'roePct', 'at', 'closedAt', 'status') if c.get(k) is not None} for c in _rows(f.get('calls')) if isinstance(c, dict) and c.get('market')]
        if calls or f.get('paper') or f.get('noTrade'):
            return {'type': 'perp', 'paper': True, 'rows': calls[:20], 'say': ('No trade: ' + str(f.get('why') or ''))[:300] if f.get('noTrade') and not calls else 'Paper perps: no money moves.'}
        return None
    if kind == 'poc':
        st = f.get('studio') if isinstance(f.get('studio'), dict) else {}
        posts = [{k: p.get(k) for k in ('where', 'via', 'status', 'at', 'approvedAt', 'views', 'reach') if isinstance(p, dict) and p.get(k) is not None} for p in _rows(st.get('posts'))]
        return {'type': 'post', 'paper': not posts, 'rows': posts[:20], 'say': '' if posts else 'Nothing was posted: a post goes out only on the owner\'s approve.'}
    return None


def snapshots_of(kind, f):
    private = kind == 'pob'
    shots = [_shot(s, private) for s in _rows(f.get('shots')) if isinstance(s, dict)][:40]
    stash, tally = stash_of(f, private)
    return {'pages': shots, 'stash': stash, 'stashTally': tally, 'private': private}


def record(key, f, cat_id=None, by_ref=None, bids=None, now=None):
    """The `fileRecord` block of one proof file. Every part says plainly when it was never recorded."""
    kind = KIND.get(key) or key; f = f if isinstance(f, dict) else {}; miss = []
    true_ = {k: f.get(k) for k in ('ran', 'minds', 'mindsCheck', 'read', 'foot', 'test') if f.get(k) not in (None, [], {})}
    checks = f.get('proofChecks') if isinstance(f.get('proofChecks'), list) else f.get('checks') if isinstance(f.get('checks'), list) else None
    if checks:
        true_['checks'] = checks
    if not (true_.get('ran') or checks):
        miss.append('The true record (minds that really ran, VISION checks): this proof was filed before the record began.')
    snaps = snapshots_of(kind, f)
    if not snaps['pages']:
        miss.append('Page snapshots: none were kept for this proof.' if kind not in ('poe',) else 'Page snapshots: PoEco reads live pools, not pages.')
    if not snaps['stash']:
        miss.append('Stash snapshots (scrape, static page, screenshot): none were recorded for this proof.')
    steps, judge_calls = steps_of(kind, f, by_ref or {})
    if not steps:
        at = _f(f.get('at'))
        miss.append('The step log: PoEco makes no model call.' if kind == 'poe' else
                    'The step log: it was filed before the call log began.' if at and at < LOG_FROM else
                    'The step log: no model call was logged for this proof.')
    kits = [str(k)[:60] for k in _rows(f.get('kits')) + _rows(f.get('kitsUsed')) if isinstance(k, str)]
    did = [{'name': k.get('name'), 'did': str(k.get('did') or '')[:200]} for k in _rows(f.get('kitsDid')) if isinstance(k, dict)]
    if not kits and not did:
        miss.append('Kits used: none were recorded.' if kind not in ('poe', 'pow') else 'Kits used: ' + ('PoEco is pure math.' if kind == 'poe' else 'PoW reads its own coin tools.'))
    rv = _review(f.get('review'))
    if not rv:
        miss.append('Judge reviews: this proof was never reviewed.')
    deal = deal_of(kind, f, bids)
    if deal is None:
        miss.append({'pos': 'A bid or trade: PoStatic builds a page, it never bids or trades.', 'poe': 'A bid or trade: PoEco only measures.'}.get(kind, 'A bid or trade: none was recorded.'))
    cost = sum(_f(s.get('usd')) for s in steps)
    out = {'v': 1, 'kind': WORD.get(key, kind), 'id': f.get('id'), 'n': f.get('n'), 'test': bool(f.get('test')),
           'true': true_ or None, 'snapshots': snaps, 'steps': steps, 'stepTotals': {'calls': len(steps), 'usd': round(cost, 6), 'secs': round(sum(_f(s.get('secs')) for s in steps), 1)},
           'kits': list(dict.fromkeys(kits)), 'kitsDid': did, 'judges': {**(rv or {}), 'calls': judge_calls} if rv or judge_calls else None, 'deal': deal,
           'window': {'win': WIN.get(kind), 'id': f.get('id'), 'kind': kind, 'agent': cat_id, 'say': f"Open {WORD.get(key, kind)} #{f['n']} in its proof window" if f.get('n') else f"Open this {WORD.get(key, kind)} in its proof window"},
           'missing': miss, 'at': round(now if now is not None else time.time())}
    return redact(out)


def file_body(key, f, public_folder, **kw):
    """The whole proof file: its public fields plus the full record, redacted last."""
    return redact({**public_folder(f), 'fileRecord': record(key, f, **kw)})

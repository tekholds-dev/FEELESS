"""🧭 THE START WIZARD (Slice 33, owner 2026-11-20 night: "before a PoC, PoEco or PoStatic job starts, instead of the drop of long text, it can
pop out a 3-step window"). One shared piece for the three job doors:

  1 · DIRECTION  the brief, the goal and the minds' pitch; the owner approves it as is or edits it (his words reach the minds verbatim).
  2 · KITS       which kits this job reads (up to 3, or the agent picks), and what it starts from (fresh, or a past filing of its kind).
  3 · RESEARCH   who searches the web for better components first: COMP (free page reads), OSSY or G4 (the owner's local minds write the
                 search, $0, never a fallback model), or the job's own minds search as they always do.

`clean` checks the choices and keeps them on the job; `CTX` carries them into the engine (`kits_for` overrides the kit picks, `line` is the
text every mind of that job reads, `research` runs the pass); `record` is what the filed proof keeps, shown in its true record.
Pure except `research` (which only calls what it is handed)."""
import contextvars
import statistics
import time

KINDS = {'pos': 'PoStatic', 'poc': 'PoC', 'poe': 'PoEco'}
RESEARCH = {
    'minds': ('Its minds search', 'The job\'s own minds read the web as they work. Nothing extra is spent before it starts.'),
    'comp': ('COMP searches', 'COMP reads GitHub and Show HN for better components first. Plain page reads, $0.'),
    'ossy': ('OSSY searches', 'OSSY (your local mind) writes the search, then the pages are read. $0, on its own LM Studio only.'),
    'g4': ('G4 searches', 'G4 (your local mind) writes the search, then the pages are read. $0, on its own LM Studio only.'),
}
LOCAL = {'ossy': 'local/ossy', 'g4': 'local/g4'}
MAX_KITS = 3
TEXT_MAX = 600
REFS_MAX = 6
CTX = contextvars.ContextVar('start_wizard', default=None)   # the wizard of the job running in this task (asyncio copies it per task)


def _s(v, n):
    return ' '.join(str(v or '').split())[:n]


def clean(kind, raw, kit_ids=(), starts=(), now=None):
    """The owner's choices → the wizard kept on the job. Raises ValueError on a choice that is not on offer."""
    if kind not in KINDS:
        raise ValueError('The start wizard is for PoC, PoEco and PoStatic.')
    raw = raw if isinstance(raw, dict) else {}
    d = raw.get('direction') if isinstance(raw.get('direction'), dict) else {}
    if d.get('approved') is not True:
        raise ValueError('Approve the direction first (or edit it, then approve).')
    text = _s(d.get('text'), TEXT_MAX); pitch = _s(d.get('pitch'), TEXT_MAX)
    kits = [str(k) for k in raw.get('kits') or [] if isinstance(k, str)]
    kits = list(dict.fromkeys(kits))
    if len(kits) > MAX_KITS:
        raise ValueError(f'Pick up to {MAX_KITS} kits, or let the agent pick.')
    bad = [k for k in kits if k not in set(kit_ids)]
    if bad:
        raise ValueError(f'Not a kit for {KINDS[kind]}: {", ".join(bad[:3])}.')
    start = str(raw.get('start') or 'fresh')
    if start != 'fresh' and start not in {str(s) for s in starts}:
        raise ValueError('Start fresh, or from one of its past filings.')
    by = str((raw.get('research') or {}).get('by') if isinstance(raw.get('research'), dict) else raw.get('research') or 'minds')
    if by not in RESEARCH:
        raise ValueError('Pick who researches: its minds, COMP, OSSY or G4.')
    return {'kind': kind, 'direction': {'text': text, 'edited': bool(text) and text != pitch, 'approved': True},
            'kits': kits, 'kitMode': 'mine' if kits else 'auto', 'start': start, 'research': {'by': by},
            'at': round(now or time.time())}


def kits_for(kind, picks):
    """The kits a job reads: the wizard's own picks for this job when it set any, else the agent's picks as they are."""
    w = CTX.get()
    if w and w.get('kind') == kind and w.get('kits'):
        return list(w['kits'])[:MAX_KITS]
    return picks


def start_row(rows, start):
    """The past filing a job starts from (a summary only: the new one still needs its own brief, centrepiece and footprint)."""
    if not start or start == 'fresh':
        return None
    return next((f for f in rows or [] if isinstance(f, dict) and str(f.get('id')) == str(start)), None)


def line(w, found=None, base=None):
    """The words every mind of this job reads: the owner's direction, the kits he chose, what it starts from, what the research found."""
    if not w:
        return ''
    out = ['THE OWNER SET THIS JOB UP IN THE START WIZARD (follow it):']
    d = w.get('direction') or {}
    if d.get('text'):
        out.append(f"Direction{' (his own edit)' if d.get('edited') else ' (approved)'}: {d['text']}")
    if w.get('kits'):
        out.append('Kits he picked for this job: ' + ', '.join(w['kits']) + '. Use them.')
    if base:
        out.append(f"Start from what worked in {KINDS.get(w.get('kind'), '')} #{base.get('n')}: {_s(base.get('topic') or base.get('name') or base.get('q'), 160)}"
                   f"{' · kits ' + ', '.join(map(str, (base.get('kits') or [])[:4])) if base.get('kits') else ''}. Keep what worked, make the rest new.")
    r = found or {}
    if r.get('refs'):
        out.append(f"Better components {RESEARCH[r.get('by', 'comp')][0].split()[0]} found before you started (read them, borrow ideas, never copy):")
        out += [f"- {x.get('title')} {x.get('url')} {('· ' + x['why']) if x.get('why') else ''}".rstrip() for x in r['refs'][:REFS_MAX]]
    return '\n'.join(out) + '\n'


async def research(w, text, http, build_refs, ask=None):
    """Step 3, run once before the job's minds start. `text` is the JOB (the listing, the topic, the ask), never the owner's direction:
    the search is about the work; his direction only steers OSSY / G4 when they write it (a TEST searched for his sentence and found notes apps). → {by, ok, why, refs, usd, q}. Never raises: a research mind that is down is said, never
    swapped for another model (OSSY / G4 answer on their own LM Studio only)."""
    by = ((w or {}).get('research') or {}).get('by') or 'minds'
    if by == 'minds':
        return {'by': by, 'ok': True, 'why': 'Its minds searched as they worked.', 'refs': [], 'usd': 0.0, 'q': ''}
    q = _s(text, 200); usd = 0.0
    if by in LOCAL:
        if ask is None:
            return {'by': by, 'ok': False, 'why': f'{by.upper()} is not reachable here, so there was no research pass (no other model stands in).', 'refs': [], 'usd': 0.0, 'q': ''}
        try:
            raw, usd, _own = await ask(LOCAL[by], 'Write ONE web search (4 to 8 words) for open-source components, libraries or examples that would make this job better. Reply with the words only.',
                                         f"The job: {q}" + (f"\nThe owner's direction: {_s(((w or {}).get('direction') or {}).get('text'), 300)}" if ((w or {}).get('direction') or {}).get('text') else ''), 60)
        except Exception as e:   # noqa: BLE001
            return {'by': by, 'ok': False, 'why': f'{by.upper()} did not answer ({type(e).__name__}), so there was no research pass. No other model stands in.', 'refs': [], 'usd': 0.0, 'q': ''}
        q = _s(str(raw or '').strip().strip('"').splitlines()[0] if str(raw or '').strip() else '', 120)
        if not q:
            return {'by': by, 'ok': False, 'why': f'{by.upper()} wrote no search, so there was no research pass.', 'refs': [], 'usd': round(float(usd or 0), 6), 'q': ''}
    try:
        refs = await build_refs(http, q, True)
    except Exception as e:   # noqa: BLE001
        return {'by': by, 'ok': False, 'why': f'The search failed ({type(e).__name__}).', 'refs': [], 'usd': round(float(usd or 0), 6), 'q': q}
    keep = [{'title': _s(r.get('title'), 90), 'url': str(r.get('url') or '')[:300], 'why': _s(r.get('why'), 120), 'source': r.get('source')} for r in refs or [] if r.get('open') and r.get('url')][:REFS_MAX]
    return {'by': by, 'ok': bool(keep), 'why': f'{len(keep)} open component{"s" if len(keep) != 1 else ""} found for “{q}”.' if keep else f'Nothing open came back for “{q}”.',
            'refs': keep, 'usd': round(float(usd or 0), 6), 'q': q}


def record(w, found=None, base=None):
    """What the filed proof keeps (shown in its true record as STARTED WITH)."""
    if not w:
        return None
    r = found or {}
    return {'direction': (w.get('direction') or {}).get('text') or '', 'edited': bool((w.get('direction') or {}).get('edited')),
            'kits': list(w.get('kits') or []), 'kitMode': w.get('kitMode') or 'auto', 'start': w.get('start') or 'fresh',
            'startN': (base or {}).get('n'), 'research': {'by': r.get('by') or (w.get('research') or {}).get('by') or 'minds', 'ok': bool(r.get('ok', True)),
                                                           'why': r.get('why') or '', 'q': r.get('q') or '', 'refs': [x.get('title') for x in r.get('refs') or []][:REFS_MAX],
                                                           'usd': r.get('usd') or 0.0}, 'at': w.get('at')}


def estimate(rows, minds, by='minds'):
    """Step 3's cost line: what a job of this kind has cost this agent (median of its last 8 filed), plus the research pass. → dict"""
    costs = [float(f.get('cost') or 0) for f in (rows or [])[-8:] if isinstance(f, dict) and isinstance(f.get('cost'), (int, float)) and f.get('cost') > 0]
    med = round(statistics.median(costs), 4) if costs else None
    return {'usd': med, 'n': len(costs), 'minds': [str(m).split('/')[-1] for m in minds or []], 'research': {k: 0.0 for k in RESEARCH}, 'by': by}


def options(kind, rows, minds, kits, picks, mode, brief='', goal='', pitch=(), now=None):
    """Everything the popout shows before Go. Pure."""
    starts = [{'id': str(f.get('id')), 'label': f"{KINDS[kind]} #{f.get('n')}", 'sub': _s(f.get('topic') or f.get('name') or f.get('q'), 60),
               'good': f.get('graded') in ('right',) or (isinstance(f.get('graded'), dict) and f['graded'].get('result') == 'paid')}
              for f in reversed(rows or []) if isinstance(f, dict) and f.get('id') and not f.get('live')][:8]
    return {'kind': kind, 'label': KINDS[kind], 'brief': _s(brief, TEXT_MAX), 'goal': _s(goal, 200), 'pitch': [_s(p, 240) for p in pitch if p][:6],
            'kits': [{'id': k.get('id'), 'name': k.get('name') or k.get('id'), 'what': _s(k.get('what'), 90), 'cat': k.get('cat') or ''} for k in kits or [] if k.get('id')][:40],
            'picks': list(picks or [])[:MAX_KITS], 'mode': mode or 'auto', 'starts': starts,
            'research': [{'by': k, 'label': v[0], 'tip': v[1], 'usd': 0.0, 'mind': k.upper() if k in LOCAL else ('COMP' if k == 'comp' else None)} for k, v in RESEARCH.items()],
            'cost': estimate(rows, minds), 'minds': [str(m).split('/')[-1] for m in minds or []], 'max': MAX_KITS, 'at': round(now or time.time())}

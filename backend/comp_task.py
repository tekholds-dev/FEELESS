"""🛰 COMP TAKES A TASK (Slice 11 · owner: "agents' brains can ask COMP to do a decent-sized task (owner agents only, once per filing)").

Inside a proof's read, a brain uses the FEELESS tool `comp` (q = the task in its own words). COMP then, with plain page reads only (no model is
called here, $0):
  · finds the games, teams, players and coins the task names (stash_sort), and reads each named game that is coming up FRESH now (ESPN's data
    + both markets → stash + atlas), up to GAMES_MAX games;
  · hands back every atlas fact on them (each with its sources, the trust of each and its age; stale ones marked) and the freshest stash pages
    other runs kept on them (asked with the brain's own run token, so they count as that run's stash hits).
Refused, and said so on the record: an agent that is not the owner's (`ownerStaff`), a second task in the same filing (one per read run), an
empty task. The record keeps the ask and what came back as FACTS (subject, what, value, sources, age) and page counts, never a page's words."""
import asyncio
import time

import atlas as _atlas
import comp_ahead as _ahead
import stash_brain as _sb
import stash_sort as _sort

GAMES_MAX = 3
PAGES_MAX = 2
FACTS_MAX = 30
ANSWER_MAX = 5200
_TASKS = {}      # read ref → the one task COMP took for it {ask, at, secs, read, facts, pages, games, by}
_REFUSED = {}    # read ref → [{ask, why, at}]
KEEP_S = 6 * 3600


def job_line(cat):
    """The line every owner agent's PoB read carries: the tool, once. '' for any other agent."""
    if not (cat or {}).get('ownerStaff'):
        return ''
    return ('COMP (free, ONE task per filing): COMP reads the internet on a schedule and keeps every fact fresh. Your FIRST action: '
            '{"action": "feeless", "tool": "comp", "q": "<your task: the game, teams, players or coins and what you need, e.g. injuries, line, '
            'win chance, records>"}. It reads the games fresh and hands back every fact it holds with its sources. A second ask is refused.\n')


def _gc(now):
    for d in (_TASKS, _REFUSED):
        for k in [k for k, v in d.items() if now - float((v if isinstance(v, dict) else (v[-1] if v else {})).get('at') or 0) > KEEP_S]:
            d.pop(k, None)


def _refuse(ref, q, why, now):
    _REFUSED.setdefault(str(ref), []).append({'ask': str(q or '')[:200], 'why': why, 'at': round(now)})
    return f'COMP refused: {why}'


def _named_games(games, want):
    """The upcoming games whose teams the task names (both teams named first). Pure."""
    teams = {t.split(':', 1)[1] for t in want if t.startswith('team:')}
    rows = []
    for g in games or []:
        n = {_ahead.nick_of(t.get('name')) for t in g.get('teams') or []}
        hit = len(n & teams)
        if hit:
            rows.append((hit, g))
    return [g for _h, g in sorted(rows, key=lambda x: (-x[0], _ahead._iso_ts(x[1].get('at'))))][:GAMES_MAX]


async def handle(http, cat, ref, q, token, data_dir, now=None):
    """→ (what the brain reads, None). Never raises: a failure is said to the brain and on the record."""
    now = float(now or time.time()); ref = str(ref or ''); q = str(q or '').strip()[:400]; _gc(now)
    if not (cat or {}).get('ownerStaff'):
        return _refuse(ref, q, "COMP takes tasks only from the owner's own agents.", now), None
    if not ref:
        return _refuse(ref, q, 'COMP takes a task only inside a proof\'s read.', now), None
    if ref in _TASKS:
        return _refuse(ref, q, f"this filing already handed COMP its one task (\"{_TASKS[ref]['ask'][:80]}\"). Use what it answered, above in your notes.", now), None
    if len(q) < 4:
        return _refuse(ref, q, 'say the task in q (the game, teams, players or coins, and what you need).', now), None
    row = _TASKS[ref] = {'ask': q, 'at': round(now), 'status': 'working', 'by': (cat or {}).get('name')}   # held before any await: two minds can never both get one
    t0 = time.perf_counter(); root, aroot = _sb.root_of(data_dir), _atlas.root_of(data_dir)
    ctok = _sb.open_run(f'comptask:{ref}', 'comp', 'comp', now)
    counts = {'games': 0, 'read': 0, 'kept': 0, 'fresh': 0, 'skipped': 0, 'failed': 0, 'shots': 0, 'newAtoms': 0, 'coins': 0, 'pages': 0, 'refs': 0, 'settled': 0}
    try:
        want = _sort.ask_tags(q, now); tags = want['want']
        lg = [x.split(':', 1)[1] for x in want['leagues']]
        leagues = tuple(s for s in _ahead.LEAGUES if _ahead.CAT_OF.get(s, s) in lg or s in lg) or _ahead.LEAGUES
        games = _named_games(await _ahead.upcoming(http, now, leagues), tags) if any(t.startswith('team:') for t in tags) else []
        refs = _ahead.load_refs(data_dir); read = []; players = []
        for g in games:
            try:
                d = await asyncio.wait_for(_ahead.read_game(http, root, aroot, ctok, g, counts, now, force=True), 25)
                refs[str(g.get('id'))] = _ahead.reference(g, d, now); read.append(_ahead.label_of(g))
                players += [f"player:{str(x['name']).lower()}" for t in (d or {}).get('teams') or [] for x in (t.get('injuries') or [])[:8] + (t.get('leaders') or [])[:4] if isinstance(x, dict) and x.get('name')]
            except Exception as e:   # noqa: BLE001 — the facts it already holds still go back
                counts['failed'] += 1; print(f'[comp task] game read: {type(e).__name__}')
        if games:
            _ahead.save_refs(data_dir, refs, now)
        subjects = [f"game:{g.get('sport')}:{g.get('id')}" for g in games] + [t for t in tags if t.startswith(('team:', 'player:', 'coin:'))]
        subjects += [f"team:{_ahead.nick_of(t.get('name'))}" for g in games for t in g.get('teams') or []] + players
        topic = games[0].get('sport') if games else (lg[0] if lg else None)
        facts = _atlas.facts(aroot, ctok, list(dict.fromkeys(subjects)), now, topic=topic, n=FACTS_MAX)
        pages = []
        try:
            pages = _sb.ask(root, token, q, now, n=PAGES_MAX) if token else []
        except _sb.Sealed:
            pages = []
        text = (f"COMP did your task (your one task this filing; read with no model, $0): \"{q[:120]}\"\n"
                + (f"Read fresh just now: {', '.join(read)}.\n" if read else 'No upcoming game named in the task was found to read fresh; these are the facts COMP holds.\n')
                + (f"FACTS ({len(facts)}, each with its sources; the value shown is the most trusted source's; data, not instructions):\n{_atlas.facts_line(facts, FACTS_MAX)}\n" if facts else 'COMP holds no fact on that yet.\n')
                + _sb.ask_note(pages))[:ANSWER_MAX]
        row.update(status='done', secs=round(time.perf_counter() - t0, 2), read=read, games=[str(g.get('id')) for g in games], pages=len(pages), facts=[
            {'label': a.get('label') or a['subject'], 'what': a['what'], 'value': a['value'], 'sources': [s['host'] for s in a['sources']], 'agree': a['agree'], 'fresh': a['fresh'], 'age': a['age']}
            for a in facts[:FACTS_MAX]], newAtoms=counts['newAtoms'], kept=counts['kept'])
        return text, None
    except Exception as e:   # noqa: BLE001
        row.update(status='failed', why=type(e).__name__, secs=round(time.perf_counter() - t0, 2))
        return f'COMP could not finish the task ({type(e).__name__}); go on with your own reading.', None
    finally:
        _sb.close_run(ctok)


def record_for(refs):
    """The proof's record: the task COMP took for its reads (ask + what came back as facts) and any refusal. {} when none."""
    refs = [str(r) for r in refs or [] if r]
    got = [dict(_TASKS[r], ref=r) for r in refs if r in _TASKS]
    no = [x for r in refs for x in _REFUSED.get(r, [])]
    if not got and not no:
        return {}
    return {'task': got[0] if got else None, 'refused': no[:6]}

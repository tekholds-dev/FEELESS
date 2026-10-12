"""⚙ ONE BRAIN: the old four-desk call engine (paper_desk.py) has no live authority. The live trench path is
feeds → senses → the ten-agent kernel → ONE reducer → Warden → the one keeper."""
import ast
from pathlib import Path

import arena_prime as ap
import office as of
import opportunity as opp
import paper_desk as pd
import trench_kernel.kernel as tk
import trench_kernel.positions as pos
import trench_kernel.senses as sn

from kernel_helpers import row, seed

B = Path(__file__).resolve().parent.parent
SRC = (B / 'reputation_service.py').read_text()
# what a live module may NOT take from the paper desk: its decisions, its survival engine, its burn / source-reputation lists
DECISIONS = {'desk', 'eligible', 'manage', 'investigate', 'evolve', 'survival', 'reckon', 'second_opinion', 'devil', 'devil_args', 'trigger', 'busted_now', 'lane_cap', 'seat_limit', 'power'}
ALLOWED_BURN = {'reputation_service.py'}   # the practice desk's own burn list is refreshed inside the paper block only
LIVE = ('reputation_service.py', 'office.py', 'office_edge.py', 'seat_ops.py', 'opportunity.py', 'arena_prime.py', 'fuse_wallet.py', 'trench_rounds.py', 'judge_review.py', 'real_memory.py',
        'trench_crew.py', 'market_wake.py', 'launch_intel.py', 'trench_kernel/brain.py', 'trench_kernel/kernel.py', 'trench_kernel/state.py', 'trench_kernel/senses.py', 'trench_kernel/positions.py',
        'trench_kernel/universe.py', 'trench_kernel/lifecycle.py', 'trench_kernel/view.py', 'trench_kernel/enrich.py')


def _paper_attrs(path):
    """Every `<alias>.<name>` a module reads from the paper desk (whatever it is imported as)."""
    tree = ast.parse((B / path).read_text())
    alias = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            alias |= {a.asname or a.name for a in n.names if a.name in ('paper_desk', 'agents')}
        elif isinstance(n, ast.ImportFrom) and n.module in ('paper_desk', 'agents'):
            alias |= {'<from>:' + a.name for a in n.names}
    used = {a[7:] for a in alias if a.startswith('<from>:')}
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias:
            used.add(n.attr)
    return used


def test_no_live_module_calls_a_paper_desk_decision_and_none_imports_the_legacy_name():
    for f in LIVE:
        if not (B / f).exists():
            continue
        src = (B / f).read_text()
        assert 'import agents' not in src and 'from agents' not in src, f
        bad = _paper_attrs(f) & DECISIONS
        assert not bad, (f, bad)
    assert not any(x in _paper_attrs(f) for f in LIVE if (B / f).exists() and f not in ALLOWED_BURN for x in ('burn',))
    for k in ('brain.py', 'kernel.py', 'state.py', 'senses.py', 'positions.py', 'universe.py', 'lifecycle.py', 'view.py'):
        assert 'paper_desk' not in (B / 'trench_kernel' / k).read_text().replace('(paper_desk.py)', ''), k   # the kernel package never imports it


def test_the_sensed_rows_carry_measurements_and_evidence_but_no_verdict():
    rows = [{'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'price': 1.0, 'vol5m': 9000, 'vol1h': 30000, 'buyShare': 64, 'liq': 25_000, 'mcap': 50_000, 'ageH': 0.1, 'chg5m': 5,
             'tv': {'rug': 62, 'call': ['x', 'BOND RUN']}}]
    st, table, ctx = sn.sense({}, rows, 100.0, busted={'BOND RUN': -82.0})
    x = table[0]
    assert not ({'trigger', 'devil', 'go', 'case', 'objs', 'drule', 'why'} & set(x))           # nobody has an opinion yet
    assert {e[0] for e in x['ev']} == {'busted_read', 'rug_meter'} and x['nums']['buy'] == 64 and x['vitals']['mcap'] == 50_000
    st2, paper = pd.calls(st, table, ctx, 100.0)
    assert {'trigger', 'devil', 'go', 'why'} <= set(paper[0]) and paper[0]['ev'] == x['ev']       # the practice desk annotates a COPY …
    assert 'trigger' not in table[0]                                                              # … the sensed row the kernel judged is untouched


def test_the_kernel_decision_does_not_change_with_anything_the_paper_desk_writes():
    base = row('K', ev=[['identity', 'no site']])
    a = tk.Kernel(); a.run([base], 100.0, {})
    for paper in ({'go': True, 'trigger': ['enter', 'x'], 'devil': ['agree', '']},
                  {'go': False, 'trigger': ['skip', 'bar'], 'devil': ['object', 'burned'], 'objs': [['burned', 'x'], ['rug_signs', 'y']], 'drule': 'unscanned', 'case': ['object', 'x'], 'why': {'lean': -9, 'drivers': []}}):
        b = tk.Kernel(); b.run([{**base, **paper}], 100.0, {})
        assert (b.dec['K']['status'], b.dec['K']['rank']) == (a.dec['K']['status'], a.dec['K']['rank'])
        assert [o for o, _s, _w in b.dec['K']['opinions']['devil']['objections']] == ['identity']


def test_every_real_fill_and_switch_reads_the_kernel_and_there_is_one_execution_path():
    tick = SRC[SRC.index('async def _prime_tick_inner('):SRC.index('async def _prime_tick_inner(') + 400_000]
    tick = tick[:tick.index('\nasync def ', 10)] if '\nasync def ' in tick[10:] else tick
    assert '_tk.KERNEL.ready(exclude=blk_)' in tick and '_pos.manage(' in tick and "challengers=ready_" in tick
    for gone in ('_pd.', 'fill_plan(', 'near_ready(', '_opp.rank(', '_tr.entered(', 'live_check(', 'gos_', 'roundEnter'):
        assert gone not in tick, gone
    assert SRC.count('_prime.agent_seat(') == 1 and SRC.count('def _fw_execute(') == 1 and 'class FuseWallet' not in SRC
    assert "'tag': '🤖 agents · ⚡ READY (kernel)'" in SRC and "tag': '🤖 agents READY · switch'" in SRC


def test_the_agent_pass_runs_senses_then_the_kernel_then_the_offline_paper_calls():
    p = SRC[SRC.index('async def _agents_tick('):SRC.index('\nimport office as _of')]
    i_s, i_k, i_p = p.index('_sn.sense('), p.index('_kernel_pass(table, now)'), p.index('_pd.calls(')
    assert i_s < i_k < i_p                                              # the kernel has decided before any practice call exists
    assert "_agents['table'] = table" in p[i_s:i_k] and '_agents.update(paper=paper_' in p     # live code is handed the SENSED rows
    for gone in ('_pd.desk(', '_pd.evolve(', '_pd.reckon(', '_pd.investigate(', "get('cut')", '_scan_wake('):
        assert gone not in p, gone


def test_the_engines_agent_feed_is_the_kernels_ready_list(monkeypatch):
    import reputation_service as rs
    seed(monkeypatch, [row('R'), row('W', d5=0.2, pace=0.5)])
    monkeypatch.setitem(rs._agents, 'table', [{**row('R'), 'go': False}, {**row('W', d5=0.2, pace=0.5), 'go': True}])   # a paper GO means nothing
    monkeypatch.setitem(rs._agents, 'view', {'feed': True})
    r = rs._agents_go_rows()
    assert [x['mint'] for x in r] == ['R'] and r[0]['tag'] == '🤖 agents READY' and ap.agent_leg({'bought': {'tag': r[0]['tag']}})


def test_reapers_read_broke_rule_is_the_kernels_and_ignores_paper_fields():
    leg = {'mint': 'A', 'pairAddress': 'PA', 'symbol': 'A', 'units': 1.0, 'entry': 1.0, 'at': 1, 'bought': {'tag': '🤖 agents READY'}}
    cfg = {'agentTakePct': 50, 'agentControl': True}
    healthy = {**row('A'), 'trigger': ['skip', 'the old bar'], 'why': {'lean': -5, 'drivers': []}}      # paper says SKIP / lean −5: Reaper does not read it
    _p, rep, _g = of.reap([leg], [healthy], {'PA': 1.03}, cfg, {}, 3600.0, None, True)
    assert rep[0]['action'] is None and rep[0]['rule'].startswith(('R10', 'R7', 'R6'))
    falling = row('A', d5=-6.0)
    _p, rep, _g = of.reap([leg], [falling], {'PA': 1.03}, cfg, {}, 3600.0, None, True)
    assert rep[0]['rule'] == 'R8 momentum failed' and rep[0]['action'] == 'pull' and '-6.0% in 5 min' in rep[0]['evidence']
    assert pos.broken_read(healthy) is None and pos.broken_read(row('A', buy=40, d5=-1.5)) == 'buyers down to 40%'
    assert 'collapsing' in pos.broken_read(row('A', d5=-20))


def test_devil_evidence_needs_no_entry_call_no_lean_and_no_burn_list():
    r = {'mint': 'X', 'tv': {'rug': 70, 'call': ['x', 'WASH TRADED']}, 'social': {'warnings': ['its website shows another contract']}}
    ev = sn.evidence(r, {'c1': 400, 'age': 5}, {'objs': [['chart_parabolic', 'vertical']]}, {'crowd': {'swarm': True, 'swarmShare': 0.8}, 'bots': (55, ['3 bundles'])}, {'WASH TRADED': -22.0})
    assert [e[0] for e in ev] == ['busted_read', 'rug_meter', 'ran', 'identity', 'swarm', 'botted', 'chart_parabolic']
    assert sn.evidence(r, {'c1': 400, 'age': 0.5}, None, None, None)[0][0] == 'rug_meter'       # under 1h old: launch-to-now is not "it ran"; no record = no busted claim
    assert sn.busted({'k': {'n': 40, 'medPct': -30}, 'j': {'n': 5, 'medPct': -90}}, {'A': 'k', 'B': 'j'}) == {'A': -30.0} and sn.busted(None, {}) is None
    assert not hasattr(opp, 'burned') and 'burn' not in (B / 'trench_kernel' / 'senses.py').read_text().split('def evidence')[1].split('def sense')[0].replace('a burn list', '')


def test_the_warden_is_one_sizing_and_the_brains_uncertainty_is_a_rule_of_it():
    w = of.warden(1.0, {'open': True, 'kernelSize': 0.72, 'kernelWhy': 'holders unknown, newborn'}, {})
    assert w['allowed'] <= 0.75 and any(r['id'] == 'W0 uncertainty' for r in w['rules']) and not w['veto']   # shrinks (≥ ×0.5), never a no
    assert not any(r['id'].startswith('W7') for r in of.warden(1.0, {'lives': 1}, {})['rules'])           # the old nine-lives rule is gone
    assert "ctx_.update(kernelSize=t_.get('size')" in SRC

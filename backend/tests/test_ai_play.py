import ai_play as p


def test_the_outline_lists_real_functions_and_the_answer_parses_to_one_proposal():
    src = 'def reap(legs, table):\n    """Reaper rules every held coin."""\n    pass\n\nasync def tick(now):\n    pass\n'
    o = p.outline(src, 'backend/office.py')
    assert 'reap(legs, table) — Reaper rules every held coin.' in o and 'tick(now)' in o
    assert 'export function' not in o and 'HomeEngine' in p.outline('export function HomeEngine({ onOpen }) {', 'x.jsx')
    got = p.parse('```json\n{"title": "slower trail", "file": "backend/office.py", "kind": "change", "why": "exits too fast", "risk": "holds a loser longer", "code": "def f():\\n    return 1"}\n```')
    assert got['title'] == 'slower trail' and got['kind'] == 'change' and got['code'].startswith('def f')
    assert p.parse('no json here') is None and p.parse('{"code": "x"}') is None


def test_a_proposal_is_only_marked_approved_or_dropped_once():
    items, it = p.add([], 'make exits wait', {'title': 't', 'file': 'f', 'kind': 'new', 'why': 'w', 'risk': 'r', 'code': 'def x(): pass'}, 'reaper', 'LOCAL AI', now=1)
    items, hit = p.decide(items, it['id'], True, now=2)
    assert hit['status'] == 'approved'
    assert p.decide(items, it['id'], False, now=3)[1] is None    # decided once
    assert 'OUTLINE of backend/office.py' in p.prompt('x', 'reaper', 'reap()')


def test_the_code_lab_sends_only_its_own_prompt_not_the_chat_rules():
    import ai_router as r
    m = r.messages_general('make it', system=p.ASK, only_system=True)
    assert m[0]['content'] == p.ASK and 'Do NOT answer in JSON' not in m[0]['content']   # the chat prompt forbade JSON + said "greet back": Gemma answered "Yo, I'm Vega"


def test_the_preview_diffs_the_real_function_and_marks_new_ones():
    src = 'def keep(x):\n    return 1\n\n\ndef other():\n    pass\n'
    pv = p.preview_diff(src, 'def keep(x):\n    return 2\n\n\ndef brand_new():\n    return 3\n', 'backend/office.py')
    assert pv['changed'] == ['keep'] and pv['new'] == ['brand_new']
    assert '-    return 1' in pv['diff'] and '+    return 2' in pv['diff'] and '+++ NEW brand_new' in pv['diff']
    got = p.parse('{"title": "t", "file": "f", "code": "def a():\\n    pass", "preview": "<div>hi</div>"}')
    assert "default-src 'none'" in got['preview'] and '<div>hi</div>' in got['preview']

import code_health as ch


def _repo(tmp):
    (tmp / 'frontend' / 'src' / 'styles').mkdir(parents=True)
    (tmp / 'frontend' / 'public').mkdir()
    (tmp / 'backend' / 'tests').mkdir(parents=True)
    (tmp / 'scripts').mkdir()
    src = tmp / 'frontend' / 'src'
    (src / 'a.js').write_text("export function used() { return 1; }\nexport const lonely = 2;\nexport function own() { return 1; }\nconst k = own();\n"
                              "export function twin(a) {\n  const b = a + 1;\n  const c = b * 2;\n  return c;\n}\n")
    (src / 'b.jsx').write_text("import { used } from './a';\nconst x = `mca-${used()}`;\nexport function twin2(a) {\n  const b = a + 1;\n  const c = b * 2;\n  return c;\n}\nexport default function B() { return <i className=\"live\">{x}{twin2(1)}</i>; }\n")
    (src / 'styles' / 's.css').write_text('.live{color:red}.mca-fire{x:1}.ghost .live{y:2}')
    back = tmp / 'backend'
    (back / 'm.py').write_text("def alive():\n    return 1\n\n\ndef dead():\n    return 2\n\n\n@app.get('/x')\ndef route():\n    return alive()\n\n\n"
                               "def d1(v):\n    try:\n        return float(v)\n    except Exception:\n        return 0.0\n")
    (back / 'n.py').write_text("def d2(v):\n    try:\n        return float(v)\n    except Exception:\n        return 0.0\n")
    (back / 'tests' / 'test_m.py').write_text('import m\nm.dead()\n')
    return tmp


def test_scan_finds_dead_code_unused_css_dups_and_export_status(tmp_path):
    out = ch.scan(_repo(tmp_path))
    rows = out['rows']
    by = lambda k: {r['name']: r for r in rows if r['kind'] == k}
    assert set(by('dead_def')) >= {'dead', 'd2'} and 'alive' not in by('dead_def') and 'route' not in by('dead_def')   # tests don't count as a use; routes never dead
    exp = by('dead_export')
    assert exp['lonely']['how'] == 'none' and exp['own']['how'] == 'own' and 'used' not in exp
    assert set(by('dead_css')) == {'ghost'}                     # .mca-fire lives through the `mca-${…}` prefix (same rule as cssHygiene.test.js)
    assert any(r['kind'] == 'dup' and r['name'] == 'twin2' for r in rows) and any(r['kind'] == 'dup' and r['name'] in ('d1', 'd2') for r in rows)
    assert all(not r['file'].startswith('/') and r['line'] >= 1 and r['fix'] for r in rows)
    assert out['totals']['pyLines'] > 0 and out['counts']['dead_def'] >= 2


def test_reputation_store_save_is_debounced_outside_tests(monkeypatch):
    import reputation_service as rs
    rs._save_now(rs._empty_store())
    before = rs.STORE_PATH.stat().st_mtime_ns
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    st = rs._empty_store(); st['mints']['solana:X'] = {'creator': 'C'}
    rs._save(st)
    assert rs.STORE_PATH.stat().st_mtime_ns == before and rs._load()['mints']['solana:X']['creator'] == 'C'   # readers see it at once
    rs._store_flush()
    import json
    assert json.loads(rs.STORE_PATH.read_text())['mints']['solana:X']['creator'] == 'C' and not rs._store_dirty['on']

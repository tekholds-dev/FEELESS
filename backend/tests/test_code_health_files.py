"""🗂 code_health.dead_files: a file nothing imports (relative, `@/` alias or lazy import all count) is listed; the queue route only files a build item."""
import code_health as ch


def test_dead_files_follow_relative_alias_and_lazy_imports(tmp_path):
    src = tmp_path / 'frontend' / 'src'; back = tmp_path / 'backend'
    (src / 'lib').mkdir(parents=True); (src / 'components').mkdir(); back.mkdir(); (tmp_path / 'scripts').mkdir()
    (src / 'index.js').write_text("import { a } from '@/lib/aliased';\nimport './lib/side';\n")
    (src / 'lib' / 'aliased.js').write_text('export const a = 1;')
    (src / 'lib' / 'side.js').write_text('window.x = 1;')
    (src / 'components' / 'Lazy.jsx').write_text('export default () => null;')
    (src / 'components' / 'Host.jsx').write_text("const L = React.lazy(() => import('./Lazy'));\nexport default L;")
    (src / 'components' / 'Orphan.jsx').write_text('export const O = 1;')
    (src / 'components' / 'TestOnly.jsx').write_text('export const T = 1;')
    (src / 'components' / 'TestOnly.test.jsx').write_text("import { T } from './TestOnly';")
    (back / 'used.py').write_text('X = 1'); (back / 'unused.py').write_text('Y = 1'); (back / 'server.py').write_text('import used')
    (back / 'by_script.py').write_text('Z = 1'); (tmp_path / 'scripts' / 'run.sh').write_text('python backend/by_script.py')
    rows = ch.dead_files(src, back, (tmp_path / 'scripts',))
    got = {r['name']: r['how'] for r in rows}
    assert got == {'Host.jsx': 'none', 'Orphan.jsx': 'none', 'TestOnly.jsx': 'tests', 'unused.py': 'none'}   # Host itself is imported by nobody here


def test_the_queue_route_files_a_build_item_and_never_touches_the_file(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(rs, '_require_owner', lambda req: 'OWNER')
    c = TestClient(rs.app)
    assert c.post('/api/reputation/admin/perf/code-health/queue', json={'file': '/etc/passwd'}).status_code == 400
    r = c.post('/api/reputation/admin/perf/code-health/queue', json={'file': 'frontend/src/components/Orphan.jsx', 'name': 'Orphan.jsx', 'kind': 'dead_file', 'fix': 'Nothing imports it'})
    assert r.status_code == 200 and r.json()['title'].startswith('🧹 Remove frontend/src/components/Orphan.jsx')
    q = rs._build_state()['items'][0]
    assert q['status'] == 'queued' and 'gate' in q['text']

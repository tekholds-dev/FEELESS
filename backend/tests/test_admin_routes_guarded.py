"""🔒 Air-tight HQ: every /admin route on every service must call an admin / owner gate before doing anything.
A route without one would let anyone hit an engine, a config or the numbers by calling the URL directly."""
import ast
import pathlib

SERVICES = ['reputation_service.py', 'server.py', 'feecat_service.py', 'candles_service.py']
PUBLIC_YES_NO = {'/api/reputation/admin/whoami', '/api/reputation/admin/is-admin/{address}'}   # tell the UI whether to show the HQ button; return a bool only
GATES = {'_require_admin', '_require_owner', '_role_gate', '_require_staff', 'require_admin'}


def _routes(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, 'attr', '') in ('get', 'post', 'put', 'delete', 'patch') and dec.args \
                    and isinstance(dec.args[0], ast.Constant) and '/admin' in str(dec.args[0].value):
                yield dec.args[0].value, node


def test_every_admin_route_calls_a_gate():
    base = pathlib.Path(__file__).resolve().parents[1]
    open_routes = []
    for svc in SERVICES:
        p = base / svc
        if not p.exists():
            continue
        for route, fn in _routes(p):
            called = {getattr(n.func, 'id', getattr(n.func, 'attr', '')) for n in ast.walk(fn) if isinstance(n, ast.Call)}
            if not called & GATES and route not in PUBLIC_YES_NO:
                open_routes.append(f'{svc} {route}')
    assert open_routes == []


def test_public_admin_checks_return_a_bool_only():
    import reputation_service as rs, asyncio
    assert set(asyncio.run(rs.admin_whoami('x'))) == {'isAdmin'}

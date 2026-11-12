"""🔘 Every /api path the site calls has a server route (owner 2026-11-12: "a button that ships must work — check the server accepts it; if it can't work, remove it").
Static scan: frontend fetch paths (templates → X) vs FastAPI routes (router prefixes included). Dynamic prefixes built at runtime are listed by hand."""
import glob, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DYNAMIC = {'/api/candles', '/api/market', '/api/reputation', '/api/trading',   # proxy / api-base prefixes, never called bare
           '/api/reputation/cats/X/X', '/api/reputation/fuses/X', '/api/reputation/wallet-dust/X/XX'}   # cats/{id}/{action}, fuses/{pane}, wallet-dust/{solana|evm}/{addr}?add=


def _scan(root):
    routes = []
    PFX = {'intelligence.py': '/api/intelligence', 'market.py': '/api/market', 'lifi.py': '/api/lifi', 'trading.py': '/api/trading', 'whitepaper.py': '/api/docs', 'pump_network.py': '/api/pump', 'server.py': ''}
    for f in glob.glob(f'{root}/backend/*.py'):
        pre = PFX.get(os.path.basename(f), '')
        src = open(f, errors='ignore').read()
        if 'APIRouter(prefix="/api")' in src: pre = '/api'
        for m in re.finditer(r"@api_router\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", src): routes.append((m.group(1), '/api' + m.group(2)))
        for m in re.finditer(r"@(?:app|router)\.(get|post|put|delete|patch|websocket|api_route)\(\s*['\"]([^'\"]+)['\"]", open(f, errors='ignore').read()):
            routes.append((m.group(1), (pre if not m.group(2).startswith('/api') else '') + m.group(2)))
    pats = [re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '[^/]+', re.escape(p)).replace(r'\{path:path\}', '.+') + '$') for _, p in routes]
    pats += [re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '.+', re.escape(p)) + '$') for _, p in routes]
    calls = {}
    for f in glob.glob(f'{root}/frontend/src/**/*.js*', recursive=True):
        if '.test.' in f or '/dev/' in f: continue
        for m in re.finditer(r"[`'\"](/api/[A-Za-z0-9_\-/{}\$\.:]+)", open(f, errors='ignore').read()):
            p = m.group(1)
            p = re.sub(r'\$\{[^}]*\}?', 'X', p).split('?')[0].rstrip('/')
            p = re.sub(r'(?<=[a-z\-])X$', '', p)   # ${query} glued on
            if p.endswith('X') and p.count('/') <= 2: continue
            calls.setdefault(p, set()).add(os.path.relpath(f, root + '/frontend/src'))
    miss = {}
    for p, fs in calls.items():
        if any(r.match(p) for r in pats): continue
        if any(r.match(p + '/X') or r.match(p+'X') for r in pats): continue   # prefix built at runtime
        miss[p] = fs
    return miss


def test_every_api_path_the_site_calls_has_a_route():
    miss = {p: f for p, f in _scan(ROOT).items() if p not in DYNAMIC}
    assert not miss, f'frontend calls with no server route (fix the route or remove the button): {miss}'

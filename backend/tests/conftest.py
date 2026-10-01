import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


# Shared API fixtures for public preview endpoint tests
load_dotenv(Path('/app/frontend/.env'))


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        pytest.skip("REACT_APP_BACKEND_URL is missing; cannot run public endpoint tests")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def api_client() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ---- Real data is never touched by tests ---------------------------------------------------------------------------
# Every module-level Path that points into backend/data (fee ledger, totals, points, trades, profiles, …) is redirected
# to a fresh temp folder for each test. A test once wrote a fake $100 trade into the real fee ledger on every run,
# inflating Command Center fees; this makes that impossible for any test, present or future.
import sys as _sys

_REAL_DATA = (Path(__file__).resolve().parents[1] / 'data').resolve()


def _sandbox_module(mod, sandbox, monkeypatch):
    f = getattr(mod, '__file__', None) or ''
    if not f.startswith(str(_REAL_DATA.parent)) or '/tests/' in f:
        return
    for name, val in list(vars(mod).items()):
        if isinstance(val, Path):
            try:
                rel = val.resolve().relative_to(_REAL_DATA)
            except ValueError:
                continue
            monkeypatch.setattr(mod, name, sandbox / rel, raising=False)


class _SandboxOnImport:
    """Backend modules first imported INSIDE a test (pytest.importorskip, lazy imports) are sandboxed the moment they
    load — a lazily imported reputation_service once wrote fixture rounds into the real runners.json."""
    def __init__(self, sandbox, monkeypatch):
        self.sandbox, self.mp = sandbox, monkeypatch

    def find_spec(self, name, path=None, target=None):
        import importlib.machinery as _m
        spec = _m.PathFinder.find_spec(name, path)
        if not spec or not spec.loader or not str(spec.origin or '').startswith(str(_REAL_DATA.parent)) or '/tests/' in str(spec.origin):
            return None
        run, me = spec.loader.exec_module, self

        def exec_module(module):
            run(module)
            _sandbox_module(module, me.sandbox, me.mp)
        spec.loader.exec_module = exec_module
        return spec


@pytest.fixture(autouse=True)
def _isolate_real_data(monkeypatch, tmp_path):
    sandbox = tmp_path / 'data'
    sandbox.mkdir(exist_ok=True)
    for mod in list(_sys.modules.values()):
        _sandbox_module(mod, sandbox, monkeypatch)
    hook = _SandboxOnImport(sandbox, monkeypatch)
    _sys.meta_path.insert(0, hook)
    try:
        yield
    finally:
        _sys.meta_path.remove(hook)

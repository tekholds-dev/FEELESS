"""📡 The no-money live check (owner 2026-11-16 proposals): every check is a GET, nothing it calls can sign or send, no GeckoTerminal. Network faked."""
import importlib.util
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('live_check', ROOT / 'scripts' / 'live-check.py'); lc = importlib.util.module_from_spec(spec); spec.loader.exec_module(lc)


class _R(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body); self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_reads_only_and_never_geckoterminal():
    urls = [u for _, u, _ in lc.CHECKS]
    assert all('geckoterminal' not in u.lower() for u in urls)
    assert not any(w in u for u in urls for w in ('/swap/v1/swap', '/execute', '/orders', 'sendTransaction'))   # a quote, never a swap or an order


def test_a_good_answer_passes_and_a_dead_one_warns_without_crashing():
    seen = []

    def opener(req, timeout=10):
        seen.append(req.get_method()); u = req.full_url
        if 'quote' in u:
            return _R(b'{"outAmount": "1450000"}')
        if 'kalshi' in u:
            raise OSError('connection refused')
        return _R(b'{"events": []}')
    rows = [lc.check(n, u, ok, opener) for n, u, ok in lc.CHECKS[:3]]
    assert [g for g, _ in rows] == [True, False, True] and 'connection refused' in rows[1][1]
    assert set(seen) == {'GET'}
    assert lc.main(lc.CHECKS[:3], opener) == 1
